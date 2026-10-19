from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.protocol.messages import wartune_pb2 as pb


async def _grade(g: Game, grades: int) -> None:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    session.snapshot.character.grades = grades


def _chats(got: list) -> list[pb.ChatChannelMsg]:  # type: ignore[type-arg]
    return [pb.ChatChannelMsg.FromString(p.body) for p in got if p.code == 83]


async def test_world_chat_reaches_everyone_with_the_server_filling_the_sender(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await _grade(a, 20)
        await a.idle()

        forged = '<a t="1" id="1" name="GM"/>oi <b>todos</b>'
        a.client.send(8198, pb.ChatChannelMsg(channel=10, encodeMsg=forged, name="GM", userType=2))
        for g in (a, b):
            [msg] = _chats(await g.idle())
            assert (msg.channel, msg.encodeMsg, msg.otherId, msg.name, msg.userType) == (
                10,
                "oi todos",
                a.user_id,
                "Maga",
                0,
            )

        a.client.send(8198, pb.ChatChannelMsg(channel=10, encodeMsg="de novo"))  # antes de 2 s
        assert _chats(await b.idle()) == []


async def test_world_chat_needs_level_20_and_keeps_the_free_bugle(tmp_path: Path) -> None:
    """tutorial_en #2779-#2782: no nível 14 o 8198 recebe só o 111; a cota grátis (SMALL_BUGLE_FREE_COUNT) fica."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await _grade(a, 14)
        await a.idle()
        a.client.send(8198, pb.ChatChannelMsg(channel=10, encodeMsg="Olá"))
        got = await a.idle()
        assert [p.code for p in got] == [111]
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "Requires character Level of 20"
        assert _chats(await b.idle()) == []
        a.client.send(8705)
        assert pb.CampaignReqMsg.FromString((await a.until(4500))[-1].body).paraInt1 == 10


async def test_chat_needs_level_6(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        a.client.send(15005, pb.ChatChannelMsg(channel=8, encodeMsg="oi"))
        assert _chats(await b.idle()) == []


async def test_private_chat_and_offline_target(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await _grade(a, 6)
        await b.idle()

        a.client.send(15023, pb.ChatFriendMsg(toId=b.user_id, encodeMsg="psiu", fromNick="GM"))
        got = await b.until(4231)
        msg = pb.ChatFriendMsg.FromString(got[-1].body)
        assert (msg.fromId, msg.fromNick, msg.encodeMsg) == (a.user_id, "Maga", "psiu")
        echo = pb.ChatFriendMsg.FromString((await a.until(4236))[-1].body)
        assert echo.result == 0 and echo.toId == b.user_id

        b.client.send(15038, pb.InfoReqMsg(otherId=a.user_id, **{"from": 2}))
        info = pb.RelationPlayerMsg.FromString((await b.until(4256))[-1].body)
        assert (info.player.userId, info.player.nickName, getattr(info, "from")) == (a.user_id, "Maga", 2)

        session_b = b.server.online.get(b.user_id)
        assert session_b is not None
        b.client.writer.close()
        await session_b.gone.wait()
        a.server.online.get(a.user_id).chat_at.clear()  # type: ignore[union-attr]  # sem esperar o intervalo
        a.client.send(15023, pb.ChatFriendMsg(toId=b.user_id, encodeMsg="ainda aí?"))
        assert pb.ChatFriendMsg.FromString((await a.until(4236))[-1].body).result == -1


async def test_small_bugle_free_quota_then_item(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await _grade(a, 6)
        session = a.server.online.get(a.user_id)
        assert session is not None and session.snapshot is not None
        c = session.snapshot.character
        c.bugle_free_day, c.bugle_free_used = session.ctx.clock.now().date().isoformat(), 10
        a.client.send(8705)
        assert pb.CampaignReqMsg.FromString((await a.until(4500))[-1].body).paraInt1 == 0
        await b.idle()

        a.client.send(8198, pb.ChatChannelMsg(channel=10, encodeMsg="sem corneta"))
        assert _chats(await b.idle()) == []
