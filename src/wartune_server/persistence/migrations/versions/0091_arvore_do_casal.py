"""Árvore do casal: o estado em JSON nas duas linhas de ``marriages`` (``game/marriage_tree.py``)

Revision ID: 0091
Revises: 0090
Create Date: 2026-10-25 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0091"
down_revision = "0090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tree", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.drop_column("tree")
