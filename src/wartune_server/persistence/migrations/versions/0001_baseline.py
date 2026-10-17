"""baseline

Revision ID: 0001
Revises:
Create Date: 2026-10-17 03:38:19.632654
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import wartune_server.persistence.schema

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=True),
        sa.Column("banned", sa.Boolean(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("username", name=op.f("uq_accounts_username")),
    )
    op.create_table(
        "game_servers",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("site", sa.String(length=64), nullable=False),
        sa.Column("public_host", sa.String(length=255), nullable=False),
        sa.Column("http_port", sa.Integer(), nullable=False),
        sa.Column("socket_port", sa.Integer(), nullable=False),
        sa.Column("opened_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=False),
        sa.Column("websocket_port", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rsa_modulus", sa.Text(), server_default="", nullable=False),
        sa.Column("rsa_exponent", sa.String(length=32), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_servers")),
        sa.UniqueConstraint("site", name=op.f("uq_game_servers_site")),
    )
    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("nickname", sa.String(length=32), nullable=True),
        sa.Column("sex", sa.Integer(), server_default="0", nullable=False),
        sa.Column("camp", sa.Integer(), server_default="1", nullable=False),
        sa.Column("job", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("grades", sa.Integer(), server_default="1", nullable=False),
        sa.Column("gp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_gp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gift_token", sa.Integer(), server_default="0", nullable=False),
        sa.Column("weary", sa.Integer(), server_default="200", nullable=False),
        sa.Column("weary_limit", sa.Integer(), server_default="200", nullable=False),
        sa.Column("novice_process", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fighting_capacity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("repute", sa.Integer(), server_default="0", nullable=False),
        sa.Column("geste", sa.Integer(), server_default="0", nullable=False),
        sa.Column("charm", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name=op.f("fk_characters_account_id_accounts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["server_id"], ["game_servers.id"], name=op.f("fk_characters_server_id_game_servers")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_characters")),
        sa.UniqueConstraint("account_id", "server_id", name=op.f("uq_characters_account_id_server_id")),
        sa.UniqueConstraint("server_id", "nickname", name=op.f("uq_characters_server_id_nickname")),
    )
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_characters_account_id"), ["account_id"], unique=False)

    op.create_table(
        "play_tickets",
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("created_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=False),
        sa.Column("expires_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], name=op.f("fk_play_tickets_account_id_accounts"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["server_id"], ["game_servers.id"], name=op.f("fk_play_tickets_server_id_game_servers")
        ),
        sa.PrimaryKeyConstraint("token", name=op.f("pk_play_tickets")),
    )
    with op.batch_alter_table("play_tickets", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_play_tickets_account_id"), ["account_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_play_tickets_expires_at"), ["expires_at"], unique=False)

    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("property1", sa.Integer(), server_default="0", nullable=False),
        sa.Column("property2", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_buildings_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buildings")),
    )
    with op.batch_alter_table("buildings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_buildings_character_id"), ["character_id"], unique=False)

    op.create_table(
        "castles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("map_id", sa.Integer(), nullable=False),
        sa.Column("pos_x", sa.Integer(), nullable=False),
        sa.Column("pos_y", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Integer(), server_default="1", nullable=False),
        sa.Column("energy", sa.Integer(), server_default="500", nullable=False),
        sa.Column("state", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_castles_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_castles")),
        sa.UniqueConstraint("character_id", name=op.f("uq_castles_character_id")),
    )
    op.create_table(
        "heroes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("nickname", sa.String(length=32), nullable=False),
        sa.Column("grades", sa.Integer(), server_default="1", nullable=False),
        sa.Column("gp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("power", sa.Integer(), server_default="0", nullable=False),
        sa.Column("agility", sa.Integer(), server_default="0", nullable=False),
        sa.Column("intellect", sa.Integer(), server_default="0", nullable=False),
        sa.Column("captain", sa.Integer(), server_default="0", nullable=False),
        sa.Column("physique", sa.Integer(), server_default="0", nullable=False),
        sa.Column("power_point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("agility_point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("intellect_point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("captain_point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("physique_point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("remain_point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skill_point", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skill_script", sa.String(length=255), server_default="", nullable=False),
        sa.Column("fast_key", sa.String(length=255), server_default="", nullable=False),
        sa.Column("fight_pos", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_leader", sa.Boolean(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_heroes_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_heroes")),
    )
    with op.batch_alter_table("heroes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_heroes_character_id"), ["character_id"], unique=False)

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("bag_type", sa.Integer(), server_default="1", nullable=False),
        sa.Column("object_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("random_skill", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_new", sa.Boolean(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_items_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_items")),
    )
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_items_character_id"), ["character_id"], unique=False)

    op.create_table(
        "quests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("added_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=False),
        sa.Column("completed_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_quests_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quests")),
        sa.UniqueConstraint("character_id", "template_id", name=op.f("uq_quests_character_id_template_id")),
    )
    with op.batch_alter_table("quests", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_quests_character_id"), ["character_id"], unique=False)


def downgrade() -> None:

    with op.batch_alter_table("quests", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_quests_character_id"))

    op.drop_table("quests")
    with op.batch_alter_table("items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_items_character_id"))

    op.drop_table("items")
    with op.batch_alter_table("heroes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_heroes_character_id"))

    op.drop_table("heroes")
    op.drop_table("castles")
    with op.batch_alter_table("buildings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_buildings_character_id"))

    op.drop_table("buildings")
    with op.batch_alter_table("play_tickets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_play_tickets_expires_at"))
        batch_op.drop_index(batch_op.f("ix_play_tickets_account_id"))

    op.drop_table("play_tickets")
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_characters_account_id"))

    op.drop_table("characters")
    op.drop_table("game_servers")
    op.drop_table("accounts")
