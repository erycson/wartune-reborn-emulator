"""despertar do mascote: ``heroes.awake``

O valor do 4600 (``AwakeMsg``) passa de uma luta para outra: o 157 da luta seguinte traz o herói com ``awake`` 3000
(visto peri_uyanis #50). Teto 3000 no cliente (``HeroRoleInfo.updateAwaken``).

Revision ID: 0080
Revises: 0079
Create Date: 2026-10-24 23:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("heroes") as batch_op:
        batch_op.add_column(sa.Column("awake", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("heroes") as batch_op:
        batch_op.drop_column("awake")
