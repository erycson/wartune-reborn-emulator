"""Remonta pacotes cifrados a partir de um fluxo TCP fragmentado."""

from __future__ import annotations

import struct

from .cipher import StreamCipher
from .packet import HEADER_SIZE, MAGIC, Packet, PacketError

POLICY_REQUEST = b"<policy-file-request/>\x00"


class PacketDecoder:
    """Recebe bytes cifrados e devolve pacotes completos e decifrados.

    O cabeçalho é lido com ``peek`` (sem avançar a chave); a chave só avança
    quando o pacote inteiro chega. Não é thread-safe: um decoder por conexão.
    """

    def __init__(self, cipher: StreamCipher) -> None:
        self._cipher = cipher
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[Packet]:
        self._buffer += data
        packets: list[Packet] = []
        while len(self._buffer) >= HEADER_SIZE:
            magic, length = struct.unpack(">hH", self._cipher.peek(bytes(self._buffer[:4])))
            if magic != MAGIC:
                raise PacketError(f"magic inválido no fluxo: {magic}")
            if length < HEADER_SIZE:
                raise PacketError(f"tamanho inválido no fluxo: {length}")
            if len(self._buffer) < length:
                break
            raw = self._cipher.decrypt(bytes(self._buffer[:length]))
            del self._buffer[:length]
            packets.append(Packet.decode(raw))
        return packets
