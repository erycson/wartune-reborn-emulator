"""Guerra de guildas (mapa 4501): o estado puro de ``game/guildwar.py`` (par, fator, placar, defesa, buffs)."""

from __future__ import annotations

from datetime import datetime, timedelta

from wartune_server.game import guildwar as gw

NOW = datetime(2026, 10, 26, 20, 0)


def _war() -> gw.War:
    return gw.War(gw.Side(1, "A", gw.RED), gw.Side(2, "B", gw.BLUE), NOW)


def test_pares_e_grupos() -> None:
    top = [10, 20, 30, 40, 50, 60, 70, 80]
    p = gw.pairs(top)
    assert p[10] == (50, gw.RED, 1) and p[50] == (10, gw.BLUE, 1)
    assert p[40] == (80, gw.RED, 4)
    assert gw.group_of(top, 60) == 2 and gw.group_of(top, 99) == 0
    assert gw.pairs([1, 2, 3]) == {}  # sem par ninguém luta


def test_janela() -> None:
    opened, ends = gw.window(NOW + timedelta(minutes=7))
    assert (opened.hour, ends.hour) == (20, 21)


def test_fator_das_torres_e_placar() -> None:
    w = _war()
    assert w.hit(w.red, 7, "x", 1, 100_000) == 50_000  # sem torre: x0,5
    w.owner = {1: gw.RED, 2: gw.RED, 3: gw.RED, 4: gw.RED}
    assert w.hit(w.red, 7, "x", 1, 100_000) == 200_000  # 4 torres: x2
    w.dead.add(9)
    assert w.tick(NOW) == [9] and not w.dead
    assert w.red.score == 25 and w.blue.hp == gw.TOWER_HP - 250_000
    assert w.wounds[7].wound == 250_000


def test_vitoria_por_vantagem_e_torre_caida() -> None:
    w = _war()
    w.red.dealt = gw.WIN_LEAD * gw.POINT_DAMAGE
    w.tick(NOW)
    assert w.winner == gw.RED
    w = _war()
    w.owner = {i: gw.BLUE for i in range(4)}
    w.hit(w.blue, 8, "y", 1, gw.TOWER_HP)
    assert w.red.hp == 0 and w.winner == gw.BLUE
    w = _war()
    w.time_over()
    assert w.winner == gw.RED  # empate fica com a vermelha


def test_defesa() -> None:
    w = _war()
    assert w.defend(5, 1, w.red, set(), cap=1) == "taken" and w.owner[5] == gw.RED
    assert w.defend(5, 2, w.blue, {1}, cap=1) == "full"
    assert w.defend(5, 3, w.red, set(), cap=2) == "ok"
    w.owner[5] = gw.BLUE
    assert w.defend(5, 2, w.red, {1, 3}, cap=5) == "contested"
    w.wound_of(1, "a", 1)
    w.tick(NOW)
    assert w.wounds[1].wound == gw.DEFEND_WOUND
    assert w.stop_defending(1) == 5 and w.defending(1) == 0


def test_buffs() -> None:
    w = _war()
    assert w.can_buff(w.red, gw.INSPIRATION, 1, 60, NOW)
    w.use_buff(w.red, gw.INSPIRATION, NOW)
    assert not w.can_buff(w.red, gw.INSPIRATION, 1, 60, NOW)
    assert w.rage(w.red, 7) and not w.rage(w.red, 7)
    w.red.hp = 1
    w.use_buff(w.red, gw.BLESSING, NOW)
    assert w.red.hp == 1 + int(gw.TOWER_HP * gw.BLESSING_HEAL)
    assert not w.can_buff(w.red, gw.BLESSING, 2, 60, NOW + timedelta(seconds=30))
    assert w.can_buff(w.red, gw.BLESSING, 2, 60, NOW + timedelta(seconds=60))
