"""Despeja uma captura no formato ``replay_packets.json`` com o corpo protobuf decodificado.

Uma linha por pacote: índice, direção, opcode, nome, extend1/extend2 e a mensagem em texto
(``text_format`` numa linha), ou hex quando o opcode não tem tipo conhecido ou o corpo não decodifica.

Uso::

    uv run python tools/dump_capture.py D:/wartune/server-relay/replay_packets.json --from 100 --to 200
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from google.protobuf import text_format
from google.protobuf.message import DecodeError

from wartune_server.protocol.registry import Direction, MessageRegistry


def describe(registry: MessageRegistry, code: int, direction: Direction, body: bytes) -> str:
    if not body:
        return "(vazio)"
    try:
        msg = registry.decode(code, direction, body)
    except DecodeError:
        msg = None
    if msg is None:
        return f"hex={body.hex()}"
    return f"{type(msg).__name__} {{{text_format.MessageToString(msg, as_one_line=True, as_utf8=True)}}}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--from", dest="start", type=int, default=0, help="índice inicial (inclusivo)")
    parser.add_argument("--to", dest="end", type=int, default=None, help="índice final (inclusivo)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    registry = MessageRegistry.load_default()
    for p in json.loads(args.capture.read_text(encoding="utf-8")):
        if p["index"] < args.start or (args.end is not None and p["index"] > args.end):
            continue
        direction = Direction.CLIENT_TO_SERVER if p["isClient"] else Direction.SERVER_TO_CLIENT
        arrow = "C>S" if p["isClient"] else "S>C"
        body = describe(registry, p["code"], direction, bytes.fromhex(p["bodyHex"]))
        print(f"{p['index']:5} {arrow} {p['code']:5} {registry.name(p['code'])} e={p['extend1']}/{p['extend2']} {body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
