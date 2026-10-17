"""Pedidos da cidade do céu: entrar (8688) e andar (8690). A lógica está em ``game/space.py``."""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from .. import space
from ..router import router
from ..session import GameSession

MAX_PATH = 16  # o cliente manda no máximo ~7 passos; o resto é repassado a todos, então corta


@router.on(8688)
async def enter_space(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    space.back(s)


@router.on(8690)
async def space_move(s: GameSession, msg: pb.SpacePlayerMoveMsg) -> None:
    # o cliente manda só o próprio jogador; o playerId dele é ignorado (vale o da sessão)
    path = [(p.x, p.y) for player in msg.players[:1] for p in player.path[:MAX_PATH] if p.x >= 0 and p.y >= 0]
    space.move(s, path)
