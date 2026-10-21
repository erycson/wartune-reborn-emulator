"""vínculo dos itens

``items.is_binds``: o ``ItemInfoMsg.bind`` do cliente inglês (tooltip "Bound"/"Unbound"). Só item livre vai ao leilão
(``Auction.ResultAlert7`` "Item is bound!"). Os itens que já existem ficam vinculados, como o servidor mandava até
aqui (``bind`` true para todos, igual à captura inglesa).

Revision ID: 0043
Revises: 0042
Create Date: 2026-10-20 18:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("is_binds", sa.Boolean(), server_default="1", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.drop_column("is_binds")
