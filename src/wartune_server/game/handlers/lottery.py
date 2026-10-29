"""Loteria, "Wheel of Prosperity" (8750 abrir, 8748 girar). Regras em ``game_settings.lottery`` (migração 0103: edição
``begin``/``cycleDays``, ``onceNeedPoint``, ``dayMaxCount``, ``items`` [[TemplateId, quantidade], ...] até 16,
``weights``, ``noticeText``, ``notices``); sem ela, fechada (4637 ``isOpen`` falso, como em todas as capturas).

Cliente (``LotteryManager``, ``LotteryFrame``) e idioma (``lottery.LotteryFrame.describe``: "cumulatively consumes
{0} Balens to obtain a Lucky Draw attempt", "a maximum of {1} Lucky Draw attempts daily"):

- 8750: 4637 (estado), 4636 (``LotteryMsg``: ``payedPoint`` gasto de hoje, ``onceNeedPoint``, ``dayMaxCount``,
  ``dayAddCount`` tentativas ganhas hoje, ``totalCount``, ``leftCount``, ``leftMillis`` até o fim), 4641 (as casas,
  ``VipRouletteMsg.leftItem``) e 4639 (``property3``, os últimos prêmios, canal 21);
- 8748: 4642 (``SimplePropertyMsg``: ``param1`` TemplateId sorteado, igual ao de uma casa; ``param2`` tentativas
  que sobram; ``param3`` quantidade). O cliente põe "Obtained {0}x{1}" no chat sozinho.

As tentativas saem do ``cash_ledger``: por dia do jogo, ``min(dayMaxCount, gasto // onceNeedPoint)``.
Os últimos prêmios do servidor ficam gravados na linha ``lottery:notices`` de quem girou por último (``mj.shared``).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from ...domain import gameday
from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import minijogo as mj

S_INFO, S_STATE, S_NOTICE, S_ITEMS, S_RESULT = 4636, 4637, 4639, 4641, 4642
KEY = "lottery"
NOTICES = "lottery:notices"
RNG = random.Random()  # os testes trocam


def state_msg(s: GameSession) -> pb.LotteryMsg:
    return pb.LotteryMsg(isOpen=mj.is_open(mj.cfg(s, KEY), s.ctx.clock.now()))


async def _earned(s: GameSession, c: Any, now: datetime) -> tuple[int, int, int]:
    """(ganhas na edição, ganhas hoje, Balens gastos hoje)."""
    once, cap = int(c["onceNeedPoint"]), int(c["dayMaxCount"])
    start, total, today, paid = gameday.day_start(_edition(c, now)[0]), 0, 0, 0
    while start <= now:
        end = start + timedelta(days=1)
        spent = await s.ctx.characters.read(lambda uow, a=start, z=end: uow.characters.spent(s.player_id, a, z))
        today, paid = min(cap, spent // once), spent
        total += today
        start = end
    return total, today, paid


def _edition(c: Any, now: datetime) -> tuple[datetime, datetime]:
    ed = mj.edition(c, now)
    assert ed is not None
    return ed


def _used(snap: PlayerSnapshot, c: Any, now: datetime) -> int:
    data = mj.load(snap, KEY)
    return int(data.get("used", 0)) if data.get("edition") == mj.fmt(_edition(c, now)[0]) else 0


async def _notices(s: GameSession, c: Any, now: datetime) -> list[str]:
    data = await mj.shared(s, NOTICES)
    return list(data.get("lines", [])) if data.get("edition") == mj.fmt(_edition(c, now)[0]) else []


@router.on(8750)
async def lottery(s: GameSession, _: object) -> None:
    c, now, snap = mj.cfg(s, KEY), s.ctx.clock.now(), s.snapshot
    assert snap is not None
    s.send(S_STATE, state_msg(s))
    if not mj.is_open(c, now):
        return
    total, today, paid = await _earned(s, c, now)
    info = pb.LotteryMsg(
        payedPoint=paid,
        totalCount=total,
        leftCount=total - _used(snap, c, now),
        dayMaxCount=int(c["dayMaxCount"]),
        onceNeedPoint=int(c["onceNeedPoint"]),
        leftMillis=mj.left_ms(c, now),
        isOpen=True,
        dayAddCount=today,
    )
    s.send(S_INFO, b.complete(info))
    items = pb.VipRouletteMsg()
    for tid, n in mj.pairs(c["items"])[:16]:
        items.leftItem.add(tempId=tid, count=n)
    s.send(S_ITEMS, b.complete(items))
    s.send(S_NOTICE, b.complete(pb.LotteryMsg(property3=await _notices(s, c, now))))


@router.on(8748)
async def spin(s: GameSession, _: object) -> None:
    c, now, snap = mj.cfg(s, KEY), s.ctx.clock.now(), s.snapshot
    assert snap is not None
    if not mj.is_open(c, now) or not c["items"]:
        s.send(S_STATE, state_msg(s))  # o cliente fecha a tela com isOpen falso
        return
    items = mj.pairs(c["items"])[:16]
    total = (await _earned(s, c, now))[0]
    used = _used(snap, c, now)
    if used >= total:
        s.log.info("8748 sem tentativa", ganhas=total, usadas=used)
        s.send(S_RESULT, b.complete(pb.SimplePropertyMsg(param1=0, param2=0)))
        return
    tid, n = RNG.choices(items, weights=[float(w) for w in c["weights"]][: len(items)])[0]
    edition = mj.fmt(_edition(c, now)[0])
    name = (s.ctx.templates.get("ItemTempInfos", tid) or {}).get("TemplateName", str(tid))
    line = str(c["noticeText"]).format(nick=snap.character.nickname, item=name, count=n)
    lines = [line, *await _notices(s, c, now)][: int(c["notices"])]
    st = mj.store(snap, KEY, {"edition": edition, "used": used + 1}, now)
    board = mj.store(snap, NOTICES, {"edition": edition, "lines": lines}, now)
    await mj.give(s, snap, [(tid, n)], st, board, chat=False)  # o 83 "Obtained" é do cliente (LotteryFrame)
    s.send(S_RESULT, b.complete(pb.SimplePropertyMsg(param1=tid, param2=total - used - 1, param3=n)))
