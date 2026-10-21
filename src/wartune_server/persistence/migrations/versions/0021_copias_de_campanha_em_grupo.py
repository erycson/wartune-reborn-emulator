"""entradas de campanha em grupo (4240) e o dia delas

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-17 21:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("multi_copy_count", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("multi_copy_max", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("multi_copy_day", sa.String(length=10), server_default="", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.drop_column("multi_copy_day")
        batch_op.drop_column("multi_copy_max")
        batch_op.drop_column("multi_copy_count")
