"""equipamento de mascote: bênção do encantamento, vínculo do mascote e skills do torneio

``items.bless_value``: a bênção do encantamento do equipamento de mascote (8644, ``ItemInfoMsg.blessValue``; o
``PetEquipStrengView`` soma na taxa e mostra "Blessing N/100"). ``pets.is_bind``: o ``PetInfoMsg.isBind`` (só o
mascote livre vai ao leilão, ``PetSellView``); os que já existem ficam vinculados, como o servidor mandava até aqui.
``pets.cha_skills``: as skills escolhidas para o torneio de mascotes (8726, ``PetInfoMsg.chaSkillIndexs``).

Revision ID: 0047
Revises: 0046
Create Date: 2026-10-21 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("bless_value", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("pets") as batch:
        batch.add_column(sa.Column("is_bind", sa.Boolean(), server_default="1", nullable=False))
        batch.add_column(sa.Column("cha_skills", sa.String(32), server_default="-1,-1,-1", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("pets") as batch:
        batch.drop_column("cha_skills")
        batch.drop_column("is_bind")
    with op.batch_alter_table("items") as batch:
        batch.drop_column("bless_value")
