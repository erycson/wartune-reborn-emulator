"""Tabela opcode -> handler, preenchida com ``@router.on(code)``.

O handler recebe a sessão e a mensagem já decodificada (ou ``None`` quando o
opcode não tem corpo). Opcodes sem handler são registrados no log e ignorados.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .session import GameSession

Handler = Callable[["GameSession", Any], Awaitable[None]]


class PacketRouter:
    def __init__(self) -> None:
        self._handlers: dict[int, Handler] = {}

    def on(self, *codes: int) -> Callable[[Handler], Handler]:
        def register(fn: Handler) -> Handler:
            for code in codes:
                if code in self._handlers:
                    raise ValueError(f"opcode {code} já tem handler")
                self._handlers[code] = fn
            return fn

        return register

    def get(self, code: int) -> Handler | None:
        return self._handlers.get(code)


router = PacketRouter()
