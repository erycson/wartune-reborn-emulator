"""fazenda de amigo, amizade e bônus da coleção de cartas

``castles``: contadores do dia da fazenda (EXP de amigos, roubos, regas da própria árvore e de amigos) com o dia
do jogo em ``farm_day``. ``farm_lands.stolen_by``: quem já roubou a terra (``stolenUsers``). ``relations``: a
amizade (``friend_gp``, o "Friendship + 1" de ciftlik #87) e o dia em que regou a árvore do outro (``tree_day``).
``game_settings``: os números sem fonte melhor que a Internet ou dedução (ver docs/castelo.md e heroi-exercito.md).

Revision ID: 0038
Revises: 0035
Create Date: 2026-10-19 13:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0035"
branch_labels = None
depends_on = None

CASTLE_INTS = ("farm_friend_gp", "farm_steals", "tree_water_today", "tree_friend_today")
SETTINGS = [
    (
        "farm_steal_percent",
        10,
        "(internet) https://breezewiki.discard.no/wartune/wiki/Farm (espelho de wartune.fandom.com/wiki/Farm): "
        "o amigo leva 'a small portion of the plant's value (10%)', até 3 vezes; % do rewardCount por roubo",
    ),
    (
        "friend_grade_step",
        10,
        "(dedução) grau de amizade = 1 + amizade // passo; ciftlik #85: grau 4 com 34 pontos. Tabela real: captura",
    ),
    (
        "powcard_suite_slots",
        [[4, 1], [4, 3], [4, 8]],
        "(dedução) [cartas, grau mínimo] de cada degrau do bônus da coleção; language EN "
        "card.CardSlotView.Notactive0..2 ('4 cards', '3 level 4 cards', '8 level 4 cards'); login #76: só a "
        "coleção com 4 cartas tem bufInfos",
    ),
]


def upgrade() -> None:
    with op.batch_alter_table("castles") as batch:
        batch.add_column(sa.Column("farm_day", sa.String(length=10), server_default="", nullable=False))
        for name in CASTLE_INTS:
            batch.add_column(sa.Column(name, sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("farm_lands") as batch:
        batch.add_column(sa.Column("stolen_by", sa.String(length=255), server_default="", nullable=False))
    with op.batch_alter_table("relations") as batch:
        batch.add_column(sa.Column("friend_gp", sa.Integer(), server_default="0", nullable=False))
        batch.add_column(sa.Column("tree_day", sa.String(length=10), server_default="", nullable=False))
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": k, "value": json.dumps(v), "source": s} for k, v, s in SETTINGS])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([k for k, _, _ in SETTINGS])))
    with op.batch_alter_table("relations") as batch:
        batch.drop_column("tree_day")
        batch.drop_column("friend_gp")
    with op.batch_alter_table("farm_lands") as batch:
        batch.drop_column("stolen_by")
    with op.batch_alter_table("castles") as batch:
        for name in reversed(CASTLE_INTS):
            batch.drop_column(name)
        batch.drop_column("farm_day")
