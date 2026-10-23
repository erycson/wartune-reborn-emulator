"""Castelos NPC dos mapas do mundo (1 a 5)

``game_settings.npc_castles``: os 5 castelos NPC vistos no mapa 1 (id, tile, dono, nome e grau do oficial), quantos por
grade nas grades vistas e a vida das 2 pilhas da luta.

(visto) oficial_20261023-153200-1 #197/#1524/#1531/#1532 e oficial_20261023-171155-1 #290: os mesmos 5 nas duas
capturas; #749 e #1893: 2 pilhas de 10112 com 443 de vida no grau 12. (dedução) per_grid = quantos as 45 grades
vistas (``world_mines.seen_grids``) têm. TODO(inventado): os das grades não vistas saem desse sorteio e a vida das
pilhas nos outros graus é ``Live`` × ``hp_factor`` (443 / 422).

Revision ID: 0065
Revises: 0064
Create Date: 2026-10-24 09:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None

KEY = "npc_castles"
SEEN = [
    {"id": 728858, "map": 1, "x": 2454, "y": 2638, "user_id": 1300000013, "name": "Alberthim", "grade": 14},
    {"id": 729056, "map": 1, "x": 2486, "y": 2671, "user_id": 1300000011, "name": "Aladyr", "grade": 12},
    {"id": 732447, "map": 1, "x": 2525, "y": 2569, "user_id": 1300000043, "name": "Barbh", "grade": 14},
    {"id": 736544, "map": 1, "x": 2559, "y": 2596, "user_id": 1300000077, "name": "Calena", "grade": 18},
    {"id": 745995, "map": 1, "x": 2432, "y": 2594, "user_id": 1300000073, "name": "Brochesth", "grade": 14},
]
VALUE = {"seen": SEEN, "per_grid": {"0": 40, "1": 5}, "pawn_hp": {"12": 443}, "hp_factor": 1.05}
SOURCE = (
    "(visto) oficial_20261023-153200-1/171155-1: seen, pawn_hp do grau 12; (dedução) per_grid = quantos castelos NPC "
    "as 45 grades vistas têm; TODO(inventado): os castelos das grades não vistas e hp_factor (443 / 422) "
    "nos outros graus"
)


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
