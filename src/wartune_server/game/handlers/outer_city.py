"""Cidade externa (mapa do castelo) e a volta para o castelo no fim do tutorial."""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..builders.army import castle_pawns
from ..router import router
from ..session import GameSession
from .campaign import ARMY_IDLE, map_sync
from .player import castle_yield

S_MAP_BOSS, S_PHYSICS, S_GRID_ARMY, S_FIGHT_MOVIE = 4938, 4129, 169, 4382
S_BUILDINGS, S_BUILD_ORDER, S_ARMY_PAWN = 4130, 104, 100


@router.on(9525)
async def map_boss(s: GameSession, _: pb.MapBossQuestMsg) -> None:
    s.send(S_MAP_BOSS, pb.MapBossMsg(count1=0, count2=0, count3=0, leftBossTime=0, leftFogTime=0))


@router.on(8201)
async def physics_by_grid(s: GameSession, msg: pb.PhysicUpdateReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    # ponytail: só o próprio castelo; terras selvagens e castelos vizinhos quando houver mapa compartilhado
    reply = pb.PhysicListUpdateMsg(reqGrid=msg.reqGrid)
    reply.baseCastle.add().CopyFrom(b.complete(b.castle_msg(snap, snap.castle)))
    s.send(S_PHYSICS, reply)
    grid = pb.OutercityArmyUpdatedGridMsg()
    grid.updatedArmy.add().CopyFrom(map_sync(s, ARMY_IDLE).army)
    s.send(S_GRID_ARMY, grid)


@router.on(8747)
async def enter_castle(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    s.send(S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=0))
    s.battle_gp = 0


@router.on(8281)
async def building_init(s: GameSession, _: object) -> None:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    castle_yield(s)
    castle_yield(s)
    s.send(S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    s.send(S_BUILDINGS, b.buildings_msg(snap, snap.castle, s.ctx.templates))
    s.send(S_BUILD_ORDER, pb.OrderInfoMsg(orderId=1, orderType=1, remainTime=0))
