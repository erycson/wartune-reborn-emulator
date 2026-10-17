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
E as figuras de subida de nível que faltam (``swf/register1/N.swf``) são geradas a partir da que existe,
e o corpo padrão de batalha que falta para uma classe/sexo é copiado de outro (``fill_default_bodies``).

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


FIGURES = "swf/register1"
JOBS = range(1, 7)


def fill_level_up_figures(out: Path) -> int:
    """Gera ``swf/register1/N.swf`` para as classes que faltam, a partir de uma que exista.

    Ao subir de nível o ``HeroLeveUpdateAction`` carrega ``register1/<job>.swf`` e procura a classe
    ``asset.choicefigure.Human_<job>``; sem ela, recarrega para sempre (estouro de pilha). Só a
    figura da maga (6) veio da captura, então as outras classes ganham uma cópia dela com o nome da
    classe trocado (mesmo tamanho, um dígito). # ponytail: figura errada até achar as originais
    """
    folder = out / FIGURES
    existing = {job: folder / f"{job}.swf" for job in JOBS if (folder / f"{job}.swf").is_file()}
    if not existing:
        return 0
    source_job, source = next(iter(existing.items()))
    swf = source.read_bytes()
    body = zlib.decompress(swf[8:]) if swf[:3] == b"CWS" else swf[8:]
    made = 0
    for job in JOBS:
        if job in existing:
            continue
        renamed = body.replace(f"Human_{source_job}".encode(), f"Human_{job}".encode())
        (folder / f"{job}.swf").write_bytes(b"CWS" + swf[3:8] + zlib.compress(renamed, 9))
        made += 1
    return made


AVATARS = "swf/avatar"
CLASSES = ("warrior", "hunter", "wizard")


def fill_default_bodies(out: Path, cdn: Path) -> int:
    """Copia ``swf/avatar/<classe>_default_body/<sexo>.bswf`` quando falta nas duas pastas.

    Na batalha o herói sem roupa usa esse corpo; sem ele o ``HeroRoleView.bossLoadComplete`` acessa
    um conteúdo nulo e a batalha trava (cabelo e capa só ficam invisíveis). O CDN copiado só tem
    alguns. Substituto: a primeira roupa da classe naquele sexo, ou o corpo padrão de outra classe.
    O cliente acha as classes de dentro pelo caminho (``asset.<pasta>_<arquivo>.S_0_0``,
    ``DomainResourceLoad.getPackageName``), então a cópia tem o pacote renomeado (``rename_bswf``).
    # ponytail: figura de outra roupa/classe até achar os arquivos originais
    """

    def find(rel: str) -> Path | None:
        return next((root / rel for root in (out, cdn) if (root / rel).is_file()), None)

    made = 0
    for sex in (0, 1):
        defaults = {job: find(f"{AVATARS}/{job}_default_body/{sex}.bswf") for job in CLASSES}
        for job in CLASSES:
            if defaults[job] is not None:
                continue
            items = sorted(p for p in (cdn / AVATARS).glob(f"{job}_body0*/{sex}.bswf"))
            source = items[0] if items else next((d for d in defaults.values() if d is not None), None)
            if source is None:
                continue
            target = out / f"{AVATARS}/{job}_default_body/{sex}.bswf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(rename_bswf(source.read_bytes(), _package(source), _package(target)))
            made += 1
    return made


def _package(path: Path) -> str:
    return f"asset.{path.parent.name.lower()}_{path.stem.lower()}"


def rename_bswf(data: bytes, old: str, new: str) -> bytes:
    """``.bswf``: registros de cabeçalho (tipo de 1 byte) e o SWF no registro 16 (int32 + bytes)."""
    pos = 0
    while pos < len(data):
        kind = data[pos]
        pos += 1
        if kind == 16:
            size = struct.unpack_from(">i", data, pos)[0]
            swf = rename_swf(data[pos + 4 : pos + 4 + size], old, new)
            return data[:pos] + struct.pack(">i", len(swf)) + swf
        if kind in (2, 3, 8):  # readUTF
            pos += 2 + struct.unpack_from(">H", data, pos)[0]
        else:  # 1, 4, 6: byte; 5, 7, 9: int
            pos += 4 if kind in (5, 7, 9) else 1
    raise ValueError("bswf sem SWF")


def _u30(buf: bytes, pos: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        byte = buf[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, pos


def _put_u30(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _rename_abc(abc: bytes, old: bytes, new: bytes) -> bytes:
    """Troca ``old`` por ``new`` nas strings do pool de constantes; o resto do ABC só usa índices."""
    pos = 4  # minor, major
    count, pos = _u30(abc, pos)  # int
    for _ in range(max(count - 1, 0)):
        pos = _u30(abc, pos)[1]
    count, pos = _u30(abc, pos)  # uint
    for _ in range(max(count - 1, 0)):
        pos = _u30(abc, pos)[1]
    count, pos = _u30(abc, pos)  # double
    pos += 8 * max(count - 1, 0)
    out = bytearray(abc[:pos])
    count, pos = _u30(abc, pos)  # string
    out += _put_u30(count)
    for _ in range(max(count - 1, 0)):
        size, pos = _u30(abc, pos)
        text = abc[pos : pos + size].replace(old, new)
        pos += size
        out += _put_u30(len(text)) + text
    return bytes(out + abc[pos:])


def rename_swf(swf: bytes, old: str, new: str) -> bytes:
    """Renomeia o pacote nas tags DoABC (72, 82) e SymbolClass (76); recalcula os tamanhos."""
    o, n = old.encode(), new.encode()
    body = zlib.decompress(swf[8:]) if swf[:3] == b"CWS" else swf[8:]
    rect = 5 + 4 * (body[0] >> 3)
    pos = (rect + 7) // 8 + 4  # RECT, frame rate, frame count
    out = bytearray(body[:pos])
    while pos < len(body):
        header = struct.unpack_from("<H", body, pos)[0]
        code, size, pos = header >> 6, header & 0x3F, pos + 2
        if size == 0x3F:
            size, pos = struct.unpack_from("<I", body, pos)[0], pos + 4
        tag = body[pos : pos + size]
        pos += size
        if code == 82:  # flags (4) + nome (C string) + ABC
            end = tag.index(b"\0", 4) + 1
            tag = tag[:end] + _rename_abc(tag[end:], o, n)
        elif code == 72:
            tag = _rename_abc(tag, o, n)
        elif code == 76:
            tag = tag.replace(o, n)  # (id, C string)*: nenhum tamanho interno
        out += struct.pack("<HI", code << 6 | 0x3F, len(tag)) + tag
    return b"CWS" + swf[3:4] + struct.pack("<I", len(out) + 8) + zlib.compress(bytes(out), 9)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", type=Path, help="pasta de saída (ex.: D:/xampp/htdocs/wartune-reborn/cdn)")
    parser.add_argument("--cdn", type=Path, default=CDN)
    args = parser.parse_args()
    stats = build(args.out, SOURCES, args.cdn)
    stats["modulos"] = normalize_modules(args.out)
    stats["md5_corrigidos"] = sync_md5_list(args.out, args.cdn)
    stats["figuras"] = fill_level_up_figures(args.out)
    stats["corpos"] = fill_default_bodies(args.out, args.cdn)
    print(stats)


if __name__ == "__main__":
    main()
