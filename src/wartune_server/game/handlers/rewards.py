"""Caixa por tempo (5019), recompensa offline (8287) e reforço em batalha (8255). Ver docs/castelo.md."""

from __future__ import annotations

from ...domain.models import BagType, Item
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import record_cash
from .. import castle as cs
from .. import rules, timebox
from ..builders import login as b
from ..builders.player import item_moved
from ..router import router
from ..session import GameSession
from .login import player_info
from .player import BAG_SIZE, CURRENCIES

S_PLAYER, S_BOX, S_ITEMS, S_ALERT = 3, 4, 115, 111
RATES = {0: 1}  # rateCount do HookRewardFrame: 0 = x1, 15 = x1,5, 20 = x2


def box_msg(s: GameSession) -> pb.BoxBoxMsg:
    assert s.snapshot is not None
    period, run = timebox.box_state(s.snapshot.character, s.ctx.clock.now())
    return pb.BoxBoxMsg(time=period, operate=period > 0, timerun=run)


@router.on(5019)
async def player_time(s: GameSession, msg: pb.BoxBoxMsg) -> None:
    """``operate=false`` sincroniza; ``operate=true, time=P`` recebe a caixa do período P (TimeDrop)."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    timebox.settle_box(c, now)
    if not msg.operate:
        await s.ctx.characters.save(c)
        s.send(S_BOX, box_msg(s))
        return
    period = timebox.next_period(c, templates)
    jt = rules.job_type(c.job)
    drops = [d for d in templates.find("TimeDrop", Grade=msg.time) if int(d.get("Job") or 0) in (0, jt)]
    goods = [d for d in drops if int(d["TemplateId"]) > 0]
    ids = [int(d["TemplateId"]) for d in drops]
    known = all(t in CURRENCIES or templates.get("ItemTempInfos", t) for t in ids)
    fits = sum(i.bag_type == BagType.BAG for i in snap.items) + len(goods) <= BAG_SIZE
    if period is None or msg.time != period or c.box_seconds < period * 60 or not (drops and known and fits):
        s.log.info("5019 recusado", time=msg.time, proximo=period, segundos=c.box_seconds, cabe=fits)
        await s.ctx.characters.save(c)
        s.send(S_BOX, box_msg(s))  # o cliente reinicia o contador com o estado real
        return

    c.box_period = period
    new: list[Item] = []
    for d in goods:
        new.append(Item(c.id or 0, int(d["TemplateId"]), count=int(d["Data"]), pos=rules.free_bag_pos(snap)))
        snap.items.append(new[-1])
    changed: list[object] = [c, *new]
    currencies = [(CURRENCIES[int(d["TemplateId"])], int(d["Data"])) for d in drops if int(d["TemplateId"]) < 0]
    if any(f == "gold" for f, _ in currencies):
        cs.settle(snap, templates, now)
        changed.append(snap.castle)
    for field, amount in currencies:
        setattr(c, field, getattr(c, field) + amount)
        if field in ("point", "gift_token"):
            delta = (amount, 0) if field == "point" else (0, amount)
            changed.append(record_cash(c, *delta, reason="time_box", ref=f"period:{period}", now=now))
    await s.ctx.characters.save(*changed)

    s.send(S_BOX, box_msg(s))
    for item in new:
        s.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
    if any(f in ("gold", "crystals") for f, _ in currencies):
        cs.castle_yield(s)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(8287)
async def take_offline_reward(s: GameSession, msg: pb.OfflineRewardMsg) -> None:
    """EXP do tempo offline (4195 no login). O cliente só manda ``rateCount``."""
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    gp = timebox.offline_gp(c)
    # ponytail: x1,5 e x2 custam diamante no oficial, mas o preço não está no cliente; recusados
    if gp <= 0 or msg.rateCount not in RATES:
        s.log.info("8287 recusado", gp=gp, rate=msg.rateCount)
        return
    rules.add_gp(snap, s.ctx.templates, gp * RATES[msg.rateCount])
    c.offline_seconds = 0
    await s.ctx.characters.save(c, snap.leader)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(8255)
async def player_reinforce(s: GameSession, msg: pb.CampaignNodeMsg) -> None:
    # entrar como reforço numa batalha em curso num nó do mapa (estado 4): é do sistema de
    # batalha/campanha multijogador, que ainda não existe aqui
    s.log.info("8255 recusado", motivo="sem batalha em grupo", node=msg.campDataId)
