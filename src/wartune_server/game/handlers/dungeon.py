"""Masmorra: varredura (8528) e dublê de chefe (8526).

Varredura de campanha (``sweepType`` 1) em ``game/sweep.py``; regras e status em docs/salas-campanha.md. O dublê
precisa do chefe mundial (docs/boss-eventos.md).
"""

from __future__ import annotations

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import events as gev
from .. import maze as mz
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


async def _settle_maze(s: GameSession, sweep: sw.Sweep, *, all_now: bool = False) -> list[str]:
    """Andares vencidos da varredura do labirinto. (só turco: yeralti #7-#22) 3, 4540/4387 do mascote, 4476/4426;
    o 4425 fica com quem chama, e o 83 dos textos devolvidos sai depois dele (a EXP sai antes só quando há baú)."""
    from . import pets as P  # pets importa shop, que importa este módulo

    snap = s.snapshot
    assert snap is not None
    now, before = s.ctx.clock.now(), snap.character.grades
    kind = mz.kind_of(sweep.campaign_id) or mz.CATACOMBS
    tower = mz.load(snap, now, kind)
    done = sweep.done
    got, changed = sw.settle_maze(
        snap, s.ctx.templates, sweep, tower, mz.settings(s.ctx.world.settings, kind), s.ctx.world.settings, now,
        all_now=all_now,
    )  # fmt: skip
    pet = P.share_gp(s, sum(gp for gp, _, _ in got))
    rows = [*rewards.owners(snap), *changed, mz.store(snap, tower, now, kind), sw.store(snap, sweep, now)]
    await s.ctx.characters.save(*rows, *([pet] if pet is not None else []))
    if not got:
        return []
    from . import events

    _player(s)
    if pet is not None:
        P.send_gained(s, pet)
    texts = [rules.exp_text(*g) for g in got]
    if changed:  # (visto) 10/25 #9394-#9410: 115, 83 da EXP, 111 dos baús; depois o 4425 e o 83 dos itens
        s.send(S_ITEMS, rewards.items_msg(changed, s.player_id))
        for text in texts:
            s.send(S_CHAT, b.complete(pb.ChatChannelMsg(channel=3, encodeMsg=text)))
        text = rewards.received(s.ctx.templates, [g for r in sweep.rounds[done:] for g in r.items])
        alert(s, text)
        texts = [text]
    events.progress(s)
    if snap.character.grades > before:
        await push_level(s, before)
    return texts


async def _settle(s: GameSession, sweep: sw.Sweep, *, all_now: bool = False) -> list[str]:
    """Acerta as rodadas vencidas e grava. (só turco: savasa_baskin_ve_elmas_ile_hizlandirma #5-#33) 109, 3, 115 da
    chave gasta, 4152 do leed 4 por rodada, 112 das missões de campanha (313 "Gain passage through any dungeon"), 140
    do exército parado quando acabou, 109, 115 dos itens, 4476/4426, 83 da devoção, os 4484, 111 e 83 dos itens,
    4476/4426 de novo; depois a subida de nível. O 4902/150/4434 do #7-#9 é o periódico de 5 min."""
    if sweep.kind == sw.MAZE:
        return await _settle_maze(s, sweep, all_now=all_now)
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
        return []
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
    return []


async def _maze_start(s: GameSession, msg: pb.CampaignSweepReq) -> None:
    """Varredura do labirinto (``MazeMopupPrepareFrame``: ``eIndex`` = o último andar). (só turco: yeralti #2-#4)
    109, 140 do exército ocupado e o 4425 status 1 (sem ``campaignId``)."""
    from .campaign import ARMY_FIGHTING, S_MAP_SYNC, map_sync  # campaign importa login, que importa este módulo

    snap = s.snapshot
    assert snap is not None
    now, templates = s.ctx.clock.now(), s.ctx.templates
    kind = mz.kind_of(msg.campaignId) or mz.CATACOMBS  # (cliente) MazeMopupPrepareFrame manda o campaignId da torre
    cfg = mz.settings(s.ctx.world.settings, kind)
    tower = mz.load(snap, now, kind)
    if why := sw.maze_refusal(snap, templates, tower, cfg, msg.eIndex):
        s.log.info("8528 do labirinto recusado", status=why, até=msg.eIndex, andar=tower.index)
        _send(s, pb.CampaignSweepRsp(status=why, sweepType=sw.MAZE))
        return
    first = max(tower.index, 1)
    new = sw.Sweep(kind.campaign, msg.eIndex - first + 1, b.fmt_time(now), kind=sw.MAZE, first=first)
    out = sw.response(new, templates, now, sw.OK)
    out.ClearField("result")  # (só turco: #4) o 4425 do começo vai só com o status
    await s.ctx.characters.save(sw.store(snap, new, now))
    s.log.info("varredura do labirinto começou", de=first, até=msg.eIndex)
    castle_yield(s)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    _send(s, out)


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
    if msg.sweepType == sw.MAZE and msg.opType == sw.START:
        await _maze_start(s, msg)
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
    texts: list[str] = []
    if msg.opType == sw.SPEED_UP and current.end == 0:
        free = gev.has_contract(snap, sw.MAZE_KING, now) if current.kind == sw.MAZE else sw.free(snap, now)
        cost = 0 if free else sw.speed_up_cost(current, templates, now)
        paid = cash.pay(snap.character, cost, msg.payType, "sweep", str(current.campaign_id), now) if cost else None
        if cost and paid is None:
            s.log.info("8528 aceleração sem Balens", custo=cost)
            _send(s, pb.CampaignSweepRsp(status=sw.NO_POINT, sweepType=current.kind, campaignId=current.campaign_id))
            return
        if paid is not None:
            await s.ctx.characters.save(snap.character, paid)
        texts = await _settle(s, current, all_now=True)
    else:
        texts = await _settle(s, current)
    out = sw.response(current, templates, now, current.end or sw.POLLED)
    await s.ctx.characters.save(sw.store(snap, current, now))
    _send(s, out)
    for text in texts:  # (só turco: yeralti #22) "8,800 EXP kazanıldı(Dahil4,000 Dünya EXP,4,400 çevrimdışı EXP)"
        s.send(S_CHAT, b.complete(pb.ChatChannelMsg(channel=3, encodeMsg=text)))


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
