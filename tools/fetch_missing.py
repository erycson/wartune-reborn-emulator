"""Baixa do CDN oficial os assets que o cliente pediu e o espelho local não tem.

O ``wartune-cdn`` foi montado a partir das capturas, então só tem o que o jogador capturado (job 6,
mago) carregou. Os arquivos de outras classes e sexos existem no CDN oficial, que é o mesmo build
(md5 idêntico nos arquivos em comum). A ferramenta lê os 404 do ``access.log`` do Apache e baixa
os originais, sem alterar nada.

    uv run python tools/fetch_missing.py                       # 404s do log
    uv run python tools/fetch_missing.py equip/x/1.swf ...     # caminhos avulsos
"""

import argparse
import re
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

OFFICIAL = "http://res134-bmclas-sq.7road.net/"  # inglês (turco, legado: res114lortr.creaction-network.com:8080)
LOG = Path("D:/xampp/apache/logs/access.log")
CDN = Path("D:/xampp/htdocs/wartune-reborn/cdn")  # link para mirror/res134-bmclas-sq.7road.net
PREFIX = "/wartune-reborn/cdn/"
SKIP = ("xml/",)  # respostas do nosso servidor/portal, não assets


def missing_from_log(log: Path) -> list[str]:
    paths = re.findall(r'"GET (\S+) HTTP/[\d.]+" 404 ', log.read_text(errors="replace"))
    found = {p.split("?")[0][len(PREFIX) :] for p in paths if p.startswith(PREFIX)}
    return sorted(p for p in found if not p.startswith(SKIP))


def safe(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return bool(parts) and ".." not in parts and not path.startswith("/")


def fetch(path: str, base: str, cdn: Path) -> str:
    target = cdn / path
    if target.exists():
        return "já existe"
    try:
        with urllib.request.urlopen(base + path, timeout=60) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        return f"oficial {error.code}"
    except (urllib.error.URLError, TimeoutError) as error:
        return f"erro {error}"
    if not data:
        return "oficial vazio"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"baixado {len(data)} bytes"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="caminhos relativos ao CDN; sem nenhum, lê os 404 do log")
    parser.add_argument("--log", type=Path, default=LOG)
    parser.add_argument("--cdn", type=Path, default=CDN)
    parser.add_argument("--base", default=OFFICIAL)
    args = parser.parse_args()
    for path in args.paths or missing_from_log(args.log):
        print(f"{path}: {fetch(path, args.base, args.cdn) if safe(path) else 'caminho recusado'}")


if __name__ == "__main__":
    main()
