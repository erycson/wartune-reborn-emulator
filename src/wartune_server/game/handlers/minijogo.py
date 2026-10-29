"""Peças comuns dos minijogos do operador (caça-níquel, loteria, sorteio de grupo, cadeiras, caça ao tesouro,
minério e quiz): toda regra vem de ``game_settings`` (semeada ligada pela migração 0103; sem a chave, o jogo fica
fechado como nas capturas oficiais, que só mostram o estado fechado), o estado do jogador é JSON num ``EventState`` e
o prêmio vai para a mochila ou, cheia, pelo correio (``shop.place``/``save_with_mail``)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
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
    """Data em hora do jogo (``YYYY-MM-DD hh:mm:ss``, o formato que o cliente mostra)."""
    return datetime.strptime(str(c[name]), ev.TIME_FMT).replace(tzinfo=gameday.GAME_TZ)


def fmt(when: datetime) -> str:
    return gameday.local(when).strftime(ev.TIME_FMT)


def edition(c: Mapping[str, Any], now: datetime) -> tuple[datetime, datetime] | None:
    """(começo, fim) da edição vigente: com ``cycleDays`` a edição se repete a partir de ``begin``; sem ele,
    ``begin``/``end`` fixos. None fora da janela ou sem config."""
    if not c or now < at(c, "begin"):
        return None
    if "cycleDays" in c:
        size = timedelta(days=int(c["cycleDays"]))
        start = at(c, "begin") + size * ((now - at(c, "begin")) // size)
        return start, start + size
    return (at(c, "begin"), at(c, "end")) if now < at(c, "end") else None


def is_open(c: Mapping[str, Any], now: datetime) -> bool:
    return edition(c, now) is not None


def left_ms(c: Mapping[str, Any], now: datetime) -> int:
    ed = edition(c, now)
    return max(0, int((ed[1] - now).total_seconds() * 1000)) if ed else 0


def load(snap: PlayerSnapshot, key: str) -> dict[str, Any]:
    st = ev.peek(snap, key)
    return load_text(st.text if st is not None else "")


def load_text(text: str | None) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(text) if text else {}
    return data


def store(snap: PlayerSnapshot, key: str, data: Mapping[str, Any], now: datetime) -> EventState:
    st = ev.state(snap, key, now)
    st.text, st.updated_at = json.dumps(data), now
    return st


async def shared(s: GameSession, key: str) -> dict[str, Any]:
    """Estado do servidor (veio do minério, avisos da loteria): fica na linha ``key`` de quem o mudou por último, e
    vale a mais nova do servidor (o mesmo jeito da árvore dourada, sem tabela própria)."""
    snap = s.snapshot
    assert snap is not None
    states = await s.ctx.characters.read(lambda uow: uow.events.by_prefix(snap.character.server_id, key))
    rows = [(load_text(st.text), st) for st in states if st.key == key]
    newest = max(rows, key=lambda r: (int(r[0].get("rev", 0)), r[1].updated_at), default=None)
    return newest[0] if newest is not None else {}


def store_shared(snap: PlayerSnapshot, key: str, data: dict[str, Any], now: datetime) -> EventState:
    """Grava o estado do servidor com ``rev`` + 1 (a mais nova é a de maior ``rev``, mesmo com o relógio igual)."""
    return store(snap, key, {**data, "rev": int(data.get("rev", 0)) + 1}, now)


_locks: dict[tuple[int, str], asyncio.Lock] = {}


def lock(s: GameSession, key: str) -> asyncio.Lock:
    """Serializa ler+gravar o estado do servidor ``key`` (o servidor é um processo só)."""
    snap = s.snapshot
    assert snap is not None
    return _locks.setdefault((snap.character.server_id, key), asyncio.Lock())


def pairs(raw: Sequence[Sequence[int]]) -> list[tuple[int, int]]:
    return [(int(t), int(n)) for t, n in raw]


async def give(
    s: GameSession,
    snap: PlayerSnapshot,
    drops: Sequence[tuple[int, int]],
    *entities: object,
    chat: bool = True,
    delete: tuple[object, ...] = (),
) -> str:
    """Moedas e EXP no personagem, itens na mochila (cheia: correio). Grava ``entities`` (e apaga ``delete``) junto e
    manda 3/150/109/115 e o 83 com o ``Received: ...``."""
    templates, now = s.ctx.templates, s.ctx.clock.now()
    rewards.grant(snap, templates, [d for d in drops if d[0] < 0])
    got, letters = place(s, snap, s.player_id, [d for d in drops if d[0] > 0], now)
    await save_with_mail(s, letters, *rewards.owners(snap), *got, *entities, delete=delete)
    text = rewards.text(templates, drops)
    granted(s, drops, got, text, chat=chat)
    return text
