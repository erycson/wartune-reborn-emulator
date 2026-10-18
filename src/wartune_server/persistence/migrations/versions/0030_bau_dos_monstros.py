"""baú dos monstros dos Wilds: a tabela de queda (o que cai, com que chance e quanto) e os baús fechados

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-18 15:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

# (boss_type, min_level, max_level, template_id, chance, min_count, max_count, source)
DROPS: list[tuple[int, int, int, int, float, int, int, str]] = []


def _int(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), server_default="0", nullable=False)


def upgrade() -> None:
    drops = op.create_table(
        "world_monster_drops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _int("boss_type"),
        _int("min_level"),
        _int("max_level"),
        _int("template_id"),
        sa.Column("chance", sa.Float(), nullable=False),
        _int("min_count"),
        _int("max_count"),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_monster_drops")),
    )
    keys = ("boss_type", "min_level", "max_level", "template_id", "chance", "min_count", "max_count", "source")
    op.bulk_insert(drops, [dict(zip(keys, row, strict=True)) for row in DROPS])
    op.create_table(
        "wild_boxes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        _int("map_id"),
        _int("pos_x"),
        _int("pos_y"),
        _int("boss_type"),
        _int("grade"),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_wild_boxes_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wild_boxes")),
    )
    op.create_index(op.f("ix_wild_boxes_character_id"), "wild_boxes", ["character_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wild_boxes_character_id"), table_name="wild_boxes")
    op.drop_table("wild_boxes")
    op.drop_table("world_monster_drops")
