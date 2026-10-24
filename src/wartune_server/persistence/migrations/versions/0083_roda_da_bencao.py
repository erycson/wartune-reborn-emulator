"""roda da bênção: ``game_settings.seminary_bless_gain``

(cliente) SeminaryBlessFrame: cada giro mostra um número e a bênção só sobe; (só turco: city_city_upgrade #140) o 1º
giro do dia foi de 10 para 50. TODO(inventado): o quanto sobe, sorteado entre os dois números (média 40, o visto).

Revision ID: 0083
Revises: 0082
Create Date: 2026-10-24 08:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None

KEY = "seminary_bless_gain"
SOURCE = "(só turco: city_city_upgrade #140) 10 -> 50 no 1º giro; TODO(inventado) o sorteio entre 10 e 70"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps([10, 70]), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
