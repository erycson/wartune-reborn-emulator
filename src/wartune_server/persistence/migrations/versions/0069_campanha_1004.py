"""campanha 1004 (Temple of Ibalize (Inner))

Conteúdo da sala 1051 extraído da captura do oficial inglês ``oficial_20261023-171155-1`` (#5249-#5831) por
``tools/extract_dungeon.py`` (``0069_campanha_1004.json``, ao lado): nós, névoa, 6 lutas (o chefe Bantashee no 105109,
com o diálogo, e o Demonic Mage no 105113, que deu Lamenter's Band x1), o baú 105107, as caixas 105110-105112 e o
quadro de cartas do fim (135: ``cardCount`` 5, ``payCardCount`` 5, ``price`` 0, #5799), igual ao das 1001-1003.

Cartas do fim (``campaign_cards``): (visto) #5828 a carta 3 deu Skeleton Key (208005) x1, que não está no
``Campaigns.Item`` (1070103, 1070102, 2040101). (dedução) as quatro com o mesmo peso, de uma amostra.

Revision ID: 0069
Revises: 0068
Create Date: 2026-10-24 13:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None

CAMPAIGN = 1004
SEED = Path(__file__).with_name("0069_campanha_1004.json")
SOURCE = "(visto) captures/oficial_20261023-171155-1.json #5249-#5831, tools/extract_dungeon.py"
CARDS = {"sceneType": "SINGLE_CAMPAIGN_MAP_SCENE", "cardCount": 5, "payCardCount": 5, "price": 0}
LAST_MAP = "1051"
CARD_SOURCE = "(visto) oficial_20261023-171155-1 #5828: 208005; o resto do Campaigns.Item; pesos iguais (dedução)"
POOL = (1070103, 1070102, 2040101, 208005)


def upgrade() -> None:
    data = json.loads(SEED.read_text(encoding="utf-8"))[str(CAMPAIGN)]
    data["maps"][LAST_MAP].setdefault("cards", CARDS)
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(
        contents, [{"campaign_id": CAMPAIGN, "data": json.dumps(data, ensure_ascii=False), "source": SOURCE}]
    )
    cards = sa.table(
        "campaign_cards", sa.column("campaign_id"), sa.column("template_id"), sa.column("weight"), sa.column("source")
    )
    rows = [{"campaign_id": CAMPAIGN, "template_id": t, "weight": 1.0, "source": CARD_SOURCE} for t in POOL]
    op.bulk_insert(cards, rows)


def downgrade() -> None:
    for name in ("campaign_contents", "campaign_cards"):
        table = sa.table(name, sa.column("campaign_id"))
        op.execute(table.delete().where(table.c.campaign_id == CAMPAIGN))
