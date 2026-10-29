"""arena em grupo: o prêmio de cada luta (``game_settings.arena_party``)

``{"win": [[templateId, quantidade], ...], "lose": [...]}``, a quem pediu prêmio (``isNoGet`` falso) no fim da luta
da sala PvP (``handlers/arena_grupo.py``). (visto) oficial_20261027-152321-1 #19933 e #19993: derrota, Insignia x10.
TODO(inventado): a vitória, Insignia x20 (sem captura).

Pontos do ranking (``game/arena_grupo.py``, ``crossScore`` e ``cross/crossscore.xml``): ``win_points`` 10,
``lose_points`` 5 (sem ficar negativo) e ``reset`` "week" (o ``PvpHeroFrame`` é semanal). TODO(inventado): os
valores dos pontos; nem o cliente nem a captura dizem.

Revision ID: 0107
Revises: 0106
Create Date: 2026-10-29 12:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0107"
down_revision = "0106"
branch_labels = None
depends_on = None

KEY = "arena_party"
SOURCE = (
    "(visto) oficial_20261027-152321-1 #19933/#19993 derrota Insignia x10; (cliente) PvpHeroFrame semanal; "
    "TODO(inventado) vitória Insignia x20 e os pontos 10/5"
)


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    value = {"win": [[208001, 20]], "lose": [[208001, 10]], "win_points": 10, "lose_points": 5, "reset": "week"}
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(value), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
