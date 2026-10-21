"""nível das terras da fazenda e fruto da árvore

``castles.land_grade``: nível das terras (15044 op 9, cliente inglês ``FarmSocketSendManager.sendLandUp``, 1 a 10).
``game_settings.tree_fruit``: o que a colheita da árvore (5178) rende; o cliente não diz quanto (ver docs/castelo.md).

Revision ID: 0041
Revises: 0040
Create Date: 2026-10-20 12:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

SETTINGS = [
    (
        "tree_fruit",
        {"daru": [3800, 3800], "kyanite": [1000, 100]},
        "(internet) https://wartune.fandom.com/wiki/Farm: 'A level 1 Tree of Ancients generates ? Daru and 1000 "
        "Kyanite; each additional level up increases this by (e.g.) 3800 Daru and (e.g.) 100 or 250 Kyanite'. "
        "[base, por nível acima do 1] de Daru (-300) e Kyanite (-600). O Daru do nível 1 é dedução. "
        "Conferir com captura",
    ),
]


def upgrade() -> None:
    with op.batch_alter_table("castles") as batch:
        batch.add_column(sa.Column("land_grade", sa.Integer(), server_default="1", nullable=False))
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": k, "value": json.dumps(v), "source": s} for k, v, s in SETTINGS])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([k for k, _, _ in SETTINGS])))
    with op.batch_alter_table("castles") as batch:
        batch.drop_column("land_grade")
