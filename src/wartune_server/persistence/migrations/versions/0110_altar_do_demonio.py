"""altar do demônio da guilda (7601): o que o cliente e a ajuda não dizem

``altar_demon`` (``handlers/altar.py``): o herói de cada onda (``GameHeroTemp``, a vida é o ``Live`` dele vezes
``hp_mult`` vezes o número da onda), a vida do altar e quanto uma onda que escapa (5 min sem morrer) tira, a entrada
e o nó do demônio no mapa (tiles), o passo do dano para cada grau do buff (511-530) e o ouro/Daru por onda do correio
do fim (dividido pela posição). Sem captura do altar: tudo TODO(inventado).

Revision ID: 0110
Revises: 0109
Create Date: 2026-10-29 22:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0110"
down_revision = "0109"
branch_labels = None
depends_on = None

ROWS = [
    {
        "key": "altar_demon",
        "value": json.dumps(
            {
                "hero": 1042,
                "hp_mult": 50,
                "durability": 100,
                "leak": 20,
                "start": [20, 120],
                "node": [100, 75],
                "buff_step": 100000,
                "reward_per_wave": 10000,
            }
        ),  # fmt: skip
        "source": "TODO(inventado): sem captura do altar; hero 1042 Demonic Mage pelo nome; regras de tempo na ajuda",
    },
]


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, ROWS)


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
