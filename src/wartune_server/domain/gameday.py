"""Hora e dia do jogo.

O relógio do jogo é o fuso do servidor (``GAME_TZ``, de ``Settings.game_timezone``): é nele que o cliente vê o
``sysCurtime``, os horários dos chefes e o ``createDate`` das minas. O dia do jogo vira às 5h desse fuso, não à
meia-noite (cliente: TaskTemplate.checkInRepeatTime; language.txt: "Energy counters are reset daily at 5 am",
"100 Stamina is restored daily at 5:00 A.M.", "Boosts will reset to 10% daily at 5 a.m."). Todo contador diário
usa ``today``/``game_day`` daqui.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

RESET = timedelta(hours=5)  # o dia do jogo começa às 5h


def parse_timezone(text: str) -> tzinfo:
    """``"UTC"``, ``"+03:00"``, ``"UTC-7"`` (deslocamento fixo) ou um nome IANA (``"America/Los_Angeles"``, com
    horário de verão; no Windows vem do pacote ``tzdata``)."""
    text = text.strip()
    if text.upper() == "UTC":
        return UTC
    fixed = re.fullmatch(r"(?:UTC)?([+-])(\d{1,2})(?::?(\d{2}))?", text)
    if fixed is None:
        return ZoneInfo(text)
    sign = -1 if fixed.group(1) == "-" else 1
    return timezone(sign * timedelta(hours=int(fixed.group(2)), minutes=int(fixed.group(3) or 0)))


# Padrão UTC; o oficial inglês segue o horário do Pacífico (troca PDT/PST; captura inglesa #72: fim às 23:59:59).
# ``set_timezone`` na subida (``build_services``). Leia sempre como ``gameday.GAME_TZ`` (o valor é trocado).
GAME_TZ: tzinfo = UTC


def set_timezone(text: str) -> None:
    global GAME_TZ
    GAME_TZ = parse_timezone(text)


def local(at: datetime) -> datetime:
    return at.astimezone(GAME_TZ)


def game_day(at: datetime) -> date:
    """Dia do jogo de um instante (vira às 5h no fuso do jogo)."""
    return (local(at) - RESET).date()


def today(now: datetime) -> str:
    """``"YYYY-MM-DD"`` do dia do jogo: a marca dos contadores diários gravados no banco."""
    return game_day(now).isoformat()


def same_day(a: datetime | None, b: datetime) -> bool:
    return a is not None and game_day(a) == game_day(b)


def day_start(now: datetime) -> datetime:
    """Instante em que o dia do jogo de ``now`` começou (5h no fuso do jogo)."""
    return datetime.combine(game_day(now), time(), GAME_TZ) + RESET


def days_between(earlier: str, now: datetime) -> int:
    """Dias do jogo de ``earlier`` (``today`` gravado) até ``now``; marca vazia conta como 1."""
    if not earlier:
        return 1
    return max(0, (game_day(now) - date.fromisoformat(earlier)).days)
