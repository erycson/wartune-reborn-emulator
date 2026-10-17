"""limite diario de compra no mercado

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-17 20:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mall_spent", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("mall_day", sa.String(length=10), server_default="", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.drop_column("mall_day")
        batch_op.drop_column("mall_spent")
