"""compra coletiva ligada por padrão

``game_settings.group_buy`` (``handlers/group_buy.py``): edição de ``cycleDays`` a partir de ``begin`` (hora do jogo),
``buyHours`` de compra e o resto de acerto; ``offers`` gira uma por edição. Cada oferta é um ``MainDiscountInfo``
(o servidor põe ``type`` 3 e as datas). ``shopId``/``templateId`` vêm das ofertas reais do 0053 (o cliente descarta
a oferta se o ``ShopTempInfos.ItemId`` não bate). ``source`` de cada valor: ``cliente`` (ActionScript decompilado) ou
``TODO(inventado)`` (sem captura de compra coletiva).

Revision ID: 0104
Revises: 0103
Create Date: 2026-10-30 12:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0104"
down_revision = "0103"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"
KEY = "group_buy"


def _offer(id_: int, shop: int, tid: int, counts: int, names: str, price: int, levels: list[int], prices: list[int]):
    return {
        "id": id_,
        "shopId": shop,
        "templateId": tid,
        "counts": counts,
        "names": names,
        "price": price,
        "frontMoney": price,
        "oneDayCount": 5,
        "maxCount": -1,
        "sortId": 1,
        "discount": 100,
        **{f"level{n}": lv for n, lv in enumerate(levels, 1)},
        **{f"price{n}": p for n, p in enumerate(prices, 1)},
    }


GROUP_BUY: dict[str, Any] = {
    "begin": "2026-01-05 05:00:00",
    "cycleDays": 7,
    "buyHours": 120,
    "offers": [
        _offer(9601, 200111, 208028, 300, "Crystal Shard*300", 389, [10, 30, 60], [349, 309, 269]),
        _offer(9602, 1243, 2125057, 10, "Slyph Stone*10", 299, [10, 30, 60], [269, 239, 199]),
        _offer(9603, 200108, 2032101, 1, "Battle Pack", 299, [10, 30, 60], [269, 239, 199]),
    ],
    "source": {
        "fases": "cliente GroupBuyView.timeHandler (compra até endDate, acerto até sendDate)",
        "levelN/priceN": "cliente GroupBuyProgressBar.initData (3 degraus); " + INV + " os valores",
        "frontMoney": "cliente GroupBuyView.rengouHandler (sinal por unidade); " + INV + " = preço cheio",
        "acerto": "cliente GroupBuyView.jiesuanHandler/CheckView (cobra ou devolve a diferença)",
        "offers": "shopId/templateId reais do 0053; " + INV + " o catálogo, preços e oneDayCount",
        "begin/cycleDays/buyHours": INV,
    },
}
SOURCE = "compra coletiva (handlers/group_buy): cliente + " + INV


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(GROUP_BUY), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
