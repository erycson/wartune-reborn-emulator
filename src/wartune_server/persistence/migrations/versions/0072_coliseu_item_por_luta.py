"""coliseu: o item de cada luta (``game_settings.arena_challenge_items``)

Um item sorteado de ``pool`` ([[templateId, quantidade], ...]) entra na mochila ao fim da luta do coliseu (8253);
``win_only`` e ``daily`` (vezes por dia, 0 = sem limite).

Depois do 4176 de uma vitória (a 1ª do dia): (visto) oficial_20261023-215937-1 #1168-#1181 VIP Token x1 (208015);
(só turco: meydan_okuma #30-#45) Lvl. 3 Luck Stone x1 (2040103). TODO(inventado): o resto do conjunto, pesos iguais,
``win_only`` true e ``daily`` 1; nem o cliente nem a internet dizem a regra.

Revision ID: 0072
Revises: 0071
Create Date: 2026-10-24 14:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None

KEY = "arena_challenge_items"
SOURCE = (
    "(visto) oficial_20261023-215937-1 #1168-#1181 VIP Token x1; (só turco) meydan_okuma #30 Lvl. 3 Luck Stone x1; "
    "TODO(inventado) a regra"
)


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    value = {"pool": [[208015, 1], [2040103, 1]], "win_only": True, "daily": 1}
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(value), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
