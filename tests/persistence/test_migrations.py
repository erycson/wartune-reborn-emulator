from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text

from wartune_server.persistence.database import Database
from wartune_server.persistence.schema import metadata


async def test_migrations_match_schema(database: Database) -> None:
    """Mudou ``schema.py``? Rode ``wartune-server db revision "<o quê>"``."""
    async with database.engine.connect() as conn:
        diff = await conn.run_sync(lambda c: compare_metadata(MigrationContext.configure(c), metadata))
    assert diff == []


async def test_database_from_before_migrations_is_stamped(tmp_path: Path) -> None:
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
    async with db.engine.begin() as conn:  # como o create_all deixava
        await conn.run_sync(metadata.create_all)
    await db.migrate()
    async with db.engine.connect() as conn:
        assert (await conn.execute(text("select version_num from alembic_version"))).scalar() is not None
    await db.dispose()
