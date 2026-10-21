"""Gera ``proto/wartune.proto`` a partir das classes netease-protobuf decompiladas.

A fonte da verdade é o ``readFromSlice`` de cada classe (é ele que decodifica o
que o servidor envia). O ``writeToBuffer`` do cliente tem bugs (tags repetidas em
``PlayerMsg`` e ``ChatChannelMsg``), por isso não é usado.

O leitor é um ``switch`` sobre ``tag >>> 3`` (às vezes com ``- 1`` ou ``- 2``);
cada ``case`` tem uma das formas::

    nome = ReadUtils.read$TYPE_X(param1);                       // escalar
    nome.push(ReadUtils.read$TYPE_X(param1));                   // escalar repetido
    ReadUtils.readPackedRepeated(param1, read$TYPE_X, nome);    // idem, empacotado
    nome = new T(); ReadUtils.read$TYPE_MESSAGE(param1, nome);  // mensagem
    _locN_ = new T(); read$TYPE_MESSAGE(param1, _locN_); nome.push(_locN_);  // mensagem repetida

Uso::

    uv run python tools/as3_to_proto.py <pastas scripts/ do cliente inglês: decomp/2, decomp/m3..m18, decomp/Loading>

(o comando completo está em docs/ferramentas.md)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROTO_ROOT = ("com", "road", "yishi", "proto")
SCALARS = {
    "INT32": "int32",
    "INT64": "int64",
    "UINT32": "uint32",
    "STRING": "string",
    "BOOL": "bool",
    "BYTES": "bytes",
    "FLOAT": "float",
    "DOUBLE": "double",
}

RE_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)", re.M)
RE_CLASS = re.compile(r"class\s+(\w+)\s+extends\s+Message")
RE_IMPORT = re.compile(r"^\s*import\s+([\w.]+);", re.M)
RE_READ_FN = re.compile(
    r"function\s+readFromSlice\(param1:IDataInput,\s*param2:uint\)\s*:\s*void\s*\{(.*?)\n      \}", re.S
)
RE_SWITCH = re.compile(r"switch\(.*?>>>\s*3\)(?:\s*-\s*(\d+)\))?")
RE_CASE = re.compile(r"case\s+(\d+):(.*?)(?=case\s+\d+:|default:)", re.S)
RE_RD_REP_MSG = re.compile(
    r"=\s*new\s+([\w.]+)\(\);\s*ReadUtils\.read\$TYPE_MESSAGE\(param1,\s*_loc\d+_\);\s*(\w+)\.push"
)
RE_RD_MSG = re.compile(r"(\w+)\s*=\s*new\s+([\w.]+)\(\);\s*ReadUtils\.read\$TYPE_MESSAGE\(param1,\s*\1\)")
RE_RD_PACKED = re.compile(r"readPackedRepeated\(param1,\s*ReadUtils\.read\$TYPE_(\w+),\s*(\w+)\)")
RE_RD_PUSH = re.compile(r"(\w+)\.push\(ReadUtils\.read\$TYPE_(\w+)\(param1\)\)")
RE_RD_SCALAR = re.compile(r"(\w+)\s*=\s*ReadUtils\.read\$TYPE_(\w+)\(param1\)")


@dataclass
class Field:
    number: int
    name: str
    type: str  # escalar proto ou FQN AS3 da mensagem
    repeated: bool
    is_message: bool


@dataclass
class MessageDef:
    fqn: str
    package: str
    name: str
    fields: list[Field] = field(default_factory=list)
    proto_name: str = ""


def parse_class(path: Path) -> MessageDef | None:
    src = path.read_text(encoding="utf-8", errors="replace")
    cls = RE_CLASS.search(src)
    pkg = RE_PACKAGE.search(src)
    if not cls or not pkg:
        return None
    package, name = pkg.group(1), cls.group(1)
    imports = {imp.rsplit(".", 1)[-1]: imp for imp in RE_IMPORT.findall(src)}

    def resolve(type_name: str) -> str:
        if "." in type_name:
            return type_name
        return imports.get(type_name, f"{package}.{type_name}")

    msg = MessageDef(f"{package}.{name}", package, name)
    reader = RE_READ_FN.search(src)
    if not reader:
        return msg
    body = reader.group(1)
    switch = RE_SWITCH.search(body)
    if not switch:
        if "case " in body:
            raise ValueError(f"{path}: readFromSlice com cases mas switch nao reconhecido")
        return msg
    offset = int(switch.group(1) or 0)
    seen: set[int] = set()
    for case, block in RE_CASE.findall(body[switch.end() :]):
        number = int(case) + offset
        if number in seen:
            continue
        parsed = _parse_case(block)
        if parsed is None:
            raise ValueError(f"{path}: case {case} nao reconhecido:\n{block}")
        fname, kind, ftype, repeated = parsed
        seen.add(number)
        if kind == "MESSAGE":
            msg.fields.append(Field(number, fname, resolve(ftype), repeated, True))
        elif kind in SCALARS:
            msg.fields.append(Field(number, fname, SCALARS[kind], repeated, False))
        else:
            raise ValueError(f"{path}: tipo desconhecido {kind}")
    return msg


def _parse_case(block: str) -> tuple[str, str, str, bool] | None:
    if m := RE_RD_REP_MSG.search(block):
        return m.group(2), "MESSAGE", m.group(1), True
    if m := RE_RD_MSG.search(block):
        return m.group(1), "MESSAGE", m.group(2), False
    if m := RE_RD_PACKED.search(block):
        return m.group(2), m.group(1), "", True
    if m := RE_RD_PUSH.search(block):
        return m.group(1), m.group(2), "", True
    if m := RE_RD_SCALAR.search(block):
        return m.group(1), m.group(2), "", False
    return None


def collect(roots: list[Path]) -> dict[str, MessageDef]:
    messages: dict[str, MessageDef] = {}
    for root in roots:
        base = root.joinpath(*PROTO_ROOT)
        for path in sorted(base.rglob("*.as")):
            msg = parse_class(path)
            if msg is None:
                continue
            old = messages.get(msg.fqn)
            if old and len(old.fields) >= len(msg.fields):
                continue  # mantém a definição mais completa entre os módulos
            messages[msg.fqn] = msg
    return messages


def assign_proto_names(messages: dict[str, MessageDef]) -> None:
    by_name: dict[str, list[MessageDef]] = {}
    for msg in messages.values():
        by_name.setdefault(msg.name, []).append(msg)
    for name, group in by_name.items():
        for msg in group:
            sub = msg.package.split(".")[-1]
            msg.proto_name = name if len(group) == 1 else f"{sub.capitalize()}{name}"


def render(messages: dict[str, MessageDef]) -> str:
    lines = [
        "// GERADO por tools/as3_to_proto.py a partir do cliente decompilado. Nao edite.",
        'syntax = "proto2";',
        "package wartune;",
        "",
    ]
    for msg in sorted(messages.values(), key=lambda m: m.proto_name):
        lines.append(f"// {msg.fqn}")
        lines.append(f"message {msg.proto_name} {{")
        for f in sorted(msg.fields, key=lambda x: x.number):
            if f.is_message:
                target = messages.get(f.type)
                if target is None:
                    raise ValueError(f"{msg.fqn}.{f.name}: mensagem {f.type} ausente")
                ftype = target.proto_name
            else:
                ftype = f.type
            label = "repeated" if f.repeated else "optional"
            lines.append(f"  {label} {ftype} {f.name} = {f.number};")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="pastas scripts/ do FFDec")
    parser.add_argument("--out", type=Path, default=Path("proto/wartune.proto"))
    parser.add_argument("--index", type=Path, default=Path("proto/message_index.json"))
    args = parser.parse_args()

    messages = collect(args.roots)
    assign_proto_names(messages)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(messages), encoding="utf-8")
    index = {fqn: m.proto_name for fqn, m in sorted(messages.items())}
    args.index.write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"{len(messages)} mensagens -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
