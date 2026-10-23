"""time box

``game_settings.time_box``: regra da caixa de tempo online (5019 / 4 / 4250). ``count_offline``: depois do primeiro
período a corrente conta também o tempo fora; ``daily_reset``: recomeça no dia novo do jogo (05:00).

Revision ID: 0056
Revises: 0055
Create Date: 2026-10-23 20:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None

KEY = "time_box"
RULE = {"count_offline": True, "daily_reset": False}
SOURCE = (
    "(visto, amostra única) oficial_encantar #131: no login time 10 e timerun 40009 "
    "(11 h fora, atravessando as 05:00); "
    "tutorial_en #1594-#1598: conta nova só começa no primeiro 5019"
)


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(RULE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
