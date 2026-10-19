"""validade dos itens e corneta grátis do VIP

``items.valid_date`` (minutos) e ``items.begin_date``: o ``validDate``/``beginDate`` do ItemInfoMsg (115). A loja de
honra vende medalhas com ``ShopTempInfos.ValidDate`` 10080/21600/43200 (7, 15 e 30 dias); o cliente some com o item
vencido (``BaseBagListView``/``EquipBagII`` mandam 8346).

``game_settings.vip_bugle_bonus``: cornetas pequenas grátis a mais por nível VIP (índice = nível, 0..9). Nem o cliente
(``VipPrerogativeTempInfos`` não tem esse tipo; ``ConfigInfos`` só tem ``SMALL_BUGLE_FREE_COUNT`` 10) nem a captura
dizem quanto: padrão 0 (sem efeito) até capturar um 4500 de uma conta VIP.

Revision ID: 0036
Revises: 0035
Create Date: 2026-10-19 15:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

SETTINGS = [
    (
        "vip_bugle_bonus",
        [0] * 10,
        "sem fonte: cliente e captura não dizem; falta captura do 8705 -> 4500 de uma conta VIP (docs/chat.md)",
    ),
]


def upgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("valid_date", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("begin_date", UTCDateTime(timezone=True), nullable=True))
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": k, "value": json.dumps(v), "source": s} for k, v, s in SETTINGS])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([k for k, _, _ in SETTINGS])))
    with op.batch_alter_table("items") as batch:
        batch.drop_column("begin_date")
        batch.drop_column("valid_date")
