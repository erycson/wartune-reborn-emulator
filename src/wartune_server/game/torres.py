"""Torres 8200-8204: Tower of Kings (``SonTypes`` 300, ``DifficultyGrade`` 1-4) e The Spire (8201, ``SonTypes`` 301).

As duas são masmorras em grupo (``Capacity`` 4, sala) com mapa gerado (migração 0102). Do cliente:

- Tower of Kings: uma entrada por dia (``KingTowerInfo.maxKingCount`` 1; "Already entered the Tower of Kings
  today!"); a dificuldade N só abre com a N-1 vencida ("Clear {0} to enter"); ``KingTowerInfoMsg`` (4900) com
  ``enterCount``, ``maxIndex`` (a maior dificuldade vencida), e no fim ``currentStep`` (a dificuldade),
  ``currentIndex`` (o andar, "Tower of Kings L{1}") e ``rewardCount`` ("obtained REWARD x{2}").
- The Spire: "Each player may only challenge the Spire once per day" (``PlayerMsg.trialCount``/``trialMaxCount``);
  "rewarded according to the stages you've completed"; o andar é a onda da luta (``battle.layer``).
- Prêmio: a coluna ``Item`` da campanha (``-700`` EXP e o baú: 2131002-2131005 dos reis, 2060045 da Spire).

TODO(inventado): andares = lutas vencidas no mapa (King) e ondas vencidas (Spire); um baú por andar da King e um
baú da Spire a cada 5 andares (mínimo 1); a EXP do ``-700`` fica nas lutas (sem número no cliente).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ..domain import gameday
from ..domain.models import EventState, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from . import events as ev

KING, SPIRE = 300, 301  # Campaigns.SonTypes
MAX_PER_DAY = 1  # KingTowerInfo.maxKingCount; PlayerMsg.trialMaxCount (builders/login)
SPIRE_LEED = 28  # LeedTemp "Enter the Spire" (PassCount 1): a devoção da entrada (handlers/events.leed_done)
KING_KEY, KING_MAX_KEY = "king_tower", "king_tower:max"  # entradas de hoje; maior dificuldade vencida
DAILY = {KING: KING_KEY, SPIRE: "spire"}  # EventState diário (``recover`` lê o "spire": Recuperar EXP sonType 5)
SPIRE_TOTAL = "spire:total"  # entradas na Spire desde sempre (guia de 7 dias, condição 23 ENTER_CAMPAIGN)
SPIRE_PER_CHEST = 5  # TODO(inventado)


def son(row: Mapping[str, Any]) -> int:
    """300/301 nas torres, 0 fora delas."""
    kind = int(row.get("SonTypes") or 0)
    return kind if kind in DAILY else 0


def used(snap: PlayerSnapshot, kind: int, now: datetime) -> int:
    """Entradas de hoje na torre ``kind``."""
    st = ev.peek(snap, DAILY[kind])
    return st.value if st is not None and gameday.same_day(st.updated_at, now) else 0


def best(snap: PlayerSnapshot) -> int:
    st = ev.peek(snap, KING_MAX_KEY)
    return st.value if st is not None else 0


def unlocked(snap: PlayerSnapshot, row: Mapping[str, Any]) -> bool:
    """Tower of Kings: a dificuldade N pede a N-1 vencida ("Clear {0} to enter"); a Spire abre sempre."""
    return son(row) != KING or best(snap) >= int(row.get("DifficultyGrade") or 1) - 1


def enter(snap: PlayerSnapshot, row: Mapping[str, Any], now: datetime) -> tuple[bool, list[EventState]]:
    """Gasta a entrada do dia se ainda houver. Devolve (com prêmio?, linhas a gravar)."""
    kind = son(row)
    st = ev.daily(snap, DAILY[kind], now)
    if st.value >= MAX_PER_DAY:
        return False, []
    st.value, st.updated_at = st.value + 1, now
    rows = [st]
    if kind == SPIRE:
        total = ev.state(snap, SPIRE_TOTAL, now)
        total.value, total.updated_at = total.value + 1, now
        rows.append(total)
    return True, rows


def chest(row: Mapping[str, Any]) -> int:
    """O baú da coluna ``Item`` (``-700,2131002``)."""
    return next((int(x) for x in str(row.get("Item", "")).split(",") if x and int(x) > 0), 0)


def prize(row: Mapping[str, Any], floors: int) -> list[tuple[int, int]]:
    """Os baús pelos andares vencidos (TODO(inventado) a quantidade)."""
    if floors <= 0 or not (tid := chest(row)):
        return []
    n = floors if son(row) == KING else max(1, floors // SPIRE_PER_CHEST)
    return [(tid, n)]


def finish(snap: PlayerSnapshot, row: Mapping[str, Any], now: datetime) -> list[EventState]:
    """King vencida: grava a maior dificuldade."""
    if son(row) != KING:
        return []
    st = ev.state(snap, KING_MAX_KEY, now)
    st.value, st.updated_at = max(st.value, int(row.get("DifficultyGrade") or 1)), now
    return [st]


def king_msg(snap: PlayerSnapshot, now: datetime, **end: int) -> pb.KingTowerInfoMsg:
    """4900: entradas de hoje e a maior dificuldade; ``end`` (currentIndex, currentStep, rewardCount) no fim."""
    return pb.KingTowerInfoMsg(enterCount=used(snap, KING, now), maxIndex=best(snap), **end)
