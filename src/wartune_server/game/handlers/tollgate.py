"""Pedágio (tollgate): recompensa, pontuação, pedido e ataque (8752-8755).

Evento fechado: não há agenda do evento nem a tabela de pontos (TollgateReward.ScoreRewards é descartado
pelo parser). As respostas dizem "fechado" (4645 com isOpen=false), que é o estado verdadeiro hoje.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_TOLLGATE_IS_OPEN = 4645


def _closed(s: GameSession) -> None:
    s.send(S_TOLLGATE_IS_OPEN, pb.TollgateMsg(isOpen=False))


@router.on(8752)
async def get_reward(s: GameSession, _: object) -> None:
    s.log.info("8752 sem recompensa (evento fechado)")
    _closed(s)


@router.on(8753)
async def request(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    s.log.info("8753 recusado (evento fechado)", alvo=msg.tarUserId)
    _closed(s)


@router.on(8754)
async def score(s: GameSession, _: object) -> None:
    s.log.info("8754 sem pontuação (evento fechado)")
    _closed(s)


@router.on(8755)
async def request_attack(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    s.log.info("8755 recusado (evento fechado)", alvo=msg.tarUserId)
    _closed(s)
