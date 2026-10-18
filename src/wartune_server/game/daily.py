"""Virada do dia do jogo (5h, ``domain/gameday``) do que o cliente reinicia de uma vez (4202 ``DataResetMsg``):
energia de teleporte cheia, +100 de stamina por dia (até o máximo), as poções do dia zeradas e a bênção
de volta a 10%, além dos contadores da arena. Roda no login e no 20008 (o cliente manda a cada ~60 s),
então quem fica online também vira às 5h, e quem volta depois de dias recebe a stamina de cada dia que
passou."""

from __future__ import annotations

from datetime import datetime

from ..domain import gameday
from ..domain.models import PlayerSnapshot
from ..templates.repository import GameTemplates
from . import arena
from .castle import energy_max

WEARY_DAILY = 100  # stamina dada a cada virada, sem passar do máximo
POTION_DAY = 300  # stamina por poção no dia (cliente: 300 - wearyLimit)
# roda da bênção: "Boosts will reset to 10% daily at 5 a.m." (language ExtraBufferSeminaryTips); abre no nível 41
# (SeminaryFrame.BlessAlert). Visto: blessingBuff 10 no login do nível 56; o do nível 11 não traz o campo
BLESS_BASE, BLESS_LEVEL = 10, 41


def roll(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> list[object]:
    """Aplica as viradas pendentes. Devolve o que mudou (para gravar e mandar o 4202), ou vazio."""
    c, changed = snap.character, list[object]()
    if days := gameday.days_between(c.reset_day, now):
        c.reset_day, c.weary_potions = gameday.today(now), 0
        c.weary = max(c.weary, min(c.weary_limit, c.weary + WEARY_DAILY * days))
        if c.grades >= BLESS_LEVEL:
            c.seminary_effect = BLESS_BASE
        changed.append(c)
        if snap.castle is not None:
            snap.castle.energy = max(snap.castle.energy, energy_max(templates))  # comprada a mais não some
            changed.append(snap.castle)
    if snap.arena is not None and snap.arena.day != arena.today(now):
        arena.roll_day(snap.arena, now)
        changed.append(snap.arena)
    return changed
