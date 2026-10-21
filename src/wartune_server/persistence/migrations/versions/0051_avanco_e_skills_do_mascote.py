"""avanço e skills do mascote

``pets.quality_gp``: a barra de bênção do avanço de qualidade (8621 op 4, ``PetInfoMsg.curQualityGp``).
``player_systems.pet_free_skill_at``: o último aprendizado aleatório grátis de skill de pet (8621 op 5,
``PlayerMsg.lastFreeSkillLearnTime``).

Revision ID: 0051
Revises: 0050
Create Date: 2026-10-21 04:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pets") as batch:
        batch.add_column(sa.Column("quality_gp", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("player_systems") as batch:
        batch.add_column(sa.Column("pet_free_skill_at", UTCDateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("player_systems") as batch:
        batch.drop_column("pet_free_skill_at")
    with op.batch_alter_table("pets") as batch:
        batch.drop_column("quality_gp")
