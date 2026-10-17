"""Remonta pacotes cifrados a partir de um fluxo TCP fragmentado."""

from __future__ import annotations

import struct

from .cipher import StreamCipher
from .packet import HEADER_SIZE, MAGIC, Packet, PacketError

POLICY_REQUEST = b"<policy-file-request/>\x00"


class PacketDecoder:
    """Recebe bytes cifrados e devolve pacotes completos e decifrados, **um por vez**.

    Um por vez porque a chave pode mudar entre dois pacotes que chegaram juntos
    (o cliente troca a chave logo depois de enviar o 20001): quem consome decide,
    a cada pacote, se troca a chave antes de pedir o próximo.

    O cabeçalho é lido com ``peek`` (sem avançar a chave); a chave só avança
    quando o pacote inteiro chega. Não é thread-safe: um decoder por conexão.
    """

    def __init__(self, cipher: StreamCipher) -> None:
        self._cipher = cipher
        self._buffer = bytearray()

    @property
    def cipher(self) -> StreamCipher:
        return self._cipher

    @property
    def buffered(self) -> int:
        return len(self._buffer)

    def feed(self, data: bytes) -> None:
        self._buffer += data

    def next_packet(self) -> Packet | None:
        if len(self._buffer) < HEADER_SIZE:
            return None
        magic, length = struct.unpack(">hH", self._cipher.peek(bytes(self._buffer[:4])))
        if magic != MAGIC:
            raise PacketError(f"magic inválido no fluxo: {magic}")
        if length < HEADER_SIZE:
            raise PacketError(f"tamanho inválido no fluxo: {length}")
        if len(self._buffer) < length:
            return None
        raw = self._cipher.decrypt(bytes(self._buffer[:length]))
        del self._buffer[:length]
        return Packet.decode(raw)

    def drain(self) -> list[Packet]:
        """Todos os pacotes completos com a chave atual (útil em testes)."""
        out: list[Packet] = []
        while (packet := self.next_packet()) is not None:
            out.append(packet)
        return out
