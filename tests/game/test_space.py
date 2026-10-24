import asyncio
from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.domain.models import Item
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb


def _of(got: list[Packet], code: int) -> list[bytes]:
    return [p.body for p in got if p.code == code]


async def test_players_see_each_other_in_the_sky_city(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as a:
        b = await a.join("bruxa")

        got_b = await b.idle()
        [present] = [pb.RoomEnterMsg.FromString(x) for x in _of(got_b, 4597)]
        assert [(p.playerId, p.nickName, p.campaignId) for p in present.player] == [(a.user_id, "Maga", 10000)]
        assert (present.player[0].curPosX, present.player[0].curPosY) == (76, 76)  # personagem novo: tutorial_en #7
        assert [p.code for p in got_b if p.code in (4597, 4594)] == [4597, 4594]  # 4594 só depois do 4597
        got_a = await a.idle()
        assert [pb.RoomEnterMsg.FromString(x).player[0].playerId for x in _of(got_a, 4597)] == [b.user_id]
        assert [p.code for p in got_a if p.code in (4597, 4594, 149)] == [4597, 4594, 149]  # 215937 #826-#830
        assert pb.HeroEquUpdatedMsg.FromString(_of(got_a, 149)[0]).playerId == b.user_id

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


async def test_login_before_the_end_of_the_tutorial_has_no_sky_city(tmp_path: Path) -> None:
    """(visto) oficial_encantar #98-#99: noviceProcess 28500, do 6 direto ao 4151, sem 4595."""
    async with logged_in(tmp_path, novice=28500) as a:
        assert _of(await a.idle(), 4595) == []
        session = a.server.online.get(a.user_id)
        assert session is not None and session.space_pos is None


async def test_two_logins_at_once_only_one_loads_the_character(tmp_path: Path) -> None:
    """Os dois 20001 passam pelo kick juntos; o segundo não pode virar sessão com snapshot velho."""
    async with logged_in(tmp_path, novice=33000) as a:
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


async def test_sky_city_remembers_position_and_shows_new_equipment(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as a:
        b = await a.join("bruxa")
        await a.idle()
        session_a = a.server.online.get(a.user_id)
        assert session_a is not None and session_a.snapshot is not None and session_a.snapshot.leader is not None
        weapon = Item(a.user_id, 1013002, pos=0)
        session_a.snapshot.items.append(weapon)
        await a.server.services.characters.save(weapon)

        hero = session_a.snapshot.leader.id
        a.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=4, endObjId=hero, endPos=0))
        [look] = [pb.HeroEquUpdatedMsg.FromString(x) for x in _of(await b.idle(), 149)]
        assert look.playerId == a.user_id and look.armStr.startswith("/")

        walk = pb.SpacePlayerMoveMsg()
        walk.players.add().path.extend([pb.PosMsg(x=90, y=60)])
        a.client.send(8690, walk)
        await b.idle()
        a2 = await a.connect()  # relogin: volta onde parou, não em (76,76)
        session = a2.server.online.get(a.user_id)
        assert session is not None and session.space_pos == (90, 60)

        await a2.idle()
        a2.client.send(8701, pb.SpacePlayerArmyInfoReqMsg(userList=[b.user_id, 999]))
        [info] = [pb.RoomEnterMsg.FromString(x) for x in _of(await a2.idle(), 4597)]
        assert [p.playerId for p in info.player] == [b.user_id]


def _walk(x: int, y: int) -> pb.SpacePlayerMoveMsg:
    msg = pb.SpacePlayerMoveMsg()
    msg.players.add().path.extend([pb.PosMsg(x=x, y=y)])
    return msg


async def test_space_nodes_and_pet_island(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as a:
        b = await a.join("bruxa")
        await a.idle()
        c = a.client
        c.send(8692, pb.SimplePropertyMsg(param1=1))  # Bounty Board em (142,112): longe demais
        assert _of(await a.idle(), 4601) == []
        c.send(8690, _walk(140, 112))
        c.send(8692, pb.SimplePropertyMsg(param1=1))
        assert [pb.SimplePropertyMsg.FromString(x).param1 for x in _of(await a.idle(), 4601)] == [1]

        c.send(8690, _walk(20, 112))
        c.send(8692, pb.SimplePropertyMsg(param1=5))  # Sylph Atoll pede nível 50
        assert await a.idle() == []
        session = a.server.online.get(a.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.grades = 50
        await b.idle()
        c.send(8692, pb.SimplePropertyMsg(param1=5))
        got = await a.idle()
        assert [p.code for p in got] == [140, 125, 21]
        assert pb.RoomCreatedMsg.FromString(got[1].body).room.campaignId == 20001
        assert _of(await b.idle(), 4607) != []  # sumiu da cidade do céu dos outros

        c.send(5035, pb.LoginStateMsg(state=4))  # cena carregada: o oficial repete o 21, o 127 e a patrulha
        got = await a.idle()
        assert [p.code for p in got][:2] == [21, 127] and set([p.code for p in got][2:]) <= {4122}
        assert len(pb.CampaignNodeListMsg.FromString(got[1].body).node) == 121
        walkers = {pb.NPCMoveMsg.FromString(p.body).id for p in got if p.code == 4122}
        assert walkers and walkers <= {n.nodeId for n in pb.CampaignNodeListMsg.FromString(got[1].body).node}
        c.send(5125, pb.CampaignReqMsg(paraInt1=2000101, paraBool1=True))  # pisar no nó de chegada não sai
        assert _of(await a.idle(), 4606) == []

        c.send(5025, pb.RoomExitMsg(msg=""))  # botão de sair
        back = [pb.RoomEnterMsg.FromString(x) for x in _of(await a.idle(), 4606)]
        assert back and back[0].player[0].campaignId == 10000 and session.campaign is None
        assert _of(await b.idle(), 4597) != []

        c.send(8689, pb.SimplePropertyMsg())
        assert _of(await b.idle(), 4607) != []
