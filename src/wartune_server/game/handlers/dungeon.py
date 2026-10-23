"""Masmorra: varredura (8528) e dublê de chefe (8526).

Varredura de campanha (``sweepType`` 1) em ``game/sweep.py``; regras e status em docs/salas-campanha.md. O dublê
precisa do chefe mundial (docs/boss-eventos.md).
"""

from __future__ import annotations

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import rewards
from .. import sweep as sw
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .player import _player, push_level

S_SWEEP, S_ITEMS = 4425, 115


def _send(s: GameSession, msg: pb.CampaignSweepRsp) -> None:
    s.send(S_SWEEP, msg)


async def _settle(s: GameSession, sweep: sw.Sweep, *, all_now: bool = False) -> None:
    """Acerta as rodadas vencidas, grava e manda 3 (estamina, ouro), 115 (cartas, chave gasta) e a subida de nível."""
    from .vip import VIP_EXP, vip_right  # vip importa player, que importa login, que importa campaign

    snap = s.snapshot
    assert snap is not None
    now, before, done = s.ctx.clock.now(), snap.character.grades, sweep.done
    table = s.ctx.world.campaign_cards.get(sweep.campaign_id, ())
    exp = vip_right(s, snap, VIP_EXP)
    changed, gone = sw.settle(snap, s.ctx.templates, sweep, now, vip_exp=exp, table=table, all_now=all_now)
    st = sw.store(snap, sweep, now)
    await s.ctx.characters.save(*rewards.owners(snap), st, *changed, delete=tuple(gone))
    if sweep.done == done and not changed:
        return
    _player(s)
    moved: list[Item] = [i for i in changed if i not in gone]
    if moved:
        s.send(S_ITEMS, rewards.items_msg(moved, s.player_id))
    for item in gone:
        s.send(S_ITEMS, rewards.taken_msg(item, True, s.player_id))
    if snap.character.grades > before:
        push_level(s, before)


@router.on(8528)
async def sweep(s: GameSession, msg: pb.CampaignSweepReq) -> None:
    """op 1 começa, 2 acelera (``ceil(segundos/60)`` Balens; grátis com o contrato 5), 3 pergunta (o cliente a cada
    rodada), 4 fecha ou cancela (sem resposta: ``uninit`` zera o quadro e uma resposta tardia vazaria para a
    próxima varredura). Status vistos (só turco, savasa_baskin_ve_elmas_ile_hizlandirma, em salas-campanha.md):
    1 no início, 5 nas perguntas e 11 no fim."""
    snap = s.snapshot
    assert snap is not None
    now, templates = s.ctx.clock.now(), s.ctx.templates
    if msg.sweepType != sw.CAMPAIGN:
        # labirinto (sweepType 2): depende do progresso da torre (docs/plano-pendencias.md, seção 4)
        s.log.info("8528 do labirinto sem progresso da torre", op=msg.opType, andar=msg.eIndex)
        return
    if msg.opType == sw.START:
        if why := sw.refusal(snap, templates, msg, now):
            s.log.info("8528 recusado", status=why, campanha=msg.campaignId, rodadas=msg.count)
            _send(s, pb.CampaignSweepRsp(status=why, sweepType=sw.CAMPAIGN, campaignId=msg.campaignId))
            return
        new = sw.Sweep(msg.campaignId, msg.count, b.fmt_time(now), msg.openSilverBox, msg.openSecretBox)
        out = sw.response(new, templates, now, sw.OK)
        await s.ctx.characters.save(sw.store(snap, new, now))
        s.log.info("varredura começou", campanha=msg.campaignId, rodadas=msg.count)
        _send(s, out)
        return
    current = sw.load(snap)
    if current is None:
        s.log.info("8528 sem varredura", op=msg.opType)
        return
    if msg.opType == sw.CLOSE:
        await _settle(s, current)
        await s.ctx.characters.save(sw.store(snap, None, now))
        s.log.info("varredura fechada", feitas=current.done, de=current.count)
        return
    if msg.opType == sw.SPEED_UP and current.end == 0:
        cost = 0 if sw.free(snap, now) else sw.speed_up_cost(current, templates, now)
        paid = cash.pay(snap.character, cost, msg.payType, "sweep", str(current.campaign_id), now) if cost else None
        if cost and paid is None:
            s.log.info("8528 aceleração sem Balens", custo=cost)
            _send(s, pb.CampaignSweepRsp(status=sw.NO_POINT, sweepType=sw.CAMPAIGN, campaignId=current.campaign_id))
            return
        if paid is not None:
            await s.ctx.characters.save(snap.character, paid)
        await _settle(s, current, all_now=True)
    else:
        await _settle(s, current)
    out = sw.response(current, templates, now, current.end or sw.POLLED)
    await s.ctx.characters.save(sw.store(snap, current, now))
    _send(s, out)


async def login_push(s: GameSession) -> None:
    """Varredura aberta no login: acerta o que venceu offline e manda o 4425 ``RESUME`` (status 10) com todas as
    rodadas; o cliente abre o quadro na cidade (``MopupManager.enterSpaceShow``)."""
    snap = s.snapshot
    assert snap is not None
    current = sw.load(snap)
    if current is None:
        return
    await _settle(s, current)
    now = s.ctx.clock.now()
    out = sw.response(current, s.ctx.templates, now, sw.RESUME, all_rounds=True)
    await s.ctx.characters.save(sw.store(snap, current, now))
    _send(s, out)


@router.on(8526)
async def replacement(s: GameSession, msg: pb.OprateReplacemntMsg) -> None:
    # dublê do chefe (4424/4423). Depende do chefe mundial, que não está ligado a este servidor ainda
    s.log.info("8526 sem efeito (dublê depende do chefe mundial)", op=msg.op, campanha=msg.campaignId)
