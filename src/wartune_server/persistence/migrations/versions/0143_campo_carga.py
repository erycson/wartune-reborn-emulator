"""taxas.field_carry_speed: fator da velocidade de quem carrega minério no campo

(visto) 152321 #9958: "Entered resource transport state. Movement speed is now decreased by 50%." -> 0,5.

Revision ID: 0143
Revises: 0142
Create Date: 2026-10-29 23:30:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0143"
down_revision = "0142"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {"field_carry_speed": 0.5}
SOURCES = {"field_carry_speed": "(visto) 152321 #9958 decreased by 50%"}


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
