"""Chefe do mundo: agenda (8271 -> 4182), entrada (8258), reviver pago (8264), buff (8470) e info (8259).

Regras e fontes em ``docs/boss-eventos.md``. A batalha compartilhada do chefe (mapa 5001/5003 com nós,
HP global, morte e relatório) não existe aqui: os templates não têm ``CampaignData`` para essas
campanhas e não há captura da luta. Por isso o que muda estado (entrar, reviver, comprar buff) é
recusado com um aviso (111) e não cobra nada.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from .. import worldboss
from ..router import router
from ..session import GameSession
from .player import alert

S_BOSS_STATE = 4182
NO_MAP = "Dünya Boss savaş haritası henüz hazır değil."
UNAVAILABLE = "Bu işlem şu an kullanılamıyor."  # reviver e buff: o cliente só pede dentro do mapa do chefe


@router.on(8535)
async def cancel_transport(s: GameSession, _: object) -> None:
    """Cancela o transporte do jogador morto no mapa de PvP do chefe (ExtraBufferItem, tipo 5). Esse estado de
    morte vem do mapa da batalha compartilhada, que não existe aqui: nada para cancelar, e o cliente não espera
    resposta. Só registramos."""
    s.log.info("8535 sem transporte de morte: não há mapa de PvP do chefe")


@router.on(8271)
async def boss_state(s: GameSession, _: object) -> None:
    """Agenda de hoje dos dois chefes. O cliente pede isso uma vez, no login (``WorldBossManager.setup``)."""
    s.send(S_BOSS_STATE, worldboss.states_msg(s.ctx.templates, s.ctx.clock.now()))


@router.on(8259)
async def boss_info(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Info por mapa: ``reqWorldBossCmd`` não tem chamador no cliente, então não há o que responder."""
    s.log.info("pedido de info do chefe ignorado", pedido=str(msg))


@router.on(8258)
async def enter_boss(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Entrar no chefe (``param1`` = campanha). Recusa com o motivo; quem passa ainda cai no aviso de mapa."""
    alert(s, _refusal(s, msg.param1) or NO_MAP)


def _refusal(s: GameSession, campaign_id: int) -> str | None:
    row = worldboss.boss(s.ctx.templates, campaign_id)
    if row is None:
        return "Geçersiz Dünya Boss."
    snap = s.snapshot
    assert snap is not None
    if worldboss.state(row, s.ctx.clock.now()) != worldboss.OPEN:
        return "Dünya Boss şu an açık değil."
    if snap.character.grades < int(row["MinLevel"]):
        return f"Dünya Boss için seviye {row['MinLevel']} gerekli."
    if s.battle is not None or s.campaign is not None:
        return "Önce mevcut savaşını ya da haritanı bitir."
    return None


@router.on(8264)
async def revive_or_fight(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Entrar na luta agora, pagando (``Live_Fight_Pay`` 3; payType 0 = vinculado primeiro, 1 = só
    diamante). O botão existe na ``RiverView`` tipo 1, depois de morrer no chefe, e o servidor ainda
    não sabe disso: nada é cobrado. ``Live_Pay`` (2) não tem botão no chefe.

    ponytail: o mesmo 8264 é o reviver do altar de guilda (``RiverView`` tipo 2, paga em contribuição);
    quem fizer o mapa do altar tem de separar pelo mapa do jogador.
    """
    s.log.info("reviver pago recusado (sem morte no chefe)", pedido=str(msg))
    alert(s, UNAVAILABLE)


@router.on(8470)
async def buy_buff(s: GameSession, msg: pb.WorldBossBufferMsg) -> None:
    """Buff de Moral do chefe: só se compra dentro do mapa do chefe. Nada é cobrado."""
    s.log.info("buff do chefe recusado (sem mapa do chefe)", pedido=str(msg))
    alert(s, UNAVAILABLE)
