"""ponto de chegada do castelo mudado para outro mapa (``game/outer_city.py``, ``LANDING``)

``castle_landing``: mapa -> [x, y] da âncora; o castelo cai no tile livre mais próximo dela. Vistos no 105 do
5176 inglês: mapa 2 em 2084,1953 (oficial_20261024-191924-1 #15693) e mapa 3 em 1229,1103
(oficial_20261027-152321-1 #18053). Sem entrada, o centro do mapa.

Revision ID: 0114
Revises: 0113
Create Date: 2026-10-30 00:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0114"
down_revision = "0113"
branch_labels = None
depends_on = None

settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
VALUE = {"2": [2084, 1953], "3": [1229, 1103]}
SOURCE = "captura inglesa: 105 de oficial_20261024-191924-1 #15693 e oficial_20261027-152321-1 #18053"


def upgrade() -> None:
    op.bulk_insert(settings, [{"key": "castle_landing", "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    op.execute(settings.delete().where(settings.c.key == "castle_landing"))
