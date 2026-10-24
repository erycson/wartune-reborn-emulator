"""castelo NPC vencido: ouro saqueado, proteção de 2 h e o poder do castelo no relatório

``game_settings.npc_castles`` ganha ``loot_per_grade``, ``shield_seconds`` e ``fight``.

(visto) oficial_20261023-171155-1 #6014-#6027 e a carta 11569 do ``maillist`` da mesma sessão: vencer o Aladyr (grau 12)
deu 4950 de ouro (``gold`` 4950 / -4950 no relatório; o ouro aparece no 109 #6046), o 118 com ``leftTime`` 7200 e o
castelo de volta com ``defenceLefttime`` 7199; o relatório leva ``fight`` 1760 para o castelo (11554, 11564, 11569).
TODO(inventado): nos outros graus o saque é ``loot_per_grade`` × grau (4950 / 12) e o ``fight`` 1760 × grau / 12.

Revision ID: 0066
Revises: 0065
Create Date: 2026-10-24 10:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None

KEY = "npc_castles"
NEW = {"loot_per_grade": 412.5, "shield_seconds": 7200, "fight": {"12": 1760}}
SOURCE = (
    "(visto) oficial_20261023-153200-1/171155-1: seen, pawn_hp do grau 12, loot 4950 / shield 7200 / fight 1760 do "
    "Aladyr (grau 12); (dedução) per_grid = quantos castelos NPC as 45 grades vistas têm; TODO(inventado): os castelos "
    "das grades não vistas, hp_factor (443 / 422), loot_per_grade e fight nos outros graus"
)


def _table() -> sa.TableClause:
    return sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _load() -> dict[str, object] | None:
    t = _table()
    row = op.get_bind().execute(sa.select(t.c.value).where(t.c.key == KEY)).first()
    return json.loads(row[0]) if row else None


def upgrade() -> None:
    value = _load()
    if value is None:
        return
    value.update(NEW)
    t = _table()
    op.execute(t.update().where(t.c.key == KEY).values(value=json.dumps(value), source=SOURCE))


def downgrade() -> None:
    value = _load()
    if value is None:
        return
    for k in NEW:
        value.pop(k, None)
    t = _table()
    op.execute(t.update().where(t.c.key == KEY).values(value=json.dumps(value)))
