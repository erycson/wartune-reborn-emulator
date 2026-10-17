"""Mercado entre jogadores: anunciar (8448), listas (8449 meus anúncios, 8450 mercado, 8452 meus lances,
8457 busca), lance (8451), compra pelo preço fixo (8453) e cancelar (8454). Regras e fontes em
``docs/mercado.md``; encerramento dos anúncios vencidos em ``game/mall.py``.

Cada pedido roda numa transação só (``characters.write``): a varredura dos vencidos, a operação e os
correios. Quem pede recebe direto na mochila; quem não pede (vendedor, vencedor, lance devolvido) recebe
pelo correio, porque o snapshot dele pode não estar carregado aqui.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from google.protobuf.message import Message

from ...domain.models import BagType, Character, Item, Mail, MallBid, MallListing, PlayerSnapshot
from ...domain.repositories import UnitOfWork
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates
from .. import bag
from .. import mail as mailbox
from .. import mall as market
from ..builders import login as b
from ..builders.player import item_info, item_moved
from ..router import router
from ..session import GameSession
from .items import _copy
from .player import _player

S_ITEMS = 115  # ItemMovedListMsg (a bolsa muda)
S_SOLD, S_LIST_SELL, S_LIST_MARKET, S_BID = 4352, 4353, 4354, 4355
S_LIST_BIDS, S_FIX, S_CANCEL, S_SEARCH = 4356, 4357, 4358, 4359

# SellResultType do cliente (``Auction.ResultAlert`` = abs(código))
OK, GONE, COUNT, PRICE, FIX_PRICE, HOUR = 0, -2, -3, -4, -5, -6
BLOCKED, NO_ITEM, NO_POINT, NOT_AUCTION, FIX_FAIL, CANCEL_FAIL, OWN_FIX, OWN_BID = -7, -8, -11, -12, -14, -15, -16, -17
SELL_MAX_COUNT = -18  # MALL_SELL_MAX_COUNT: mais de 9 unidades num anúncio
DAILY_LIMIT = -52  # Auction.ResultAlert52: "İhale günlük satın alma sınırına ulaştı!" (fora do SellResultType)
# -7 aqui é item travado (8809). O texto do cliente para -7 é "eşya bağlı halde" (vinculado): falta o dado de vínculo

GOODS, PET = 1, 2  # SellItemVO.itemType (e MallItemMsg.itemFrom): só item vai ao mercado
# ponytail: a tela oferece 8, 24 e 48 h (Auction.SubmitHour1..3); o valor enviado não está no decompilado
MIN_HOUR, MAX_HOUR = 1, 72
MAX_COUNT = 9  # (cliente) Auction.ResultAlert18: "o item vendido tem no máximo 9 unidades" (por anúncio)
# ponytail: a lista pede 9 por página (8449, 8452); o teto de 50 é dedução, a tela de leilão não está no decompilado
PAGE, PAGE_MAX = 9, 50
MIN_POINT = 2  # (cliente) Auction.SubmitAlert2: "İlk Fiyat 2'den az olamaz"

# (cliente) language.txt AuctionHelp.helpContent itens 9-11: limite diário de compra em diamante por nível,
# Lv40-60 500, Lv60-70 1000, Lv70-80 1500.
# ponytail: o texto repete 60 e 70 nas duas faixas; aqui 60 e 70 já são da faixa de cima. Abaixo de 40 vale
# a primeira faixa e acima de 80 a última (o texto não diz). Conta o diamante pago (lance e preço fixo), e o
# lance devolvido não volta para a cota (o texto não diz).
DAILY_LIMITS = ((60, 500), (70, 1000))
TOP_DAILY_LIMIT = 1500


def daily_limit(grades: int) -> int:
    return next((limit for below, limit in DAILY_LIMITS if grades < below), TOP_DAILY_LIMIT)


def _spent_today(c: Character, now: datetime) -> int:
    return c.mall_spent if c.mall_day == now.date().isoformat() else 0


def _over_limit(c: Character, cost: int, now: datetime) -> bool:
    return _spent_today(c, now) + cost > daily_limit(c.grades)


def _count_spent(c: Character, cost: int, now: datetime) -> None:
    c.mall_spent, c.mall_day = _spent_today(c, now) + cost, now.date().isoformat()


@dataclass
class Reply:
    """O que um pedido manda depois do commit: pacotes, diamante do personagem e cartas (148)."""

    out: list[tuple[int, Message]] = field(default_factory=list)
    player: bool = False
    mails: list[Mail] = field(default_factory=list)


async def _transact(s: GameSession, op: Callable[[UnitOfWork, datetime], Awaitable[Reply]]) -> None:
    """Uma transação: varredura dos vencidos, ``op`` (valida, muda o snapshot, grava) e os correios.
    Os pacotes saem só depois do commit."""
    snap = s.snapshot
    assert snap is not None
    server, templates, now = snap.character.server_id, s.ctx.templates, s.ctx.clock.now()

    async def change(uow: UnitOfWork) -> tuple[Reply, list[Mail]]:
        settled = await market.settle(uow, templates, server, now)
        return await op(uow, now), settled

    async with market.MALL_LOCK:
        reply, settled = await s.ctx.characters.write(change)
    for mail in [*settled, *reply.mails]:
        mailbox.notify(s.ctx.online, mail)
    for code, msg in reply.out:
        s.send(code, msg if isinstance(msg, pb.ItemMovedListMsg) else b.complete(msg))
    if reply.player:
        _player(s)


async def _pairs(uow: UnitOfWork, listings: list[MallListing]) -> list[tuple[MallListing, Item]]:
    items = {i.id: i for i in await uow.items.by_ids([x.item_id for x in listings])}
    return [(x, items[x.item_id]) for x in listings if x.item_id in items]


async def _market(uow: UnitOfWork, server: int, kind: int) -> list[tuple[MallListing, Item]]:
    """Anúncios abertos do servidor, do mais novo para o mais antigo. Mascote (PET) não tem leilão."""
    if kind == PET:
        return []
    rows = await _pairs(uow, await uow.mall.open_listings(server))
    rows.reverse()
    return rows


def _page[T](rows: list[T], page: int, count: int) -> tuple[int, int, list[T]]:
    size = min(max(count, 1), PAGE_MAX) if count > 0 else PAGE
    pages = max(1, -(-len(rows) // size))
    idx = max(page, 1)
    return idx, pages, rows[(idx - 1) * size : idx * size]


def _listing_msg(listing: MallListing, item: Item) -> pb.MallItemMsg:
    msg = pb.MallItemMsg(
        id=listing.id or 0,
        templateId=item.template_id,
        userId=listing.seller_id,
        nickName=listing.seller_nick,
        point=listing.point,
        fixPoint=listing.fix_point,
        hour=listing.hour,
        itemFrom=GOODS,
        startTime=b.fmt_time(listing.started_at),
        maxAuctionId=(listing.id or 0) if listing.bidder_id else 0,  # > 0 = já tem lance (``auctioned``)
    )
    msg.itemInfo.CopyFrom(_copy(item_info(item, listing.seller_id), pb.SimpleItemInfoMsg()))
    return msg


def _items_msg(rows: list[tuple[MallListing, Item]], page: int, count: int) -> pb.AuctionItemsMsg:
    idx, pages, part = _page(rows, page, count)
    out = pb.AuctionItemsMsg(pageIdx=idx, pageCount=pages)
    out.sellItem.extend(_listing_msg(listing, item) for listing, item in part)
    return out


def _bid_msg(bid: MallBid, listing: MallListing, item: Item) -> pb.MallItemBuyMsg:
    return pb.MallItemBuyMsg(
        id=bid.id or 0,
        userId=bid.bidder_id,
        mallItem=_listing_msg(listing, item),
        bidupPoint=bid.price,
        buyTime=b.fmt_time(bid.bid_at),
    )


def _bids_msg(rows: list[tuple[MallBid, MallListing, Item]], page: int, count: int) -> pb.AuctionItemsMsg:
    idx, pages, part = _page(rows, page, count)
    out = pb.AuctionItemsMsg(pageIdx=idx, pageCount=pages)
    out.itemBuy.extend(_bid_msg(bid, listing, item) for bid, listing, item in part)
    return out


def _matches(msg: pb.SearchItemReqMsg, item: Item, snap: PlayerSnapshot, templates: GameTemplates) -> bool:
    """Filtros do 8457 (``AuctionModel``: nível em faixas, qualidade = ``Profile``, classe 1-3 = guerreiro,
    caçador, mago). ``type``/``sonType`` batem com ``MasterType``/``SonType``; ``usable`` vale para equipamento."""
    row = templates.get("ItemTempInfos", item.template_id) or {}
    need = int(row.get("NeedGrades") or 0)
    jobs = {int(j) for j in (row.get("Job") or "0").split(",") if j}
    ok = not msg.itemName or msg.itemName.lower() in row.get("TemplateName", "").lower()
    ok = ok and (not msg.minLevel or need >= msg.minLevel) and (not msg.maxLevel or need <= msg.maxLevel)
    ok = ok and (not msg.quality or int(row.get("Profile") or 0) == msg.quality)
    ok = ok and (not msg.job or 0 in jobs or any((j - 1) % 3 + 1 == msg.job for j in jobs))
    ok = ok and (not msg.type or row.get("MasterType") == str(msg.type))
    ok = ok and (not msg.sonType or row.get("SonType") == str(msg.sonType))
    if msg.usable and row.get("MasterType") == "1" and snap.leader is not None:
        hero = templates.hero(snap.leader.template_id)
        ok = ok and bag.fits_hero(snap, row, hero.job, hero.sex)
    return ok


def _label(templates: GameTemplates, item: Item) -> str:
    return f"{bag.name(templates, item.template_id)} x{item.count}"


# --- anunciar (8448) ---


@router.on(8448)
async def sell(s: GameSession, msg: pb.SellItemReqMsg) -> None:
    """Põe um item da mochila à venda: ``point`` é o lance inicial (mínimo ``StartingPrice`` × quantidade),
    ``fixPoint`` 0 = sem compra imediata, ``hour`` a duração. O item sai da mochila na mesma transação
    que cria o anúncio: nunca existe nos dois lugares."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        item = bag.at(snap, BagType.BAG, 0, msg.itemPos)
        row = templates.get("ItemTempInfos", item.template_id) if item is not None else None
        code = OK
        if msg.sellType != GOODS:
            code = NOT_AUCTION
        elif item is None or row is None or item.id != msg.itemId:
            code = NO_ITEM
        elif int(row.get("StartingPrice") or 0) <= 0:  # 0 = o template não vai a leilão (cliente: -12)
            code = NOT_AUCTION
        elif item.is_locked:
            code = BLOCKED
        elif not 1 <= msg.count <= item.count:
            code = COUNT
        elif msg.count > MAX_COUNT:
            code = SELL_MAX_COUNT
        elif msg.point < max(MIN_POINT, int(row["StartingPrice"]) * msg.count):
            code = PRICE
        elif msg.fixPoint and msg.fixPoint <= msg.point:
            code = FIX_PRICE
        elif not MIN_HOUR <= msg.hour <= MAX_HOUR:
            code = HOUR
        if code != OK or item is None:
            s.log.info("8448 recusado", pedido=str(msg), resultado=code)
            return Reply([(S_SOLD, pb.SellItemRspMsg(result=code))])

        old_pos = item.pos
        if msg.count < item.count:  # parte de uma pilha: a mochila fica com o resto
            item.count -= msg.count
            listed = replace(item, id=None, count=msg.count, bag_type=BagType.AUCTION, object_id=0, pos=0)
            await uow.save(item)
            await uow.save(listed)
            await uow.flush()  # o anúncio precisa do id do item
            moved = bag.moved([item], s.player_id)
        else:
            snap.items.remove(item)
            listed = item
            listed.bag_type, listed.object_id, listed.pos = BagType.AUCTION, 0, 0
            await uow.save(listed)
            moved = item_moved(BagType.BAG, 0, old_pos, None, s.player_id)
        listing = MallListing(
            c.server_id,
            c.id or 0,
            listed.id or 0,
            c.nickname or "",
            msg.point,
            msg.fixPoint,
            msg.hour,
            now,
            now + timedelta(hours=msg.hour),
        )
        await uow.save(listing)
        await uow.flush()
        return Reply([(S_ITEMS, moved), (S_SOLD, pb.SellItemRspMsg(result=OK, item=_listing_msg(listing, listed)))])

    await _transact(s, op)


# --- listas (8449, 8450, 8452, 8457) ---


@router.on(8449)
async def my_listings(s: GameSession, msg: pb.MallItemViewReqMsg) -> None:
    """Meus anúncios abertos (4353, lista ``sellItem``)."""

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _pairs(uow, await uow.mall.by_seller(s.player_id))
        rows.reverse()
        return Reply([(S_LIST_SELL, _items_msg(rows, msg.page, msg.count))])

    await _transact(s, op)


@router.on(8450)
async def market_list(s: GameSession, msg: pb.MallItemViewReqMsg) -> None:
    """Anúncios de todos os jogadores do servidor (4354, a aba de compra)."""
    snap = s.snapshot
    assert snap is not None
    server = snap.character.server_id

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _market(uow, server, getattr(msg, "from"))
        return Reply([(S_LIST_MARKET, _items_msg(rows, msg.page, msg.count))])

    await _transact(s, op)


@router.on(8452)
async def my_bids(s: GameSession, msg: pb.MallItemViewReqMsg) -> None:
    """Meus lances em anúncios abertos (4356, lista ``itemBuy`` com o meu ``bidupPoint``)."""

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        bids = await uow.mall.bids_by(s.player_id)
        listings = [x for x in [await uow.mall.listing(bid.listing_id) for bid in bids] if x is not None]
        mine = {bid.listing_id: bid for bid in bids}
        rows = [(mine[x.id or 0], x, item) for x, item in await _pairs(uow, listings)]
        rows.reverse()
        return Reply([(S_LIST_BIDS, _bids_msg(rows, msg.page, msg.count))])

    await _transact(s, op)


@router.on(8457)
async def search(s: GameSession, msg: pb.SearchItemReqMsg) -> None:
    """Busca no mercado (4359). O 8457 não manda tamanho de página: usa ``PAGE``."""
    snap = s.snapshot
    assert snap is not None
    server, templates = snap.character.server_id, s.ctx.templates

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _market(uow, server, 0)
        hits = [(x, item) for x, item in rows if _matches(msg, item, snap, templates)]
        return Reply([(S_SEARCH, _items_msg(hits, msg.page, PAGE))])

    await _transact(s, op)


# --- lance (8451), preço fixo (8453), cancelar (8454) ---


@router.on(8451)
async def bid(s: GameSession, msg: pb.AuctionItemReqMsg) -> None:
    """Lance em ``id`` (anúncio) por ``point``. O primeiro lance é ≥ o inicial; os seguintes > o último.
    O diamante do lance sai agora (``ledger``); quem foi superado recebe o dele de volta pelo correio."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _pairs(uow, [x for x in [await uow.mall.listing(msg.id)] if x is not None])
        if not rows:
            return Reply([(S_BID, pb.AuctionItemRspMsg(result=GONE))])
        listing, item = rows[0]
        minimum = listing.point + 1 if listing.bidder_id else listing.point
        if listing.seller_id == s.player_id:
            code = OWN_BID
        elif msg.point < minimum or (listing.fix_point and msg.point >= listing.fix_point):
            code = PRICE
        else:
            code = OK
        if code != OK:
            return Reply([(S_BID, pb.AuctionItemRspMsg(result=code))])
        own = listing.bidder_id == s.player_id
        cost = msg.point - listing.point if own else msg.point  # quem já lidera paga só a diferença
        if _over_limit(c, cost, now):
            return Reply([(S_BID, pb.AuctionItemRspMsg(result=DAILY_LIMIT))])
        paid = ledger.pay(c, cost, bind=False, reason="mall", ref=f"mall:{listing.id} lance", now=now)
        if paid is None:
            return Reply([(S_BID, pb.AuctionItemRspMsg(result=NO_POINT))])
        _count_spent(c, cost, now)
        reply = Reply(player=True)
        if listing.bidder_id and not own:
            reply.mails.append(
                await market.post(
                    uow,
                    listing.bidder_id,
                    now,
                    "Teklif iadesi",
                    f"{_label(templates, item)}: teklifiniz geri döndü.",
                    goods=[(market.DIAMOND, listing.point)],
                )
            )
        listing.point, listing.bidder_id = msg.point, s.player_id
        rec = await uow.mall.bid(listing.id or 0, s.player_id)
        if rec is None:
            rec = MallBid(listing.id or 0, s.player_id, msg.point, now)
        else:
            rec.price, rec.bid_at = msg.point, now
        await uow.save(listing)
        await uow.save(rec)
        await uow.save(c)
        await uow.save(paid)
        await uow.flush()
        reply.out.append((S_BID, pb.AuctionItemRspMsg(result=OK, itemBuy=_bid_msg(rec, listing, item))))
        return reply

    await _transact(s, op)


@router.on(8453)
async def buy_now(s: GameSession, msg: pb.AuctionItemReqMsg) -> None:
    """Compra pelo preço fixo (``point`` tem que ser igual ao ``fixPoint`` do anúncio, senão o cliente
    recarrega a lista). Paga agora; o item vai ao comprador e o diamante (menos o imposto) ao vendedor, os dois
    pelo correio: (cliente) AuctionHelp.helpContent item 3, "a compra chega pela mensagem do sistema", e o 4357
    do cliente só tira a linha da lista."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _pairs(uow, [x for x in [await uow.mall.listing(msg.id)] if x is not None])
        if not rows:
            return Reply([(S_FIX, pb.FixAuctionItemRspMsg(result=GONE, mallItemId=msg.id))])
        listing, item = rows[0]
        own = listing.bidder_id == s.player_id
        cost = listing.fix_point - listing.point if own else listing.fix_point
        if listing.seller_id == s.player_id:
            code = OWN_FIX
        elif not listing.fix_point:
            code = FIX_FAIL
        elif msg.point != listing.fix_point:
            code = PRICE
        elif _over_limit(c, cost, now):
            code = DAILY_LIMIT
        else:
            code = OK
        if code != OK:
            return Reply([(S_FIX, pb.FixAuctionItemRspMsg(result=code, mallItemId=listing.id or 0))])
        paid = ledger.pay(c, cost, bind=False, reason="mall", ref=f"mall:{listing.id} compra", now=now)
        if paid is None:
            return Reply([(S_FIX, pb.FixAuctionItemRspMsg(result=NO_POINT, mallItemId=listing.id or 0))])
        _count_spent(c, cost, now)
        reply = Reply(player=True)
        if listing.bidder_id and not own:
            reply.mails.append(
                await market.post(
                    uow,
                    listing.bidder_id,
                    now,
                    "Teklif iadesi",
                    f"{_label(templates, item)}: teklifiniz geri döndü.",
                    goods=[(market.DIAMOND, listing.point)],
                )
            )
        reply.mails.append(
            await market.post(
                uow,
                listing.seller_id,
                now,
                "Satış geliri",
                f"{_label(templates, item)} satıldı.",
                goods=[(market.DIAMOND, market.income(listing.fix_point))],
            )
        )
        label = _label(templates, item)
        reply.mails.append(
            await market.post(
                uow, s.player_id, now, "Satın alınan eşya", f"{label}: sabit fiyatla alındı.", items=[item]
            )
        )
        for bid in await uow.mall.bids_of(listing.id or 0):
            await uow.delete(bid)
        await uow.delete(listing)
        await uow.save(c)
        await uow.save(paid)
        reply.out.append((S_FIX, pb.FixAuctionItemRspMsg(result=OK, mallItemId=listing.id or 0)))
        return reply

    await _transact(s, op)


@router.on(8454)
async def cancel(s: GameSession, msg: pb.AuctionItemReqMsg) -> None:
    """Cancela o próprio anúncio sem lance: o item volta à mochila (se couber)."""
    snap = s.snapshot
    assert snap is not None

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _pairs(uow, [x for x in [await uow.mall.listing(msg.id)] if x is not None])
        free = bag.free_positions(snap, now)
        if not rows or rows[0][0].seller_id != s.player_id:
            return Reply([(S_CANCEL, pb.CanceltemRspMsg(result=GONE, id=msg.id))])
        if rows[0][0].bidder_id or not free:  # com lance o anúncio já é de quem deu o lance
            return Reply([(S_CANCEL, pb.CanceltemRspMsg(result=CANCEL_FAIL, id=msg.id))])
        listing, item = rows[0]
        await uow.delete(listing)
        item.bag_type, item.object_id, item.pos = BagType.BAG, 0, free[0]
        snap.items.append(item)
        await uow.save(item)
        return Reply(
            [
                (S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, s.player_id)),
                (S_CANCEL, pb.CanceltemRspMsg(result=OK, id=listing.id or 0)),
            ]
        )

    await _transact(s, op)
