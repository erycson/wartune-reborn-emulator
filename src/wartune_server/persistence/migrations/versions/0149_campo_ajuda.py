"""taxas do campo de batalha pela ajuda do cliente (``worldboss.view.BaseHelpFrame.BattleHelpContent``)

(cliente) "If the score gap between the two sides reaches 5000 points, the battle ends early" -> ``field_score_gap``;
"defeating players or guards from the enemy side will increase both side and individual scores" ->
``field_guardian_points``: quanto vale o guardião vencido é TODO(inventado) (vitória sem pontos vistos; 20 = a base
do ganho no PvP).

Revision ID: 0149
Revises: 0148
Create Date: 2026-11-01 20:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0149"
down_revision = "0148"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {"field_score_gap": 5000, "field_guardian_points": 20}
SOURCES = {
    "field_score_gap": "(cliente) language.txt BattleHelpContent: a diferença de 5000 encerra antes",
    "field_guardian_points": "TODO(inventado): a ajuda diz que o guardião vencido soma; o valor não foi visto",
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
        for k in NEW:
            data.pop(k, None)
            data.get("source", {}).pop(k, None)
        _save(conn, data)
