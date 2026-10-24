"""campanhas 1005 (Orc Plains) e 1006 (Tribal Plateau)

Conteúdo extraído da captura do oficial inglês ``oficial_20261023-231733-1`` por ``tools/extract_dungeon.py``
(``0075_campanhas_1005_1006.json``, ao lado): as duas etapas de cada uma, como o ``MapInfos`` (1005: 1071-1073 #319 e
1081-1083 #2120; 1006: 1151 #3253 e 1161 #4158), com nós, névoa, lutas, diálogos, baús, caixas, drops e o quadro de
cartas do último mapa de cada etapa.

TODO(inventado): a luta do "[Elite] Bloodthirsty Tauren" (115116, ``heroTempId`` 1062): ninguém lutou com ele na
captura e a 1161 não tem um igual. Vai como a do Kronos (115111): o herói sozinho, com os números do
``GameHeroTemp`` 1062 (3020 de vida, ``boss005C``) e o ``DefaultSkill`` 60095 em toda a fila.

Cartas do fim (``campaign_cards``): (visto) 1005 deu Regalian Robe (1043103, #1313) e Lvl. 1 Luck Stone (2040101,
#3229), as duas no ``Campaigns.Item``; 1006 deu VIP Token (208015, #3908 e #4758), que não está no ``Item``
(1060103, 1060102, 2040101). (dedução) pesos iguais, como a 0069.

Revision ID: 0075
Revises: 0074
Create Date: 2026-10-24 18:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0075_campanhas_1005_1006.json")
SOURCE = "(visto) captures/oficial_20261023-231733-1.json, tools/extract_dungeon.py; 115116 TODO(inventado)"
CARD_SOURCE = "(visto) oficial_20261023-231733-1 #1313/#3229/#3908/#4758; o resto do Campaigns.Item; pesos iguais"
POOLS = {
    1005: (1041103, 1042103, 1043103, 1043102, 1042102, 1041102, 2040101),
    1006: (1060103, 1060102, 2040101, 208015),
}


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(
        contents,
        [{"campaign_id": c, "data": json.dumps(seed[str(c)], ensure_ascii=False), "source": SOURCE} for c in POOLS],
    )
    cards = sa.table(
        "campaign_cards", sa.column("campaign_id"), sa.column("template_id"), sa.column("weight"), sa.column("source")
    )
    op.bulk_insert(
        cards,
        [
            {"campaign_id": c, "template_id": t, "weight": 1.0, "source": CARD_SOURCE}
            for c, pool in POOLS.items()
            for t in pool
        ],
    )


def downgrade() -> None:
    for name in ("campaign_contents", "campaign_cards"):
        table = sa.table(name, sa.column("campaign_id"))
        op.execute(table.delete().where(table.c.campaign_id.in_(tuple(POOLS))))
