"""Lojas: compra (5154/8592), poção rápida (5633), limites do dia (8218/8693), loja misteriosa
(8482/8483), ofertas (8632/8645) e títulos (8597). Ver ``docs/itens.md``.

Preço e moeda seguem ``ShopGoodsInfo.setPrice`` do cliente: a primeira coluna > 0 entre Point,
GiftToken, Gold, Honor, ConsortiaOffer e MazeCoin. Honor e MazeCoin são itens na mochila
(208001 Insignia, 208009 Crypt Tokens). Toda compra com diamante grava o ``cash_ledger``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from google.protobuf.message import Message

from ...domain import gameday
from ...domain.models import CashLedger, Item, MysteryShop, PlayerSnapshot, Purchase, ShopBuy
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from ...templates.repository import Row
from .. import bag, rules
from ..builders import login as b
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .guild import shop_buy as guild_shop_buy
from .player import _army, _player
from .tower import MAZE_MAX_INDEX

S_ITEMS, S_ALERT, S_CHAT, S_HERO = 115, 111, 83, 113
S_SHOP_BUY, S_HAS_BUY, S_FASHION_BUY, S_BLOOD = 90, 4145, 4486, 170
S_FLASH_FRESH, S_BUY_COUNT, S_MYSTERY_BUY, S_MYSTERY_LIST, S_APPELLS = 4547, 4599, 4383, 4384, 4484
S_OFFERS, S_OFFER = 4238, 4375
OFFERS_PER_MSG = 50  # o oficial parte em 50 + 3 com o mesmo flag (oficial_encantar #57-#58); o cliente junta

# BuyInfo.result (ShopManager.shopingResult)
OK, NO_PLAYER, NO_ITEM, NO_MONEY, LIMIT, VIP, GONE, GUILD, LEVEL, FAIL = 1, 2, 3, 4, 6, 7, 8, 9, 10, 11
CURRENCY_ITEMS = {"Honor": 208001, "MazeCoin": 208009}  # BuyFrameI.PayMoney
PRICE_COLUMNS = ("Point", "GiftToken", "Gold", "Honor", "ConsortiaOffer", "MazeCoin")
MYSTERY, BLOOD, MAIN_OFFER = "5", "100", "99"  # ShopType: misteriosa, poção de HP, itens das ofertas da home
MAZE = "4"  # ShopType: loja do labirinto, preço em Crypt Tokens (208009, MazeCoin)
MYSTERY_FRESH = timedelta(seconds=14400)  # cliente: MysteryShopModel.remainTime = 14400 - (agora - freshLastdate)
MYSTERY_GOODS = 6  # MysteryShopModel.MAX_GOODS_NUM; o MysteryShopFrame cria 6 BuyGoodsItem
MYSTERY_GRADE = 26  # MysteryShopView: "Unlocks at Lvl. 26."
MAX_COUNT = 999


def price(row: Row) -> tuple[str, int] | None:
    """(coluna, preço unitário) como ``ShopGoodsInfo.setPrice``; None = moeda que não existe aqui."""
    # pontuações de outros sistemas (Score); 7 = troca por pontos da misteriosa (MysteryShopFrame página 2): a linha
    # pode ter GiftToken, mas o Score também é cobrado, e quanto se ganha de ponto por compra não tem fonte
    if row.get("ShopType") in ("7", "8", "15", "13", "20"):
        return None
    return next(((k, int(row[k])) for k in PRICE_COLUMNS if int(row.get(k) or 0) > 0), None)


@dataclass
class Charge:
    """O que uma compra mudou, para gravar e mandar depois."""

    ledger: CashLedger | None = None
    gold: bool = False
    changed: list[Item] = field(default_factory=list)
    gone: list[Item] = field(default_factory=list)


def binds(column: str) -> bool:
    """O item comprado nasce vinculado? Só o pago em Balens (coluna ``Point``, que o ``charge`` cobra sem vinculado)
    sai livre: as lojas das outras moedas são vinculadas (``warlords.WarlordsShopFrame.helpContent`` "All items
    obtained from the Glory Shop are bound", ``View.subshop.MineralShopFrame.describe`` da ametista)."""
    return column != "Point"


def charge(snap: PlayerSnapshot, column: str, total: int, pay_type: int, ref: str, now: datetime) -> Charge | None:
    """Debita ``total`` na moeda da coluna; None (nada muda) se faltar."""
    c = snap.character
    if column in ("Point", "GiftToken"):
        ledger = cash.pay(c, total, pay_type, "shop", ref, now, gift_ok=column == "GiftToken")
        return Charge(ledger=ledger) if ledger is not None else None
    if column == "Gold":
        if c.gold < total:
            return None
        c.gold -= total
        return Charge(gold=True)
    if column in CURRENCY_ITEMS:
        tid = CURRENCY_ITEMS[column]
        if bag.count_of(snap, tid) < total:
            return None
        changed, gone = bag.take(snap, tid, total)
        return Charge(changed=changed, gone=gone)
    return None  # ConsortiaOffer: o mercado da guilda paga pelo guild.shop_buy (5154)


def check(s: GameSession, row: Row | None, count: int) -> int:
    """Validações do ``BuyFrameI``/servidor antes de cobrar. Devolve OK ou o código de recusa."""
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    if (
        row is None
        or row.get("ShopType") == MAIN_OFFER
        or s.ctx.templates.get("ItemTempInfos", int(row["ItemId"])) is None
    ):
        return GONE
    if not 1 <= count <= MAX_COUNT or price(row) is None:
        return NO_ITEM
    if int(row.get("NeedMinVip") or 0) > 0:  # ponytail: nenhuma loja tem NeedMinVip hoje; regra não conferida
        return VIP
    maze = row.get("ShopType") == MAZE
    if maze and (int(row.get("MazeLayers") or 0) > MAZE_MAX_INDEX or int(row.get("MazeLayers2") or 0) > 0):
        # ponytail: o cliente esconde o botão se o andar passa do maxIndex (GoodsItem.as:380; o 4205 manda 0)
        # ou se é do segundo labirinto (towerInfo2 nunca chega). Progresso real do labirinto não existe. Código: dedução
        return FAIL
    if int(row.get("NeedConsortiaLevels") or 0) > 0:  # depende da guilda
        return GUILD
    low, high = int(row.get("NeedGrades") or 0), int(row.get("NeedMaxGrade") or 0)
    if c.grades < max(low, int(row.get("NeedMinGrade") or 0)) or (high and c.grades > high):
        return LEVEL
    if c.geste < int(row.get("NeedGeste") or 0):
        return FAIL
    limit = int(row.get("VIP0Count") or -1)
    if limit != -1 and today_count(snap, int(row["Id"]), s.ctx.clock.now()) + count > limit:
        return LIMIT
    now, column = s.ctx.clock.now(), price(row)[0]  # type: ignore[index]
    if not bag.fits(snap, s.ctx.templates, [(int(row["ItemId"]), count)], now, valid_minutes(row), binds(column)):
        return FAIL  # o oficial manda pelo correio (12); aqui não há correio
    return OK


def valid_minutes(row: Row) -> int:
    """``ShopTempInfos.ValidDate``: validade do item comprado, em minutos (as medalhas da loja de honra: 10080,
    21600, 43200 = 7, 15, 30 dias). *(cliente)* ``NumBuyFrame`` põe o valor direto no ``GoodsInfo.validDate``."""
    return int(row.get("ValidDate") or 0)


def day(now: datetime) -> str:
    return gameday.today(now)


def today_count(snap: PlayerSnapshot, good_id: int, now: datetime) -> int:
    rec = next((r for r in snap.shop_buys if r.good_id == good_id), None)
    return rec.counts if rec is not None and rec.day == day(now) else 0


def count_buy(snap: PlayerSnapshot, good_id: int, count: int, now: datetime) -> ShopBuy:
    rec = next((r for r in snap.shop_buys if r.good_id == good_id), None)
    if rec is None:
        rec = ShopBuy(snap.character.id or 0, good_id, day(now))
        snap.shop_buys.append(rec)
    if rec.day != day(now):
        rec.day, rec.counts = day(now), 0
    rec.counts += count
    return rec


def purchase(
    snap: PlayerSnapshot,
    source: str,
    good_id: int,
    template_id: int,
    count: int,
    currency: str,
    total: int,
    now: datetime,
) -> Purchase:
    """A linha de ``purchases`` da compra (gravada com o resto, na mesma transação)."""
    return Purchase(snap.character.id or 0, source, good_id, template_id, count, currency, total, now)


def send_charge(s: GameSession, paid: Charge) -> None:
    if paid.ledger is not None:
        _player(s)
    if paid.gold:
        castle_yield(s)
    if paid.changed or paid.gone:
        send(s, S_ITEMS, bag.moved(paid.changed, s.player_id, empty=paid.gone))


def send(s: GameSession, code: int, msg: Message) -> None:
    """Manda completando os campos (strings ausentes viram null no AS3). O 115 vai como está: o
    oficial omite attack/defence/... do item e o cliente usaria o 0 no lugar do template."""
    s.send(code, msg if isinstance(msg, pb.ItemMovedListMsg) else b.complete(msg))


def alert(s: GameSession, text: str) -> None:
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


async def buy(s: GameSession, info: pb.BuyInfo, pay_type: int) -> int:
    """Uma compra de loja comum: valida, cobra, põe na mochila e grava numa transação."""
    snap = s.snapshot
    assert snap is not None
    now, templates = s.ctx.clock.now(), s.ctx.templates
    if info.isDiscount:
        return await buy_offer(s, info, pay_type)
    if info.receiveId not in (0, s.player_id):  # ponytail: presente depende do correio
        return NO_PLAYER
    row = templates.get("ShopTempInfos", info.goodId, key="Id")
    if row is not None and row.get("ShopType") == MYSTERY:  # só pelo 8482
        row = None
    if (code := check(s, row, info.count)) != OK:
        return code
    assert row is not None
    column, unit = price(row)  # type: ignore[misc]
    paid = charge(snap, column, unit * info.count, pay_type, f"good:{info.goodId} x{info.count}", now)
    if paid is None:
        return NO_MONEY
    tid = int(row["ItemId"])
    got = bag.add(snap, templates, tid, info.count, now, valid_minutes(row), binds(column))
    rec = count_buy(snap, info.goodId, info.count, now)
    extra = [paid.ledger] if paid.ledger else []
    bought = purchase(snap, "shop", info.goodId, tid, info.count, column, unit * info.count, now)
    await s.ctx.characters.save(snap.character, *paid.changed, *got, rec, *extra, bought, delete=tuple(paid.gone))

    send_charge(s, paid)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    # texto deduzido (sem fonte no cliente/captura)
    alert(s, f"{bag.name(templates, tid)} x{info.count} purchased successfully!")
    return OK


# ---------------------------------------------------------------- ofertas por tempo (4238; Timed Sales do Hot Events)


def _offer_time(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=gameday.GAME_TZ)


def offers(s: GameSession) -> list[dict[str, Any]]:
    """Ofertas de ``game_settings.shop_offers`` (0053) que ainda não acabaram. As futuras vão junto, como no oficial
    (#57 traz ofertas que começam no dia 29); o cliente só mostra as que já começaram (``remainTime``)."""
    now = s.ctx.clock.now()
    cfg = s.ctx.world.settings.get("shop_offers") or {}
    return [o for o in cfg.get("offers", []) if _offer_time(str(o["endDate"])) >= now]


def offer_goods(offer: dict[str, Any]) -> list[tuple[int, int, int]]:
    """(shopId, templateId, quantidade) de uma unidade: o item principal e os do pacote (``shopId1..8``)."""
    goods = [(int(offer["shopId"]), int(offer["templateId"]), int(offer.get("counts", 0)))]
    goods += [
        (int(offer[f"shopId{n}"]), int(offer[f"templateId{n}"]), int(offer[f"count{n}"]))
        for n in range(1, 9)
        if int(offer.get(f"shopId{n}", 0))
    ]
    return goods


def offer_key(offer_id: int) -> int:
    """Chave em ``shop_buys``: negativa, para não misturar com ``ShopTempInfos.Id`` (o cliente separa pelo
    ``isDiscount``)."""
    return -offer_id


async def _sold(s: GameSession) -> dict[int, int]:
    snap = s.snapshot
    assert snap is not None
    server = snap.character.server_id
    return await s.ctx.characters.read(lambda uow: uow.characters.offers_sold(server))


async def send_offers(s: GameSession) -> None:
    """4238 no login (8224 ``user``; o oficial manda dois pares, #57-#58 e #84-#85, e o cliente refaz a lista igual).
    Mesmo ``flag`` em todas as partes: ``ShopManager.__shopHandler`` (cliente inglês) junta as partes de flag igual e
    recomeça a lista quando ele muda. ``currentCount`` = vendidos neste servidor (o do oficial é o dele)."""
    cfg = s.ctx.world.settings.get("shop_offers") or {}
    live, sold = offers(s), await _sold(s)
    for i in range(0, max(len(live), 1), OFFERS_PER_MSG):
        msg = pb.ShopMainRspMsg(flag=int(cfg.get("flag", 0)))
        for o in live[i : i + OFFERS_PER_MSG]:
            msg.discountInfo.add(**o, currentCount=sold.get(int(o["id"]), 0))
        send(s, S_OFFERS, msg)


async def buy_offer(s: GameSession, info: pb.BuyInfo, pay_type: int) -> int:
    """Compra de oferta (5154 ``isDiscount``, ``goodId`` = id da oferta): preço ``price`` em Balens por unidade
    (``MainShopInfo.price``: o ``price`` da oferta vale quando > 0; todas as do 0053 têm), dentro da janela,
    até ``oneDayCount`` por dia (``MainShopInfo.canOneCount``). Itens saem livres, como na loja em Balens."""
    snap = s.snapshot
    assert snap is not None
    now, templates = s.ctx.clock.now(), s.ctx.templates
    offer = next((o for o in offers(s) if o["id"] == info.goodId), None)
    if offer is None or not _offer_time(str(offer["beginDate"])) <= now or int(offer.get("price", 0)) <= 0:
        return GONE
    if not 1 <= info.count <= MAX_COUNT or info.receiveId not in (0, s.player_id):
        return NO_ITEM
    if int(offer.get("vip", 0)) > 0:
        from .vip import is_vip, vip_grade  # vip -> player -> ... -> shop

        if not is_vip(snap, now) or vip_grade(s, snap) < int(offer["vip"]):
            return VIP
    one_day = int(offer.get("oneDayCount", -1))
    if one_day != -1 and today_count(snap, offer_key(info.goodId), now) + info.count > one_day:
        return LIMIT
    sold = (await _sold(s)).get(info.goodId, 0)
    if int(offer.get("maxCount", -1)) != -1 and sold + info.count > int(offer["maxCount"]):
        return LIMIT  # MainShopInfo.canTotalCount; todas as do 0053 têm -1
    goods = [(tid, n * info.count) for _, tid, n in offer_goods(offer)]
    if not bag.fits(snap, templates, goods, now, binds=False):
        return FAIL
    total = int(offer["price"]) * info.count
    paid = charge(snap, "Point", total, pay_type, f"offer:{info.goodId} x{info.count}", now)
    if paid is None:
        return NO_MONEY
    got: list[Item] = []
    for shop_id, tid, n in offer_goods(offer):
        row = templates.get("ShopTempInfos", shop_id, key="Id")
        got += bag.add(snap, templates, tid, n * info.count, now, valid_minutes(row) if row else 0, False)
    rec = count_buy(snap, offer_key(info.goodId), info.count, now)
    tid = int(offer["templateId"])
    bought = purchase(snap, "offer", info.goodId, tid, info.count, "Point", total, now)
    extra = [paid.ledger] if paid.ledger else []
    await s.ctx.characters.save(snap.character, *got, rec, *extra, bought)

    send_charge(s, paid)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    alert(s, f"{offer['names']} x{info.count} purchased successfully!")  # mesmo texto deduzido da loja comum
    # 4375 para todos: a oferta inteira com o currentCount novo (oficial_encantar #2640-#2666, compras de outros)
    s.ctx.online.broadcast(S_OFFER, b.complete(pb.MainDiscountInfo(**offer, currentCount=sold + info.count)))
    return OK


def _shop_msg(msg: object) -> pb.ShopMsg:
    # o registro decodifica o 5154 como FashionShopMsg (o primeiro tipo do opcode); o campo 1 é o
    # mesmo BuyInfo e o resto viaja como campo desconhecido: reler como ShopMsg recupera o payType
    assert isinstance(msg, pb.FashionShopMsg | pb.ShopMsg)
    return pb.ShopMsg.FromString(msg.SerializeToString())


@router.on(5154)
async def shop_buy(s: GameSession, msg: pb.FashionShopMsg) -> None:
    req = _shop_msg(msg)
    if await guild_shop_buy(s, req.buyInfo):  # ShopType 2: mercado da guilda, paga com contribuição
        return
    result = await buy(s, req.buyInfo, req.payType)
    if result != OK:
        s.log.info("5154 recusado", pedido=str(req), resultado=result)
    out = pb.ShopMsg()
    out.buyInfo.CopyFrom(req.buyInfo)
    out.buyInfo.result = result
    send(s, S_SHOP_BUY, out)


@router.on(8592)
async def fashion_shop_buy(s: GameSession, msg: pb.FashionShopMsg) -> None:
    """Compra de moda (uma ou várias, ``FashionAllBuyFrame``): 90 por item e 4486 no fim."""
    ok = True
    for info in msg.buyInfos[:20]:
        result = await buy(s, info, msg.payType)
        ok = ok and result == OK
        out = pb.ShopMsg()
        out.buyInfo.CopyFrom(info)
        out.buyInfo.result = result
        send(s, S_SHOP_BUY, out)
    send(s, S_FASHION_BUY, pb.FashionShopMsg(result=ok))


@router.on(8218)
async def shop_has_buy(s: GameSession, _: object) -> None:
    """Compras de hoje contra os limites diários (4145 ``hasDataInfo``)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    out = pb.ShopMsg()
    for rec in snap.shop_buys:
        if rec.day == day(now) and rec.counts:
            info = out.hasDataInfo.add(userId=s.player_id, itemId=abs(rec.good_id), counts=rec.counts)
            info.buyDate, info.isDiscount = b.fmt_time(now), rec.good_id < 0  # offer_key
    send(s, S_HAS_BUY, out)


@router.on(8693)
async def buy_discount_count(s: GameSession, msg: pb.ShopMsg) -> None:
    """Quantos daquele item já comprei hoje (4599); o cliente abre a janela de compra com isso."""
    snap = s.snapshot
    assert snap is not None
    out = pb.ShopMsg()
    out.buyInfo.CopyFrom(msg.buyInfo)
    good = offer_key(msg.buyInfo.goodId) if msg.buyInfo.isDiscount else msg.buyInfo.goodId
    out.buyInfo.count = today_count(snap, good, s.ctx.clock.now())
    send(s, S_BUY_COUNT, out)


@router.on(8632)
async def flash_sale_fresh(s: GameSession, _: object) -> None:
    """Rodízio das ofertas (``type`` 2 do 4238; ``ShopManager.__refreshTimeBuyHandler``): o 0053 só tem ``type`` 1,
    então a lista vai vazia (o oficial também manda só o ``refreshDate``, #1633)."""
    send(s, S_FLASH_FRESH, pb.ShopMsg(refreshDate=b.fmt_time(s.ctx.clock.now())))


@router.on(8645)
async def groupon(s: GameSession, msg: pb.ShopMsg) -> None:
    # compra coletiva só existe com uma oferta type 3 do 4238 (evento do operador): não há nenhuma,
    # então o cliente nem abre a tela; um pedido assim é recusado sem resposta
    s.log.info("8645 recusado: nenhuma compra coletiva ativa", pedido=str(msg))


@router.on(5633)
async def fast_use_blood(s: GameSession, msg: pb.ShopMsg) -> None:
    """Compra e usa na hora uma poção de HP (ShopType 100): a reserva ``blood`` do herói sobe."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    now, templates = s.ctx.clock.now(), s.ctx.templates
    info = msg.buyInfo
    row = templates.get("ShopTempInfos", info.goodId, key="Id")
    tpl = templates.get("ItemTempInfos", int(row["ItemId"])) if row is not None else None
    result, paid = OK, None
    if row is None or row.get("ShopType") != BLOOD or tpl is None or not 1 <= info.count <= MAX_COUNT:
        result = GONE
    elif (p := price(row)) is None or (
        paid := charge(snap, p[0], p[1] * info.count, msg.payType, f"blood:{info.goodId}", now)
    ) is None:
        result = NO_MONEY
    if result != OK or paid is None or tpl is None:
        s.log.info("5633 recusado", pedido=str(msg), resultado=result)
        send(s, S_BLOOD, pb.FastUseBloodMsg(result=result, templateId=info.goodId))
        return
    leader = snap.leader
    leader.blood += int(tpl.get("Property1") or 0) * info.count
    leader.blood_id = int(tpl["TemplateId"])
    extra = [paid.ledger] if paid.ledger else []
    cost = price(row) if row is not None else None
    assert cost is not None  # cobrado acima: tem preço
    record = purchase(snap, "blood", info.goodId, leader.blood_id, info.count, cost[0], cost[1] * info.count, now)
    await s.ctx.characters.save(snap.character, leader, *paid.changed, *extra, record, delete=tuple(paid.gone))

    send_charge(s, paid)
    send_blood(s)
    send(s, S_BLOOD, pb.FastUseBloodMsg(result=OK, templateId=leader.blood_id))


def send_blood(s: GameSession) -> None:
    """113 só com a reserva de HP (como o oficial depois de usar a poção)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    hp = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now()).live
    send(
        s,
        S_HERO,
        pb.SimpleHeroInfoMsg(heroId=snap.leader.id or 0, hp=hp, blood=snap.leader.blood, bloodId=snap.leader.blood_id),
    )


# --- loja misteriosa (ShopType 5) ---


def _config(s: GameSession, name: str, default: int, hint: str = "") -> int:
    rows = [r for r in s.ctx.templates.find("ConfigInfos", ConfigName=name) if hint in r.get("Description", "")]
    return int(rows[0]["ConfigValue"]) if rows else default


def _roll(s: GameSession, snap: PlayerSnapshot) -> list[int]:
    """Sorteia os itens pelo peso ``Rands`` entre os do nível do jogador (``NeedMaxGrade``)."""
    g = snap.character.grades
    pool = [
        r
        for r in s.ctx.templates.find("ShopTempInfos", ShopType=MYSTERY)
        if int(r.get("Rands") or 0) > 0
        and int(r.get("NeedGrades") or 0) <= g
        and (int(r.get("NeedMaxGrade") or 0) in (0,) or g <= int(r["NeedMaxGrade"]))
    ]
    goods: list[int] = []
    while pool and len(goods) < MYSTERY_GOODS:
        pick = random.choices(pool, weights=[int(r["Rands"]) for r in pool])[0]
        pool.remove(pick)
        goods.append(int(pick["Id"]))
    return goods


def _mystery(s: GameSession) -> MysteryShop:
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    if not snap.mystery:
        snap.mystery.append(MysteryShop(snap.character.id or 0, now, ",".join(map(str, _roll(s, snap))), day=day(now)))
    shop = snap.mystery[0]
    if shop.day != day(now):  # as compras do dia (ShopBuy_MaxCount) zeram na virada das 5h
        shop.day, shop.buy_count = day(now), 0
    if now - shop.fresh_at >= MYSTERY_FRESH:  # os itens trocam 4 h depois do último refresh
        shop.goods, shop.bought, shop.fresh_at = ",".join(map(str, _roll(s, snap))), "", now
    return shop


def _ints(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x]


def _mystery_list(s: GameSession, shop: MysteryShop) -> pb.ShopFreshRspMsg:
    goods, bought = _ints(shop.goods), set(_ints(shop.bought))
    out = pb.ShopFreshRspMsg(freshLastdate=b.fmt_time(shop.fresh_at), buyCount=shop.buy_count)
    out.maxBuyCount = _config(s, "ShopBuy_MaxCount", 20, "神秘")
    out.itemId.extend(goods)
    out.isCanBuy.extend(1 if i in bought else 0 for i in range(len(goods)))  # BuyGoodsItem: 0 = à venda, 1 = comprado
    return out


@router.on(8483)
async def mystery_fresh(s: GameSession, msg: pb.ShopFreshReqMsg) -> None:
    """Lista da loja misteriosa (4384); ``isButton`` = atualizar pagando ``ShopFresh_NeedDiamond``."""
    snap = s.snapshot
    assert snap is not None
    if snap.character.grades < MYSTERY_GRADE:
        s.log.info("8483 recusado: nível", nivel=snap.character.grades)
        return
    now = s.ctx.clock.now()
    shop = _mystery(s)
    extra: list[object] = []
    if msg.isButton:
        ledger = cash.pay(
            snap.character, _config(s, "ShopFresh_NeedDiamond", 10), msg.payType, "shop", "mystery:fresh", now
        )
        if ledger is None:
            s.log.info("8483 recusado: sem diamante")
            send(s, S_MYSTERY_LIST, _mystery_list(s, shop))
            return
        shop.goods, shop.bought, shop.fresh_at = ",".join(map(str, _roll(s, snap))), "", now
        extra = [snap.character, ledger]
    await s.ctx.characters.save(shop, *extra)
    if msg.isButton:
        _player(s)
    send(s, S_MYSTERY_LIST, _mystery_list(s, shop))


@router.on(8482)
async def mystery_buy(s: GameSession, msg: pb.ShopItemBuyMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    now, templates = s.ctx.clock.now(), s.ctx.templates
    shop = _mystery(s)
    goods, bought = _ints(shop.goods), _ints(shop.bought)
    row = templates.get("ShopTempInfos", msg.itemId, key="Id")
    valid = 0 <= msg.index < len(goods) and goods[msg.index] == msg.itemId and msg.index not in bought
    result, paid = OK, None
    if snap.character.grades < MYSTERY_GRADE:
        result = LEVEL
    elif not valid or row is None or (p := price(row)) is None:
        result = GONE
    elif shop.buy_count >= _config(s, "ShopBuy_MaxCount", 20, "神秘"):
        result = LIMIT
    elif not bag.fits(snap, templates, [(int(row["ItemId"]), 1)], now, binds=binds(p[0])):
        result = FAIL
    elif (paid := charge(snap, p[0], p[1], msg.payType, f"mystery:{msg.itemId}", now)) is None:
        result = NO_MONEY
    if result != OK or paid is None:
        s.log.info("8482 recusado", pedido=str(msg), resultado=result)
        send(s, S_MYSTERY_BUY, pb.ShopItemBuyRspMsg(result=result, buyCount=shop.buy_count, score=0))
        return
    assert row is not None
    cost = price(row)
    assert cost is not None  # cobrado acima: tem preço
    tid = int(row["ItemId"])
    got = bag.add(snap, templates, tid, 1, now, binds=binds(cost[0]))
    shop.bought = ",".join(map(str, [*bought, msg.index]))
    shop.buy_count += 1
    extra = [paid.ledger] if paid.ledger else []
    record = purchase(snap, "mystery", msg.itemId, tid, 1, cost[0], cost[1], now)
    await s.ctx.characters.save(snap.character, shop, *paid.changed, *got, *extra, record, delete=tuple(paid.gone))

    send_charge(s, paid)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    # texto deduzido (sem fonte no cliente/captura)
    alert(s, f"{bag.name(templates, tid)} x1 purchased successfully!")
    send(s, S_MYSTERY_BUY, pb.ShopItemBuyRspMsg(result=OK, buyCount=shop.buy_count, score=0))
    send(s, S_MYSTERY_LIST, _mystery_list(s, shop))


# --- títulos ---


@router.on(8597)
async def appell_exchange(s: GameSession, msg: pb.AppellExchangeMsg) -> None:
    """``look``: lista de títulos (4484). Trocar o título exige tê-lo ganho, e quem dá títulos são as
    conquistas (``AppellInfos.CondtionType``), que não existem aqui: a lista vai vazia e a troca é recusada."""
    snap = s.snapshot
    assert snap is not None
    if msg.look:
        send(s, S_APPELLS, pb.AppellsMsg())
        return
    if msg.appellId == 0 and snap.character.appell_id:
        snap.character.appell_id = 0
        await s.ctx.characters.save(snap.character)
        _player(s)
        _army(s)
        return
    s.log.info("8597 recusado: título não obtido", titulo=msg.appellId)
