"""Sylph no leilão: 8448 ``sellType`` 2, o item -900 com o pet no ``property1``, busca, compra, correio e cancelar."""

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_mall import _diamonds, _listings, _mail_id, _pick, last
from tests.game.test_shop import me
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item, Pet
from wartune_server.game import mall as market
from wartune_server.game.handlers import mall as h
from wartune_server.game.handlers.pets import BASE_SLOTS
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

PAN = 104101  # "Pan", Quality 1


async def _pet(g: Game, **fields: object) -> Pet:
    """Pet livre na lista do jogador (no snapshot e no banco) e ouro para a taxa do anúncio."""
    snap = me(g)
    pos = max((p.pos for p in snap.pets), default=-1) + 1
    pet = Pet(g.user_id, PAN, "Pan", **({"grade": 7, "gp": 9000, "pos": pos, "is_bind": False} | fields))  # type: ignore[arg-type]
    snap.pets.append(pet)
    snap.character.gold = max(snap.character.gold, 10**5)
    snap.character.grades = max(snap.character.grades, h.SYLPH_GRADE)
    await g.server.services.characters.save(pet, snap.character)
    return pet


def _sell(pet: Pet, **fields: int) -> pb.SellItemReqMsg:
    """8448 como a AuctionSellSubmitPane manda para o Sylph: ``itemPos`` = id do pet, ``itemId`` vazio."""
    base = {"sellType": h.PET, "itemPos": pet.id or 0, "count": 1, "point": 10, "fixPoint": 50, "hour": 8}
    return pb.SellItemReqMsg(**(base | fields))


async def _held(g: Game, pet_id: int) -> Pet | None:
    return await g.server.services.characters.read(lambda uow: uow.pets.get(pet_id))


async def test_sell_lists_the_sylph_as_item_900_and_takes_it_off_the_roster(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        pet = await _pet(a)
        a.client.send(8448, _sell(pet))
        got = await a.until(4352)
        assert [p.code for p in got if p.code in (4540, 4352)] == [4540, 4352]
        gone = pb.PlayerPetMsg.FromString(next(p for p in got if p.code == 4540).body)
        assert [(i.petId, i.isDel) for i in gone.petInfo] == [(pet.id, True)]
        sold = last(got, pb.SellItemRspMsg)
        assert (sold.result, sold.item.templateId, sold.item.itemFrom) == (h.OK, market.SYLPH, h.PET)
        head, stats, resists, follow, change = sold.item.itemInfo.property1.split("|")
        assert head.split(",")[0::4] == [str(PAN), "7"] and head.split(",")[6] == "9000"  # template, nível, EXP total
        assert (len(stats.split(",")), len(resists.split(",")), follow, change) == (8, 6, "", "")
        assert me(a).pets == [] and (await _held(a, pet.id or 0)).held  # type: ignore[union-attr]

        again = await a.server.services.characters.snapshot(a.user_id)  # logar de novo: o pet à venda não aparece
        assert again.pets == []

        b = await a.join("bruxa")
        b.client.send(8457, pb.SearchItemReqMsg(itemName="pan", type=4, sonType=309, page=1))
        (row,) = last(await b.until(4359), pb.AuctionItemsMsg).sellItem
        assert (row.templateId, row.itemFrom, row.itemInfo.property1) == (
            market.SYLPH,
            h.PET,
            sold.item.itemInfo.property1,
        )
        b.client.send(8457, pb.SearchItemReqMsg(itemName="blank hero", page=1))  # o nome é o do pet, não o do -900
        assert list(last(await b.until(4359), pb.AuctionItemsMsg).sellItem) == []


async def test_sell_refuses_bound_fighting_arena_and_equipped_sylphs(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        bound = await _pet(g, is_bind=True)
        fighting = await _pet(g, is_fight=True)
        arena = await _pet(g)
        dressed = await _pet(g)
        snap = me(g)
        assert snap.arena is not None
        snap.arena.pet_formation = f"{arena.id},-1,-1,-1,-1,-1"
        gear = Item(g.user_id, 3110101, bag_type=26, object_id=dressed.id or 0)
        snap.items.append(gear)
        await g.server.services.characters.save(snap.arena, gear)
        free = await _pet(g)
        cases = [
            (_sell(bound), h.BLOCKED),
            (_sell(fighting), h.BLOCKED),
            (_sell(arena), h.BLOCKED),
            (_sell(dressed), h.BLOCKED),
            (_sell(free, count=2), h.COUNT),
            (_sell(free, point=9), h.START_PRICE),  # StartingPrice do -900 é 10
            (_sell(free, itemPos=999), h.NO_ITEM),
            (_sell(free, sellType=3), h.NOT_AUCTION),
        ]
        snap.character.grades = h.SYLPH_GRADE - 1
        g.client.send(8448, _sell(free))  # a aba abre no nível 50
        assert last(await g.until(4352), pb.SellItemRspMsg).result == h.NOT_AUCTION
        snap.character.grades = h.SYLPH_GRADE
        for msg, code in cases:
            g.client.send(8448, msg)
            assert last(await g.until(4352), pb.SellItemRspMsg).result == code, msg
        assert await _listings(g) == [] and len(snap.pets) == 5


async def test_buy_now_mails_the_sylph_and_the_buyer_takes_it_into_the_roster(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        pet = await _pet(a)
        a.client.send(8448, _sell(pet))
        await a.until(4352)
        (listing,) = await _listings(a)
        b = await a.join("bruxa")
        await _diamonds(b, 50)
        b.client.send(8453, pb.AuctionItemReqMsg(id=listing.id, point=50))
        assert last(await b.until(4357), pb.FixAuctionItemRspMsg).result == h.OK

        mail = await _mail_id(b, "Purchased Item")
        b.client.send(5022, pb.MailMsg(mailsIdArray=[mail], position=[0]))
        got = await b.until(4131)
        assert [
            r.result for r in pb.MailPickupRspMsg.FromString(next(x for x in got if x.code == 114).body).pickupResult
        ] == [True]
        assert 115 not in [p.code for p in got]  # nada entra na mochila
        (info,) = pb.PlayerPetMsg.FromString(next(x for x in got if x.code == 4540).body).petInfo
        assert (info.petId, info.isDel, info.curGrade) == (pet.id, False, 7)
        mine = await _held(b, pet.id or 0)
        assert mine is not None and (mine.character_id, mine.held) == (b.user_id, False)
        assert [p.id for p in me(b).pets] == [pet.id]
        rows = await b.server.services.characters.read(lambda uow: uow.items.by_character(b.user_id))
        assert [i for i in rows if i.template_id == market.SYLPH] == []  # o -900 some


async def test_full_roster_keeps_the_sylph_in_the_mail(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        pet = await _pet(a)
        a.client.send(8448, _sell(pet))
        await a.until(4352)
        (listing,) = await _listings(a)
        b = await a.join("bruxa")
        await _diamonds(b, 50)
        for _ in range(BASE_SLOTS):
            await _pet(b)
        b.client.send(8453, pb.AuctionItemReqMsg(id=listing.id, point=50))
        await b.until(4357)
        mail = await _mail_id(b, "Purchased Item")
        assert await _pick(b, mail) == [False]
        assert len(me(b).pets) == BASE_SLOTS
        snap = me(b)
        snap.pets.pop()
        assert await _pick(b, mail) == [True]  # abriu vaga: o anexo continuava lá


async def test_cancel_puts_the_sylph_back_in_the_roster(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        pet = await _pet(a)
        a.client.send(8448, _sell(pet))
        await a.until(4352)
        (listing,) = await _listings(a)
        a.client.send(8454, pb.AuctionItemReqMsg(id=listing.id))
        got = await a.until(4358)
        assert last(got, pb.CanceltemRspMsg).result == h.OK
        assert 4540 in [p.code for p in got]
        assert [p.id for p in me(a).pets] == [pet.id] and await _listings(a) == []
        back = await _held(a, pet.id or 0)
        assert back is not None and not back.held
