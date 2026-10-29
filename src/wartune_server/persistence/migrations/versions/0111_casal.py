"""casamento: pontos do casal, jogo do coração e sala da cerimônia

``marriages.couple``: JSON igual nas duas linhas do casal (``handlers/marriage.py``): os pontos do casal (somam nas
missões do casal, no jogo do coração e na rega da árvore) e as compras da loja do altar (9611, ``Mate_Shop``).

``marriage_heart``: perguntas por jogo, segundos por pergunta e pontos do casal por acerto. TODO(inventado): o
cliente (``MarriageHeartMsg``) só diz que há ``maxOrder`` perguntas com ``remainTime``; a tela é do m9, sem fonte.

``couple_points``: pontos do casal por ação (``task``: o ``RewardHappy`` da missão vale; ``water``: rega da árvore).
TODO(inventado): o contador não existe no cliente inglês (a loja é da Guerra de Vênus, ``altarScore``).

Revision ID: 0111
Revises: 0110
Create Date: 2026-10-29 23:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0111"
down_revision = "0110"
branch_labels = None
depends_on = None

ROWS = [
    {
        "key": "marriage_heart",
        "value": json.dumps({"questions": 10, "seconds": 30, "points": 2}),
        "source": "TODO(inventado): a tela do jogo do coração é do m9 (sem fonte); HeartTempInfos tem as perguntas",
    },
    {
        "key": "couple_points",
        "value": json.dumps({"water": 1}),
        "source": "TODO(inventado): pontos do casal para a loja do altar; a missão usa o RewardHappy do template",
    },
]


def upgrade() -> None:
    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("couple", sa.Text(), server_default="", nullable=False))
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, ROWS)


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
    with op.batch_alter_table("marriages", schema=None) as batch_op:
        batch_op.drop_column("couple")
