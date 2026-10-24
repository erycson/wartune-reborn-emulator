"""Castelos NPC dos mapas do mundo (1 a 5): "Aladyr", "Alberthim"... com ``occupyPlayerId`` 13000000xx.

(visto) oficial_20261023-153200-1 e oficial_20261023-171155-1, mapa 1: 5 castelos NPC no 4129 (``baseCastle`` type 1,
state 1, sem guilda nem tempo de defesa, ``castleName`` = o nome), sempre no mesmo tile e grau nas duas capturas.
O ataque (#740-#749, #1886-#1893) é o do castelo-robô da instância (``robots.py``): battleType 4 no mapa 993, herói
``11000 + grau`` com o nome do castelo; as 2 pilhas são o lanceiro 101xx do grau (10112 com 443 de vida no grau 12).

O resto é ``game_settings.npc_castles`` (migração 0065): os vistos, quantos por grade nas grades vistas
(``world_mines.seen_grids``: 40 sem nenhum, 5 com um) e a vida das pilhas. TODO(inventado): os castelos das grades
não vistas (sorteio com semente mapa e grade, grau na faixa do ``MapInfos``, nome juntando metades dos nomes vistos)
e a vida das pilhas fora do grau 12 (``Live`` × ``hp_factor``, a razão 443 / 422 do grau 12).

Vitória (#6014-#6027 e o relatório 11569 do ``maillist``): 4950 de ouro saqueado do Aladyr (grau 12) e 2 h de proteção
(118 ``leftTime`` 7200; o 140 do castelo volta com ``defenceLefttime``). TODO(inventado): o saque nos outros graus
(``loot_per_grade`` × grau, 4950 / 12) e o ``fight`` do relatório fora do grau 12 (1760 × grau / 12).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from ..domain.models import PlayerSnapshot
from ..domain.world import World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import mines
from . import outer_city as oc

ID_BASE = 1_250_000_000  # castelo gerado: + mapa × 1_000_000 + (gx × 100 + gy) × 10 + n (int32)
# dono gerado: longe dos vistos (1300000011-77), dos robôs do torneio de pets (1300001401-2398) e da instância (9000)
USER_BASE = 1_300_100_000
PAWN_BASE = 10100  # 101xx: o lanceiro de nível = grau (visto 10112 no grau 12)
DEFAULT: dict[str, Any] = {
    "seen": [], "per_grid": {"0": 40, "1": 5}, "pawn_hp": {}, "hp_factor": 1.05, "loot_per_grade": 412.5,
    "shield_seconds": 7200, "fight": {"12": 1760},
}  # fmt: skip


@dataclass(frozen=True, slots=True)
class NpcCastle:
    id: int
    map_id: int
    x: int
    y: int
    grade: int
    user_id: int
    name: str


def settings(world: World) -> dict[str, Any]:
    return {**DEFAULT, **(world.settings.get("npc_castles") or {})}


def _seen(world: World, map_id: int) -> list[NpcCastle]:
    return [
        NpcCastle(int(r["id"]), map_id, int(r["x"]), int(r["y"]), int(r["grade"]), int(r["user_id"]), str(r["name"]))
        for r in settings(world)["seen"]
        if int(r["map"]) == map_id
    ]


def _name(world: World, rng: random.Random) -> str:
    """TODO(inventado): metade do começo de um nome visto e metade do fim de outro ("Ala" + "thim")."""
    pool = [str(r["name"]) for r in settings(world)["seen"]] + [str(n) for n in world.robot_names]
    if len(pool) < 2:
        return pool[0] if pool else ""
    a, b = rng.sample(pool, 2)
    return a[: math.ceil(len(a) / 2)] + b[len(b) // 2 :]


def _grid(world: World, templates: GameTemplates, map_id: int, grid: str) -> list[NpcCastle]:
    if grid in mines.world_settings(world)["seen_grids"].get(str(map_id), ()):
        return [c for c in _seen(world, map_id) if oc.grid_of(c.x, c.y) == grid]
    size, (low, high) = oc.map_size(templates, map_id), mines.band(templates, map_id)
    gx, gy = (int(p) for p in grid.split("_"))
    if size is None or not low:
        return []
    xs = range(max(gx * oc.GRID, mines.WORLD_EDGE), min(gx * oc.GRID + oc.GRID, size[0] - mines.WORLD_EDGE))
    ys = range(max(gy * oc.GRID, mines.WORLD_EDGE), min(gy * oc.GRID + oc.GRID, size[1] - mines.WORLD_EDGE))
    if not xs or not ys:
        return []
    rng = random.Random(f"npc:{map_id}:{grid}")
    counts = settings(world)["per_grid"]
    n = rng.choices([int(k) for k in counts], weights=[float(v) for v in counts.values()])[0]
    taken = {(m.x, m.y) for m in mines.world_mines_in(world, templates, map_id, {grid})}
    out: list[NpcCastle] = []
    cell = map_id * 1_000_000 + (gx * 100 + gy) * 10
    for i in range(min(n, len(xs) * len(ys) - len(taken))):
        x, y = rng.choice(xs), rng.choice(ys)
        while (x, y) in taken:  # o tile é de uma mina ou de outro castelo (o 5160 acharia o outro)
            x, y = rng.choice(xs), rng.choice(ys)
        taken.add((x, y))
        grade, name = rng.randint(low, high), _name(world, rng)
        out.append(NpcCastle(ID_BASE + cell + i, map_id, x, y, grade, USER_BASE + cell // 10 + i, name))
    return out


def castles_in(world: World, templates: GameTemplates, map_id: int, grids: set[str]) -> list[NpcCastle]:
    if not mines.is_world(world, map_id):
        return []
    return [c for g in sorted(grids) if g.count("_") == 1 for c in _grid(world, templates, map_id, g)]


def castle_at(world: World, templates: GameTemplates, map_id: int, x: int, y: int) -> NpcCastle | None:
    found = castles_in(world, templates, map_id, {oc.grid_of(x, y)})
    return next((c for c in found if (c.x, c.y) == (x, y)), None)


def tile_taken(world: World, templates: GameTemplates, map_id: int, x: int, y: int) -> bool:
    """O tile é de uma mina do mundo ou de um castelo NPC (o 5160 acharia esse, e não o baú, o monstro ou o castelo
    que caísse ali)."""
    return mines.world_mine_at(world, templates, map_id, x, y) is not None or (
        castle_at(world, templates, map_id, x, y) is not None
    )


def castle_msg(c: NpcCastle, state: int = 1, defence: int = 0) -> pb.BaseCastleMsg:
    """Como no 4129 e no 140 do oficial (#197, #748: state 4 na luta; #6025: ``defenceLefttime`` depois de vencido)."""
    return pb.BaseCastleMsg(
        id=c.id, mapId=c.map_id, posX=c.x, posY=c.y, type=1, occupyPlayerId=c.user_id, occupyPlayerName=c.name,
        occupyLeagueName="", state=state, defenceLefttime=defence, castleName=c.name, grade=c.grade, vipCastleView=0,
        vipType=0,
    )  # fmt: skip


def loot(world: World, grade: int) -> int:
    """Ouro saqueado na vitória (visto 4950 no grau 12; TODO(inventado): proporcional ao grau nos outros)."""
    return round(float(settings(world)["loot_per_grade"]) * grade)


def fight(world: World, grade: int) -> int:
    """``fight`` do castelo no relatório (visto 1760 no grau 12; TODO(inventado): proporcional nos outros)."""
    seen = {int(k): int(v) for k, v in settings(world)["fight"].items()}
    if grade in seen:
        return seen[grade]
    base = min(seen, key=lambda g: abs(g - grade)) if seen else 0
    return round(seen[base] * grade / base) if base else 0


def pawn_hp(world: World, templates: GameTemplates, grade: int) -> int:
    conf = settings(world)
    if (seen := conf["pawn_hp"].get(str(grade))) is not None:
        return int(seen)
    live = int((templates.get("PawnTempInfos", PAWN_BASE + grade) or {}).get("Live") or 1)
    return max(1, round(live * float(conf["hp_factor"])))  # TODO(inventado): a razão do grau 12


def battle(snap: PlayerSnapshot, world: World, templates: GameTemplates, c: NpcCastle) -> dict[str, object]:
    """(visto) #749: a luta do castelo-robô com 2 pilhas do lanceiro do grau."""
    return oc.robot_battle(snap, templates, c.grade, c.name, PAWN_BASE + c.grade, pawn_hp(world, templates, c.grade))
