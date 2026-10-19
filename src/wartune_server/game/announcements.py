"""Anúncios agendados do servidor (``scheduled_announcements``, migração 0036): no horário configurado, um 83 para
todos os jogadores online. O relógio é o 20008 do cliente (~60 s), como o fim das janelas do chefe do mundo.

Regras e como editar em ``docs/eventos.md`` (seção "Anúncios agendados").
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..domain import gameday
from ..domain.world import Announcement

# Horário perdido há mais que isso não sai mais: sem ninguém online por horas, o próximo 20008 não despeja todos os
# anúncios atrasados. Um pouco mais que o intervalo do 20008 (~60 s).
LATE = timedelta(minutes=2)


def due(announcements: Iterable[Announcement], since: datetime, now: datetime) -> list[Announcement]:
    """Os anúncios com horário em ``(since, now]`` (hora do jogo, ``gameday.GAME_TZ``), na ordem do id."""
    today = gameday.local(now).date()
    out = []
    for a in announcements:
        for day in (today - timedelta(days=1), today):  # ontem: o intervalo pode cruzar a meia-noite
            if a.weekdays and day.isoweekday() not in a.weekdays:
                continue
            if any(since < datetime.combine(day, t, gameday.GAME_TZ) <= now for t in a.times):
                out.append(a)
                break
    return out


@dataclass
class Announcer:
    """Quando foi a última conferência (um só por servidor, em ``GameContext``). Sem persistir: um restart perde no
    máximo os anúncios do tempo em que o servidor ficou fora."""

    checked_at: datetime | None = None

    def tick(self, announcements: Iterable[Announcement], now: datetime) -> list[Announcement]:
        """O que sai agora; cada horário sai uma vez só, mesmo com vários jogadores mandando 20008."""
        since = max(self.checked_at or datetime.min.replace(tzinfo=UTC), now - LATE)
        self.checked_at = now
        return due(announcements, since, now) if since < now else []
