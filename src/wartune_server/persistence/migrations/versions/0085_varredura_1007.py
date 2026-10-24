"""cartas da 1007 (Camp Calorn) e ouro da rodada da varredura: ``game_settings.campaign_sweep``

- Cartas: a 1007 não tinha ``campaign_cards`` (o ``Campaigns.Item`` com pesos iguais). (só turco: savasa_baskin, a
  rodada da 1007 deu Skeleton Key x1, que não está no ``Campaigns.Item``) entra 208005, como a 1004 (0069, visto).
- Ouro da rodada: (só turco: savasa_baskin) a rodada da 1007 deu 6000 de ouro (item -100). TODO(inventado): as outras
  campanhas ficam sem ouro até uma captura mostrar o delas.

Revision ID: 0085
Revises: 0084
Create Date: 2026-10-24 12:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0085"
down_revision = "0084"
branch_labels = None
depends_on = None

CAMPAIGN = 1007
KEY = "campaign_sweep"
SOURCE = "(só turco: savasa_baskin) a rodada da 1007 deu 6000 de ouro; TODO(inventado) as outras sem ouro"
CARD_SOURCE = "(só turco: savasa_baskin) a rodada deu 208005; o resto do Campaigns.Item; pesos iguais (dedução)"
POOL = (1080103, 1080113, 1080102, 1080112, 2040101, 208005)


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    value = {"round_gold": {str(CAMPAIGN): 6000}}
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(value), "source": SOURCE}])
    cards = sa.table(
        "campaign_cards", sa.column("campaign_id"), sa.column("template_id"), sa.column("weight"), sa.column("source")
    )
    rows = [{"campaign_id": CAMPAIGN, "template_id": t, "weight": 1.0, "source": CARD_SOURCE} for t in POOL]
    op.bulk_insert(cards, rows)


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    cards = sa.table("campaign_cards", sa.column("campaign_id"))
    op.execute(cards.delete().where(cards.c.campaign_id == CAMPAIGN))
