"""Sessões de login pendentes: ligam o ``POST /login`` (HTTP) ao pacote 20001 (TCP).

No ``/login`` o cliente manda ``tempPassword`` cifrado; no TCP ele manda
``key = md5(tempPassword)``. Guardamos a sessão pela ``key`` até o socket chegar.
Também é por essa ``key`` que ``visualizeregister``/``updateplayernovice`` são
autenticados (o cliente envia ``key=_userInfo.key``).

A implementação em memória basta enquanto HTTP e TCP rodam no mesmo processo;
para separar processos, troque por uma implementação em Redis/banco.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Protocol

from .clock import Clock


@dataclass(frozen=True, slots=True)
class PendingLogin:
    key: str
    account_id: int
    username: str
    server_id: int
    character_id: int | None
    last_seen_at: datetime  # TTL deslizante: renovado a cada uso


class LoginSessionStore(Protocol):
    def put(self, session: PendingLogin) -> None: ...
    def get(self, key: str) -> PendingLogin | None: ...
    def attach_character(self, key: str, character_id: int) -> PendingLogin | None: ...


class InMemoryLoginSessionStore:
    """Não precisa de trava: só é usado de dentro do event loop (uma thread)."""

    def __init__(self, clock: Clock, ttl_seconds: int) -> None:
        self._clock = clock
        self._ttl = timedelta(seconds=ttl_seconds)
        self._items: dict[str, PendingLogin] = {}

    def put(self, session: PendingLogin) -> None:
        self._purge()
        self._items[session.key] = session

    def get(self, key: str) -> PendingLogin | None:
        self._purge()
        session = self._items.get(key)
        if session is not None:
            # a criação do personagem e a carga do cliente podem levar minutos entre os usos
            session = self._items[key] = replace(session, last_seen_at=self._clock.now())
        return session

    def attach_character(self, key: str, character_id: int) -> PendingLogin | None:
        session = self.get(key)
        if session is None:
            return None
        updated = replace(session, character_id=character_id)
        self._items[key] = updated
        return updated

    def _purge(self) -> None:
        limit = self._clock.now() - self._ttl
        for key in [k for k, s in self._items.items() if s.last_seen_at < limit]:
            del self._items[key]
