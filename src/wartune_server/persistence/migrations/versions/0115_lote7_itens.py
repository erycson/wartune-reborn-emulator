"""lote 7 (itens): preço da EXP offline paga e a chave da mina de Amethyst

``offline_reward_cost``: Balens por hora fora (arredondada para cima) do x1,5 (``rateCount`` 15) e do x2 (20) do
``HookRewardFrame``. O cliente só mostra a EXP x rateCount/10 e nenhuma captura tem o 8287 pago:
TODO(inventado) os dois preços.

``closed_switches``: a 3006 (MINERAL_FIGHT) abre, porque a Amethyst Mine existe (``handlers/warfield.py``, 30000);
fica só a 3031 (GOLDROAD): o 9521 (jogar o dado, 4934 ``CastDiceMsg``) não tem handler nem captura.

Revision ID: 0115
Revises: 0114
Create Date: 2026-10-29 06:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0115"
down_revision = "0114"
branch_labels = None
depends_on = None

settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
OFFLINE = {"15": 5, "20": 10}
OFFLINE_SOURCE = "TODO(inventado): preço do x1,5/x2 do HookRewardFrame (sem fonte no cliente nem captura)"
SWITCHES_SOURCE = "shortcut: estrada dourada (3031) sem o dado 9521; a mina (3006) existe desde o warfield"


def upgrade() -> None:
    op.bulk_insert(settings, [{"key": "offline_reward_cost", "value": json.dumps(OFFLINE), "source": OFFLINE_SOURCE}])
    op.execute(
        settings.update()
        .where(settings.c.key == "closed_switches")
        .values(value=json.dumps([3031]), source=SWITCHES_SOURCE)
    )


def downgrade() -> None:
    op.execute(settings.delete().where(settings.c.key == "offline_reward_cost"))
    op.execute(
        settings.update()
        .where(settings.c.key == "closed_switches")
        .values(
            value=json.dumps([3006, 3031]), source="shortcut: mina (3006) e estrada dourada (3031) não existem aqui"
        )
    )
