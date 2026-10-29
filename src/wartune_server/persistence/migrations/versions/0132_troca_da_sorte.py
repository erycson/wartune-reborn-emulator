"""troca da sorte (9610) ligada

``game_settings.lucky_exchange`` (``handlers/minigames.py``): ``editions`` = as duas edições do 363 do tutorial_en #88
("Little Windmill" e "Nostalgic Times Exchange", nomes, itens, ``luckValue`` e datas como vieram); o operador troca
ou acrescenta edições. ``percentChance`` (chance de cada item ``dropType`` 3) e ``weights`` (itemId -> peso no
sorteio dos tipos 2/4, padrão 1) não estão no cliente nem no language (``luckyexchange.*`` só diz "Chance to receive" e
"Randomly receive one"): ``TODO(inventado)``.

Revision ID: 0132
Revises: 0131
Create Date: 2026-10-29 13:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0132"
down_revision = "0131"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"
KEY = "lucky_exchange"

EDITIONS: list[dict[str, Any]] = [
    {
        "id": "9F3FC59C-D438-5DC5-FC24-CD772F58CF95",
        "name": "Little Windmill",
        "consumeItemId": 21261040,
        "consumeItemCount": 1,
        "luckValue": 80,
        "startTime": "2026-10-08 00:00:00",
        "endTime": "2026-10-14 23:59:59",
        "dropItems": [
            {"itemId": -100, "itemCount": 50000, "rare": False, "dropType": 3},
            {"itemId": 208024, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 208017, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 208023, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 3040001, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 2125057, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 3240101, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 208014, "itemCount": 30, "rare": False, "dropType": 4},
            {"itemId": 2050603, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 3120102, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 3120604, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 2031001, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 3250101, "itemCount": 10, "rare": False, "dropType": 4},
            {"itemId": 3260101, "itemCount": 10, "rare": False, "dropType": 4},
            {"itemId": 3120003, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 208017, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 3040001, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 208023, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 21261041, "itemCount": 2, "rare": True, "dropType": 4},
            {"itemId": 21261040, "itemCount": 50, "rare": True, "dropType": 4},
            {"itemId": 3240102, "itemCount": 5, "rare": True, "dropType": 4},
            {"itemId": 2127002, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 208017, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 208023, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 3040001, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 208014, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 2050602, "itemCount": 1, "rare": False, "dropType": 4},
            {"itemId": 2032101, "itemCount": 1, "rare": False, "dropType": 4},
        ],
    },
    {
        "id": "4F65ABFB-CB48-E5C7-3026-CD8FED3A2376",
        "name": "Nostalgic Times Exchange",
        "consumeItemId": 21261044,
        "consumeItemCount": 1,
        "luckValue": 10,
        "startTime": "2026-10-23 00:00:00",
        "endTime": "2026-11-01 23:59:59",
        "dropItems": [
            {"itemId": -100, "itemCount": 50000, "rare": False, "dropType": 3},
            {"itemId": 208024, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 208017, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 208023, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 3040001, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 2125057, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 2100035, "itemCount": 15, "rare": False, "dropType": 4},
            {"itemId": 208014, "itemCount": 60, "rare": False, "dropType": 4},
            {"itemId": 2050603, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 3120102, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 3120604, "itemCount": 2, "rare": False, "dropType": 4},
            {"itemId": 2031001, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 2031204, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 2031303, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 3120003, "itemCount": 3, "rare": False, "dropType": 4},
            {"itemId": 208017, "itemCount": 60, "rare": False, "dropType": 4},
            {"itemId": 3040001, "itemCount": 60, "rare": False, "dropType": 4},
            {"itemId": 208023, "itemCount": 60, "rare": False, "dropType": 4},
            {"itemId": 3240102, "itemCount": 20, "rare": False, "dropType": 4},
            {"itemId": 21261042, "itemCount": 2, "rare": True, "dropType": 4},
            {"itemId": 2127002, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 208017, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 208023, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 3040001, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 208014, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 2050602, "itemCount": 5, "rare": False, "dropType": 4},
            {"itemId": 2032101, "itemCount": 3, "rare": False, "dropType": 4},
        ],
    },
]
LUCKY: dict[str, Any] = {
    "editions": EDITIONS,
    "percentChance": 50,
    "weights": {},
    "source": {
        "editions": "visto tutorial_en #88 (363)",
        "regras": "cliente LuckyExchangeRightView/LuckyExchangeManager e language luckyexchange.*",
        "percentChance/weights": INV,
    },
}
SOURCE = "troca da sorte: edições da captura + " + INV + " nas chances"


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(LUCKY), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
