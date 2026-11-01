"""taxas do anel (Run Circuit Quest) pela captura 20261101-165308-1 (#9520-#9747, #9986-#10013, #10089)

"Eliminate the monsters in {0}" (tipo 18): o oficial sorteia a masmorra (``condition_2``) e o alvo (``condition_4``):
vistos 1102/30 e 9002/20 -> ``ring_eliminate_targets``; uma rodada de varredura da 1102 somou 18 (#9568-#9575 e
#9687-#9694) -> ``ring_eliminate_per_round`` (TODO(inventado) para as outras masmorras). "Fetch {0}" (tipo 19):
``condition_2`` 2 (guilda) e ``condition_3`` 2013503 (Lvl. 3 Power Potion) -> ``ring_fetch_items``
(TODO(inventado): só um item visto).

Revision ID: 0150
Revises: 0149
Create Date: 2026-11-01 21:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0150"
down_revision = "0149"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {
    "ring_eliminate_targets": [20, 30],
    "ring_eliminate_per_round": 18,
    "ring_fetch_items": [[2, 2013503]],
}
SOURCES = {
    "ring_eliminate_targets": "(visto) 20261101-165308-1 #9521 1102/30 e #10090 9002/20",
    "ring_eliminate_per_round": "(visto) #9568-#9575: 1 rodada da 1102 = 18; TODO(inventado) nas outras",
    "ring_fetch_items": "(visto) #9987 condition_2 2 (guilda), condition_3 2013503; TODO(inventado) os outros",
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
