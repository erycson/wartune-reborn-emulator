"""ofertas da loja

``game_settings.shop_offers``: as ofertas por tempo do operador (Timed Sales do Hot Events e destaques da loja, 4238),
semeadas de ``0053_ofertas_da_loja.json`` (ao lado desta migração). Fonte: oficial_encantar #57-#58 (53 ofertas,
``flag`` 13); só os campos não-padrão de cada ``MainDiscountInfo``, sem o ``currentCount`` (vendidos no oficial).
Gerado por um script de varredura do 4238; conferido contra ``ShopTempInfos``/``ItemTempInfos`` (todos os
``shopIdN`` existem e o ``ItemId`` bate com o ``templateIdN``, senão o cliente descarta a oferta).

Revision ID: 0053
Revises: 0052
Create Date: 2026-10-23 16:00:00.000000
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0053_ofertas_da_loja.json")
KEY = "shop_offers"
SOURCE = "(visto) captura do oficial inglês oficial_encantar #57-#58 (4238), #1312 (4375)"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": SEED.read_text(encoding="utf-8"), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
