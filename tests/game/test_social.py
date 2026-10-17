from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import RelationType
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


def _bodies[T](got: list, code: int, kind: type[T]) -> list[T]:  # type: ignore[type-arg]
    return [kind.FromString(p.body) for p in got if p.code == code]  # type: ignore[attr-defined]


async def _friends(a: Game, b: Game) -> None:
    for g in (a, b):
        _session(g).snapshot.character.grades = 40  # type: ignore[union-attr]
    a.client.send(15003, pb.FriendRelationMsg(nickName="Bruxa", relation=1))
    await a.until(78)
    await b.until(84)
    b.client.send(15003, pb.FriendRelationMsg(nickName="Maga", relation=1))
    await b.until(78)
    await a.until(165)


async def test_friend_request_accept_and_login_logout_notice(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await _friends(a, b)
        assert [r.relation for r in _session(a).snapshot.relations] == [RelationType.FRIEND]  # type: ignore[union-attr]
        assert [r.relation for r in _session(b).snapshot.relations] == [RelationType.FRIEND]  # type: ignore[union-attr]

        session_b = _session(b)
        b.client.writer.close()
        await session_b.gone.wait()
        assert _bodies(await a.until(161), 161, pb.FriendRelationMsg)[-1].otherId == b.user_id

        again = await b.connect()
        assert _bodies(await a.until(160), 160, pb.FriendRelationMsg)[-1].otherId == b.user_id
        friends = _bodies(await again.idle(), 4156, pb.FriendRelationList)
        assert friends == [] or friends[-1].maxPage == 1


async def test_blacklist_hides_private_chat(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await _friends(a, b)
        b.client.send(15003, pb.FriendRelationMsg(nickName="Maga", relation=2))
        await b.until(78)
        await a.idle()
        a.client.send(15023, pb.ChatFriendMsg(toId=b.user_id, encodeMsg="oi"))
        assert pb.ChatFriendMsg.FromString((await a.until(4236))[-1].body).result == -1
        assert all(p.code != 4231 for p in await b.idle())


async def test_groups_and_lookups(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        a.client.send(15025, pb.FriendGroupMsg(groupName="guerra"))
        group = _bodies(await a.until(4227), 4227, pb.FriendGroupMsg)[-1]
        assert group.groupId >= 3 and group.groupName == "guerra"

        a.client.send(8223, pb.CheckNickMsg(nickName="Bruxa"))
        assert _bodies(await a.until(4148), 4148, pb.CheckNickMsg)[-1].playerId == b.user_id
        a.client.send(8223, pb.CheckNickMsg(nickName="Ninguem"))
        assert _bodies(await a.until(4148), 4148, pb.CheckNickMsg)[-1].playerId == -1

        a.client.send(8257, pb.SimplePlayerSearchReqMsg(otherNickname="Bruxa"))
        found = _bodies(await a.until(4170), 4170, pb.SimplePlayerSearchRspMsg)[-1]
        assert found.HasField("info")

        a.client.send(8285)
        assert _bodies(await a.until(4193), 4193, pb.RefuseFriendRspMsg)[-1].result is True


async def test_rename_needs_card_and_free_name(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await a.join("bruxa")
        taken = await a.http.post("/nicknamecheck", data={"nickname": "Bruxa"})
        assert 'value="false"' in await taken.text()
        free = await a.http.post("/nicknamecheck", data={"nickname": "Novo"})
        assert 'value="true"' in await free.text()

        a.client.send(8345, pb.PlayerRenameReqMsg(type=1, pos=0, nickName="Novo"))  # sem carta
        assert _bodies(await a.until(4271), 4271, pb.PlayerRenameRspMsg)[-1].result is False

        _session(a).snapshot.character.nickname = "Maga!"  # type: ignore[union-attr]  # nome de fusão
        a.client.send(8345, pb.PlayerRenameReqMsg(type=2, nickName="Novo"))
        assert _bodies(await a.until(4271), 4271, pb.PlayerRenameRspMsg)[-1].result is True
        assert _session(a).snapshot.castle.name == "Novo"  # type: ignore[union-attr]
