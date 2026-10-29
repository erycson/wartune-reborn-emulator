"""Atalhos fechados: velocidade do tanque, skill de caixa sem Maximum e as taxas novas (0135)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from tests.game.test_veiculos import OPEN, TEMPLATES, TRAP, _duel, _templates
from wartune_server.game import arena as A
from wartune_server.game import taxas
from wartune_server.game import vehicles as vh

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def test_move_respects_template_speed() -> None:
    m, _ = _duel()
    x, y = vh.CENTER
    # Turbo Turret: Speed 7 px/quadro × 25 fps = 8,75 tiles/s, mais SLACK
    assert not m.move(2, [(x + 20, y)], OPEN + timedelta(seconds=1))
    assert m.move(2, [(x + 10, y)], OPEN + timedelta(seconds=1))
    assert (m.tanks[2].x, m.tanks[2].moved) == (x + 10, OPEN + timedelta(seconds=1))


def test_box_skill_without_maximum_is_unlimited() -> None:
    m, _ = _duel()
    t = m.tanks[1]
    m.tick(OPEN + timedelta(seconds=1))
    [box] = [n for n in m.nodes.values() if n.type == vh.NODE_PROP]
    row = _templates().get("VehicleSkillTempInfos", box.skill)
    assert m.pickup(1, box.node_id, OPEN + timedelta(seconds=1))
    limit = int(row["Maximum"]) if row else 0
    assert t.extra_left == (limit if limit > 0 else vh.UNLIMITED)
    t.extra, t.extra_left = TRAP, vh.UNLIMITED
    m._spend(t, TRAP)
    assert (t.extra, t.extra_left) == (TRAP, vh.UNLIMITED)


def test_defence_div_from_rules() -> None:
    m, _ = _duel()
    assert m._raw(100, 100, 50) == 75
    m.rules = m.rules | {"defence_div": 5}
    assert m._raw(100, 100, 50) == 90


def test_taxas_defaults_0135() -> None:
    assert [taxas.get({}, k) for k in ("pet_max_buy", "robot_hp", "robot_attack", "enemy_cast_ms")] == [
        10,
        0.35,
        0.15,
        3500,
    ]
    robot = A.Robot(1, 20)
    _, [hero] = A.robot_spec(robot, _templates(), 1000, 100, {"taxas": {"robot_hp": 0.5, "robot_attack": 1}})
    assert (hero["maxHp"], hero["attack"]) == (500, 100)
