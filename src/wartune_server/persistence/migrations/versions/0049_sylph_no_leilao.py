"""Sylph no leilão: o pet à venda e o item que o leva

``items.property1``: o ``ItemInfoMsg.property1``; no Sylph à venda (item -900, ``PetData.convertToGoods``) leva o pet
como o ``PetData.createWidthString`` lê. ``pets.held``: o pet está no leilão ou no correio e fica fora da lista do
dono até alguém pegar (5022) ou o anúncio ser cancelado (8454).

Revision ID: 0049
Revises: 0048
Create Date: 2026-10-21 02:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("property1", sa.String(1024), server_default="", nullable=False))
    with op.batch_alter_table("pets") as batch:
        batch.add_column(sa.Column("held", sa.Boolean(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("pets") as batch:
        batch.drop_column("held")
    with op.batch_alter_table("items") as batch:
        batch.drop_column("property1")
