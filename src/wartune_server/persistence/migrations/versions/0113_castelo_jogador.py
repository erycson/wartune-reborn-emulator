"""ataque a castelo de jogador: saque e proteção depois de vencido (``handlers/outer_city.py``, ``PLAYER_CASTLE``)

``player_castle``: TODO(inventado) nenhuma captura tem o ataque a castelo de jogador; ``loot_pct`` = % do ouro do
dono que vai para quem vence e ``shield_seconds`` = proteção do castelo vencido (as 2 h do castelo NPC, visto).

Revision ID: 0113
Revises: 0112
Create Date: 2026-10-29 23:59:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0113"
down_revision = "0112"
branch_labels = None
depends_on = None

settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
VALUE = {"loot_pct": 10, "shield_seconds": 7200}
SOURCE = "TODO(inventado) loot_pct; shield_seconds = as 2 h do castelo NPC (npc_castles, visto)"


def upgrade() -> None:
    op.bulk_insert(settings, [{"key": "player_castle", "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    op.execute(settings.delete().where(settings.c.key == "player_castle"))
