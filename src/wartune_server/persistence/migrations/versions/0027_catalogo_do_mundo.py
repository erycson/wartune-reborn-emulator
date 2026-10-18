"""catálogo do mundo no banco (minas, guardas, castelos-robô e chefes do mapa) e o nível da mina ocupada

A semente é o que as capturas mostram (docs/cidade-externa.md). O .maps do mapa 100 do cliente só tem
decoração (sem minas nem robôs) e o tempinfos não liga mina a guarda, então não há fonte melhor.

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-18 21:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

# replay #706 e cevre #11: mesmos ids e tiles em contas diferentes (modelo do mapa 100). Nível: as duas
# capturas têm 8, 9 e 10 (dedução: sorteado a cada ciclo)
MINES = [(853876, 16, 34), (853877, 36, 34), (853874, 71, 54), (853875, 54, 64)]
# visto: 6504 no nível 8 (replay), 6505 nos níveis 9 e 10 (replay e cevre)
GUARDS = [(8, 6504), (9, 6505), (10, 6505)]
# replay #706 e cevre #11: 765958 em (44,22) e 765957 em (59,56); grau 8 em 3 dos 4 castelos vistos
ROBOTS = [(765958, 44, 22), (765957, 59, 56)]
# visto: ♣Chloe♣, ♫Elizabeth♫, ►Abigail◄
ROBOT_NAMES = [("Chloe", "♣", "♣"), ("Elizabeth", "♫", "♫"), ("Abigail", "►", "◄")]
# transfer: bosslist do mapa 2 (template pelo nome e grau no tempinfos turco da captura)
BOSSES = [(210106, 1540, 3323), (210124, 1239, 2870), (210129, 739, 388), (210129, 2164, 2112), (210120, 1865, 527)]


def _int(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), server_default="0", nullable=False)


def upgrade() -> None:
    with op.batch_alter_table("wild_lands") as batch:
        batch.add_column(_int("template_id"))
        batch.add_column(_int("pos_x"))
        batch.add_column(_int("pos_y"))
    mines = op.create_table(
        "world_mines",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        _int("position"), _int("map_id"), _int("pos_x"), _int("pos_y"), _int("min_level"), _int("max_level"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_mines")),
    )  # fmt: skip
    guards = op.create_table(
        "world_mine_guards",
        sa.Column("level", sa.Integer(), autoincrement=False, nullable=False),
        _int("pawn_id"),
        sa.PrimaryKeyConstraint("level", name=op.f("pk_world_mine_guards")),
    )
    robots = op.create_table(
        "world_robots",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        _int("position"), _int("map_id"), _int("pos_x"), _int("pos_y"), _int("grade"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_robots")),
    )  # fmt: skip
    names = op.create_table(
        "world_robot_names",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=32), server_default="", nullable=False),
        sa.Column("prefix", sa.String(length=8), server_default="", nullable=False),
        sa.Column("suffix", sa.String(length=8), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_robot_names")),
    )
    bosses = op.create_table(
        "map_boss_spawns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _int("map_id"), _int("template_id"), _int("pos_x"), _int("pos_y"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_map_boss_spawns")),
    )  # fmt: skip
    op.bulk_insert(mines, [
        {"id": i, "position": n, "map_id": 100, "pos_x": x, "pos_y": y, "min_level": 8, "max_level": 10}
        for n, (i, x, y) in enumerate(MINES)
    ])  # fmt: skip
    op.bulk_insert(guards, [{"level": lv, "pawn_id": p} for lv, p in GUARDS])
    op.bulk_insert(robots, [
        {"id": i, "position": n, "map_id": 100, "pos_x": x, "pos_y": y, "grade": 8}
        for n, (i, x, y) in enumerate(ROBOTS)
    ])  # fmt: skip
    op.bulk_insert(names, [{"name": n, "prefix": a, "suffix": b} for n, a, b in ROBOT_NAMES])
    op.bulk_insert(bosses, [{"map_id": 2, "template_id": t, "pos_x": x, "pos_y": y} for t, x, y in BOSSES])


def downgrade() -> None:
    for table in ("map_boss_spawns", "world_robot_names", "world_robots", "world_mine_guards", "world_mines"):
        op.drop_table(table)
    with op.batch_alter_table("wild_lands") as batch:
        batch.drop_column("pos_y")
        batch.drop_column("pos_x")
        batch.drop_column("template_id")
