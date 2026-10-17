"""Monta a pasta de sobreposição do CDN (servida pelo Apache antes do CDN completo).

Copia de cada origem, na ordem, os arquivos que faltam no CDN ou têm conteúdo diferente.
A primeira origem que tiver o arquivo vence:

1. ``data/overlay``: respostas capturadas do servidor oficial (tools/export_captures.py)
2. ``server-relay/public``: SWFs/PNGs do relay validados contra a captura (os .png de código
   diferem dos do CDN)

O que não for asset (páginas, scripts, respostas de endpoints dinâmicos) fica de fora: isso é
papel do portal ou do servidor do jogo.

    uv run python tools/build_cdn_overrides.py D:/xampp/htdocs/wartune-reborn/cdn
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

SOURCES = [Path("data/overlay"), Path("D:/wartune/server-relay/public")]
CDN = Path("D:/xampp/htdocs/wartune-cdn")

SKIP_SUFFIXES = {".php", ".html", ".jsp", ".json"}
SKIP_NAMES = {"loginselectlist", "visualizeregister", "search", "url", "generate_204", "timestory", "config.xml"}
SKIP_DIRS = {"serverlist", "plugins", "api", "_"}


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _is_asset(rel: Path) -> bool:
    return not (
        rel.suffix.lower() in SKIP_SUFFIXES
        or rel.name in SKIP_NAMES
        or (rel.parts and rel.parts[0] in SKIP_DIRS)
    )


def build(out: Path, sources: list[Path], cdn: Path) -> dict[str, int]:
    stats = {"copiados": 0, "iguais_ao_cdn": 0, "ignorados": 0}
    seen: set[Path] = set()
    for src in sources:
        for file in sorted(p for p in src.rglob("*") if p.is_file()):
            rel = file.relative_to(src)
            if rel in seen:
                continue
            seen.add(rel)
            if not _is_asset(rel):
                stats["ignorados"] += 1
                continue
            original = cdn / rel
            if original.is_file() and _md5(original) == _md5(file):
                stats["iguais_ao_cdn"] += 1
                continue
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
            stats["copiados"] += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path, help="pasta de saída (ex.: D:/xampp/htdocs/wartune-reborn/cdn)")
    parser.add_argument("--cdn", type=Path, default=CDN)
    args = parser.parse_args()
    print(build(args.out, SOURCES, args.cdn))


if __name__ == "__main__":
    main()
