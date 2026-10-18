"""compras dos jogadores (purchases): loja, poção, loja misteriosa e mercado, com o item e o preço do momento

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-18 13:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="", nullable=False),
        sa.Column("good_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=32), server_default="", nullable=False),
        sa.Column("price", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", UTCDateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_purchases_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchases")),
    )
    op.create_index(op.f("ix_purchases_character_id"), "purchases", ["character_id"], unique=False)
    op.create_index(op.f("ix_purchases_template_id"), "purchases", ["template_id"], unique=False)
    op.create_index(op.f("ix_purchases_created_at"), "purchases", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchases_created_at"), table_name="purchases")
    op.drop_index(op.f("ix_purchases_template_id"), table_name="purchases")
    op.drop_index(op.f("ix_purchases_character_id"), table_name="purchases")
    op.drop_table("purchases")
