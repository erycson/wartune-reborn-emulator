"""Varredura ("Blitz") de campanha: 8528 ``sweepType`` 1 (ver docs/salas-campanha.md).

(cliente) ``CampaignMopupPrepareFrame``/``CampaignMopupIngFrame``/``MopupManager``: cada rodada leva
``Campaign_Sweep_Time`` (300 s), gasta 20 de estamina e ``Campaign_Sweep_Gold`` (5000) de ouro, cobrados aos
poucos ("gold is deducted gradually"); o contrato do rei 5 (Free Blitz) tira o ouro. A rodada dá a EXP do fim da
masmorra e uma carta (``drops.card``). A varredura segue com o jogador offline: as rodadas vencidas se acertam no
próximo pedido ou no login.

Estado em ``EventState`` ``sweep`` (``text`` = JSON), apagado no 8528 op 4 (fechar ou cancelar).
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..domain.models import Item, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import campaign, drops, rewards, rules
from . import events as ev

KEY = "sweep"
CAMPAIGN = 1  # sweepType: 1 campanha, 2 labirinto
START, SPEED_UP, POLL, CLOSE = 1, 2, 3, 4  # opType (CampaignMopupIngFrame)
OK, BUSY, NO_GOLD, NO_POINT, NO_WEARY, POLLED, RESUME, DONE, BROKEN = 1, 2, 3, 4, 6, 5, 10, 11, 15  # status do 4425
ROUND, RUNNING = 1, 2  # SweepResult.type: rodada feita / ainda varrendo
WEARY = 20  # CampaignMopupPrepareFrame.WEARY
MAX_COUNT = 99  # o campo do quadro aceita 1..99
MIN_GRADE = 20  # CampaignInfoView: "Unlocks at Lvl. 20"
FREE_BLITZ = 5  # KingContracts 5 "Free Blitz": "Gold won't be consumed when blitzing."
SKELETON_KEY = 208005  # "Used to open Mystery Boxes"
# TODO(inventado): ouro do baú de prata e o que ele e a caixa misteriosa dão na varredura (o cliente só tem as
# frases "Spend Gold to open Silver Treasure Chests." e "Use Skeleton Keys to open Mystery Boxes.")
SILVER_GOLD = 2000
EARLY = 2  # s: o cliente pergunta no fim do tempo; um pedido um pouco antes ainda acerta a rodada
SETTING = "campaign_sweep"  # game_settings: ``round_gold`` = {campanha: ouro por rodada} (migração 0085)


@dataclass
class Round:
    gp: int
    items: list[tuple[int, int]]


@dataclass
class Sweep:
    campaign_id: int
    count: int
    started: str  # fmt de rules/builders (``ev.parse_time``)
    silver: bool = False
    secret: bool = False
    rounds: list[Round] = field(default_factory=list)
    sent: int = 0  # rodadas já mandadas ao cliente
    end: int = 0  # 0 varrendo, DONE ou BROKEN

    @property
    def done(self) -> int:
        return len(self.rounds)


def period(templates: GameTemplates) -> int:
    return int(rules.config(templates, "Campaign_Sweep_Time", "300"))


def gold_cost(templates: GameTemplates) -> int:
    return int(rules.config(templates, "Campaign_Sweep_Gold", "5000"))


def load(snap: PlayerSnapshot) -> Sweep | None:
    st = ev.peek(snap, KEY)
    if st is None or not st.text:
        return None
    data: dict[str, Any] = json.loads(st.text)
    data["rounds"] = [Round(r["gp"], [tuple(i) for i in r["items"]]) for r in data.get("rounds", [])]
    return Sweep(**data)


def store(snap: PlayerSnapshot, sweep: Sweep | None, now: datetime) -> Any:
    st = ev.state(snap, KEY, now)
    st.text, st.updated_at = (json.dumps(asdict(sweep)) if sweep is not None else ""), now
    return st


def free(snap: PlayerSnapshot, now: datetime) -> bool:
    return ev.has_contract(snap, FREE_BLITZ, now)


def refusal(snap: PlayerSnapshot, templates: GameTemplates, msg: pb.CampaignSweepReq, now: datetime) -> int:
    """Status do 4425 que recusa o início (0 = pode)."""
    c = snap.character
    cleared = (st := ev.peek(snap, f"campaign_rank:{msg.campaignId}")) is not None and st.value > 0
    row = templates.get("Campaigns", msg.campaignId, key="CampaignId") or {}
    if load(snap) is not None:
        return BUSY
    if not cleared or int(row.get("Types") or -1) != 0 or c.grades < MIN_GRADE or not 1 <= msg.count <= MAX_COUNT:
        return BROKEN  # (dedução) o cliente não deixa chegar aqui: botão escondido sem nota, campo 1..99
    if c.weary < msg.count * WEARY:
        return NO_WEARY
    if not free(snap, now) and c.gold < msg.count * gold_cost(templates):
        return NO_GOLD
    return 0


def remaining(sweep: Sweep, templates: GameTemplates, now: datetime) -> int:
    end = ev.parse_time(sweep.started) + timedelta(seconds=sweep.count * period(templates))
    return max(0, math.ceil((end - now).total_seconds()))


def _round_drops(
    snap: PlayerSnapshot, templates: GameTemplates, sweep: Sweep, table: Any, now: datetime, rng: random.Random
) -> tuple[list[tuple[int, int]], list[Item], list[Item]]:
    """Carta da rodada e, se marcados, o baú de prata (ouro) e a caixa misteriosa (Skeleton Key). Devolve os
    itens ganhos (template, quantidade), os itens novos ou mudados e os apagados."""
    pulls = 1
    if sweep.silver and snap.character.gold >= SILVER_GOLD:
        snap.character.gold -= SILVER_GOLD
        pulls += 1
    changed: list[Item] = []
    gone: list[Item] = []
    if sweep.secret and (taken := rewards.take_one(snap, SKELETON_KEY)) is not None:
        (gone if taken[1] else changed).append(taken[0])
        pulls += 1
    got: list[tuple[int, int]] = []
    for _ in range(pulls):
        card = drops.card(snap, templates, sweep.campaign_id, 0, rng, table, now=now)
        if card is None:
            break  # mochila cheia: a rodada segue sem item (TODO(inventado): o mailIn do oficial manda pelo correio)
        changed.append(card[0])
        got.append((card[0].template_id, card[0].count))
    return got, changed, gone


def settle(
    snap: PlayerSnapshot,
    templates: GameTemplates,
    sweep: Sweep,
    now: datetime,
    *,
    vip_exp: int = 0,
    table: Any = (),
    rng: random.Random | None = None,
    all_now: bool = False,
    round_gold: int = 0,
) -> tuple[list[Item], list[Item]]:
    """Faz as rodadas vencidas (todas com ``all_now``, a aceleração). Cobra estamina e ouro por rodada; sem eles a
    varredura para (``BROKEN``). ``vip_exp``: % do VIP na EXP da masmorra; ``round_gold``: ouro que a rodada dá
    (item -100 na lista). Acima do ``MaxLevel`` da campanha a rodada não dá EXP (só turco: savasa_baskin, a 1007,
    MaxLevel 21, no nível 56 deu gp 0). Devolve itens mudados e apagados."""
    rng = rng or random.Random()
    due = (
        sweep.count
        if all_now
        else int((now - ev.parse_time(sweep.started)).total_seconds() + EARLY) // period(templates)
    )
    due = min(due, sweep.count)
    row = templates.get("Campaigns", sweep.campaign_id, key="CampaignId") or {}
    changed: list[Item] = []
    gone: list[Item] = []
    c = snap.character
    while sweep.end == 0 and sweep.done < due:
        cost = 0 if free(snap, now) else gold_cost(templates)
        if c.weary < WEARY or c.gold < cost:
            sweep.end = BROKEN
            break
        c.weary -= WEARY
        c.gold -= cost
        top = int(row.get("MaxLevel") or 0)
        gp = 0 if top and c.grades > top else campaign.total_gp(int(row.get("BaseGp") or 0))
        gp += gp * vip_exp // 100
        rules.add_gp(snap, templates, gp)
        c.gold += round_gold
        got, more, out = _round_drops(snap, templates, sweep, table, now, rng)
        if round_gold:
            got.insert(0, (campaign.GOLD, round_gold))
        changed += more
        gone += out
        sweep.rounds.append(Round(gp, got))
    if sweep.end == 0 and sweep.done >= sweep.count:
        sweep.end = DONE
    return changed, gone


def _result(sweep: Sweep, index: int, time: int) -> pb.SweepResult:
    r = sweep.rounds[index]
    out = pb.SweepResult(
        type=ROUND, gp=r.gp, campaignId=sweep.campaign_id, time=time, finishCount=index + 1, count=sweep.count
    )
    for tid, n in r.items:
        out.items.add(templateId=tid, count=n)
    return out


def response(
    sweep: Sweep, templates: GameTemplates, now: datetime, status: int, *, all_rounds: bool = False
) -> pb.CampaignSweepRsp:
    """4425 com as rodadas novas (todas no ``RESUME``: o quadro do login começa vazio; o cliente soma linhas a cada
    resposta). Varrendo, a última entrada é ``RUNNING`` com o tempo que falta."""
    left = remaining(sweep, templates, now) if sweep.end == 0 else 0
    out = pb.CampaignSweepRsp(status=status, sweepType=CAMPAIGN, campaignId=sweep.campaign_id)
    first = 0 if all_rounds else sweep.sent
    for i in range(first, sweep.done):
        out.result.append(_result(sweep, i, left))
    if sweep.end == 0:
        out.result.add(type=RUNNING, campaignId=sweep.campaign_id, time=max(1, left), finishCount=sweep.done,
                       count=sweep.count)  # fmt: skip
    if status == RESUME:
        out.totalGp = sum(r.gp for r in sweep.rounds)
        totals: dict[int, int] = {}
        for r in sweep.rounds:
            for tid, n in r.items:
                totals[tid] = totals.get(tid, 0) + n
        for tid, n in totals.items():
            out.dropItems.add(templateId=tid, count=n)
    sweep.sent = sweep.done
    return out


def speed_up_cost(sweep: Sweep, templates: GameTemplates, now: datetime) -> int:
    """CampaignMopupIngFrame: ``ceil(segundos que faltam / 60)`` Balens."""
    return math.ceil(remaining(sweep, templates, now) / 60)
