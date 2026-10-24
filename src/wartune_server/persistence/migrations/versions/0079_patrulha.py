"""patrulha dos monstros nos mapas de campanha (4122 ``U_C_NPC_MOVE``)

``game_settings.npc_patrol``: os pontos de cada nó por ``campDataId`` (``0079_patrulha.json``, ao lado), a união de
todos os 4122 das capturas inglesas (tutorial_en, oficial_encantar, oficial_20261023-*). Nem o cliente nem os
templates têm os pontos: o cliente só anda até onde o servidor manda (``CampaignSocketManger.__npcMoveHandler``).

(visto) só os nós agressivos (masterType 42, attackTypes 1) e os trabalhadores da pedreira 6001 (masterType 101)
andam; cada passo vai para outro ponto do conjunto, nunca o mesmo (3 repetidos em 510). O 1º passo de todos sai ~6,5 s
depois da entrada (125) e os seguintes em múltiplos de 6 s: 309 de 1 tique, 112 de 2, 45 de 3, 21 de 4, então
``chance`` 0,62 por tique. Na pedreira o tique é de 20 s e a chance 0,3 (10 intervalos, poucos).

Revision ID: 0079
Revises: 0078
Create Date: 2026-10-24 23:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0079_patrulha.json")
KEY = "npc_patrol"
SOURCE = "(visto) 4122 das capturas inglesas: pontos por campDataId, tique de 6 s (pedreira 20 s), chance 0,62 (0,3)"


def upgrade() -> None:
    value = {
        "tick": 6,
        "chance": 0.62,
        "quarry_tick": 20,
        "quarry_chance": 0.3,
        "points": json.loads(SEED.read_text("utf-8")),
    }
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(value), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
