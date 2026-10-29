"""Caça-níquel (9500 ``SlotActiveRequest {op}`` -> 4901 ``SlotActiveMsg``). Regras em ``game_settings.slot_machine``
(migração 0103: ``begin``/``cycleDays`` edição semanal, ``type``, ``rewardTemplateId``, ``findCost``,
``digitWeights``, ``noMoneyText``, cada valor com a ``source``); sem a chave, fechado (4901 ``open`` falso, como em
todas as capturas oficiais).

Cliente (``SlotManager``, ``SlotFrame``) e ajuda do idioma (``slot.slotHelpFrame.describe``, "Other servers"):

- uma casa por dia da edição, sorteada uma vez por dia "do maior para o menor" (a 1ª casa é o dígito mais alto);
- ``slot``: dígito sorteado, ``*`` sorteio de hoje, ``+`` dia perdido (recupera pagando ``findcost`` Balens),
  ``-`` dia que ainda vem (``conTomorrowNotice``); ``type`` 2 ("Other servers"): o cliente completa com ``#`` até 7;
- ops: 1 abrir, 2 puxar (o ``*``), 11 recuperar (o último ``+``, ``SlotFrame.setCurrentIndexByAdd``), 3 resgatar;
  a resposta repete o ``op`` (``__slotInfoHandler``: 2/11 rodam a animação, 3 apaga o botão);
- ``status`` 1 libera o resgate, 2 já resgatou (``gotRewardNotice``);
- prêmio: o número formado pelas casas na moeda ``rewarditemtemplateid`` (-100 ouro, -300 Daru, -500 Balens
  vinculados, -600 cristais: os quatro ícones de ``setRewardIcon``).

TODO(inventado): casa perdida vale 0 no resgate; resgate liberado quando não sobra ``*`` nem ``-``.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from ...domain import gameday
from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .player import _player, alert

S_SLOT = 4901
KEY = "slot_machine"
OPEN, PULL, CLAIM, RESTORE = 1, 2, 3, 11
CLAIMABLE, CLAIMED = 1, 2
RNG = random.Random()  # os testes trocam


def _days(c: Any, now: datetime) -> tuple[str, int, int]:
    """(edição, número de dias, dia de hoje). Chame só com a edição aberta."""
    ed = mj.edition(c, now)
    assert ed is not None
    first = gameday.game_day(ed[0])
    return mj.fmt(ed[0]), (gameday.game_day(ed[1]) - first).days or 1, (gameday.game_day(now) - first).days


def _state(snap: PlayerSnapshot, edition: str) -> dict[str, Any]:
    data = mj.load(snap, KEY)
    if data.get("edition") != edition:  # edição nova: tudo do zero
        data = {"edition": edition, "digits": {}, "claimed": False}
    return data


def _slot(c: Any, data: dict[str, Any], now: datetime) -> str:
    _, days, today = _days(c, now)
    digits = data["digits"]
    return "".join(
        str(digits[str(d)]) if str(d) in digits else "+" if d < today else "*" if d == today else "-"
        for d in range(days)
    )


def _msg(c: Any, data: dict[str, Any], now: datetime, op: int) -> pb.SlotActiveMsg:
    slot = _slot(c, data, now)
    status = CLAIMED if data["claimed"] else CLAIMABLE if "*" not in slot and "-" not in slot else 0
    return pb.SlotActiveMsg(open=True, op=op, status=status, slot=slot, type=int(c["type"]),
                            rewarditemtemplateid=int(c["rewardTemplateId"]), findcost=int(c["findCost"]))  # fmt: skip


def _roll(c: Any) -> int:
    return RNG.choices(range(10), weights=[float(w) for w in c["digitWeights"]])[0]


def login_push(s: GameSession) -> None:
    """Só com edição aberta (o ícone do topo precisa do ``open``; fechado, o servidor não manda nada)."""
    c, snap, now = mj.cfg(s, KEY), s.snapshot, s.ctx.clock.now()
    if snap is not None and mj.is_open(c, now):
        s.send(S_SLOT, b.complete(_msg(c, _state(snap, _days(c, now)[0]), now, 0)))


@router.on(9500)
async def slot(s: GameSession, msg: pb.SlotActiveRequest) -> None:
    c, now = mj.cfg(s, KEY), s.ctx.clock.now()
    snap = s.snapshot
    assert snap is not None
    if not mj.is_open(c, now):
        s.send(S_SLOT, b.complete(pb.SlotActiveMsg(open=False, op=0)))
        return
    data = _state(snap, _days(c, now)[0])
    slot_ = _slot(c, data, now)
    op = msg.op
    if op == PULL and "*" in slot_ and not data["claimed"]:
        data["digits"][str(slot_.index("*"))] = _roll(c)
        await s.ctx.characters.save(mj.store(snap, KEY, data, now))
    elif op == RESTORE and "+" in slot_ and not data["claimed"]:
        cost = int(c["findCost"])
        paid = ledger.pay(snap.character, cost, bind=False, reason="slot_restore", ref=data["edition"], now=now)
        if paid is None:
            alert(s, str(c["noMoneyText"]))
            op = OPEN
        else:
            data["digits"][str(slot_.rindex("+"))] = _roll(c)
            await s.ctx.characters.save(snap.character, paid, mj.store(snap, KEY, data, now))
            _player(s)
    elif op == CLAIM and _msg(c, data, now, op).status == CLAIMABLE:
        data["claimed"] = True
        number = int("".join(str(data["digits"].get(str(d), 0)) for d in range(len(slot_))))
        st = mj.store(snap, KEY, data, now)
        if number > 0:
            await mj.give(s, snap, [(int(c["rewardTemplateId"]), number)], st)
        else:
            await s.ctx.characters.save(st)
    elif op != OPEN:
        s.log.info("9500 recusado", op=op, slot=slot_, resgatado=data["claimed"])
        op = OPEN
    s.send(S_SLOT, b.complete(_msg(c, data, now, op)))
