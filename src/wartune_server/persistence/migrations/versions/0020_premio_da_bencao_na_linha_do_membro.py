"""prêmio da bênção pendente fica na linha do membro (antes só na memória)

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-17 19:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = '0020'
down_revision = '0019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consortia_members", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bless_item", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("bless_item_count", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("consortia_members", schema=None) as batch_op:
        batch_op.drop_column("bless_item_count")
        batch_op.drop_column("bless_item")
