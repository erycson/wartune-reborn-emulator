"""Loteria, "Wheel of Prosperity" (8750 abrir, 8748 girar). Edição em ``game_settings.lottery`` (``begin``/``end``
em hora do jogo, ``onceNeedPoint``, ``dayMaxCount``, ``items`` [[TemplateId, quantidade], ...] até 16 e ``weights``
opcional); sem ela, fechada (4637 ``isOpen`` falso, como em todas as capturas).

Cliente (``LotteryManager``, ``LotteryFrame``) e idioma (``lottery.LotteryFrame.describe``: "cumulatively consumes
{0} Balens to obtain a Lucky Draw attempt", "a maximum of {1} Lucky Draw attempts daily"):

- 8750: 4637 (estado), 4636 (``LotteryMsg``: ``payedPoint`` gasto de hoje, ``onceNeedPoint``, ``dayMaxCount``,
  ``dayAddCount`` tentativas ganhas hoje, ``totalCount``, ``leftCount``, ``leftMillis`` até o fim), 4641 (as casas,
  ``VipRouletteMsg.leftItem``) e 4639 (``property3``, os últimos prêmios, canal 21);
- 8748: 4642 (``SimplePropertyMsg``: ``param1`` TemplateId sorteado, igual ao de uma casa; ``param2`` tentativas
  que sobram; ``param3`` quantidade). O cliente põe "Obtained {0}x{1}" no chat sozinho.

As tentativas saem do ``cash_ledger``: por dia do jogo, ``min(dayMaxCount, gasto // onceNeedPoint)``.
TODO(inventado): sorteio pelos ``weights`` (uniforme sem eles), padrões 100 Balens e 5 por dia, texto do 4639.
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
ONCE, DAY_MAX = 100, 5  # TODO(inventado): padrões quando a edição não diz
NOTICE = "{} obtained {} x{}"  # TODO(inventado): o texto do 4639 não está em captura nem no idioma
NOTICES = 10
RNG = random.Random()  # os testes trocam
_notices: dict[str, list[str]] = {}  # edição -> últimos prêmios do servidor (memória: some ao reiniciar)


def state_msg(s: GameSession) -> pb.LotteryMsg:
    return pb.LotteryMsg(isOpen=mj.is_open(mj.cfg(s, KEY), s.ctx.clock.now()))


async def _earned(s: GameSession, c: Any, now: datetime) -> tuple[int, int, int]:
    """(ganhas na edição, ganhas hoje, Balens gastos hoje)."""
    once, cap = int(c.get("onceNeedPoint", ONCE)), int(c.get("dayMaxCount", DAY_MAX))
    start, total, today, paid = gameday.day_start(mj.at(c, "begin")), 0, 0, 0
    while start <= now:
        end = start + timedelta(days=1)
        spent = await s.ctx.characters.read(lambda uow, a=start, z=end: uow.characters.spent(s.player_id, a, z))
        today, paid = min(cap, spent // once), spent
        total += today
        start = end
    return total, today, paid


def _used(snap: PlayerSnapshot, c: Any) -> int:
    data = mj.load(snap, KEY)
    return int(data.get("used", 0)) if data.get("edition") == c["begin"] else 0


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
        leftCount=total - _used(snap, c),
        dayMaxCount=int(c.get("dayMaxCount", DAY_MAX)),
        onceNeedPoint=int(c.get("onceNeedPoint", ONCE)),
        leftMillis=mj.left_ms(c, now),
        isOpen=True,
        dayAddCount=today,
    )
    s.send(S_INFO, b.complete(info))
    items = pb.VipRouletteMsg()
    for tid, n in mj.pairs(c.get("items", []))[:16]:
        items.leftItem.add(tempId=tid, count=n)
    s.send(S_ITEMS, b.complete(items))
    s.send(S_NOTICE, b.complete(pb.LotteryMsg(property3=_notices.get(c["begin"], []))))


@router.on(8748)
async def spin(s: GameSession, _: object) -> None:
    c, now, snap = mj.cfg(s, KEY), s.ctx.clock.now(), s.snapshot
    assert snap is not None
    items = mj.pairs(c.get("items", []))[:16] if c else []
    if not mj.is_open(c, now) or not items:
        s.send(S_STATE, state_msg(s))  # o cliente fecha a tela com isOpen falso
        return
    total = (await _earned(s, c, now))[0]
    used = _used(snap, c)
    if used >= total:
        s.log.info("8748 sem tentativa", ganhas=total, usadas=used)
        s.send(S_RESULT, b.complete(pb.SimplePropertyMsg(param1=0, param2=0)))
        return
    weights = [float(w) for w in c.get("weights", [])][: len(items)] or None
    tid, n = RNG.choices(items, weights=weights)[0]
    st = mj.store(snap, KEY, {"edition": c["begin"], "used": used + 1}, now)
    await mj.give(s, snap, [(tid, n)], st, chat=False)  # o 83 "Obtained" é do cliente (LotteryFrame)
    s.send(S_RESULT, b.complete(pb.SimplePropertyMsg(param1=tid, param2=total - used - 1, param3=n)))
    name = (s.ctx.templates.get("ItemTempInfos", tid) or {}).get("TemplateName", str(tid))
    notices = _notices.setdefault(c["begin"], [])
    notices.insert(0, NOTICE.format(snap.character.nickname, name, n))
    del notices[NOTICES:]
