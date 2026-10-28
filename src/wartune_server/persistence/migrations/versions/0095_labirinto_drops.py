"""Forgotten Catacombs: o ``drops`` de ``game_settings.maze`` vira vazio

A linha de 0087 dava Minor HP Pack x2 em todos os andares (turco, yeralti #69). Nas capturas novas (24/10 #12181 a
#13269) as vitórias dos andares 1 a 15 dão só EXP no 4103; nenhum item de monstro. Os andares 21 e 22 têm loot depois
do 4103, mas não dá para atribuir a um monstro: segue TODO.

Revision ID: 0095
Revises: 0094
Create Date: 2026-10-28 18:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0095"
down_revision = "0094"
branch_labels = None
depends_on = None

OLD = [[2090101, 2, 1.0]]
NEW: list[list[int | float]] = []


def _set_drops(drops: list[list[int | float]]) -> None:
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT value FROM game_settings WHERE key = 'maze'")).first()
    if row is None:
        return
    value = json.loads(row[0]) | {"drops": drops}
    conn.execute(sa.text("UPDATE game_settings SET value = :v WHERE key = 'maze'"), {"v": json.dumps(value)})


def upgrade() -> None:
    _set_drops(NEW)


def downgrade() -> None:
    _set_drops(OLD)
