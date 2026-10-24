import sqlite3
from pathlib import Path

from tests.game.harness import logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item, Pawn
from wartune_server.game import rules
from wartune_server.protocol.messages import wartune_pb2 as pb

WAND = 1013002  # Templar Priest Staff: arma de mago (SonType 101, espaço 0), SellGold 150
GOLD_BOX = 2030101  # Gold Chest: SonType 203, Property1 1 (ouro), Property2 1000
EXP_BOOK = 2030701  # Lvl. 1 EXP Book: EXP+500
HONOR_CERT = 2030601  # Lvl. 1 Honor Certificate: honra (geste) +500
GEM_BOX = 2060008  # Lvl. 1 Gem Pack
SMALL_HP = 2090101  # Minor HP Pack: SonType 209, +10000 HP
LANCER = 10101


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
        assert codes(await g.until(115) + await g.until(115)) == [115, 115]  # (visto) oficial_encantar #215
        assert (wand.bag_type, wand.pos) == (0, 0)
        g.client.send(5005, pb.ItemReqMsg(beginBagType=0, beginPos=0, endBagType=1, endPos=0))  # e de volta
        await g.until(115)
        await g.until(115)
        assert (wand.bag_type, wand.pos) == (1, 0)


async def test_equipment_from_the_hero_goes_back_to_the_hero_when_it_leaves_the_bench(tmp_path: Path) -> None:
    """(visto) tutorial_en #3202/#3217: o cajado do herói vai para a bancada (3, 150, 115 do herói, 115 da bancada) e o
    ``endBagType`` 1 da volta o veste de novo, com o 115 do herói antes do da bancada."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        leader = snap.leader
        assert leader is not None
        wand = Item(g.user_id, WAND, bag_type=4, object_id=leader.id or 0, pos=0)
        snap.items.append(wand)
        await g.server.services.characters.save(wand)

        g.client.send(5005, pb.ItemReqMsg(beginBagType=4, beginObjId=leader.id, beginPos=0, endBagType=0, endPos=0))
        got = await g.until(115) + await g.until(115)
        assert [c for c in codes(got) if c != 113] == [3, 150, 115, 115] and wand.bag_type == 0
        g.client.send(5005, pb.ItemReqMsg(beginBagType=0, beginPos=0, endBagType=1, endPos=0))
        got = await g.until(115) + await g.until(115)
        assert (wand.bag_type, wand.object_id, wand.pos) == (4, leader.id, 0)
        first, second = (pb.ItemMovedListMsg.FromString(p.body).moved[0] for p in got if p.code == 115)
        assert (first.changeType, first.item.templateId, second.changeType, second.HasField("item")) == (
            4,
            WAND,
            0,
            False,
        )


async def test_using_resources_potions_and_gem_boxes(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        c, gold, gp = snap.character, snap.character.gold, snap.character.total_gp
        items = [Item(g.user_id, t, pos=p, count=n) for p, (t, n) in enumerate([(GOLD_BOX, 3), (EXP_BOOK, 1)])]
        items += [Item(g.user_id, GEM_BOX, pos=2, count=2), Item(g.user_id, SMALL_HP, pos=3)]
        snap.items.extend(items)
        await g.server.services.characters.save(*items)

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=2, bagType=1))
        got = await g.until(3)
        assert codes(got) == [115, 109, 111, 3]  # (visto) 153200 #2188-#2192
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Received:Gold x2000"
        assert (c.gold, items[0].count) == (gold + 2000, 1)

        g.client.send(5006, pb.ItemUseMsg(pos=1, count=1, bagType=1))
        got = await g.until(83)
        assert codes(got)[:4] == [115, 111, 3, 83] and c.total_gp == gp + 500

        honor = Item(g.user_id, HONOR_CERT, pos=10)
        snap.items.append(honor)
        await g.server.services.characters.save(honor)
        g.client.send(5006, pb.ItemUseMsg(pos=10, count=1, bagType=1))
        got = await g.until(3)
        assert pb.PlayerMsg.FromString(got[-1].body).geste == c.geste == 500 and c.repute == 0
        assert not pb.ItemMovedListMsg.FromString(got[0].body).moved[0].HasField("item")  # o livro acabou

        g.client.send(5006, pb.ItemUseMsg(pos=2, count=2, bagType=1))
        got = await g.until(83)
        assert codes(got) == [115, 115, 4476, *[4484] * 9, 111, 3, 83]  # (só turco: lvl1_degerli_tas_sandigi)
        stones = [i for i in snap.items if 2050101 <= i.template_id <= 2050801 and i.template_id % 100 == 1]
        assert sum(i.count for i in stones) == 2 and all(i.template_id != GEM_BOX for i in snap.items)

        c.grades = 11  # a poção pede nível 11
        assert snap.leader is not None
        snap.leader.hp = 100  # ferido: a reserva nova já cura
        g.client.send(5006, pb.ItemUseMsg(pos=3, count=1, bagType=1))
        got = await g.until(83)
        assert codes(got) == [115, 113, 150, 3, 83]  # oficial_20261023-171155-1 #7589-#7593
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Used HP pack to restore HP."
        blood = snap.leader.blood
        assert 0 < blood < 10000 and snap.leader.hp > 100

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.gold == gold + 2000 and saved.leader.blood == blood  # type: ignore[union-attr]


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
        got = await g.until(111)
        assert codes(got) == [115, 109, 111]  # 231733 #224-#229
        # 150 + 70% de (1.5^1 * 3 * 1 * 5 + 500)
        assert c.gold == gold + int(150 + 0.7 * (1.5 * 3 * 5 + 500)) and other not in snap.items
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Sale successful! You have received 515 gold."

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


async def test_equipping_and_stacking_bind_the_item(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        hero = snap.leader.id  # type: ignore[union-attr]
        wand = Item(g.user_id, WAND, pos=0, is_binds=False)
        free, bound = Item(g.user_id, GOLD_BOX, pos=1, count=2, is_binds=False), Item(g.user_id, GOLD_BOX, pos=2)
        loose_a, loose_b = Item(g.user_id, GEM_BOX, pos=3, is_binds=False), Item(g.user_id, GEM_BOX, pos=4)
        snap.items.extend([wand, free, bound, loose_a, loose_b])
        await g.server.services.characters.save(wand, free, bound, loose_a, loose_b)

        # (cliente) PlayerBagCellClickMediator: equipar item livre pede "...will change this item to become bound"
        g.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=4, endObjId=hero, endPos=0))
        got = await g.idle()
        assert wand.bag_type == 4 and wand.is_binds
        moved = [m.item for p in got if p.code == 115 for m in pb.ItemMovedListMsg.FromString(p.body).moved]
        assert [m.bind for m in moved if m.templateId == WAND] == [True]

        # GoodsCheck.isAddToChecker: juntar livre com vinculado vincula a pilha
        g.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=1, endBagType=1, endPos=2))
        await g.idle()
        assert free not in snap.items and (bound.count, bound.is_binds) == (3, True)

        # arrumar não junta livre com vinculado
        info = [pb.ArrangeInfo(oldplace=3, newplace=0), pb.ArrangeInfo(oldplace=4, newplace=1)]
        g.client.send(8220, pb.ArrangeReq(isStackItem=True, bagType=1, arrangeInfo=info))
        await g.idle()
        assert loose_a in snap.items and loose_b in snap.items

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert [(i.bag_type, i.is_binds) for i in saved.items if i.template_id == WAND] == [(4, True)]


async def test_unequipping_lowers_hp_and_sends_extra_troops_home(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #2310-#2316: o cajado com Captain +6 e Physique +6 (70406, 70506) saiu; 113
    com a vida no máximo novo, 100 com 6 soldados de volta ao castelo (exército 218 -> 212), 3, 150, 115, 115."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        leader = snap.leader
        assert leader is not None
        wand = Item(g.user_id, WAND, bag_type=4, object_id=leader.id or 0, pos=0)
        wand.random_skills = [70406, 70506]
        snap.items.append(wand)
        now = g.server.services.clock.now()
        stats = rules.leader_stats(snap, g.server.services.templates, now).total
        for other in snap.pawns:
            other.army_count = 0
        pawn = next((p for p in snap.pawns if p.template_id == LANCER), None) or Pawn(snap.character.id or 0, LANCER)
        pawn.castle_count, pawn.army_count = 100, stats["ConatArmy"]
        if pawn not in snap.pawns:
            snap.pawns.append(pawn)
        leader.hp = 0  # cheia
        blood = leader.blood
        await g.server.services.characters.save(wand, *snap.pawns, leader)

        g.client.send(5005, pb.ItemReqMsg(beginBagType=4, beginObjId=leader.id, beginPos=0, endBagType=1, endPos=0))
        got = await g.until(115) + await g.until(115)
        assert codes(got) == [113, 100, 3, 150, 115, 115]
        live = rules.leader_stats(snap, g.server.services.templates, now).total["Live"]
        assert live == stats["Live"] - 120 and pb.SimpleHeroInfoMsg.FromString(got[0].body).hp == live
        # (visto) 231733 #233/#300: os 120 que passaram do máximo voltam para a reserva
        assert pb.SimpleHeroInfoMsg.FromString(got[0].body).blood == leader.blood == blood + 120
        assert (pawn.army_count, pawn.castle_count) == (stats["ConatArmy"] - 6, 106)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert [(p.army_count, p.castle_count) for p in saved.pawns if p.template_id == LANCER] == [
            (stats["ConatArmy"] - 6, 106)
        ]
