"""recomendação de amigos (15013): desligada como no oficial

``game_settings.friend_recommend``: ``false`` manda o 85 vazio; ``true`` lista os online que não estão na lista.

(visto) oficial_20261023-171155-1 #67/#71, #4214/#4219 e #5847/#5864: o 85 veio vazio as três vezes, com a guilda de 99
membros online no mesmo servidor.

Revision ID: 0070
Revises: 0069
Create Date: 2026-10-24 12:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None

KEY = "friend_recommend"
SOURCE = "(visto) oficial_20261023-171155-1 #71, #4219, #5864: 85 sempre vazio"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(False), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
