"""Engine assíncrona para SQLite, MySQL ou PostgreSQL a partir de uma URL."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .schema import map_entities, metadata

SUPPORTED_DRIVERS = {"sqlite+aiosqlite", "mysql+asyncmy", "postgresql+asyncpg"}


class Database:
    def __init__(self, url: str, *, echo: bool = False) -> None:
        parsed = make_url(url)
        if parsed.drivername not in SUPPORTED_DRIVERS:
            raise ValueError(f"driver não suportado: {parsed.drivername} (use um de {sorted(SUPPORTED_DRIVERS)})")
        map_entities()
        kwargs: dict[str, object] = {"echo": echo, "pool_pre_ping": True}
        if parsed.drivername.startswith("sqlite"):
            if parsed.database and parsed.database != ":memory:":
                Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        else:
            kwargs.update(pool_size=10, max_overflow=20, pool_recycle=1800)
        self.engine: AsyncEngine = create_async_engine(parsed, **kwargs)
        if parsed.drivername.startswith("sqlite"):
            event.listen(self.engine.sync_engine, "connect", _sqlite_pragmas)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)

    def session(self) -> AsyncSession:
        return self.sessions()

    async def create_schema(self) -> None:
        """Cria as tabelas que faltam. Em produção prefira ``alembic upgrade head``."""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()


def _sqlite_pragmas(dbapi_conn, _record) -> None:  # type: ignore[no-untyped-def]
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")  # leitores não bloqueiam o escritor
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()
