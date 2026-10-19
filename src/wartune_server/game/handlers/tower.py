"""Torre (8297/8300) e guarda de batalha (8742).

Estado parcial, documentado em docs/salas-campanha.md: o limite de entradas vem das capturas turcas (só turco:
yeralti_labirenti, labirent_sandik_toplama_odulu; o tutorial_en manda o 4373 vazio, #52), mas o
progresso da torre (totalGp, itemTempIds, order) não é salvo, e as gemas da guarda não são modeladas.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_TOWER_INFO, S_BATTLEGUARD = 4205, 4631
# maxIndex do Forgotten Catacombs 8001 (só turco: login.json #55); a torre de referência ainda não tem o seu
MAZE_MAX_INDEX = 60
# campaignId do Forgotten Catacombs (só turco: 4205 em labirent_sandik_toplama_odulu #17 e yeralti_labirenti #1)
MAZE_CAMPAIGN = 8001


@router.on(8297)
async def tower_info(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Info de uma torre (4205). Só turco (yeralti_labirenti #1, labirent_sandik_toplama_odulu #17): sem entrada
    feita, 1 entrada livre de 1. ``index`` ecoa o pedido (MazeControler pede 0; a captura volta ``index: 0``);
    ``towerIndex`` é o andar atual (capturas turcas: 1, 2, 3, 5 conforme ``totalGp`` sobe; MazeView mostra esse valor).
    Sem progresso salvo, o andar fica 0 (MazeMopupPrepareFrame trata 0 como "não começou") e ``totalGp`` 0."""
    s.send(
        S_TOWER_INFO,
        pb.TowerInfoMsg(
            index=msg.index,
            towerIndex=0,  # ponytail: sem progresso salvo da torre; andar real precisa do progresso
            maxIndex=MAZE_MAX_INDEX,
            campaignId=MAZE_CAMPAIGN,
            enterCount=0,
            freeEnterCount=1,
            maxEnterCount=1,
        ),
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
