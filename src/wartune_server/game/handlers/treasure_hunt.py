"""Caça ao tesouro, "Great Card Hunt" (9502 ``PlayerSeekInfoMsg {op}`` -> 4914 o mesmo tipo, 4915 linha do diário).

Cliente (``TreasureHuntManager``, ``TreasureHuntControler``, ``TreasureHuntFrame``, ``HunterDialogFrame``,
``SeekType``) e idioma (``hunt.*``):

- nível 32 (``gotoSeekLimit``); até 10 explorações acumuladas, +1 a cada intervalo (``addLastTime``), o
  ``nextAddTime`` é o que falta em segundos (``setTxtState``/``repeatCount``);
- ops: 1 abrir (com ``seekNodeList``: o cliente só lê os nós com ``op`` 1), 2 o relógio venceu, 3 explorar
  (``op`` 3 + ``state`` 1 anda até ``curNodeId`` e abre o diálogo "You are at {nó}. {eventDesc}"), 4 o botão de
  confirmar do diálogo (pagar o ouro e levar o tesouro; o diálogo não se fecha sozinho, o segundo clique chega como
  outro op 4), 5 desistir, 6 trocar 100 Summoner's Shard (2131019) por 1 Master Summoner's Kit (2131018,
  ``exchangeBtnTipData``), 7 o botão "+" de exploração (sem confirmação): gasta 1 Exploration Artifact (2131022),
  115, 111 "Treasure Hunt attempts increased!" e 4914 op 2; sem o item só o 111 (d29 #2803-#2806, #2859-#2860);
- 4915 ``MessageForSeekMsg.info``: o cliente guarda as 3 últimas linhas.

Captura inglesa 20261029-121453-1 (d29): #447-#448 op 1 (3 explorações, 21600 s, nó 7, 36 nós); #449-#453 op 3:
4476 só da atividade "Great Card Hunt" (tipo 101) e o 4426, 112 da missão 930, 4914 ``state`` 1 com ``eventDesc``
(sem 4915); #465-#496 e #551-#570 op 4: 109 (-32000 de ouro), 115 do que coube, 4476 de todas/4426, 4484 ×9, 148 se
foi algo pelo correio, 111 "Received: ...[, inventory full, please check your mail!]", 4915 "Gained Ax1,Bxn from
{nó}", 4914 ``state`` 0, 83 com o texto do 111 e 83 com o do 4915; #514-#528 op 4 sem tesouro: só 111 "Operation
failed". O correio é "Treasure Hunt Rewards" com o que não coube (4131 #606). Cada ``eventDesc`` tem a sua moeda:
ouro sai no 109, Daru (``strategy``) no 3 no lugar do 109 (#2837-#2840: 3, 115, 4476...).

Captura 20261031-183522-1 (#8956-#9254, nível 34): o prêmio é sorteado (kit Novice/Expert x1 + 2-5 shards, o mesmo
nó dá prêmios diferentes) e a moeda é sorteada à parte do texto (a caravana pede Gold em #8962 e Kyanite em #8985);
o preço é por nível: 1000 Gold, 600 Daru ou 20 Kyanite (``crystals``, no 109) por nível. Sem reset diário.

Regras em ``game_settings.treasure_hunt`` (migrações 0136, 0137 e 0145, cada valor com a ``source``); sem a chave o
servidor não responde.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from .. import bag, rewards, rules
from .. import events as ev
from ..builders import login as b
from ..castle import castle_yield
from ..mail import notify as notify_mail
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .player import S_CHAT, _player, alert, granted
from .shop import place, save_with_mail

S_NODES, S_INFO, S_ITEMS = 4914, 4915, 115
KEY = "treasure_hunt"
OPEN, SYNC, START, TREASURE, GIVE_UP, EXCHANGE, ADD = range(1, 8)
RNG = random.Random()  # os testes trocam


def _state(snap: PlayerSnapshot, c: Any, now: datetime) -> dict[str, Any]:
    """Recarrega as explorações vencidas (``since`` é o começo do intervalo que corre). A primeira abertura começa
    com ``startCount`` e o relógio cheio (d29 #448: 3 e 21600)."""
    data = mj.load(snap, KEY) or {
        "count": int(c["startCount"]),
        "since": now.isoformat(),
        "state": 0,
        "node": int(c["startNode"]),
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
    desc = data.get("desc", "")
    msg.curNodeId, msg.eventDesc = (
        data["node"],
        str(desc[0] if isinstance(desc, list) else desc) if data["state"] else "",
    )
    if op == OPEN:
        msg.seekNodeList.SetInParent()
        for nid, name, x, y in c["nodes"]:
            msg.seekNodeList.seekNode.add(nodeId=nid, nodeName=name, pointX=x, pointY=y)
    return msg


def _cost(data: dict[str, Any]) -> tuple[str, int]:
    """(moeda, valor) do evento sorteado; estado gravado antes da 0137 (só o texto) era de ouro."""
    desc = data.get("desc")
    return (str(desc[1]), int(desc[2])) if isinstance(desc, list) else ("gold", 32000)


def _event(c: Any, grade: int) -> list[Any]:
    """[texto, moeda, valor]: texto e moeda sorteados à parte, o valor é o da moeda por nível (0145)."""
    coin, per, name = RNG.choice(c["coins"])
    cost = int(per) * grade
    return [str(RNG.choice(c["eventDescs"])).format(cost=f"{cost} {name}"), str(coin), cost]


def _pay(snap: PlayerSnapshot, coin: str, cost: int) -> bool:
    ch = snap.character
    field = {"daru": "strategy", "kyanite": "crystals"}.get(coin, "gold")
    if getattr(ch, field) < cost:
        return False
    setattr(ch, field, getattr(ch, field) - cost)
    return True


def _prize(c: Any) -> list[tuple[int, int]]:
    """Kit x1 e Summoner's Shard xN sorteados (0145; o prêmio não é do nó)."""
    kit = RNG.choices([k for k, _ in c["prizeKits"]], weights=[w for _, w in c["prizeKits"]])[0]
    n = RNG.choices([k for k, _ in c["prizeShards"]], weights=[w for _, w in c["prizeShards"]])[0]
    return [(int(kit), 1), (int(c["shard"]), int(n))]


async def _treasure(s: GameSession, snap: PlayerSnapshot, c: Any, data: dict[str, Any], node: str) -> None:
    """op 4 com tesouro: paga o ouro, dá o prêmio do nó (o que não cabe vai pelo correio) e manda na ordem do d29."""
    templates, now = s.ctx.templates, s.ctx.clock.now()
    drops = _prize(c)
    coin, _ = _cost(data)
    data["state"] = 0
    got, letters = place(s, snap, s.player_id, drops, now)
    for letter, _, items in letters:  # 4131 #606: título fixo, texto com o que foi no correio
        letter.title = str(c["mailTitle"])
        letter.contents = ", ".join(f"{rewards._name(templates, i.template_id)} x{i.count}" for i in items)
        letter.validity_days, letter.send_type = int(c["mailDays"]), int(c["mailSendType"])
    state = mj.store(snap, KEY, data, now)
    await save_with_mail(s, letters, snap.character, state, *got, notify=False)
    if coin == "daru":
        _player(s)  # d29 #2839
    else:
        castle_yield(s)  # ouro e Kyanite (crystalsCount, 183522 #8987)
    await granted(s, drops, got, "", chat=False, player=None)
    for letter, _, _ in letters:
        notify_mail(s.ctx.online, letter)
    text = rewards.text(templates, drops) + (str(c["mailSuffix"]) if letters else "")
    found = ",".join(f"{rewards._name(templates, t)}x{n}" for t, n in drops)
    gained = str(c["gainedText"]).format(items=found, node=node)
    alert(s, text)
    s.send(S_INFO, b.complete(pb.MessageForSeekMsg(info=gained)))
    s.send(S_NODES, b.complete(_msg(c, data, now, TREASURE)))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=gained))


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
    if op == TREASURE:
        if data["state"] != 1:  # d29 #514-#528: o segundo clique do diálogo
            alert(s, str(c["failText"]))
            return
        if not _pay(snap, *_cost(data)):
            alert(s, str(c["noGoldText"]))  # TODO(inventado): sem captura de ouro insuficiente
            return
        await _treasure(s, snap, c, data, names[data["node"]])
        return
    explored = op == START and data["count"] > 0 and data["state"] == 0
    counted = []
    if explored:
        data["count"] -= 1
        data["node"] = RNG.choice([n for n in names if n != data["node"]] or list(names))
        data["state"], data["desc"] = 1, _event(c, snap.character.grades)
        counted = ev.count(snap, s.ctx.events, ev.GREAT_CARD_HUNT, now)
    elif op == GIVE_UP:
        data["state"] = 0
    elif op == EXCHANGE and bag.count_of(snap, shard) >= per:
        changed, gone = bag.take(snap, shard, per)
        s.send(S_ITEMS, bag.moved(changed, s.player_id, gone))
        await mj.give(s, snap, [(int(c["kit"]), 1)], *changed, delete=tuple(gone))
    elif op == ADD:
        if data["count"] >= int(c["maxCount"]):
            # TreasureHuntFrame._addSeekCountClick manda sem conferir: recusa com o huntcountFull, sem gastar o item
            alert(s, str(c["fullText"]))
            return
        if bag.count_of(snap, int(c["addItem"])) < 1:
            alert(s, str(c["addNoItemText"]))  # d29 #2860: só o 111
            return
        changed, gone = bag.take(snap, int(c["addItem"]), 1)
        data["count"] += 1
        await s.ctx.characters.save(mj.store(snap, KEY, data, now), *changed, delete=tuple(gone))
        s.send(S_ITEMS, bag.moved(changed, s.player_id, gone))
        alert(s, str(c["addOkText"]))
        s.send(S_NODES, b.complete(_msg(c, data, now, SYNC)))  # d29 #2806: op 2
        return
    elif op not in (OPEN, SYNC):
        s.log.info("9502 recusado", op=op, vezes=data["count"], estado=data["state"])
    await s.ctx.characters.save(mj.store(snap, KEY, data, now), snap.character, *counted)
    if explored:  # d29 #450-#452: 4476 só desta/4426 e o 112 antes do 4914
        from .army import count_quest
        from .events import progress_of

        if counted:
            progress_of(s, ev.GREAT_CARD_HUNT)
        await count_quest(s, rules.EXPLORE_CONDITION)  # 930
    s.send(S_NODES, b.complete(_msg(c, data, now, op)))
