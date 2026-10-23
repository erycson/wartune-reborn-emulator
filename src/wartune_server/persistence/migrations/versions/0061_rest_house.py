"""teto diário da Rest House

``game_settings.rest_house``: ``daily`` = estamina que as salas do gancho (Altar of Ennoblement, 7001-7009) dão por
dia (``handlers/hangup.py``). Sem fonte: o cliente não traz o número (``DataResetMsg.leftHangupWeary`` existe, mas
ninguém lê) e nenhuma captura entrou na sala.

Revision ID: 0061
Revises: 0060
Create Date: 2026-10-23 23:59:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None

KEY = "rest_house"
SOURCE = "TODO(inventado): sem fonte no cliente, na captura ou na internet"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps({"daily": 50}), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
