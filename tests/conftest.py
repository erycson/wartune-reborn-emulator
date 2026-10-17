from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime

import pytest

from wartune_server.domain.models import GameServer
from wartune_server.persistence.database import Database
from wartune_server.persistence.repositories import SqlAlchemyUnitOfWork


@pytest.fixture
async def database(tmp_path) -> AsyncIterator[Database]:  # type: ignore[no-untyped-def]
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await db.create_schema()
    async with SqlAlchemyUnitOfWork(db.sessions) as uow:
        await uow.servers.upsert(
            GameServer(1, "S1 - Teste", "local_0001", "127.0.0.1", 8080, 5000, datetime.now(UTC))
        )
        await uow.commit()
    yield db
    await db.dispose()


@pytest.fixture
def uow_factory(database: Database) -> Callable[[], SqlAlchemyUnitOfWork]:
    return lambda: SqlAlchemyUnitOfWork(database.sessions)
