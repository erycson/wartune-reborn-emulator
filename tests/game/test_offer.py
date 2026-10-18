from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Item, PlayerSnapshot
from wartune_server.protocol.messages import wartune_pb2 as pb


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _board(got: list) -> pb.RewardFreshRspMsg:  # type: ignore[type-arg]
    return pb.RewardFreshRspMsg.FromString(next(p for p in reversed(got) if p.code == 4197).body)


async def test_offer_board_refresh_accept_and_pass(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = _snap(g).character
        c.grades = 20
        g.client.send(8290, pb.RewardFreshReqMsg(isButton=False))
        board = _board(await g.until(4197))
        assert len(board.templateId) == 4 and list(board.isIsValid) == [1, 1, 1, 1] and board.freeTimes == 0

        for _ in range(2):  # 2 renovações grátis por dia
            g.client.send(8290, pb.RewardFreshReqMsg(isButton=True, payType=1))
        assert _board(await g.idle()).freeTimes == 2
        g.client.send(8290, pb.RewardFreshReqMsg(isButton=True, payType=0))  # 2 diamantes que não tem
        assert await g.idle() == []
        c.gift_token = 2
        g.client.send(8290, pb.RewardFreshReqMsg(isButton=True, payType=0))  # payType 0 aceita vinculado
        board = _board(await g.until(4197))
        assert c.gift_token == 0

        g.client.send(8288, pb.RewardAddedMsg(rewardId=1))
        got = await g.until(4197)
        [info] = pb.RewardUpdatedRspMsg.FromString(next(p for p in got if p.code == 4198).body).reward
        assert info.templateId == board.templateId[1] and info.isAccept and _board(got).isIsValid[1] == 2
        g.client.send(8288, pb.RewardAddedMsg(rewardId=2))  # uma por vez
        g.client.send(8291, pb.RewardFinishedReqMsg(templateId=info.templateId, isPass=True))  # sem contrato 2
        assert await g.idle() == []

        need = {int(r["Id"]): int(r["NeedPoint"]) for r in g.server.services.templates.rows("KingContracts")}
        c.point = need[2]  # o contrato 2 custa NeedPoint do template
        g.client.send(8540, pb.KingContractBuyMsg(ids=[2], friendId=g.user_id))
        await g.until(4434)
        gold = c.gold
        g.client.send(8291, pb.RewardFinishedReqMsg(templateId=info.templateId, isPass=True))
        got = await g.until(83)
        done = pb.RewardUpdatedRspMsg.FromString(next(p for p in got if p.code == 4198).body).reward[0]
        assert done.isComplete and _board(got).isIsValid[1] == 3 and _board(got).rewardTimes == 1
        assert c.gold > gold


async def test_ring_task_finish_with_item_or_diamonds(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        c = snap.character
        g.client.send(8732)  # nível < 35: só o estado
        assert [p.code for p in await g.idle()] == [4616]
        c.grades = 40
        g.client.send(8732)
        got = await g.until(4614)
        ring = pb.RewardUpdatedRspMsg.FromString(got[-1].body).reward[0].templateId
        assert ring and not pb.RewardUpdatedRspMsg.FromString(got[-1].body).reward[0].isComplete

        g.client.send(8730, pb.SimplePropertyMsg(param1=0))  # sem item nem 35 diamantes
        assert await g.idle() == []
        c.point = 35
        g.client.send(8730, pb.SimplePropertyMsg(param1=0))
        got = await g.until(83)
        assert pb.SimplePropertyMsg.FromString(next(p for p in got if p.code == 4616).body).param1 == 1
        assert pb.RewardUpdatedRspMsg.FromString(next(p for p in got if p.code == 4614).body).reward[0].isComplete
        assert c.point == 0

        g.client.send(8732)
        await g.until(4614)
        item = Item(c.id or 0, 2131021, count=1, pos=40)  # o item vale no lugar dos diamantes
        snap.items.append(item)
        await g.server.services.characters.save(item)
        g.client.send(8730, pb.SimplePropertyMsg(param1=0))
        got = await g.until(83)
        assert not any(i.template_id == 2131021 for i in snap.items) and got[0].code == 115
