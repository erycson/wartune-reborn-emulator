"""taxas.field_ore_weights: qualidade do minério da coleta do campo de batalha

A qualidade sai na coleta, não no nó: o mesmo 4007007 deu inferior, superior e normal (152321 #14517, #14611,
#15122). Pesos = a contagem das 26 entregas vistas (152321 4005/4007 e 121453 4002): superior 12, normal 5,
inferior 9. TODO(inventado): a chance real não está no cliente.

Revision ID: 0140
Revises: 0139
Create Date: 2026-10-29 23:30:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0140"
down_revision = "0139"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {"field_ore_weights": {"superior": 12, "normal": 5, "inferior": 9}}
SOURCES = {"field_ore_weights": "(visto) contagem das entregas 152321 e 121453; TODO(inventado): a chance real"}


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
