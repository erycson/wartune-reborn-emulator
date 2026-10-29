"""taxas.card_burn_gp: EXP de cada carta repetida engolida (9505 op 3)

O cliente diz que a carta sobe engolindo a do mesmo tipo (ajuda "burn the same kind", idioma
card.cardHelper.content01) e corta o gp no Data do grau seguinte (MagicCardInfo.currentGP), mas não diz quanto
cada uma vale: ``TODO(inventado)`` 1.

Revision ID: 0139
Revises: 0138
Create Date: 2026-10-29 23:30:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0139"
down_revision = "0138"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {"card_burn_gp": 1}
SOURCES = {"card_burn_gp": "TODO(inventado): o cliente não diz a EXP por carta engolida (MagicCardManager/ajuda)"}


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
