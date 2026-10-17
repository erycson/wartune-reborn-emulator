from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item
from wartune_server.game.handlers import forge
from wartune_server.protocol.messages import wartune_pb2 as pb

WAND = 1013002  # Saray Rahibi Değneği: NeedGrades 1, Profile 2, StrengthenMax 3, sem furos
LUCK_1 = 2040101  # Şans Taşı Lv.1: +10% no reforço
DRILL = 208004  # Elmas Delici
ATTACK_1, ATTACK_2, MAGIC_1 = 2050101, 2050102, 2050201  # Saldırı Taşı Lv.1/2 e outra pedra Lv.1
SWORD = 1011003  # Saray Süvarisi Kılıcı: refino com 2127001, 3 atributos


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
        assert codes(got) == [115, 109, 115, 86]
        rsp = pb.StoreRspMsg.FromString(got[-1].body)
        assert (rsp.strengResult, rsp.strengthenGrade, wand.strengthen_grade, luck.count) == (True, 1, 1, 1)
        assert c.gold == 2000 - 522  # 1.5^1 * (2+1) * 1^2.2 * 5 + 500

        monkeypatch.setattr(forge.random, "randint", lambda a, b: 101)  # 90% + 10% da pedra: só passa até 100
        g.client.send(5150)
        got = await g.until(86)
        assert codes(got) == [115, 109, 86] and not pb.StoreRspMsg.FromString(got[-1].body).strengResult
        assert wand.strengthen_grade == 1 and luck not in me(g).items  # a pedra vai mesmo na falha

        c.gold = 0
        g.client.send(5150)  # sem ouro
        assert await g.idle() == []


async def test_drill_inlay_and_remove(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold = 1000
        wand = Item(g.user_id, WAND, bag_type=0, pos=0)
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
        assert wand.joins == [0, 0, -1, -1] and drills not in me(g).items

        g.client.send(5151, pb.StoreReqMsg(mountPos=1, bagType=1, bagPos=1))
        got = await g.until(83)
        assert codes(got) == [109, 115, 115, 111, 83] and wand.join_1 == ATTACK_1
        g.client.send(5151, pb.StoreReqMsg(mountPos=2, bagType=1, bagPos=2))  # mesmo atributo (Saldırı)
        assert await g.idle() == []

        g.client.send(5152, pb.StoreReqMsg(holePos=1, operate=False))  # tirar custa 200 (Property3)
        got = await g.until(83)
        assert codes(got) == [109, 115, 115, 111, 83] and wand.join_1 == 0 and c.gold == 800
        assert (
            pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Başarıyla söküldü! Kazanılan:Saldırı Taşı Lv.1 x1!"
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
        assert codes(got) == [115, 109, 115, 111, 89, 83] and c.gold == 40000
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg == "Kazanılan:İnanç Kılıcı x1"
        assert {(i.template_id, i.count) for i in me(g).items if i.bag_type == 1} >= {(2129001, 1), (1991011, 1)}
        g.client.send(5153, pb.StoreReqMsg(composeId=1, composeNum=1))  # falta material
        assert await g.idle() == []

        g.client.send(8538, pb.StoreReqMsg(srcItemid=ATTACK_1, desItemid=MAGIC_1, count=2))
        got = await g.until(83)
        assert codes(got) == [115, 109, 115, 111, 83] and c.gold == 20000
        assert {(i.template_id, i.count) for i in me(g).items} >= {(ATTACK_1, 1), (MAGIC_1, 2)}
        g.client.send(8538, pb.StoreReqMsg(srcItemid=ATTACK_1, desItemid=ATTACK_2, count=1))  # nível diferente
        assert await g.idle() == []


async def test_refine_needs_replace_to_apply(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        sword = Item(g.user_id, SWORD, bag_type=0, pos=0, random_skill=70302)
        await put(g, sword, Item(g.user_id, 2127001, pos=0))

        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, False, False], payType=0))
        got = await g.until(4258)
        skills = list(pb.SmithFreshRspMsg.FromString(got[-1].body).randomSkill)
        assert codes(got) == [115, 4258] and len(skills) == 3 and skills[0] == 70302
        assert sword.random_skills == [70302, 0, 0, 0, 0]  # ainda não trocou

        g.client.send(8339)
        got = await g.until(115)
        assert pb.SmithFreshReplaceRspMsg.FromString(got[0].body).result and sword.random_skills[:3] == skills
        g.client.send(8339)  # nada pendente
        assert not pb.SmithFreshReplaceRspMsg.FromString((await g.until(4259))[-1].body).result
        g.client.send(8340)
        assert not pb.SmithResolveRspMsg.FromString((await g.until(4260))[-1].body).result
