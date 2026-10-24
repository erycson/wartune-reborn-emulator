"""Minas de ouro (``WildLandMsg`` type 20): as 4 do mapa do castelo e as dos mapas do mundo (1 a 5).

Mapa do castelo: as minas vêm do catálogo do mundo (``domain/world.py``); o ciclo e as ocupações são do jogador
(``Castle.mines_at`` e ``wild_lands``). Cada conta tem a sua cópia das minas (inglês #532 contra o turco replay
#706: mesmos ids e tiles): a instância, os robôs, os ids do armyPawn e o createDate mudam de uma para a outra, e a
ocupação de outro jogador não aparece nem bloqueia. O guia do tutorial (m8 NewbieBaseActionMediator, alvo 80)
procura as duas primeiras pelos pixels (320,680) e (720,680).

Mapas do mundo (visto: oficial_20261023-153200-1 e oficial_20261023-171155-1, mapa 1):

- O ciclo é do mundo: createDate 01:15:41 e 13:15:52 (fuso do jogo) em todas as minas, de 12 em 12 h; o nível de
  cada mina é sorteado de novo a cada ciclo (806736: 200418 às 13:15) na faixa do mapa (``MapInfos`` MinLevel e
  MaxLevel: 11 a 20 no mapa 1). ``refreshTime`` é o que falta do ciclo, em ms (5109784 às 11:50).
- Todo jogador vê as mesmas minas e quem ocupou (Alt29 e a guilda dele em ``occupyLeagueName``, com o poder dele em
  ``fightCapaity``); a livre mostra o poder do guarda (866 no 6506 ... 1601 no 6522).
- 152: ``wildPoxName`` "Autaric Plains(2487,2632)" (``MapName`` + tile) e ``mapId`` do mapa.
- Na virada, com o jogador online, cada mina sai com 109, 152 e uma carta (148) (#170-#175).
- (cliente) até 2 minas por jogador (``MapPhysicsField``: "Max number of occupiable resource quarries") e mina de
  alguém da mesma guilda não se ataca (``AttackConsortiaMember``); a de outro jogador mostra "Attack".

As minas das grades vistas são as do catálogo (``world_mines``); nas outras, sorteio com semente (mapa, grade) pela
contagem das vistas (``game_settings.world_mines``). TODO(inventado): essas minas geradas.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

from ..domain import gameday
from ..domain.models import PlayerSnapshot, WildLand
from ..domain.world import Mine, World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from .outer_city import BASE_MAP, GRID, grid_of, map_size, template_of

MINE_TYPE, MINE_SON_TYPE = 20, 2006  # WildLandMsg.type; MapPhysicsTempInfos.SonType (missão 60, Para1)
MINE_FREE, MINE_FIGHTING = 1, 4  # WildLandMsg.state
MINE_CAPACITY = 324  # fightCapaity da mina livre nas capturas
# Refresh: RefreshTime 43200 s em todas as minas (MapPhysicsTempInfos). O ciclo é do jogador
# (``Castle.mines_at``): o createDate vem no fuso do jogo e cai na entrada da conta, não numa hora do mundo.
# Inglês #532: 18:21:37 (Pacífico), 2 s antes do beginDate 18:21:39 das 4152 da conta nova (#50). Só turco
# (cevre e login.json): o relogin não mudou o createDate, e duas contas ficaram 7 h 29 min distantes.
# ponytail: (dedução) o ciclo vencido só renova no próximo acerto de ouro, login, 8201 ou 5160 e começa nessa hora;
# quem fica online pode ver o oficial renovar na hora certa (sem captura de um refresh ao vivo).
MINE_PERIOD = timedelta(hours=12)
DATE = "%Y-%m-%d %H:%M:%S"
WORLD_ID_BASE = 1_200_000_000  # mina gerada: + mapa × 1_000_000 + (gx × 100 + gy) × 10 + n (int32)
WORLD_EDGE = 20  # tiles da borda do mapa, como os monstros
WORLD_DEFAULT: dict[str, Any] = {
    "anchor": "01:15:41",
    "maps": [1, 2, 3, 4, 5],
    "seen_grids": {},
    "per_grid": {"0": 7, "1": 23, "2": 10, "3": 4, "5": 1},
    "max_held": 2,
}
# (visto) fightCapaity da mina livre com cada guarda (4129 das duas capturas)
GUARD_CAPACITY = {6506: 866, 6509: 962, 6511: 1108, 6513: 1223, 6514: 1292, 6516: 1312, 6517: 1362, 6520: 1436,
                  6521: 1403, 6522: 1601}  # fmt: skip


def mine_at(world: World, map_id: int, x: int, y: int) -> Mine | None:
    if template_of(map_id) != BASE_MAP:
        return None
    return next((m for m in world.mines_on(BASE_MAP) if (m.x, m.y) == (x, y)), None)


def mines_in(world: World, grids: set[str]) -> list[Mine]:
    return [m for m in world.mines_on(BASE_MAP) if grid_of(m.x, m.y) in grids]


def cycle_start(snap: PlayerSnapshot) -> datetime:
    """Começo do ciclo de minas do jogador. Castelo de antes da migração 0018 (``mines_at`` vazio):
    a ocupação mais velha, para a mina dele não vencer na hora (o refresh do login grava o valor)."""
    castle = snap.castle
    assert castle is not None
    if castle.mines_at is not None:
        return castle.mines_at
    return min((w.occupied_at for w in snap.wild_lands), default=datetime.fromtimestamp(0, UTC))


def cycle_end(snap: PlayerSnapshot) -> datetime:
    return cycle_start(snap) + MINE_PERIOD


def game_date(at: datetime) -> str:
    """Data como o oficial manda (createDate): no fuso do jogo."""
    return gameday.local(at).strftime(DATE)


def level_template(templates: GameTemplates, level: int) -> int:
    """Template da mina de um nível (MapPhysicsTempInfos SonType 2006: Grades = nível, Property4 = ouro/h)."""
    row = next(templates.find("MapPhysicsTempInfos", SonType=MINE_SON_TYPE, Grades=level), None)
    return int(row["TemplateId"]) if row else 0


def draw(snap: PlayerSnapshot, world: World, templates: GameTemplates, mine: Mine) -> tuple[int, int]:
    """(template, guarda) da mina no ciclo atual do jogador. A semente é o jogador, a mina e o começo do
    ciclo: o sorteio fica o mesmo até o refresh e muda a cada um."""
    seed = f"{snap.character.id}:{mine.id}:{int(cycle_start(snap).timestamp())}"
    level = random.Random(seed).choice(mine.levels)
    return level_template(templates, level), world.mine_guards.get(level, 0)


def _current(snap: PlayerSnapshot) -> list[WildLand]:
    start = cycle_start(snap)
    return [w for w in snap.wild_lands if w.occupied_at >= start]


def occupied(snap: PlayerSnapshot, mine: Mine) -> WildLand | None:
    """Ocupação do jogador no ciclo atual. A linha de um ciclo vencido fica no banco e é reaproveitada
    por ``occupy`` (unique personagem + mina)."""
    return next((w for w in _current(snap) if w.wild_id == mine.id), None)


def release(snap: PlayerSnapshot) -> list[WildLand]:
    """Solta as minas do ciclo: o castelo saiu do mapa delas. (visto) oficial_20261023-153200-1 #184-#186: o 5176
    para o mapa 1 manda o 152 sem ``wildYield`` e o ``goldYield`` cai de 2760 para 1240 (#183, #186)."""
    gone = _current(snap)
    snap.wild_lands[:] = [w for w in snap.wild_lands if w not in gone]
    return gone


def occupy(snap: PlayerSnapshot, mine: Mine, template: int, now: datetime) -> WildLand:
    """Grava a mina como do jogador, com o nível sorteado agora: o rendimento sai da linha, e o catálogo
    pode mudar sem mexer no que já está ocupado."""
    land = next((w for w in snap.wild_lands if w.wild_id == mine.id), None)
    if land is None:
        land = WildLand(snap.character.id or 0, mine.id, now)
        snap.wild_lands.append(land)
    land.occupied_at, land.template_id, land.pos_x, land.pos_y = now, template, mine.x, mine.y
    return land


def backfill(snap: PlayerSnapshot, world: World, templates: GameTemplates) -> list[WildLand]:
    """Ocupações de antes da migração 0027 (sem nível gravado): completa com o sorteio do ciclo."""
    filled = []
    for land in _current(snap):
        mine = world.mine(land.wild_id)
        if land.template_id or mine is None:
            continue
        land.template_id, land.pos_x, land.pos_y = draw(snap, world, templates, mine)[0], mine.x, mine.y
        filled.append(land)
    return filled


def world_settings(world: World) -> dict[str, Any]:
    return dict(world.settings.get("world_mines") or WORLD_DEFAULT)


def is_world(world: World, map_id: int) -> bool:
    return map_id in world_settings(world)["maps"]


def band(templates: GameTemplates, map_id: int) -> tuple[int, int]:
    """Faixa de nível das minas do mapa (``MapInfos`` MinLevel e MaxLevel); (0, 0) sem a linha."""
    row = templates.get("MapInfos", map_id, key="Id") or {}
    return int(row.get("MinLevel") or 0), int(row.get("MaxLevel") or 0)


def map_name(templates: GameTemplates, map_id: int) -> str:
    return str((templates.get("MapInfos", map_id, key="Id") or {}).get("MapName", ""))


def world_cycle_start(world: World, now: datetime) -> datetime:
    """Começo do ciclo do mundo em que ``now`` está: a hora ``anchor`` no fuso do jogo, de 12 em 12 h."""
    h, m, s = (int(p) for p in world_settings(world)["anchor"].split(":"))
    local = gameday.local(now)
    base = local.replace(hour=h, minute=m, second=s, microsecond=0)
    return (base + math.floor((local - base) / MINE_PERIOD) * MINE_PERIOD).astimezone(UTC)


def next_cycle(snap: PlayerSnapshot, now: datetime) -> datetime:
    """Começo do ciclo que vem depois do vencido: no mapa do castelo, ``now`` (o ciclo é da conta); num mapa do mundo,
    o ciclo do mundo continua de 12 em 12 h (``mines_at`` foi alinhado ao entrar nele)."""
    assert snap.castle is not None
    if template_of(snap.castle.map_id) == BASE_MAP:
        return now
    start = cycle_start(snap)
    return start + math.floor((now - start) / MINE_PERIOD) * MINE_PERIOD


def _grid_mines(world: World, templates: GameTemplates, map_id: int, grid: str) -> list[Mine]:
    conf = world_settings(world)
    if grid in conf["seen_grids"].get(str(map_id), ()):
        return [m for m in world.mines_on(map_id) if grid_of(m.x, m.y) == grid]
    size, (low, high) = map_size(templates, map_id), band(templates, map_id)
    gx, gy = (int(p) for p in grid.split("_"))
    if size is None or not low:
        return []
    xs = range(max(gx * GRID, WORLD_EDGE), min(gx * GRID + GRID, size[0] - WORLD_EDGE))
    ys = range(max(gy * GRID, WORLD_EDGE), min(gy * GRID + GRID, size[1] - WORLD_EDGE))
    if not xs or not ys:
        return []
    rng = random.Random(f"mina:{map_id}:{grid}")
    counts = conf["per_grid"]
    n = rng.choices([int(k) for k in counts], weights=[float(v) for v in counts.values()])[0]
    tiles = {(rng.choice(xs), rng.choice(ys)) for _ in range(n)}  # tile repetido: uma mina a menos
    base = WORLD_ID_BASE + map_id * 1_000_000 + (gx * 100 + gy) * 10
    return [Mine(base + i, map_id, x, y, low, high) for i, (x, y) in enumerate(sorted(tiles))]


def world_mines_in(world: World, templates: GameTemplates, map_id: int, grids: set[str]) -> list[Mine]:
    if not is_world(world, map_id):
        return []
    return [m for g in sorted(grids) if g.count("_") == 1 for m in _grid_mines(world, templates, map_id, g)]


def world_mine_at(world: World, templates: GameTemplates, map_id: int, x: int, y: int) -> Mine | None:
    found = world_mines_in(world, templates, map_id, {grid_of(x, y)})
    return next((m for m in found if (m.x, m.y) == (x, y)), None)


def world_mine(world: World, templates: GameTemplates, map_id: int, mine_id: int) -> Mine | None:
    """A mina pelo id (152 e 5179 só trazem o tile; a ocupação guarda id, mapa e tile)."""
    if (m := world.mine(mine_id)) is not None:
        return m
    if not WORLD_ID_BASE <= mine_id < WORLD_ID_BASE + 6_000_000:
        return None
    cell = (mine_id - WORLD_ID_BASE) % 1_000_000 // 10
    found = world_mines_in(world, templates, map_id, {f"{cell // 100}_{cell % 100}"})
    return next((m for m in found if m.id == mine_id), None)


def world_draw(world: World, templates: GameTemplates, mine: Mine, cycle: datetime) -> tuple[int, int]:
    """(template, guarda) da mina no ciclo do mundo: a semente é a mina e o ciclo, igual para todo jogador."""
    level = random.Random(f"{mine.map_id}:{mine.id}:{int(cycle.timestamp())}").choice(mine.levels)
    return level_template(templates, level), world.mine_guards.get(level, 0)


@cache
def _formula_capacity(templates: GameTemplates, guard: int) -> int:
    row = templates.get("PawnTempInfos", guard) or {}
    total = int(row.get("Live") or 0) * 0.006
    total += sum(int(row.get(k) or 0) for k in ("Attack", "MagicAttack", "Defence", "MagicDefence"))
    return max(0, round(total) - 6)


def guard_capacity(templates: GameTemplates, guard: int) -> int:
    """``fightCapaity`` da mina livre. (visto) os 10 guardas de ``GUARD_CAPACITY``; (dedução) os outros pela conta
    ``Live`` / 100 × 0,6 + ataques + defesas - 6, que dá o valor visto em 9 dos 10 (o 6522 dá 1621 contra 1601)."""
    return GUARD_CAPACITY.get(guard) or _formula_capacity(templates, guard)


def world_mine_msg(
    world: World,
    templates: GameTemplates,
    mine: Mine,
    now: datetime,
    state: int,
    holder: WildLand | None = None,
    name: str = "",
    guild: str = "",
) -> pb.WildLandMsg:
    """Mina do mundo como no 4129 e no 140 do oficial (#1503, #3040, #3079): ``refreshTime`` = o que falta do ciclo,
    a livre com o poder do guarda, a ocupada com o dono, a guilda dele e o poder gravado na ocupação."""
    cycle = world_cycle_start(world, now)
    template, guard = world_draw(world, templates, mine, cycle)
    if holder is not None and holder.template_id:
        template = holder.template_id
    row = templates.get("MapPhysicsTempInfos", template) or {}
    msg = pb.WildLandMsg(
        id=mine.id,
        mapId=mine.map_id,
        posX=mine.x,
        posY=mine.y,
        templateId=template,
        type=MINE_TYPE,
        occupyPlayerId=0,
        level=int(row.get("Grades", 0)),
        refreshTime=max(0, int((cycle + MINE_PERIOD - now).total_seconds() * 1000)),
        state=state,
        createDate=game_date(cycle),
        fightCapaity=guard_capacity(templates, guard),
        bossType=0,
        size=0,
    )
    if holder is not None:
        msg.occupyPlayerId, msg.occupyPlayerName, msg.fightCapaity = holder.character_id, name, holder.capacity
        if guild:
            msg.occupyLeagueName = guild
    msg.armyPawn.add(id=mine.id, armyId=mine.id, tempateId=guard, ownPawns=1)
    return msg


def occupy_world(
    snap: PlayerSnapshot, mine: Mine, template: int, cycle: datetime, capacity: int, now: datetime
) -> WildLand:
    """Como ``occupy``, com o mapa, o ciclo do mundo (uma ocupação por mina e ciclo) e o poder de quem ocupou."""
    land = occupy(snap, mine, template, now)
    land.map_id, land.cycle_at, land.capacity = mine.map_id, cycle, capacity
    return land


def held(snap: PlayerSnapshot) -> list[WildLand]:
    """Minas ocupadas no ciclo atual (o limite de 2 do cliente conta estas)."""
    return _current(snap)


def land_at(snap: PlayerSnapshot, x: int, y: int) -> WildLand | None:
    """Ocupação do ciclo atual no tile (o 5179 manda "x,y", o ``wildPox`` do 152)."""
    return next((w for w in _current(snap) if (w.pos_x, w.pos_y) == (x, y)), None)


def give_up(snap: PlayerSnapshot, land: WildLand) -> None:
    snap.wild_lands.remove(land)


def mine_msg(
    snap: PlayerSnapshot, world: World, templates: GameTemplates, mine: Mine, state: int, capacity: int, guild: str = ""
) -> pb.WildLandMsg:
    """Como no 4129 e no 140 do oficial: a livre não tem ``occupyPlayerName``; a ocupada leva o nome, o
    poder do jogador em ``fightCapaity`` e a guilda em ``occupyLeagueName`` (só turco), como a do mundo."""
    land = occupied(snap, mine)
    template, guard = draw(snap, world, templates, mine)
    if land is not None and land.template_id:
        template = land.template_id
    row = templates.get("MapPhysicsTempInfos", template) or {}
    msg = pb.WildLandMsg(
        id=mine.id,
        mapId=BASE_MAP,
        posX=mine.x,
        posY=mine.y,
        templateId=template,
        type=MINE_TYPE,
        occupyPlayerId=0,
        level=int(row.get("Grades", 0)),
        refreshTime=int(row.get("RefreshTime", 0)) * 1000,
        state=state,
        createDate=game_date(cycle_start(snap)),
        fightCapaity=MINE_CAPACITY,
        bossType=0,
        size=0,
    )
    if land is not None:
        msg.occupyPlayerId, msg.occupyPlayerName = snap.character.id or 0, snap.character.nickname or ""
        msg.fightCapaity = capacity
        if guild:
            msg.occupyLeagueName = guild
    msg.armyPawn.add(id=mine.id, armyId=mine.id, tempateId=guard, ownPawns=1)
    return msg


def yield_row(templates: GameTemplates, land: WildLand, created: datetime) -> pb.WildYieldMsg:
    """Linha do 152 de uma mina ocupada, com o nível gravado nela."""
    row = templates.get("MapPhysicsTempInfos", land.template_id) or {}
    grade = int(row.get("Grades", 0))
    # mundo: "Autaric Plains(2487,2632)" (oficial_20261023-171155-1 #3078); castelo: "(16,34)" (#26)
    place = "" if land.map_id == BASE_MAP else map_name(templates, land.map_id)
    return pb.WildYieldMsg(
        wildPoxName=f"{place}({land.pos_x},{land.pos_y})",
        wildPox=f"{land.pos_x},{land.pos_y}",
        wildGrade=grade,
        # formato do oficial inglês (152, tutorial_en #751: "Gold Mine Lvl. 10")
        wildName=f"{row.get('MapPhysicsTempName', '')} Lvl. {grade}",
        wildYield=int(row.get("Property4", 0)),
        wildRefreshTime=int(row.get("RefreshTime", 0)),
        mapId=land.map_id,
        createTime=game_date(created),
    )


def mine_yield(snap: PlayerSnapshot, templates: GameTemplates) -> list[pb.WildYieldMsg]:
    """152: uma linha por mina ocupada no ciclo atual (inglês #751, #804)."""
    return [yield_row(templates, land, cycle_start(snap)) for land in _current(snap)]


def mine_gold(snap: PlayerSnapshot, templates: GameTemplates) -> int:
    """Ouro por hora das minas ocupadas (inglês: o goldYield do 109 vai de 280, #749, a 1040 com a 1ª, #772)."""
    return sum(y.wildYield for y in mine_yield(snap, templates))
