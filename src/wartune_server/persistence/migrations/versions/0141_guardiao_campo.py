"""taxas.field_guardian_range e field_guardian_loss: o guardião do campo de batalha (4002)

(visto) 121453: o guardião 1795 (Paladin Guardian, 72,32) perseguiu o jogador a 24 e 26 casas (4105 #10205 em
96,31 e #10435 em 98,32): TODO(inventado) o alcance, 26 (o maior visto). Quem perde para ele perdeu 150 pontos
(#10362, com 189): TODO(inventado) fixo 150 (um caso só).

Revision ID: 0141
Revises: 0140
Create Date: 2026-10-29 23:30:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0141"
down_revision = "0140"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {"field_guardian_range": 26, "field_guardian_loss": 150}
SOURCES = {
    "field_guardian_range": "(visto) 121453 #10205/#10435 a 24 e 26 casas; TODO(inventado) o alcance",
    "field_guardian_loss": "(visto) 121453 #10362 150 pontos; TODO(inventado) fixo",
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
