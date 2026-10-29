"""Taxas da luta, do relatório 137, do torneio de fadas e do veículo em ``game_settings`` (migração 0130)."""

from __future__ import annotations

import random
from datetime import UTC, datetime

from tests.game.test_batalha import _battle, _templates, needs_templates
from tests.game.test_veiculos import HIT, OPEN, _duel, _shoot
from wartune_server.game import arena as A
from wartune_server.game import battle as bt
from wartune_server.game import vehicles as vh
from wartune_server.game.campaign import StageRun, grades
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = needs_templates


def test_alvo_sorteado_e_heroi_primeiro_pela_config() -> None:
    b, _ = _battle(heroes=[{"livingId": 4, "tempId": 1011, "side": 2, "pos": 5, "maxHp": 750, "hp": 750}])
    assert b.player is not None
    assert [u.living_id for u in b._targets(b.player, 0)] == [4]  # padrão: o de menor livingId
    assert b._round_order()[-1] is b.player
    b.formula = b.formula | {"target_random": 1.0, "hero_first": 1.0}
    b.rng = random.Random(3)
    picked = {b._targets(b.player, 0)[0].living_id for _ in range(30)}
    assert picked == {4, 5}
    assert b._round_order()[0] is b.player


def test_despertar_lento_abaixo_do_nivel_55() -> None:
    b, _ = _battle()
    assert b._awake_gain == int(bt.FORMULA["awake_gain_low"])  # herói de nível 0 no _battle
    msg = bt.PlayerHero(pb.HeroMsg(livingId=3, userId=1, tempId=3, side=1, pos=4, grade=60), {}, 30000)
    spec = {"battleType": 6, "mapTempId": 1021, "attackModel": 2, "soldiers": [], "player": {"livingId": 3, "pos": 4}}
    settings = {"battle_formula": {"awake_gain": 300, "awake_gain_low": 100}}

    async def end(*_: object) -> None: ...

    high = bt.Battle(spec, msg, _templates(), b.clock, lambda *_: None, end, settings=settings)
    assert high._awake_gain == 300


def test_notas_do_137_com_degraus_e_curva_por_nivel() -> None:
    row = {"StandardDamage": 1000, "StandardHurt": 1000, "MinLevel": 10}
    run = StageRun(1001, 0, (1011,), datetime(2026, 10, 29, tzinfo=UTC), wound=1000, hurt=0)
    assert grades(run, row)[0] == 5
    cfg = {"level_scale": 0.1}
    assert grades(run, row, cfg, level=20)[0] == 1  # padrão dobrado no nível 20: 1000/2000 = 0,5, abaixo de 0,7 = D
    assert grades(run, row, {"wound_steps": [0.1, 0.2, 0.3, 0.4]}, level=20)[0] == 5


def test_pet_do_torneio_de_fadas_pela_config() -> None:
    t = _templates()
    base = A.pet_unit(104101, 60, 7, 1, 1, 1, 42, 77, t)
    other = A.pet_unit(104101, 60, 7, 1, 1, 1, 42, 77, t, cfg={"hp_growth_div": 3, "attack_div": 10})
    assert other["maxHp"] > base["maxHp"]
    assert other["attack"] == other["maxHp"] // 10


def test_pontos_do_veiculo_pela_config() -> None:
    m, _ = _duel()
    m.rules = m.rules | {"score_damage": 1}
    assert m.cast(1, _shoot(2), OPEN)
    assert m.scores[vh.RED] == HIT  # 1 ponto por dano
    arena = vh.Arena()
    arena.enqueue([1])
    win = (OPEN, OPEN)
    assert len(arena.place(_templates(), win, OPEN, lambda *_: None, rules={"min_players": 1})) == 0  # um lado só
    arena.enqueue([2])
    [(match, _, _), _] = arena.place(_templates(), win, OPEN, lambda *_: None, rules={"boxes": 1})
    assert match.rules["boxes"] == 1
