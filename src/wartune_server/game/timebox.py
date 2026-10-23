"""Caixa por tempo online (5019) e tempo offline (8287), sobre o ``Character``.

Caixa: ``TimeDrop.Grade`` são minutos desde o último resgate (5, 10, ... 180). ``box_period`` é o último período
recebido e ``box_seconds`` o tempo contado desde ele (zera a cada resgate); o cliente conta ``próximo*60 - timeRun``
e manda o 5019 quando zera; depois do 180 ele para de pedir (``BoxManager.needCountTime``). *(visto)*
tutorial_en #1594-#1598: a contagem só começa no primeiro 5019 (``timerun`` 0 com o personagem online havia
15 min) e o 4 depois do resgate volta a 0. *(visto, amostra única)* oficial_encantar #131: no login, ``time`` 10 e
``timerun`` 40009 (11 h desde o resgate do 10, atravessando as 05:00 do Pacífico): depois de começada, a corrente
conta também o tempo fora e não zera no dia. As duas regras ficam em ``game_settings.time_box`` (0056).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..domain import gameday
from ..domain.models import Character
from ..templates.repository import GameTemplates

OFFLINE_MAX = 8 * 3600  # HookRewardFrame: teto de 8 horas


@dataclass(frozen=True, slots=True)
class BoxRule:
    """``count_offline``: depois do primeiro período (ou de segundos já contados) o tempo fora conta;
    ``daily_reset``: a corrente recomeça no dia novo do jogo. Padrão = o visto no oficial (#131)."""

    count_offline: bool = True
    daily_reset: bool = False


DEFAULT = BoxRule()


def rule(settings: Mapping[str, Any]) -> BoxRule:
    cfg = settings.get("time_box") or {}
    return BoxRule(bool(cfg.get("count_offline", True)), bool(cfg.get("daily_reset", False)))


def _box(c: Character, now: datetime, online: bool, r: BoxRule) -> tuple[int, int]:
    """(período recebido, segundos contados) se acumulado até ``now``."""
    since, period, seconds = c.box_counted_at, c.box_period, c.box_seconds
    if r.daily_reset and since is not None and not gameday.same_day(since, now):
        period, seconds, since = 0, 0, gameday.day_start(now)
    started = r.count_offline and (period > 0 or seconds > 0)  # conta nova: só depois do primeiro 5019
    if since is not None and (online or started):
        seconds += max(0, int((now - since).total_seconds()))
    return period, seconds


def box_state(c: Character, now: datetime, *, online: bool = True, r: BoxRule = DEFAULT) -> tuple[int, int]:
    """Para mostrar (PlayerMsg e 4) sem gravar; ``online=False`` antes do primeiro 5019 da sessão."""
    return _box(c, now, online, r)


def settle_box(c: Character, now: datetime, *, online: bool = True, r: BoxRule = DEFAULT) -> None:
    """Acumula o tempo; ``online=False`` (login) só conta o tempo fora se ``r.count_offline``."""
    c.box_period, c.box_seconds = _box(c, now, online, r)
    c.box_counted_at = now


def periods(templates: GameTemplates) -> list[int]:
    return sorted({int(r["Grade"]) for r in templates.rows("TimeDrop")})


def next_period(c: Character, templates: GameTemplates) -> int | None:
    return next((p for p in periods(templates) if p > c.box_period), None)


def on_login(c: Character, now: datetime, r: BoxRule = DEFAULT) -> None:
    settle_box(c, now, online=False, r=r)
    if c.offline_at is not None:
        away = max(0, int((now - c.offline_at).total_seconds()))
        c.offline_seconds, c.offline_at = min(c.offline_seconds + away, OFFLINE_MAX), None


def on_logout(c: Character, now: datetime, *, counting: bool = True, r: BoxRule = DEFAULT) -> None:
    """``counting``: a caixa já contava nesta sessão (houve 5019)."""
    settle_box(c, now, online=counting, r=r)
    c.offline_at = now


def offline_gp(c: Character) -> int:
    # ponytail: dedução, a fórmula do oficial não está no cliente; nível x minutos fora, até 8 horas
    return c.offline_seconds // 60 * c.grades
