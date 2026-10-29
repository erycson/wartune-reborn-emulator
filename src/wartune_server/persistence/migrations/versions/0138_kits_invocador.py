"""taxas.summoner_kits: raridade das cartas de cada kit de invocador

A raridade é ``ItemTempInfos.Profile`` das cartas (SonType 600). As descrições dos kits dizem qual é a "high chance"
e qual a "lower chance" (Novice: comum/incomum, Expert: incomum/rara, Master: rara/épica). O peso 80/20 não está
no cliente: ``TODO(inventado)``, do tamanho visto na captura 20261029-121453-1 #4026 (5 Expert -> 4 incomuns e 1
rara).

Revision ID: 0138
Revises: 0137
Create Date: 2026-10-29 23:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0138"
down_revision = "0137"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {
    "summoner_kits": {"2131016": [[1, 80], [2, 20]], "2131017": [[2, 80], [3, 20]], "2131018": [[3, 80], [4, 20]]}
}
SOURCES = {
    "summoner_kits": "raridades: ItemTempInfos.Description 2131016-2131018; peso 80/20 TODO(inventado) "
    "(captura 20261029-121453-1 #4026: 4 de 5 na 'high chance')"
}


def _settings() -> Any:
    return sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _load(conn: sa.Connection) -> dict[str, Any] | None:
    s = _settings()
    row = conn.execute(sa.select(s.c.value).where(s.c.key == "taxas")).first()
    if row is None:
        return None
    return dict(row[0] if isinstance(row[0], dict) else json.loads(row[0]))


def _save(conn: sa.Connection, value: dict[str, Any]) -> None:
    s = _settings()
    conn.execute(s.update().where(s.c.key == "taxas").values(value=json.dumps(value)))


def upgrade() -> None:
    conn = op.get_bind()
    if (data := _load(conn)) is not None:
        data |= NEW
        data.setdefault("source", {}).update(SOURCES)
        _save(conn, data)


def downgrade() -> None:
    conn = op.get_bind()
    if (data := _load(conn)) is not None:
        for key in NEW:
            data.pop(key, None)
            data.get("source", {}).pop(key, None)
        _save(conn, data)
