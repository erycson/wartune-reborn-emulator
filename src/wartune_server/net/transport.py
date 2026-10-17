"""Transportes de bytes: TCP puro (Flash real) e WebSocket binário (Ruffle ``socketProxy``)."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Protocol

from aiohttp import WSMsgType, web


class Transport(Protocol):
    @property
    def peer(self) -> str: ...
    async def read(self) -> bytes:
        """Próximo bloco recebido; ``b""`` quando o outro lado fechou."""
        ...
    async def write(self, data: bytes) -> None: ...
    async def close(self) -> None: ...


class StreamTransport:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, chunk: int = 65536) -> None:
        self._reader, self._writer, self._chunk = reader, writer, chunk
        peer = writer.get_extra_info("peername")
        self._peer = f"{peer[0]}:{peer[1]}" if peer else "?"

    @property
    def peer(self) -> str:
        return self._peer

    async def read(self) -> bytes:
        return await self._reader.read(self._chunk)

    async def write(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()  # backpressure: não acumula se o cliente não lê

    async def close(self) -> None:
        if not self._writer.is_closing():
            self._writer.close()
        with contextlib.suppress(ConnectionError, OSError):
            await self._writer.wait_closed()


class WebSocketTransport:
    def __init__(self, ws: web.WebSocketResponse, peer: str) -> None:
        self._ws, self._peer = ws, peer

    @property
    def peer(self) -> str:
        return self._peer

    async def read(self) -> bytes:
        while True:
            msg = await self._ws.receive()
            if msg.type == WSMsgType.BINARY:
                return bytes(msg.data)
            if msg.type == WSMsgType.TEXT:
                return str(msg.data).encode()
            if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED, WSMsgType.ERROR):
                return b""

    async def write(self, data: bytes) -> None:
        await self._ws.send_bytes(data)

    async def close(self) -> None:
        if not self._ws.closed:
            await self._ws.close()
