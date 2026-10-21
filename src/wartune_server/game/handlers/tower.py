"""Torre (8296/8297/8299/8300) e guarda de batalha (8742).

Estado parcial, documentado em docs/salas-campanha.md: o limite de entradas vem das capturas turcas (só turco:
yeralti_labirenti, labirent_sandik_toplama_odulu; o tutorial_en manda o 4373 vazio, #52), mas o
progresso da torre (totalGp, itemTempIds, order) não é salvo, e as gemas da guarda não são modeladas.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_TOWER_INFO, S_BATTLEGUARD = 4205, 4631
# maxIndex é o recorde (maior andar): "My Record" do MazeFrame, a missão tipo 38 (TaskTemplate.checkMazeRecord:
# maxIndex >= Para2) e os itens da loja do labirinto (GoodsItem: MazeLayers > maxIndex some). Sem progresso salvo, 0;
# o 60 do turco (login.json #55) era o recorde daquele personagem e fechava a missão 6 sem jogar
MAZE_MAX_INDEX = 0
# campaignId do Forgotten Catacombs (só turco: 4205 em labirent_sandik_toplama_odulu #17 e yeralti_labirenti #1)
MAZE_CAMPAIGN = 8001
# aba 1 do MazeFrame (__mazePanelChangeHandler pede o 8297 com o índice da aba): Tormented Necropolis
MAZE_CAMPAIGNS = (MAZE_CAMPAIGN, 8101)


def _tower_msg(index: int) -> pb.TowerInfoMsg:
    """Só turco (yeralti_labirenti #1, labirent_sandik_toplama_odulu #17): sem entrada feita, 1 entrada livre de 1.
    ``index`` ecoa o pedido (MazeControler pede 0; a captura volta ``index: 0``); ``towerIndex`` é o andar atual
    (capturas turcas: 1, 2, 3, 5 conforme ``totalGp`` sobe; MazeView mostra esse valor). Sem progresso salvo, o andar e
    o recorde ficam 0 (MazeMopupPrepareFrame trata 0 como "não começou")."""
    return pb.TowerInfoMsg(
        index=index,
        towerIndex=0,  # ponytail: sem progresso salvo da torre; andar e recorde reais precisam do progresso
        maxIndex=MAZE_MAX_INDEX,
        campaignId=MAZE_CAMPAIGNS[index] if 0 <= index < len(MAZE_CAMPAIGNS) else MAZE_CAMPAIGN,
        enterCount=0,
        freeEnterCount=1,
        maxEnterCount=1,
    )


@router.on(8297)
async def tower_info(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Info de uma torre (4205)."""
    s.send(S_TOWER_INFO, _tower_msg(msg.index))


@router.on(8299)
async def tower_reset(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Reset do andar (``MazeFrame``: botão Reset, visível com ``towerIndex`` > 0, depois da confirmação). A tela só se
    refaz com o 4205 (``PlayerManager.__towerInfoHandler`` -> ``UPDATE_TOWER_INFO`` -> ``refreshView``): volta ao andar
    0 com o mesmo ``index``."""
    s.send(S_TOWER_INFO, _tower_msg(msg.index))


@router.on(8296)
async def tower_enter(s: GameSession, msg: pb.EnterTowerInfoMsg) -> None:
    """Entrar no labirinto (``MazeFrame``: ``chooseIndex`` 1 começar, 0 continuar; ``isDouble`` 2 lucro dobrado, gasta
    a chave sonType 297; o cliente segura um novo envio por 5 s). Sem os andares, não entra: nada muda nem é cobrado."""
    # ponytail: os nós e monstros dos MapInfo 8001+ não estão nos templates (o .maps só tem o desenho) e não há
    # captura do 8296 nem da resposta; entrar, contar a entrada e gastar a chave esperam uma captura do labirinto
    s.log.info("8296 sem efeito (andares do labirinto sem dados)", campanha=msg.campaignId, escolha=msg.chooseIndex)


@router.on(8300)
async def tower_live(s: GameSession, msg: pb.PayTypeMsg) -> None:
    # pagamento de entrada da torre (PayTypeMsg): sem tabela de custo, nada é cobrado nem liberado
    s.log.info("8300 sem efeito (custo da torre não modelado)", pay=msg.payType)


@router.on(8742)
async def battleguard_op(s: GameSession, msg: pb.HeroWatchOpMsg) -> None:
    """Gemas da guarda de batalha (4631). Sem inventário de gemas, a operação é recusada e volta o estado vazio."""
    s.log.info("8742 recusado (gemas não modeladas)", op=msg.opType)
    s.send(S_BATTLEGUARD, pb.HeroWatchMsg(userId=s.player_id))
