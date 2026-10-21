"""Tira do ``maps/<id>/<id>.titles`` da CDN os tiles do mapa de veículos para ``data/vehicle_map_<id>.json``.

O ``.titles`` é um objeto AMF3 dinâmico comprimido com zlib: chave ``"x_y"`` e valor inteiro, o mesmo
``mapTielsData`` do cliente (``PreCampaignData``). Andável é valor > 0 e diferente de 2
(``VehicleModel.getWalkable``); os 29 tiles de valor 3 do 3001 vão em ``marks`` (o servidor sorteia neles o
surgimento dos tanques e das caixas, ``game/vehicles.py``).

    uv run python tools/extract_vehicle_map.py <mirror>/res134-bmclas-sq.7road.net/maps/3001/3001.titles
"""

from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path

OBJECT, DYNAMIC, INTEGER = 0x0A, 0x0B, 0x04
BARRIER, MARK = 2, 3


def _u29(data: bytes, i: int) -> tuple[int, int]:
    value = 0
    for n in range(4):
        byte = data[i]
        i += 1
        if n == 3:
            return (value << 8) | byte, i
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            break
    return value, i


def read_tiles(raw: bytes) -> dict[tuple[int, int], int]:
    """Os tiles do ``.titles`` (só objeto dinâmico sem classe com valores inteiros, como os mapas do jogo)."""
    data = zlib.decompress(raw)
    if data[:3] != bytes((OBJECT, DYNAMIC, 0x01)):
        raise ValueError("não é um objeto AMF3 dinâmico")
    tiles: dict[tuple[int, int], int] = {}
    names: list[str] = []
    i = 3
    while True:
        head, i = _u29(data, i)
        if head & 1:
            name = data[i : i + (head >> 1)].decode()
            i += head >> 1
            if not name:  # fim dos pares dinâmicos
                return tiles
            names.append(name)
        else:
            name = names[head >> 1]
        if data[i] != INTEGER:
            raise ValueError(f"valor não inteiro em {name}")
        value, i = _u29(data, i + 1)
        x, y = name.split("_")
        tiles[int(x), int(y)] = value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("titles", type=Path)
    parser.add_argument("-o", "--out-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    tiles = read_tiles(args.titles.read_bytes())
    walk = sorted(f"{x}_{y}" for (x, y), v in tiles.items() if v > 0 and v != BARRIER)
    marks = sorted([x, y] for (x, y), v in tiles.items() if v == MARK)
    out = args.out_dir / f"vehicle_map_{args.titles.stem}.json"
    out.write_text(json.dumps({"walkable": walk, "marks": marks}, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{out}: {len(walk)} andáveis, {len(marks)} marcas")


if __name__ == "__main__":
    main()
