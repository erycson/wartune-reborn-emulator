"""vida do herói

``heroes.hp``: vida atual do líder (0 = cheia). A derrota deixa 1 e a reserva das poções (``blood``) completa depois
da luta, na compra da poção e ao vestir um item que sobe a vida máxima (oficial_20261023-153200-1 #774, #804-#807,
#1320-#1332, #2182-#2185: "Used HP pack to restore HP.").

``game_settings.hero_free_heal_grade``: abaixo deste nível a vida volta cheia de graça depois da luta. (cliente)
``BaseManager.showAlertTip`` só avisa da falta de poção a partir do nível 10; no tutorial (níveis 1 a 10) o herói chega
a 0 e volta cheio sem reserva.

Revision ID: 0059
Revises: 0058
Create Date: 2026-10-23 23:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None

KEY = "hero_free_heal_grade"
SOURCE = "(cliente) BaseManager.showAlertTip: grades >= 10; (visto) tutorial_en #1466, #1657"


def upgrade() -> None:
    with op.batch_alter_table("heroes") as batch:
        batch.add_column(sa.Column("hp", sa.Integer(), server_default="0", nullable=False))
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(10), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    with op.batch_alter_table("heroes") as batch:
        batch.drop_column("hp")
