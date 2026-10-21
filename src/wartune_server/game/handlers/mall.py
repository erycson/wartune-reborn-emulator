"""Mercado entre jogadores: anunciar (8448), listas (8449 meus anúncios, 8450 mercado, 8452 meus lances,
8457 busca), lance (8451), compra pelo preço fixo (8453) e cancelar (8454); itens e Sylphs. Regras e fontes em
``docs/mercado.md`` (telas inglesas em ``m7/scripts/auction``); encerramento dos anúncios vencidos em ``game/mall.py``.
O 8450 não tem chamador no cliente inglês (a aba de compra usa o 8457); fica para quem mandar.

Cada pedido roda numa transação só (``characters.write``): a varredura dos vencidos, a operação e os
correios. Quem pede recebe direto na mochila; quem não pede (vendedor, vencedor, lance devolvido) recebe
pelo correio, porque o snapshot dele pode não estar carregado aqui.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from google.protobuf.message import Message

from ...domain import gameday
from ...domain.models import BagType, Character, Item, Mail, MallBid, MallListing, Pet, PlayerSnapshot, Purchase
from ...domain.repositories import UnitOfWork
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates
from .. import bag, rules
from .. import mail as mailbox
from .. import mall as market
from ..builders import login as b
from ..builders.player import item_info, item_moved, quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .items import _copy
from .pets import _in_arena, pet_items, pet_string, pets_msg, roster_full, take_back
from .player import _player

S_ITEMS = 115  # ItemMovedListMsg (a bolsa muda)
S_PETS = 4540  # PlayerPetMsg (o Sylph sai da lista ou volta)
S_QUESTS = 112  # QuestUpdatedRspMsg (missão 56)
S_SOLD, S_LIST_SELL, S_LIST_MARKET, S_BID = 4352, 4353, 4354, 4355
S_LIST_BIDS, S_FIX, S_CANCEL, S_SEARCH = 4356, 4357, 4358, 4359

# SellResultType do cliente (``Auction.ResultAlert`` = abs(código))
OK, GONE, COUNT, PRICE, FIX_PRICE, HOUR = 0, -2, -3, -4, -5, -6
BLOCKED, NO_ITEM, NO_GOLD, NO_POINT, NOT_AUCTION = -7, -8, -10, -11, -12
FIX_FAIL, CANCEL_FAIL, OWN_FIX, OWN_BID = -14, -15, -16, -17
SELL_MAX_COUNT = -18  # MALL_SELL_MAX_COUNT: mais de 9 unidades num anúncio
START_PRICE = -19  # Auction.ResultAlert19: "Starting Price cannot be less than the default price."
# Recusa do limite diário. O cliente inglês não tem o texto (Auction.ResultAlert52 só existia no turco): mostra o
# alerta genérico. Só sai com ``game_settings.mall_daily_limit`` configurado.
DAILY_LIMIT = -52
# -7: item vinculado ("Item is bound!") ou travado (8809)

GOODS, PET = 1, 2  # SellItemVO.itemType e MallItemMsg.itemFrom: item ou Sylph (o item -900, ``market.SYLPH``)
HOURS = (8, 24, 48)  # AuctionSellSubmitPane.getSelectTime: o 8448 leva as horas (Auction.SubmitHour1..3)
FEE_PER_HOUR = 250  # AuctionSellSubmitPane.updateCarryingCost: taxa em ouro = 250 × horas
MAX_COUNT = 9  # (cliente) Auction.ResultAlert18: "Number of items sold cannot exceed 9!" (por anúncio)
PAGE, PAGE_MAX = 9, 50  # 8449/8452 pedem 9 (AuctionFrame, AuctionRecordResultPane); o teto 50 é só defesa
SEARCH_PAGE = 7  # AuctionBuyResultPane: AuctionListComponent de 7 linhas (o 8457 não manda tamanho)
SYLPH_GRADE = 50  # AuctionFrame: a aba "Sell Sylphs" abre no nível 50 ("Unlocks at Lvl. 50")
MIN_POINT = 2  # AuctionSellSubmitPane.onSellBtnClick: inicial < 2 é recusado (Auction.SubmitAlert2)
# orderBy do 8457/8452 (AuctionSearchControl/AuctionRecordResultPane.__onTitleClick): 1 nível, 2 tempo restante,
# 3 preço atual, 4 preço fixo; orderType 2 = decrescente (o 1º clique, como a AuctionSellResultPane ordena a dela)
DESCENDING = 2

# Limite diário de compra em diamante: a ajuda inglesa do leilão (AuctionHelp.helpContent, 8 itens) não tem; o
# padrão é sem limite. ``game_settings.mall_daily_limit`` (JSON) liga: ``{"bands": [[nível abaixo de, limite],
# ...], "top": limite acima da última faixa}``, ex. o do turco ``{"bands": [[60, 500], [70, 1000]], "top": 1500}``.
# Conta o diamante pago (lance e preço fixo); o lance devolvido não volta para a cota.
DAILY_LIMIT_KEY = "mall_daily_limit"


def daily_limit(grades: int, config: Any) -> int | None:
    """Limite do dia para o nível, ou ``None`` (sem limite) quando o operador não configurou."""
    if not config:
        return None
    bands = config.get("bands") or []
    return next((int(limit) for below, limit in bands if grades < below), int(config["top"]))


def _spent_today(c: Character, now: datetime) -> int:
    return c.mall_spent if c.mall_day == gameday.today(now) else 0


def _over_limit(s: GameSession, c: Character, cost: int, now: datetime) -> bool:
    limit = daily_limit(c.grades, s.ctx.world.settings.get(DAILY_LIMIT_KEY))
    return limit is not None and _spent_today(c, now) + cost > limit


def _count_spent(c: Character, cost: int, now: datetime) -> None:
    c.mall_spent, c.mall_day = _spent_today(c, now) + cost, gameday.today(now)


@dataclass
class Reply:
    """O que um pedido manda depois do commit: pacotes, diamante do personagem, ouro (109) e cartas (148)."""

    out: list[tuple[int, Message]] = field(default_factory=list)
    player: bool = False
    mails: list[Mail] = field(default_factory=list)
    gold: bool = False


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
        # 115 e 4540 vão como estão: o complete() mandaria chaPos vazio e o cliente desfaria a equipe da arena
        s.send(code, msg if isinstance(msg, pb.ItemMovedListMsg | pb.PlayerPetMsg) else b.complete(msg))
    if reply.player:
        _player(s)
    if reply.gold:
        castle_yield(s)


async def _pairs(uow: UnitOfWork, listings: list[MallListing]) -> list[tuple[MallListing, Item]]:
    items = {i.id: i for i in await uow.items.by_ids([x.item_id for x in listings])}
    return [(x, items[x.item_id]) for x in listings if x.item_id in items]


async def _market(uow: UnitOfWork, server: int, kind: int) -> list[tuple[MallListing, Item]]:
    """Anúncios abertos do servidor, do mais novo para o mais antigo. ``kind`` GOODS só itens, PET só Sylphs,
    outro (o 8457 manda 0) os dois: **dedução**, o 8450 não tem chamador no cliente inglês."""
    rows = await _pairs(uow, await uow.mall.open_listings(server))
    rows.reverse()
    if kind in (GOODS, PET):
        rows = [(x, item) for x, item in rows if (item.template_id == market.SYLPH) == (kind == PET)]
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
        itemFrom=PET if item.template_id == market.SYLPH else GOODS,
        startTime=b.fmt_time(listing.started_at),
        maxAuctionId=(listing.id or 0) if listing.bidder_id else 0,  # > 0 = já tem lance (``auctioned``)
    )
    msg.itemInfo.CopyFrom(_copy(item_info(item, listing.seller_id), pb.SimpleItemInfoMsg()))
    return msg


def _sort_key(templates: GameTemplates, order_by: int) -> Callable[[MallListing, Item], Any] | None:
    keys: dict[int, Callable[[MallListing, Item], Any]] = {
        1: lambda _, item: int(market.goods_row(templates, item).get("NeedGrades") or 0),
        2: lambda x, _: x.ends_at,
        3: lambda x, _: x.point,
        4: lambda x, _: x.fix_point,
    }
    return keys.get(order_by)


def _ordered[T](
    rows: list[T],
    pair: Callable[[T], tuple[MallListing, Item]],
    templates: GameTemplates,
    order_by: int,
    order_type: int,
) -> list[T]:
    """Ordena pela coluna clicada; sem ``orderBy``, a ordem de sempre (o mais novo primeiro)."""
    key = _sort_key(templates, order_by)
    return rows if key is None else sorted(rows, key=lambda r: key(*pair(r)), reverse=order_type == DESCENDING)


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
    caçador, mago). ``type``/``sonType`` batem com ``MasterType``/``SonType``; ``usable`` vale para equipamento.
    O Sylph (categoria 4/309) busca pelo nome, nível e cor do pet (``market.goods_row``)."""
    row = market.goods_row(templates, item)
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


# --- anunciar (8448) ---


def _blocked(snap: PlayerSnapshot, item: Item | None, pet: Pet | None) -> bool:
    """Auction.ResultAlert7 ("Item is bound!"): item vinculado ou travado (8809); Sylph vinculado, em batalha, na
    equipe do Sylph Arena ou com equipamento (``PetSellView``: os outros nem aparecem na lista de venda)."""
    if item is not None:
        return item.is_binds or item.is_locked
    return pet is not None and (pet.is_bind or pet.is_fight or _in_arena(snap, pet) or bool(pet_items(snap, pet)))


@router.on(8448)
async def sell(s: GameSession, msg: pb.SellItemReqMsg) -> None:
    """Põe um item da mochila à venda: ``point`` é o lance inicial (mínimo 2 e ``StartingPrice`` × quantidade),
    ``fixPoint`` o preço fixo (obrigatório e acima do inicial, AuctionSellSubmitPane), ``hour`` 8, 24 ou 48 e a taxa
    de 250 × horas de ouro. O item sai da mochila na mesma transação que cria o anúncio: nunca existe nos dois
    lugares.

    Sylph (``sellType`` 2, ``itemPos`` = id do pet, ``AuctionSellSubmitPane``): nível 50, só o livre, fora de
    batalha, fora da equipe do Sylph Arena e sem equipamento (``PetSellView``), quantidade 1 e o ``StartingPrice`` do
    -900. Vai como o item -900 com o pet no ``property1``; o pet sai da lista (``held``, 4540 ``isDel``) até alguém
    pegar o correio."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        item = bag.at(snap, BagType.BAG, 0, msg.itemPos) if msg.sellType == GOODS else None
        pet = next((p for p in snap.pets if p.id == msg.itemPos), None) if msg.sellType == PET else None
        row = templates.get("ItemTempInfos", item.template_id if item is not None else market.SYLPH)
        have = item.count if item is not None else 1
        code = OK
        if msg.sellType not in (GOODS, PET):
            code = NOT_AUCTION
        elif row is None or (item is None and pet is None) or (item is not None and item.id != msg.itemId):
            code = NO_ITEM
        # StartingPrice 0 = o template não vai a leilão (cliente: -12); o Sylph pede o nível da aba
        elif int(row.get("StartingPrice") or 0) <= 0 or (pet is not None and c.grades < SYLPH_GRADE):
            code = NOT_AUCTION
        elif _blocked(snap, item, pet):
            code = BLOCKED
        elif not 1 <= msg.count <= have:
            code = COUNT
        elif msg.count > MAX_COUNT:
            code = SELL_MAX_COUNT
        elif row is not None and msg.point < max(MIN_POINT, int(row["StartingPrice"]) * msg.count):
            code = START_PRICE
        elif msg.fixPoint <= msg.point:
            code = FIX_PRICE
        elif msg.hour not in HOURS:
            code = HOUR
        elif c.gold < FEE_PER_HOUR * msg.hour:
            code = NO_GOLD
        if code != OK or (item is None and pet is None):
            s.log.info("8448 recusado", pedido=str(msg), resultado=code)
            return Reply([(S_SOLD, pb.SellItemRspMsg(result=code))])

        moved: Message
        if pet is not None:
            listed = Item(
                c.id or 0,
                market.SYLPH,
                bag_type=BagType.AUCTION,
                is_new=False,
                is_binds=False,
                object_id=pet.id or 0,
                property1=pet_string(pet, templates),
            )
            pet.held = True
            snap.pets.remove(pet)
            await uow.save(pet)
            await uow.save(listed)
            await uow.flush()  # o anúncio precisa do id do item
            moved = pets_msg(snap, templates, [])
            moved.petInfo.add(petId=pet.id or 0, isDel=True)
        elif item is None:  # já recusado acima; só para o mypy
            return Reply()
        elif msg.count < item.count:  # parte de uma pilha: a mochila fica com o resto
            item.count -= msg.count
            listed = replace(item, id=None, count=msg.count, bag_type=BagType.AUCTION, object_id=0, pos=0)
            await uow.save(item)
            await uow.save(listed)
            await uow.flush()  # o anúncio precisa do id do item
            moved = bag.moved([item], s.player_id)
        else:
            old_pos = item.pos
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
        c.gold -= FEE_PER_HOUR * msg.hour  # ponytail: o cancelamento não devolve a taxa (sem fonte)
        await uow.save(listing)
        await uow.save(c)
        await uow.flush()
        quests = rules.quest_event(snap, templates, rules.SELL_CONDITION, 0, 1)  # condição 56, "Auction" (missão 825)
        for q in quests:
            await uow.save(q)
        out: list[tuple[int, Message]] = [
            (S_PETS if pet is not None else S_ITEMS, moved),
            (S_SOLD, pb.SellItemRspMsg(result=OK, item=_listing_msg(listing, listed))),
        ]
        if quests:
            out.append((S_QUESTS, quest_update(quests, rules.quest_bitmap(snap))))
        return Reply(out, gold=True)

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
    """Meus lances em anúncios abertos (4356, lista ``itemBuy`` com o meu ``bidupPoint``), na ordem pedida."""

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        bids = await uow.mall.bids_by(s.player_id)
        listings = [x for x in [await uow.mall.listing(bid.listing_id) for bid in bids] if x is not None]
        mine = {bid.listing_id: bid for bid in bids}
        rows = [(mine[x.id or 0], x, item) for x, item in await _pairs(uow, listings)]
        rows.reverse()
        rows = _ordered(rows, lambda r: (r[1], r[2]), s.ctx.templates, msg.orderBy, msg.orderType)
        return Reply([(S_LIST_BIDS, _bids_msg(rows, msg.page, msg.count))])

    await _transact(s, op)


@router.on(8457)
async def search(s: GameSession, msg: pb.SearchItemReqMsg) -> None:
    """Busca no mercado (4359), na ordem pedida. O 8457 não manda tamanho de página: a tela tem 7 linhas."""
    snap = s.snapshot
    assert snap is not None
    server, templates = snap.character.server_id, s.ctx.templates

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _market(uow, server, 0)
        hits = [(x, item) for x, item in rows if _matches(msg, item, snap, templates)]
        hits = _ordered(hits, lambda r: r, templates, msg.orderBy, msg.orderType)
        return Reply([(S_SEARCH, _items_msg(hits, msg.page, SEARCH_PAGE))])

    await _transact(s, op)


# --- lance (8451), preço fixo (8453), cancelar (8454) ---


@router.on(8451)
async def bid(s: GameSession, msg: pb.AuctionItemReqMsg) -> None:
    """Lance em ``id`` (anúncio) por ``point``. O primeiro lance é ≥ o inicial (AuctionBuyResultPane manda o
    inicial quando ainda não há lance); os seguintes > o último; ≥ fixo o cliente já troca pelo 8453. O líder não
    cobre o próprio lance (Auction.ResultAlert17). O diamante do lance sai agora (``ledger``); quem foi superado
    recebe o dele de volta pelo correio."""
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
            code = OWN_FIX  # AuctionChecker.checkAuction já barra; −16 "You can't buy an item from yourself!"
        elif listing.bidder_id == s.player_id:
            code = OWN_BID  # Auction.ResultAlert17: "Bid failed:you are already the high bidder."
        elif msg.point < minimum or (listing.fix_point and msg.point >= listing.fix_point):
            code = PRICE
        else:
            code = OK
        if code != OK:
            return Reply([(S_BID, pb.AuctionItemRspMsg(result=code))])
        if _over_limit(s, c, msg.point, now):
            return Reply([(S_BID, pb.AuctionItemRspMsg(result=DAILY_LIMIT))])
        paid = ledger.pay(c, msg.point, bind=False, reason="mall", ref=f"mall:{listing.id} lance", now=now)
        if paid is None:
            return Reply([(S_BID, pb.AuctionItemRspMsg(result=NO_POINT))])
        _count_spent(c, msg.point, now)
        reply = Reply(player=True)
        if listing.bidder_id:
            reply.mails.append(
                await market.post(
                    uow,
                    listing.bidder_id,
                    now,
                    "Bid Refund",  # texto deduzido (sem fonte no cliente/captura)
                    f"{market.label(templates, item)}: your bid has been returned.",
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
        elif _over_limit(s, c, cost, now):
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
                    "Bid Refund",  # texto deduzido (sem fonte no cliente/captura)
                    f"{market.label(templates, item)}: your bid has been returned.",
                    goods=[(market.DIAMOND, listing.point)],
                )
            )
        reply.mails.append(
            await market.post(
                uow,
                listing.seller_id,
                now,
                "Sale Income",  # texto deduzido (sem fonte no cliente/captura)
                f"{market.label(templates, item)} has been sold.",
                goods=[(market.DIAMOND, market.income(listing.fix_point))],
            )
        )
        label = market.label(templates, item)
        reply.mails.append(
            await market.post(
                # texto deduzido (sem fonte no cliente/captura); termo Buy-It-Now do language.txt
                uow,
                s.player_id,
                now,
                "Purchased Item",
                f"{label}: bought at the Buy-It-Now price.",
                items=[item],
            )
        )
        for bid in await uow.mall.bids_of(listing.id or 0):
            await uow.delete(bid)
        await uow.delete(listing)
        await uow.save(c)
        await uow.save(paid)
        await uow.save(
            Purchase(c.id or 0, "mall", listing.id or 0, item.template_id, item.count, "Point", listing.fix_point, now)
        )
        reply.out.append((S_FIX, pb.FixAuctionItemRspMsg(result=OK, mallItemId=listing.id or 0)))
        return reply

    await _transact(s, op)


@router.on(8454)
async def cancel(s: GameSession, msg: pb.AuctionItemReqMsg) -> None:
    """Cancela o próprio anúncio sem lance: o item volta à mochila (se couber), o Sylph à lista (se houver vaga)."""
    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates

    async def op(uow: UnitOfWork, now: datetime) -> Reply:
        rows = await _pairs(uow, [x for x in [await uow.mall.listing(msg.id)] if x is not None])
        if not rows or rows[0][0].seller_id != s.player_id:
            return Reply([(S_CANCEL, pb.CanceltemRspMsg(result=GONE, id=msg.id))])
        listing, item = rows[0]
        sylph = item.template_id == market.SYLPH
        pet = await uow.pets.get(item.object_id) if sylph else None
        free = bag.free_positions(snap, now)
        stuck = (pet is None or roster_full(snap)) if sylph else not free
        if listing.bidder_id or stuck:  # com lance o anúncio já é de quem deu o lance
            return Reply([(S_CANCEL, pb.CanceltemRspMsg(result=CANCEL_FAIL, id=msg.id))])
        await uow.delete(listing)
        await uow.flush()  # antes do item: apagar o item já apaga o anúncio (cascata)
        back: tuple[int, Message]
        if pet is not None:
            await uow.delete(item)  # o -900 só embrulha o pet
            take_back(snap, pet)
            await uow.save(pet)
            back = (S_PETS, pets_msg(snap, templates, [pet]))
        else:
            item.bag_type, item.object_id, item.pos = BagType.BAG, 0, free[0]
            snap.items.append(item)
            await uow.save(item)
            back = (S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
        return Reply([back, (S_CANCEL, pb.CanceltemRspMsg(result=OK, id=listing.id or 0))])

    await _transact(s, op)
