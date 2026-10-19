"""Campo de batalha (Ancient Battleground, campanhas 4001-4013) e Amethyst Mine (campanha 30000): fechados.

Os dois são mapas de campanha com muitos jogadores ao mesmo tempo (times, pontos, carrinhos de
minério), em janelas diárias de 25 min. Sem esse mapa compartilhado, o servidor os mantém fechados
do jeito que o cliente entende (``docs/pvp.md``): 4248 com ``state 1`` no login esconde o botão;
a mina já nasce escondida (4549/4422 nunca abrem). Pedidos que chegarem mesmo assim não têm efeito.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_WARFIELD_STATE, S_WAR_ORDER = 4248, 4255
WARFIELDS = range(4001, 4014)  # CampaignInfo Types=5
CLOSED = 1  # CampaignTemplate.state: 0 aberto (o padrão do cliente!), 1/2 fechado


def login(s: GameSession) -> None:
    msg = pb.WorldBossStateMsg()
    for campaign in WARFIELDS:
        msg.worldBossInfo.add(campaignId=campaign, state=CLOSED)
    s.send(S_WARFIELD_STATE, msg)


@router.on(8337)
async def war_order(s: GameSession, _: object) -> None:
    """Classificação do campo: ninguém lutando, lista vazia."""
    s.send(S_WAR_ORDER, pb.WarReportListMsg())


@router.on(8332, 8334, 8338, 8633)
async def closed(s: GameSession, msg: object) -> None:
    """Entrar no campo (8332), atacar lá dentro (8334), restaurar vida (8338) e entrar na mina
    (8633): sem 125 o cliente não troca de cena e não fica esperando nada."""
    s.log.info("campo de batalha/mina fechados", pedido=str(msg))
