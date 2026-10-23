"""super assinatura

``game_settings.super_signin``: a edição do Super Check-in Card que o oficial inglês mandava em oficial_encantar
(4590 #118: aberta de 2026-10-23 00:00 a 2026-10-30 00:00; 514 #119: cartão 500 Balens, assinar dia perdido 10, os
7 dias de prêmio). ``minGrades`` 6 e ``cardDays`` 8 vêm do cliente (``TopToolsBar.showSuperSigninCardBtn`` e
``SuperSigninCardFrame.descTxt2`` "lasts up to 8 days").

Revision ID: 0054
Revises: 0053
Create Date: 2026-10-23 17:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None

KEY = "super_signin"
SUPER_SIGNIN = {
    "openTime": "2026-10-23 00:00:00",
    "stopTime": "2026-10-30 00:00:00",
    "cardPrice": 500,
    "reSigninPrice": 10,
    "minGrades": 6,
    "cardDays": 8,
    "temp": [
        [1, "3040001,5|21261044,1"],
        [2, "208023,5|21261044,1"],
        [3, "3040001,10|3270101,10"],
        [4, "208023,10|3270101,10"],
        [5, "3270101,10|3040001,10"],
        [6, "3240102,2|208023,10"],
        [7, "3240102,3|3270101,15"],
    ],
}
SOURCE = "(visto) oficial_encantar #118 (4590) e #119 (514); (cliente) minGrades e cardDays"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(SUPER_SIGNIN), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
