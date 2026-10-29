"""PvP entre servidores como fila local: o prêmio dos pontos (``game_settings.cross_score``)

``{"min_points": 1000, "top": 20, "mark": [[templateId, quantidade], ...]}``, resgatado no 8590
(``handlers/arena.py``). (cliente) ``pvpHeroFrame.rewardTip``: 1000 pontos dão a Warrior's Mark; top 20 com 1000,
o título. TODO(inventado): a Warrior's Mark não existe nos templates (grep sem resultado); vai Insignia x1 (208001).

Revision ID: 0121
Revises: 0118
Create Date: 2026-10-29 18:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0121"
down_revision = "0119"
branch_labels = None
depends_on = None

KEY = "cross_score"
SOURCE = "(cliente) pvpHeroFrame.rewardTip 1000 pontos / top 20; TODO(inventado) Warrior's Mark = Insignia x1"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    value = {"min_points": 1000, "top": 20, "mark": [[208001, 1]]}
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(value), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
