"""Defend Sylph Atoll (invasão da ilha dos pets): janela, andar e contadores.

Horas, tetos e fúria vêm do ``ConfigInfos`` (``pet_island_defend_hour`` 1,4,7,...,22, ``_reward_count`` 20,10,1,
``_boss_rage`` 100, ``_rage_add`` 2,5), os mesmos que o cliente usa (``PetBossModel``). *(visto)* oficial_encantar
#43, #866, #2337: a janela abre na hora cheia do fuso do jogo e dura 1 h (07:39 PDT ``leftTime`` 1242307 até as
08:00; 10:00:16 com 3584000 até as 11:00), no andar 20002 com o chefe 5102 e no 20004 com o 5104
(``bossId`` = 5100 + andar). Duração e andares ficam em ``game_settings.pet_island_defend`` (0057): só o 20001 tem
nós (``content/petisland.json``), então o padrão sorteia só ele.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from ..domain import gameday
from ..domain.models import EventState, PlayerSnapshot
from ..templates.repository import GameTemplates
from . import events as ev

BOSS_BASE, FLOOR_BASE = 5100, 20000
COUNT_KEYS = ("pet_defend:middle", "pet_defend:high", "pet_defend:boss")  # EventState diário (05:00)
MIDDLE, HIGH, BOSS = range(3)  # índice em COUNT_KEYS, ``max_counts`` e ``rewards``
REWARD_KEYS = ("middle", "high", "boss")


def _ints(templates: GameTemplates, name: str, default: str) -> list[int]:
    return [int(v) for v in ev.config(templates, name, default).split(",") if v.strip()]


def hours(templates: GameTemplates) -> list[int]:
    return _ints(templates, "pet_island_defend_hour", "1,4,7,10,13,16,19,22")


def max_counts(templates: GameTemplates) -> list[int]:
    return _ints(templates, "pet_island_defend_reward_count", "20,10,1")


def max_rage(templates: GameTemplates) -> int:
    return int(ev.config(templates, "pet_island_defend_boss_rage", "100") or 100)


def rage_add(templates: GameTemplates, kind: int) -> int:
    """Fúria por vitória: ``pet_island_defend_rage_add`` (avançado, sofisticado); o chefe não soma."""
    adds = _ints(templates, "pet_island_defend_rage_add", "2,5")
    return adds[kind] if kind < len(adds) else 0


def kind(hero_id: int) -> int | None:
    """Herói do nó 1003: 7511x avançado (Fire/Water/Electro/Wind), 7512x sofisticado, 5101-5108 o chefe."""
    if hero_id // 10 == 7511:
        return MIDDLE
    if hero_id // 10 == 7512:
        return HIGH
    if BOSS_BASE < hero_id <= BOSS_BASE + 8:
        return BOSS
    return None


def drops(settings: Mapping[str, Any], kind: int) -> list[tuple[int, int]]:
    return [(int(t), int(n)) for t, n in (cfg(settings).get("rewards") or {}).get(REWARD_KEYS[kind], [])]


def count_state(snap: PlayerSnapshot, kind: int, now: datetime) -> EventState:
    return ev.daily(snap, COUNT_KEYS[kind], now)


def cfg(settings: Mapping[str, Any]) -> Mapping[str, Any]:
    return settings.get("pet_island_defend") or {}


def window(
    templates: GameTemplates, settings: Mapping[str, Any], now: datetime
) -> tuple[datetime, datetime, int] | None:
    """(início, fim, andar) da invasão aberta agora, ou ``None``. O andar é sorteado por janela (semente = início)."""
    c = cfg(settings)
    floors = [int(f) for f in c.get("floors", [FLOOR_BASE + 1])]
    duration = timedelta(seconds=int(c.get("duration", 3600)))
    local = gameday.local(now)
    for h in hours(templates):
        for day in (0, -1):  # a janela das 23h, se houvesse, passaria da meia-noite
            start = local.replace(hour=h, minute=0, second=0, microsecond=0) + timedelta(days=day)
            if floors and start <= local < start + duration:
                return start, start + duration, random.Random(int(start.timestamp())).choice(floors)
    return None


def boss_id(map_id: int) -> int:
    return BOSS_BASE + map_id - FLOOR_BASE


def counts(snap: PlayerSnapshot, now: datetime) -> list[int]:
    """Vitórias com prêmio hoje (avançado, sofisticado, chefe): ``PetBossInfoView`` mostra contra ``max_counts``."""
    out = []
    for key in COUNT_KEYS:
        st = ev.peek(snap, key)
        out.append(st.value if st is not None and gameday.same_day(st.updated_at, now) else 0)
    return out
