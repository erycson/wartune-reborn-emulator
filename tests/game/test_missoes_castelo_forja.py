"""Missões de castelo e forja (tipos 12, 17, 18, 19, 42 e 47): a ação validada e gravada avança a missão
e manda o 112 com o progresso. Tipos 46, 63 e 90 não estão ligados (ver o relatório da rodada)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item, PlayerSnapshot, Quest
from wartune_server.game.handlers import forge
from wartune_server.protocol.messages import wartune_pb2 as pb

READY = 20000  # castelo pronto (como em test_castelo.py)
WAND = 1013002  # Saray Rahibi Değneği: StrengthenMax 3, sem furos
DRILL = 208004  # Elmas Delici
ATTACK_1, ATTACK_2 = 2050101, 2050102  # Saldırı Taşı Lv.1 e Lv.2
SWORD = 1011003  # Saray Süvarisi Kılıcı: refino com 2127001
STONE_REFINE = 2127001


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _building(snap: PlayerSnapshot, template_id: int) -> int:
    return next(b.id for b in snap.buildings if b.template_id == template_id and b.id)


async def _set(g: Game, **fields: int) -> PlayerSnapshot:
    snap = _snap(g)
    for name, value in fields.items():
        setattr(snap.character, name, value)
    await g.server.services.characters.save(snap.character)
    return snap


async def put(g: Game, *items: Item) -> None:
    me(g).items.extend(items)
    await g.server.services.characters.save(*items)


def _progress(got: list) -> tuple[int, int]:
    """(templateId, condition_1) da primeira missão no 112 de ``got``."""
    quest = pb.QuestUpdatedRspMsg.FromString(next(p for p in got if p.code == 112).body).quest[0]
    return quest.templateId, quest.condition_1


async def test_missao_12_acelerar_fila_de_predio_conta_uma_acao(tmp_path: Path) -> None:
    """Missão 111 "Bekleme Süresini Kaldır" (Para1 1 = fila de prédio): o 5172 numa fila de prédio avança 1."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=2, gold=1000, point=5)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 90101)))  # cria a fila de prédio
        await g.until(83)
        snap.quests.append(Quest(g.user_id, 111, datetime.now(UTC)))

        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=1))
        got = await g.until(112)
        assert _progress(got) == (111, 1)  # o isComplete só vem no 5014, como nas outras missões


async def test_missao_42_altin_topla_conta_cada_cobranca(tmp_path: Path) -> None:
    """Missão 763 "Altın Topla" (Para1 0): a cobrança de ouro no conselho (8327) avança 1."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=14, gold=0, point=100)
        snap.quests.append(Quest(g.user_id, 763, datetime.now(UTC)))

        g.client.send(8327, pb.PayTypeMsg())
        got = await g.until(112)
        assert _progress(got) == (763, 1)
        assert snap.character.gold > 0


async def test_missao_17_reforco_conta_quando_o_grau_chega_ao_minimo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missão 121 (Para1 2 = grau mínimo do item): reforço que chega a +1 não conta; o que chega a +2 conta."""
    async with logged_in(tmp_path, novice=19000) as g:
        me(g).character.gold = 2000
        wand = Item(g.user_id, WAND, bag_type=0, pos=0)
        await put(g, wand)
        me(g).quests.append(Quest(g.user_id, 121, datetime.now(UTC)))
        monkeypatch.setattr(forge.random, "randint", lambda a, b: 1)  # sempre dá certo

        g.client.send(5150)
        got = await g.until(86)
        assert wand.strengthen_grade == 1 and 112 not in codes(got)

        g.client.send(5150)
        got = await g.until(112)
        assert wand.strengthen_grade == 2 and _progress(got) == (121, 1)


async def test_missao_18_mosaico_de_pedra_de_ataque(tmp_path: Path) -> None:
    """Missão 281 (Para1 1 = pedra de ataque, Property1 1): o mosaico (5151) com essa pedra avança 1."""
    async with logged_in(tmp_path, novice=19000) as g:
        me(g).character.gold = 1000
        wand = Item(g.user_id, WAND, bag_type=0, pos=0)
        await put(g, wand, Item(g.user_id, DRILL, pos=0, count=1), Item(g.user_id, ATTACK_1, pos=1))
        me(g).quests.append(Quest(g.user_id, 281, datetime.now(UTC)))

        g.client.send(5152, pb.StoreReqMsg(holePos=1, operate=True))  # abre o furo 1 com o Elmas Delici
        await g.until(115)
        await g.until(115)
        g.client.send(5151, pb.StoreReqMsg(mountPos=1, bagType=1, bagPos=1))
        got = await g.until(112)
        assert wand.join_1 == ATTACK_1 and _progress(got) == (281, 1)


async def test_missao_19_compor_pedra_conta_so_pedra(tmp_path: Path) -> None:
    """Missão 311 (Para1 0): 4 x Saldırı Taşı Lv.1 -> Lv.2 (receita 33) é pedra e avança 1."""
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold, c.grades = 50000, 20
        await put(g, Item(g.user_id, ATTACK_1, pos=0, count=4))
        me(g).quests.append(Quest(g.user_id, 311, datetime.now(UTC)))

        g.client.send(5153, pb.StoreReqMsg(composeId=33, composeNum=1))
        got = await g.until(112)
        assert _progress(got) == (311, 1)
        assert any(i.template_id == ATTACK_2 for i in me(g).items)


async def test_missao_47_arita_conta_cada_sorteio(tmp_path: Path) -> None:
    """Missão 769 "Ekipman Arıt" (Para1 0): o 8336 que gasta a pedra de refino avança 1."""
    async with logged_in(tmp_path, novice=19000) as g:
        sword = Item(g.user_id, SWORD, bag_type=0, pos=0, random_skill=70302)
        await put(g, sword, Item(g.user_id, STONE_REFINE, pos=0))
        me(g).quests.append(Quest(g.user_id, 769, datetime.now(UTC)))

        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, False, False], payType=0))
        got = await g.until(112)
        assert codes(got)[-2:] == [4258, 112] and _progress(got) == (769, 1)
