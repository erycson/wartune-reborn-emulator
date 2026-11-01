"""taxas.field_respawn_period 30 -> 35: a onda de renascer do campo conferida na captura de 01/11

(visto) 20261101-165308-1, campo 4003 (13:00): os renascimentos (4175 state 0/2 depois do 1/3) de três exércitos
caem numa grade só de ~35,3 s (96,0, 166,6, 201,9, 273,6, 484,3, 590,2, 1084,4 e 1190,4 s desde a entrada; dois
mortos em momentos diferentes renascem juntos em 273,6) e o ``leftTime`` da morte é o tempo até a próxima onda,
arredondado para baixo a 5 s (30, 15, 5, 5, 25, 5, 25, 20 e 0). Com 30 s a grade não fecha. A fase (desde a
abertura) segue TODO(inventado).

Revision ID: 0147
Revises: 0146
Create Date: 2026-11-01 18:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0147"
down_revision = "0146"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {"field_respawn_period": 35}
OLD: dict[str, Any] = {"field_respawn_period": 30}
SOURCES = {
    "field_respawn_period": "(visto) 20261101-165308-1: renascimentos numa grade de ~35 s; "
    "TODO(inventado) a fase da onda"
}
OLD_SOURCES = {"field_respawn_period": "(visto) mortes de 0 a 30 s; TODO(inventado) a origem da onda"}


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


def _apply(values: dict[str, Any], sources: dict[str, str]) -> None:
    conn = op.get_bind()
    if (data := _load(conn)) is not None:
        data |= values
        data.setdefault("source", {}).update(sources)
        _save(conn, data)


def upgrade() -> None:
    _apply(NEW, SOURCES)


def downgrade() -> None:
    _apply(OLD, OLD_SOURCES)
