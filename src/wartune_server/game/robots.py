"""Castelos-robô do mapa do castelo (missões 100, 411 e 765), do catálogo do mundo.

Nos mesmos tiles em todas as contas (captura inglesa #532; a turca, replay #706, também). O guia da missão 100
procura o de (44,22) (m8,
alvo 80_3); sem ele a tela escurece, como na missão 60. O userId e o nome mudam de uma conta para outra
(visto: inglês 1300001446 "Aillendre", turco 1300001984 "♣Chloe♣" no mesmo 765958), então o nome sai da conta.
Não têm estado: o robô está sempre lá.
"""

from __future__ import annotations

import random

from ..domain.models import PlayerSnapshot
from ..domain.world import RobotCastle, World
from ..protocol.messages import wartune_pb2 as pb
from .outer_city import BASE_MAP, grid_of, template_of

# (visto) inglês #532: 1300001446 e 1300001447, um por robô na ordem do catálogo; o turco teve 1300001984/1985.
# Fica fora da faixa 1300001401-1300002398 dos robôs do torneio de pets (arena.PET_ROBOT_BASE) para não colidir
ROBOT_USER_BASE = 1_300_009_000


def _in_own_instance(snap: PlayerSnapshot, map_id: int) -> bool:
    """Só na instância do próprio castelo, a mesma regra das minas (``template_of`` == modelo 100): num mapa
    compartilhado (1 a 5) os robôs não aparecem nem lutam."""
    return snap.castle is not None and map_id == snap.castle.map_id and template_of(map_id) == BASE_MAP


def robot_at(snap: PlayerSnapshot, world: World, map_id: int, x: int, y: int) -> RobotCastle | None:
    """Castelo-robô no tile pedido, na instância do próprio castelo."""
    if not _in_own_instance(snap, map_id):
        return None
    return next((r for r in world.robots_on(BASE_MAP) if (r.x, r.y) == (x, y)), None)


def robots_in(snap: PlayerSnapshot, world: World, map_id: int, grids: set[str]) -> list[RobotCastle]:
    """Robôs das grades pedidas, na instância do próprio castelo (4129 do 8201)."""
    if not _in_own_instance(snap, map_id):
        return []
    return [r for r in world.robots_on(BASE_MAP) if grid_of(r.x, r.y) in grids]


def robot_name(world: World, char_id: int, robot: RobotCastle) -> str:
    """Nome do robô nesta conta: os robôs da conta tiram nomes distintos da lista (dedução); com mais robôs
    que nomes, os nomes se repetem."""
    names = world.robot_names
    if not names:
        return ""
    picks = random.Random(f"robo:{char_id}").sample(names, min(len(names), len(world.robots)))
    return str(picks[world.robots.index(robot) % len(picks)])


def robot_castle_msg(snap: PlayerSnapshot, world: World, robot: RobotCastle) -> pb.BaseCastleMsg:
    """Castelo-robô como no 4129 do oficial (inglês #532): tipo 1, estado 1, sem liga e sem tempo de defesa."""
    assert snap.castle is not None
    name = robot_name(world, snap.character.id or 0, robot)
    return pb.BaseCastleMsg(
        id=robot.id, mapId=snap.castle.map_id, posX=robot.x, posY=robot.y, type=1,
        occupyPlayerId=ROBOT_USER_BASE + world.robots.index(robot), occupyPlayerName=name, occupyLeagueName="",
        state=1, defenceLefttime=0, castleName=name, grade=robot.grade, vipCastleView=0, vipType=0,
    )  # fmt: skip
