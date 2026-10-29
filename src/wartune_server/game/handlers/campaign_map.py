"""Pedidos do mapa de campanha (PvE) que não são o movimento nem a batalha (esses estão em ``campaign.py``).

5033 (caixa Pandora), 5122 (vira a carta) e 5180 (fecha o quadro das cartas) estão em ``handlers/campaign.py``,
junto da masmorra. Estado parcial, documentado em docs/salas-campanha.md: 5121 não tem captura do pedido; o
5126 devolve a névoa (19) só na masmorra. Sem mudança de estado onde não há dado.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_SYSTEM_ARMY = 20
# exército do sistema (SystemArmyMsg): as masmorras e a pedreira levam o seu no conteúdo (``maps[mapa]["army"]``,
# migração 0034, inglesa #924, #1524, #2513; o 2011 na 0084, só turco: peri_uyanis #89-90). Os demais ficam vazios


@router.on(5038)
async def system_army(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Pré-carga de batalha do mapa (``PreLoadNextCampaign``, ``paraInt1`` = mapa): responde 20 com a lista do mapa.

    (cliente) o 20 só alimenta ``BattleResPreloadManager``. (visto) um 20 para cada 5038 na masmorra (tutorial_en
    #922 -> #924 ... #1518 -> #1524). Responder logo a cada 5038; o cliente remove o
    listener do 20 depois do primeiro (``PreLoadNextCampaign``, linhas 46 e 80).
    """
    c = s.campaign
    if c is not None and c.world_boss and (boss := s.ctx.world.world_bosses.get(c.map_id)) is not None:
        # (visto) #1408-#1409 e depois de cada morte (#1734): o herói do chefe
        s.send(S_SYSTEM_ARMY, pb.SystemArmyMsg(heroTemplated=[boss.hero_id]))
        return
    if c is not None and c.altar:  # o herói da onda do altar (como o do chefe)
        from .altar import cfg  # altar importa campaign, que importa este módulo

        s.send(S_SYSTEM_ARMY, pb.SystemArmyMsg(heroTemplated=[int(cfg(s.ctx)["hero"])]))
        return
    key = str(msg.paraInt1)
    data = next((c["maps"][key] for c in s.ctx.world.campaigns.values() if key in c["maps"]), None)
    heroes: list[int] = []
    soldiers: list[int] = []
    if data is not None:  # pedreira: sem ``army`` (inglesa #1821, 20 vazio)
        heroes, soldiers = data.get("army", {}).get("hero", []), data.get("army", {}).get("soldier", [])
    else:
        # ponytail: mapa sem captura manda lista vazia; falta a lista de cada mapa (nós do .maps). Não muda estado
        s.log.info("5038 mapa sem captura (lista vazia)", mapa=msg.paraInt1)
    s.send(S_SYSTEM_ARMY, pb.SystemArmyMsg(heroTemplated=heroes, soldierTemplated=soldiers))


@router.on(5121)
async def campaign_army(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # sem captura do pedido: paraInt1 conflita com o NpcInfoFrame (paraInt1=2). Não muda estado
    s.log.info("5121 sem efeito (sem captura do pedido)", p1=msg.paraInt1)


@router.on(5126)
async def fog_update(s: GameSession, msg: pb.CampaignFogDataListReqMsg) -> None:
    # na masmorra o servidor devolve a névoa revelada (19 com os mesmos índices, tutorial_en #881 -> #883); no
    # tutorial a névoa não é guardada (130 volta só no próximo ENTER)
    if s.campaign is not None and s.campaign.dungeon:
        update = [pb.FogUpdateMsg(index=d.index, fogByte=d.fogByte) for d in msg.dataList]
        s.send(19, pb.CampaignFogUpdateMsg(fogUpdate=update))
    else:
        s.log.info("5126 névoa não gravada", tiles=len(msg.dataList))
