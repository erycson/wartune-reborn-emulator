"""janela do PvP

``game_settings.pvp_match``: horas (no fuso do jogo) em que o PvP abre e quanto dura, em segundos. O 8294 responde
se está aberto agora e o 20008 manda o 4201 sozinho quando abre ou fecha. (visto) oficial_20261023-153200-1 #2231:
4201 ``true`` às 12:00 do jogo, sem pedido; (dedução) a duração de 1 hora, sem fonte (nem o fechamento na captura).

Revision ID: 0060
Revises: 0059
Create Date: 2026-10-23 23:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None

KEY = "pvp_match"
SOURCE = "(visto) oficial_20261023-153200-1 #2231: abre às 12:00; (dedução) dura 1 hora"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    value = json.dumps({"hours": [12], "duration": 3600})
    op.bulk_insert(settings, [{"key": KEY, "value": value, "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
