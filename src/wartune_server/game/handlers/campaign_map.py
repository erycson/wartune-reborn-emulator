"""Pedidos do mapa de campanha (PvE) que não são o movimento nem a batalha (esses estão em ``campaign.py``).

Estado parcial, documentado em docs/salas-campanha.md: 5033 e 5180 disparam nós e batalhas (140/131/128/157
no replay) e dependem do mapa de nós 1011/2011 e do progresso de campanha; 5121 e 5122 não têm captura do
pedido; 5126 só guarda a névoa que o cliente já mostra. Sem mudança de estado onde não há dado.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_SYSTEM_ARMY = 20


@router.on(5033)
async def campaign_confirm(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # confirmação de nó (replay: 140, 131, 128, 157). Sem o mapa de nós e o progresso, não há o que confirmar
    s.log.info("5033 sem efeito (dependência de nós)", p1=msg.paraInt1, p2=msg.paraInt2)


@router.on(5038)
async def system_army(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # exército do sistema do nó (replay: 20 SystemArmyMsg). Sem tabela de nó, a lista vai vazia
    s.log.info("5038 exército do sistema vazio (dependência)", p1=msg.paraInt1)
    s.send(S_SYSTEM_ARMY, pb.SystemArmyMsg())


@router.on(5121)
async def campaign_army(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # sem captura do pedido: paraInt1 conflita com o NpcInfoFrame (paraInt1=2). Não muda estado
    s.log.info("5121 sem efeito (sem captura do pedido)", p1=msg.paraInt1)


@router.on(5122)
async def take_card(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # pegar carta (replay: 19 e 4105 depois). A tabela de cartas não está modelada
    s.log.info("5122 sem efeito (cartas não modeladas)", p1=msg.paraInt1)


@router.on(5126)
async def fog_update(s: GameSession, msg: pb.CampaignFogDataListReqMsg) -> None:
    # névoa que o cliente já revelou; o servidor não guarda ainda (130 volta só no próximo ENTER)
    s.log.info("5126 névoa não gravada", tiles=len(msg.dataList))


@router.on(5180)
async def campaign_finish(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # fim de campanha (replay: 140, 131, 128, 157 com paraInt1=1). Depende do progresso de campanha
    s.log.info("5180 sem efeito (progresso de campanha não modelado)", p1=msg.paraInt1)
