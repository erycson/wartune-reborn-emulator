"""virada do dia do jogo (5h): o dia já aplicado e a stamina tomada em poções no dia

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-18 20:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("characters") as batch:
        batch.add_column(sa.Column("reset_day", sa.String(length=10), server_default="", nullable=False))
        batch.add_column(sa.Column("weary_potions", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("weary_potions")
        batch.drop_column("reset_day")
