"""estrela das montarias

``player_systems.mount_stars``: estrela e bênção de cada montaria ("1000:2:30"), do refino da estrela (8529 op 6,
``MountsPromotionView``; ``AvatarInfoMsg.starLevel`` e ``blessing``).

Revision ID: 0050
Revises: 0049
Create Date: 2026-10-21 03:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("player_systems") as batch:
        batch.add_column(sa.Column("mount_stars", sa.String(1024), server_default="", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("player_systems") as batch:
        batch.drop_column("mount_stars")
