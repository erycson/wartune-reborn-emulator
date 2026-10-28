"""teto diário do altar: 60

``game_settings.rest_house.daily`` deixa de ser inventado: RecoverInfos SonType 6 (Altar of Ennoblement) tem
OneDayMax 60, e o Recuperar EXP oficial mostra 3 unidades de 20 para quem não meditou (d27 #63).

Revision ID: 0096
Revises: 0095
Create Date: 2026-10-28 18:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0096"
down_revision = "0095"
branch_labels = None
depends_on = None

settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _set(daily: int, source: str) -> None:
    op.execute(
        settings.update()
        .where(settings.c.key == "rest_house")
        .values(value=json.dumps({"daily": daily}), source=source)
    )


def upgrade() -> None:
    _set(60, "RecoverInfos SonType 6 OneDayMax; Recuperar EXP d27 #63 (3 x 20)")


def downgrade() -> None:
    _set(50, "TODO(inventado): sem fonte no cliente, na captura ou na internet")
