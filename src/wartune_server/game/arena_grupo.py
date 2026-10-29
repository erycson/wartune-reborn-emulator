"""Pontos e ranking da arena em grupo (lógica pura; as lutas em ``handlers/arena_grupo.py``).

O cliente mostra estes pontos como ``crossScore`` (``PlayerMsg``) e o ranking no ``PvpHeroFrame``, que baixa
``cross/crossscore.xml`` (``CrossScoreTotalAdd`` com ``weekScore``, lido pelo ``SortController.read``): é o ranking
semanal do PvP de partida (o mesmo ``match`` do painel do dia que a luta da sala PvP soma, 27/10 #19932).
``game_settings.arena_party`` (migração 0107): ``win_points``, ``lose_points`` e ``reset`` ("week" ou "never").
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ..domain.models import EventState, PlayerSnapshot
from . import events as ev

KEY = "arena_party"  # event_state: value = pontos, text = período dos pontos, updated_at = quando chegou neles


def period(now: datetime, cfg: Mapping[str, Any]) -> str:
    """Semana ISO (o ``PvpHeroFrame`` é semanal) ou "" sem reset."""
    if cfg.get("reset", "week") != "week":
        return ""
    year, week, _ = now.isocalendar()
    return f"{year}-{week:02d}"


def points(st: EventState | None, now: datetime, cfg: Mapping[str, Any]) -> int:
    return st.value if st is not None and st.text == period(now, cfg) else 0


def add(snap: PlayerSnapshot, won: bool, now: datetime, cfg: Mapping[str, Any]) -> tuple[EventState, int]:
    """Vitória soma ``win_points``, derrota tira ``lose_points``, sem ficar negativo. Devolve a linha e o que mudou."""
    st = ev.state(snap, KEY, now)
    before = points(st, now, cfg)
    delta = int(cfg.get("win_points", 0)) if won else -int(cfg.get("lose_points", 0))
    after = max(0, before + delta)
    st.value, st.text = after, period(now, cfg)
    if after != before:
        st.updated_at = now  # desempate: quem chegou antes nos mesmos pontos fica na frente
    return st, after - before


REWARD_KEY = "cross_score_reward"  # event_state: text = período do prêmio já resgatado (8590)
MIN_POINTS, TITLE_TOP = 1000, 20  # (cliente) pvpHeroFrame.rewardTip: 1000 pontos dão a marca; top 20 com 1000, título


def can_claim(snap: PlayerSnapshot, now: datetime, cfg: Mapping[str, Any], cross: Mapping[str, Any]) -> bool:
    """Prêmio dos pontos entre servidores (4481/8590): ``min_points`` no período e ainda não resgatado nele."""
    done = ev.peek(snap, REWARD_KEY)
    claimed = done is not None and done.text == period(now, cfg)
    return not claimed and points(ev.peek(snap, KEY), now, cfg) >= int(cross.get("min_points", MIN_POINTS))


def ranked(states: list[EventState], now: datetime, cfg: Mapping[str, Any]) -> list[tuple[int, int]]:
    """(personagem, pontos) com pontos no período, do maior ao menor; empate: quem chegou antes."""
    rows = [(e, points(e, now, cfg)) for e in states if e.key == KEY]
    rows = [(e, p) for e, p in rows if p > 0]
    rows.sort(key=lambda x: (-x[1], x[0].updated_at, x[0].character_id))
    return [(e.character_id, p) for e, p in rows]


def position(states: list[EventState], character_id: int, now: datetime, cfg: Mapping[str, Any]) -> int:
    """Posição no ranking (1 = primeiro); 0 fora dele."""
    ids = [c for c, _ in ranked(states, now, cfg)]
    return ids.index(character_id) + 1 if character_id in ids else 0
