"""Treasure Cache do mapa do mundo

``treasure_cache_opens``: baú aberto por qualquer jogador (chave mapa, vaga, nascimento), que some até a próxima vida
(``game/caches.py``). ``game_settings.treasure_caches``: vagas e faixa de nível por mapa e o prêmio.

(visto) oficial_20261023-153200-1 e oficial_20261023-171155-1: templates 2201xx, 3 guardas, ``battleType`` 3, prêmio
Lvl. 3 Luck Stone e Elders Robe. Nível na faixa do mapa (MapInfos MinLevel-MaxLevel). TODO(inventado): quantas
vagas por mapa e a regra do prêmio (pedra da sorte do nível ou equipamento da classe).

Revision ID: 0063
Revises: 0062
Create Date: 2026-10-24 01:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None

KEY = "treasure_caches"
SOURCE = (
    "(visto) oficial_20261023-171155-1 #570-#670 (luta e prêmio); levels = MapInfos MinLevel-MaxLevel (cliente); "
    "TODO(inventado): count (1 vaga a cada 25 000 tiles) e loot (pedra Lvl. ceil(nível/5) ou equipamento da classe)"
)
VALUE = {
    "maps": {
        "1": {"count": 1000, "levels": [11, 20]},
        "2": {"count": 640, "levels": [21, 30]},
        "3": {"count": 250, "levels": [31, 40]},
        "4": {"count": 160, "levels": [41, 50]},
        "5": {"count": 90, "levels": [51, 60]},
    },
    "loot": {"stone_weight": 1, "gear_weight": 1, "gear_profile": 2, "gear_below": 5, "gear_above": 2},
}


def upgrade() -> None:
    op.create_table(
        "treasure_cache_opens",
        sa.Column("map_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("cache_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("born_at", UTCDateTime(), nullable=False),
        sa.Column("character_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("opened_at", UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("map_id", "cache_id", "born_at", name=op.f("pk_treasure_cache_opens")),
    )
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    op.drop_table("treasure_cache_opens")
