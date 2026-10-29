"""Peças comuns dos minijogos do operador (caça-níquel, loteria, sorteio de grupo, cadeiras, caça ao tesouro,
minério e quiz): a edição vem de ``game_settings`` (sem a chave, o jogo fica fechado como nas capturas oficiais,
que só mostram o estado fechado), o estado do jogador é JSON num ``EventState`` e o prêmio vai para a mochila ou,
cheia, pelo correio (``shop.place``/``save_with_mail``)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from ...domain import gameday
from ...domain.models import EventState, PlayerSnapshot
from .. import events as ev
from .. import rewards
from ..session import GameSession
from .player import granted
from .shop import place, save_with_mail


def cfg(s: GameSession, key: str) -> Mapping[str, Any]:
    return s.ctx.world.settings.get(key) or {}


def at(c: Mapping[str, Any], name: str) -> datetime:
    """Data da edição em hora do jogo (``YYYY-MM-DD hh:mm:ss``, o formato que o cliente mostra)."""
    return datetime.strptime(str(c[name]), ev.TIME_FMT).replace(tzinfo=gameday.GAME_TZ)


def is_open(c: Mapping[str, Any], now: datetime) -> bool:
    return bool(c) and at(c, "begin") <= now < at(c, "end")


def left_ms(c: Mapping[str, Any], now: datetime) -> int:
    return max(0, int((at(c, "end") - now).total_seconds() * 1000)) if c else 0


def load(snap: PlayerSnapshot, key: str) -> dict[str, Any]:
    st = ev.peek(snap, key)
    data: dict[str, Any] = json.loads(st.text) if st is not None and st.text else {}
    return data


def store(snap: PlayerSnapshot, key: str, data: Mapping[str, Any], now: datetime) -> EventState:
    st = ev.state(snap, key, now)
    st.text, st.updated_at = json.dumps(data), now
    return st


def pairs(raw: Sequence[Sequence[int]]) -> list[tuple[int, int]]:
    return [(int(t), int(n)) for t, n in raw]


async def give(
    s: GameSession, snap: PlayerSnapshot, drops: Sequence[tuple[int, int]], *entities: object, chat: bool = True
) -> str:
    """Moedas e EXP no personagem, itens na mochila (cheia: correio). Grava ``entities`` junto e manda 3/150/109/115
    e o 83 com o ``Received: ...``."""
    templates, now = s.ctx.templates, s.ctx.clock.now()
    rewards.grant(snap, templates, [d for d in drops if d[0] < 0])
    got, letters = place(s, snap, s.player_id, [d for d in drops if d[0] > 0], now)
    await save_with_mail(s, letters, *rewards.owners(snap), *got, *entities)
    text = rewards.text(templates, drops)
    granted(s, drops, got, text, chat=chat)
    return text
