"""Missões de castelo e forja (tipos 12, 17, 18, 19, 42, 47 e 63): a ação validada e gravada avança a missão
e manda o 112 com o progresso. Tipos 46 e 90 não estão ligados (ver o relatório da rodada)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item, PlayerSnapshot, Quest
from wartune_server.game.handlers import forge
from wartune_server.protocol.messages import wartune_pb2 as pb

READY = 20000  # castelo pronto (como em test_castelo.py)
WAND = 1013002  # Templar Priest Staff: StrengthenMax 3, sem furos
DRILL = 208004  # Elmas Delici
ATTACK_1, ATTACK_2 = 2050101, 2050102  # Lvl. 1 e Lvl. 2 Physical Attack Gem
SWORD = 1011003  # Templar Knight Long Sword: refino com 2127001
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
    """Missão 111 "Accelerate Building Construction Cooldown 1 time" (Para1 1 = fila de prédio): o 5172 numa fila de prédio avança 1."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=2, gold=1000, point=5)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 90101)))  # cria a fila de prédio
        await g.until(83)
        snap.quests.append(Quest(g.user_id, 111, datetime.now(UTC)))

        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=1))
        got = await g.until(112)
        assert _progress(got) == (111, 1)  # o isComplete só vem no 5014, como nas outras missões


async def test_missao_42_altin_topla_conta_cada_cobranca(tmp_path: Path) -> None:
    """Missão 763 "Collect Levy" (Para1 0): a cobrança de ouro no conselho (8327) avança 1."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=14, gold=0, point=100)
        snap.quests.append(Quest(g.user_id, 763, datetime.now(UTC)))

        g.client.send(8327, pb.PayTypeMsg())
        got = await g.until(112)
        assert _progress(got) == (763, 1)
        assert snap.character.gold > 0


async def test_missao_17_reforco_conta_quando_o_grau_passa_do_minimo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missão 121 (Para1 2, Detail "3 lv"): só conta quando o grau passa de 2, ou seja, ao chegar a +3."""
    async with logged_in(tmp_path, novice=19000) as g:
        me(g).character.gold = 3000
        wand = Item(g.user_id, WAND, bag_type=0, pos=0)
        await put(g, wand)
        me(g).quests.append(Quest(g.user_id, 121, datetime.now(UTC)))
        monkeypatch.setattr(forge.random, "randint", lambda a, b: 1)  # sempre dá certo

        for grade in (1, 2):
            g.client.send(5150)
            got = await g.until(86)
            assert wand.strengthen_grade == grade and 112 not in codes(got)

        g.client.send(5150)
        got = await g.until(112)
        assert wand.strengthen_grade == 3 and _progress(got) == (121, 1)


async def test_missao_18_qualquer_mosaico_avanca(tmp_path: Path) -> None:
    """Missão 281 ("Socket a Gem", qualquer pedra): o mosaico (5151) de qualquer pedra avança 1."""
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
    """Missão 311 (Para1 0): 4 x Lvl. 1 Physical Attack Gem -> Lvl. 2 (receita 33) é pedra e avança 1."""
    async with logged_in(tmp_path, novice=19000) as g:
        c = me(g).character
        c.gold, c.grades = 50000, 20
        await put(g, Item(g.user_id, ATTACK_1, pos=0, count=4))
        me(g).quests.append(Quest(g.user_id, 311, datetime.now(UTC)))

        g.client.send(5153, pb.StoreReqMsg(composeId=33, composeNum=1))
        got = await g.until(112)
        assert _progress(got) == (311, 1)
        assert any(i.template_id == ATTACK_2 for i in me(g).items)


async def test_missao_63_devotion_guarda_o_total_da_atividade(tmp_path: Path) -> None:
    """Missão 863 "Increasing Devotion (VIP Daily)" (Para2 20): vale o totalNum do 4152; login 5 + chat no mundo 5 = 10."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = await _set(g, grades=20)  # chat no mundo pede nível 20 (tutorial_en #2779)
        snap.quests.append(Quest(g.user_id, 863, datetime.now(UTC)))

        g.client.send(8198, pb.ChatChannelMsg(channel=10, encodeMsg="oi"))  # leed 16 "Speak in world chat"
        got = await g.until(112)
        assert pb.LeedUpdatedRspMsg.FromString(next(p for p in got if p.code == 4152).body).totalNum == 10
        assert _progress(got) == (863, 10)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert next(q.progress for q in saved.quests if q.template_id == 863) == 10


async def test_missao_47_arita_conta_cada_sorteio(tmp_path: Path) -> None:
    """Missão 769 "Equipment Refine" (Para1 0): o 8336 que gasta a pedra de refino avança 1."""
    async with logged_in(tmp_path, novice=19000) as g:
        sword = Item(g.user_id, SWORD, bag_type=0, pos=0, random_skill=70302)
        await put(g, sword, Item(g.user_id, STONE_REFINE, pos=0))
        me(g).quests.append(Quest(g.user_id, 769, datetime.now(UTC)))

        g.client.send(8336, pb.SmithFreshReqMsg(lock=[True, False, False], payType=0))
        got = await g.until(112)
        assert codes(got)[-2:] == [4258, 112] and _progress(got) == (769, 1)
