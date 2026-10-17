"""Cidade externa (mapa-múndi): posição do exército, grade visível e castelo que muda de lugar.

Regras vindas do cliente (`OuterCityController`, `WorldMapControler`, `WorldMapHelper`) e da captura
`transfer_kampi_sistemi.json` (5176 -> 140, 152, 105). O mapa é compartilhado só no que o servidor
guarda: castelos e minas ocupadas de quem já jogou (ver docs/cidade-externa.md). Exército andando de
outro jogador e terra selvagem fora das 4 minas não existem aqui.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..domain.models import Castle, PlayerSnapshot, WildLand
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates

TILE = 20  # o cliente manda pixels (PosMoveMsg.routes); curPosX * 20 é o pixel do cliente
GRID = 50  # a grade pedida pelo cliente é "x_y" de 50 × 50 tiles (OuterCitySocketOutManager)
HOME_OFFSET = 2  # army_msg: o exército fica 2 tiles antes do castelo
ATTACK_PRICE = 100  # ConfigInfos AddAttck_Point: diamantes por ataque extra (AttackAlertFrame)
ENERGY_SAME_MAP = 100  # MapPhysicsCastle: energia para mudar de posição no mesmo mapa
ENERGY_OTHER_MAP = 200  # WorldMapControler: energia para mudar de mapa (captura: 500 -> 300)
BASE_MAP, INSTANCE_MAP = 100, 100_000  # mapas do castelo começam em 100000xxx (characters.GridCastlePlacement)
DATE = "%Y-%m-%d %H:%M:%S"


def home(castle: Castle) -> tuple[int, int, int]:
    """(mapa, x, y) do exército parado no castelo."""
    return castle.map_id, castle.pos_x - HOME_OFFSET, castle.pos_y - HOME_OFFSET


def position(castle: Castle, moved: tuple[int, int, int] | None) -> tuple[int, int, int]:
    """Onde está o exército: o último ponto andado nesta sessão, ou o castelo."""
    return moved if moved is not None and moved[0] == castle.map_id else home(castle)


def grid_of(x: int, y: int) -> str:
    return f"{x // GRID}_{y // GRID}"


def map_allowed(map_id: int, grade: int) -> bool:
    """WorldMapHelper.chcekMapId: mapas 1 a 5 têm nível mínimo 11, 21, 31, 41 e 51; o -1 não abre."""
    if map_id == -1:
        return False
    needs = {1: 11, 2: 21, 3: 31, 4: 41, 5: 51}.get(map_id)
    return needs is None or grade >= needs


def template_of(map_id: int) -> int:
    """O mapa do castelo (100000xxx) é uma cópia do modelo 100 (Loş Sahil), como no OuterCityController."""
    return BASE_MAP if map_id >= INSTANCE_MAP else map_id


def map_size(templates: GameTemplates, map_id: int) -> tuple[int, int] | None:
    """Tamanho do mapa em tiles (MapInfos.Width/Height estão em pixels)."""
    row = templates.get("MapInfos", template_of(map_id), key="Id")
    if row is None:
        return None
    return int(row["Width"]) // TILE, int(row["Height"]) // TILE


def inside(templates: GameTemplates, map_id: int, x: int, y: int) -> bool:
    size = map_size(templates, map_id)
    return size is not None and 0 <= x < size[0] and 0 <= y < size[1]


def centre(templates: GameTemplates, map_id: int) -> tuple[int, int]:
    """Onde o castelo cai ao chegar num mapa novo.

    ponytail: o oficial escolhe um ponto livre; sem outros castelos no servidor, usamos o centro
    (captura: mapa 2 em 2191,1952, perto do centro de 4000×4000 tiles).
    """
    size = map_size(templates, map_id) or (0, 0)
    return size[0] // 2, size[1] // 2


def energy_diamonds(castle: Castle, top: int, need: int) -> int:
    """Diamantes para completar a energia de teleporte (``ceil((máximo - atual) / 5)``, como o cliente).
    Zero quando já basta para ``need``."""
    if castle.energy >= need:
        return 0
    return math.ceil((top - castle.energy) / 5)


# -- minas de ouro ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Mine:
    """Mina de ouro do mapa 100 (``WildLandMsg`` type 20). O guarda é um soldado só (``ownPawns`` 1)."""

    id: int
    x: int
    y: int


# As 4 minas do mapa 100 nas capturas (replay #706, cevre #11): mesmos ids e posições para contas
# diferentes, então são do modelo do mapa. O guia do tutorial (m8 NewbieBaseActionMediator, alvo 80)
# procura as duas primeiras pelos pixels (320,680) e (720,680).
MINES = (Mine(853876, 16, 34), Mine(853877, 36, 34), Mine(853874, 71, 54), Mine(853875, 54, 64))
MINE_TYPE, MINE_SON_TYPE = 20, 2006  # WildLandMsg.type; MapPhysicsTempInfos.SonType (missão 60, Para1)
MINE_FREE, MINE_FIGHTING = 1, 4  # WildLandMsg.state
MINE_CAPACITY = 324  # fightCapaity da mina livre nas capturas
# Refresh: RefreshTime 43200 s em todas as minas (MapPhysicsTempInfos). A fase do ciclo é do mundo:
# ponytail: o replay abriu às 12:19:54 e a cevre às 19:48:57; usamos a do replay.
MINE_EPOCH = datetime(2026, 5, 21, 12, 19, 54, tzinfo=UTC)
MINE_PERIOD = timedelta(hours=12)
# (dedução) nível sorteado a cada refresh: as duas capturas têm 8, 9 e 10 (replay: 8, 9, 10, 10; cevre:
# 9, 9, 10, 10). Template = MapPhysicsTempInfos (Grades = nível, Property4 = ouro por hora).
MINE_TEMPLATE = {8: 200408, 9: 200409, 10: 200410}
# guarda por nível: visto 6504 no nível 8 (replay) e 6505 nos níveis 9 e 10 (replay e cevre)
MINE_GUARD = {8: 6504, 9: 6505, 10: 6505}


@dataclass(frozen=True, slots=True)
class Holder:
    """Dono da mina: o próprio jogador ou outro. ``capacity`` é o poder do dono (``fightCapaity``)."""

    id: int
    name: str
    capacity: int


def mine_at(map_id: int, x: int, y: int) -> Mine | None:
    if template_of(map_id) != BASE_MAP:
        return None
    return next((m for m in MINES if (m.x, m.y) == (x, y)), None)


def mines_in(grids: set[str]) -> list[Mine]:
    return [m for m in MINES if grid_of(m.x, m.y) in grids]


def cycle_start(now: datetime) -> datetime:
    """Começo do ciclo de refresh em que ``now`` cai. Ocupação feita antes dele já venceu."""
    return MINE_EPOCH + ((now - MINE_EPOCH) // MINE_PERIOD) * MINE_PERIOD


def draw(mine: Mine, start: datetime) -> tuple[int, int]:
    """(template, guarda) da mina no ciclo que começou em ``start``. A semente é a mina e o começo do
    ciclo: todo jogador vê o mesmo sorteio, e ele muda a cada refresh."""
    level = random.Random(f"{mine.id}:{start.isoformat()}").choice(tuple(MINE_TEMPLATE))
    return MINE_TEMPLATE[level], MINE_GUARD[level]


def occupied(snap: PlayerSnapshot, mine: Mine) -> WildLand | None:
    """Ocupação do próprio jogador. Quem chama antes precisa ter rodado ``castle.expire_mines``."""
    return next((w for w in snap.wild_lands if w.wild_id == mine.id), None)


def mine_msg(
    templates: GameTemplates, mine: Mine, start: datetime, state: int, holder: Holder | None
) -> pb.WildLandMsg:
    """Como no 4129 e no 140 do oficial: a livre não tem ``occupyPlayerName``; a ocupada leva o nome e o
    poder do dono em ``fightCapaity``."""
    template, guard = draw(mine, start)
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
        createDate=start.strftime(DATE),
        fightCapaity=MINE_CAPACITY,
        bossType=0,
        size=0,
    )
    if holder is not None:
        msg.occupyPlayerId, msg.occupyPlayerName, msg.fightCapaity = holder.id, holder.name, holder.capacity
    msg.armyPawn.add(id=mine.id, armyId=mine.id, tempateId=guard, ownPawns=1)
    return msg


def mine_yield(snap: PlayerSnapshot, templates: GameTemplates) -> list[pb.WildYieldMsg]:
    """152: uma linha por mina ocupada (replay #743, #794). Ocupação válida é do ciclo atual, então o
    sorteio é o do começo do ciclo em que ela foi feita."""
    out = []
    for mine in MINES:
        land = occupied(snap, mine)
        if land is None:
            continue
        start = cycle_start(land.occupied_at)
        row = templates.get("MapPhysicsTempInfos", draw(mine, start)[0]) or {}
        grade = int(row.get("Grades", 0))
        out.append(
            pb.WildYieldMsg(
                wildPoxName=f"({mine.x},{mine.y})",
                wildPox=f"{mine.x},{mine.y}",
                wildGrade=grade,
                wildName=f"{row.get('MapPhysicsTempName', '')} {grade} seviye",
                wildYield=int(row.get("Property4", 0)),
                wildRefreshTime=int(row.get("RefreshTime", 0)),
                mapId=BASE_MAP,
                createTime=start.strftime(DATE),
            )
        )
    return out


def mine_gold(snap: PlayerSnapshot, templates: GameTemplates) -> int:
    """Ouro por hora das minas ocupadas (replay: o goldYield do 109 vai de 280 para 960 com a 1ª)."""
    return sum(y.wildYield for y in mine_yield(snap, templates))


def mine_battle(snap: PlayerSnapshot, templates: GameTemplates, mine: Mine, guard: int) -> dict[str, object]:
    """Spec da luta da mina (replay #718): battleType 1 no mapa 100, as tropas do exército em duas
    pilhas (pos 3 e 9), o herói na 4 e o guarda na 5. Vida da pilha = Live × soldados / 100."""
    soldiers: list[dict[str, object]] = []
    pawn = next((p for p in snap.pawns if p.army_count > 0), None)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    if pawn is not None and tpl is not None:
        half = (pawn.army_count + 1) // 2
        for living, pos, count in ((1, 3, half), (2, 9, pawn.army_count - half)):
            if count <= 0:
                continue
            hp = max(1, int(tpl["Live"]) * count // 100)
            soldiers.append(
                {"livingId": living, "tempId": pawn.template_id, "type": 1, "side": 1, "pos": pos,
                 "initHp": hp, "hp": hp, "qteTime": 0, "castTime": 4000,
                 "skillId": [int(tpl["DefaultSkill"])]}
            )  # fmt: skip
    guard_row = templates.get("PawnTempInfos", guard) or {}
    hp = max(1, int(guard_row.get("Live", 100)) // 100)
    soldiers.append(
        {"livingId": 4, "tempId": guard, "type": 1, "side": 2, "pos": 5,
         "initHp": hp, "hp": hp, "qteTime": 0, "castTime": 6000}
    )  # fmt: skip
    return {
        "battleType": 1,
        "mapTempId": BASE_MAP,
        "attackModel": 2,
        "battleScene": 4,
        "soldiers": soldiers,
        "heroes": [],
        "player": {"livingId": 3, "pos": 4},
    }


def occupy(snap: PlayerSnapshot, mine: Mine, now: datetime) -> WildLand:
    land = WildLand(snap.character.id or 0, mine.id, now)
    snap.wild_lands.append(land)
    return land


def rival_castle_msg(castle: Castle, name: str) -> pb.BaseCastleMsg:
    """Castelo de outro jogador no 4129 (o do próprio jogador é ``builders.login.castle_msg``)."""
    return pb.BaseCastleMsg(
        id=castle.id or 0,
        mapId=castle.map_id,
        posX=castle.pos_x,
        posY=castle.pos_y,
        type=1,
        occupyPlayerId=castle.character_id,
        occupyPlayerName=name,
        state=castle.state,
        castleName=castle.name,
        leftEnergy=castle.energy,
        grade=castle.grade,
    )
