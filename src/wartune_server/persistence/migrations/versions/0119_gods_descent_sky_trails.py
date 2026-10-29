"""lote 9: Gods Descent e Sky Trails

``gods_descent`` (``handlers/tollgate.py``): o cliente dá as tentativas, a recuperação, as compras e o custo da
contagem (ConfigInfo ``tollgate_*``/``restore_count_time``), mas não a agenda do evento, quanto dura a contagem do
chefe, os pontos de cada chefe nem as posições da sorte. TODO(inventado): edição de 7 dias a partir de 2026-10-26
com 5 dias de luta (os 2 últimos só para receber o prêmio), 30 min de contagem, 10 pontos x índice do chefe, 3
posições da sorte entre as 50 primeiras e o ranking das 50 primeiras.

``sky_trails`` (``handlers/singlepass.py``): a avaliação D..S. TODO(inventado): pela vida que sobra ao herói (% para
S, A, B, C).

Revision ID: 0119
Revises: 0118
Create Date: 2026-10-29 18:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0119"
down_revision = "0118"
branch_labels = None
depends_on = None

settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
ROWS = [
    {
        "key": "gods_descent",
        "value": json.dumps(
            {
                "begin": "2026-10-26 00:00:00",
                "cycleDays": 7,
                "openHours": 120,
                "resetMinutes": 30,
                "pointsPerStage": 10,
                "luckyCount": 3,
                "luckyTop": 50,
                "rankTop": 50,
            }
        ),
        "source": "TODO(inventado): agenda, contagem do chefe, pontos, posições da sorte e tamanho do ranking do "
        "Gods Descent (sem captura; o resto vem do ConfigInfo do cliente)",
    },
    {
        "key": "sky_trails",
        "value": json.dumps({"judge": [80, 60, 40, 20]}),
        "source": "TODO(inventado): avaliação do Sky Trails pela % de vida que sobra ao herói (S, A, B, C; abaixo D)",
    },
]


def upgrade() -> None:
    op.bulk_insert(settings, ROWS)


def downgrade() -> None:
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
