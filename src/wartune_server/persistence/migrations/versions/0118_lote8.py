"""lote 8: treino de mascote na fazenda e Venus Crystal pela missão do casal

``farm_pet_practice``: terras de mascote da fazenda (15044 ops 12-16, ``handlers/farm_pets.py``). O cliente dá as
2 terras, o nível 50, as 10 partes e as 5 comidas, mas não as horas nem a EXP. TODO(inventado): 12 h, 1000 de EXP
por hora e +10% por comida.

``venus_crystal_sources``: o Venus Crystal (``eternalCrystal``) só vinha da Venus Battle, que é entre servidores.
TODO(inventado): 5 por missão do casal entregue (8774).

Revision ID: 0118
Revises: 0117
Create Date: 2026-10-29 12:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0118"
down_revision = "0117"
branch_labels = None
depends_on = None

settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
ROWS = [
    {
        "key": "farm_pet_practice",
        "value": json.dumps({"hours": 12, "gp_per_hour": 1000, "feed_pct": 10}),
        "source": "TODO(inventado): horas, EXP por hora e % por comida do treino de mascote na fazenda (sem captura)",
    },
    {
        "key": "venus_crystal_sources",
        "value": json.dumps({"couple_task": 5}),
        "source": "TODO(inventado): Venus Crystal local por missão do casal (a Venus Battle é entre servidores)",
    },
]


def upgrade() -> None:
    op.bulk_insert(settings, ROWS)


def downgrade() -> None:
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
