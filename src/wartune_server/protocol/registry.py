"""Opcode -> classe protobuf, a partir de ``data/opcodes.json`` (gerado por ``tools/scan_opcodes.py``)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib import resources

from google.protobuf.message import Message

from .messages import wartune_pb2

EMPTY_BODY = "(vazio)"


class Direction(StrEnum):
    CLIENT_TO_SERVER = "c2s"
    SERVER_TO_CLIENT = "s2c"


@dataclass(frozen=True, slots=True)
class OpcodeInfo:
    code: int
    names: tuple[str, ...]
    c2s: tuple[str, ...]
    s2c: tuple[str, ...]

    @property
    def name(self) -> str:
        return self.names[0] if self.names else f"0x{self.code:04X}"


class MessageRegistry:
    """Consulta somente leitura; seguro para compartilhar entre corrotinas."""

    def __init__(self, table: dict[int, OpcodeInfo]) -> None:
        self._table = table

    @classmethod
    def load_default(cls) -> MessageRegistry:
        return _default_registry()

    def info(self, code: int) -> OpcodeInfo | None:
        return self._table.get(code)

    def name(self, code: int) -> str:
        info = self._table.get(code)
        return info.name if info else f"0x{code:04X}"

    def message_type(self, code: int, direction: Direction) -> type[Message] | None:
        info = self._table.get(code)
        if info is None:
            return None
        names = info.c2s if direction is Direction.CLIENT_TO_SERVER else info.s2c
        for name in names:
            if name != EMPTY_BODY and not name.startswith("?"):
                return message_class(name)
        return None

    def decode(self, code: int, direction: Direction, body: bytes) -> Message | None:
        cls = self.message_type(code, direction)
        if cls is None:
            return None
        msg = cls()
        msg.ParseFromString(body)
        return msg


def message_class(proto_name: str) -> type[Message]:
    cls = getattr(wartune_pb2, proto_name, None)
    if cls is None:
        raise KeyError(f"mensagem protobuf desconhecida: {proto_name}")
    return cls  # type: ignore[no-any-return]


@cache
def _default_registry() -> MessageRegistry:
    raw = json.loads(resources.files(__package__).joinpath("data/opcodes.json").read_text(encoding="utf-8"))
    table = {
        int(code): OpcodeInfo(int(code), tuple(v["names"]), tuple(v["c2s"]), tuple(v["s2c"]))
        for code, v in raw.items()
    }
    return MessageRegistry(table)
