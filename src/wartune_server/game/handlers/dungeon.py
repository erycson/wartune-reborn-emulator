"""Masmorra: varredura (8528) e dublê de chefe (8526).

Varredura de campanha (``sweepType`` 1) em ``game/sweep.py``; regras e status em docs/salas-campanha.md. O dublê
precisa do chefe mundial (docs/boss-eventos.md).
"""

from __future__ import annotations

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import rewards, rules, titles
from .. import sweep as sw
from ..builders import login as b
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import _player, alert, push_level

S_SWEEP, S_ITEMS, S_CHAT = 4425, 115, 83


def _send(s: GameSession, msg: pb.CampaignSweepRsp) -> None:
    s.send(S_SWEEP, msg)


async def _settle(s: GameSession, sweep: sw.Sweep, *, all_now: bool = False) -> None:
    """Acerta as rodadas vencidas e grava. (só turco: savasa_baskin_ve_elmas_ile_hizlandirma #5-#33) 109, 3, 115 da
    chave gasta, 4152 do leed 4 por rodada, 112 das missões de campanha (313 "Gain passage through any dungeon"), 140
    do exército parado quando acabou, 109, 115 dos itens, 4476/4426, 83 da devoção, os 4484, 111 e 83 dos itens,
    4476/4426 de novo; depois a subida de nível. O 4902/150/4434 do #7-#9 é o periódico de 5 min."""
    from .vip import VIP_EXP, vip_right  # vip importa player, que importa login, que importa campaign

    snap = s.snapshot
    assert snap is not None
    now, before, done = s.ctx.clock.now(), snap.character.grades, sweep.done
    first = len(sweep.rounds)
    table = s.ctx.world.campaign_cards.get(sweep.campaign_id, ())
    exp = vip_right(s, snap, VIP_EXP)
    gold = int(((s.ctx.world.settings.get(sw.SETTING) or {}).get("round_gold") or {}).get(str(sweep.campaign_id), 0))
    changed, gone = sw.settle(
        snap, s.ctx.templates, sweep, now, vip_exp=exp, table=table, all_now=all_now, round_gold=gold
    )
    st = sw.store(snap, sweep, now)
    await s.ctx.characters.save(*rewards.owners(snap), st, *changed, delete=tuple(gone))
    if sweep.done == done and not changed:
        return
    castle_yield(s)
    _player(s)
    moved: list[Item] = [i for i in changed if i not in gone]
    for item in gone:
        s.send(S_ITEMS, rewards.taken_msg(item, True, s.player_id))
    from . import events  # events importa este módulo (login_push)
    from .army import send_quests
    from .campaign import ARMY_IDLE, S_MAP_SYNC, map_sync  # campaign importa login, que importa este módulo

    new = sweep.rounds[first:]
    devotion = events.devotion(s)
    quests = []
    for _ in new:
        await events.leed_done(s, events.CAMPAIGN_LEED, say=False)
        # (dedução) a rodada fecha a masmorra como a luta do fim (``campaign._loot``)
        solo = int((s.ctx.templates.get("Campaigns", sweep.campaign_id, key="CampaignId") or {}).get("Capacity") or 0)
        for kind, para1 in ((rules.CAMPAIGN_CONDITION, sweep.campaign_id), (rules.SOLO_CONDITION, solo)):
            quests += [q for q in rules.quest_event(snap, s.ctx.templates, kind, para1, 1) if q not in quests]
    if quests:
        await s.ctx.characters.save(*quests)
        send_quests(s, quests)
    if sweep.end:
        s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        castle_yield(s)
    if moved:
        s.send(S_ITEMS, rewards.items_msg(moved, s.player_id))
        events.progress(s)
    if events.devotion(s) != devotion:
        events.say_devotion(s)
    if moved:
        for _ in range(titles.item_checks(s.ctx.templates)):
            events.send_titles(s)
    if got := [t for r in new for t in r.items]:
        # (dedução) "Kazanılan Eşyalar:" no turco; no inglês, como os outros "Kazanılan:" ("Received: Worg Tooth x2")
        text = rewards.received(s.ctx.templates, got)
        alert(s, text)
        s.send(S_CHAT, b.complete(pb.ChatChannelMsg(channel=3, encodeMsg=text)))
        events.progress(s)
    if snap.character.grades > before:
        await push_level(s, before)


@router.on(8528)
async def sweep(s: GameSession, msg: pb.CampaignSweepReq) -> None:
    """op 1 começa, 2 acelera (``ceil(segundos/60)`` Balens; grátis com o contrato 5), 3 pergunta (o cliente a cada
    rodada), 4 fecha ou cancela (sem resposta: ``uninit`` zera o quadro e uma resposta tardia vazaria para a
    próxima varredura). Status vistos (só turco, savasa_baskin_ve_elmas_ile_hizlandirma, em salas-campanha.md):
    1 no início (com 109, 3 e o 140 do exército ocupado antes, #1-#4), 5 nas perguntas e 11 no fim; a pergunta depois
    do fim leva 5 sem rodadas e ``sweepType`` 0 (#35)."""
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
        from .campaign import ARMY_FIGHTING, S_MAP_SYNC, map_sync  # campaign importa login, que importa este módulo

        castle_yield(s)
        _player(s)
        s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
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
    if msg.opType == sw.POLL and current.end:
        _send(s, pb.CampaignSweepRsp(status=sw.POLLED, sweepType=0))
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
