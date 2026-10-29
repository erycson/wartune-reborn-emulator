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

Sem captura (todas mostram o estado fechado). TODO(inventado): os nós (nomes e posições), os achados e o texto,
1 exploração a cada 30 min, o "+" por 10 Balens. ``game_settings.treasure_hunt`` troca ``nodes``, ``finds``
([[TemplateId, quantidade, peso], ...]), ``interval`` (s) e ``addCost``.
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
OPEN_GRADE, MAX_COUNT = 32, 10
SHARD, MASTER_KIT, SHARDS_PER_KIT = 2131019, 2131018, 100
# TODO(inventado): mapa, achados, intervalo e preço (sem captura nem internet)
NODES = [
    (1, "Whispering Woods", 120, 330),
    (2, "Old Watchtower", 230, 210),
    (3, "Misty Lake", 350, 300),
    (4, "Ruined Temple", 470, 180),
    (5, "Dragon Bones", 560, 320),
    (6, "Crystal Cave", 650, 200),
]
FINDS = [[SHARD, 5, 50], [SHARD, 10, 25], [2131016, 1, 15], [2131017, 1, 8], [MASTER_KIT, 1, 2]]
EVENT = "you found a buried chest!"
INTERVAL, ADD_COST = 1800, 10
RNG = random.Random()  # os testes trocam


def _cfg(s: GameSession) -> dict[str, Any]:
    c = mj.cfg(s, KEY)
    return {"nodes": NODES, "finds": FINDS, "interval": INTERVAL, "addCost": ADD_COST, **c}


def _state(snap: PlayerSnapshot, c: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Recarrega as explorações vencidas (``since`` é o começo do intervalo que corre)."""
    data = mj.load(snap, KEY) or {"count": MAX_COUNT, "since": now.isoformat(), "state": 0, "node": c["nodes"][0][0]}
    gained, interval = 0, int(c["interval"])
    if data["count"] >= MAX_COUNT:
        data["since"] = now.isoformat()
    else:
        gained = int((now - datetime.fromisoformat(data["since"])).total_seconds()) // interval
        data["count"] = min(MAX_COUNT, data["count"] + gained)
        data["since"] = (datetime.fromisoformat(data["since"]) + timedelta(seconds=gained * interval)).isoformat()
    return data


def _msg(c: dict[str, Any], data: dict[str, Any], now: datetime, op: int) -> pb.PlayerSeekInfoMsg:
    wait = 0
    if data["count"] < MAX_COUNT:
        wait = int(c["interval"]) - int((now - datetime.fromisoformat(data["since"])).total_seconds())
    msg = pb.PlayerSeekInfoMsg(seekCount=data["count"], nextAddTime=max(wait, 0), state=data["state"], op=op)
    msg.curNodeId, msg.eventDesc = data["node"], EVENT if data["state"] else ""
    if op == OPEN:
        msg.seekNodeList.SetInParent()
        for nid, name, x, y in c["nodes"]:
            msg.seekNodeList.seekNode.add(nodeId=nid, nodeName=name, pointX=x, pointY=y)
    return msg


def _info(s: GameSession, text: str) -> None:
    s.send(S_INFO, b.complete(pb.MessageForSeekMsg(info=text)))


@router.on(9502)
async def treasure_hunt(s: GameSession, msg: pb.PlayerSeekInfoMsg) -> None:
    snap, now, c = s.snapshot, s.ctx.clock.now(), _cfg(s)
    assert snap is not None
    if snap.character.grades < OPEN_GRADE:
        alert(s, "Must be at least level 32 to claim.")  # hunt.TreasureHuntFrame.gotoSeekLimit
        return
    data, op = _state(snap, c, now), msg.op
    names = {nid: name for nid, name, _, _ in c["nodes"]}
    if op == START and data["count"] > 0 and data["state"] == 0:
        data["count"] -= 1
        data["node"] = RNG.choice([n for n in names if n != data["node"]] or list(names))
        data["state"] = 1
        _info(s, f"You arrived at {names[data['node']]}.")  # TODO(inventado)
    elif op == TREASURE and data["state"] == 1:
        tid, count, _ = RNG.choices(c["finds"], weights=[f[2] for f in c["finds"]])[0]
        data["state"] = 0
        text = await mj.give(s, snap, [(int(tid), int(count))], mj.store(snap, KEY, data, now), chat=False)
        _info(s, text)
    elif op == GIVE_UP:
        data["state"] = 0
    elif op == EXCHANGE and bag.count_of(snap, SHARD) >= SHARDS_PER_KIT:
        changed, gone = bag.take(snap, SHARD, SHARDS_PER_KIT)
        s.send(S_ITEMS, bag.moved(changed, s.player_id, gone))
        await mj.give(s, snap, [(MASTER_KIT, 1)], *changed, delete=tuple(gone))
    elif op == ADD and data["count"] < MAX_COUNT:
        paid = ledger.pay(snap.character, int(c["addCost"]), bind=False, reason="seek_add", ref="", now=now)
        if paid is None:
            alert(s, "Insufficient Balens")  # TODO(inventado)
        else:
            data["count"] += 1
            await s.ctx.characters.save(paid)
            _player(s)
    elif op not in (OPEN, SYNC):
        s.log.info("9502 recusado", op=op, vezes=data["count"], estado=data["state"])
    await s.ctx.characters.save(mj.store(snap, KEY, data, now), snap.character)
    s.send(S_NODES, b.complete(_msg(c, data, now, op)))
