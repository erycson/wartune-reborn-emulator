"""Fórmulas da batalha contra os números da captura oficial (tutorial_en) e o ciclo dos buffers."""

from __future__ import annotations

import asyncio
import functools
import random
import time
from pathlib import Path
from typing import Any

import pytest
from google.protobuf.message import Message

from wartune_server.game import battle as bt
from wartune_server.game.builders.login import HeroStats
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock
from wartune_server.templates.repository import GameTemplates

TEMPLATES = Path("data/templates/tempinfos.xml")


@pytest.mark.parametrize(
    ("patk", "pdef", "matk", "mdef", "fh", "parry", "live", "conat", "fc"),
    [  # (visto) tutorial_en, 150: #3, #305, #374, #638, #3204, #3226
        (4, 5, 20, 9, 10, 10, 200, 100, 199),
        (4, 13, 44, 23, 10, 10, 260, 120, 278),
        (4, 13, 76, 25, 10, 10, 260, 120, 313),
        (4, 36, 112, 73, 10, 10, 350, 152, 472),
        (4, 52, 159, 121, 19, 10, 500, 192, 664),
        (4, 52, 200, 134, 10, 10, 500, 192, 712),
    ],
)
def test_poder_de_combate_bate_com_o_150(
    patk: int, pdef: int, matk: int, mdef: int, fh: int, parry: int, live: int, conat: int, fc: int
) -> None:
    total = {"PhyAttack": patk, "PhyDefence": pdef, "MagicAttack": matk, "MagicDefence": mdef, "ForceHit": fh}
    total |= {"Parry": parry, "Live": live, "ConatArmy": conat}
    assert HeroStats({}, total).fighting_capacity == fc


@pytest.mark.parametrize(
    ("attack", "defence", "p1", "p2", "expected", "seen"),
    [  # golpe antes do sorteio; ``seen`` = o 153 da captura
        (20, 0, 102, 15, 25, (25,)),  # maga nível 1, Lightning Bolt (#189)
        (20, 0, 100, 0, 10, (10, 9)),  # golpe básico 30000 (#152, #191)
        (155, 49, 100, 0, 53, (53, 48)),  # maga nível 8 contra o 10102 (MDef 49) (#1676, #1937)
        (64, 66, 100, 0, 6, (5, 6)),  # Lancer contra o 10102 (Def 66): o piso de 10% (#1673, #1679)
        (84, 44, 150, 0, 30, (28, 30, 29)),  # 10102 skill 11 (150%) na maga (PDef 44) (#1670, #1671, #1698)
        (0, 0, 0, -50, -50, (-53, -51)),  # cura 40183 da Dinah (#555, #563)
    ],
)
def test_dano_bate_com_o_153(attack: int, defence: int, p1: int, p2: int, expected: int, seen: tuple[int, ...]) -> None:
    value = bt.damage(attack, defence, p1, p2)
    assert int(value) == expected
    assert all(abs(s - value) <= abs(value) * bt.FORMULA["spread"] + 1 for s in seen)


@functools.cache
def _templates() -> GameTemplates:
    return GameTemplates.parse(TEMPLATES.read_bytes())


def _battle(**extra: Any) -> tuple[bt.Battle, list[tuple[int, Message]]]:
    sent: list[tuple[int, Message]] = []
    spec: dict[str, Any] = {
        "battleType": 6,
        "mapTempId": 1021,
        "attackModel": 2,
        "soldiers": [{"livingId": 5, "tempId": 2011, "type": 1, "side": 2, "pos": 2, "initHp": 400, "hp": 400}],
        "heroes": [{"livingId": 4, "tempId": 1011, "side": 2, "pos": 5, "maxHp": 750, "hp": 750}],
        "player": {"livingId": 3, "pos": 4},
    } | extra
    msg = pb.HeroMsg(livingId=3, userId=1, tempId=3, side=1, pos=4, maxHp=410, hp=410, sp=0)
    msg.skillId.extend([30711, 30811, 30111])
    stats = {"PhyAttack": 4, "PhyDefence": 40, "MagicAttack": 124, "MagicDefence": 91, "ForceHit": 10, "Parry": 10}
    player = bt.PlayerHero(msg, stats, 30000)

    async def end(*_: Any) -> None: ...

    b = bt.Battle(spec, player, _templates(), FakeClock(), lambda c, m: sent.append((c, m)), end, rng=random.Random(1))
    return b, sent


def _unit(b: bt.Battle, living_id: int) -> bt.Unit:
    return next(u for u in b.units if u.living_id == living_id)


needs_templates = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


@needs_templates
def test_passiva_vira_buffer_no_157_e_da_furia_por_golpe() -> None:
    b, sent = _battle()
    hero = next(h for h in b.prepare_msg().heros if h.livingId == 3)
    buf = hero.buffers[0]  # (visto) #1466
    got = (buf.bufferId, buf.templateId, buf.curTurn, buf.seeType, buf.exeWay, buf.pressedNum)
    assert got == (1, 30111, -1, 1, 0, 1)
    assert 30111 not in [c.templatedId for c in b.prepare_msg().coolDown]
    assert not b._affordable(30111)

    b._act(_unit(b, 3), 30000)  # golpe básico: Cost 2 + 1 de fúria pelo dano (visto #1334: sp 3)
    msg = sent[-1][1]
    assert isinstance(msg, pb.AttackOrderMsg)
    assert (msg.sp, msg.spAdded) == (3, 2)
    rage = next(x for x in msg.buffers if x.templateId == 30111)
    assert (rage.curTurn, rage.exeWay, rage.maxTurn) == (-2, 3, -1)
    assert [(d.damageType, d.damageValue, d.leftValue) for d in rage.damage] == [(9, 1, 3)]


@needs_templates
def test_sangramento_do_chomp_segue_a_captura() -> None:
    """60023 (Chomp do Wulfgar): entra com 2 turnos, sangra 25 em cada ação da maga e sai (visto #1484-#1493)."""
    b, sent = _battle()
    hero, wolf = _unit(b, 3), _unit(b, 4)
    b._act(wolf, 60023)
    bleed = next(x for x in sent[-1][1].buffers if x.templateId == 60023)  # type: ignore[attr-defined]
    assert (bleed.sourceId, bleed.targetId, bleed.curTurn, bleed.maxTurn, bleed.seeType) == (4, 3, 2, 2, 0)

    before = hero.hp
    b._act(hero, 30000)
    bleed = next(x for x in sent[-1][1].buffers if x.templateId == 60023)  # type: ignore[attr-defined]
    assert (bleed.curTurn, bleed.seeType, bleed.exeWay) == (1, 1, 1)
    assert [(d.damageType, d.damageValue, d.leftValue) for d in bleed.damage] == [(6, 25, before - 25)]

    b._act(hero, 30000)
    bleed = next(x for x in sent[-1][1].buffers if x.templateId == 60023)  # type: ignore[attr-defined]
    assert (bleed.curTurn, bleed.seeType) == (0, 2)
    assert not any(x.row["Id"] == "60023" for x in b.buffs)


@needs_templates
def test_atordoamento_tira_a_vez_e_respeita_o_reject_type() -> None:
    b, _ = _battle()
    hero, wolf, worg = _unit(b, 3), _unit(b, 4), _unit(b, 5)
    assert b._apply(hero, wolf, 41) is None  # Wulfgar: RejectType 19,100,38,39 (imune a atordoamento)
    stun = b._apply(hero, worg, 41)  # "Stunned - Movement inhibited", 1 turno
    assert stun is not None and b._has(worg, bt.NO_ACTION)
    b._turn_buffs(worg)  # a vez perdida conta o turno
    assert not b._has(worg, bt.NO_ACTION) and stun.see == 2


@needs_templates
async def test_sem_ordem_o_heroi_da_o_golpe_basico_na_vez_dele() -> None:
    """(visto) tutorial_en #152, #271, #274: sem 10008 o herói golpeia com o 30000 na vez dele; a ordem que
    chega antes vale, e a que não dá mais (fúria) vira golpe básico (#279 -> #281)."""
    b, _ = _battle()
    b._t0 = time.monotonic()
    assert await b._player_skill(b.frame + 2) == 30000

    hero = _unit(b, 3)
    hero.sp = 100
    b.order(3, 30711)
    assert await b._player_skill(b.frame + 2) == 30711

    b.order(3, 30811)
    hero.sp = 0  # gastou a fúria antes da vez
    assert await b._player_skill(b.frame + 2) == 30000


@needs_templates
def test_so_a_luta_roteirizada_segura_o_lado_do_jogador_em_1_de_vida() -> None:
    """Tutorial (``undying``): nenhuma unidade do jogador a 0 (#144-#540); fora dele morre (#1466, #1657)."""
    b, _ = _battle()
    hero = _unit(b, 3)
    assert b._floor_hp(hero, 9999) == 9999
    b, _ = _battle(undying=True)
    hero = _unit(b, 3)
    assert b._floor_hp(hero, 9999) == hero.hp - 1


@needs_templates
def test_tropas_mortas_saem_e_a_reserva_repoe() -> None:
    """tutorial_en #1466: 162 Lancers (Live 323) com 238 de vida no fim -> 88 mortos; a reserva 738 -> 650."""
    from types import SimpleNamespace

    from wartune_server.domain.models import Pawn
    from wartune_server.game import outer_city as oc

    pawn = Pawn(1, 10101, castle_count=738, army_count=162)
    snap: Any = SimpleNamespace(pawns=[pawn], buildings=[])  # lose_troops só lê as tropas e as tecnologias
    templates = _templates()
    assert oc.lose_troops(snap, templates, (523, 523)) is None  # sem dano, sem perda
    hit = oc.lose_troops(snap, templates, (238, 523))
    assert hit == (pawn, 88) and pawn.army_count == 74
    oc.refill(*hit)
    assert (pawn.army_count, pawn.castle_count) == (162, 650)
    pawn.castle_count = 50  # reserva curta: o exército fica menor
    hit = oc.lose_troops(snap, templates, (0, 523))
    assert hit == (pawn, 162)
    oc.refill(*hit)
    assert (pawn.army_count, pawn.castle_count) == (50, 0)


def _pet_battle(awake: int) -> tuple[bt.Battle, list[tuple[int, Message]], list[int]]:
    """Herói 3 com o Pan (104101) em batalha, como peri_uyanis #50."""
    sent: list[tuple[int, Message]] = []
    saved: list[int] = []
    spec: dict[str, Any] = {
        "battleType": 6,
        "mapTempId": 1021,
        "attackModel": 2,
        "soldiers": [{"livingId": 5, "tempId": 2011, "type": 1, "side": 2, "pos": 2, "initHp": 9000, "hp": 9000}],
        "heroes": [{"livingId": 4, "tempId": 1011, "side": 2, "pos": 5, "maxHp": 9000, "hp": 9000}],
        "player": {"livingId": 3, "pos": 4},
    }
    msg = pb.HeroMsg(livingId=3, userId=1, tempId=3, side=1, pos=4, maxHp=410, hp=410, sp=0, awake=awake)
    msg.skillId.extend([30711, 30811])
    msg.changeSkillId.extend([735101, 731001, 733101])
    change = [735101, 731001, 733101, 731201]
    pet = {"tempId": 104101, "side": 1, "pos": 0, "maxHp": 7173, "initHp": 7173, "hp": 7173, "userId": 1}
    pet |= {"skillId": [728101, 729101, 730101, *change], "follow": [729101, 730101], "change": change}
    stats = {"PhyAttack": 4, "PhyDefence": 40, "MagicAttack": 124, "MagicDefence": 91, "ForceHit": 10, "Parry": 10}
    player = bt.PlayerHero(msg, stats, 30000, pet=pet, on_awake=saved.append)

    async def end(*_: Any) -> None: ...

    b = bt.Battle(spec, player, _templates(), FakeClock(), lambda c, m: sent.append((c, m)), end, rng=random.Random(1))
    return b, sent, saved


def _awakes(sent: list[tuple[int, Message]]) -> list[int]:
    return [m.awake[0].awake for c, m in sent if c == bt.S_AWAKE]  # type: ignore[attr-defined]


@needs_templates
def test_mascote_entra_na_luta_e_o_despertar_sobe_250() -> None:
    b, sent, saved = _pet_battle(0)
    prep = b.prepare_msg()
    hero = next(h for h in prep.heros if h.livingId == 3)
    assert (hero.livingId2, [p.livingId for p in prep.pets], prep.pets[0].livingId2) == (6, [6], 3)
    assert _unit(b, 6).skills == [729101, 730101]  # as passivas e as do modo mascote não entram na rotação
    b._act(_unit(b, 3), 30000)
    b._act(_unit(b, 4), _unit(b, 4).default_skill)
    b._act(_unit(b, 5), _unit(b, 5).default_skill)
    assert _awakes(sent) == [250, 500]  # golpe levado: um 4600 só até a próxima ação do herói
    assert saved == [250, 500]
    attack = next(m for c, m in sent if c == bt.S_ATTACK)
    assert attack.awake == 0  # type: ignore[attr-defined]  (o 153 leva o valor de antes)


@needs_templates
def test_transforma_com_3000_gasta_150_e_desfaz_no_zero() -> None:
    b, sent, _ = _pet_battle(3000)
    hero = _unit(b, 3)
    b.order(3, bt.UNMORPH)
    assert sent[-1][1].result == 1  # type: ignore[attr-defined]  (não está transformado)
    b.order(3, bt.MORPH)
    assert sent[-1][1].result == 0  # type: ignore[attr-defined]
    b._act(hero, bt.MORPH)
    assert b.morphed and hero.skills == [735101, 731001, 733101]
    assert any(x.row["Id"] == "731201" and x.active for x in b.buffs)
    b._act(_unit(b, 4), _unit(b, 4).default_skill)  # transformado, golpe levado não dá
    b._act(hero, 731001)
    assert _awakes(sent) == [2850, 2700]  # (visto peri_uyanis #59, #69)
    b.awake = 0
    assert asyncio.run(b._player_skill(0)) == bt.UNMORPH
    b._act(hero, bt.UNMORPH)
    assert not b.morphed and hero.skills == [30711, 30811]
    assert not any(x.row["Id"] == "731201" and x.active for x in b.buffs)
