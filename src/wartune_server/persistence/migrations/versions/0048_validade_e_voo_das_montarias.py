"""validade e voo das montarias

``player_systems.mount_expiry``: o fim das montarias temporárias (carta de montaria com ``Property2`` dias,
``AvatarInfoMsg.expairDate``; sem entrada = permanente). ``player_systems.mount_fly``: as montarias que ganharam voo
com a Flystone (8529 op 13, ``AvatarInfoMsg.isBuyFly``).

Revision ID: 0048
Revises: 0047
Create Date: 2026-10-21 02:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("player_systems") as batch:
        batch.add_column(sa.Column("mount_expiry", sa.String(1024), server_default="", nullable=False))
        batch.add_column(sa.Column("mount_fly", sa.String(1024), server_default="", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("player_systems") as batch:
        batch.drop_column("mount_fly")
        batch.drop_column("mount_expiry")
