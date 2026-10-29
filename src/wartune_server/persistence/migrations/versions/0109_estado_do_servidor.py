"""estado do servidor que antes vivia só na memória, e a data de ativação das montarias

``server_states``: uma linha por (servidor, chave), ``text`` em JSON, carregada no arranque
(``persistence/server_state.py``): proteção dos castelos NPC (``shields``), fúria da ilha dos pets (``pet_rage``),
Invasores da terra secreta (``invasions``) e os times livres (``teams``).

``player_systems.mount_since``: quando cada montaria entrou nas possuídas, ``"1000:<segundos Unix>,..."``, o
``activeDate`` do 4427 (as anteriores a esta coluna mostram a criação do personagem).

Revision ID: 0109
Revises: 0108
Create Date: 2026-10-29 20:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import wartune_server.persistence.schema

revision = "0109"
down_revision = "0108"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "server_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=96), nullable=False),
        sa.Column("text", sa.Text(), server_default="", nullable=False),
        sa.Column("updated_at", wartune_server.persistence.schema.UTCDateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_server_states")),
        sa.UniqueConstraint("server_id", "key", name=op.f("uq_server_states_server_id_key")),
    )
    with op.batch_alter_table("player_systems", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mount_since", sa.String(length=1024), server_default="", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("player_systems", schema=None) as batch_op:
        batch_op.drop_column("mount_since")
    op.drop_table("server_states")
