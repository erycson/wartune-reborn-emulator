"""fuso do jogo de cada servidor (game_servers.timezone), mostrado na lista de servidores do portal

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-18 18:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("game_servers") as batch:
        batch.add_column(sa.Column("timezone", sa.String(length=64), server_default="UTC", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("game_servers") as batch:
        batch.drop_column("timezone")
