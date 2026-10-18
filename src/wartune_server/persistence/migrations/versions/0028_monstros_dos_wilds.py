"""monstros dos Wilds: quantos de cada tipo por mapa, poder visto e a névoa tirada pela Divine Light

Os monstros saem de um sorteio por (mapa, ciclo) (game/monsters.py), então ``map_boss_spawns`` (a foto do
bosslist de um ciclo da transfer) deixa de ser a fonte: os chefes do painel são os monstros de tipo 3.

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-18 23:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

# bossType 3 (chefe): 5 no mapa 2 (visto, bosslist da transfer). Normais e elites: sem captura nem fonte na
# Internet; (dedução) na proporção do limite diário WorldMapKill 5,3,1. Os mapas 1, 3, 4 e 5 copiam o 2.
COUNTS = [(m, t, n) for m in (1, 2, 3, 4, 5) for t, n in ((1, 40), (2, 20), (3, 5))]
POWER = [(210127, 746796)]  # visto: transfer #14 (fightCapaity); os outros templates não têm fonte
BOSSES = [(210106, 1540, 3323), (210124, 1239, 2870), (210129, 739, 388), (210129, 2164, 2112), (210120, 1865, 527)]


def _int(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), server_default="0", nullable=False)


def upgrade() -> None:
    counts = op.create_table(
        "world_monster_counts",
        sa.Column("map_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("boss_type", sa.Integer(), autoincrement=False, nullable=False),
        _int("quantity"),
        sa.PrimaryKeyConstraint("map_id", "boss_type", name=op.f("pk_world_monster_counts")),
    )
    power = op.create_table(
        "world_monster_power",
        sa.Column("template_id", sa.Integer(), autoincrement=False, nullable=False),
        _int("fight_capacity"),
        sa.PrimaryKeyConstraint("template_id", name=op.f("pk_world_monster_power")),
    )
    op.bulk_insert(counts, [{"map_id": m, "boss_type": t, "quantity": n} for m, t, n in COUNTS])
    op.bulk_insert(power, [{"template_id": t, "fight_capacity": f} for t, f in POWER])
    op.drop_table("map_boss_spawns")
    with op.batch_alter_table("characters") as batch:
        batch.add_column(_int("fog_map"))
        batch.add_column(sa.Column("fog_until", UTCDateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("fog_until")
        batch.drop_column("fog_map")
    bosses = op.create_table(
        "map_boss_spawns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _int("map_id"), _int("template_id"), _int("pos_x"), _int("pos_y"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_map_boss_spawns")),
    )  # fmt: skip
    op.bulk_insert(bosses, [{"map_id": 2, "template_id": t, "pos_x": x, "pos_y": y} for t, x, y in BOSSES])
    op.drop_table("world_monster_power")
    op.drop_table("world_monster_counts")
