"""Caixa por tempo online (5019) e tempo offline (8287), sobre o ``Character``.

Caixa: ``TimeDrop.Grade`` são minutos online no dia (5, 10, ... 180). ``box_period`` é o último
período recebido; o cliente conta ``próximo*60 - timeRun`` e manda o 5019 quando zera.
"""

from __future__ import annotations

from datetime import datetime, time

from ..domain.models import Character
from ..templates.repository import GameTemplates

OFFLINE_MAX = 8 * 3600  # HookRewardFrame: teto de 8 horas


def _box(c: Character, now: datetime, online: bool) -> tuple[int, int]:
    """(período recebido, segundos online hoje) se acumulado até ``now``."""
    # ponytail: o dia vira à meia-noite UTC; sem o horário de reset do servidor oficial
    since, period, seconds = c.box_counted_at, c.box_period, c.box_seconds
    if since is not None and since.date() != now.date():
        period, seconds, since = 0, 0, datetime.combine(now.date(), time(), now.tzinfo)
    if since is not None and online:
        seconds += max(0, int((now - since).total_seconds()))
    return period, seconds


def box_state(c: Character, now: datetime) -> tuple[int, int]:
    """Para mostrar (PlayerMsg e 4) sem gravar: o jogador está online."""
    return _box(c, now, online=True)


def settle_box(c: Character, now: datetime, *, online: bool = True) -> None:
    """Acumula o tempo online; ``online=False`` (login) só fecha o dia, sem contar o tempo fora."""
    c.box_period, c.box_seconds = _box(c, now, online)
    c.box_counted_at = now


def periods(templates: GameTemplates) -> list[int]:
    return sorted({int(r["Grade"]) for r in templates.rows("TimeDrop")})


def next_period(c: Character, templates: GameTemplates) -> int | None:
    return next((p for p in periods(templates) if p > c.box_period), None)


def on_login(c: Character, now: datetime) -> None:
    settle_box(c, now, online=False)
    if c.offline_at is not None:
        away = max(0, int((now - c.offline_at).total_seconds()))
        c.offline_seconds, c.offline_at = min(c.offline_seconds + away, OFFLINE_MAX), None


def on_logout(c: Character, now: datetime) -> None:
    settle_box(c, now)
    c.offline_at = now


def offline_gp(c: Character) -> int:
    # ponytail: dedução, a fórmula do oficial não está no cliente; nível x minutos fora, até 8 horas
    return c.offline_seconds // 60 * c.grades
