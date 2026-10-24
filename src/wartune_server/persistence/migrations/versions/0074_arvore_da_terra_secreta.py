"""terra secreta: a árvore da guilda (nível, EXP, energia, invocação) e o que cada membro fez nela

Regras em ``game/fam.py`` (cliente ``ConsortiaSecretInfo``, ``UpGradeTempInfos`` tipo 20, ajuda da terra secreta).
``game_settings.fam_tree``: TODO(inventado) EXP por tique (``exp_per_grade``), o bônus da energia (``power_step``,
``power_rate``) e a contribuição por coleta (``collect_offer``); nem cliente nem captura dizem os valores.

Revision ID: 0074
Revises: 0073
Create Date: 2026-10-24 16:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None

KEY = "fam_tree"
SOURCE = "TODO(inventado): a ajuda do cliente não dá os valores (EXP por tique, bônus da energia, coleta)"


def upgrade() -> None:
    with op.batch_alter_table("consortias") as batch:
        batch.add_column(sa.Column("tree_grade", sa.Integer(), server_default="1", nullable=False))
        batch.add_column(sa.Column("tree_gp", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("tree_power", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("tree_called_at", UTCDateTime(), nullable=True))
    with op.batch_alter_table("consortia_members") as batch:
        batch.add_column(sa.Column("fam_power_at", UTCDateTime(), nullable=True))
        batch.add_column(sa.Column("fam_buff_at", UTCDateTime(), nullable=True))
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    value = {"exp_per_grade": 2, "power_step": 10, "power_rate": 0.1, "collect_offer": 5}
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(value), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    with op.batch_alter_table("consortia_members") as batch:
        batch.drop_column("fam_buff_at")
        batch.drop_column("fam_power_at")
    with op.batch_alter_table("consortias") as batch:
        batch.drop_column("tree_called_at")
        batch.drop_column("tree_power")
        batch.drop_column("tree_gp")
        batch.drop_column("tree_grade")
