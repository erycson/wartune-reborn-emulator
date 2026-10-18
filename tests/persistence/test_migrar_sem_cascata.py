"""Migrar um banco com jogadores não pode apagar nada (a 0029 recriou ``characters`` e o DROP apagou em cascata)."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Connection, inspect

from wartune_server.persistence.database import Database, _upgrade


def _fill(conn: Connection, table: str, values: dict[str, object]) -> None:
    """Insere uma linha com ``values`` e um valor qualquer nas colunas obrigatórias sem default."""
    row = dict(values)
    for col in inspect(conn).get_columns(table):
        if col["name"] in row or col["nullable"] or col.get("default") is not None or col.get("autoincrement") is True:
            continue
        if col["name"] == "id":
            continue
        kind = str(col["type"]).upper()
        row[col["name"]] = (
            datetime.now(UTC).isoformat(" ") if "DATE" in kind or "TIME" in kind
            else 0 if any(k in kind for k in ("INT", "BOOL", "FLOAT", "NUMERIC")) else ""
        )  # fmt: skip
    cols = ", ".join(row)
    conn.exec_driver_sql(f"INSERT INTO {table} ({cols}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))


async def test_migrar_ate_o_fim_nao_apaga_herois_nem_castelo(tmp_path: Path) -> None:
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'velho.db'}")
    try:

        def old(conn: Connection) -> None:
            _upgrade(conn, "0028")
            _fill(conn, "game_servers", {"id": 1})
            _fill(conn, "accounts", {"id": 1, "username": "velho"})
            _fill(conn, "characters", {"id": 1, "account_id": 1, "server_id": 1, "nickname": "Velho"})
            _fill(conn, "heroes", {"id": 1, "character_id": 1})
            _fill(conn, "castles", {"id": 1, "character_id": 1})

        async with db.engine.begin() as conn:
            await conn.run_sync(old)
        await db.engine.dispose()
        await db.migrate()  # 0029 em diante: recria characters
        async with db.engine.connect() as conn:
            counts = [
                (await conn.exec_driver_sql(f"SELECT count(*) FROM {t}")).scalar()
                for t in ("characters", "heroes", "castles")
            ]
            assert counts == [1, 1, 1]
            assert (await conn.exec_driver_sql("PRAGMA foreign_keys")).scalar() == 1  # conexão nova: ligadas de novo
    finally:
        await db.dispose()
