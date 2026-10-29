"""Sorteio de grupo, "Lucky Draw" da compra coletiva (9523 ``LeadRewardMsg {op}``). Prêmios em
``game_settings.group_draw`` (``items`` [[TemplateId, quantidade], ...] nas 9 casas e ``weights`` opcional).

Cliente (``GroupBuyView``, ``FunnyControler.sendLuckDraw``, ``GroupLuckFrame``):

- op 3 (botão da compra coletiva): 338 ``VipRouletteMsg`` (``leftCount`` sorteios, ``leftItem`` as 9 casas) e o
  cliente abre a roleta;
- op 1 (girar): 4936 ``LeadRewardMsg`` (``templateId`` e ``count`` iguais aos de uma casa, que a roleta procura;
  ``leadExtractTimes`` os que sobram). O cliente barra mochila cheia e zero sorteios antes de pedir;
- op 2: fim da animação, sem resposta (o prêmio já foi no op 1).

Idioma (``dayGuide.view.GroupLuckFrameWarn``): "purchase an item to gain one draw chance (stackable)": cada compra
coletiva soma um sorteio (``add_chance``). A compra coletiva (8645) ainda não existe, então ninguém ganha sorteio.
TODO(inventado): sorteio pelos ``weights`` (uniforme sem eles).
"""

from __future__ import annotations

import random
from datetime import datetime

from ...domain.models import EventState, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import minijogo as mj

S_LIST, S_DRAW = 338, 4936
KEY = "group_draw"
DRAW, DONE, OPEN = 1, 2, 3
RNG = random.Random()  # os testes trocam


def left(snap: PlayerSnapshot) -> int:
    return int(mj.load(snap, KEY).get("left", 0))


def add_chance(snap: PlayerSnapshot, now: datetime) -> EventState:
    """Um sorteio a mais (uma compra coletiva). Grave o estado devolvido junto com a compra."""
    return mj.store(snap, KEY, {"left": left(snap) + 1}, now)


@router.on(9523)
async def group_draw(s: GameSession, msg: pb.LeadRewardMsg) -> None:
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    items = mj.pairs(mj.cfg(s, KEY).get("items", []))[:9]
    n = left(snap)
    if msg.op == OPEN:
        out = pb.VipRouletteMsg(leftCount=n)
        for tid, count in items:
            out.leftItem.add(tempId=tid, count=count)
        s.send(S_LIST, b.complete(out))
    elif msg.op == DRAW and n > 0 and items:
        weights = [float(w) for w in mj.cfg(s, KEY).get("weights", [])][: len(items)] or None
        tid, count = RNG.choices(items, weights=weights)[0]
        await mj.give(s, snap, [(tid, count)], mj.store(snap, KEY, {"left": n - 1}, now))
        s.send(S_DRAW, b.complete(pb.LeadRewardMsg(op=DRAW, templateId=tid, count=count, leadExtractTimes=n - 1)))
    elif msg.op == DRAW:
        s.log.info("9523 sem sorteio", sobram=n, casas=len(items))
        s.send(S_DRAW, b.complete(pb.LeadRewardMsg(op=DRAW, leadExtractTimes=n)))
    elif msg.op != DONE:
        s.log.info("9523 op desconhecido", op=msg.op)
