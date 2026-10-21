"""Campo de batalha (Ancient Battleground, campanhas 4001-4011) e Amethyst Mine (campanha 30000): fechados.

Os dois são mapas de campanha com muitos jogadores ao mesmo tempo (times, pontos, carrinhos de
minério), em janelas diárias de 25 min. Sem esse mapa compartilhado, o servidor os mantém fechados
do jeito que o cliente entende (``docs/pvp.md``): o 4248 do login nunca tem ``state`` 0, e o botão fica escondido;
a mina já nasce escondida (4549/4422 nunca abrem). Pedidos que chegarem mesmo assim não têm efeito.
"""

from __future__ import annotations

from datetime import datetime

from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import worldboss
from ..router import router
from ..session import GameSession

S_WARFIELD_STATE, S_WAR_ORDER = 4248, 4255
WARFIELDS = range(4001, 4012)  # CampaignInfo Types=5 nos templates EN (inglesa #104: 4001-4011)
# CampaignTemplate.state: 0 aberto (o único que o cliente lê: WorldBossManager.__updateWarFightStateHandler mostra o
# botão), 1 ainda não abriu hoje, 2 encerrado hoje, 3 na janela (inglesa #104 às 18:24: 4001-4007 = 2, 4008 = 3,
# 4009-4011 = 1; #133 às 18:25 o 4008 vira 2; #3110 às 19:00 o 4009 vira 0)
BEFORE, CLOSED, RUNNING = 1, 2, 3


def states(templates: GameTemplates, now: datetime) -> pb.WorldBossStateMsg:
    """Estado de cada campo pelo ``OpenTime``/``StopTime`` de hoje; na janela vai 3, não 0."""
    # ponytail: sem o mapa do campo de batalha nada abre: sem o 0 nem o 4248 nas viradas (#133, #3110); mandar 0 e
    # empurrar no relógio (20008) quando o campo existir
    msg = pb.WorldBossStateMsg()
    for campaign in WARFIELDS:
        row = templates.get("Campaigns", campaign, key="CampaignId")
        value = worldboss.state(row, now) if row is not None else worldboss.CLOSED
        msg.worldBossInfo.add(campaignId=campaign, state=RUNNING if value == worldboss.OPEN else value)
    return msg


def login(s: GameSession) -> None:
    s.send(S_WARFIELD_STATE, states(s.ctx.templates, s.ctx.clock.now()))


@router.on(8337)
async def war_order(s: GameSession, _: object) -> None:
    """Classificação do campo: ninguém lutando, lista vazia."""
    s.send(S_WAR_ORDER, pb.WarReportListMsg())


@router.on(8332, 8334, 8338, 8599, 8633)
async def closed(s: GameSession, msg: object) -> None:
    """Entrar no campo (8332), atacar lá dentro (8334), restaurar vida (8338), pedir entradas quando acabaram (8599,
    ``WarFightItem`` com ``warFieldCount`` <= 0; o login manda 2 e o botão só aparece no estado 0, nunca mandado) e
    entrar na mina (8633): sem 125 o cliente não troca de cena e não fica esperando nada."""
    s.log.info("campo de batalha/mina fechados", pedido=str(msg))
