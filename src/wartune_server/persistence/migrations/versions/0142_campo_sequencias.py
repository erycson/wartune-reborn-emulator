"""taxas do campo: frases de sequência de abates, onda de renascer e passo do exército

field_streaks: abates seguidos sem morrer -> frase (152321: Kawaii spree no 3º #9968, dominating no 4º #10068,
unstoppable no 5º e 6º #10225/#10965, yasuo god no 7º #11022, reaper do 8º em diante #11460/#11620). field_streak_stop
4: VRIES em `dominating` (#10533) morto por Kawaii gerou o `has put a stop to` (#10966); TODO(inventado) se 3
também gera (um caso). field_respawn_period 30: os tempos de morte vistos (0, 5, 10, 20, 25, 30 s) cabem numa onda
de 30 s; TODO(inventado) a origem da onda (aqui a abertura). field_move_speed 10 casas/s: 13 casas em 1,35 s
(121453 #10203 -> #10205); TODO(inventado) aproximado, e o meio-passo de quem carrega não entra.

Revision ID: 0142
Revises: 0141
Create Date: 2026-10-29 23:30:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0142"
down_revision = "0141"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {
    "field_streaks": [[3, "spree"], [4, "dominating"], [5, "unstoppable"], [7, "god"], [8, "reaper"]],
    "field_streak_stop": 4,
    "field_respawn_period": 30,
    "field_move_speed": 10,
}
SOURCES = {
    "field_streaks": "(visto) 152321 #9968 #10068 #10225 #11022 #11460",
    "field_streak_stop": "(visto) 152321 #10966; TODO(inventado) um caso",
    "field_respawn_period": "(visto) mortes de 0 a 30 s; TODO(inventado) a origem da onda",
    "field_move_speed": "(visto) 121453 #10203-#10205 ~9,6 casas/s; TODO(inventado) aproximado",
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
