"""Servidores de socket: TCP do jogo, policy (843) e ponte WebSocket (Ruffle).

Cada conexão aceita vira uma ``Connection`` + um handler criado pela fábrica
injetada (a camada de jogo) - a rede não conhece regras do jogo.
"""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import Callable

import structlog
from aiohttp import web

from ..protocol.registry import MessageRegistry
from .connection import POLICY_XML, Connection, ConnectionHandler
from .transport import StreamTransport, Transport, WebSocketTransport

log = structlog.get_logger(__name__)

HandlerFactory = Callable[[Connection], ConnectionHandler]


class ConnectionAcceptor:
    """Junta transporte + conexão + handler; compartilhado por TCP e WS."""

    def __init__(self, registry: MessageRegistry, factory: HandlerFactory, idle_timeout: float) -> None:
        self._registry, self._factory, self._idle = registry, factory, idle_timeout
        self._ids = itertools.count(1)
        self._active: set[Connection] = set()

    @property
    def active(self) -> int:
        return len(self._active)

    async def serve(self, transport: Transport) -> None:
        conn = Connection(transport, self._registry, conn_id=next(self._ids), idle_timeout=self._idle)
        self._active.add(conn)
        try:
            await conn.run(self._factory(conn))
        finally:
            self._active.discard(conn)

    def close_all(self) -> None:
        for conn in list(self._active):
            conn.close()

    # -- adaptadores de transporte ----------------------------------------------------
    async def on_tcp(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await self.serve(StreamTransport(reader, writer))

    async def on_websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(max_msg_size=1 << 20)
        await ws.prepare(request)
        await self.serve(WebSocketTransport(ws, request.remote or "?"))
        return ws


async def _policy_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await asyncio.wait_for(reader.read(64), timeout=5)
        writer.write(POLICY_XML)
        await writer.drain()
    except (TimeoutError, ConnectionError, OSError):
        pass
    finally:
        writer.close()


async def start_tcp(acceptor: ConnectionAcceptor, host: str, port: int) -> asyncio.Server:
    server = await asyncio.start_server(acceptor.on_tcp, host, port)
    log.info("socket do jogo ouvindo", host=host, port=port)
    return server


async def start_policy(host: str, port: int) -> asyncio.Server | None:
    """Porta 843 exige admin em alguns sistemas; o Flash cai para a porta do jogo se falhar."""
    try:
        server = await asyncio.start_server(_policy_client, host, port)
    except OSError as exc:
        log.warning("policy server indisponível (o socket do jogo também responde a policy)", port=port, erro=str(exc))
        return None
    log.info("policy server ouvindo", host=host, port=port)
    return server


def websocket_app(acceptor: ConnectionAcceptor) -> web.Application:
    app = web.Application()
    app.router.add_get("/{tail:.*}", acceptor.on_websocket)
    return app
