"""Prêmio do Treasure Cache: equipamento de qualquer classe e Profile 1 ou 2

(visto) oficial_20261023-171155-1: 4 baús vencidos por um mago, 1 pedra (Lvl. 3 Luck Stone, #661) e 3 equipamentos:
Elders Robe (Job 3, Profile 2, #1803), Lunalurite Staff (Job 3, Profile 2, #8047) e Pagaentro Necklace (Job 0,
Profile 1, #8586). O colar não cabia na regra de 0063 (só a classe e Profile 2). Pesos 1 : 3 = a proporção vista.

Revision ID: 0088
Revises: 0087
Create Date: 2026-10-24 14:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0088"
down_revision = "0087"
branch_labels = None
depends_on = None

KEY = "treasure_caches"
settings = sa.table("game_settings", sa.column("key"), sa.column("value"))
NEW: dict[str, object] = {
    "stone_weight": 1,
    "gear_weight": 3,
    "gear_profiles": [1, 2],
    "gear_below": 5,
    "gear_above": 2,
}
OLD: dict[str, object] = {"stone_weight": 1, "gear_weight": 1, "gear_profile": 2, "gear_below": 5, "gear_above": 2}


def _set(loot: dict[str, object]) -> None:
    row = op.get_bind().execute(sa.select(settings.c.value).where(settings.c.key == KEY)).first()
    if row is None:
        return
    value = json.loads(row[0])
    value["loot"] = loot
    op.execute(settings.update().where(settings.c.key == KEY).values(value=json.dumps(value)))


def upgrade() -> None:
    _set(NEW)


def downgrade() -> None:
    _set(OLD)
