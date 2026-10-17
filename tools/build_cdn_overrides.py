"""Monta a pasta de sobreposição do CDN (servida pelo Apache antes do CDN completo).

Copia de cada origem, na ordem, os arquivos que faltam no CDN ou têm conteúdo diferente.
A primeira origem que tiver o arquivo vence:

1. ``tools/cdn_stubs``: arquivos mínimos para o que o CDN não tem e o cliente pede
   (``xml/version.xml``, ``xml/resource.xml``); no 404 o Ruffle entrega o HTML do Apache e o
   cliente quebra ao ler como XML
2. ``data/overlay``: respostas capturadas do servidor oficial (tools/export_captures.py)
3. ``server-relay/public``: SWFs/PNGs do relay validados contra a captura (os .png de código
   diferem dos do CDN)

Depois da cópia, os módulos de código cifrados (``N.png``, cabeçalho ``road7``) que o relay
deixou com ~20 MB de zeros depois do tag End são recomprimidos sem esse enchimento (o Flash
ignora, o Ruffle carrega o lixo para a memória) e o ``ui/zh_cn/size.xml`` recebe os novos tamanhos.
Por fim, a lista ``client/resouececheck.sq`` recebe o md5 embutido em cada módulo servido
(os que só existem no CDN completo são de outro build e seriam descartados em silêncio).

O que não for asset (páginas, scripts, respostas de endpoints dinâmicos) fica de fora: isso é
papel do portal ou do servidor do jogo.

    uv run python tools/build_cdn_overrides.py D:/xampp/htdocs/wartune-reborn/cdn
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import struct
import zlib
from pathlib import Path

SOURCES = [Path("tools/cdn_stubs"), Path("data/overlay"), Path("D:/wartune/server-relay/public")]
CDN = Path("D:/xampp/htdocs/wartune-cdn")

SKIP_SUFFIXES = {".php", ".html", ".jsp", ".json"}
SKIP_NAMES = {"loginselectlist", "visualizeregister", "search", "url", "generate_204", "timestory", "config.xml"}
SKIP_DIRS = {"serverlist", "plugins", "api", "_"}


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _is_asset(rel: Path) -> bool:
    return not (
        rel.suffix.lower() in SKIP_SUFFIXES or rel.name in SKIP_NAMES or (rel.parts and rel.parts[0] in SKIP_DIRS)
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


MODULE_PREFIX = 37  # "road7" + md5 do resouececheck.sq; o ModuleLoader descarta isso
TAIL = 121  # o decry() move os últimos 121 bytes para logo depois do "CWS"


def decrypt_module(raw: bytes) -> bytes:
    """Mesmo algoritmo de ``ModuleLoader.decry`` (m2): devolve o SWF ``CWS``."""
    b = raw[MODULE_PREFIX:]
    return b"CWS" + b[-TAIL:] + b[21:-TAIL]


def encrypt_module(raw: bytes, swf: bytes) -> bytes:
    """Inverso de :func:`decrypt_module`, preservando os 58 bytes de prefixo de ``raw``."""
    return raw[: MODULE_PREFIX + 21] + swf[3 + TAIL :] + swf[3 : 3 + TAIL]


def strip_module_padding(raw: bytes) -> bytes | None:
    """Recomprime o módulo cortando o que vem depois do tamanho do cabeçalho; ``None`` se já está limpo."""
    swf = decrypt_module(raw)
    length = struct.unpack("<I", swf[4:8])[0]
    body = zlib.decompressobj().decompress(swf[8:])
    if len(body) + 8 <= length:
        return None
    return encrypt_module(raw, swf[:8] + zlib.compress(body[: length - 8], 9))


def normalize_modules(out: Path) -> int:
    sizes: dict[str, int] = {}
    for file in sorted(out.glob("*.png")):
        raw = file.read_bytes()
        if raw[:5] != b"road7":
            continue
        fixed = strip_module_padding(raw)
        if fixed is not None:
            file.write_bytes(fixed)
        sizes[file.name] = file.stat().st_size
    size_xml = out / "ui/zh_cn/size.xml"
    if sizes and size_xml.is_file():
        text = size_xml.read_text(encoding="utf-8-sig")
        for name, size in sizes.items():
            # o ModuleLoader recusa o módulo se o tamanho diferir em 3000 bytes ou mais
            text = re.sub(rf'size="\d+"(\s+name="{re.escape(name)}")', rf'size="{size}"\1', text)
        size_xml.write_text(text, encoding="utf-8-sig")
    return len(sizes)


def sync_md5_list(out: Path, cdn: Path) -> int:
    """Põe na lista ``client/resouececheck.sq`` o md5 embutido em cada ``N.png`` servido.

    O ModuleLoader compara os bytes 5..37 do arquivo com a lista e, se diferirem, descarta o
    módulo sem erro. Os módulos que só existem no CDN completo são de outro build que a lista.
    """
    check = out / "client/resouececheck.sq"
    if not check.is_file():
        return 0
    text = zlib.decompress(check.read_bytes()).decode("utf-8-sig")
    changed = 0
    for name in sorted(set(re.findall(r'name="(\d+\.png)"', text))):
        file = out / name if (out / name).is_file() else cdn / name
        if not file.is_file():
            continue
        head = file.read_bytes()[:MODULE_PREFIX]
        if head[:5] != b"road7":
            continue
        embedded = head[5:].decode("ascii")
        text, n = re.subn(rf'(name="{re.escape(name)}"\s+md5=")(?!{embedded})\w+"', rf'\g<1>{embedded}"', text)
        changed += n
    if changed:
        check.write_bytes(zlib.compress(("﻿" + text).encode("utf-8"), 9))
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path, help="pasta de saída (ex.: D:/xampp/htdocs/wartune-reborn/cdn)")
    parser.add_argument("--cdn", type=Path, default=CDN)
    args = parser.parse_args()
    stats = build(args.out, SOURCES, args.cdn)
    stats["modulos"] = normalize_modules(args.out)
    stats["md5_corrigidos"] = sync_md5_list(args.out, args.cdn)
    print(stats)


if __name__ == "__main__":
    main()
