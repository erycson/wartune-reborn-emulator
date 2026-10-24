"""terra secreta da guilda (Guild Chamber, 7501): conteúdo do mapa e a contribuição por Invasor

Conteúdo extraído por ``tools/extract_dungeon.py`` de oficial_20261023-171155-1 #5056-#5172
(``0073_terra_secreta.json``, ao lado): os 62 nós do 127 (Invasores, a árvore, coletas e Master Treasure Thief), a
entrada (55, 83), o exército do sistema (3001) e a luta do Invasor 750109 (battleType 23, 4 soldados 3001).

``game_settings.fam_invader_offer``: TODO(inventado) 10 de contribuição por Invasor vencido; a ajuda do cliente
(``ConsortiaSecretInfoView.helpContent``) só diz "additional guild contribution points" e a captura foi uma derrota.

Revision ID: 0073
Revises: 0072
Create Date: 2026-10-24 15:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None

CAMPAIGN, KEY = 7501, "fam_invader_offer"
SEED = Path(__file__).with_name("0073_terra_secreta.json")
SOURCE = "(visto) oficial_20261023-171155-1 #5056-#5172 (tools/extract_dungeon.py)"
OFFER_SOURCE = "TODO(inventado): a ajuda do cliente só diz 'additional guild contribution points'"


def upgrade() -> None:
    data = json.loads(SEED.read_text(encoding="utf-8"))[str(CAMPAIGN)]
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(
        contents, [{"campaign_id": CAMPAIGN, "data": json.dumps(data, ensure_ascii=False), "source": SOURCE}]
    )
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(10), "source": OFFER_SOURCE}])


def downgrade() -> None:
    contents = sa.table("campaign_contents", sa.column("campaign_id"))
    op.execute(contents.delete().where(contents.c.campaign_id == CAMPAIGN))
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
