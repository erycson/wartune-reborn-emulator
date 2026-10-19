import sqlite3
from pathlib import Path

from tests.game.harness import logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item
from wartune_server.protocol.messages import wartune_pb2 as pb

WAND = 1013002  # Saray Rahibi Değneği: arma de mago (SonType 101, espaço 0), SellGold 150
GOLD_BOX = 2030101  # Altın Kutusu: SonType 203, Property1 1 (ouro), Property2 1000
EXP_BOOK = 2030701  # Küçük EXP Kitabı: EXP+500
GEM_BOX = 2060008  # Değerli Taş Kutusu Lv.1
SMALL_HP = 2090101  # Küçük HP Paketi: SonType 209, +10000 HP


async def test_bag_move_checks_the_hero_slot(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        wand = Item(g.user_id, WAND, pos=0)
        snap.items.append(wand)
        await g.server.services.characters.save(wand)
        hero = snap.leader.id  # type: ignore[union-attr]

        for bad in (
            pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=4, endObjId=hero, endPos=2),  # espaço da armadura
            pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=4, endObjId=hero + 99, endPos=0),  # herói alheio
            pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=9, endPos=0),  # bolsa que não existe
            pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=1, endPos=500),  # fora da mochila
        ):
            g.client.send(5005, bad)
        assert await g.idle() == []

        g.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=0, endPos=0))  # para a bancada
        assert codes(await g.until(115) + await g.until(115)) == [3, 150, 115, 115]
        assert (wand.bag_type, wand.pos) == (0, 0)
        g.client.send(5005, pb.ItemReqMsg(beginBagType=0, beginPos=0, endBagType=1, endPos=0))  # e de volta
        await g.until(115)
        await g.until(115)
        assert (wand.bag_type, wand.pos) == (1, 0)


async def test_using_resources_potions_and_gem_boxes(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        c, gold, gp = snap.character, snap.character.gold, snap.character.total_gp
        items = [Item(g.user_id, t, pos=p, count=n) for p, (t, n) in enumerate([(GOLD_BOX, 3), (EXP_BOOK, 1)])]
        items += [Item(g.user_id, GEM_BOX, pos=2, count=2), Item(g.user_id, SMALL_HP, pos=3)]
        snap.items.extend(items)
        await g.server.services.characters.save(*items)

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=2, bagType=1))
        got = await g.until(109)
        assert codes(got) == [115, 111, 109]
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg == "Received: 2,000 Gold"
        assert (c.gold, items[0].count) == (gold + 2000, 1)

        g.client.send(5006, pb.ItemUseMsg(pos=1, count=1, bagType=1))
        got = await g.until(83)
        assert codes(got)[:4] == [115, 111, 3, 83] and c.total_gp == gp + 500
        assert not pb.ItemMovedListMsg.FromString(got[0].body).moved[0].HasField("item")  # o livro acabou

        g.client.send(5006, pb.ItemUseMsg(pos=2, count=2, bagType=1))
        got = await g.until(83)
        assert codes(got) == [115, 115, 111, 3, 83]
        stones = [i for i in snap.items if 2050101 <= i.template_id <= 2050801 and i.template_id % 100 == 1]
        assert sum(i.count for i in stones) == 2 and all(i.template_id != GEM_BOX for i in snap.items)

        c.grades = 11  # a poção pede nível 11
        g.client.send(5006, pb.ItemUseMsg(pos=3, count=1, bagType=1))
        got = await g.until(3)
        assert codes(got) == [115, 113, 150, 3] and snap.leader.blood == 10000  # type: ignore[union-attr]

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.gold == gold + 2000 and saved.leader.blood == 10000  # type: ignore[union-attr]


async def test_sell_lock_and_buy_bag_rows(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        c = snap.character
        c.point, c.gift_token, gold = 25, 0, c.gold
        wand, other = Item(g.user_id, WAND, pos=0), Item(g.user_id, WAND, pos=1, strengthen_grade=1)
        snap.items.extend([wand, other])
        await g.server.services.characters.save(c, wand, other)

        g.client.send(8809, pb.LockAndUnlockMsg(opType=1, itemPos=0))
        await g.until(115)
        g.client.send(5007, pb.ItemReqMsg(beginPos=0))  # travado: não vende
        assert await g.idle() == []
        g.client.send(8624, pb.ItemSellReqMsg(selledItemInfos=[pb.SelledItemInfo(pos=1, count=1)]))
        assert codes(await g.until(109)) == [115, 109]
        # 150 + 70% de (1.5^1 * 3 * 1 * 5 + 500)
        assert c.gold == gold + int(150 + 0.7 * (1.5 * 3 * 5 + 500)) and other not in snap.items

        g.client.send(5010, pb.PayTypeMsg(payType=1, property1=2))  # 10 + 20 elmas: só tem 25
        assert await g.idle() == []
        g.client.send(5010, pb.PayTypeMsg(payType=1, property1=1))
        assert pb.PlayerMsg.FromString((await g.until(3))[-1].body).bagCount == 7
        with sqlite3.connect(tmp_path / "game.db") as db:
            assert list(db.execute("SELECT delta_point, reason FROM cash_ledger")) == [(-10, "bag")]


async def test_arrange_moves_and_stacks(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        a, b, w = (
            Item(g.user_id, GOLD_BOX, pos=0, count=2),
            Item(g.user_id, GOLD_BOX, pos=5, count=3),
            Item(g.user_id, WAND, pos=3),
        )
        snap.items.extend([a, b, w])
        await g.server.services.characters.save(a, b, w)

        info = [
            pb.ArrangeInfo(oldplace=3, newplace=0),
            pb.ArrangeInfo(oldplace=0, newplace=1),
            pb.ArrangeInfo(oldplace=5, newplace=2),
        ]
        g.client.send(8220, pb.ArrangeReq(isStackItem=True, bagType=1, arrangeInfo=info))
        await g.until(115)
        assert (w.pos, a.pos, a.count) == (0, 1, 5) and b not in snap.items

        g.client.send(8220, pb.ArrangeReq(bagType=1, arrangeInfo=[pb.ArrangeInfo(oldplace=0, newplace=1)]))  # colide
        assert await g.idle() == []
