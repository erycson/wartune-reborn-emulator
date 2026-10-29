"""Minério de Stokes (9645 ``extend1`` 35, ``OreActiveClientOpMsg {opType, isUseProp}``). Edição em
``game_settings.stokes_ore``; sem ela, fechado (190 ``param7`` falso, como em todas as capturas).

Cliente (``StokesOreManager``, ``StokesOreModel``, ``StokesOreFrame``):

- 190 ``SimplePropertyMsg``: ``param7`` aberto, ``param4``/``param5`` começo e fim;
- 188 ``OreActiveBaseInfoMsg``: ``mineOncePrice``/``mineTimesPrice`` (1 e 10 golpes) e ``rewards`` por
  ``rewardType``: o 0 é a lista de achados comuns (a grade da tela), 1-4 os andares especiais (``specialFloorNum``;
  o 4º é o fundo, ``layerArray[4]``, o fim da barra);
- 189 ``OreWindowMsg``: ``todayRemainTurns`` golpes de hoje, ``curSeq`` o andar do veio (de todo o servidor),
  ``spRewardRemainTimes`` prêmios especiais que ainda posso ganhar hoje (0 abre o alerta ``openTips2``),
  ``countDown`` segundos até o veio novo (-1 o cliente zera a barra);
- 187 ``OreMineRespMsg``: ``passType`` 1 as linhas dos meus achados (somam no painel), 2 as linhas dos prêmios
  especiais do servidor;
- ops: 3 abrir (188, 189, 187 tipo 2), 1 um golpe, 2 dez; ``isUseProp`` gasta a picareta 208523 antes dos Balens
  (``sendOpen``: o preço cai ``oneOpenCost`` por picareta).

Sem captura nem idioma em inglês. TODO(inventado): preços 10/95, 50 golpes e 3 especiais por dia, andares 25/50/75/100,
1 min de espera entre veios, achados e textos; o andar do veio fica na memória do processo (reinício zera).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from ...domain import gameday
from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import bag
from ..builders import login as b
from ..session import GameSession
from . import minijogo as mj
from .player import _player, alert

S_MINE, S_BASE, S_WINDOW, S_OPEN, S_ITEMS = 187, 188, 189, 190, 115
KEY = "stokes_ore"
ONE, TEN, OPEN = 1, 2, 3
MINE, LUCK = 1, 2
PICK = 208523
DEFAULTS: dict[str, Any] = {  # TODO(inventado): sem captura
    "oncePrice": 10,
    "tenPrice": 95,
    "dailyTurns": 50,
    "dailySpecial": 3,
    "cooldown": 60,
    "finds": [[208009, 1, 50], [208014, 1, 30], [3020010, 1, 15], [2131019, 1, 5]],
    "special": [[25, [[208017, 2]]], [50, [[208017, 5]]], [75, [[2131018, 1]]], [100, [[2131023, 1]]]],
}
FIND_LINE = "Received {} x{}"  # TODO(inventado): textos do 187
LUCK_LINE = "{} reached floor {} and received {} x{}"
RNG = random.Random()  # os testes trocam
# shortcut: veio de cada servidor na memória do processo, sem gravar; gravar se o reinício no meio da edição importar
_veins: dict[int, dict[str, Any]] = {}


def _cfg(s: GameSession) -> dict[str, Any]:
    c = mj.cfg(s, KEY)
    return {**DEFAULTS, **c} if c else {}


def open_msg(s: GameSession) -> pb.SimplePropertyMsg:
    c, now = mj.cfg(s, KEY), s.ctx.clock.now()
    if not c:
        return pb.SimplePropertyMsg(param7=False)
    return pb.SimplePropertyMsg(param7=mj.is_open(c, now), param4=str(c["begin"]), param5=str(c["end"]))


def _vein(s: GameSession, now: datetime) -> dict[str, Any]:
    v = _veins.setdefault(s.snapshot.character.server_id if s.snapshot else 0, {"seq": 0, "next": None, "luck": []})
    if v["next"] is not None and now >= v["next"]:
        v["seq"], v["next"] = 0, None
    return v


def _today(snap: PlayerSnapshot, now: datetime) -> dict[str, Any]:
    data = mj.load(snap, KEY)
    day = gameday.today(now)
    return data if data.get("day") == day else {"day": day, "turns": 0, "special": 0}


def _window(c: dict[str, Any], data: dict[str, Any], v: dict[str, Any], now: datetime) -> pb.OreWindowMsg:
    wait = int((v["next"] - now).total_seconds()) if v["next"] else 0
    return pb.OreWindowMsg(
        todayRemainTurns=int(c["dailyTurns"]) - data["turns"],
        curSeq=v["seq"],
        spRewardRemainTimes=int(c["dailySpecial"]) - data["special"],
        countDown=max(wait, 0),
        mineCount=data["turns"],
    )


def _base(c: dict[str, Any]) -> pb.OreActiveBaseInfoMsg:
    msg = pb.OreActiveBaseInfoMsg(
        openTime=str(c["begin"]),
        closeTime=str(c["end"]),
        mineOncePrice=int(c["oncePrice"]),
        mineTimesPrice=int(c["tenPrice"]),
    )
    common = msg.rewards.add(rewardType=0)
    for tid, n, _ in c["finds"]:
        common.rewards.add(templateId=int(tid), count=int(n))
    for kind, (floor, items) in enumerate(c["special"], start=1):
        tier = msg.rewards.add(rewardType=kind, specialFloorNum=int(floor))
        for tid, n in items:
            tier.rewards.add(templateId=int(tid), count=int(n))
    return msg


async def operate(s: GameSession, msg: pb.OreActiveClientOpMsg) -> None:
    c, now, snap = _cfg(s), s.ctx.clock.now(), s.snapshot
    assert snap is not None
    if not c or not mj.is_open(c, now):
        s.send(S_OPEN, open_msg(s))
        return
    v, data = _vein(s, now), _today(snap, now)
    if msg.opType == OPEN:
        s.send(S_BASE, b.complete(_base(c)))
    elif msg.opType in (ONE, TEN):
        await _mine(s, c, snap, v, data, 1 if msg.opType == ONE else 10, msg.isUseProp, now)
    else:
        s.log.info("9645 minério: op desconhecido", op=msg.opType)
    s.send(S_WINDOW, b.complete(_window(c, data, v, now)))
    if msg.opType == OPEN:
        s.send(S_MINE, b.complete(pb.OreMineRespMsg(passType=LUCK, infos=v["luck"])))


async def _mine(
    s: GameSession, c: Any, snap: PlayerSnapshot, v: Any, data: Any, hits: int, use_pick: bool, now: datetime
) -> None:
    floors = {int(f): items for f, items in c["special"]}
    bottom = max(floors)
    hits = min(hits, int(c["dailyTurns"]) - data["turns"], bottom - v["seq"])  # o veio acaba no fundo
    if hits <= 0 or v["next"] is not None:
        s.log.info("9645 minério recusado", golpes=hits, espera=v["next"])
        return
    picks = min(bag.count_of(snap, PICK), hits) if use_pick else 0
    cost = int(c["tenPrice"]) if hits == 10 and not picks else int(c["oncePrice"]) * (hits - picks)
    paid = ledger.pay(snap.character, cost, bind=False, reason="stokes_ore", ref=str(hits), now=now) if cost else None
    if cost and paid is None:
        alert(s, "Insufficient Balens")  # TODO(inventado): o cliente já barra (RechargeAlertMannager)
        return
    changed, gone = bag.take(snap, PICK, picks) if picks else ([], [])
    drops: list[tuple[int, int]] = []
    hit_floors: list[int] = []
    for _ in range(hits):
        tid, n, _w = RNG.choices(c["finds"], weights=[f[2] for f in c["finds"]])[0]
        drops.append((int(tid), int(n)))
        v["seq"] += 1
        if v["seq"] in floors and data["special"] < int(c["dailySpecial"]):
            data["special"] += 1
            hit_floors.append(v["seq"])
            for stid, sn in floors[v["seq"]]:
                drops.append((int(stid), int(sn)))
                name = bag.name(s.ctx.templates, int(stid))
                v["luck"] = [LUCK_LINE.format(snap.character.nickname, v["seq"], name, sn), *v["luck"]][:10]
        if v["seq"] >= bottom:
            v["next"] = now + timedelta(seconds=int(c["cooldown"]))
    data["turns"] += hits
    if changed or gone:
        s.send(S_ITEMS, bag.moved(changed, s.player_id, gone))
    extra = [paid] if paid else []
    await mj.give(s, snap, drops, mj.store(snap, KEY, data, now), *extra, *changed, chat=False, delete=tuple(gone))
    if paid:
        _player(s)
    lines = [FIND_LINE.format(bag.name(s.ctx.templates, t), n) for t, n in drops]
    s.send(S_MINE, b.complete(pb.OreMineRespMsg(passType=MINE, count=hits, floors=hit_floors, infos=lines)))
