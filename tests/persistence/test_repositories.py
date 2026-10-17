from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from wartune_server.domain.models import Account, Castle, Character, GameServer, Hero


def _now() -> datetime:
    return datetime.now(UTC)


async def _account(uow, name: str = "alice") -> Account:  # type: ignore[no-untyped-def]
    return await uow.accounts.add(Account(name, "hash", _now()))


async def test_account_roundtrip_keeps_timezone(uow_factory) -> None:  # type: ignore[no-untyped-def]
    async with uow_factory() as uow:
        acc = await _account(uow)
        await uow.commit()
    async with uow_factory() as uow:
        loaded = await uow.accounts.by_username("alice")
        assert loaded is not None and loaded.id == acc.id
        assert loaded.created_at.tzinfo is not None


async def test_uncommitted_changes_are_discarded(uow_factory) -> None:  # type: ignore[no-untyped-def]
    async with uow_factory() as uow:
        await _account(uow)
    async with uow_factory() as uow:
        assert await uow.accounts.by_username("alice") is None


async def test_one_character_per_account_per_server(uow_factory) -> None:  # type: ignore[no-untyped-def]
    async with uow_factory() as uow:
        await uow.servers.upsert(GameServer(2, "S2", "local_0002", "127.0.0.1", 8081, 5002, _now()))
        acc = await _account(uow)
        assert acc.id is not None
        await uow.characters.add(Character(acc.id, 1, "Herói", 1, 1, 1, _now()))
        await uow.characters.add(Character(acc.id, 2, "Herói", 1, 1, 1, _now()))  # outro servidor: ok
        await uow.commit()

    async with uow_factory() as uow:
        assert (await uow.characters.by_account(acc.id, 2)) is not None
        assert await uow.characters.nickname_taken(1, "Herói")
        assert not await uow.characters.nickname_taken(1, "Outro")
        with pytest.raises(IntegrityError):
            await uow.characters.add(Character(acc.id, 1, "Segundo", 1, 1, 1, _now()))


async def test_hero_and_castle_belong_to_character(uow_factory) -> None:  # type: ignore[no-untyped-def]
    async with uow_factory() as uow:
        acc = await _account(uow)
        assert acc.id is not None
        char = await uow.characters.add(Character(acc.id, 1, "Maga", 0, 1, 6, _now()))
        assert char.id is not None
        await uow.heroes.add(Hero(char.id, 6, "Maga", intellect=5, is_leader=True))
        await uow.castles.add(Castle(char.id, "Maga", 100000313, 26, 46))
        await uow.commit()
    async with uow_factory() as uow:
        heroes = await uow.heroes.by_character(char.id)
        castle = await uow.castles.by_character(char.id)
    assert [h.intellect for h in heroes] == [5]
    assert castle is not None and castle.energy == 500
