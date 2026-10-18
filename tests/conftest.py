from __future__ import annotations

import secrets
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta

import pytest

from wartune_server.domain.models import Account, GameServer, PlayTicket
from wartune_server.game import worldboss
from wartune_server.persistence.database import Database
from wartune_server.persistence.repositories import SqlAlchemyUnitOfWork


@pytest.fixture(autouse=True)
def game_timezone() -> None:
    """Os testes reproduzem as capturas do servidor turco (UTC+3); o padrão do servidor é o fuso do inglês."""
    worldboss.set_timezone("+03:00")


@pytest.fixture
async def database(tmp_path) -> AsyncIterator[Database]:  # type: ignore[no-untyped-def]
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await db.migrate()
    async with SqlAlchemyUnitOfWork(db.sessions) as uow:
        await uow.servers.upsert(GameServer(1, "S1 - Teste", "local_0001", "127.0.0.1", 8080, 5000, datetime.now(UTC)))
        await uow.commit()
    yield db
    await db.dispose()


@pytest.fixture
def uow_factory(database: Database) -> Callable[[], SqlAlchemyUnitOfWork]:
    return lambda: SqlAlchemyUnitOfWork(database.sessions)


class Portal:
    """Faz o papel do portal PHP: grava contas e tickets direto no banco."""

    def __init__(self, uow_factory: Callable[[], SqlAlchemyUnitOfWork]) -> None:
        self._uow = uow_factory

    async def account(self, username: str) -> Account:
        async with self._uow() as uow:
            account = await uow.accounts.add(Account(username, "$2y$10$hash-do-php", datetime.now(UTC)))
            await uow.commit()
            return account

    async def ticket(self, account_id: int, server_id: int = 1, now: datetime | None = None, ttl: int = 300) -> str:
        now = now or datetime.now(UTC)
        async with self._uow() as uow:
            ticket = await uow.tickets.add(
                PlayTicket(secrets.token_urlsafe(24), account_id, server_id, now, now + timedelta(seconds=ttl))
            )
            await uow.commit()
            return ticket.token


@pytest.fixture
def portal(uow_factory: Callable[[], SqlAlchemyUnitOfWork]) -> Portal:
    return Portal(uow_factory)
