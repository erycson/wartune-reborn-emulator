"""Compra coletiva (8645 ``ShopMsg``; oferta ``type`` 3 do 4238). Regras em ``game_settings.group_buy`` (migração
0104): ``begin``/``cycleDays`` repetem a edição, ``buyHours`` é a fase de compra e o resto da edição a de acerto;
``offers`` gira uma por edição (rodízio).

Cliente (``GroupBuyView``, ``GroupBuyListItem``, ``GroupBuyProgressBar``, ``CheckView``, ``ShopModel``):

- ``payType`` 3 (clique na lista): 4559 ``GrouponShopMsg`` com o estado (``curCount`` do servidor, ``curPrice``,
  ``buyCount``/``totalPoint`` meus, ``count`` de hoje, ``isReward`` acertado, ``frontMoney``);
- ``payType`` 1 (Buy, até ``endDate``): cobra ``frontMoney`` (sinal) em Balens; o cliente barra ``maxCount`` do
  servidor e ``oneDayCount`` meu por dia; cada unidade dá 1 sorteio de grupo (``group_draw.add_chance``);
- ``payType`` 2 (Settle, entre ``endDate`` e ``sendDate``): preço final = ``buyCount * curPrice``; a diferença para o
  que já pagou é cobrada ou devolvida (``jiesuanHandler``), e os itens saem (mochila; cheia, correio). 4560 com
  ``buyCount``, ``totalPoint`` e ``param1`` = Balens devolvidos (``CheckView`` "fanhui").

Preço: ``price`` até ``level1`` compradores no servidor, depois ``price1``/``price2``/``price3``
(``GroupBuyProgressBar.initData``). TODO(inventado): o catálogo, os níveis, o sinal e a entrega só no acerto (sem
captura de compra coletiva).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import bag
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import group_draw
from . import minijogo as mj
from .shop import (
    S_ITEMS,
    Charge,
    alert,
    count_buy,
    offer_goods,
    offer_key,
    place,
    purchase,
    save_with_mail,
    send_charge,
    today_count,
)

S_STATE, S_CHECK = 4559, 4560
KEY, SOLD = "group_buy", "group_buy_sold"
BUY, SETTLE, INFO = 1, 2, 3


def current(s: GameSession, now: datetime) -> dict[str, Any] | None:
    """A oferta da edição vigente, com as datas (``beginDate``/``endDate``/``sendDate``) e ``type`` 3."""
    c = mj.cfg(s, KEY)
    ed = mj.edition(c, now)
    if ed is None or not c.get("offers"):
        return None
    n = int((ed[0] - mj.at(c, "begin")).total_seconds() // (int(c["cycleDays"]) * 86400))
    offer = dict(c["offers"][n % len(c["offers"])])
    end = ed[0] + timedelta(hours=int(c["buyHours"]))
    return {
        **offer,
        "type": 3,
        "beginDate": mj.fmt(ed[0]),
        "endDate": mj.fmt(end),
        "sendDate": mj.fmt(ed[1]),
        "maxCurrentDate": mj.fmt(ed[0]),
        "frontMoney": int(offer.get("frontMoney") or offer["price"]),
    }


def unit_price(offer: dict[str, Any], sold: int) -> int:
    """Preço por unidade com ``sold`` compradores no servidor (``GroupBuyProgressBar``)."""
    p = int(offer["price"])
    for n in (1, 2, 3):
        if sold >= int(offer[f"level{n}"]):
            p = int(offer[f"price{n}"])
    return p


async def sold(s: GameSession, offer: dict[str, Any]) -> tuple[dict[str, Any], int]:
    data = await mj.shared(s, SOLD)
    if data.get("edition") != offer["beginDate"] or data.get("id") != offer["id"]:
        data = {"rev": data.get("rev", 0), "edition": offer["beginDate"], "id": offer["id"], "sold": 0}
    return data, int(data["sold"])


def mine(snap: PlayerSnapshot, offer: dict[str, Any]) -> dict[str, Any]:
    st = mj.load(snap, KEY)
    if st.get("edition") != offer["beginDate"] or st.get("id") != offer["id"]:
        st = {"edition": offer["beginDate"], "id": offer["id"], "buy": 0, "paid": 0, "settled": False}
    return st


def state_msg(offer: dict[str, Any], st: dict[str, Any], n: int, today: int) -> pb.GrouponShopMsg:
    return pb.GrouponShopMsg(
        goodId=int(offer["id"]),
        buyCount=st["buy"],
        totalPoint=st["paid"],
        curPrice=unit_price(offer, n),
        curCount=n,
        count=today,
        isReward=st["settled"],
        frontMoney=offer["frontMoney"],
    )


@router.on(8645)
async def groupon(s: GameSession, msg: pb.ShopMsg) -> None:
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    offer = current(s, now)
    if offer is None or msg.buyInfo.goodId != int(offer["id"]):
        s.log.info("8645 recusado: oferta fora da edição", pedido=str(msg))
        return
    async with mj.lock(s, SOLD):
        shared, n = await sold(s, offer)
        st = mine(snap, offer)
        key = offer_key(int(offer["id"]))
        if msg.payType == BUY:
            await _buy(s, snap, offer, shared, st, now)
        elif msg.payType == SETTLE:
            await _settle(s, snap, offer, st, n, now)
        elif msg.payType != INFO:
            s.log.info("8645 payType desconhecido", pedido=str(msg))
        _, n = await sold(s, offer)
        st = mine(snap, offer)
        s.send(S_STATE, b.complete(state_msg(offer, st, n, today_count(snap, key, now))))


async def _buy(
    s: GameSession,
    snap: PlayerSnapshot,
    offer: dict[str, Any],
    shared: dict[str, Any],
    st: dict[str, Any],
    now: datetime,
) -> None:
    key, front = offer_key(int(offer["id"])), int(offer["frontMoney"])
    if not mj.at(offer, "beginDate") <= now < mj.at(offer, "endDate"):
        return s.log.info("8645 compra fora da fase de compra")
    if int(offer["maxCount"]) != -1 and int(shared["sold"]) >= int(offer["maxCount"]):
        return alert(s, "The group buy is sold out.")  # TODO(inventado) texto (cliente: funny.groupbuy.error2)
    if int(offer["oneDayCount"]) != -1 and today_count(snap, key, now) >= int(offer["oneDayCount"]):
        return alert(s, "Daily purchase limit reached.")  # TODO(inventado) texto (cliente: funny.groupbuy.error1)
    ledger = cash.pay(snap.character, front, 1, "shop", f"groupon:{offer['id']}", now, gift_ok=False)
    if ledger is None:
        return alert(s, "Insufficient Balens")
    st = {**st, "buy": st["buy"] + 1, "paid": st["paid"] + front}
    shared = mj.store_shared(snap, SOLD, {**shared, "sold": int(shared["sold"]) + 1}, now)
    rec = count_buy(snap, key, 1, now)
    bought = purchase(snap, "groupon", int(offer["id"]), int(offer["templateId"]), 1, "Point", front, now)
    chance = group_draw.add_chance(snap, now)
    await save_with_mail(s, [], snap.character, ledger, rec, bought, mj.store(snap, KEY, st, now), shared, chance)
    send_charge(s, Charge(ledger=ledger))


async def _settle(
    s: GameSession, snap: PlayerSnapshot, offer: dict[str, Any], st: dict[str, Any], n: int, now: datetime
) -> None:
    if not mj.at(offer, "endDate") <= now < mj.at(offer, "sendDate") or st["settled"] or st["buy"] <= 0:
        return s.log.info("8645 acerto recusado", estado=str(st))
    final = st["buy"] * unit_price(offer, n)
    diff = final - st["paid"]  # > 0 cobra, < 0 devolve
    ref = f"groupon:{offer['id']} acerto"
    if diff > 0:
        ledger = cash.pay(snap.character, diff, 1, "shop", ref, now, gift_ok=False)
        if ledger is None:
            return alert(s, "Insufficient Balens")
    else:
        ledger = cash.change(snap.character, -diff, 0, "groupon", ref, now)
    st = {**st, "paid": final, "settled": True}
    goods = [(tid, count * st["buy"]) for _, tid, count in offer_goods(offer)]
    got, letters = place(s, snap, s.player_id, goods, now)
    await save_with_mail(s, letters, snap.character, ledger, *got, mj.store(snap, KEY, st, now))
    send_charge(s, Charge(ledger=ledger))
    if got:
        s.send(S_ITEMS, bag.moved(got, s.player_id))
    s.send(S_CHECK, b.complete(pb.GrouponShopMsg(buyCount=st["buy"], totalPoint=final, param1=max(0, -diff))))
