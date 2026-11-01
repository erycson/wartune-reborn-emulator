import json
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Item, PlayerSnapshot
from wartune_server.game import events as ev
from wartune_server.game.handlers import offer
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
        g.client.send(
            8290, pb.RewardFreshReqMsg(isButton=True, payType=0)
        )  # 10 Balens que não tem (REFRESH_REWARD_NEEDPAY)
        assert await g.idle() == []
        c.point, c.gift_token = 0, 10
        g.client.send(8290, pb.RewardFreshReqMsg(isButton=True, payType=0))  # payType 0 aceita vinculado
        board = _board(await g.until(4197))
        assert c.gift_token == 0
        await g.idle()  # o 4152/83 do leed 15 (gasto de diamante) vem depois do 4197

        g.client.send(8288, pb.RewardAddedMsg(rewardId=1))
        got = await g.until(4197)
        [info] = pb.RewardUpdatedRspMsg.FromString(next(p for p in got if p.code == 4198).body).reward
        assert [p.code for p in got] == [4198, 4197]  # oficial_20261023-231733-1 #1465-#1466
        assert info.templateId == board.templateId[1] and not info.isAccept and info.repeatFinish == 1
        assert _board(got).isIsValid[1] == 2
        g.client.send(8288, pb.RewardAddedMsg(rewardId=2))  # uma por vez
        g.client.send(8291, pb.RewardFinishedReqMsg(templateId=info.templateId, isPass=True))  # sem contrato 2
        assert await g.idle() == []

        need = {int(r["Id"]): int(r["NeedPoint"]) for r in g.server.services.templates.rows("KingContracts")}
        c.point = need[2]  # o contrato 2 custa NeedPoint do template
        g.client.send(8540, pb.KingContractBuyMsg(ids=[2], friendId=g.user_id))
        await g.until(4434)
        gold = c.gold
        g.client.send(8291, pb.RewardFinishedReqMsg(templateId=info.templateId, isPass=True))
        got = await g.until(4196) + await g.until(83)
        done = pb.RewardUpdatedRspMsg.FromString(next(p for p in got if p.code == 4198).body).reward[0]
        assert done.isComplete and done.isAccept and _board(got).isIsValid[1] == 3 and _board(got).rewardTimes == 1
        assert c.gold > gold
        leed = pb.LeedUpdatedRspMsg.FromString(next(p for p in got if p.code == 4152).body)  # leed 24
        assert [(x.templateId, x.currentCount, x.isComplete) for x in leed.leed] == [(24, 1, False)]  # PassCount 5


async def test_bounty_24_counts_friend_trees_and_finishes_without_pass(tmp_path: Path) -> None:
    """(visto) oficial_20261024-121659-1: 4198 a cada rega de árvore de amigo (#230, #241) e a entrega sem passe
    (#498-#506): 109, 3, 4197, 4198, 4152, 4413, 4196 e "Received 18,240 EXP "."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        snap.character.grades = 19
        s = g.server.online.get(g.user_id)
        assert s is not None
        board = ev.state(snap, "offer:list", s.ctx.clock.now())
        board.text = json.dumps({"ids": [24, 25, 46, 24], "q": [5, 4, 2, 4], "st": [1, 1, 1, 1]})
        g.client.send(8288, pb.RewardAddedMsg(rewardId=0))
        await g.until(4197)
        g.client.send(8291, pb.RewardFinishedReqMsg(templateId=24, isPass=False))  # nada feito ainda
        assert await g.idle() == []

        for step in (1, 2, 3):  # a terceira passa do Para2 2: não manda nada
            await offer.progress(s, offer.TREE_FRIEND)
            got = await g.idle()
            if step < 3:
                [info] = pb.RewardUpdatedRspMsg.FromString(got[-1].body).reward
                assert (info.condition_1, info.isAccept, info.isComplete) == (step, False, False)
            else:
                assert got == []

        g.client.send(8291, pb.RewardFinishedReqMsg(templateId=24, isPass=False))
        got = await g.until(4196) + await g.until(83)
        assert [p.code for p in got] == [109, 3, 4197, 4198, 4152, 4413, 4196, 83]
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Received 18,240 EXP "
        [done] = pb.RewardUpdatedRspMsg.FromString(got[3].body).reward
        assert (done.condition_1, done.isAccept, done.isComplete) == (2, True, True)
        # (visto) 121659 #504-#505: 4413 {"reward", 1, hora} e 4196 com o TemplateId ("0818")
        [click] = pb.ClickDatasRspMsg.FromString(got[5].body).info
        assert (click.keys, click.keyData) == ("reward", 1)
        assert got[6].body == bytes.fromhex("0818")


def test_click_keeps_first_time_of_day() -> None:
    """(visto) 20261030-151436 #587-#1974: o ``changeTime`` do "reward" fica na hora do 1º do dia."""
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    snap: PlayerSnapshot = SimpleNamespace(character=SimpleNamespace(id=1), events=[])  # type: ignore[assignment]
    first = datetime(2026, 10, 30, 13, 58, 4, tzinfo=UTC)
    ev.click(snap, "reward", first)
    st = ev.click(snap, "reward", first + timedelta(minutes=30))
    assert (st.value, st.updated_at) == (2, first)


async def test_arrest_opens_army_battle_against_the_npc(tmp_path: Path) -> None:
    """(visto) 20261030-145704 #245-#247: 8298 -> um 140 do exército em luta e a 157 battleType 12, mapTempId 1,
    com as tropas e o herói NPC (type 3) do ``Para1``. NPC fora de qualquer condição 14: nada."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        s = g.server.online.get(g.user_id)
        assert s is not None
        row = next(r for r in s.ctx.templates.rows("RewardCondictionInfos") if int(r["CondictionType"]) == 14)
        tid, npc = int(row["TemplateId"]), int(row["Para1"])
        board = ev.state(snap, "offer:list", s.ctx.clock.now())
        board.text = json.dumps({"ids": [tid], "q": [1], "st": [1]})
        g.client.send(8288, pb.RewardAddedMsg(rewardId=0))
        await g.until(4197)

        g.client.send(8298, pb.RewardArrestMsg(param1=npc + 123456, condictionType=14))
        assert await g.idle() == []
        g.client.send(8298, pb.RewardArrestMsg(param1=npc, condictionType=14))
        got = await g.until(157)
        assert [p.code for p in got].count(140) == 1
        army = pb.MapUpdatedMsg.FromString(next(p.body for p in got if p.code == 140)).army
        prep = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert army.state == 2 and (prep.battleType, prep.mapTempId) == (12, 1)
        enemy = next(h for h in prep.heros if h.side == 2)
        assert (enemy.tempId, enemy.type) == (npc, 3)


async def test_ring_task_finish_with_item_or_diamonds(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        c = snap.character
        g.client.send(8732)  # nível < 35: nada
        assert await g.idle() == []
        c.grades = 40
        g.client.send(8732)
        got = await g.until(111)  # 4614 e o "Circuit Quest has been accepted!"
        ring = pb.RewardUpdatedRspMsg.FromString(got[-2].body).reward[0].templateId
        assert ring and not pb.RewardUpdatedRspMsg.FromString(got[-2].body).reward[0].isComplete

        g.client.send(8730, pb.SimplePropertyMsg(param1=0))  # sem item nem 35 diamantes
        assert await g.idle() == []
        c.point = 35
        g.client.send(8730, pb.SimplePropertyMsg(param1=0))
        got = await g.until(83)
        assert pb.SimplePropertyMsg.FromString(next(p for p in got if p.code == 4616).body).param1 == 1
        assert pb.RewardUpdatedRspMsg.FromString(next(p for p in got if p.code == 4614).body).reward[0].isComplete
        assert c.point == 0
        assert 4617 in [p.code for p in got + await g.idle()]  # fim do anel, vazio (165308 #8309)

        g.client.send(8732)
        await g.until(111)
        item = Item(c.id or 0, 2131021, count=1, pos=40)  # o item vale no lugar dos diamantes
        snap.items.append(item)
        await g.server.services.characters.save(item)
        g.client.send(8730, pb.SimplePropertyMsg(param1=0))
        got = await g.until(83)
        assert not any(i.template_id == 2131021 for i in snap.items) and got[0].code == 115


async def test_anel_aceite_e_entrega_do_recrutar_como_a_captura(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """165308 #9367-#9392: 8732 manda 4614 e o 111 (sem 4616); 8729 leva os 200 Paladinos (100), 4616 e o texto."""
    from wartune_server.domain.models import Pawn

    monkeypatch.setattr(offer, "_roll_ring", lambda s, snap: 2103)  # "Recruit Paladins" (SonType 103, 200)
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        snap.character.grades = 35
        g.client.send(8732)
        got = await g.idle()
        assert [p.code for p in got] == [4614, 111]
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg == offer.ACCEPTED_TEXT
        g.client.send(8729)  # sem as tropas: nada
        assert await g.idle() == []
        pawn = Pawn(snap.character.id or 0, 10329)
        pawn.castle_count = 200
        snap.pawns.append(pawn)
        g.client.send(8729)
        got = await g.until(83)
        codes = [p.code for p in got]
        assert codes.index(100) < codes.index(4616) < codes.index(4617) and pawn.castle_count == 0
        first = pb.RewardUpdatedRspMsg.FromString(next(p.body for p in got if p.code == 4614)).reward[0]
        assert (first.condition_1, first.isComplete) == (200, False)
        last = pb.RewardUpdatedRspMsg.FromString([p.body for p in got if p.code == 4614][-1]).reward[0]
        assert last.isComplete and last.isAccept
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == (
            "Complete Circuit Quests (1/200) Received: 2,000 Gold, 10,000 Daru"
        )


async def test_anel_eliminar_sorteia_masmorra_e_conta_so_nela(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(offer, "_roll_ring", lambda s, snap: 2102)  # "Eliminate the monsters in {0}"
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        _snap(g).character.grades = 35
        g.client.send(8732)
        info = pb.RewardUpdatedRspMsg.FromString((await g.until(4614))[-1].body).reward[0]
        assert info.condition_2 > 0 and info.condition_4 in (20, 30)
        await g.idle()
        await offer.progress(s, offer.ELIMINATE, 18, info.condition_2 + 1)  # outra masmorra não conta
        assert await g.idle() == []
        for _ in range(2):
            await offer.progress(s, offer.ELIMINATE, 18, info.condition_2)
        got = [pb.RewardUpdatedRspMsg.FromString(p.body).reward[0] for p in await g.idle() if p.code == 4614]
        assert got[-1].condition_1 == info.condition_4
        g.client.send(8729)
        assert (
            pb.RewardUpdatedRspMsg.FromString([p.body for p in await g.until(83) if p.code == 4614][-1])
            .reward[0]
            .isComplete
        )
