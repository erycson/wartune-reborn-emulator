"""ciclo de 12 h das minas do castelo (castles.mines_at)

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-17 21:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # vazio = castelo de antes: o primeiro refresh começa o ciclo na ocupação mais velha (outer_city.cycle_start)
    with op.batch_alter_table("castles", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mines_at", UTCDateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("castles", schema=None) as batch_op:
        batch_op.drop_column("mines_at")
