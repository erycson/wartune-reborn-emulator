"""limites do lote 2: teto diário de EXP de itens e a espera da colheita da pedreira

``item_exp_daily``: EXP de herói que os itens de recurso (SonType 203, ``Property1`` 7, o EXP Book) dão por dia do
jogo (``handlers/items.py``). TODO(inventado): 5.000.000; nem o cliente nem a captura mostram teto. A stamina das
poções já tem o seu (300 por dia, ``daily.POTION_DAY``, do ``PlayerMsg.wearyLimit`` do cliente).

``quarry_collect_seconds``: segundos entre o 143 COLLECTION (ou a última colheita) e o 5032 que colhe na pedreira
(``handlers/campaign.py``). (cliente) ``CollectionAction`` só manda o 5032 no fim da animação; (visto) tutorial_en
#1843 -> #1847 4,6 s e #1847 -> #1861 5,6 s; 4 s deixa folga para o atraso da rede.

Revision ID: 0108
Revises: 0107
Create Date: 2026-10-29 18:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0108"
down_revision = "0107"
branch_labels = None
depends_on = None

ROWS = [
    {
        "key": "item_exp_daily",
        "value": json.dumps(5_000_000),
        "source": "TODO(inventado): sem teto no cliente nem na captura",
    },
    {
        "key": "quarry_collect_seconds",
        "value": json.dumps(4),
        "source": "(cliente) CollectionAction: 5032 no fim da animação; (visto) tutorial_en #1843-#1861, 4,6 s e 5,6 s",
    },
]


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, ROWS)


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
