import asyncio
from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb


def _of(got: list[Packet], code: int) -> list[bytes]:
    return [p.body for p in got if p.code == code]


async def test_players_see_each_other_in_the_sky_city(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")

        got_b = await b.idle()
        [present] = [pb.RoomEnterMsg.FromString(x) for x in _of(got_b, 4597)]
        assert [(p.playerId, p.nickName, p.campaignId) for p in present.player] == [(a.user_id, "Maga", 10000)]
        assert [p.code for p in got_b if p.code in (4597, 4594)] == [4597, 4594]  # 4594 só depois do 4597
        got_a = await a.idle()
        assert [pb.RoomEnterMsg.FromString(x).player[0].playerId for x in _of(got_a, 4597)] == [b.user_id]

        walk = pb.SpacePlayerMoveMsg()
        walk.players.add(playerId=999).path.extend([pb.PosMsg(x=73, y=74), pb.PosMsg(x=80, y=74)])
        a.client.send(8690, walk)
        [moved] = [pb.SpacePlayerMoveMsg.FromString(x) for x in _of(await b.idle(), 4594)]
        assert moved.players[0].playerId == a.user_id  # vale o da sessão, não o do pacote
        assert [(p.x, p.y) for p in moved.players[0].path] == [(73, 74), (80, 74)]
        assert _of(await a.idle(), 4594) == []  # sem eco

        b.client.send(8688, pb.SimplePropertyMsg(param1=10000))
        back = pb.RoomEnterMsg.FromString((await b.until(4606))[-1].body)
        assert back.player[0].playerId == b.user_id

        # relogin: a sessão anterior some (4607) antes da nova aparecer, já na posição de entrada
        a2 = await a.connect()
        codes = [p.code for p in await b.idle() if p.code in (4607, 4597)]
        assert codes == [4607, 4597]
        assert a2.server.online.get(a.user_id) is not None

        session_b = b.server.online.get(b.user_id)
        assert session_b is not None
        b.client.writer.close()
        await session_b.gone.wait()
        [gone] = [pb.SpacePlayerMoveMsg.FromString(x) for x in _of(await a2.idle(), 4607)]
        assert gone.players[0].playerId == b.user_id


async def test_tutorial_players_are_not_in_the_sky_city(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=0) as a:
        b = await a.join("bruxa")
        assert _of(await b.idle(), 4595) == [] and _of(await a.idle(), 4597) == []


async def test_two_logins_at_once_only_one_loads_the_character(tmp_path: Path) -> None:
    """Os dois 20001 passam pelo kick juntos; o segundo não pode virar sessão com snapshot velho."""
    async with logged_in(tmp_path, novice=19000) as a:
        online = a.server.online
        bound: list[int] = []
        bind = online.bind
        online.bind = lambda pid, s: (bound.append(pid), bind(pid, s))[1]  # type: ignore[method-assign]
        characters = a.server.services.characters
        load = characters.snapshot

        async def slow_snapshot(character_id: int):  # type: ignore[no-untyped-def]
            await asyncio.sleep(0.2)  # os dois logins ficam carregando ao mesmo tempo
            return await load(character_id)

        characters.snapshot = slow_snapshot  # type: ignore[method-assign]
        results = await asyncio.gather(a.connect(), a.connect(), return_exceptions=True)
        assert sum(not isinstance(r, BaseException) for r in results) == 1
        assert bound == [a.user_id] and len(online) == 1
