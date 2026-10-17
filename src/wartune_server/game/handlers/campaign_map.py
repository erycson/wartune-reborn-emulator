"""Pedidos do mapa de campanha (PvE) que não são o movimento nem a batalha (esses estão em ``campaign.py``).

5033 (caixa Pandora) e 5180 (solta a última luta) estão em ``handlers/campaign.py``, junto da masmorra.
Estado parcial, documentado em docs/salas-campanha.md: 5121 não tem captura do pedido; o 5122 guarda a carta
escolhida (masmorra) e o 5126 devolve a névoa (19) só na masmorra. Sem mudança de estado onde não há dado.
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
    # carta escolhida: paraInt2 é o index. Chega antes do fim do mapa (replay #1166 -> #1241): guarda e
    # o fim (``_dungeon_end``) entrega a carta. Fora da masmorra, sem efeito (cartas do tutorial não existem)
    if s.campaign is not None and s.campaign.dungeon:
        s.campaign.card = msg.paraInt2
    else:
        s.log.info("5122 sem efeito fora da masmorra", p1=msg.paraInt1)


@router.on(5126)
async def fog_update(s: GameSession, msg: pb.CampaignFogDataListReqMsg) -> None:
    # na masmorra o servidor devolve a névoa revelada (19 com os mesmos índices, replay #950 -> #953); no
    # tutorial a névoa não é guardada (130 volta só no próximo ENTER)
    if s.campaign is not None and s.campaign.dungeon:
        update = [pb.FogUpdateMsg(index=d.index, fogByte=d.fogByte) for d in msg.dataList]
        s.send(19, pb.CampaignFogUpdateMsg(fogUpdate=update))
    else:
        s.log.info("5126 névoa não gravada", tiles=len(msg.dataList))
