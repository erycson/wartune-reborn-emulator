import sqlite3
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.protocol.messages import wartune_pb2 as pb

HORN = 35  # ShopTempInfo 35: Büyük Borazan (208002), 50 Bağlı Elmas
SMALL_HP = 32  # ShopType 100: Küçük HP Paketi (2090101), 5000 Altın, +10000 HP


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
        c = me(g).character
        c.gift_token, c.point = 150, 0
        await g.server.services.characters.save(c)

        g.client.send(5154, buy(HORN, 2))
        got = await g.until(90)
        assert codes(got) == [3, 115, 111, 83, 90]
        assert pb.ShopMsg.FromString(got[-1].body).buyInfo.result == 1
        item = pb.ItemMovedListMsg.FromString(got[1].body).moved[0].item
        assert (item.templateId, item.count) == (208002, 2)
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg.endswith("x2 başarıyla alındı!")
        assert ledger(tmp_path) == [(0, -100, 0, 50, "shop", "good:35 x2")]

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
        c.gold, c.gift_token, c.point = 10**7, 1000, 1000
        await g.server.services.characters.save(c)

        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))
        listed = pb.ShopFreshRspMsg.FromString((await g.until(4384))[-1].body)
        assert listed.itemId and all(listed.isCanBuy) and listed.maxBuyCount == 20

        g.client.send(8482, pb.ShopItemBuyMsg(itemId=listed.itemId[0], index=0, payType=0))
        got = await g.until(4384)
        assert pb.ShopItemBuyRspMsg.FromString(got[-2].body).result == 1
        assert list(pb.ShopFreshRspMsg.FromString(got[-1].body).isCanBuy)[0] == 0

        g.client.send(8482, pb.ShopItemBuyMsg(itemId=listed.itemId[0], index=0, payType=0))  # de novo: recusado
        assert pb.ShopItemBuyRspMsg.FromString((await g.until(4383))[-1].body).result == 8
