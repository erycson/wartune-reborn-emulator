"""lote 7: destino 2100/2200 e o bônus da vocação do dragão

``fate_unlock``: nível do herói que abre os tipos 2100 e 2200 da roda do destino (as SkillTempInfos existem; o
``FateRotaryFrame`` mostra o que o 4544 manda, sem regra de abertura). TODO(inventado): 65 e 75.

``dragon_vocation_bonus``: % por grau de vocação depois da transferência (8643) nos atributos da luta. O
``DragonSoulView`` só mostra o nome da vocação. TODO(inventado): +1% de ataque físico e mágico por grau.

Revision ID: 0116
Revises: 0115
Create Date: 2026-10-29 08:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0116"
down_revision = "0115"
branch_labels = None
depends_on = None

settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
ROWS = [
    {
        "key": "fate_unlock",
        "value": json.dumps({"2100": 65, "2200": 75}),
        "source": "TODO(inventado): nível que abre os destinos 2100/2200 (sem regra no cliente nem captura)",
    },
    {
        "key": "dragon_vocation_bonus",
        "value": json.dumps({"PhyAttack": 1, "MagicAttack": 1}),
        "source": "TODO(inventado): % por grau de vocação do dragão na luta (DragonSoulView só mostra o nome)",
    },
]


def upgrade() -> None:
    op.bulk_insert(settings, ROWS)


def downgrade() -> None:
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
