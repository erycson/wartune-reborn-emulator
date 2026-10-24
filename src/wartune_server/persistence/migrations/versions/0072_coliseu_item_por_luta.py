"""coliseu: o item de cada luta (``game_settings.arena_challenge_items``)

[[templateId, quantidade], ...] que entram na mochila ao fim de cada luta do coliseu (8253).

(visto) oficial_20261023-215937-1 #1168-#1181: depois do 4176, VIP Token x1 (208015) com 115, 111 e 83
"Received: VIP Token x1"; o jogador não era VIP. TODO(inventado): uma luta só (vitória), não se sabe se a derrota
também dá, se é sorteio ou se tem limite por dia.

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
SOURCE = "(visto) oficial_20261023-215937-1 #1168-#1181: VIP Token x1 depois da luta; TODO(inventado) a regra"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps([[208015, 1]]), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
