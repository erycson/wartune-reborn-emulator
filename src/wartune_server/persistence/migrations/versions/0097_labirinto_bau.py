"""Forgotten Catacombs: o ``chest`` de ``game_settings.maze`` vira o baú visto no andar 5

A linha de 0087 guarda o baú inventado (2050201 x2). O baú visto nas capturas do andar 5 (4205, 24/10 #12439) é
2050701 x2 e 208009 x2; o ``maze.DEFAULT`` usa o mesmo para os andares sem captura. Os andares 5, 10, 15 e 20 têm o
próprio baú em ``content/maze_floors.json``: esta linha só vale para os andares 25 em diante.

Revision ID: 0097
Revises: 0092
Create Date: 2026-10-28 16:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0097"
down_revision = "0092"
branch_labels = None
depends_on = None

OLD = [[2050201, 2], [208009, 2]]
NEW = [[2050701, 2], [208009, 2]]


def _set_chest(chest: list[list[int]]) -> None:
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT value FROM game_settings WHERE key = 'maze'")).first()
    if row is None:
        return
    value = json.loads(row[0]) | {"chest": chest}
    conn.execute(sa.text("UPDATE game_settings SET value = :v WHERE key = 'maze'"), {"v": json.dumps(value)})


def upgrade() -> None:
    _set_chest(NEW)


def downgrade() -> None:
    _set_chest(OLD)
