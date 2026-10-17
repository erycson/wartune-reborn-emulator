"""Engine assíncrona para SQLite, MySQL ou PostgreSQL a partir de uma URL."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, event, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .schema import map_entities

SUPPORTED_DRIVERS = {"sqlite+aiosqlite", "mysql+asyncmy", "postgresql+asyncpg"}
MIGRATIONS = Path(__file__).with_name("migrations")
BASELINE = "0001"  # o esquema de antes das migrações (bancos criados pelo create_all)


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

    async def migrate(self) -> None:
        """Leva o banco à última migração. Um banco de antes das migrações é marcado como baseline."""
        async with self.engine.begin() as conn:
            await conn.run_sync(_upgrade)

    async def new_revision(self, message: str) -> None:
        """Gera ``migrations/versions/NNNN_*.py`` comparando o banco (já migrado) com ``schema.py``."""
        number = len(list((MIGRATIONS / "versions").glob("[0-9]*.py"))) + 1
        async with self.engine.begin() as conn:
            await conn.run_sync(
                lambda c: command.revision(_alembic(c), message, autogenerate=True, rev_id=f"{number:04d}")
            )

    async def dispose(self) -> None:
        await self.engine.dispose()


def _alembic(connection: Connection) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    return config


def _upgrade(connection: Connection) -> None:
    config = _alembic(connection)
    tables = set(inspect(connection).get_table_names())
    if "alembic_version" not in tables and "characters" in tables:
        command.stamp(config, BASELINE)
    command.upgrade(config, "head")


def _sqlite_pragmas(dbapi_conn, _record) -> None:  # type: ignore[no-untyped-def]
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")  # leitores não bloqueiam o escritor
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()
