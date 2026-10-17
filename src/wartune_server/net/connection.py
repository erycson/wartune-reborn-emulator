"""Uma conexão de jogo: leitura, decifragem, despacho e escrita ordenada.

Concorrência (por conexão):

* **leitor** (a corrotina de ``run``): lê bytes, monta pacotes um por vez e
  aguarda o handler de cada um antes do próximo - preserva a ordem do cliente.
* **escritor** (uma tarefa): única dona da cifra de envio. Tudo que sai passa
  por uma fila; a troca de chave também entra na fila para não ultrapassar
  pacotes já enfileirados com a chave antiga.

``send`` nunca bloqueia: enfileira e volta. Se a fila encher (cliente que não
lê), a conexão é encerrada em vez de crescer a memória sem limite.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import Protocol

import structlog
from google.protobuf import text_format
from google.protobuf.message import Message

from ..logging_setup import PACKET_LOGGER
from ..protocol import POLICY_REQUEST, Packet, PacketDecoder, PacketError, StreamCipher
from ..protocol.registry import Direction, MessageRegistry
from .transport import Transport

log = structlog.get_logger(__name__)
packet_log = structlog.get_logger(PACKET_LOGGER)

POLICY_XML = (
    b'<?xml version="1.0"?><!DOCTYPE cross-domain-policy SYSTEM "/xml/dtds/cross-domain-policy.dtd">'
    b'<cross-domain-policy><allow-access-from domain="*" to-ports="*" /></cross-domain-policy>\x00'
)


class ConnectionHandler(Protocol):
    """Camada de jogo que reage à conexão (implementada por ``game.session.GameSession``)."""

    async def on_packet(self, packet: Packet) -> None: ...
    async def on_disconnect(self) -> None: ...


@dataclass(frozen=True, slots=True)
class _Rekey:
    key: bytes


_CLOSE = object()


class Connection:
    def __init__(
        self,
        transport: Transport,
        registry: MessageRegistry,
        *,
        conn_id: int,
        idle_timeout: float = 300.0,
        queue_size: int = 4096,
    ) -> None:
        self.transport = transport
        self.id = conn_id
        self._registry = registry
        self._idle_timeout = idle_timeout
        self._decoder = PacketDecoder(StreamCipher())
        self._send_cipher = StreamCipher()
        self._queue: asyncio.Queue[object] = asyncio.Queue(maxsize=queue_size)
        self._closing = False
        self._log = log.bind(conn=conn_id, peer=transport.peer)
        self.client_id = 0  # vai no cabeçalho dos pacotes enviados (id do jogador)

    @property
    def closing(self) -> bool:
        return self._closing

    # -- API usada pela camada de jogo -------------------------------------------------
    def send(self, packet: Packet) -> None:
        if self._closing:
            return
        try:
            self._queue.put_nowait(packet)
        except asyncio.QueueFull:
            self._log.warning("fila de envio cheia; desconectando cliente lento")
            self.close()

    def send_message(self, code: int, message: Message | None = None, *, extend1: int = 0, extend2: int = 0) -> None:
        body = message.SerializeToString() if message is not None else b""
        self.send(Packet(code, body, self.client_id, extend1, extend2))

    def rekey(self, key: bytes) -> None:
        """Troca a chave das duas direções a partir de agora (após o 20001)."""
        self._decoder.cipher.reset(key)  # recebimento: estamos dentro do leitor, entre pacotes
        self._queue.put_nowait(_Rekey(key))  # envio: em ordem com o que já está na fila

    def close(self) -> None:
        if not self._closing:
            self._closing = True
            with contextlib.suppress(asyncio.QueueFull):
                self._queue.put_nowait(_CLOSE)

    # -- ciclo de vida ------------------------------------------------------------------
    async def run(self, handler: ConnectionHandler) -> None:
        self._log.info("conexão aberta")
        writer = asyncio.create_task(self._writer_loop(), name=f"writer-{self.id}")
        try:
            await self._reader_loop(handler)
        except PacketError as exc:
            self._log.warning("protocolo inválido; desconectando", erro=str(exc))
        except (ConnectionError, OSError) as exc:
            self._log.info("conexão perdida", erro=str(exc))
        except TimeoutError:
            self._log.info("conexão ociosa; desconectando")
        finally:
            self.close()
            try:
                await handler.on_disconnect()
            except Exception:
                self._log.exception("erro em on_disconnect")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(writer, timeout=5)
            if not writer.done():
                writer.cancel()
            await self.transport.close()
            self._log.info("conexão fechada")

    async def _reader_loop(self, handler: ConnectionHandler) -> None:
        first = True
        while not self._closing:
            data = await asyncio.wait_for(self.transport.read(), timeout=self._idle_timeout)
            if not data:
                return
            if first:
                first = False
                if data.startswith(POLICY_REQUEST[:-1]):  # Flash pede a policy na mesma porta
                    self._log.debug("policy-file-request")
                    self._queue.put_nowait(POLICY_XML)
                    self.close()
                    return
            self._decoder.feed(data)
            while not self._closing and (packet := self._decoder.next_packet()) is not None:
                self._log_packet(Direction.CLIENT_TO_SERVER, packet)
                try:
                    await handler.on_packet(packet)
                except Exception:
                    # um handler com bug não derruba a conexão inteira
                    self._log.exception("erro tratando pacote", code=packet.code, nome=self._registry.name(packet.code))

    async def _writer_loop(self) -> None:
        while True:
            item = await self._queue.get()
            if item is _CLOSE:
                return
            if isinstance(item, _Rekey):
                self._send_cipher.reset(item.key)
            elif isinstance(item, Packet):
                self._log_packet(Direction.SERVER_TO_CLIENT, item)
                await self.transport.write(self._send_cipher.encrypt(item.encode()))
            elif isinstance(item, bytes):  # cru, sem cifra (policy)
                await self.transport.write(item)

    def _log_packet(self, direction: Direction, packet: Packet) -> None:
        if not logging.getLogger(PACKET_LOGGER).isEnabledFor(logging.DEBUG):
            return
        try:
            msg = self._registry.decode(packet.code, direction, packet.body)
            text = text_format.MessageToString(msg, as_one_line=True, as_utf8=True)[:2000] if msg else ""
        except Exception:  # corpo que não bate com a mensagem esperada
            msg, text = None, ""
        packet_log.debug(
            "pacote",
            conn=self.id,
            dir=direction.value,
            code=packet.code,
            nome=self._registry.name(packet.code),
            mensagem=type(msg).__name__ if msg else None,
            tamanho=len(packet.body),
            corpo=text or (packet.body[:64].hex() if packet.body else ""),
        )
