"""Extrai das capturas oficiais o que fica parado no mapa do mundo (mapas 1 a 5) para a semente do banco.

Tira dos 4129 (``PhysicListUpdateMsg``) e dos 140 (``MapUpdatedMsg``) as terras (``wildLand``: minas tipo 20 e
Treasure Caches tipo 22; os monstros tipo 21 já são sorteados em ``game/monsters.py``) e os lugares de castelo
(``baseCastle``). De jogador real só fica o lugar: o castelo dele vira um lugar livre. Os castelos de NPC
(``occupyPlayerId`` 13000000xx, ex. "Aladyr") ficam com nome e nível. Cada linha leva ``seen`` (captura#índice).

    uv run python tools/extract_world.py captures/oficial_20261023-153200-1.json captures/oficial_20261023-171155-1.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from wartune_server.protocol.registry import Direction, MessageRegistry

OUT = Path("mundo.json")  # as listas vão à mão para a migração (minas: 0064_minas_do_mundo)
NPC_BASE = 1_300_000_000  # ids dos donos NPC no oficial (arena.ROBOT_BASE é outro: aqui é o do oficial)
LAND_TYPES = (20, 22)  # mina de ouro, Treasure Cache


def extract(captures: list[Path]) -> dict[str, list[dict[str, Any]]]:
    reg = MessageRegistry.load_default()
    lands: dict[int, dict[str, Any]] = {}
    castles: dict[int, dict[str, Any]] = {}
    for cap in captures:
        for p in json.loads(cap.read_text(encoding="utf-8")):
            if p["isClient"] or p["code"] not in (4129, 140):
                continue
            msg = reg.decode(p["code"], Direction.SERVER_TO_CLIENT, bytes.fromhex(p["bodyHex"]))
            if msg is None:
                continue
            seen = f"{cap.stem}#{p['index']}"
            if p["code"] == 4129:
                wilds, bases = list(msg.wildLand), list(msg.baseCastle)
            else:
                wilds = [msg.wildLand] if msg.HasField("wildLand") else []
                bases = [msg.baseCastle] if msg.HasField("baseCastle") else []
            for w in wilds:
                if w.type in LAND_TYPES and w.id not in lands:
                    lands[w.id] = {
                        "id": w.id,
                        "map": w.mapId,
                        "x": w.posX,
                        "y": w.posY,
                        "template": w.templateId,
                        "type": w.type,
                        "level": w.level,
                        "guards": [[a.tempateId, a.ownPawns] for a in w.armyPawn],
                        "seen": seen,
                    }
            for c in bases:
                npc = c.occupyPlayerId >= NPC_BASE
                row = castles.setdefault(c.id, {"id": c.id, "map": c.mapId, "x": c.posX, "y": c.posY, "seen": seen})
                if npc and "npc" not in row:
                    row["npc"] = {"id": c.occupyPlayerId, "name": c.occupyPlayerName, "grade": c.grade}
    return {
        "lands": sorted(lands.values(), key=lambda r: r["id"]),
        "castles": sorted(castles.values(), key=lambda r: r["id"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("captures", type=Path, nargs="+")
    parser.add_argument("-o", "--out", type=Path, default=OUT)
    args = parser.parse_args()
    data = extract(args.captures)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(data['lands'])} terras, {len(data['castles'])} castelos -> {args.out}")


if __name__ == "__main__":
    main()
