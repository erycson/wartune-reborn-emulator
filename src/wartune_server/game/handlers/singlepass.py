"""Passe de progresso (SinglePass): área atual e recompensa da área (8636, 8637).

O progresso das fases (8753 e 8755) não existe no servidor, então a área é sempre a 1 e nada está
concluído. A recompensa da área só vale com as 10 fases dela feitas (``maxIndex`` == área * 10, em
``SinglePassManager``), o que não acontece aqui: o pedido é recusado com a 4552 atual, que é o que o cliente
usa para se atualizar.
"""

from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession

S_SINGLE_PASS = 4552
AREA = 1  # área inicial do passe


def _state(s: GameSession) -> pb.SinglePassMsg:
    return b.complete(pb.SinglePassMsg(userId=s.player_id, area=AREA, maxIndex=0))


@router.on(8636)
async def update_area(s: GameSession, _: object) -> None:
    s.send(S_SINGLE_PASS, _state(s))


@router.on(8637)
async def get_area_reward(s: GameSession, _: object) -> None:
    s.log.info("8637 recompensa de área recusada", motivo="fases não concluídas")
    s.send(S_SINGLE_PASS, _state(s))
