"""Masmorra: varredura (8528) e dublê de chefe (8526).

Estado parcial, documentado em docs/salas-campanha.md: a varredura precisa do progresso de campanha
(status do MopupManager) e o dublê precisa do chefe mundial (docs/boss-eventos.md). Sem eles, o pedido
não muda nada; o cliente recebe só o que já existe (nada novo aqui).
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession


@router.on(8528)
async def sweep(s: GameSession, msg: pb.CampaignSweepReq) -> None:
    # varredura (4425 CampaignSweepRsp). Sem progresso salvo não há como provar que a campanha foi vencida
    s.log.info("8528 sem efeito (progresso de campanha não modelado)", campanha=msg.campaignId, tipo=msg.sweepType)


@router.on(8526)
async def replacement(s: GameSession, msg: pb.OprateReplacemntMsg) -> None:
    # dublê do chefe (4424/4423). Depende do chefe mundial, que não está ligado a este servidor ainda
    s.log.info("8526 sem efeito (dublê depende do chefe mundial)", op=msg.op, campanha=msg.campaignId)
