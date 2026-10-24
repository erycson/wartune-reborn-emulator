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


async def test_friend_request_texts_follow_the_english_official(tmp_path: Path) -> None:
    """oficial_encantar #1777-#1779 (pedido) e #1792-#1793 (o outro aceitou)."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        for g in (a, b):
            _session(g).snapshot.character.grades = 40  # type: ignore[union-attr]
        link = f'<a t="1" id="{b.user_id}" name="Bruxa" consortiaId="0" serverName="" grades="0" />'
        a.client.send(15003, pb.FriendRelationMsg(nickName="Bruxa", relation=1))
        got = await a.until(83)
        assert [p.code for p in got][-3:] == [78, 111, 83]
        assert _bodies(got, 78, pb.FriendInfoMsg)[0].relation == RelationType.PENDING
        alert = _bodies(got, 111, pb.ChatChannelMsg)[0]
        assert (alert.channel, alert.encodeMsg) == (111, "Added successfully, awaiting the other player's response.")
        assert _bodies(got, 83, pb.ChatChannelMsg)[0].encodeMsg == f"You added a new friend: {link}."

        await b.until(84)
        b.client.send(15003, pb.FriendRelationMsg(nickName="Maga", relation=1))
        got = await a.until(83)
        assert [p.code for p in got] == [165, 83]
        assert _bodies(got, 165, pb.FriendInfoMsg)[0].relation == RelationType.FRIEND
        text = _bodies(got, 83, pb.ChatChannelMsg)[0].encodeMsg
        assert text == f"{link} has added you to his/her friends list."


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
        assert (group.groupId, group.groupName) == (4, "guerra")  # o 3 é a lista negra (FridendsListView)
        for name in ("a|b", "paz", "trégua", "fim"):  # | proibido; 3 grupos no máximo
            a.client.send(15025, pb.FriendGroupMsg(groupName=name))
        got = await a.until(4227)
        made = _bodies([*got, *await a.idle()], 4227, pb.FriendGroupMsg)
        assert [(g.groupId, g.groupName) for g in made][-1] == (6, "trégua")
        assert len(_session(a).snapshot.groups) == 3  # type: ignore[union-attr]

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


async def test_recommend_list_is_empty_like_the_official_unless_enabled(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #71, #4219, #5864: 85 vazio; ``game_settings.friend_recommend`` liga a lista."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        b.server.online.get(b.user_id).snapshot.character.grades = 20  # type: ignore[union-attr]
        world = a.server.services.world
        assert world.settings["friend_recommend"] is False  # migração 0070
        a.client.send(15013)
        got = pb.RecommendListMsg.FromString((await a.until(85))[-1].body)
        assert list(got.girlList) == list(got.boyList) == []
        object.__setattr__(world, "settings", {**world.settings, "friend_recommend": True})  # só do teste
        a.client.send(15013)
        got = pb.RecommendListMsg.FromString((await a.until(85))[-1].body)
        assert [p.playerId for p in (*got.girlList, *got.boyList)] == [b.user_id]


async def test_user_info_carries_the_friendship(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #7758: 4256 com relation 1, friendRp, friendGrade 1 e groupId 2 do amigo."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await _friends(a, b)
        a.client.send(15038, pb.InfoReqMsg(otherId=b.user_id))
        info = pb.RelationPlayerMsg.FromString((await a.until(4256))[-1].body)
        assert (info.relation, info.friendRp, info.friendGrade, info.groupId) == (1, 0, 1, 2)


async def test_friend_messages_match_the_official_fields(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1: 78 com ``onlineState`` 7 e ``snsInfo`` sem ``job`` (#6069); o 165 do aceite só
    com a amizade e a guilda (#6143)."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        for g in (a, b):
            _session(g).snapshot.character.grades = 40  # type: ignore[union-attr]
        a.client.send(15003, pb.FriendRelationMsg(nickName="Bruxa", relation=1))
        added = pb.FriendInfoMsg.FromString((await a.until(78))[-1].body)
        assert added.onlineState == 7 and not added.snsInfo.HasField("job")
        await b.until(84)
        b.client.send(15003, pb.FriendRelationMsg(nickName="Maga", relation=1))
        await b.until(78)
        update = pb.FriendInfoMsg.FromString((await a.until(165))[-1].body)
        assert (update.userId, update.relation, update.relationGrade, update.groupId) == (b.user_id, 1, 1, 2)
        assert not update.HasField("nickName") and not update.HasField("snsInfo")
