import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

HORN = 602  # ShopTempInfo 602 (ShopType 1): Bullhorn (Large) (208002), 195 vinculado (GiftToken)
SMALL_HP = 32  # ShopType 100: Minor HP Pack (2090101), 5000 de ouro, +10000 HP


def codes(got: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in got]


def me(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def ledger(tmp_path: Path) -> list[tuple[int, int, int, int, str, str]]:
    with sqlite3.connect(tmp_path / "game.db") as db:
        sql = "SELECT delta_point, delta_gift_token, balance_point, balance_gift_token, reason, ref FROM cash_ledger"
        return list(db.execute(sql))


def buy(good: int, count: int, pay_type: int = 0) -> pb.ShopMsg:
    msg = pb.ShopMsg(payType=pay_type)
    msg.buyInfo.goodId, msg.buyInfo.count = good, count
    return msg


async def test_buy_with_gift_token_writes_the_ledger(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        unit = int(next(g.server.services.templates.find("ShopTempInfos", Id=HORN))["GiftToken"])
        c = me(g).character
        c.gift_token, c.point = 2 * unit + 50, 0  # duas unidades e sobram 50
        await g.server.services.characters.save(c)

        g.client.send(5154, buy(HORN, 2))
        got = await g.until(90)
        assert codes(got) == [3, 115, 111, 83, 90]
        assert codes(await g.until(83)) == [4152, 83]  # leed 15 (gasto de vinculado), depois da resposta
        assert pb.ShopMsg.FromString(got[-1].body).buyInfo.result == 1
        item = pb.ItemMovedListMsg.FromString(got[1].body).moved[0].item
        assert (item.templateId, item.count) == (208002, 2)
        assert not item.HasField("attack")  # 115 sem complete(): o oficial omite os atributos do item
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg.endswith("x2 purchased successfully!")
        assert ledger(tmp_path) == [(0, -2 * unit, 0, 50, "shop", f"good:{HORN} x2")]

        g.client.send(5154, buy(HORN, 2))  # só sobram 50: falta dinheiro, nada muda
        got = await g.until(90)
        assert codes(got) == [90] and pb.ShopMsg.FromString(got[0].body).buyInfo.result == 4
        g.client.send(5154, buy(HORN, 1, pay_type=1))  # payType 1 = só elmas
        assert pb.ShopMsg.FromString((await g.until(90))[-1].body).buyInfo.result == 4
        g.client.send(5154, buy(999999, 1))
        assert pb.ShopMsg.FromString((await g.until(90))[-1].body).buyInfo.result == 8

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.gift_token == 50 and len(ledger(tmp_path)) == 1
        assert [(i.template_id, i.count) for i in saved.items if i.bag_type == 1] == [(208002, 2)]

        g.client.send(8218)
        has = pb.ShopMsg.FromString((await g.until(4145))[-1].body).hasDataInfo
        assert [(h.itemId, h.counts) for h in has] == [(HORN, 2)]


async def test_fast_blood_buys_and_fills_the_reserve(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold = 6000
        await g.server.services.characters.save(c)

        g.client.send(5633, buy(SMALL_HP, 1))
        got = await g.until(170)
        assert codes(got) == [109, 113, 170]
        assert pb.SimpleHeroInfoMsg.FromString(got[1].body).blood == 10000
        assert pb.FastUseBloodMsg.FromString(got[-1].body).result == 1

        g.client.send(5633, buy(SMALL_HP, 1))  # 1000 de ouro não paga
        got = await g.until(170)
        assert codes(got) == [170] and pb.FastUseBloodMsg.FromString(got[0].body).result == 4
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert (saved.character.gold, saved.leader.blood) == (1000, 10000)  # type: ignore[union-attr]


async def test_mystery_shop_lists_and_sells_once(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold, c.gift_token, c.point, c.grades = 10**7, 10**6, 10**6, 25
        await g.server.services.characters.save(c)
        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))  # MysteryShopView: abre no nível 26
        assert await g.idle() == []
        c.grades = 26

        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))
        listed = pb.ShopFreshRspMsg.FromString((await g.until(4384))[-1].body)
        # 6 itens (MAX_GOODS_NUM); isCanBuy 0 = à venda (BuyGoodsItem)
        assert len(listed.itemId) == 6 and not any(listed.isCanBuy) and listed.maxBuyCount == 20

        g.client.send(8482, pb.ShopItemBuyMsg(itemId=listed.itemId[0], index=0, payType=0))
        got = await g.until(4384)
        assert pb.ShopItemBuyRspMsg.FromString(got[-2].body).result == 1
        assert list(pb.ShopFreshRspMsg.FromString(got[-1].body).isCanBuy)[0] == 1

        g.client.send(8482, pb.ShopItemBuyMsg(itemId=listed.itemId[0], index=0, payType=0))  # de novo: recusado
        assert pb.ShopItemBuyRspMsg.FromString((await g.until(4383))[-1].body).result == 8


async def test_mystery_shop_goods_renew_after_4_hours_and_buys_on_the_next_day(tmp_path: Path) -> None:
    """Itens: 14400 s depois do ``freshLastdate`` (MysteryShopModel.remainTime). Compras do dia: virada das 5h."""
    clock = FakeClock(datetime(2026, 1, 1, 9, tzinfo=UTC))  # 09:00 (fuso dos testes: UTC)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        c = me(g).character
        c.gold, c.gift_token, c.point, c.grades = 10**7, 10**6, 10**6, 30
        await g.server.services.characters.save(c)
        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))
        first = pb.ShopFreshRspMsg.FromString((await g.until(4384))[-1].body)
        g.client.send(8482, pb.ShopItemBuyMsg(itemId=first.itemId[0], index=0, payType=0))
        await g.until(4384)

        clock.advance(4 * 3600 - 1)
        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))
        same = pb.ShopFreshRspMsg.FromString((await g.until(4384))[-1].body)
        assert (same.freshLastdate, same.isCanBuy[0], same.buyCount) == (first.freshLastdate, 1, 1)

        clock.advance(1)  # 4 h: itens novos, todos à venda; a compra do dia continua contada
        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))
        renewed = pb.ShopFreshRspMsg.FromString((await g.until(4384))[-1].body)
        assert renewed.freshLastdate != first.freshLastdate and not any(renewed.isCanBuy) and renewed.buyCount == 1

        clock.advance(17 * 3600)  # 06:00 do dia 2: outro dia do jogo
        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))
        assert pb.ShopFreshRspMsg.FromString((await g.until(4384))[-1].body).buyCount == 0


LUCK_POINT, LUCK_GIFT = 90, 625  # Lvl. 3 Luck Stone (2040103): 35 Balens ou 35 Balens vinculados


async def test_balens_buys_unbound_and_other_currencies_bound(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.point, c.gift_token = 1000, 1000
        await g.server.services.characters.save(c)

        g.client.send(5154, buy(LUCK_POINT, 2, pay_type=1))
        got = await g.until(90)
        item = pb.ItemMovedListMsg.FromString(next(p.body for p in got if p.code == 115)).moved[0].item
        assert (item.templateId, item.count, item.bind) == (2040103, 2, False)  # Balens: livre (vai ao leilão)

        g.client.send(5154, buy(LUCK_GIFT, 1))  # Balens vinculados: vinculado, não entra na pilha livre
        await g.until(90)
        g.client.send(5154, buy(LUCK_POINT, 1, pay_type=1))  # e o livre completa a pilha livre
        await g.until(90)
        stacks = sorted((i.is_binds, i.count) for i in me(g).items if i.template_id == 2040103)
        assert stacks == [(False, 3), (True, 1)]
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert sorted((i.is_binds, i.count) for i in saved.items if i.template_id == 2040103) == stacks


async def test_mystery_points_exchange_is_not_sold_for_bound_balens(tmp_path: Path) -> None:
    """ShopType 7 (troca por pontos da misteriosa): a linha 681 tem GiftToken, mas cobra o Score também."""
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gift_token = 7000
        g.client.send(5154, buy(681, 1))
        assert pb.ShopMsg.FromString((await g.until(90))[-1].body).buyInfo.result != 1
        assert c.gift_token == 7000 and ledger(tmp_path) == []
