"""minas de ouro ocupadas e castelo no ponto do tutorial

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-17 18:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wild_lands",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("wild_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("occupied_at", UTCDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_wild_lands_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wild_lands")),
        sa.UniqueConstraint("character_id", "wild_id", name=op.f("uq_wild_lands_character_id_wild_id")),
    )
    with op.batch_alter_table("wild_lands", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_wild_lands_character_id"), ["character_id"], unique=False)
    # castelos ainda no ponto da grade antiga (GridCastlePlacement 10,10 + 4n) vão para o ponto do
    # oficial, (26,46): o guia do tutorial procura o castelo no pixel (520,920)
    op.execute(
        "UPDATE castles SET pos_x = 26, pos_y = 46 WHERE map_id = 100000313 "
        "AND pos_x >= 10 AND pos_y >= 10 AND (pos_x - 10) % 4 = 0 AND (pos_y - 10) % 4 = 0"
    )


def downgrade() -> None:
    with op.batch_alter_table("wild_lands", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_wild_lands_character_id"))
    op.drop_table("wild_lands")
