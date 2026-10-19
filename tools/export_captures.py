"""Exporta respostas HTTP capturadas (dumps do Fiddler) para uma árvore de arquivos estáticos.

Legado da CDN turca: as sessões são do oficial turco e alimentavam ``data/overlay`` (CDN turca);
a CDN ativa é a inglesa. Ver docs/ferramentas.md.

Cada sessão ``NNN_c.txt`` (requisição) / ``NNN_s.txt`` (resposta) vira
``<saida>/<caminho da URL>`` com o corpo **exatamente como o Flash o recebia**:
sem ``Transfer-Encoding: chunked`` e sem ``Content-Encoding`` (gzip/deflate de
transporte, que o navegador removia). Compressões *do próprio arquivo* (ex.:
XML em zlib que o cliente descomprime com ``ByteArray.uncompress``) são mantidas.

Só respostas ``200`` são exportadas; se o mesmo caminho aparecer várias vezes,
fica a última. Gera também ``_capturas.json`` com a origem de cada arquivo.

Uso::

    uv run python tools/export_captures.py D:/wartune/server-relay/loginprotokol/raw \
        D:/wartune/server-relay/testraconu/raw --out data/overlay
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import zlib
from pathlib import Path
from urllib.parse import unquote, urlsplit

RE_REQUEST_LINE = re.compile(rb"^(GET|POST)\s+(\S+)\s+HTTP/")


def split_http(raw: bytes) -> tuple[list[bytes], bytes]:
    sep = raw.find(b"\r\n\r\n")
    if sep < 0:
        sep = raw.find(b"\n\n")
        return raw[:sep].split(b"\n"), raw[sep + 2 :]
    return raw[:sep].split(b"\r\n"), raw[sep + 4 :]


def headers_of(lines: list[bytes]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            out[k.strip().lower().decode("latin-1")] = v.strip().decode("latin-1")
    return out


def dechunk(body: bytes) -> bytes:
    out, pos = bytearray(), 0
    while pos < len(body):
        end = body.find(b"\r\n", pos)
        if end < 0:
            break
        size = int(body[pos:end].split(b";")[0] or b"0", 16)
        if size == 0:
            break
        out += body[end + 2 : end + 2 + size]
        pos = end + 2 + size + 2
    return bytes(out)


def transport_decode(body: bytes, headers: dict[str, str]) -> bytes:
    if "chunked" in headers.get("transfer-encoding", "").lower():
        body = dechunk(body)
    encoding = headers.get("content-encoding", "").lower()
    if encoding == "gzip":
        body = gzip.decompress(body)
    elif encoding == "deflate":
        try:
            body = zlib.decompress(body)
        except zlib.error:
            body = zlib.decompress(body, -zlib.MAX_WBITS)
    return body


def export(raw_dirs: list[Path], out: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for raw_dir in raw_dirs:
        for req_file in sorted(raw_dir.glob("*_c.txt")):
            session = req_file.name.split("_")[0]
            resp_file = raw_dir / f"{session}_s.txt"
            if not resp_file.exists():
                continue
            match = RE_REQUEST_LINE.match(req_file.read_bytes().split(b"\n", 1)[0])
            if not match or match.group(1) != b"GET":
                continue
            url_path = unquote(urlsplit(match.group(2).decode("latin-1")).path).lstrip("/")
            if not url_path or url_path.endswith("/") or ".." in url_path:
                continue
            lines, body = split_http(resp_file.read_bytes())
            status = lines[0].split()
            if len(status) < 2 or status[1] != b"200":
                continue
            try:
                body = transport_decode(body, headers_of(lines))
            except (OSError, zlib.error, ValueError) as exc:
                print(f"ignorado {url_path} ({raw_dir.name}/{session}): {exc}")
                continue
            target = out / url_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            index[url_path] = f"{raw_dir.parent.name}/{session}"
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_dirs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/overlay"))
    args = parser.parse_args()
    index = export(args.raw_dirs, args.out)
    (args.out / "_capturas.json").write_text(json.dumps(index, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(index)} arquivos exportados para {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
