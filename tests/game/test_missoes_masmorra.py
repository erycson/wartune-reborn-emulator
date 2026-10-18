"""Condições 14, 25, 26, 27 e 31 ligadas à masmorra Kurt İni, e Para1 em lista (14 e 26). Ver docs/missoes.md."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.content import dungeon
from wartune_server.domain.models import BagType, Item, PlayerSnapshot, Quest
from wartune_server.game import bag, rules
from wartune_server.game.campaign import DONE, CampaignMap
from wartune_server.game.handlers.campaign import _map_finished
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

KURT_DIS, SANS_TASI = 2100001, 2040101


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def test_para1_em_lista_nao_derruba_o_aceite(tmp_path: Path) -> None:
    # 760 tem Para1 "9004,9104" (tipo 14): antes, int("9004,9104") derrubava o aceite (update_state_quests)
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        snap = _snap(g)
        q = Quest(g.user_id, 760, datetime.now(UTC))
        snap.quests.append(q)
        rules.update_state_quests(snap, templates, [q])  # não levanta


def test_para1_lista_casa_qualquer_um_dos_ids() -> None:
    assert rules.para1_ids("9004,9104") == {9004, 9104}
    assert rules.para1_ids("0") == {0}
    assert rules._para1_ok(14, "9004,9104", 9004)
    assert rules._para1_ok(14, "9004,9104", 9104)
    assert not rules._para1_ok(14, "9004,9104", 9005)
    assert rules._para1_ok(14, "0", 1001)  # 0 = qualquer campanha


async def test_14_passou_a_campanha_casa_o_id_e_nao_soma(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        snap = _snap(g)
        now = datetime.now(UTC)
        q70 = Quest(g.user_id, 70, now)  # linha: tipo 14, Para1 1001 (Kurt İni)
        snap.quests.append(q70)
        assert rules.quest_event(snap, templates, rules.CAMPAIGN_CONDITION, 1002, 1) == []  # outra campanha
        assert rules.quest_event(snap, templates, rules.CAMPAIGN_CONDITION, 1001, 1) == [q70]
        assert rules.quest_event(snap, templates, rules.CAMPAIGN_CONDITION, 1001, 1) == []  # sim, não soma
        assert rules.progress_of(q70, 0) == 1
        assert rules.quest_done(snap, templates, q70, now)


async def test_26_chefe_pelo_template_e_nao_pelo_mapa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        snap = _snap(g)
        now = datetime.now(UTC)
        q80 = Quest(g.user_id, 80, now)  # tipo 26, Para1 1011 = 'Wulfgar' (GameHeroTemp; 'Çene' no turco), Para3 1001
        snap.quests.append(q80)
        assert templates.get("GameHeroTemp", 1011, key="TemplateId")["TemplateName"] == "Wulfgar"
        assert rules.quest_event(snap, templates, rules.HERO_KILL_CONDITION, 1031, 1) == []  # outro chefe
        assert rules.quest_event(snap, templates, rules.HERO_KILL_CONDITION, 1011, 1) == [q80]
        assert rules.quest_done(snap, templates, q80, now)


async def test_31_cena_solo_casa_a_capacidade(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        snap = _snap(g)
        q313 = Quest(g.user_id, 313, datetime.now(UTC))  # Para1 1 = solo; 371 é Para1 2 (grupo)
        snap.quests.append(q313)
        assert rules.quest_event(snap, templates, rules.SOLO_CONDITION, 2, 1) == []
        assert rules.quest_event(snap, templates, rules.SOLO_CONDITION, 1, 1) == [q313]
        assert rules.progress_of(q313, 0) == 1
        # Para2 3: "herhangi bir haritayı [3 kez] geç" (qualquer mapa, não só a 1001)
        assert not rules.quest_done(snap, templates, q313, datetime.now(UTC))
        rules.quest_event(snap, templates, rules.SOLO_CONDITION, 1, 2)
        assert rules.quest_done(snap, templates, q313, datetime.now(UTC))


async def test_27_conta_a_bolsa_e_a_entrega_leva_todas_as_unidades(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        snap = _snap(g)
        now = datetime.now(UTC)
        q90 = Quest(g.user_id, 90, now)  # tipo 27: 8 de 2100001 (Kurt Dişi)
        snap.quests.append(q90)
        pile = Item(g.user_id, KURT_DIS, count=7, pos=0)
        snap.items.append(pile)
        assert rules.goods_count(snap, KURT_DIS) == 7
        assert not rules.quest_done(snap, templates, q90, now)  # 7 de 8
        snap.items.append(Item(g.user_id, KURT_DIS, count=3, pos=1))
        assert rules.quest_done(snap, templates, q90, now)  # bolsa, não contador: sem quest_event
        assert rules.goods_to_take(snap, templates, 90) == [(KURT_DIS, 10)]  # item de missão sai inteiro (replay)


async def test_27_nao_conta_item_que_nao_esta_na_bolsa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        snap = _snap(g)
        q90 = Quest(g.user_id, 90, datetime.now(UTC))
        snap.quests.append(q90)
        snap.items.append(Item(g.user_id, KURT_DIS, count=9, pos=0, bag_type=BagType.HERO))  # fora da bolsa
        assert rules.goods_count(snap, KURT_DIS) == 0
        assert not rules.quest_done(snap, templates, q90, datetime.now(UTC))


def test_drops_por_no_do_1021_como_visto_no_replay() -> None:
    drops = dungeon()["drops"]
    assert drops == {
        "102102": [[KURT_DIS, 2], [SANS_TASI, 1]],
        "102103": [[KURT_DIS, 2]],
        "102105": [[KURT_DIS, 3]],
        "102106": [[KURT_DIS, 3]],
    }
    assert sum(n for nodo in drops.values() for t, n in nodo if t == KURT_DIS) == 10  # 8 da 90, com folga


def test_fim_de_mapa_so_com_o_grupo_caido_e_sem_param4() -> None:
    camp = CampaignMap.enter_dungeon(1011)
    for wolf in (101102, 101105, 101106):  # 101103 ainda de pé
        camp.nodes[wolf]["state"] = DONE
    assert not _map_finished(camp, 101109)
    camp.nodes[101103]["state"] = DONE
    assert _map_finished(camp, 101109)  # último lobo do 1011: sem param4, o mapa acaba

    camp = CampaignMap.enter_dungeon(1021)
    for wolf in (102102, 102103, 102105):
        camp.nodes[wolf]["state"] = DONE
    assert not _map_finished(camp, 102106)  # o 102106 tem param4 (libera o chefe): desbloqueia, não acaba
    assert _map_finished(camp, 102109)  # chefe sem grupo: acaba o mapa


def test_kurt_dis_e_sans_tasi_existem_e_cabem_numa_pilha() -> None:
    # (visto) ItemTempInfos: Worg Tooth (Kurt Dişi) MaxCount 999 no inglês (9999 no turco)
    # então as 10 unidades do 1021 cabem numa pilha só
    templates = GameTemplates.parse(TEMPLATES.read_bytes())
    assert templates.get("ItemTempInfos", SANS_TASI) is not None
    assert bag.max_count(templates, KURT_DIS) >= 10
