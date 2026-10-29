"""Caça ao tesouro, "Great Card Hunt" (9502 ``PlayerSeekInfoMsg {op}`` -> 4914 o mesmo tipo, 4915 linha do diário).

Cliente (``TreasureHuntManager``, ``TreasureHuntControler``, ``TreasureHuntFrame``, ``HunterDialogFrame``,
``SeekType``) e idioma (``hunt.*``):

- nível 32 (``gotoSeekLimit``); até 10 explorações acumuladas, +1 a cada intervalo (``addLastTime``), o
  ``nextAddTime`` é o que falta em segundos (``setTxtState``/``repeatCount``);
- ops: 1 abrir (com ``seekNodeList``: o cliente só lê os nós com ``op`` 1), 2 o relógio venceu, 3 explorar
  (``op`` 3 + ``state`` 1 anda até ``curNodeId`` e abre o diálogo "You are at {nó}. {eventDesc}"), 4 abrir o achado
  (botão do diálogo; ``op`` 4 + ``state`` 0 fecha o alerta), 5 desistir, 6 trocar 100 Summoner's Shard (2131019)
  por 1 Master Summoner's Kit (2131018, ``exchangeBtnTipData``), 7 o botão "+" de exploração;
- 4915 ``MessageForSeekMsg.info``: o cliente guarda as 3 últimas linhas.

Regras em ``game_settings.treasure_hunt`` (migração 0103: ``openGrade``, ``maxCount``, ``interval`` (s), ``addCost``,
``shard``/``kit``/``shardsPerKit``, ``nodes`` [[id, nome, x, y], ...], ``finds`` [[TemplateId, quantidade, peso], ...]
e os textos, cada valor com a ``source``); sem a chave o servidor não responde.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import bag
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .player import _player, alert

S_NODES, S_INFO, S_ITEMS = 4914, 4915, 115
KEY = "treasure_hunt"
OPEN, SYNC, START, TREASURE, GIVE_UP, EXCHANGE, ADD = range(1, 8)
RNG = random.Random()  # os testes trocam


def _state(snap: PlayerSnapshot, c: Any, now: datetime) -> dict[str, Any]:
    """Recarrega as explorações vencidas (``since`` é o começo do intervalo que corre)."""
    data = mj.load(snap, KEY) or {
        "count": int(c["maxCount"]),
        "since": now.isoformat(),
        "state": 0,
        "node": c["nodes"][0][0],
    }
    gained, interval, top = 0, int(c["interval"]), int(c["maxCount"])
    if data["count"] >= top:
        data["since"] = now.isoformat()
    else:
        gained = int((now - datetime.fromisoformat(data["since"])).total_seconds()) // interval
        data["count"] = min(top, data["count"] + gained)
        data["since"] = (datetime.fromisoformat(data["since"]) + timedelta(seconds=gained * interval)).isoformat()
    return data


def _msg(c: Any, data: dict[str, Any], now: datetime, op: int) -> pb.PlayerSeekInfoMsg:
    wait = 0
    if data["count"] < int(c["maxCount"]):
        wait = int(c["interval"]) - int((now - datetime.fromisoformat(data["since"])).total_seconds())
    msg = pb.PlayerSeekInfoMsg(seekCount=data["count"], nextAddTime=max(wait, 0), state=data["state"], op=op)
    msg.curNodeId, msg.eventDesc = data["node"], str(c["eventDesc"]) if data["state"] else ""
    if op == OPEN:
        msg.seekNodeList.SetInParent()
        for nid, name, x, y in c["nodes"]:
            msg.seekNodeList.seekNode.add(nodeId=nid, nodeName=name, pointX=x, pointY=y)
    return msg


def _info(s: GameSession, text: str) -> None:
    s.send(S_INFO, b.complete(pb.MessageForSeekMsg(info=text)))


@router.on(9502)
async def treasure_hunt(s: GameSession, msg: pb.PlayerSeekInfoMsg) -> None:
    snap, now, c = s.snapshot, s.ctx.clock.now(), mj.cfg(s, KEY)
    assert snap is not None
    if not c:
        s.log.info("9502 sem game_settings.treasure_hunt")
        return
    if snap.character.grades < int(c["openGrade"]):
        alert(s, str(c["lowLevelText"]))  # hunt.TreasureHuntFrame.gotoSeekLimit
        return
    shard, per = int(c["shard"]), int(c["shardsPerKit"])
    data, op = _state(snap, c, now), msg.op
    names = {nid: name for nid, name, _, _ in c["nodes"]}
    if op == START and data["count"] > 0 and data["state"] == 0:
        data["count"] -= 1
        data["node"] = RNG.choice([n for n in names if n != data["node"]] or list(names))
        data["state"] = 1
        _info(s, str(c["arriveText"]).format(node=names[data["node"]]))
    elif op == TREASURE and data["state"] == 1:
        tid, count, _ = RNG.choices(c["finds"], weights=[f[2] for f in c["finds"]])[0]
        data["state"] = 0
        text = await mj.give(s, snap, [(int(tid), int(count))], mj.store(snap, KEY, data, now), chat=False)
        _info(s, text)
    elif op == GIVE_UP:
        data["state"] = 0
    elif op == EXCHANGE and bag.count_of(snap, shard) >= per:
        changed, gone = bag.take(snap, shard, per)
        s.send(S_ITEMS, bag.moved(changed, s.player_id, gone))
        await mj.give(s, snap, [(int(c["kit"]), 1)], *changed, delete=tuple(gone))
    elif op == ADD and data["count"] < int(c["maxCount"]):
        paid = ledger.pay(snap.character, int(c["addCost"]), bind=False, reason="seek_add", ref="", now=now)
        if paid is None:
            alert(s, str(c["noMoneyText"]))
        else:
            data["count"] += 1
            await s.ctx.characters.save(paid)
            _player(s)
    elif op not in (OPEN, SYNC):
        s.log.info("9502 recusado", op=op, vezes=data["count"], estado=data["state"])
    await s.ctx.characters.save(mj.store(snap, KEY, data, now), snap.character)
    s.send(S_NODES, b.complete(_msg(c, data, now, op)))
