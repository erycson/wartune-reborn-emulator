"""Wishing Wall do Sky Trails (``game_settings.wishing_wall``, ``handlers/wishwall.py``)

``{"prizes": [[templateId, quantidade, peso], ...8], "costs": [Balens da 1ª carta, da 2ª, ...]}``.
(cliente) 8 cartas (``SinglePassBugleView`` pos_1..pos_8), a 1ª sem Balens (``_currentPointsCost`` começa em 0).
TODO(inventado): sem captura nem tabela nos templates; prêmios tirados dos BossReward/AreaReward do próprio Sky
Trails (Star Sand, Star Tear, ouro, Kyanite, Daru), pesos e custos inventados.

Revision ID: 0122
Revises: 0121
Create Date: 2026-10-29 20:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0122"
down_revision = "0121"
branch_labels = None
depends_on = None

KEY = "wishing_wall"
SOURCE = "(cliente) SinglePassBugleView 8 cartas, 1ª grátis; TODO(inventado) prêmios, pesos e custos"
VALUE = {
    "prizes": [
        [2125057, 10, 30],  # Star Sand
        [2125057, 30, 15],
        [2100035, 5, 15],  # Star Tear Shard
        [2125051, 1, 5],  # Star Tear - Fire
        [-100, 300000, 15],  # ouro
        [-600, 20000, 10],  # Kyanite
        [-300, 1000000, 8],  # Daru
        [2125057, 100, 2],
    ],
    "costs": [0, 10, 20, 30, 50, 80, 120, 200],
}


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
