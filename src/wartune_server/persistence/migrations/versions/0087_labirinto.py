"""Forgotten Catacombs: ``game_settings.maze``

As regras dos andares gerados (``game/maze.py``): andares, EXP por andar, entradas do dia, drop, baú, chave do lucro
dobrado, custo de reviver e o andar mínimo da varredura. Fontes no ``maze.DEFAULT``: (só turco: yeralti_labirenti,
labirent_sandik) a EXP, as entradas, o drop do 8002 e o baú do andar 5; (cliente) MazeFrame, MazeRiverView,
MazeMopupPrepareFrame; TODO(inventado) o drop e o baú iguais em todos os andares.

Revision ID: 0087
Revises: 0086
Create Date: 2026-10-24 15:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0087"
down_revision = "0086"
branch_labels = None
depends_on = None

KEY = "maze"
SOURCE = "(só turco: yeralti_labirenti, labirent_sandik) EXP 400/andar, 1 entrada, baú do andar 5; (cliente) o resto"
VALUE = {
    "floors": 100,
    "gp_per_floor": 400,
    "free_enter": 1,
    "max_enter": 1,
    "drops": [[2090101, 2, 1.0]],
    "chest": [[2050201, 2], [208009, 2]],
    "chest_every": 5,
    "key": 208008,
    "revive": 25,
    "sweep_from": 10,
}


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
