"""Wishing Wall do Sky Trails: virar cartas com Heaven Horn (3150001).

Cliente: ``SinglePassSocketOutManager.sendRequestBugleOpen``/``sendRequestBugleRoulette``,
``SinglePassManager.__bugleReqHandler``/``__bugleRewardsHandler`` e ``singlepass.bugle.SinglePassBugleView`` (m11).

* 8640 (sem corpo): mesa nova; 4553 ``leftItem`` = as 8 cartas (``SinglePassBugleView`` tem ``pos_1``..``pos_8``).
  A tela manda ao abrir e no "de novo" (``__againBtnClickHandler``), que recomeça a mesa e o custo.
* 8639 ``VipRouletteMsg.leftCount`` = carta 1..8, ``opType`` 0 = vinculado primeiro (``openCard(i, useBind)``).
  Cada carta gasta 1 Heaven Horn (``__itemClickHandler`` recusa sem corneta) e o ``needVipItem`` da resposta
  anterior em Balens (a primeira é grátis: ``_currentPointsCost`` começa em 0).
* 4554: ``needVipItem`` = custo da próxima, ``leftCount`` = cartas já viradas (> 0 mostra "de novo"),
  ``openIndex`` = posições viradas e ``leftItem`` alinhado a elas (``openIndex.indexOf``).

TODO(inventado): prêmios, pesos e custos em ``game_settings.wishing_wall`` (migração 0122); sem captura.
"""

from __future__ import annotations

import random
from typing import Any

from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import bag, rewards
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .player import S_ITEMS
from .singlepass import BUGLE
from .vip import wheel_pick

S_BUGLE_REQ, S_BUGLE_REWARD = 4553, 4554
KEY = "wishwall"
CARDS = 8  # SinglePassBugleView.initView: pos_1..pos_8
BIND = 0  # opType 0 = sendRequestBugleRoulette(i, true): usa o vinculado
_rng = random.Random()  # os testes trocam por um com semente


def _prizes(s: GameSession) -> list[list[int]]:
    """``[templateId, quantidade, peso]`` das 8 cartas."""
    return [list(map(int, p)) for p in mj.cfg(s, "wishing_wall").get("prizes", [])][:CARDS]


def _cost(s: GameSession, opened: int) -> int:
    costs = mj.cfg(s, "wishing_wall").get("costs") or [0]
    return int(costs[min(opened, len(costs) - 1)])


def _result(s: GameSession, opened: list[list[int]]) -> pb.VipRouletteMsg:
    prizes = _prizes(s)
    msg = pb.VipRouletteMsg(needVipItem=_cost(s, len(opened)), leftCount=len(opened))
    for pos, i in opened:
        msg.openIndex.append(pos)
        msg.leftItem.add(tempId=prizes[i][0], count=prizes[i][1])
    return msg


@router.on(8640)
async def open_wall(s: GameSession, _: object) -> None:
    snap = s.snapshot
    assert snap is not None
    msg = pb.VipRouletteMsg()
    for t, n, _w in _prizes(s):
        msg.leftItem.add(tempId=t, count=n)
    await s.ctx.characters.save(mj.store(snap, KEY, {"open": []}, s.ctx.clock.now()))
    s.send(S_BUGLE_REQ, msg)


@router.on(8639)
async def flip(s: GameSession, msg: pb.VipRouletteMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    now, prizes = s.ctx.clock.now(), _prizes(s)
    d: dict[str, Any] = mj.load(snap, KEY)
    opened: list[list[int]] = d.get("open", [])
    pos, cost = msg.leftCount, _cost(s, len(opened))
    index = wheel_pick([p[2] for p in prizes], [i for _, i in opened], _rng)
    reason = (
        "mesa fechada" if "open" not in d or len(prizes) < CARDS
        else "carta inválida" if not 1 <= pos <= CARDS or any(p == pos for p, _ in opened)
        else "sem cartas" if index is None
        else "sem Heaven Horn" if bag.count_of(snap, BUGLE) < 1
        else ""
    )  # fmt: skip
    spent = None
    if not reason and cost > 0:
        spent = ledger.pay(snap.character, cost, bind=msg.opType == BIND, reason="wishing_wall", ref=str(pos), now=now)
        reason = "" if spent is not None else "sem Balens"
    taken = rewards.take_one(snap, BUGLE) if not reason else None
    if reason or index is None or taken is None:
        s.log.info("8639 recusado", motivo=reason or "sem Heaven Horn", carta=pos)
        s.send(S_BUGLE_REWARD, _result(s, opened))
        return
    opened.append([pos, index])
    item, gone = taken
    st = mj.store(snap, KEY, {"open": opened}, now)
    extra = [x for x in (spent, None if gone else item) if x is not None]
    s.send(S_ITEMS, rewards.taken_msg(item, gone, s.player_id))
    await mj.give(s, snap, [(prizes[index][0], prizes[index][1])], st, *extra, delete=(item,) if gone else ())
    s.send(S_BUGLE_REWARD, _result(s, opened))
