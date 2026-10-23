"""recharge gift pack

``game_settings.rebate``: o Recharge Gift Pack (``FeedBackManager``: 4461 / 8574 / 4463) do oficial_encantar #61, de
2026-10-23 a 2026-10-28: 7 pacotes por Balens recarregados na janela (500 a 40000). A recarga vem do ``cash_ledger``
``reason='recharge'`` que o portal grava.

Revision ID: 0055
Revises: 0054
Create Date: 2026-10-23 18:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None

KEY = "rebate"
REBATE = {
    "id": "05E8C640-2BDA-E798-EFE5-CD8663F29F62",
    "beginDate": "2026-10-23 00:00:00",
    "endDate": "2026-10-28 23:59:59",
    "type": 1,
    "packages": [  # ordem do #61; o cliente ordena pelo ``order``
        {"packageId": "0249D00C-78CB-2A8E-A75B-CD8663F2C9B7", "order": 4, "point": 4000, "price": 4000,
         "items": [[208023, 15], [2060488, 10], [3040001, 15], [3120604, 1], [21261044, 2]]},
        {"packageId": "5A8C628F-617C-7FB2-BA2F-CD8663F3F859", "order": 7, "point": 40000, "price": 40000,
         "items": [[2125057, 50], [2125125, 50], [3120005, 1], [3240102, 50], [21261042, 2]]},
        {"packageId": "7708D856-3FF2-D39D-E978-CD8663F3DB03", "order": 6, "point": 20000, "price": 20000,
         "items": [[2060488, 30], [2125123, 50], [2125124, 50], [3120004, 1], [21261042, 1]]},
        {"packageId": "928A9DA3-BD4E-9C04-EE3A-CD8663F22AC1", "order": 5, "point": 10000, "price": 10000,
         "items": [[208023, 30], [2060488, 15], [3040001, 30], [3270101, 15], [21261042, 1]]},
        {"packageId": "9CAE7140-FBB3-3AFD-9E1C-CD8663F28891", "order": 3, "point": 2000, "price": 2000,
         "items": [[208017, 20], [208131, 1], [2060487, 10], [2060488, 10], [21261044, 1]]},
        {"packageId": "A7C07FB5-4874-7375-1344-CD8663F2FE8C", "order": 1, "point": 500, "price": 500,
         "items": [[208017, 4], [2060487, 5], [2126025, 2], [21261044, 1]]},
        {"packageId": "BFA9BF57-58FF-E0F1-2A9E-CD8663F2FCB7", "order": 2, "point": 1000, "price": 1000,
         "items": [[208017, 10], [2060487, 10], [2126025, 3], [21261044, 1]]},
    ],
}  # fmt: skip
SOURCE = "(visto) captura do oficial inglês oficial_encantar #61 (4461) e #76 (4463)"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(REBATE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
