"""Mapeia opcode -> mensagem protobuf varrendo o cliente decompilado.

* Servidor -> cliente: ``addEventListener("SLGSocketEvent" + N, handler)`` e, no
  corpo do ``handler``, o ``readBody(...)`` diz qual mensagem é lida.
* Cliente -> servidor: na função que faz ``new PackageOut(N)``, a mensagem passada
  a ``sendProtoBuffer``/``sendProtobuffer``.
* Transações (``getCode()`` retornando N) contam como listener de N com os ``readBody`` da classe.
* Nomes vêm de ``ProtocolType.as`` (C→S) e ``AcceptProtocolType.as`` (S→C).
* O que a varredura estática não alcança fica em ``SPECIAL_S2C``/``SPECIAL_C2S``.

Gera ``proto/opcodes.json`` e ``docs/packets.md``.

Uso::

    uv run python tools/scan_opcodes.py D:/wartune/decompiled/m2/scripts D:/wartune/decompiled/m3/scripts \
        D:/wartune/decompiled/m4/scripts D:/wartune/decompiled/m5/scripts D:/wartune/decompiled/m8/scripts \
        D:/wartune/decompiled/m10/scripts D:/wartune/decompiled/m11/scripts \
        D:/wartune/decompiled/m15/scripts D:/wartune/decompiled/m16/scripts
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

RE_IMPORT = re.compile(r"^\s*import\s+([\w.]+);", re.M)
RE_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)", re.M)
RE_FUNC = re.compile(r"function\s+(?:get\s+|set\s+)?(\w+)\s*\(")
RE_LISTEN = re.compile(r'(?:addEventListener\("SLGSocketEvent"\s*\+\s*|\.listener\(\s*)(\d+),\s*(\w+)')
RE_READ_NEW = re.compile(r"readBody\(\s*new\s+([\w.]+)\(\)\s*\)")
RE_READ_VAR = re.compile(r"readBody\(\s*(\w+)\s*\)")
RE_PKG_OUT = re.compile(r"new\s+PackageOut\(\s*(\d+)")
# Os dois argumentos: wrappers locais invertem a ordem (``sendProtoBuffer(msg, pkg)``).
RE_SEND = re.compile(r"send[Pp]roto[Bb]uffer\(\s*(new\s+[\w.]+\(\)|\w+|null)\s*,\s*(new\s+[\w.]+\(\)|\w+|null)")
# Repasse: ``f(param1)`` ou callback passado como último argumento (``addPkgToBuffer(pkg, cena, f)``).
RE_DELEGATE = re.compile(r"(\w+)\(\s*param1\s*\)|,\s*(\w+)\s*\)")
RE_CONST = re.compile(r"public\s+static\s+const\s+(\w+)\s*:\s*u?int\s*=\s*(\d+)\s*;")
RE_GETCODE = re.compile(r"function\s+getCode\(\)\s*:\s*int\s*\{\s*return\s+(\d+)\s*;")

# Casos especiais de yishi/service/managers/SocketManager.as (__chatSocketData): esses opcodes não viram
# "SLGSocketEvent" + N. 157 e a família GAME_CMD (153, 156, 69, 77, 4149, 4361, 4600) caem em transações
# com getCode() e são achados pela varredura; 159 e 171 não têm readBody conhecido. Valores: FQN AS3.
SPECIAL_S2C = {
    140: "com.road.yishi.proto.army.MapUpdatedMsg",  # SocketManager.mapDataSync
    143: "com.road.yishi.proto.player.PlayerMovieMsg",  # "U_PLAY_MOVIE" -> map/space/manager/SpaceSocketManager.as
    154: "com.road.yishi.proto.battle.PrepareOverMsg",  # battle/transaction/VictoryFailTransaction.as
    72: "com.road.yishi.proto.battle.ReinforceMsg",  # ReinfoTransaction -> battle/handler/ReinforceHandler.as
}
# Opcode passado em variável: SocketSendManager.sendLoadOverByType(10007 | 10018, ...).
SPECIAL_C2S = {
    10007: "com.road.yishi.proto.battle.LoadOverMsg",
    10018: "com.road.yishi.proto.battle.LoadOverMsg",
}


def split_functions(src: str) -> dict[str, str]:
    """Divide o arquivo em corpos de função (aproximação por posição de 'function')."""
    starts = [(m.start(), m.group(1)) for m in RE_FUNC.finditer(src)]
    bodies: dict[str, str] = {}
    for i, (pos, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(src)
        bodies.setdefault(name, src[pos:end])
    return bodies


def var_type(body: str, var: str) -> str | None:
    m = re.search(rf"(?:var\s+|\(|,\s*){re.escape(var)}\s*:\s*([\w.]+)", body)
    if m and m.group(1) not in ("*", "Object", "Message"):
        return m.group(1)
    if m := re.search(rf"{re.escape(var)}\s*=\s*new\s+([\w.]+)\(\)", body):
        return m.group(1)
    if m := re.search(rf"{re.escape(var)}\s*=\s*[^;]*readBody\([^)]*\)\s+as\s+([\w.]+)", body):
        return m.group(1)
    return None


class Scanner:
    def __init__(self, index: dict[str, str]) -> None:
        self.index = index  # FQN AS3 -> nome proto
        self.short = defaultdict(set)
        for fqn, proto in index.items():
            self.short[fqn.rsplit(".", 1)[-1]].add(proto)
        self.s2c: dict[int, set[str]] = defaultdict(set)
        self.c2s: dict[int, set[str]] = defaultdict(set)
        self.names: dict[int, set[str]] = defaultdict(set)

    def resolve(self, type_name: str, imports: dict[str, str], package: str) -> str:
        fqn = type_name if "." in type_name else imports.get(type_name, f"{package}.{type_name}")
        if fqn in self.index:
            return self.index[fqn]
        candidates = self.short.get(type_name.rsplit(".", 1)[-1], set())
        return next(iter(candidates)) if len(candidates) == 1 else f"?{type_name}"

    def scan_file(self, path: Path) -> None:
        src = path.read_text(encoding="utf-8", errors="replace")
        if path.name in ("ProtocolType.as", "AcceptProtocolType.as"):
            for name, code in RE_CONST.findall(src):
                self.names[int(code)].add(name)
            return
        if "SLGSocketEvent" not in src and "PackageOut(" not in src and "getCode" not in src:
            return
        imports = {imp.rsplit(".", 1)[-1]: imp for imp in RE_IMPORT.findall(src)}
        pkg = RE_PACKAGE.search(src)
        package = pkg.group(1) if pkg else ""
        funcs = split_functions(src)

        for code, handler in RE_LISTEN.findall(src):
            body = funcs.get(handler, "")
            types = self._read_types(body)
            if not types:  # handler que só repassa o evento: segue um nível
                for callee in filter(None, sum(RE_DELEGATE.findall(body), ())):
                    if callee != handler:
                        types += self._read_types(funcs.get(callee, ""))
            for t in types:
                self.s2c[int(code)].add(self.resolve(t, imports, package))
            self.s2c.setdefault(int(code), set())

        if m := RE_GETCODE.search(src):  # transação: os readBody de qualquer método da classe
            code = int(m.group(1))
            for t in (t for body in funcs.values() for t in self._read_types(body)):
                self.s2c[code].add(self.resolve(t, imports, package))
            self.s2c.setdefault(code, set())

        for body in funcs.values():
            codes = [int(c) for c in RE_PKG_OUT.findall(body)]
            if not codes:
                continue
            sends = RE_SEND.findall(body)
            for code in codes:
                self.c2s.setdefault(code, set())
                for first, second in sends:
                    arg = second if var_type(body, first) == "PackageOut" else first
                    if arg == "null":
                        self.c2s[code].add("(vazio)")
                    elif arg.startswith("new"):
                        self.c2s[code].add(self.resolve(arg[3:].strip()[:-2], imports, package))
                    elif t := var_type(body, arg):
                        self.c2s[code].add(self.resolve(t, imports, package))
                    else:  # corpo existe, mas o tipo não é estático (ex.: param1:Message)
                        self.c2s[code].add("?Message")

    @staticmethod
    def _read_types(body: str) -> list[str]:
        types = RE_READ_NEW.findall(body)
        for var in RE_READ_VAR.findall(body):
            if t := var_type(body, var):
                types.append(t)
        return types

    def result(self) -> dict[str, dict[str, list[str]]]:
        codes = sorted(set(self.s2c) | set(self.c2s) | set(self.names))
        return {
            str(c): {
                "names": sorted(self.names.get(c, ())),
                "c2s": sorted(self.c2s.get(c, ())) if c in self.c2s else [],
                "s2c": sorted(self.s2c.get(c, ())) if c in self.s2c else [],
                "client_sends": c in self.c2s,
                "client_listens": c in self.s2c,
            }
            for c in codes
        }


def render_markdown(table: dict[str, dict[str, list[str]]]) -> str:
    out = [
        "# Tabela de pacotes",
        "",
        "> Gerado por `tools/scan_opcodes.py` a partir do cliente decompilado. Não edite à mão.",
        "",
        "Direção: **C→S** = o cliente envia (`new PackageOut`), **S→C** = o cliente escuta "
        '(`"SLGSocketEvent" + N`). Um mesmo opcode pode existir nas duas direções.',
        "",
        "| Opcode | Hex | Nome(s) em ProtocolType | C→S (mensagem) | S→C (mensagem) |",
        "|---:|---|---|---|---|",
    ]
    for code, info in table.items():
        c = int(code)
        if not (info["client_sends"] or info["client_listens"]):
            continue
        c2s = ", ".join(info["c2s"]) or ("(sem corpo)" if info["client_sends"] else "")
        s2c = ", ".join(info["s2c"]) or ("(não lê corpo)" if info["client_listens"] else "")
        out.append(f"| {c} | 0x{c:04X} | {', '.join(info['names'])} | {c2s} | {s2c} |")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path)
    parser.add_argument("--index", type=Path, default=Path("proto/message_index.json"))
    parser.add_argument("--out", type=Path, default=Path("src/wartune_server/protocol/data/opcodes.json"))
    parser.add_argument("--doc", type=Path, default=Path("docs/packets.md"))
    args = parser.parse_args()
    if missing := [str(r) for r in args.roots if not r.is_dir()]:
        parser.error(f"diretório inexistente: {', '.join(missing)}")

    scanner = Scanner(json.loads(args.index.read_text(encoding="utf-8")))
    for root in args.roots:
        for path in sorted(root.rglob("*.as")):
            scanner.scan_file(path)
    for code, fqn in SPECIAL_S2C.items():
        scanner.s2c[code].add(scanner.index[fqn])
    for code, fqn in SPECIAL_C2S.items():
        scanner.c2s[code].add(scanner.index[fqn])
    table = scanner.result()
    args.out.write_text(json.dumps(table, indent=1, ensure_ascii=False), encoding="utf-8")
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(render_markdown(table), encoding="utf-8")
    s2c = sum(1 for v in table.values() if v["client_listens"])
    c2s = sum(1 for v in table.values() if v["client_sends"])
    unresolved = sum(1 for v in table.values() for m in v["c2s"] + v["s2c"] if m.startswith("?"))
    print(f"opcodes: {len(table)} | cliente escuta {s2c} | cliente envia {c2s} | não resolvidos {unresolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
