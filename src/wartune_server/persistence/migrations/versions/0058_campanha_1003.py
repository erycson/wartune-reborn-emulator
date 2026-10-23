"""campanha 1003 (Temple of Ibalize (Outer))

Conteúdo das salas 1031 e 1032 extraído da captura do oficial inglês ``oficial_20261023-153200-1`` por
``tools/extract_dungeon.py`` (``0058_campanha_1003.json``, ao lado): nós, névoa, 9 lutas, diálogo do chefe, baús,
caixas, a caixa do caçador do 103105 (Lvl. 3 Luck Stone) e a alavanca do 103204 ("Successfully open the outer
temple.", que some o 103205 e mostra o chefe 103207). Os nós 103111 e 103112 vêm no estado 9 e não tiveram luta.

(dedução) o chefe não caiu na captura (três derrotas): o quadro de cartas do fim (135) é o das 1001/1002
(``cardCount`` 5, ``payCardCount`` 5, ``price`` 0) e o sorteio usa o ``Campaigns.Item`` (pesos iguais).

Revision ID: 0058
Revises: 0057
Create Date: 2026-10-23 22:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0058_campanha_1003.json")
SOURCE = "(visto) captures/oficial_20261023-153200-1.json, tools/extract_dungeon.py; cartas do fim (dedução)"
CARDS = {"sceneType": "SINGLE_CAMPAIGN_MAP_SCENE", "cardCount": 5, "payCardCount": 5, "price": 0}
LAST_MAP = "1032"


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    data = seed["1003"]
    data["maps"][LAST_MAP].setdefault("cards", CARDS)
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(contents, [{"campaign_id": 1003, "data": json.dumps(data, ensure_ascii=False), "source": SOURCE}])


def downgrade() -> None:
    contents = sa.table("campaign_contents", sa.column("campaign_id"))
    op.execute(contents.delete().where(contents.c.campaign_id == 1003))
