"""guarda de batalha

``player_systems.battle_guard``: encaixes abertos da guarda de batalha e as gemas neles ("2:1:3120101:0:0"), do
8742 (``PlayerManager.sendOpenBattleItem``/``sendAddBattleGem``/``sendRemoveBattleGem``) e do 4631.

Revision ID: 0106
Revises: 0105
Create Date: 2026-10-28 18:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0106"
down_revision = "0105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("player_systems") as batch:
        batch.add_column(sa.Column("battle_guard", sa.String(255), server_default="", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("player_systems") as batch:
        batch.drop_column("battle_guard")
