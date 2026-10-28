"""Colheita da árvore com Daru, Kyanite e ouro vistos nas capturas, por grau da fazenda

``game_settings.tree_fruit`` passa a ser ``{grau: {"daru", "kyanite", "gold"}}`` com os dois graus vistos (o resto é
reta entre eles, ``farm.tree_reward``). O formato antigo (base e passo da internet, 0041) não bate com a captura.

Revision ID: 0093
Revises: 0092
Create Date: 2026-10-28 13:00:00.000000

(visto) oficial_20261025-232017-1 #218-#227 (grau 6) e oficial_20261027-152321-1 #5075-#5086 (grau 10).
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0093"
down_revision = "0092"
branch_labels = None
depends_on = None

NEW = {"6": {"daru": 6100, "kyanite": 2400, "gold": 160}, "10": {"daru": 12500, "kyanite": 3400, "gold": 300}}
SOURCE = (
    "colheita da árvore por grau da fazenda: (visto) oficial_20261025-232017-1 #218-#227 (grau 6: 6.100 Daru, 2.400 "
    "Kyanite, 160 de ouro) e oficial_20261027-152321-1 #5075-#5086 (grau 10: 12.500, 3.400, 300). O resto é reta "
    "entre eles (TODO(inventado))"
)
OLD = {"daru": [3800, 3800], "kyanite": [1000, 100]}  # 0041, para o downgrade


def _settings() -> sa.TableClause:
    return sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def upgrade() -> None:
    t = _settings()
    op.execute(t.update().where(t.c.key == "tree_fruit").values(value=json.dumps(NEW), source=SOURCE))


def downgrade() -> None:
    t = _settings()
    op.execute(t.update().where(t.c.key == "tree_fruit").values(value=json.dumps(OLD)))
