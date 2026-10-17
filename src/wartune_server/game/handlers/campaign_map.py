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
# exército do sistema por mapa (SystemArmyMsg): só os mapas com resposta na captura; os demais ficam vazios
SYSTEM_ARMY: dict[int, tuple[list[int], list[int]]] = {  # mapa -> (heroTemplated, soldierTemplated)
    # (visto) replay #923: 5038 com paraInt1=1011; o 20 com soldierTemplated 2011 é o pacote #924
    1011: ([], [2011]),
    # (visto) replay #1321: 20 com heroTemplated 1011, depois do pedido #1219 e das entradas #1312/#1314;
    # ligar esse 20 ao #1219 é dedução
    1021: ([1011], [2011]),
    # (visto) peri_uyanis #89-90: 5038 paraInt1=2011 -> 20
    2011: ([3011], [4012, 4011]),
}


@router.on(5033)
async def campaign_confirm(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # confirmação de nó (replay: 140, 131, 128, 157). Sem o mapa de nós e o progresso, não há o que confirmar
    s.log.info("5033 sem efeito (dependência de nós)", p1=msg.paraInt1, p2=msg.paraInt2)


@router.on(5038)
async def system_army(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Pré-carga de batalha do mapa (``PreLoadNextCampaign``, ``paraInt1`` = mapa): responde 20 com a lista do mapa.

    (cliente) o 20 só alimenta ``BattleResPreloadManager``. (visto) nem todo 5038 tem um 20 no pacote seguinte
    do replay (o #1219 não tem). (dedução) responder logo a cada 5038; o cliente remove o listener do 20 depois
    do primeiro (``PreLoadNextCampaign``, linhas 46 e 80).
    """
    heroes, soldiers = SYSTEM_ARMY.get(msg.paraInt1, ([], []))
    if msg.paraInt1 not in SYSTEM_ARMY:
        # ponytail: mapa sem captura manda lista vazia; falta a lista de cada mapa (nós do .maps). Não muda estado
        s.log.info("5038 mapa sem captura (lista vazia)", mapa=msg.paraInt1)
    s.send(S_SYSTEM_ARMY, pb.SystemArmyMsg(heroTemplated=heroes, soldierTemplated=soldiers))


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
