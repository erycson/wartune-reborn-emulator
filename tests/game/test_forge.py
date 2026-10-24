from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item
from wartune_server.game.handlers import forge
from wartune_server.protocol.messages import wartune_pb2 as pb

WAND = 1013002  # Templar Priest Staff: NeedGrades 1, Profile 2, StrengthenMax 3, sem furos
LUCK_1 = 2040101  # Lvl. 1 Luck Stone: +10% no reforço
DRILL = 208004  # Elmas Delici
ATTACK_1, ATTACK_2, MAGIC_1 = 2050101, 2050102, 2050201  # Lvl. 1/2 Physical Attack Gem e Lvl. 1 Physical Defense Gem
SWORD = 1011003  # Templar Knight Long Sword: refino com 2127001, 3 atributos, Profile 3
CRYSTAL = 2127001  # Lvl. 1 Refinement Crystal


async def put(g: Game, *items: Item) -> None:
    me(g).items.extend(items)
    await g.server.services.characters.save(*items)


async def test_strengthen_success_and_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold = 2000
        wand, luck = Item(g.user_id, WAND, bag_type=0, pos=0), Item(g.user_id, LUCK_1, bag_type=0, pos=1, count=2)
        await put(g, wand, luck)

        monkeypatch.setattr(forge.random, "randint", lambda a, b: 1)
        g.client.send(5150)
        got = await g.until(86)
        assert codes(got) == [109, 109, 115, 115, 86]  # oficial_encantar #219-#223 (com pedra)
        rsp = pb.StoreRspMsg.FromString(got[-1].body)
        assert (
            got[-1].body
            == pb.StoreRspMsg(strengResult=True, strengthenGrade=1, pos=0, objectId=0, bagType=0).SerializeToString()
        )
        assert (rsp.strengResult, rsp.strengthenGrade, wand.strengthen_grade, luck.count) == (True, 1, 1, 1)
        assert c.gold == 2000 - 522  # 1.5^1 * (2+1) * 1^2.2 * 5 + 500

        monkeypatch.setattr(forge.random, "randint", lambda a, b: 101)  # 90% + 10% da pedra: só passa até 100
        g.client.send(5150)
        got = await g.until(86)
        assert codes(got) == [109, 109, 115, 86]  # turco "atölye item basma ve mozaik" #9-#12
        assert got[-1].body == pb.StoreRspMsg(strengResult=False).SerializeToString()
        assert wand.strengthen_grade == 1 and luck not in me(g).items  # a pedra vai mesmo na falha

        c.gold = 0
        g.client.send(5150)  # sem ouro
        assert await g.idle() == []

        # helpContent01: "Enchantment will cause any unbound items to become bound" (mesmo na falha)
        c.gold, wand.is_binds = 2000, False
        g.client.send(5150)
        got = await g.until(86)
        assert codes(got) == [109, 109, 115, 86] and wand.is_binds and wand.strengthen_grade == 1
        assert pb.ItemMovedListMsg.FromString(got[2].body).moved[0].item.bind


async def test_drill_inlay_and_remove(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold = 1000
        wand = Item(g.user_id, WAND, bag_type=0, pos=0, is_binds=False)
        drills, a1, a2 = (
            Item(g.user_id, DRILL, pos=0, count=2),
            Item(g.user_id, ATTACK_1, pos=1),
            Item(g.user_id, ATTACK_2, pos=2),
        )
        await put(g, wand, drills, a1, a2)

        g.client.send(5151, pb.StoreReqMsg(mountPos=1, bagType=1, bagPos=1))  # furo fechado
        assert await g.idle() == []
        for hole in (1, 2):
            g.client.send(5152, pb.StoreReqMsg(holePos=hole, operate=True))
            await g.until(115)
            await g.until(115)
        assert wand.joins == [0, 0, -1, -1] and drills not in me(g).items and not wand.is_binds

        g.client.send(5151, pb.StoreReqMsg(mountPos=1, bagType=1, bagPos=1))
        got = await g.until(83)
        # (visto) 231733 #1392: furo vazio, sem 109
        assert codes(got) == [115, 115, 111, 83] and wand.join_1 == ATTACK_1
        assert wand.is_binds  # helpContent02: "Socketing will cause unbound items to become bound"
        g.client.send(5151, pb.StoreReqMsg(mountPos=2, bagType=1, bagPos=2))  # mesmo atributo (Physical Attack)
        assert await g.idle() == []

        g.client.send(5152, pb.StoreReqMsg(holePos=1, operate=False))  # tirar custa 200 (Property3)
        got = await g.until(83)
        assert codes(got) == [109, 115, 115, 4476] + [4484] * 9 + [111, 83] and wand.join_1 == 0 and c.gold == 800
        assert (
            pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg
            == "Unsocketing successful! Received: Lvl. 1 Physical Attack Gem x1!"
        )
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert sorted(i.template_id for i in saved.items if i.bag_type == 1) == [ATTACK_1, ATTACK_2]


async def test_compose_and_transform(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold, c.grades = 50000, 20
        await put(
            g,
            Item(g.user_id, 2129001, pos=0, count=6),
            Item(g.user_id, 2128101, pos=1),
            Item(g.user_id, ATTACK_1, pos=2, count=3),
        )

        g.client.send(5153, pb.StoreReqMsg(composeId=1, composeNum=1))
        got = await g.until(83)
        assert codes(got) == [115, 109, 109, 115, 4476] + [4484] * 9 + [111, 89, 83] and c.gold == 40000
        assert pb.ChatChannelMsg.FromString(got[14].body).encodeMsg == "Received: Gartan Sword x1"
        assert {(i.template_id, i.count) for i in me(g).items if i.bag_type == 1} >= {(2129001, 1), (1991011, 1)}
        g.client.send(5153, pb.StoreReqMsg(composeId=1, composeNum=1))  # falta material
        assert await g.idle() == []

        g.client.send(8538, pb.StoreReqMsg(srcItemid=ATTACK_1, desItemid=MAGIC_1, count=2))
        got = await g.until(83)
        assert codes(got) == [115, 109, 115, 4476] + [4484] * 9 + [111, 83] and c.gold == 20000
        assert {(i.template_id, i.count) for i in me(g).items} >= {(ATTACK_1, 1), (MAGIC_1, 2)}
        g.client.send(8538, pb.StoreReqMsg(srcItemid=ATTACK_1, desItemid=ATTACK_2, count=1))  # nível diferente
        assert await g.idle() == []


async def test_refine_needs_replace_to_apply(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.point, c.gift_token = 45, 0
        sword = Item(g.user_id, SWORD, bag_type=0, pos=0, random_skill=70302, random_skill_2=70407, is_binds=False)
        free, bound = Item(g.user_id, CRYSTAL, pos=0, count=3, is_binds=False), Item(g.user_id, CRYSTAL, pos=1, count=2)
        await put(g, sword, free, bound)

        # Profile 3 = 4 pedras (RefreshView.updateMateMaterial); bindType 2 = só as livres: 3 não bastam
        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, False, False], bindType=2, payType=1))
        assert await g.idle() == []
        free.count = 4
        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, True, False], bindType=2, payType=1))  # travar todos
        assert await g.idle() == []

        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, False, False], bindType=2, payType=1))
        got = await g.until(4258)
        skills = list(pb.SmithFreshRspMsg.FromString(got[-1].body).randomSkill)
        assert codes(got) == [115, 3, 4258] and len(skills) == 3 and skills[0] == 70302
        assert sword.random_skills == [70302, 70407, 0, 0, 0]  # ainda não trocou
        assert free not in me(g).items and bound.count == 2 and not sword.is_binds
        assert c.point == 0  # o cadeado sem Refinement Lock custa 45 Balens
        assert 4152 in codes(await g.idle())  # gasto de Balens (leed), depois da resposta

        g.client.send(8339)
        got = await g.until(115)
        assert pb.SmithFreshReplaceRspMsg.FromString(got[0].body).result and sword.random_skills[:3] == skills
        g.client.send(8339)  # nada pendente
        assert not pb.SmithFreshReplaceRspMsg.FromString((await g.until(4259))[-1].body).result

        # bindType 0: as vinculadas primeiro, e o equipamento livre fica vinculado; o cadeado gasta o 208027
        lock, more = Item(g.user_id, forge.LOCK_ITEM, pos=2), Item(g.user_id, CRYSTAL, pos=3, count=2, is_binds=False)
        await put(g, lock, more)
        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, False, False], bindType=0, payType=0))
        await g.until(4258)
        assert bound not in me(g).items and more not in me(g).items and lock not in me(g).items
        assert sword.is_binds and c.point == 0


async def test_resolve_turns_equipment_into_refinement_crystals(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold = 2999
        free = Item(g.user_id, SWORD, bag_type=0, pos=0, is_binds=False)
        bound = Item(g.user_id, SWORD, bag_type=0, pos=1)
        wand = Item(g.user_id, WAND, bag_type=0, pos=5, join_1=ATTACK_1)  # Profile 2, Refresh 0
        await put(g, free, bound, wand)

        g.client.send(8340)  # isResolePoint: equipamento com pedra não entra
        assert await g.idle() == []  # recusa calada: o ResolveView limpa a bancada com qualquer 4260
        wand.join_1 = 0
        g.client.send(8340)  # 3 equipamentos = 3.000 de ouro (ResolveView)
        assert await g.idle() == []

        c.gold = 3000
        g.client.send(8340)
        got = await g.until(4260)
        assert codes(got) == [115, 109, 4260] and pb.SmithResolveRspMsg.FromString(got[-1].body).result
        assert c.gold == 0 and not [i for i in me(g).items if i.bag_type == 0]
        # Profile 3 = 4 pedras (mateMaterial), separadas pelo vínculo do equipamento (helpContent05)
        crystals = sorted((i.is_binds, i.count) for i in me(g).items if i.template_id == CRYSTAL)
        assert crystals == [(False, 4), (True, 4)]
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert sorted((i.is_binds, i.count) for i in saved.items if i.template_id == CRYSTAL) == crystals
        assert not [i for i in saved.items if i.template_id in (SWORD, WAND)]

        g.client.send(8340)  # bancada vazia
        assert await g.idle() == []


async def test_avanco_do_heroi_herda_reforco_furos_e_atributos(tmp_path: Path) -> None:
    """5153 com receita Types 5 (108: Wyvern Sword -> [Legend]): a peça equipada vai primeiro, é a mesma linha com o
    template novo, mantém reforço, pedras e atributos; o 89 vai com ``composeResult`` true."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        c, leader = snap.character, snap.leader
        assert leader is not None
        c.gold, c.grades = 800_000, 60
        sword = Item(g.user_id, 1991081, bag_type=4, object_id=leader.id or 0, pos=0, strengthen_grade=7)
        sword.joins, sword.random_skills = [ATTACK_1, 0, -1, -1], [70302, 0, 0, 0, 0]
        await put(g, sword, Item(g.user_id, 2129600, pos=0, count=150), Item(g.user_id, 2129601, pos=1, count=15))
        await g.idle()

        g.client.send(5153, pb.StoreReqMsg(composeId=108, composeNum=1, payType=1))
        got = await g.until(89)
        assert pb.StoreRspMsg.FromString(got[-1].body).composeResult
        assert (sword.template_id, sword.strengthen_grade, sword.joins, sword.random_skill) == (
            1891081,
            7,
            [ATTACK_1, 0, -1, -1],
            70302,
        )
        assert (sword.bag_type, c.gold, [i.template_id for i in snap.items if i.bag_type == 1]) == (4, 100_000, [])
        g.client.send(5153, pb.StoreReqMsg(composeId=108, composeNum=1, payType=1))  # a peça já avançou
        assert await g.idle() == []


async def test_avanco_do_mascote_exige_encantamento_maximo_e_paga_o_que_falta(tmp_path: Path) -> None:
    """Receita Types 10 (344: Empress Guard -> Infernal Roar): a peça da bancada com ``mouldGrade`` no máximo; o
    material que falta sai em Balens (Point 80 da loja); o encantamento volta a 0."""
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold, c.point = 10_000, 60 * 80
        guard = Item(g.user_id, 1130301, bag_type=0, pos=0, mould_grade=9, bless_value=30)
        shards = Item(g.user_id, 3240101, pos=0, count=40)
        await put(g, guard, shards)
        await g.idle()

        g.client.send(5153, pb.StoreReqMsg(composeId=344, composeNum=1, payType=1))  # encantamento 9 de 10
        assert await g.idle() == []
        guard.mould_grade = 10
        g.client.send(5153, pb.StoreReqMsg(composeId=344, composeNum=1, payType=1))
        got = await g.until(89)
        assert pb.StoreRspMsg.FromString(got[-1].body).composeResult
        assert (guard.template_id, guard.mould_grade, guard.bless_value, guard.bag_type) == (1130401, 0, 0, 0)
        assert (c.gold, c.point, shards in me(g).items) == (0, 0, False)


async def test_furo_alma_e_refino_do_equipamento_de_mascote(tmp_path: Path) -> None:
    """Empress Guard (Profile 3, 1 furo aberto): furo com a Soul Socketing Rod só abaixo do Profile; só Divinity Soul
    (329) e sem repetir o atributo; refino com 4 Golden Holy Water, as que faltam em Balens (Point 80)."""
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.point = 3 * 80
        guard = Item(g.user_id, 1130301, bag_type=0, pos=0)
        guard.joins = [0, -1, -1, -1]
        rod = Item(g.user_id, 3280101, pos=0, count=2)
        souls = Item(g.user_id, 3290101, pos=1, count=1), Item(g.user_id, 3290102, pos=2, count=1)
        gem, water = Item(g.user_id, ATTACK_1, pos=3), Item(g.user_id, 3270101, pos=4, count=1)
        await put(g, guard, rod, *souls, gem, water)
        await g.idle()

        g.client.send(5152, pb.StoreReqMsg(holePos=3, operate=True))  # 3 não é < Profile 3
        g.client.send(5151, pb.StoreReqMsg(mountPos=1, bagType=1, bagPos=3))  # pedra do herói
        assert await g.idle() == []
        g.client.send(5152, pb.StoreReqMsg(holePos=2, operate=True))
        await g.idle()
        assert (guard.joins, rod.count) == ([0, 0, -1, -1], 1)

        g.client.send(5151, pb.StoreReqMsg(mountPos=1, bagType=1, bagPos=1))
        await g.idle()
        g.client.send(5151, pb.StoreReqMsg(mountPos=2, bagType=1, bagPos=2))  # mesmo atributo (PATK)
        await g.idle()
        assert guard.joins == [3290101, 0, -1, -1]

        g.client.send(8336, pb.SmithFreshReqMsg(lock=[False, False, False], bindType=0, payType=1))
        got = await g.until(4258)
        assert len(pb.SmithFreshRspMsg.FromString(got[-1].body).randomSkill) == 3
        assert (water in me(g).items, c.point) == (False, 0)
