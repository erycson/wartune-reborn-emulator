"""Minas de ouro do mapa do castelo (``WildLandMsg`` type 20). As minas vêm do catálogo do mundo
(``domain/world.py``); o ciclo e as ocupações são do jogador (``Castle.mines_at`` e ``wild_lands``).

Cada conta tem a sua cópia das minas (inglês #532 contra o turco replay #706: mesmos ids e tiles): a
instância, os robôs, os ids do armyPawn e o
createDate mudam de uma para a outra, e a ocupação de outro jogador não aparece nem bloqueia. O guia do
tutorial (m8 NewbieBaseActionMediator, alvo 80) procura as duas primeiras pelos pixels (320,680) e (720,680).
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from ..domain import gameday
from ..domain.models import PlayerSnapshot, WildLand
from ..domain.world import Mine, World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from .outer_city import BASE_MAP, grid_of, template_of

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


def mine_msg(
    snap: PlayerSnapshot, world: World, templates: GameTemplates, mine: Mine, state: int, capacity: int
) -> pb.WildLandMsg:
    """Como no 4129 e no 140 do oficial: a livre não tem ``occupyPlayerName``; a ocupada leva o nome e o
    poder do jogador em ``fightCapaity``."""
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
    msg.armyPawn.add(id=mine.id, armyId=mine.id, tempateId=guard, ownPawns=1)
    return msg


def mine_yield(snap: PlayerSnapshot, templates: GameTemplates) -> list[pb.WildYieldMsg]:
    """152: uma linha por mina ocupada no ciclo atual (inglês #751, #804), com o nível gravado nela."""
    out = []
    for land in _current(snap):
        row = templates.get("MapPhysicsTempInfos", land.template_id) or {}
        grade = int(row.get("Grades", 0))
        out.append(
            pb.WildYieldMsg(
                wildPoxName=f"({land.pos_x},{land.pos_y})",
                wildPox=f"{land.pos_x},{land.pos_y}",
                wildGrade=grade,
                # formato do oficial inglês (152, tutorial_en #751: "Gold Mine Lvl. 10")
                wildName=f"{row.get('MapPhysicsTempName', '')} Lvl. {grade}",
                wildYield=int(row.get("Property4", 0)),
                wildRefreshTime=int(row.get("RefreshTime", 0)),
                mapId=BASE_MAP,
                createTime=game_date(cycle_start(snap)),
            )
        )
    return out


def mine_gold(snap: PlayerSnapshot, templates: GameTemplates) -> int:
    """Ouro por hora das minas ocupadas (inglês: o goldYield do 109 vai de 280, #749, a 1040 com a 1ª, #772)."""
    return sum(y.wildYield for y in mine_yield(snap, templates))
