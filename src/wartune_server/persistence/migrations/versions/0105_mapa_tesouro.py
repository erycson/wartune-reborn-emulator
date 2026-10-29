"""mapa do tesouro (Lost Treasure) ligado por padrão

``game_settings.treasure_map`` (``handlers/treasure.py``) com todos os parâmetros explícitos. O resto vem do cliente
sem config: custos (``Property3`` do mapa, ``treasure_refresh_item``, ``treasure_imm_battle``), limites
(``join_tremap_count``/``reward_tremap_count``) e o prêmio básico (``Property6`` x 208028). ``source`` de cada valor:
``cliente`` (ActionScript decompilado), ``template`` (tempinfos.xml), ``idioma`` (language.txt inglês do mirror) ou
``TODO(inventado)`` (sem captura do mapa do tesouro em inglês nem em turco além do 4633 do login).

Revision ID: 0105
Revises: 0104
Create Date: 2026-10-31 12:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0105"
down_revision = "0104"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"
KEY = "treasure_map"

TREASURE_MAP: dict[str, Any] = {
    "mapId": 10000,
    "digRange": 15,
    "teamRange": 40,
    "thieves": list(range(72001, 72015)),
    "battleType": 3841,
    "battleScene": 5,
    "legendaryBonus": 50,
    "source": {
        "mapId": "cliente TreasureMapUseFrame.checkScene/analyzeTreasureMap (randomSkill1 = mapa; Cloud City, a cena"
        " SPACE_SCENE); idioma TreasureMapUseFrame.helpContent",
        "digRange": "cliente TreasureMapModel.DISTANCE1 (15 x 20 px: TreasureMapManager.checkTreasureMap)",
        "teamRange": "cliente TreasureMapModel.DISTANCE2 (40); " + INV + " que seja o raio do grupo",
        "thieves": "template GameHeroTempInfo 'Master Treasure Thief' 72001-72014; idioma helpContent 'catching the"
        " treasure thief'; " + INV + " que seja o inimigo da escavação",
        "battleType/battleScene": INV + " (os do monstro do mapa do mundo, monsters.BATTLE_TYPE/SCENE)",
        "legendaryBonus": "idioma helpContent ('orange treasure map will receive more rewards'); " + INV + " o %",
    },
}
SOURCE = "mapa do tesouro (handlers/treasure): cliente + template + idioma + " + INV


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(TREASURE_MAP), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
