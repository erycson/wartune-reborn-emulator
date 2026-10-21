"""Mercado entre jogadores (8448-8457): anunciar, listas, lance, preço fixo, cancelar, busca e encerramento."""

import asyncio
import sqlite3
import zlib
from pathlib import Path

import pytest
from google.protobuf.message import Message

from tests.game.harness import Game, logged_in
from tests.game.test_shop import me
from wartune_server.domain.models import BagType, Item, MallListing
from wartune_server.game import mall as market
from wartune_server.game.handlers import mall as h
from wartune_server.game.router import router
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

CODES = [8448, 8449, 8450, 8451, 8452, 8453, 8454, 8457]
HORN = 208002  # Bullhorn (Large): StartingPrice 10, empilhável (MaxCount 999)
CRYSTAL = 208014  # Soul Crystal: StartingPrice 0, o template não vai a leilão
CHEAP = 208027  # StartingPrice 1


def last[T: Message](got: list[Packet], cls: type[T]) -> T:
    """O corpo do último pacote recebido (o que ``until`` esperava)."""
    return cls.FromString(got[-1].body)


def _sell(item: Item, **fields: int) -> pb.SellItemReqMsg:
    """8448 como a AuctionSellSubmitPane manda: o preço fixo é obrigatório (padrão alto, fora dos lances)."""
    base = {"sellType": h.GOODS, "itemId": item.id or 0, "itemPos": item.pos, "count": 1, "point": 10}
    return pb.SellItemReqMsg(**(base | {"fixPoint": 1000, "hour": 8} | fields))


async def _put(g: Game, template: int, count: int, pos: int = 5) -> Item:
    """Item livre (só o não vinculado vai ao leilão) na mochila do jogador, no snapshot e no banco, e ouro para a
    taxa do anúncio."""
    item = Item(g.user_id, template, pos=pos, count=count, is_binds=False)
    me(g).items.append(item)
    c = me(g).character
    c.gold = max(c.gold, 10**5)
    await g.server.services.characters.save(item, c)
    return item


async def _diamonds(g: Game, point: int) -> None:
    c = me(g).character
    c.point = point
    await g.server.services.characters.save(c)


async def _owned(g: Game, template: int) -> list[tuple[int, int, int]]:
    """(bolsa, posição, quantidade) de cada linha do banco com o template, anúncios e correio incluídos."""
    rows = await g.server.services.characters.read(lambda uow: uow.items.by_character(g.user_id))
    return sorted((i.bag_type, i.pos, i.count) for i in rows if i.template_id == template)


async def _listings(g: Game) -> list[MallListing]:
    server = me(g).character.server_id
    return await g.server.services.characters.read(lambda uow: uow.mall.open_listings(server))


async def _inbox(g: Game) -> str:
    form = {"userId": str(g.user_id), "key": g.key, "mailId": "0"}
    return zlib.decompress(await (await g.http.post("/maillist", data=form)).read()).decode()


async def _mail_id(g: Game, title: str) -> int:
    """Id do correio com esse título, lido do banco (a chave HTTP do correio vence com o relógio de teste)."""
    mails = await g.server.services.characters.read(lambda uow: uow.mails.by_receiver(g.user_id))
    ids = [m.id or 0 for m in mails if m.title == title]
    assert ids, title
    return ids[0]


async def _pick(g: Game, mail_id: int) -> list[bool]:
    g.client.send(5022, pb.MailMsg(mailsIdArray=[mail_id], position=[0]))
    return [r.result for r in last(await g.until(114), pb.MailPickupRspMsg).pickupResult]


def _purchases(tmp_path: Path) -> list[tuple[int, str, int, int, int, str, int]]:
    with sqlite3.connect(tmp_path / "game.db") as db:
        sql = "SELECT character_id, source, good_id, template_id, count, currency, price FROM purchases"
        return list(db.execute(sql))


async def test_every_code_has_a_handler() -> None:
    from wartune_server.game import handlers  # noqa: F401  (registra)

    assert [c for c in CODES if router.get(c) is None] == []


async def test_handlers_survive_empty_and_minimal_bodies(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        horn = await _put(g, HORN, 3)
        await _diamonds(g, 100)
        minimal: dict[int, Message] = {
            8448: _sell(horn, count=2),  # 2 x 10 de inicial, mas o lance é 10: recusado (START_PRICE)
            8449: pb.MallItemViewReqMsg(page=1, count=9),
            8450: pb.MallItemViewReqMsg(page=1, count=9, **{"from": h.GOODS}),
            8451: pb.AuctionItemReqMsg(id=1, point=1),
            8452: pb.MallItemViewReqMsg(page=1, count=9),
            8453: pb.AuctionItemReqMsg(id=1, point=1),
            8454: pb.AuctionItemReqMsg(id=1),
            8457: pb.SearchItemReqMsg(itemName="bullhorn", page=1),
        }
        for code in CODES:
            for msg in [None, minimal[code]]:
                g.client.send(code, msg)
                g.client.send(20008)  # o relógio volta = a sessão seguiu viva
                await g.until(4234)

        assert await _listings(g) == []  # nenhum pedido vazio ou mínimo anunciou nada
        assert await _owned(g, HORN) == [(BagType.BAG, 5, 3)]  # e a mochila ficou como estava


async def test_sell_splits_the_stack_and_a_full_sale_leaves_the_bag_in_one_save(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        stack = await _put(g, HORN, 10)
        whole = await _put(g, HORN, 1, pos=6)

        g.client.send(8448, _sell(stack, count=4, point=40, hour=8))
        got = await g.until(109)  # a taxa sai do ouro e a barra de recursos vem depois do 4352
        rsp = pb.SellItemRspMsg.FromString(next(p for p in got if p.code == 4352).body)
        assert rsp.result == h.OK and rsp.item.templateId == HORN and rsp.item.point == 40
        assert stack.count == 6
        assert me(g).character.gold == 10**5 - 250 * 8  # AuctionSellSubmitPane: 250 × horas
        assert await _owned(g, HORN) == [(BagType.BAG, 5, 6), (BagType.BAG, 6, 1), (BagType.AUCTION, 0, 4)]

        g.client.send(8448, _sell(whole, itemPos=6, hour=48))
        assert last(await g.until(4352), pb.SellItemRspMsg).result == h.OK
        assert me(g).character.gold == 10**5 - 250 * (8 + 48)
        fresh = await g.server.services.characters.snapshot(g.user_id)
        assert fresh.character.gold == 10**5 - 250 * (8 + 48)  # gravado na transação do anúncio
        assert not any(i is whole for i in me(g).items)  # saiu da mochila na mesma transação do anúncio
        assert await _owned(g, HORN) == [(BagType.BAG, 5, 6), (BagType.AUCTION, 0, 1), (BagType.AUCTION, 0, 4)]
        assert len(await _listings(g)) == 2

        # o login seguinte não põe o que está à venda no snapshot
        assert [i.count for i in fresh.items if i.template_id == HORN] == [6]


async def test_sell_refuses_with_the_client_result_codes(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        horn = await _put(g, HORN, 10)
        crystal = await _put(g, CRYSTAL, 1, pos=6)
        cases: list[tuple[pb.SellItemReqMsg, int]] = [
            (_sell(horn, sellType=3), h.NOT_AUCTION),
            (_sell(horn, sellType=h.PET), h.NO_ITEM),  # Sylph: itemPos é o id do pet
            (_sell(crystal, itemPos=6), h.NOT_AUCTION),
            (_sell(horn, count=11, point=110), h.COUNT),
            (_sell(horn, count=2, point=19), h.START_PRICE),  # Auction.ResultAlert19
            (_sell(horn, count=2, point=20, fixPoint=20), h.FIX_PRICE),
            (_sell(horn, count=2, point=20, fixPoint=0), h.FIX_PRICE),  # SubmitAlert3: o fixo é obrigatório
            (_sell(horn, count=2, point=20, hour=0), h.HOUR),
            (_sell(horn, count=2, point=20, hour=12), h.HOUR),  # só 8, 24 ou 48 (Auction.SubmitHour1..3)
            (_sell(horn, itemId=(horn.id or 0) + 999), h.NO_ITEM),
        ]
        for msg, expected in cases:
            g.client.send(8448, msg)
            assert last(await g.until(4352), pb.SellItemRspMsg).result == expected
        horn.is_binds = True
        g.client.send(8448, _sell(horn, count=2, point=20))
        assert last(await g.until(4352), pb.SellItemRspMsg).result == h.BLOCKED  # ResultAlert7: "Item is bound!"
        horn.is_binds = False
        me(g).character.gold = 250 * 24 - 1
        g.client.send(8448, _sell(horn, count=2, point=20, hour=24))
        assert last(await g.until(4352), pb.SellItemRspMsg).result == h.NO_GOLD  # ResultAlert10
        assert horn.count == 10 and crystal.count == 1 and me(g).character.gold == 250 * 24 - 1
        assert await _listings(g) == []


async def test_market_list_and_search_show_open_listings(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        horn = await _put(g, HORN, 4)
        g.client.send(8448, _sell(horn, count=4, point=40, hour=8))
        await g.until(4352)
        (listing,) = await _listings(g)
        b = await g.join("bruxa")

        b.client.send(8450, pb.MallItemViewReqMsg(page=1, count=9, **{"from": h.GOODS}))
        market = last(await b.until(4354), pb.AuctionItemsMsg)
        assert [(x.id, x.templateId, x.userId, x.point, x.hour) for x in market.sellItem] == [
            (listing.id, HORN, g.user_id, 40, 8)
        ]
        assert (market.pageIdx, market.pageCount) == (1, 1)

        b.client.send(8457, pb.SearchItemReqMsg(itemName="bullhorn", page=1))
        assert [x.id for x in last(await b.until(4359), pb.AuctionItemsMsg).sellItem] == [listing.id]
        b.client.send(8457, pb.SearchItemReqMsg(minLevel=50, page=1))
        assert list(last(await b.until(4359), pb.AuctionItemsMsg).sellItem) == []

        g.client.send(8449, pb.MallItemViewReqMsg(page=1, count=9))
        mine = last(await g.until(4353), pb.AuctionItemsMsg).sellItem
        assert [(x.id, x.maxAuctionId) for x in mine] == [(listing.id, 0)]  # ainda sem lance


async def test_bids_refund_the_outbid_player_by_mail_and_show_in_my_bids(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        horn = await _put(a, HORN, 2)
        a.client.send(8448, _sell(horn, count=2, point=20, hour=8))
        await a.until(4352)
        (listing,) = await _listings(a)
        b = await a.join("bruxa")
        c = await a.join("carol")
        await _diamonds(b, 100)
        await _diamonds(c, 100)

        b.client.send(8451, pb.AuctionItemReqMsg(id=listing.id, point=20))  # primeiro lance: o inicial
        first = last(await b.until(4355), pb.AuctionItemRspMsg)
        assert first.result == h.OK and first.itemBuy.bidupPoint == 20
        assert me(b).character.point == 80

        c.client.send(8451, pb.AuctionItemReqMsg(id=listing.id, point=20))  # precisa passar do lance atual
        assert last(await c.until(4355), pb.AuctionItemRspMsg).result == h.PRICE
        a.client.send(8451, pb.AuctionItemReqMsg(id=listing.id, point=30))  # vendedor não dá lance no próprio
        assert last(await a.until(4355), pb.AuctionItemRspMsg).result == h.OWN_FIX
        b.client.send(8451, pb.AuctionItemReqMsg(id=listing.id, point=30))  # ResultAlert17: já é o maior lance
        assert last(await b.until(4355), pb.AuctionItemRspMsg).result == h.OWN_BID
        assert me(b).character.point == 80

        c.client.send(8451, pb.AuctionItemReqMsg(id=listing.id, point=30))
        assert last(await c.until(4355), pb.AuctionItemRspMsg).result == h.OK
        (now,) = await _listings(a)
        assert (now.point, now.bidder_id) == (30, c.user_id)
        assert me(c).character.point == 70

        # o lance devolvido vai pelo correio: o diamante só entra no 5022
        assert "Bid Refund" in await _inbox(b)
        refund = await _mail_id(b, "Bid Refund")
        assert me(b).character.point == 80
        assert await _pick(b, refund) == [True]
        assert me(b).character.point == 100

        b.client.send(8452, pb.MallItemViewReqMsg(page=1, count=9))
        assert [x.bidupPoint for x in last(await b.until(4356), pb.AuctionItemsMsg).itemBuy] == [20]
        a.client.send(8449, pb.MallItemViewReqMsg(page=1, count=9))
        assert [x.maxAuctionId for x in last(await a.until(4353), pb.AuctionItemsMsg).sellItem] == [listing.id]


async def test_fixed_price_buy_mails_the_item_to_the_buyer_and_the_taxed_price_to_the_seller(tmp_path: Path) -> None:
    """(cliente) AuctionHelp.helpContent item 3 (a compra chega pelo correio) e item 7 (20% de imposto)."""
    async with logged_in(tmp_path, novice=19000) as a:
        horn = await _put(a, HORN, 1)
        a.client.send(8448, _sell(horn, point=10, fixPoint=50, hour=8))
        await a.until(4352)
        (listing,) = await _listings(a)
        b = await a.join("bruxa")
        await _diamonds(b, 60)
        seller_before = me(a).character.point

        b.client.send(8453, pb.AuctionItemReqMsg(id=listing.id, point=49))  # o preço fixo é exato
        assert last(await b.until(4357), pb.FixAuctionItemRspMsg).result == h.PRICE

        b.client.send(8453, pb.AuctionItemReqMsg(id=listing.id, point=50))
        got = await b.until(4357)
        assert last(got, pb.FixAuctionItemRspMsg).result == h.OK
        assert 115 not in [p.code for p in got]  # a mochila não muda: o item vai pelo correio
        assert me(b).character.point == 10
        assert _purchases(tmp_path) == [(me(b).character.id, "mall", listing.id, HORN, 1, "Point", 50)]
        assert await _owned(b, HORN) == [(BagType.MAIL, 0, 1)]
        assert await _listings(a) == []
        assert await _pick(b, await _mail_id(b, "Purchased Item")) == [True]
        assert [bag for bag, _, _ in await _owned(b, HORN)] == [BagType.BAG]

        sale = await _mail_id(a, "Sale Income")  # vendedor online: recebe pelo correio mesmo assim
        assert await _pick(a, sale) == [True]
        assert me(a).character.point == seller_before + 40  # 50 menos 20% de imposto


async def test_cancel_returns_the_item_and_is_refused_after_a_bid(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        horn = await _put(a, HORN, 3)
        a.client.send(8448, _sell(horn, count=3, point=30, hour=8))
        await a.until(4352)
        (first,) = await _listings(a)
        a.client.send(8454, pb.AuctionItemReqMsg(id=first.id))
        assert last(await a.until(4358), pb.CanceltemRspMsg).result == h.OK
        assert await _listings(a) == []
        assert [(bag, count) for bag, _, count in await _owned(a, HORN)] == [(BagType.BAG, 3)]  # voltou inteiro

        second = await _put(a, HORN, 1, pos=6)
        a.client.send(8448, _sell(second, point=10, hour=8, itemPos=6))
        await a.until(4352)
        (open_,) = await _listings(a)
        b = await a.join("bruxa")
        await _diamonds(b, 100)
        b.client.send(8451, pb.AuctionItemReqMsg(id=open_.id, point=10))
        assert last(await b.until(4355), pb.AuctionItemRspMsg).result == h.OK
        a.client.send(8454, pb.AuctionItemReqMsg(id=open_.id))
        assert last(await a.until(4358), pb.CanceltemRspMsg).result == h.CANCEL_FAIL
        assert len(await _listings(a)) == 1


async def test_expired_auctions_settle_by_mail_even_for_an_offline_seller(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        sold = await _put(a, HORN, 1)
        unsold = await _put(a, HORN, 1, pos=6)
        a.client.send(8448, _sell(sold, point=10, hour=8))
        await a.until(4352)
        a.client.send(8448, _sell(unsold, point=10, hour=8, itemPos=6))
        await a.until(4352)
        win, _ = await _listings(a)
        b = await a.join("bruxa")
        await _diamonds(b, 100)
        b.client.send(8451, pb.AuctionItemReqMsg(id=win.id, point=15))
        await b.until(4355)

        a.client.writer.close()  # o vendedor sai antes do fim
        await b.idle(0.3)
        assert a.server.online.get(a.user_id) is None
        # a chave de login expira após 30 min sem uso; o HTTP renova a chave enquanto o tempo passa
        for _ in range(19):
            clock.advance(1500)
            await _inbox(a)
        clock.advance(301)  # 28801 s: as 8 h dos anúncios venceram

        b.client.send(8450, pb.MallItemViewReqMsg(page=1, count=9, **{"from": h.GOODS}))
        await b.until(4354)
        assert await _listings(b) == []  # os dois anúncios venceram e foram encerrados na mesma transação
        assert await _owned(b, HORN) == [(BagType.MAIL, 0, 1)]  # o lance vencedor: item na caixa de correio
        assert _purchases(tmp_path) == [(me(b).character.id, "mall_lance", win.id, HORN, 1, "Point", 15)]

        won = await _mail_id(b, "Won Item")
        b.client.send(8206, pb.MailDelReqMsg(delList=[won]))  # item ainda não retirado: o correio não some
        assert list(last(await b.until(4132), pb.MailDelReqMsg).delList) == []
        assert await _pick(b, won) == [True]
        assert [bag for bag, _, _ in await _owned(b, HORN)] == [BagType.BAG]

        a2 = await a.connect()  # o vendedor volta: diamante do lance e item sem lance, tudo pelo correio
        before = me(a2).character.point
        assert await _pick(a2, await _mail_id(a2, "Sale Income")) == [True]
        assert me(a2).character.point == before + 12  # 15 menos 20% de imposto, para baixo
        assert await _pick(a2, await _mail_id(a2, "Returned Item")) == [True]
        assert [bag for bag, _, _ in await _owned(a2, HORN)] == [BagType.BAG]  # o sem lance voltou; o vendido é de b


async def test_scheduled_sweep_settles_an_expired_listing_with_no_request(tmp_path: Path) -> None:
    """(cliente) o anúncio vencido encerra sozinho: o agendador roda sem nenhum pedido ao mercado."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        sold = await _put(a, HORN, 1)
        a.client.send(8448, _sell(sold, point=10, hour=8))
        await a.until(4352)
        (win,) = await _listings(a)
        b = await a.join("bruxa")
        await _diamonds(b, 100)
        b.client.send(8451, pb.AuctionItemReqMsg(id=win.id, point=15))
        await b.until(4355)

        services = a.server.services
        loop = asyncio.create_task(
            market.run(
                services.characters, services.templates, a.server.online, clock, a.server.settings.server_id, 0.01
            )
        )
        try:
            clock.advance(8 * 3600 + 1)
            got = await b.idle(0.3)
        finally:
            loop.cancel()
            await asyncio.gather(loop, return_exceptions=True)
        assert await _listings(a) == []  # ninguém pediu nada ao mercado e o anúncio encerrou
        assert await _owned(b, HORN) == [(BagType.MAIL, 0, 1)]  # o vencedor recebe o item pelo correio
        assert any(p.code == 148 for p in got)  # e o vencedor online recebe o aviso do correio


async def test_sweep_closes_a_listing_exactly_at_its_end(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        horn = await _put(a, HORN, 1)
        a.client.send(8448, _sell(horn, point=10, hour=8))
        await a.until(4352)
        services = a.server.services
        server = a.server.settings.server_id

        clock.advance(8 * 3600 - 1)  # um segundo antes do fim: ainda aberto
        await market.sweep(services.characters, services.templates, a.server.online, server, clock.now())
        assert len(await _listings(a)) == 1

        clock.advance(1)  # ends_at <= agora: encerra
        await market.sweep(services.characters, services.templates, a.server.online, server, clock.now())
        assert await _listings(a) == []


async def test_scheduler_keeps_running_after_a_failed_round(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    second_round = asyncio.Event()

    async def flaky(*_: object) -> list[object]:
        calls.append(len(calls))
        if len(calls) == 1:
            raise RuntimeError("banco fora do ar")
        second_round.set()
        return []

    monkeypatch.setattr(market, "sweep", flaky)
    loop = asyncio.create_task(market.run(None, None, None, FakeClock(), 1, 0.01))  # type: ignore[arg-type]
    try:
        await asyncio.wait_for(second_round.wait(), 2)
    finally:
        loop.cancel()
        await asyncio.gather(loop, return_exceptions=True)
    assert len(calls) >= 2  # a rodada que falhou não parou o agendador


async def test_sell_caps_a_listing_at_nine_pieces(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        stack = await _put(g, HORN, 10)
        g.client.send(8448, _sell(stack, count=10, point=100))  # Auction.ResultAlert18: no máximo 9
        assert last(await g.until(4352), pb.SellItemRspMsg).result == h.SELL_MAX_COUNT
        assert stack.count == 10 and await _listings(g) == []

        g.client.send(8448, _sell(stack, count=9, point=90))
        assert last(await g.until(4352), pb.SellItemRspMsg).result == h.OK
        assert stack.count == 1


def test_sale_tax_takes_twenty_percent_rounded_down() -> None:
    assert [market.income(p) for p in (50, 15, 4, 1)] == [40, 12, 3, 0]


TURKISH_LIMIT = {"bands": [[60, 500], [70, 1000]], "top": 1500}  # o da ajuda turca, como exemplo de configuração


def test_daily_limit_by_level() -> None:
    """Sem ``game_settings.mall_daily_limit`` não há limite (a ajuda inglesa não tem); configurado, vale por faixa."""
    assert h.daily_limit(90, None) is None
    assert [h.daily_limit(g, TURKISH_LIMIT) for g in (1, 40, 59, 60, 69, 70, 80, 90)] == [
        500,
        500,
        500,
        1000,
        1000,
        1500,
        1500,
        1500,
    ]


async def test_bid_and_fixed_buy_stop_at_the_daily_limit(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        first = await _put(a, HORN, 1)
        second = await _put(a, HORN, 1, pos=6)
        a.client.send(8448, _sell(first, point=10, fixPoint=900, hour=8))
        await a.until(4352)
        a.client.send(8448, _sell(second, point=10, fixPoint=20, hour=8, itemPos=6))
        await a.until(4352)
        cheap, pricey = sorted(await _listings(a), key=lambda x: x.fix_point)
        b = await a.join("bruxa")
        await _diamonds(b, 2000)
        world = b.server.services.world
        object.__setattr__(world, "settings", {**world.settings, h.DAILY_LIMIT_KEY: TURKISH_LIMIT})  # só do teste
        limit = h.daily_limit(me(b).character.grades, TURKISH_LIMIT)
        assert limit is not None

        b.client.send(8453, pb.AuctionItemReqMsg(id=pricey.id, point=900))  # passa do limite do dia
        assert last(await b.until(4357), pb.FixAuctionItemRspMsg).result == h.DAILY_LIMIT
        b.client.send(8451, pb.AuctionItemReqMsg(id=pricey.id, point=limit + 1))
        assert last(await b.until(4355), pb.AuctionItemRspMsg).result == h.DAILY_LIMIT
        assert me(b).character.point == 2000  # recusado antes de cobrar

        b.client.send(8451, pb.AuctionItemReqMsg(id=pricey.id, point=limit - 10))
        assert last(await b.until(4355), pb.AuctionItemRspMsg).result == h.OK
        b.client.send(8453, pb.AuctionItemReqMsg(id=cheap.id, point=20))  # 10 restantes, o fixo custa 20
        assert last(await b.until(4357), pb.FixAuctionItemRspMsg).result == h.DAILY_LIMIT
        assert me(b).character.mall_spent == limit - 10
        fresh = await b.server.services.characters.snapshot(b.user_id)
        assert fresh.character.mall_spent == limit - 10  # gravado junto com o débito


async def test_sell_refuses_a_start_price_below_two(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        cheap = await _put(g, CHEAP, 1)
        # AuctionSellSubmitPane.onSellBtnClick recusa inicial < 2 (Auction.SubmitAlert2)
        for point in (0, 1):
            g.client.send(8448, _sell(cheap, point=point))
            assert last(await g.until(4352), pb.SellItemRspMsg).result == h.START_PRICE
        g.client.send(8448, _sell(cheap, point=2))
        assert last(await g.until(4352), pb.SellItemRspMsg).result == h.OK


async def test_search_pages_by_seven_in_the_clicked_order(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        stack = await _put(g, HORN, 8)
        for i, point in enumerate([13, 10, 17, 11, 16, 12, 15, 14]):
            g.client.send(8448, _sell(stack, point=point, fixPoint=100 - i))
            assert last(await g.until(4352), pb.SellItemRspMsg).result == h.OK
        b = await g.join("bruxa")

        # AuctionBuyResultPane: 7 linhas; orderBy 3 = preço atual, orderType 2 = decrescente
        b.client.send(8457, pb.SearchItemReqMsg(itemName="bullhorn", page=1, orderBy=3, orderType=2))
        first = last(await b.until(4359), pb.AuctionItemsMsg)
        assert [x.point for x in first.sellItem] == [17, 16, 15, 14, 13, 12, 11]
        assert (first.pageIdx, first.pageCount) == (1, 2)
        b.client.send(8457, pb.SearchItemReqMsg(itemName="bullhorn", page=2, orderBy=3, orderType=2))
        assert [x.point for x in last(await b.until(4359), pb.AuctionItemsMsg).sellItem] == [10]

        b.client.send(8457, pb.SearchItemReqMsg(itemName="bullhorn", page=1, orderBy=4, orderType=1))
        assert [x.fixPoint for x in last(await b.until(4359), pb.AuctionItemsMsg).sellItem] == [
            93,
            94,
            95,
            96,
            97,
            98,
            99,
        ]
