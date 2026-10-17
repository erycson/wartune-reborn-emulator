"""Formato do pacote (``yishi.comm.PackageOut`` / ``PackageIn``).

Cabeçalho de 20 bytes, big-endian::

    0  int16  magic      = 29099 (0x71AB)
    2  uint16 length     = cabeçalho + corpo
    4  int16  checksum   = (119 + sum(bytes[6:])) & 0x7F7F
    6  int16  code       (opcode)
    8  int32  client_id
    12 int32  extend1
    16 int32  extend2
    20 ...    corpo (protobuf, quando houver)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Final

MAGIC: Final[int] = 29099
HEADER_SIZE: Final[int] = 20
MAX_PACKET_SIZE: Final[int] = 0xFFFF
_HEADER = struct.Struct(">hHhhiii")


class PacketError(ValueError):
    """Pacote malformado."""


def checksum(packet: bytes) -> int:
    return (119 + sum(packet[6:])) & 0x7F7F


@dataclass(frozen=True, slots=True)
class Packet:
    code: int
    body: bytes = b""
    client_id: int = 0
    extend1: int = 0
    extend2: int = 0

    def encode(self) -> bytes:
        length = HEADER_SIZE + len(self.body)
        if length > MAX_PACKET_SIZE:
            raise PacketError(f"pacote {self.code} grande demais: {length} bytes")
        raw = bytearray(
            _HEADER.pack(MAGIC, length, 0, _to_int16(self.code), self.client_id, self.extend1, self.extend2)
        )
        raw += self.body
        struct.pack_into(">H", raw, 4, checksum(raw))
        return bytes(raw)

    @classmethod
    def decode(cls, raw: bytes, *, verify: bool = True) -> Packet:
        if len(raw) < HEADER_SIZE:
            raise PacketError(f"pacote curto: {len(raw)} bytes")
        magic, length, check, code, client_id, ext1, ext2 = _HEADER.unpack_from(raw)
        if magic != MAGIC:
            raise PacketError(f"magic inválido: {magic}")
        if length != len(raw):
            raise PacketError(f"tamanho declarado {length} != recebido {len(raw)}")
        if verify and (check & 0xFFFF) != checksum(raw):
            raise PacketError(f"checksum inválido no pacote {code & 0xFFFF}")
        return cls(code & 0xFFFF, bytes(raw[HEADER_SIZE:]), client_id, ext1, ext2)


def _to_int16(code: int) -> int:
    """Opcodes acima de 32767 (ex.: 0x8xxx) trafegam como int16 com sinal."""
    if not 0 <= code <= 0xFFFF:
        raise PacketError(f"opcode fora do intervalo: {code}")
    return code - 0x10000 if code > 0x7FFF else code
