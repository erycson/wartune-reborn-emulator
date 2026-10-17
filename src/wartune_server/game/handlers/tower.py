"""Torre (8297/8300) e guarda de batalha (8742).

Estado parcial, documentado em docs/salas-campanha.md: não há progresso de torre nem tabela de limites
(entradas, gemas equipadas), então as respostas mostram "sem progresso" em vez de inventar números.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_TOWER_INFO, S_BATTLEGUARD = 4205, 4631
MAZE_MAX_INDEX = 60  # maxIndex visto no labirinto 8001 (captura); a torre de referência ainda não tem o seu


@router.on(8297)
async def tower_info(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Info de uma torre (4205). Sem progresso salvo: nenhuma entrada feita, nenhum limite conhecido."""
    s.send(
        S_TOWER_INFO,
        pb.TowerInfoMsg(towerIndex=msg.index, maxIndex=MAZE_MAX_INDEX, enterCount=0, freeEnterCount=0, maxEnterCount=0),
    )


@router.on(8300)
async def tower_live(s: GameSession, msg: pb.PayTypeMsg) -> None:
    # pagamento de entrada da torre (PayTypeMsg): sem tabela de custo, nada é cobrado nem liberado
    s.log.info("8300 sem efeito (custo da torre não modelado)", pay=msg.payType)


@router.on(8742)
async def battleguard_op(s: GameSession, msg: pb.HeroWatchOpMsg) -> None:
    """Gemas da guarda de batalha (4631). Sem inventário de gemas, a operação é recusada e volta o estado vazio."""
    s.log.info("8742 recusado (gemas não modeladas)", op=msg.opType)
    s.send(S_BATTLEGUARD, pb.HeroWatchMsg(userId=s.player_id))
