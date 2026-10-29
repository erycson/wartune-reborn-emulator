"""História (Time Story) e caixa de ano novo (``handlers/historia.py``).

``time_story``: ``{"dailyEggs": ovos por dia, "prize": [[templateId, quantidade], ...]}``; (cliente) o ovo sai no
8629 com ``isAccess`` (a cada 5 páginas, TimeStoryFrame.as:302) e "tem muito ouro" (lang eggImage.tipData).
``new_year_box``: ``{"begin", "end", "minLevel", "name", "prize"}``; (cliente) nível 35 em
StoreSocketOutManager.sendYearBoxCollect; os nós são os MasterType 300 do mapa 10000 (tempinfos).
TODO(inventado): sem captura do evento: ovos por dia, ouro do ovo, janela do ano novo, nome e prêmio da caixa.

Revision ID: 0123
Revises: 0122
Create Date: 2026-10-29 21:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0123"
down_revision = "0122"
branch_labels = None
depends_on = None

ROWS = [
    {
        "key": "time_story",
        "value": {"dailyEggs": 5, "prize": [[-100, 50000]]},  # -100 = ouro
        "source": "(cliente) TimeStoryFrame ovo a cada 5 páginas, ouro; TODO(inventado) 5 ovos/dia e 50000 de ouro",
    },
    {
        "key": "new_year_box",
        "value": {
            "begin": "2026-12-31 00:00:00",
            "end": "2027-01-08 00:00:00",
            "minLevel": 35,
            "name": "New Year Box",
            "prize": [[-100, 100000], [-600, 1000]],  # ouro e Kyanite
        },
        "source": "(cliente) nível 35, nós MasterType 300 do 10000; TODO(inventado) janela, nome e prêmio",
    },
]


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{**r, "value": json.dumps(r["value"])} for r in ROWS])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
