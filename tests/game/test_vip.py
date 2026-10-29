from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, Item, PlayerSnapshot
from wartune_server.game import events as ev
from wartune_server.game.builders import login as b
from wartune_server.game.handlers import vip
from wartune_server.protocol.messages import wartune_pb2 as pb

TRIAL_CARD = 2031201  # VIP Trial Card


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _ledger(g: Game) -> list[tuple[int, int, str]]:
    async with g.server.services.database.sessions() as db:
        rows = (await db.execute(select(CashLedger).order_by(CashLedger.id))).scalars()  # type: ignore[arg-type]
        return [(r.delta_point, r.delta_gift_token, r.reason) for r in rows]


async def test_alchemy_and_soul_spend_diamonds(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        c = snap.character
        g.client.send(8320)  # nível 1: o oficial não responde (tutorial_en #17)
        g.client.send(8466)
        assert await g.idle() == []
        c.grades = 14  # MainToolBar pede de novo no 14
        g.client.send(8320)
        lucky = pb.PlayerLuckyMsg.FromString((await g.until(4224))[-1].body)
        assert (lucky.luckyCount, lucky.remainCount, lucky.point) == (
            0,
            20,
            2,
        )  # point 2 com 0 usos (oficial_encantar #7)
        assert lucky.gold > 0

        c.point, c.gift_token, gold = 0, 100, c.gold
        g.client.send(8321, pb.PlayerLuckyMsg())  # AlchemyFrame: o 1º do dia é grátis
        after = pb.PlayerLuckyMsg.FromString((await g.until(4224))[-1].body)
        assert (after.luckyCount, after.point) == (1, 4) and c.gold == gold + lucky.gold
        g.client.send(8321, pb.PlayerLuckyMsg())  # 50 Balens que não tem (vinculado não paga): só devolve o estado
        assert pb.PlayerLuckyMsg.FromString((await g.until(4224))[-1].body).luckyCount == 1
        c.point = 60
        g.client.send(8321, pb.PlayerLuckyMsg())
        after = pb.PlayerLuckyMsg.FromString((await g.until(4224))[-1].body)
        assert (after.luckyCount, after.point) == (2, 6) and (c.point, c.gift_token) == (10, 100)
        assert await _ledger(g) == [(-50, 0, "alchemy")]

        g.client.send(8467, pb.PlayerRefiningSoulMsg())  # nível < RefiningSoul_Grades (24)
        assert pb.PlayerRefiningSoulMsg.FromString((await g.until(4372))[-1].body).count == 0
        c.grades, strategy = 30, c.strategy
        g.client.send(8467, pb.PlayerRefiningSoulMsg())  # SoulMakeFrame: também grátis no 1º
        soul = pb.PlayerRefiningSoulMsg.FromString((await g.until(4372))[-1].body)
        assert (soul.count, soul.point) == (1, 50) and c.point == 10 and c.strategy == strategy + soul.soul
        assert soul.soul == 500 * 2  # Barracks e Cottage nível 1 x 500 (SoulMakeFrame.refreshView)

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.point == 10


async def test_login_manda_4224_e_4372_a_partir_do_nivel(tmp_path: Path) -> None:
    """(visto) oficial_20261027-152321-1 #8-#9: no login de nível 30 vêm o 4224 e o 4372; no nível 1 (tutorial_en)
    nenhum dos dois."""
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        await vip.login_push(s)
        assert not {4224, 4372} & {p.code for p in await g.idle()}
        _snap(g).character.grades = 30
        await vip.login_push(s)
        codes = [p.code for p in await g.idle()]
        assert 4224 in codes and 4372 in codes


async def test_vip_open_gift_and_king_contract(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = _snap(g).character
        g.client.send(8513, pb.VipOpenInfoMsg(days=31))  # 298 diamantes que não tem
        assert await g.idle() == []

        c.point = 400
        ev.state(_snap(g), "vip", datetime.now(UTC)).value = 300  # VIP 3 de compras antigas; o dia da compra soma 10
        g.client.send(8513, pb.VipOpenInfoMsg(days=31))
        got = await g.until(4416)
        info = pb.VipInfoMsg.FromString(next(p for p in got if p.code == 4410).body)
        assert (info.isVip, info.isExpirt, info.isTakeGift, info.vipGp, info.vipGrade) == (True, False, True, 310, 3)
        leed = pb.LeedUpdatedRspMsg.FromString((await g.until(4152))[-1].body)  # leed 15 (gasto de diamante)
        await g.until(83)
        assert leed.totalNum == 5 + 10 + 10  # login + leed 15 + "Devotion Bonus" do VIP 3
        assert c.point == 102

        g.client.send(8505)  # presente semanal: VipDrop site 3
        got = await g.idle()
        assert [p.code for p in got if p.code not in (3, 109)] == [
            115,
            4476,
            *[4484] * 9,
            111,
            4410,
            4539,
            83,
        ]  # tutorial_en #3266-#3282
        text = pb.ChatChannelMsg.FromString(next(p for p in got if p.code == 111).body).encodeMsg
        assert text.startswith("Received: ") and pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == text
        info = pb.VipInfoMsg.FromString(next(p for p in got if p.code == 4410).body)
        assert info.isTakeGift is False and info.takeGiftDate == b.fmt_time(vip.next_gift(_now(g)))
        g.client.send(8505)  # mesma semana
        assert await g.idle() == []

        need = {int(r["Id"]): int(r["NeedPoint"]) for r in g.server.services.templates.rows("KingContracts")}
        c.point = need[2] + 12  # sobram 12 depois do contrato 2; o 3 custa mais que isso
        assert need[3] > c.point
        g.client.send(8540, pb.KingContractBuyMsg(ids=[3], friendId=g.user_id))  # recusado: sem diamante
        g.client.send(8540, pb.KingContractBuyMsg(ids=[2], friendId=g.user_id))
        king = pb.KingContractMsg.FromString((await g.until(4434))[-1].body)
        assert [k.contractId for k in king.kingContractInfos] == [2] and c.point == 12  # só os comprados
        assert await _ledger(g) == [(-298, 0, "vip"), (-need[2], 0, "king_contract")]

        g.client.send(8519, pb.VipRouletteMsg())  # sem abrir a roleta: 4415 sem isStart
        got = await g.idle()
        assert [p.code for p in got] == [4415] and pb.VipRouletteMsg.FromString(got[0].body).isStart is False


def _now(g: Game) -> datetime:
    session = g.server.online.get(g.user_id)
    assert session is not None
    return session.ctx.clock.now()


def test_weekly_gift_comes_back_on_the_monday_after_next() -> None:
    sunday = datetime(2026, 10, 18, 15, 30, tzinfo=UTC)  # tutorial_en #3280
    assert vip.next_gift(sunday) == datetime(2026, 10, 26, tzinfo=UTC)
    assert vip.next_gift(datetime(2026, 10, 19, 9, tzinfo=UTC)) == datetime(2026, 10, 26, tzinfo=UTC)
    assert vip.next_gift(datetime(2026, 10, 24, 23, tzinfo=UTC)) == datetime(2026, 10, 26, tzinfo=UTC)


async def test_vip_trial_card_extends_and_marks_type_2(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        hours = int(g.server.services.templates.get("ItemTempInfos", TRIAL_CARD)["Property3"])  # type: ignore[index]
        card = Item(g.user_id, TRIAL_CARD, pos=0)
        snap.items.append(card)
        await g.server.services.characters.save(card)
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        got = await g.idle()
        assert [p.code for p in got] == [115, 111, 4410, 3]  # tutorial_en #3259-#3263
        end = _now(g) + timedelta(hours=hours)
        text = f"Your VIP service has been extended {hours} hours; new expiration date is {end:%Y-%m-%d}."
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg == text
        info = pb.VipInfoMsg.FromString(got[2].body)
        assert (info.isVip, info.vipType, info.isTakeGift) == (True, 2, True)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert all(i.template_id != TRIAL_CARD for i in saved.items)


async def test_spirit_covenant_grants_contracts_1_to_6(tmp_path: Path) -> None:
    """(visto) oficial_20261024-191924-1 #1791-#1801: 115, um 4434 por contrato (150 depois do 3º), 111 e 3."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        covenant = Item(g.user_id, 2031301, pos=0)
        snap.items.append(covenant)
        await g.server.services.characters.save(covenant)
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        got = await g.idle()
        assert [p.code for p in got] == [115, 4434, 4434, 4434, 150, 4434, 4434, 4434, 111, 3]
        kings = [pb.KingContractMsg.FromString(p.body).kingContractInfos for p in got if p.code == 4434]
        assert [[k.contractId for k in m] for m in kings] == [list(range(1, n + 1)) for n in range(1, 7)]
        [end] = {datetime.fromisoformat(k.endData).replace(tzinfo=UTC) for k in kings[-1]}
        assert abs(end - (_now(g) + timedelta(hours=24))) < timedelta(seconds=3)
        assert pb.ChatChannelMsg.FromString(got[-2].body).encodeMsg == "Spirit Covenant activation successful."
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert all(i.template_id != 2031301 for i in saved.items)


async def test_vip_wheel_opens_18_prizes_and_quick_spins_while_tokens_last(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8521)  # sem VIP: 4414 vazio, o cliente ignora
        assert [pb.VipRouletteMsg.FromString(p.body).leftItem for p in await g.idle()] == [[]]

        snap = _snap(g)
        snap.character.point = 400
        g.client.send(8513, pb.VipOpenInfoMsg(days=31))
        await g.until(4416)
        tokens = Item(g.user_id, vip.VIP_TOKEN, pos=0, count=5)
        snap.items.append(tokens)
        await g.server.services.characters.save(tokens)

        g.client.send(8521)
        wheel = pb.VipRouletteMsg.FromString((await g.until(4414))[-1].body)
        assert (len(wheel.leftItem), wheel.leftCount, wheel.needVipItem) == (18, 8, 1)  # tutorial_en #3325

        g.client.send(8519, pb.VipRouletteMsg(opType=vip.QUICK))  # 5 fichas: giro de 1 + giro de 2 (#3331-#3335)
        got = await g.idle()
        assert got[0].code == 115 and got[-1].code == 4415
        spin = pb.VipRouletteMsg.FromString(got[-1].body)
        assert (len(spin.openIndex), len(spin.takeItem), spin.leftCount, spin.needVipItem) == (2, 2, 6, 3)
        assert spin.isStart and spin.opType == vip.QUICK
        assert sum(i.count for i in snap.items if i.template_id == vip.VIP_TOKEN) == 2

        g.client.send(8519, pb.VipRouletteMsg())  # 2 fichas, o terceiro custa 3
        assert pb.VipRouletteMsg.FromString((await g.until(4415))[-1].body).isStart is False
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert sum(i.count for i in saved.items if i.template_id == vip.VIP_TOKEN) == 2
