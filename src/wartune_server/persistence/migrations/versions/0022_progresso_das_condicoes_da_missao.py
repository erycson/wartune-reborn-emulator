"""progresso das condições extras da missão (condition_2..4): missões com mais de uma linha em QuestCondictionInfos

Revision ID: 0022
Revises: 0020
Create Date: 2026-10-17 20:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quests", schema=None) as batch_op:
        for name in ("progress_2", "progress_3", "progress_4"):
            batch_op.add_column(sa.Column(name, sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("quests", schema=None) as batch_op:
        for name in ("progress_4", "progress_3", "progress_2"):
            batch_op.drop_column(name)
