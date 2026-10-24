"""Caixa por tempo (5019), recompensa offline (8287) e reforço em batalha (8255). Ver docs/castelo.md."""

from __future__ import annotations

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import record_cash
from .. import bag, rewards, rules, timebox
from .. import castle as cs
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .login import player_info
from .player import CURRENCIES, push_level

S_PLAYER, S_BOX, S_ITEMS, S_ALERT = 3, 4, 115, 111
RATES = {0: 1}  # rateCount do HookRewardFrame: 0 = x1, 15 = x1,5, 20 = x2


S_BOX_STAR, S_CHAT = 4250, 83
BOX_OK = "Reward retrieval successful!"  # tutorial_en #2114, #3360


def box_msg(s: GameSession) -> pb.BoxBoxMsg:
    assert s.snapshot is not None
    r = timebox.rule(s.ctx.world.settings)
    period, run = timebox.box_state(s.snapshot.character, s.ctx.clock.now(), online=s.box_counting, r=r)
    return pb.BoxBoxMsg(time=period, operate=period > 0, timerun=run)


def _box_star(s: GameSession) -> None:
    """4250 (o cliente não escuta): o mesmo BoxBoxMsg com ``timerun`` 0, antes do 4 (#1597, #2111, #3357)."""
    period = box_msg(s).time
    s.send(S_BOX_STAR, pb.BoxBoxMsg(time=period, operate=period > 0, timerun=0))


@router.on(5019)
async def player_time(s: GameSession, msg: pb.BoxBoxMsg) -> None:
    """``operate=false`` sincroniza; ``operate=true, time=P`` recebe a caixa do período P (TimeDrop).

    O primeiro 5019 da sessão liga a contagem (antes dele o tempo online não conta). Pedido repetido ou antes da
    hora recebe só o 4 com o estado (tutorial_en #2109, #3353: o oficial paga uma vez)."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    timebox.settle_box(c, now, online=s.box_counting, r=timebox.rule(s.ctx.world.settings))
    if not s.box_counting:
        s.box_counting = True
    if not msg.operate:
        await s.ctx.characters.save(c)
        _box_star(s)
        s.send(S_BOX, box_msg(s))
        return
    period = timebox.next_period(c, templates)
    jt = rules.job_type(c.job)
    drops = [d for d in templates.find("TimeDrop", Grade=msg.time) if int(d.get("Job") or 0) in (0, jt)]
    goods = [d for d in drops if int(d["TemplateId"]) > 0]
    ids = [int(d["TemplateId"]) for d in drops]
    known = all(t in CURRENCIES or templates.get("ItemTempInfos", t) for t in ids)
    fits = len(goods) <= len(bag.free_positions(snap, s.ctx.clock.now()))
    if period is None or msg.time != period or c.box_seconds < period * 60 or not (drops and known and fits):
        s.log.info("5019 recusado", time=msg.time, proximo=period, segundos=c.box_seconds, cabe=fits)
        await s.ctx.characters.save(c)
        s.send(S_BOX, box_msg(s))  # o cliente reinicia o contador com o estado real
        return

    c.box_period, c.box_seconds = period, 0  # o próximo período conta do resgate (o 4 volta com timerun 0)
    # (visto) oficial_20261023-171155-1 #4869: completa a pilha que já existe (82795, pos 17) e manda um 115 só, na
    # ordem inversa da TimeDrop
    new: list[Item] = []
    for d in reversed(goods):
        new += [i for i in bag.add(snap, templates, int(d["TemplateId"]), int(d["Data"]), now) if i not in new]
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

    # ordem do oficial (tutorial_en #2097-#2115, #3343-#3361; oficial_encantar #2683-#2699): 109 (ouro) ou 3 (outras
    # moedas), 115, 4476 (atividades, depois de item), 111, 4250, 4, 83 com o texto e 83 de sucesso; o texto lista do
    # fim para o começo, como o pacote da mochila. Os nove 4484 do oficial (títulos) não vão: não há títulos
    if any(f in ("gold", "crystals") for f, _ in currencies):
        cs.castle_yield(s)
    if any(f not in ("gold", "crystals") for f, _ in currencies):
        s.send(S_PLAYER, b.complete(player_info(s, snap)))
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
        from . import events  # events importa login

        events.items_gained(s)
    text = rewards.text(templates, [(int(d["TemplateId"]), int(d["Data"])) for d in reversed(drops)])
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    _box_star(s)
    s.send(S_BOX, box_msg(s))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=BOX_OK))


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
    gained = rules.add_gp(snap, s.ctx.templates, gp * RATES[msg.rateCount])
    c.offline_seconds = 0
    await s.ctx.characters.save(c, snap.leader, *snap.pawns)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    if gained:
        push_level(s, c.grades - gained)  # (dedução) como na entrega de missão


@router.on(8255)
async def player_reinforce(s: GameSession, msg: pb.CampaignNodeMsg) -> None:
    # entrar como reforço numa batalha em curso num nó do mapa (estado 4): é do sistema de
    # batalha/campanha multijogador, que ainda não existe aqui
    s.log.info("8255 recusado", motivo="sem batalha em grupo", node=msg.campDataId)
