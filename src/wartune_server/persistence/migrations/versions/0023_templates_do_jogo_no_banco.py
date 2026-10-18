"""templates do jogo no banco: o tempinfos.xml nó por nó (template_nodes) e o histórico de importações

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-18 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "template_nodes",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tag", sa.String(length=64), server_default="", nullable=False),
        sa.Column("key_name", sa.String(length=64), nullable=True),
        sa.Column("row_key", sa.String(length=64), nullable=True),
        sa.Column("attrs", sa.Text(), server_default="", nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["template_nodes.id"],
            name=op.f("fk_template_nodes_parent_id_template_nodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_template_nodes")),
    )
    op.create_index(op.f("ix_template_nodes_parent_id"), "template_nodes", ["parent_id"], unique=False)
    op.create_index(op.f("ix_template_nodes_row_key"), "template_nodes", ["row_key"], unique=False)
    op.create_table(
        "template_imports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.Column("sha256", sa.String(length=64), server_default="", nullable=False),
        sa.Column("nodes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("imported_at", UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_template_imports")),
    )


def downgrade() -> None:
    op.drop_table("template_imports")
    op.drop_index(op.f("ix_template_nodes_row_key"), table_name="template_nodes")
    op.drop_index(op.f("ix_template_nodes_parent_id"), table_name="template_nodes")
    op.drop_table("template_nodes")
