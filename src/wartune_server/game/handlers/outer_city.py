"""Cidade externa (mapa do castelo): grade de exércitos, andar, voltar ao castelo, ataques extras,
mudar o castelo de lugar e a volta para a cidade no fim do tutorial.

Regras e fontes em ``game/outer_city.py``, ``mines.py``, ``robots.py``, ``monsters.py``, ``bosses.py`` e
``docs/cidade-externa.md``. O mapa do castelo é uma instância do jogador (o castelo e as 4 minas do
mapa 100); nos mapas compartilhados (1 a 5) aparecem os castelos dos outros jogadores. Quando o cliente
pede algo que depende de exército alheio ou de terra selvagem, o pedido é recusado com log e o que o
cliente precisa para não travar é mandado.
"""

from __future__ import annotations

import asyncio
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from ...domain.errors import NotFoundError
from ...domain.models import (
    Castle,
    Item,
    Mail,
    MailType,
    PlayerSnapshot,
    TreasureCacheOpen,
    WildLand,
    WildMonsterKill,
)
from ...domain.world import Mine, RobotCastle
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import pay
from .. import arena as A
from .. import bosses, mines, monsters, npc_castles, rewards, robots, rules, social
from .. import caches as tc
from .. import castle as cs
from .. import outer_city as oc
from ..battle import Battle
from ..builders import login as b
from ..builders.army import castle_pawns
from ..builders.player import quest_update
from ..castle import S_CASTLE_YIELD, castle_yield, politics_msg, yield_msg
from ..mail import SYSTEM_SENDER, notify, stage
from ..router import router
from ..session import GameSession
from . import events
from .campaign import player_hero, quarry_fight
from .login import army, player_info
from .player import S_CHAT, alert, hero_after_fight, hp_pack
from .vip import vip_right
from .wild_boxes import drop_box, send_boxes

S_PLAYER, S_RESET, S_MAP_SYNC, S_TRANSFER, S_RETURN = 3, 4202, 140, 105, 98
S_MAP_BOSS, S_PHYSICS, S_GRID_ARMY, S_FIGHT_MOVIE = 4938, 4129, 169, 4382
S_FULL_ARMY, S_REPORT, S_ARMY_PAWN, S_QUESTS, S_POLITICS = 150, 4103, 100, 112, 152
S_ITEMS, S_UNOCCUPY, S_CASTLE_TIME, S_CASTLE_DEFENSE = 115, 108, 4452, 118
WORLD = 2  # ChatChannelMsg.channel dos anúncios para o servidor
S_TELEPORT, S_TELEPORT_FAIL = 4237, 4263
TELEPORT_ENERGY, TELEPORT_POINT = 100, 100  # TransmitHandler
VIP_PLUNDER_CRYSTALS = 7  # VipPrerogativeTempInfos "Bonus Kyanite from Plunder" (500 do VIP 4 em diante)
ARMY_IDLE, ARMY_MOVING, ARMY_FIGHTING = 0, 1, 2  # MapUpdatedMsg/ArmyArmyMsg.state
# tutorial_en #773-#777: 18 tiles em 2,34 s (do 140 andando ao 140 parado). ponytail: velocidade fixa, sem
# montaria nem efeitos
WALK_SECONDS_PER_TILE = 0.13
MAP_ARMY, MAP_WILD = 3, 1  # MapUpdatedMsg.updatedType
OCCUPY = 7  # QuestCondictionInfos.CondictionType: ocupar terra (Para1 = SonType, missão 60)
LEED_MINE = 9  # LeedTemp: ocupar mina (tutorial_en #748)
ATTACK_CASTLE = 8  # QuestCondictionInfos.CondictionType: atacar cidade (100, 411 e 765; Para1 1 = vitória)
MAP_CASTLE, CASTLE_FIGHTING, CASTLE_IDLE = 2, 4, 1  # MapUpdatedMsg.updatedType / BaseCastleMsg.state (inglês #1656)


def _army_now(s: GameSession, state: int = ARMY_IDLE) -> pb.ArmyArmyMsg:
    """O próprio exército onde ele está agora (no castelo ou no último ponto andado)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    msg = army(s, snap)[0]
    msg.mapId, msg.curPosX, msg.curPosY = oc.position(snap.castle, s.outer_army)
    msg.state = state
    return msg


def _army_brief(s: GameSession, state: int = ARMY_IDLE) -> pb.ArmyArmyMsg:
    """O exército como o oficial manda no 140 e no 169 (compacto, com ``heroTempId`` e ``job``)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    return b.brief_army(_army_now(s), rules.job_type(snap.character.job), snap.leader.template_id, state)


def _grid_msg(s: GameSession, grids: set[str], map_id: int) -> pb.OutercityArmyUpdatedGridMsg:
    """169: o exército próprio se cair numa das grades pedidas no mesmo mapa; senão lista vazia."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    msg = pb.OutercityArmyUpdatedGridMsg()
    map_now, x, y = oc.position(snap.castle, s.outer_army)
    if map_id == map_now and oc.grid_of(x, y) in grids:
        msg.updatedArmy.add().CopyFrom(_army_brief(s))
    return msg


def _send_player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _castle_state(s: GameSession) -> None:
    """105 com o castelo como está: resposta de recusa (o cliente só troca de lugar se a posição mudar)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    castle = snap.castle
    s.send(
        S_TRANSFER,
        pb.CastleReqMsg(magId=castle.map_id, posX=castle.pos_x, posY=castle.pos_y, leftEnergy=castle.energy),
    )


async def refresh(s: GameSession, push: bool = False) -> None:
    """Refresh de 12 h das minas (``castle.settle`` vira o ciclo). Sem tarefa periódica: roda ao logar, nos pedidos
    de mina (8201, 5160 e o fim da luta), em todo ``settle`` de ouro e no 20008 (``push``). Num mapa do mundo o
    ciclo é o do mundo (``mines.world_cycle_start``): o castelo que entrou num mapa do mundo antes disso é alinhado
    aqui (as minas dele, de um ciclo que não é o do mundo, caem sem carta). Cada mina vencida rende uma carta;
    com ``push`` (o jogador online na virada) vão também 109 e 152 por mina e o 148, como no oficial
    (oficial_20261023-171155-1 #170-#175). (dedução) a virada sai no 20008 seguinte, até ~60 s depois da hora."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    now, castle = s.ctx.clock.now(), snap.castle
    if filled := mines.backfill(snap, s.ctx.world, s.ctx.templates):
        await s.ctx.characters.save(*filled)
    if mines.is_world(s.ctx.world, castle.map_id):
        start = mines.world_cycle_start(s.ctx.world, now)
        if castle.mines_at is None or (start - castle.mines_at) % mines.MINE_PERIOD:
            cs.settle(snap, s.ctx.templates, now)
            castle.mines_at = start
            s.log.info("ciclo das minas alinhado ao do mundo", mapa=castle.map_id, ciclo=start.isoformat())
            await s.ctx.characters.save(snap.character, castle)
            return
    if castle.mines_at is not None and now < mines.cycle_end(snap):
        return
    before, end = mines.held(snap), mines.cycle_end(snap)
    cs.settle(snap, s.ctx.templates, now)
    gone = [w for w in before if w not in mines.held(snap)]
    await s.ctx.characters.save(snap.character, castle)
    await _mines_over(s, gone, end, push)


async def _mines_over(s: GameSession, gone: list[WildLand], end: datetime, push: bool) -> None:
    """Uma carta por mina vencida (148 só com ``push``: no login o cliente lê o correio por conta própria) e, com
    ``push``, 109 e 152 com as minas que ainda faltam sair (#170-#175: 3480 -> 2400 -> 1240).
    TODO(inventado): título e texto da carta (o cliente lê o correio por HTTP; a captura só tem o 148)."""
    snap = s.snapshot
    assert snap is not None
    templates, created = s.ctx.templates, end - mines.MINE_PERIOD
    left = list(gone)
    for land in gone:
        left.remove(land)
        row = mines.yield_row(templates, land, created)
        if push:
            rows = [mines.yield_row(templates, w, created) for w in left]
            gold = yield_msg(snap, templates, s.ctx.clock.now())
            gold.goldYield += sum(r.wildYield for r in rows)
            s.send(S_CASTLE_YIELD, gold)
            politics = politics_msg(snap, templates)
            politics.wildYield.extend(rows)
            s.send(S_POLITICS, politics)
        text = f"Your occupation of {row.wildName} at {row.wildPoxName} has ended: the mine was refreshed."
        letter = Mail(snap.character.id or 0, end, row.wildName, text, mail_type=MailType.SYSTEM,
                      send_type=SYSTEM_SENDER)  # fmt: skip
        await s.ctx.characters.write(lambda uow, m=letter: stage(uow, m))  # type: ignore[misc]
        s.log.info("mina venceu", mina=land.wild_id, mapa=land.map_id, carta=letter.id)
        if push:
            notify(s.ctx.online, letter)


async def _killed(s: GameSession, map_id: int, now: datetime) -> set[int]:
    """Ids dos monstros do mapa já abatidos neste ciclo (por qualquer jogador)."""
    cycle = monsters.cycle_start(s.ctx.templates, now)
    return await s.ctx.characters.read(lambda uow: uow.wild_kills.in_cycle(map_id, cycle))


async def _boss_info(s: GameSession, map_id: int) -> None:
    assert s.snapshot is not None
    now = s.ctx.clock.now()
    killed = await _killed(s, map_id, now)
    ctx = s.ctx
    s.send(S_MAP_BOSS, bosses.boss_msg(ctx.world, ctx.templates, ctx.wilds, s.snapshot.character, map_id, killed, now))


async def _opened(s: GameSession, map_id: int) -> set[tuple[int, datetime]]:
    """(id, nascimento) dos Treasure Caches do mapa já abertos (por qualquer jogador)."""
    return await s.ctx.characters.read(lambda uow: uow.cache_opens.on_map(map_id))


def _cache_state(s: GameSession, c: tc.Cache) -> int:
    fight = s.ctx.wilds.fighting.get((c.map_id, c.id, c.born))
    return tc.CACHE_FIGHTING if fight is not None and fight.running else tc.CACHE_ALIVE


def _cache_sync(s: GameSession, c: tc.Cache, state: int) -> None:
    """140 do baú (state 4 em luta, 0 aberto, 1 de volta) a quem vê a grade dele (#328, #381, #667)."""
    land = tc.cache_msg(s.ctx.templates, c, s.ctx.clock.now(), state)
    for other in viewers(s, c.map_id):
        assert other.outer_view is not None
        if oc.grid_of(c.x, c.y) in other.outer_view[1]:
            other.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))


@router.on(9525)
async def map_boss(s: GameSession, msg: pb.MapBossQuestMsg) -> None:
    """Painel dos chefes (4938). Os baús fechados vão no 8201 (visto: oficial_20261023-171155-1 #6961-#6970)."""
    await _boss_info(s, msg.mapId)


def viewers(s: GameSession, map_id: int) -> list[GameSession]:
    """Sessões online cujo último 8201 com monstros foi neste mapa (quem vê os monstros dele)."""
    return [o for o in s.ctx.online.sessions() if o.outer_view is not None and o.outer_view[0] == map_id]


def _monster_sync(s: GameSession, m: monsters.Monster, state: int) -> None:
    """140 do monstro (state 4 em luta com o ``curArmyId`` de quem ataca, 0 abatido, 1 de volta) a quem vê a grade."""
    assert s.snapshot is not None
    land = monsters.monster_msg(s.ctx.world, s.ctx.templates, m, state, s.snapshot.character.id or 0)
    for other in viewers(s, m.map_id):
        assert other.outer_view is not None
        if oc.grid_of(m.x, m.y) in other.outer_view[1]:
            other.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))


@router.on(5004)
async def user_display(s: GameSession, msg: pb.OutercityReqMsg) -> None:
    """Pede os jogadores da tela. O cliente não lê resposta (``client_listens false``): os exércitos
    chegam no 5181 e nas atualizações ao vivo, então só registramos."""
    s.log.info("5004 tela", mapa=msg.mapId)


@router.on(5181)
async def army_grid(s: GameSession, msg: pb.OutercityReqMsg) -> None:
    """Grade de exércitos (``files`` = "x_y,..."). Sem resposta própria: no oficial (tutorial_en
    #529-#533) o 5181 não tem S>C; a grade vem no 169 que o 8201 manda logo depois (ver 8201)."""
    s.log.info("5181 grade", mapa=msg.mapId, grades=len(msg.files.split(",")))


async def _rivals(s: GameSession, grids: set[str], map_id: int) -> list[tuple[Castle, str]]:
    """Castelos de outros jogadores nas grades pedidas de um mapa compartilhado (1 a 5). A instância
    100000xxx é do jogador: no oficial ela só tem o castelo dele e 2 robôs (tutorial_en #532)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    if map_id != snap.castle.map_id or oc.template_of(map_id) == oc.BASE_MAP:
        return []
    own = snap.character.id or 0
    castles = await s.ctx.characters.read(lambda uow: uow.castles.on_map(map_id))
    near = [c for c in castles if c.character_id != own and oc.grid_of(c.pos_x, c.pos_y) in grids]
    if not near:
        return []
    chars = await s.ctx.characters.read(lambda uow: uow.characters.by_ids([c.character_id for c in near]))
    names = {c.id: c.nickname or "" for c in chars}
    return [(c, names.get(c.character_id, "")) for c in near]


@router.on(8201)
async def physics_by_grid(s: GameSession, msg: pb.PhysicUpdateReqMsg) -> None:
    """4129 com as minas da grade (ciclo atual do jogador) ou, num mapa compartilhado, os monstros dos Wilds;
    o próprio castelo e, num mapa compartilhado, os castelos de outros jogadores; depois 169 com o exército
    próprio se cair numa grade pedida do mesmo mapa.

    ponytail: os exércitos alheios não aparecem (o 169 é só o próprio): a posição de outro jogador só existe
    na sessão dele, e não há presença entre sessões.
    """
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    await refresh(s)
    grids = {g for g in msg.reqGrid.split(",") if g}
    reply = pb.PhysicListUpdateMsg(reqGrid=msg.reqGrid)
    now = s.ctx.clock.now()
    if oc.template_of(msg.mapId) == oc.BASE_MAP:  # tutorial_en #532: as minas vêm antes do castelo
        for mine in mines.mines_in(s.ctx.world, grids):
            land = mines.mine_msg(snap, s.ctx.world, s.ctx.templates, mine, mines.MINE_FREE, _capacity(s))
            reply.wildLand.append(land)
    if found_mines := mines.world_mines_in(s.ctx.world, s.ctx.templates, msg.mapId, grids):
        holders = await _holders(s, msg.mapId, now)
        for mine in found_mines:
            reply.wildLand.append(_world_land(s, mine, now, holders.get(mine.id)))
    found = monsters.on_map(s.ctx.world, s.ctx.templates, msg.mapId, now)
    boxes = tc.on_map(s.ctx.world, s.ctx.templates, msg.mapId, now)
    if found or boxes:
        s.outer_view = (msg.mapId, grids, monsters.cycle_start(s.ctx.templates, now))
    if found:
        killed = await _killed(s, msg.mapId, now)
        for m in found:
            # no meio das terras, antes dos castelos (só turco: transfer_kampi_sistemi #14)
            if oc.grid_of(m.x, m.y) in grids and (state := s.ctx.wilds.state(m, killed)) != monsters.MONSTER_GONE:
                reply.wildLand.append(monsters.monster_msg(s.ctx.world, s.ctx.templates, m, state))
    s.outer_caches, s.outer_caches_at = {}, now
    if boxes:
        opened = await _opened(s, msg.mapId)
        for c in boxes:
            if oc.grid_of(c.x, c.y) in grids and (c.id, c.born) not in opened:
                s.outer_caches[c.id] = c
                reply.wildLand.append(tc.cache_msg(s.ctx.templates, c, now, _cache_state(s, c)))
    reply.baseCastle.add().CopyFrom(b.complete(b.castle_msg(snap, snap.castle)))
    # (visto) tutorial_en #532: os robôs vêm junto com o castelo
    for robot in robots.robots_in(snap, s.ctx.world, msg.mapId, grids):
        left = s.ctx.wilds.shield_left((snap.character.id or 0, robot.id), now)
        reply.baseCastle.add().CopyFrom(b.complete(robots.robot_castle_msg(snap, s.ctx.world, robot, 1, left)))
    # (visto) oficial_20261023-153200-1 #197: os castelos NPC do mundo junto dos castelos
    for npc in npc_castles.castles_in(s.ctx.world, s.ctx.templates, msg.mapId, grids):
        left = s.ctx.wilds.shield_left((0, npc.id), now)
        reply.baseCastle.add().CopyFrom(b.complete(npc_castles.castle_msg(npc, 1, left)))
    for castle, name in await _rivals(s, grids, msg.mapId):
        reply.baseCastle.add().CopyFrom(b.complete(oc.rival_castle_msg(castle, name)))
    s.send(S_PHYSICS, reply)
    # (visto) oficial_20261023-171155-1 #6969-#6971 e #7379: o 4940 com os baús fechados do mapa entre o 4129 e o
    # 169, quando a grade pedida tem um deles
    if any(box.map_id == msg.mapId and oc.grid_of(box.pos_x, box.pos_y) in grids for box in snap.wild_boxes):
        send_boxes(s, msg.mapId)
    s.send(S_GRID_ARMY, _grid_msg(s, grids, msg.mapId))


Holder = tuple[WildLand, str, str]  # ocupação, nome e guilda de quem ocupa


async def _holders(s: GameSession, map_id: int, now: datetime) -> dict[int, Holder]:
    """Quem ocupa cada mina do mapa no ciclo do mundo: id da mina -> (ocupação, nome, guilda). As do próprio jogador
    vêm do snapshot (mais novo que o banco)."""
    snap = s.snapshot
    assert snap is not None
    own, cycle = snap.character.id or 0, mines.world_cycle_start(s.ctx.world, now)
    lands = [w for w in await s.ctx.characters.read(lambda uow: uow.wild_lands.held_on(map_id, cycle))]
    lands = [w for w in lands if w.character_id != own] + [w for w in mines.held(snap) if w.map_id == map_id]
    others = [w.character_id for w in lands if w.character_id != own]
    chars = await s.ctx.characters.read(lambda uow: uow.characters.by_ids(others)) if others else []
    names = {c.id: c.nickname or "" for c in chars} | {own: snap.character.nickname or ""}
    out: dict[int, Holder] = {}
    for w in lands:
        guild = s.ctx.guilds.of(w.character_id)
        out[w.wild_id] = (w, names.get(w.character_id, ""), guild[0].name if guild else "")
    return out


def _world_state(s: GameSession, mine: Mine, now: datetime) -> int:
    fight = s.ctx.wilds.fighting.get((mine.map_id, mine.id, mines.world_cycle_start(s.ctx.world, now)))
    return mines.MINE_FIGHTING if fight is not None and fight.running else mines.MINE_FREE


def _world_land(s: GameSession, mine: Mine, now: datetime, holder: Holder | None, state: int = 0) -> pb.WildLandMsg:
    state = state or _world_state(s, mine, now)
    if holder is None:
        return mines.world_mine_msg(s.ctx.world, s.ctx.templates, mine, now, state)
    return mines.world_mine_msg(s.ctx.world, s.ctx.templates, mine, now, state, *holder)


def _world_sync(s: GameSession, mine: Mine, state: int, holder: Holder | None) -> None:
    """140 da mina do mundo a quem vê a grade dela (e ao próprio jogador, que pode não ter monstros na vista)."""
    land = _world_land(s, mine, s.ctx.clock.now(), holder, state)
    targets = {
        id(o): o for o in viewers(s, mine.map_id) if o.outer_view and oc.grid_of(mine.x, mine.y) in o.outer_view[1]
    }
    targets[id(s)] = s
    for other in targets.values():
        other.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))


async def _other(s: GameSession, user_id: int) -> PlayerSnapshot | None:
    """Snapshot de quem ocupa a mina: o da sessão se online (mais novo que o banco), senão do banco."""
    online = s.ctx.online.get(user_id)
    if online is not None and online.snapshot is not None:
        return online.snapshot
    try:
        snap = await s.ctx.characters.snapshot(user_id)
    except NotFoundError:
        return None
    return snap if snap.castle is not None and snap.leader is not None else None


def roll_monsters(s: GameSession) -> None:
    """Virada do ciclo dos monstros com o jogador online (20008). O cliente guarda os wildLands por tile e só
    tira um com state 0 ou quando a vista sai da grade (``OuterCityModel.updateWildLand``,
    ``removesNSSWildLand``): sem isto, quem fica parado veria os monstros do ciclo anterior. 140 com state 0
    nos velhos e 140 com os novos, nas grades do último 8201."""
    if s.outer_view is None:
        return
    map_id, grids, cycle = s.outer_view
    world, templates, now = s.ctx.world, s.ctx.templates, s.ctx.clock.now()
    _roll_caches(s, map_id, grids)
    start = monsters.cycle_start(templates, now)
    if start == cycle:
        return
    s.outer_view = (map_id, grids, start)
    for when, state in ((cycle, monsters.MONSTER_GONE), (now, monsters.MONSTER_ALIVE)):
        for m in monsters.on_map(world, templates, map_id, when):
            if oc.grid_of(m.x, m.y) in grids:
                land = monsters.monster_msg(world, templates, m, state)
                s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))


def _roll_caches(s: GameSession, map_id: int, grids: set[str]) -> None:
    """Cada baú tem a sua vida: o que venceu sai da vista (140 state 0) e o que nasceu nela entra (140 state 1).
    (dedução) o oficial avisa assim (a captura só mostra o 140 do recém-nascido 828569, #1938); o aberto já saiu
    da lista no fim da luta e não volta antes da vida seguinte (``_opened`` no 8201)."""
    now = s.ctx.clock.now()
    for c in [c for c in s.outer_caches.values() if c.ends <= now]:
        del s.outer_caches[c.id]
        land = tc.cache_msg(s.ctx.templates, c, now, tc.CACHE_GONE)
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))
    for c in tc.on_map(s.ctx.world, s.ctx.templates, map_id, now):
        if oc.grid_of(c.x, c.y) in grids and c.id not in s.outer_caches and c.born > s.outer_caches_at:
            s.outer_caches[c.id] = c
            land = tc.cache_msg(s.ctx.templates, c, now)
            s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))
    s.outer_caches_at = now


@router.on(8254)
async def army_move(s: GameSession, msg: pb.PosMoveMsg) -> None:
    """O exército andou: guarda o último ponto (pixels // 20). Como no oficial (tutorial_en #773-#777): 140 ×2
    andando no ponto de saída e, na chegada, 140 ×2 parado no destino. Sem outro jogador no mapa não
    há o que avisar (4167). Outro exército, mapa diferente, rota vazia ou fora do mapa: ignorado."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    castle = snap.castle
    if msg.armyId != snap.character.id or not msg.routes or msg.mapId != castle.map_id:
        s.log.info("8254 ignorado", exercito=msg.armyId, mapa=msg.mapId)
        return
    x, y = msg.routes[-1].x // oc.TILE, msg.routes[-1].y // oc.TILE
    if not oc.inside(s.ctx.templates, castle.map_id, x, y):
        s.log.info("8254 fora do mapa", x=x, y=y)
        return
    _stop_walk(s)
    _map, x0, y0 = oc.position(castle, s.outer_army)
    _army_sync(s, ARMY_MOVING)
    s.outer_army = (castle.map_id, x, y)
    s.outer_walk = asyncio.create_task(_arrive(s, WALK_SECONDS_PER_TILE * math.dist((x0, y0), (x, y))))


async def _arrive(s: GameSession, seconds: float) -> None:
    await asyncio.sleep(seconds)
    s.outer_walk = None
    if s.battle is None and s.campaign is None:  # numa campanha o 140 é do mapa dela
        _army_sync(s, ARMY_IDLE)


def _stop_walk(s: GameSession) -> None:
    if s.outer_walk is not None:
        s.outer_walk.cancel()
        s.outer_walk = None


@router.on(8326)
async def teleport(s: GameSession, msg: pb.ArmyPositionMsg) -> None:
    """Teleporte do exército no mapa externo: 100 de energia do castelo, ou 100 diamantes sem energia (payType 1
    diamante, 2 vinculado); recusa 4263 (fora do mapa ou sem como pagar). (visto) oficial_20261023-171155-1 #7307-#7310,
    #7469, #7541: 140 do exército parado onde está, 4237 (posição e energia, sem ``mapId``: 200 -> 100 -> 0) e 111
    "Teleportation Complete"; o exército fica no tile novo (#7312). Pagando com energia não vai 3."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    castle, c = snap.castle, snap.character
    map_id, *_ = oc.position(castle, s.outer_army)
    if not oc.inside(s.ctx.templates, map_id, msg.posX, msg.posY):
        s.log.info("8326 fora do mapa", mapa=map_id, x=msg.posX, y=msg.posY)
        s.send(S_TELEPORT_FAIL)
        return
    spent = None
    if castle.energy >= TELEPORT_ENERGY:
        castle.energy -= TELEPORT_ENERGY
    elif (
        spent := pay(c, TELEPORT_POINT, bind=msg.payType == 2, reason="teleport", ref="", now=s.ctx.clock.now())
    ) is None:
        s.log.info("8326 sem energia nem diamantes", energia=castle.energy)
        s.send(S_TELEPORT_FAIL)
        return
    await s.ctx.characters.save(c, castle, *([spent] if spent else []))
    _stop_walk(s)
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))  # um só (#7308)
    s.outer_army = (map_id, msg.posX, msg.posY)
    s.send(S_TELEPORT, pb.ArmyPositionMsg(posX=msg.posX, posY=msg.posY, leftEnergy=castle.energy))
    alert(s, "Teleportation Complete")
    if spent is not None:
        _send_player(s)


@router.on(5161)
async def return_home(s: GameSession, _: pb.PayTypeMsg) -> None:
    """Volta o exército para o castelo (de graça: o botão do exército não checa nada). 98 com a posição."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    _stop_walk(s)
    s.outer_army = None
    _map, x, y = oc.home(snap.castle)
    s.send(S_RETURN, pb.OutercityRspMsg(result=snap.character.id, curPosX=x, curPosY=y))


def _capacity(s: GameSession) -> int:
    assert s.snapshot is not None
    return rules.leader_stats(s.snapshot, s.ctx.templates, s.ctx.clock.now()).fighting_capacity


def _mine_sync(s: GameSession, mine: Mine, state: int) -> None:
    """140 da mina com o dono que ela tem agora (o próprio jogador, se ocupou)."""
    snap = s.snapshot
    assert snap is not None
    land = mines.mine_msg(snap, s.ctx.world, s.ctx.templates, mine, state, _capacity(s))
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))


def _army_sync(s: GameSession, state: int) -> None:
    for _ in range(2):  # o oficial manda o 140 do exército sempre duas vezes
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s, state)))


@router.on(5160)
async def attack(s: GameSession, msg: pb.MapPhysicAttackMsg) -> None:
    """Atacar uma posição do mapa. Mina de ouro livre: luta com o guarda (tutorial_en #723-#727): 140 do
    exército lutando, 140 da mina em luta (state 4) e a 157. Castelo-robô e castelo NPC do mundo: luta (ver
    ``_attack_castle``).
    Monstro dos Wilds: luta (ver ``_attack_monster``). Treasure Cache: luta (ver ``_attack_cache``). Mina já
    ocupada ou castelo de outro jogador: o exército só para (140 parado)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    await refresh(s)
    _stop_walk(s)
    robot = robots.robot_at(snap, s.ctx.world, msg.mapId, msg.posX, msg.posY)
    npc = npc_castles.castle_at(s.ctx.world, s.ctx.templates, msg.mapId, msg.posX, msg.posY)
    if robot is not None or npc is not None:
        target = _robot_target(s, robot) if robot is not None else _npc_target(s, npc)  # type: ignore[arg-type]
        if rows := _attack_castle(s, target):
            await s.ctx.characters.save(*rows)
        return
    boxes = tc.on_map(s.ctx.world, s.ctx.templates, msg.mapId, s.ctx.clock.now())
    if (box := tc.at(boxes, msg.posX, msg.posY)) is not None:
        await _attack_cache(s, box)
        return
    found = monsters.on_map(s.ctx.world, s.ctx.templates, msg.mapId, s.ctx.clock.now())
    if (monster := monsters.at(found, msg.posX, msg.posY)) is not None:
        await _attack_monster(s, monster)
        return
    world_mine = mines.world_mine_at(s.ctx.world, s.ctx.templates, msg.mapId, msg.posX, msg.posY)
    if world_mine is not None:
        await _attack_world_mine(s, world_mine)
        return
    mine = mines.mine_at(s.ctx.world, msg.mapId, msg.posX, msg.posY)
    if mine is None or mines.occupied(snap, mine) is not None or s.battle is not None:
        s.log.info("5160 sem alvo", mapa=msg.mapId, x=msg.posX, y=msg.posY)
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))
        return
    _, guard = mines.draw(snap, s.ctx.world, s.ctx.templates, mine)
    _army_sync(s, ARMY_FIGHTING)
    _mine_sync(s, mine, mines.MINE_FIGHTING)
    spec = oc.guard_battle(snap, s.ctx.templates, guard)

    async def finished(battle: Battle, won: bool) -> None:
        await _mine_over(s, battle, mine, won)

    s.battle = Battle(
        spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings
    )
    s.log.info("batalha da mina", mina=mine.id, battle=s.battle.id)
    s.battle.start()


async def _casualties(
    s: GameSession, battle: Battle, won: bool, scene: int, before_report: Callable[[], None] | None = None
) -> int:
    """150 com o exército sem as tropas mortas (#1760: 0 depois de perder as 172), 4103, a reposição pela reserva
    e 150 e 100 de novo (#1763-#1764: 172 e a reserva 640 -> 468). Com perda, 109 (população) e 3 antes do 4103:
    o Daru é o número de soldados perdidos, ganhando ou perdendo (oficial_20261023-153200-1 #1620-#1625: 116 na
    mina; #1896-#1903: 201 no tesouro; #2004-#2009: 106). Devolve o Daru, que o 4382 mostra na volta ao mapa.
    ``before_report``: o que vai logo antes do 4103 (o prêmio do Treasure Cache, oficial_20261023-171155-1
    #650-#662)."""
    snap = s.snapshot
    assert snap is not None
    hit = oc.lose_troops(snap, s.ctx.templates, battle.troops())
    daru = hit[1] if hit is not None else 0
    healed = hero_after_fight(s, battle.player.hp if battle.player is not None else None)
    report = pb.BattleReportMsg(battleResult=1 if won else 2, strategyBonus=daru, gpBonus=0, battleScene=scene)
    report.failCount, report.goldBonus, report.petGpBonus = s.fail_count, 0, 0
    # o do 154 sai sem o 4902; o depois do 4103 com (só turco: exp_kitabi_kullanim #91-#103)
    s.send(S_FULL_ARMY, b.complete(_army_now(s, ARMY_FIGHTING)), cards=False)
    if hit is not None:
        snap.character.strategy += daru
        castle_yield(s)
        _send_player(s)
    if before_report is not None:
        before_report()
    s.send(S_REPORT, report)
    hp_pack(s, healed)  # (visto) #1899-#1901 (com o 139 no meio, que aqui não há)
    if hit is not None:
        oc.refill(*hit)
    assert snap.leader is not None
    await s.ctx.characters.save(snap.character, snap.leader, *([hit[0]] if hit is not None else []))
    s.send(S_FULL_ARMY, b.complete(_army_now(s, ARMY_FIGHTING)))
    s.send(S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    s.battle_strategy = daru
    return daru


async def _mine_over(s: GameSession, battle: Battle, mine: Mine, won: bool) -> None:
    """Fim da luta da mina, na ordem do oficial (tutorial_en #741-#752): 150, 4103, 150, 100, 140 ×2; vencendo,
    a mina fica do jogador: 112 da missão 60, 4152, 109, 152 com o rendimento e 140 da mina ocupada."""
    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
    await _casualties(s, battle, won, 4)
    _army_sync(s, ARMY_IDLE)
    await refresh(s)  # a luta pode ter cruzado o refresh: a ocupação é do ciclo novo
    now = s.ctx.clock.now()
    if not won or mines.occupied(snap, mine) is not None:
        _mine_sync(s, mine, mines.MINE_FREE)
        return
    assert snap.castle is not None
    cs.settle(snap, templates, now)  # o ouro até agora sai na taxa antiga; a mina conta daqui em diante
    land = mines.occupy(snap, mine, mines.draw(snap, s.ctx.world, templates, mine)[0], now)
    quests = rules.quest_event(snap, templates, OCCUPY, mines.MINE_SON_TYPE, 1)
    await s.ctx.characters.save(snap.character, snap.castle, land, *quests)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    await events.leed_done(s, LEED_MINE)
    castle_yield(s)
    s.send(S_POLITICS, politics_msg(snap, templates))
    _mine_sync(s, mine, mines.MINE_FREE)
    map_id, x, y = oc.position(snap.castle, s.outer_army)
    s.send(S_GRID_ARMY, _grid_msg(s, {oc.grid_of(x, y)}, map_id))  # tutorial_en #754


async def _attack_world_mine(s: GameSession, mine: Mine) -> None:
    """Luta pela mina do mundo (oficial_20261023-171155-1 #3037-#3041): 140 ×2 do exército lutando, 140 da mina em
    luta (state 4) e a 157 (battleType 1, ``mapTempId`` = o mapa). Livre: o guarda do nível sorteado no ciclo. De
    outro jogador: o herói dele (``oc.holder_battle``, TODO(inventado)). Recusa com 140 parado se já há luta, se
    outro está lutando por ela, se é do próprio jogador, se ele já tem ``max_held`` minas (cliente: 2) ou se é de
    alguém da mesma guilda (cliente: ``AttackConsortiaMember``)."""
    snap = s.snapshot
    assert snap is not None
    world, templates, now = s.ctx.world, s.ctx.templates, s.ctx.clock.now()
    cycle = mines.world_cycle_start(world, now)
    holder = (await _holders(s, mine.map_id, now)).get(mine.id)
    own = snap.character.id or 0
    guild = s.ctx.guilds.of(own)
    full = len(mines.held(snap)) >= int(mines.world_settings(world)["max_held"])
    same_guild = holder is not None and guild is not None and holder[2] == guild[0].name
    victim = await _other(s, holder[0].character_id) if holder is not None and holder[0].character_id != own else None
    busy = _world_state(s, mine, now) == mines.MINE_FIGHTING
    mine_own = holder is not None and holder[0].character_id == own
    if s.battle is not None or busy or mine_own or full or same_guild or (holder is not None and victim is None):
        s.log.info("5160 mina do mundo recusada", mina=mine.id, cheio=full, ocupada=mine_own, guilda=same_guild,
                   em_luta=busy)  # fmt: skip
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))
        return
    _army_sync(s, ARMY_FIGHTING)
    _world_sync(s, mine, mines.MINE_FIGHTING, holder)
    if victim is not None:
        spec = oc.holder_battle(snap, templates, A.copy_hero(victim, templates, now), mine.map_id)
    else:
        spec = oc.guard_battle(snap, templates, mines.world_draw(world, templates, mine, cycle)[1])
        spec["mapTempId"] = mine.map_id  # (visto) #3041: mapTempId 1
    taken_from = holder[0].character_id if holder is not None else 0

    async def finished(battle: Battle, won: bool) -> None:
        await _world_mine_over(s, battle, mine, cycle, won, taken_from)

    s.battle = Battle(
        spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings
    )
    s.ctx.wilds.fighting[(mine.map_id, mine.id, cycle)] = s.battle
    s.log.info("batalha da mina do mundo", mina=mine.id, mapa=mine.map_id, dono=taken_from, battle=s.battle.id)
    s.battle.start()


async def _world_mine_over(
    s: GameSession, battle: Battle, mine: Mine, cycle: datetime, won: bool, taken_from: int
) -> None:
    """Fim da luta pela mina do mundo, na ordem do oficial (#3069-#3082): 150, 109, 3, 4103, 150, 100, 140 ×2 do
    exército; vencendo, 109, 152 com a mina, 140 da mina ocupada; depois 169 e o 4382 logo em seguida. Ganha a mina
    se o ciclo é o mesmo e ela ainda está como no começo (livre, ou com quem foi atacado); a de outro jogador sai
    dele (``_evict``). Uma ocupação por mina e ciclo no banco: quem chega depois perde (IntegrityError, log)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    world, templates = s.ctx.world, s.ctx.templates
    s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
    s.ctx.wilds.fighting.pop((mine.map_id, mine.id, cycle), None)
    daru = await _casualties(s, battle, won, 4)
    s.battle_strategy = 0  # (visto) #3082: o 4382 sai aqui mesmo
    _army_sync(s, ARMY_IDLE)
    await refresh(s)
    now = s.ctx.clock.now()
    holder = (await _holders(s, mine.map_id, now)).get(mine.id)
    same = mines.world_cycle_start(world, now) == cycle and (holder[0].character_id if holder else 0) == taken_from
    room = len(mines.held(snap)) < int(mines.world_settings(world)["max_held"])
    land = None
    if won and same and room:
        if holder is not None:
            await _evict(s, holder, mine)
        cs.settle(snap, templates, now)  # o ouro até agora sai na taxa antiga; a mina conta daqui em diante
        template = holder[0].template_id if holder is not None else mines.world_draw(world, templates, mine, cycle)[0]
        land = mines.occupy_world(snap, mine, template, cycle, _capacity(s), now)
        quests = rules.quest_event(snap, templates, OCCUPY, mines.MINE_SON_TYPE, 1)
        try:
            await s.ctx.characters.save(snap.character, snap.castle, land, *quests)
        except IntegrityError:
            s.log.info("mina do mundo já ocupada por outro", mina=mine.id)
            land.cycle_at, land.occupied_at = None, cycle - mines.MINE_PERIOD  # fica como ocupação vencida
            await s.ctx.characters.save(snap.character, snap.castle, land)
            land = None
        else:
            if quests:
                s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
            await events.leed_done(s, LEED_MINE)
            castle_yield(s)
            s.send(S_POLITICS, politics_msg(snap, templates))
    if land is not None:
        _world_sync(s, mine, mines.MINE_FREE, (land, snap.character.nickname or "", _guild_name(s)))
    else:
        _world_sync(s, mine, mines.MINE_FREE, (await _holders(s, mine.map_id, now)).get(mine.id))
    map_id, x, y = oc.position(snap.castle, s.outer_army)
    s.send(S_GRID_ARMY, _grid_msg(s, {oc.grid_of(x, y)}, map_id))
    s.send(S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=0, gold=0, strategy=daru))


def _guild_name(s: GameSession) -> str:
    guild = s.ctx.guilds.of(s.player_id)
    return guild[0].name if guild else ""


async def _evict(s: GameSession, holder: Holder, mine: Mine) -> None:
    """Tira a mina de quem ocupava: o ouro dele até agora sai com ela, a ocupação some do snapshot (se online, o
    da sessão) e do banco, e ele recebe carta, 109 e 152. TODO(inventado): o texto da carta e os avisos."""
    snap = s.snapshot
    assert snap is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    victim = await _other(s, holder[0].character_id)
    land = holder[0]
    if victim is not None and victim.castle is not None:
        cs.settle(victim, templates, now)
        land = next((w for w in victim.wild_lands if w.wild_id == land.wild_id and w.cycle_at == land.cycle_at), land)
        if land in victim.wild_lands:
            victim.wild_lands.remove(land)
        await s.ctx.characters.save(victim.character, victim.castle, delete=(land,))
    else:
        await s.ctx.characters.save(delete=(land,))
    row = mines.yield_row(templates, land, land.cycle_at or now)
    text = f"{snap.character.nickname} defeated your army and took {row.wildName} at {row.wildPoxName}."
    letter = Mail(land.character_id, now, row.wildName, text, mail_type=MailType.SYSTEM, send_type=SYSTEM_SENDER)
    await s.ctx.characters.write(lambda uow: stage(uow, letter))
    notify(s.ctx.online, letter)
    if victim is not None and (other := s.ctx.online.get(land.character_id)) is not None:
        other.send(S_CASTLE_YIELD, yield_msg(victim, templates, now))
        other.send(S_POLITICS, politics_msg(victim, templates))
    s.log.info("mina tomada", mina=mine.id, de=land.character_id)


@router.on(5179)
async def unoccupy_wild_land(s: GameSession, msg: pb.BuildingReqMsg) -> None:
    """Desistir da mina ("Give Up" no mapa ou no conselho: ``FieldItem``, "No gold will be obtained if you abandon
    this quarry"). ``position`` = "x,y" (o ``wildPox`` do 152). O ouro até agora sai com ela (``settle``); responde
    108 com a posição (o cliente zera o dono e mostra o aviso), 109 e 152; a mina do mundo volta livre (140) para
    quem vê. Sem mina ocupada no tile: 108 com posição vazia (o cliente não faz nada). (dedução) sem captura."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    await refresh(s)
    parts = msg.position.split(",")
    land = (
        mines.land_at(snap, int(parts[0]), int(parts[1]))
        if len(parts) == 2 and all(p.isdigit() for p in parts)
        else None
    )
    if land is None:
        s.log.info("5179 sem mina", posicao=msg.position)
        s.send(S_UNOCCUPY, pb.GiveupWildLandMsg(wildLandPos=""))
        return
    now = s.ctx.clock.now()
    cs.settle(snap, s.ctx.templates, now)
    mines.give_up(snap, land)
    await s.ctx.characters.save(snap.character, snap.castle, delete=(land,))
    s.log.info("5179 mina abandonada", mina=land.wild_id, mapa=land.map_id)
    s.send(S_UNOCCUPY, pb.GiveupWildLandMsg(wildLandPos=msg.position))
    castle_yield(s)
    s.send(S_POLITICS, politics_msg(snap, s.ctx.templates))
    mine = mines.world_mine(s.ctx.world, s.ctx.templates, land.map_id, land.wild_id)
    if mine is not None and mines.is_world(s.ctx.world, land.map_id):
        _world_sync(s, mine, mines.MINE_FREE, None)


async def _attack_monster(s: GameSession, m: monsters.Monster) -> None:
    """Luta com monstro dos Wilds (battleType 2). Recusa com 140 parado se já há luta, se o monstro já foi
    abatido no ciclo ou se o catálogo não tem a unidade dele. O 140 dele vai em state 4 a quem vê a grade."""
    snap = s.snapshot
    assert snap is not None
    killed = await _killed(s, m.map_id, s.ctx.clock.now())
    spec = monsters.battle(snap, s.ctx.world, s.ctx.templates, m)
    if s.battle is not None or m.id in killed or spec is None:  # s.battle de novo: houve await
        s.log.info("5160 monstro recusado", monstro=m.id, template=m.template_id, abatido=m.id in killed)
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))
        return
    _army_sync(s, ARMY_FIGHTING)

    async def finished(battle: Battle, won: bool) -> None:
        await _monster_over(s, battle, m, won)

    s.battle = Battle(
        spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings
    )
    s.log.info("batalha com monstro", monstro=m.id, template=m.template_id, battle=s.battle.id)
    s.ctx.wilds.fighting[(m.map_id, m.id, m.born)] = s.battle
    _monster_sync(s, m, monsters.MONSTER_FIGHTING)  # como a mina: o 140 em luta antes da 157
    if m.boss_type == monsters.CHIEF:  # (visto) #7421: o 4938 com o chefe em luta (type 4) antes da 157
        await _boss_info(s, m.map_id)
    s.battle.start()


async def _monster_over(s: GameSession, battle: Battle, m: monsters.Monster, won: bool) -> None:
    """Fim da luta com monstro (visto: oficial_20261023-171155-1 #6943-#6960 e #7227-#7238): 150, 4103 (battleScene
    5, sem Daru: não há tropa), 150, 100 e 140 ×2 do exército. Vencendo, o abate vai para o banco (o primeiro a
    terminar leva; a chave repete em quem chega depois) e conta no limite do dia (``monsters.count_kill``), e então
    cai o baú (gravado; o 4940 vem no 8201 seguinte); o monstro sai do mapa para quem vê (140 state 0) e o 4938 vem
    com os contadores novos. Perdendo, ele volta a state 1 e o exército volta para casa (140 no castelo, #7234)."""
    snap = s.snapshot
    assert snap is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
    s.ctx.wilds.fighting.pop((m.map_id, m.id, m.born), None)
    await _casualties(s, battle, won, monsters.SCENE)
    _army_sync(s, ARMY_IDLE)
    same = monsters.cycle_start(templates, now) == m.born  # luta que cruzou o refresh: o monstro já sumiu
    gone = won and same
    if gone:
        kill = WildMonsterKill(m.map_id, m.id, m.born, snap.character.id or 0, now)
        try:
            await s.ctx.characters.write(lambda uow: uow.wild_kills.add(kill))
        except IntegrityError:
            s.log.info("monstro já abatido por outro", monstro=m.id)
        else:
            if monsters.count_kill(snap.character, templates, m):
                await s.ctx.characters.save(snap.character)
                await drop_box(s, m)
            if m.boss_type == monsters.CHIEF:
                _boss_killed(s, m)
    if same:  # senão o roll_monsters já tirou o velho: um 140 dele o traria de volta
        _monster_sync(s, m, monsters.MONSTER_GONE if gone else monsters.MONSTER_ALIVE)
    if won:
        await _boss_info(s, m.map_id)
    else:
        _stop_walk(s)
        s.outer_army = None
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))


# (só turco: teknoloji_upgrade #1) o chefe morto sai no 83 canal 2 para o servidor inteiro, com o link 111 que abre o
# painel dos chefes (ChatCellData.__outerCityBossClickHandler). TODO(inventado): o texto inglês, montado do turco
# "Tebrikler, oyuncu X çevredeki BOSS Y öldürdü, ödül kazandınız" com "Wilds" do language.txt (outercity.helpContent)
BOSS_KILLED = 'Congratulations! Player {} has killed the Wilds BOSS {} and won a reward<a t="111" name="{}"/>'
BOSS_LINK = "Find the Wilds BOSS"


def _boss_killed(s: GameSession, m: monsters.Monster) -> None:
    assert s.snapshot is not None
    row = s.ctx.templates.get("MapPhysicsTempInfos", m.template_id) or {}
    text = BOSS_KILLED.format(
        social.player_link(s.ctx, s.snapshot.character), row.get("MapPhysicsTempName", ""), BOSS_LINK
    )
    shout = pb.ChatChannelMsg(channel=WORLD, encodeMsg=text)
    for other in s.ctx.online.sessions():
        other.send(S_CHAT, shout)


async def _attack_cache(s: GameSession, c: tc.Cache) -> None:
    """Luta com o Treasure Cache (oficial_20261023-171155-1 #325-#329, #570-#574): 140 do exército lutando, 140 do
    baú em luta (state 4) e a 157 (battleType 3). Recusa com 140 parado se já há luta, se o baú já foi aberto nesta
    vida ou se outro está lutando com ele."""
    snap = s.snapshot
    assert snap is not None
    opened = await _opened(s, c.map_id)
    if s.battle is not None or (c.id, c.born) in opened or _cache_state(s, c) == tc.CACHE_FIGHTING:
        s.log.info("5160 baú recusado", bau=c.id, nivel=c.level, aberto=(c.id, c.born) in opened)
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))
        return
    _army_sync(s, ARMY_FIGHTING)
    spec = tc.battle(snap, s.ctx.templates, c)

    async def finished(battle: Battle, won: bool) -> None:
        await _cache_over(s, battle, c, won)

    s.battle = Battle(
        spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings
    )
    s.log.info("batalha com baú", bau=c.id, template=c.template_id, battle=s.battle.id)
    s.ctx.wilds.fighting[(c.map_id, c.id, c.born)] = s.battle
    _cache_sync(s, c, tc.CACHE_FIGHTING)
    s.battle.start()


async def _cache_over(s: GameSession, battle: Battle, c: tc.Cache, won: bool) -> None:
    """Fim da luta com o Treasure Cache, na ordem do oficial (#645-#670): 150, 109, 3, o prêmio (115, 4476, 111),
    4103 (battleScene 0), 83 do HP, 150, 100, 140 ×2 do exército, 140 do baú (state 0 aberto; 1 perdendo), 83
    "Received: ... x1", 169 e o 4382 logo em seguida (no mapa do mundo ele não espera o 8747: #670, #1812, #3082).
    O primeiro a vencer leva (``treasure_cache_opens``); a vida que acabou no meio da luta não dá nada. Mochila
    cheia: o baú se abre sem item (log). Desvio: os 4484 de título (×9 no oficial) não existem aqui."""
    snap = s.snapshot
    assert snap is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
    s.ctx.wilds.fighting.pop((c.map_id, c.id, c.born), None)
    alive = now < c.ends
    opened = False
    new: list[Item] = []
    text = ""
    if won and alive:
        mark = TreasureCacheOpen(c.map_id, c.id, c.born, snap.character.id or 0, now)
        try:
            await s.ctx.characters.write(lambda uow: uow.cache_opens.add(mark))
        except IntegrityError:
            s.log.info("baú já aberto por outro", bau=c.id)
        else:
            opened = True
            got = tc.loot(s.ctx.world, templates, snap, c, random.Random())
            if rewards.can_grant(snap, templates, got, now):
                new, text = rewards.grant(snap, templates, got)
                await s.ctx.characters.save(*rewards.owners(snap), *new)
            else:
                s.log.info("baú sem espaço na mochila", bau=c.id, premio=got)

    def prize() -> None:
        if new:
            s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
            events.items_gained(s)
        if text:
            alert(s, text)

    daru = await _casualties(s, battle, won, tc.SCENE, prize)
    s.battle_strategy = 0  # o 4382 sai aqui mesmo
    _army_sync(s, ARMY_IDLE)
    if opened:
        s.outer_caches.pop(c.id, None)
    if alive:
        _cache_sync(s, c, tc.CACHE_GONE if opened else tc.CACHE_ALIVE)
    if text:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    assert snap.castle is not None
    map_id, x, y = oc.position(snap.castle, s.outer_army)
    s.send(S_GRID_ARMY, _grid_msg(s, {oc.grid_of(x, y)}, map_id))
    s.send(S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=0, gold=0, strategy=daru))


@dataclass(frozen=True, slots=True)
class _Target:
    """Castelo NPC atacável: o robô da instância (``robots.py``) ou o castelo NPC do mundo (``npc_castles.py``)."""

    id: int
    grade: int
    name: str
    where: tuple[int, int, int]  # mapa, x, y
    msg: Callable[[int, int], pb.BaseCastleMsg]  # o 140 com o state e o defenceLefttime
    spec: Callable[[], dict[str, Any]]
    shield: tuple[int, int]  # chave da proteção depois de vencido (``Wilds.shields``)


def _robot_target(s: GameSession, robot: RobotCastle) -> _Target:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    name = robots.robot_name(s.ctx.world, snap.character.id or 0, robot)
    return _Target(
        robot.id, robot.grade, name, (snap.castle.map_id, robot.x, robot.y),
        lambda state, left: robots.robot_castle_msg(snap, s.ctx.world, robot, state, left),
        lambda: oc.robot_battle(snap, s.ctx.templates, robot.grade, name), (snap.character.id or 0, robot.id),
    )  # fmt: skip


def _npc_target(s: GameSession, c: npc_castles.NpcCastle) -> _Target:
    snap = s.snapshot
    assert snap is not None
    return _Target(
        c.id, c.grade, c.name, (c.map_id, c.x, c.y), lambda state, left: npc_castles.castle_msg(c, state, left),
        lambda: npc_castles.battle(snap, s.ctx.world, s.ctx.templates, c), (0, c.id),
    )  # fmt: skip


def _attack_castle(s: GameSession, target: _Target) -> list[object]:
    """Ataque a um castelo NPC (cliente: MapPhysicsCastle.attack e CityInfoFrame). Recusa com 140 parado,
    sem luta, se já há luta, se não há ataque no dia (``attackCount`` do cliente), se a diferença de nível
    para o castelo for 10 ou mais ou se o castelo ainda está protegido (MapPhysicsCastle.attack, command02/03).
    Senão gasta um ataque e manda, na ordem do oficial (tutorial_en #1648-#1657, oficial_20261023-171155-1
    #740-#749): o leed 10, 140 do exército lutando, 140 do
    próprio castelo, 4452 (``defenceLefttime`` 0: atacar acaba a proteção, que aqui não existe), 3 com o
    ``attackLeftCount`` novo, 140 do castelo em luta (state 4) e a luta.
    (dedução) o ataque sai do contador do dia (o mesmo do 9506, "x/5" do AttackAlertFrame). O contador e a
    devoção voltam para quem chama gravar logo depois da luta criada: cair no meio da luta não devolve o ataque."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None and snap.arena is not None
    c, arena, now = snap.character, snap.arena, s.ctx.clock.now()
    if A.roll_day(arena, now):
        s.send(S_RESET, A.data_reset(snap, now))
    shielded = s.ctx.wilds.shield_left(target.shield, now) > 0
    if s.battle is not None or arena.attack_left <= 0 or abs(c.grades - target.grade) >= 10 or shielded:
        s.log.info(
            "5160 castelo NPC recusado",
            castelo=target.id, ataques=arena.attack_left, nivel=c.grades, protegido=shielded,
        )  # fmt: skip
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))
        return []
    arena.attack_left -= 1  # sem await até criar a luta: dois 5160 seguidos não gastam o mesmo ataque
    rows = events.leed_gain(s, events.PLUNDER_LEED)
    _army_sync(s, ARMY_FIGHTING)
    own = b.complete(b.castle_msg(snap, snap.castle))
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_CASTLE, baseCastle=own))
    s.send(S_CASTLE_TIME, pb.BaseCastleMsg(defenceLefttime=0))
    _send_player(s)
    _target_sync(s, target, CASTLE_FIGHTING)
    spec = target.spec()

    async def finished(battle: Battle, won: bool) -> None:
        await _castle_over(s, battle, target, won)

    s.battle = Battle(
        spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings
    )
    s.log.info("batalha com castelo NPC", castelo=target.id, battle=s.battle.id)
    s.battle.start()
    return [arena, *rows]


def _target_sync(s: GameSession, target: _Target, state: int) -> None:
    left = s.ctx.wilds.shield_left(target.shield, s.ctx.clock.now())
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_CASTLE, baseCastle=b.complete(target.msg(state, left))))


async def _castle_over(s: GameSession, battle: Battle, target: _Target, won: bool) -> None:
    """Fim da luta com o castelo NPC (tutorial_en #1758-#1770, oficial_20261023-171155-1 #819-#833 e a vitória
    #6014-#6027): 150, 109, 3, 4103 (battleScene 6), 150, 100, na vitória 118 (2 h de proteção), 112, 148 (o relatório
    da batalha), 140 do exército, 140 do castelo de volta ao state 1 (com o ``defenceLefttime``) e 4382. Conta o tipo 8
    com Para1 1 na vitória e 0 na derrota (#1765: a missão 100 conta perdendo; 765 pede a vitória). O Daru são os
    soldados perdidos (``_casualties``; #1762: strategyBonus 172 = as 172 tropas de #1758). O ouro saqueado (4950 no
    grau 12, ``npc_castles.loot``) não vai no 4103 nem no 4382: entra no ouro e aparece no 109 seguinte (#6046);
    o VIP soma a Kyanite do privilégio 7."""
    snap = s.snapshot
    assert snap is not None and snap.arena is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
    fight = _capacity(s)
    daru = await _casualties(s, battle, won, oc.ROBOT_SCENE)
    s.battle_strategy = 0  # o 4382 do castelo sai aqui mesmo (#1770)
    gold = npc_castles.loot(s.ctx.world, target.grade) if won else 0
    crystals = vip_right(s, snap, VIP_PLUNDER_CRYSTALS) if won else 0
    snap.character.gold += gold
    snap.character.crystals += crystals
    if won:
        seconds = int(npc_castles.settings(s.ctx.world)["shield_seconds"])
        s.ctx.wilds.shield(target.shield, now, seconds)
        _, x, y = target.where
        s.send(S_CASTLE_DEFENSE, pb.CastleDefenseRspMsg(posX=x, posY=y, leftTime=seconds))
    quests = rules.quest_event(snap, templates, ATTACK_CASTLE, int(won), 1)
    letter = _castle_report(s, target, won, fight, gold, crystals, now)
    await s.ctx.characters.save(snap.character, snap.arena, *quests)
    await s.ctx.characters.write(lambda uow: stage(uow, letter))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    notify(s.ctx.online, letter)
    s.log.info("relatório do castelo NPC", castelo=target.id, carta=letter.id, venceu=won, ouro=gold, kyanite=crystals)
    _army_sync(s, ARMY_IDLE)
    _target_sync(s, target, CASTLE_IDLE)
    s.send(S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=0, gold=0, strategy=daru))


def _castle_report(
    s: GameSession, target: _Target, won: bool, fight: int, gold: int, crystals: int, now: datetime
) -> Mail:
    """A carta do 148 (tutorial_en #1766, oficial_20261023-171155-1 #827, #1985 e #6022): "Battle Report" de
    "System Mail" (``MailType`` 3, o XML de ``oc.report_contents``), como as cartas 11554/11564/11569 do ``maillist``
    da mesma sessão: perdas vazias, ``fight`` dos dois, o ouro ganho em ``me`` e o mesmo negativo em ``he``."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    spec = target.spec()
    enemy = spec["heroes"][0] if spec["heroes"] else {}
    map_id, x, y = target.where
    empty = {"site1Name": "", "site1Count": 0, "site2Name": "", "site2Count": 0}
    contents = oc.report_contents(
        {"type": 1, "camp": 1, "result": 1 if won else 2, "playerName": target.name, "siteName": target.name,
         "pos": f"{x},{y}", "mapId": map_id, "time": mines.game_date(now)},
        {"heroId": snap.leader.template_id, **empty, "fight": fight, "grade": snap.character.grades, "gold": gold,
         "crystal": crystals},
        {"heroId": enemy.get("tempId", 0), **empty, "fight": npc_castles.fight(s.ctx.world, target.grade),
         "grade": target.grade, "gold": -gold, "crystal": 0},
    )  # fmt: skip
    return Mail(
        snap.character.id or 0,
        now,
        "Battle Report",
        contents,
        mail_type=MailType.BATTLE_REPORT,
        send_type=SYSTEM_SENDER,
    )


@router.on(8488)
async def pvp_army(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """PvP contra o exército de outro jogador no mapa. Os exércitos alheios não aparecem na cidade externa
    (ver 8201), então não há alvo: nada muda e o cliente não espera resposta para isso (ele só espera a 157)."""
    s.log.info("8488 sem alvo no mapa", alvo=msg.tarUserId)


@router.on(8699)
async def collection_battle(s: GameSession, _: object) -> None:
    """O guia do tutorial manda (ação a46 do m8) dentro da pedreira 6001: a luta da coleta (inglesa #1928,
    ``handlers/campaign.py``). Fora dela não há o que iniciar."""
    if not await quarry_fight(s):
        s.log.info("8699 fora da pedreira")


@router.on(9506)
async def add_attack(s: GameSession, msg: pb.OutercityReqMsg) -> None:
    """Ataque extra da cidade externa (AttackAlertFrame): AddAttck_Point (395) Balens, ``type 2`` usa o vinculado
    primeiro; até 5 no dia (o cliente mostra "x/5"). Responde o PlayerMsg com o contador novo."""
    snap = s.snapshot
    assert snap is not None and snap.arena is not None
    c, arena, now = snap.character, snap.arena, s.ctx.clock.now()
    if A.roll_day(arena, now):
        s.send(S_RESET, A.data_reset(snap, now))
    if arena.attack_left >= A.ATTACK_FREE:
        s.log.info("9506 recusado", motivo="cheio")
        return
    price = A.config(s.ctx.templates, "AddAttck_Point", oc.ATTACK_PRICE)
    entry = pay(c, price, bind=msg.type == 2, reason="attack_count", ref="outer_city", now=now)
    if entry is None:
        s.log.info("9506 recusado", motivo="sem diamantes")
        alert(s, "You don't have enough Balens!")  # o cliente só confere 98: abaixo do preço, sem isso nada aparece
        return
    arena.attack_left += 1
    await s.ctx.characters.save(c, arena, entry)
    _send_player(s)


async def _tile_taken(s: GameSession, map_id: int, x: int, y: int) -> bool:
    """O tile tem mina, castelo NPC, robô ou o castelo de outro jogador (o 5160 ali acharia esse)."""
    snap = s.snapshot
    assert snap is not None
    world, templates = s.ctx.world, s.ctx.templates
    if npc_castles.tile_taken(world, templates, map_id, x, y) or mines.mine_at(world, map_id, x, y) is not None:
        return True
    if robots.robot_at(snap, world, map_id, x, y) is not None:
        return True
    own = snap.character.id or 0
    castles = await s.ctx.characters.read(lambda uow: uow.castles.on_map(map_id))
    return any((c.pos_x, c.pos_y) == (x, y) and c.character_id != own for c in castles)


@router.on(5176)
async def move_castle(s: GameSession, msg: pb.CastleReqMsg) -> None:
    """Muda o castelo de lugar.

    Outro mapa (``magId`` diferente): o servidor escolhe o ponto (centro do mapa) e gasta 200 de
    energia de teleporte; sem energia, completa até o teto com diamante (``payType 2`` = vinculado).
    Mesmo mapa com ``posX``/``posY``: 100 de energia, no ponto pedido se estiver no mapa.
    Resposta: 140 com o exército no lugar novo e 105 com o castelo (mapa, posição, energia). Mudando de mapa,
    as minas ocupadas se soltam e o 152 vai entre os dois (oficial_20261023-153200-1 #184-#187). Recusa:
    105 com o castelo como está.
    """
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, castle, now = snap.character, snap.castle, s.ctx.clock.now()
    templates = s.ctx.templates
    if msg.magId in (0, castle.map_id):
        if not (msg.posX and msg.posY) or not oc.inside(templates, castle.map_id, msg.posX, msg.posY):
            s.log.info("5176 recusado", motivo="ponto fora do mapa")
            _castle_state(s)
            return
        if await _tile_taken(s, castle.map_id, msg.posX, msg.posY):
            s.log.info("5176 recusado", motivo="tile ocupado", x=msg.posX, y=msg.posY)
            _castle_state(s)
            return
        target, spot, need = castle.map_id, (msg.posX, msg.posY), oc.ENERGY_SAME_MAP
    else:
        if not oc.map_allowed(msg.magId, c.grades) or oc.map_size(templates, msg.magId) is None:
            s.log.info("5176 recusado", motivo="mapa fechado", mapa=msg.magId)
            _castle_state(s)
            return
        target, spot, need = msg.magId, oc.centre(templates, msg.magId), oc.ENERGY_OTHER_MAP
        while await _tile_taken(s, target, *spot):  # (dedução) o vizinho livre à direita do centro
            spot = (spot[0] + 1, spot[1])
    top = cs.energy_max(templates)
    diamonds = oc.energy_diamonds(castle, top, need)
    entry = None
    if diamonds:
        entry = pay(c, diamonds, bind=msg.payType == 2, reason="transfer_energy", ref="castle", now=now)
        if entry is None:
            s.log.info("5176 recusado", motivo="sem diamantes para a energia")
            _castle_state(s)
            return
        castle.energy = top
    castle.energy -= need
    released = []
    if target != castle.map_id:
        cs.settle(snap, templates, now)  # o ouro até agora sai com as minas
        released = mines.release(snap)
    moved_map = target != castle.map_id
    castle.map_id, castle.pos_x, castle.pos_y = target, spot[0], spot[1]
    if moved_map and mines.is_world(s.ctx.world, target):
        castle.mines_at = mines.world_cycle_start(s.ctx.world, now)  # as minas do mundo vivem no ciclo do mundo
    quests = rules.update_state_quests(snap, templates, snap.quests)  # 37: missões do mapa (checkMapId)
    _stop_walk(s)
    s.outer_army = None
    await s.ctx.characters.save(c, castle, *([entry] if entry else []), *quests, delete=tuple(released))
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=3, army=_army_brief(s)))
    if moved_map:
        s.send(S_POLITICS, politics_msg(snap, templates))
    s.send(S_TRANSFER, pb.CastleReqMsg(magId=target, posX=spot[0], posY=spot[1], leftEnergy=castle.energy))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    if entry is not None:
        _send_player(s)


@router.on(8747)
async def enter_castle(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    if s.fam_left:  # (visto) oficial_20261023-171155-1 #5171-#5172: o 83 logo depois do 8747 da saída da terra secreta
        s.fam_left = False
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg="Left Guild Chamber"))
    # só com luta pendente (tutorial_en #576 sim, #826 e #1128 não): sem luta o OuterCityManager quebra
    if s.outer_fight_over or s.battle_gp:
        s.send(S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=s.battle_strategy))
    s.battle_gp, s.outer_fight_over, s.battle_strategy = 0, False, 0
