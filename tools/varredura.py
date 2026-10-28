"""Cruza os pedidos (C>S) de todas as capturas com os handlers do servidor.

Lista o que foi visto e não tem handler, e o que tem handler marcado como fechado/vazio/falso.
Rodar a cada sessão nova do coletor::

    .venv\\Scripts\\python.exe tools\\varredura.py [pastas ou arquivos .jsonl/.json]
"""

from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDLERS = ROOT / "src" / "wartune_server" / "game" / "handlers"
DEFAULT = [Path(r"D:\wartune\coletor\sessoes"), ROOT / "captures"]
SUSPEITO = re.compile(r"fechad|sempre vazi|falso|sem captura|recusad|TODO", re.I)


def packets(path: Path):  # type: ignore[no-untyped-def]
    if path.suffix == ".jsonl":
        for line in path.open(encoding="utf-8"):
            if line.strip():
                yield json.loads(line)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        yield from data if isinstance(data, list) else data.get("packets", [])


def seen(paths: list[Path]) -> tuple[Counter[int], dict[int, set[str]], Counter[int]]:
    c2s: Counter[int] = Counter()
    s2c: Counter[int] = Counter()
    where: dict[int, set[str]] = defaultdict(set)
    for p in paths:
        files = sorted(p.glob("*.jsonl")) + sorted(p.glob("*.json")) if p.is_dir() else [p]
        for f in files:
            try:
                for pk in packets(f):
                    code = int(pk["code"])
                    if pk.get("isClient", pk.get("dir") == "C>S"):
                        c2s[code] += 1
                        where[code].add(f.stem)
                    else:
                        s2c[code] += 1
            except (ValueError, KeyError, json.JSONDecodeError):
                print("ignorado:", f, file=sys.stderr)
    return c2s, where, s2c


def handled() -> dict[int, tuple[str, str]]:
    """código -> (função, docstring) de cada ``@router.on``."""
    out: dict[int, tuple[str, str]] = {}
    for f in HANDLERS.rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "on":
                    for arg in dec.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                            out[arg.value] = (f"{f.stem}.{node.name}", ast.get_docstring(node) or "")
    return out


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:]] or [p for p in DEFAULT if p.exists()]
    c2s, where, _ = seen(paths)
    hs = handled()
    print("## Pedidos vistos sem handler")
    for code, n in c2s.most_common():
        if code not in hs:
            print(f"{code}\t{n}x\t{', '.join(sorted(where[code])[:3])}")
    print("\n## Pedidos vistos com handler suspeito (fechado/vazio/falso/TODO na docstring)")
    for code, n in c2s.most_common():
        if code in hs and SUSPEITO.search(hs[code][1]):
            first = hs[code][1].splitlines()[0][:110]
            print(f"{code}\t{n}x\t{hs[code][0]}\t{first}")


if __name__ == "__main__":
    main()
