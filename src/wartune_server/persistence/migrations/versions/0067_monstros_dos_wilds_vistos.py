"""monstros dos Wilds: o poder visto no 4129 e o baú do normal de nível 10

(visto) oficial_20261023-171155-1:
- ``fightCapaity`` do 4129/140 de 14 monstros do mapa 1 (o 210127 já estava, 746796, e bate);
- o baú do Tauren Gladiator (210101, normal nível 10) duas vezes igual (#6974-#6988 e #7385): Mystery Stone x1,
  10.000 de Daru e 10.000 de ouro, sem Kyanite. Troca as linhas da 0030 da faixa normal 10-29 (internet e dedução:
  ouro 5-10k, Kyanite 500-1000 a 80%, Daru 2,5-5k a 30%) e a Mystery x2 a 50% passa a valer do nível 30 em diante.

Revision ID: 0067
Revises: 0066
Create Date: 2026-10-24 11:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None

POWER = {
    210101: 1033, 210102: 4524, 210103: 6519, 210110: 14802, 210113: 17100, 210114: 48588, 210115: 145477,
    210117: 22093, 210118: 102925, 210120: 598159, 210121: 29454, 210122: 324572, 210126: 39868, 210128: 1182575,
}  # fmt: skip
NORMAL, GOLD, DARU, KYANITE, MYSTERY = 1, -100, -300, -600, 2131057
SEEN = "(visto) oficial_20261023-171155-1 #6974-#6988 e #7385: baú do normal nível 10"
NEW = [(NORMAL, 10, 29, GOLD, 1.0, 10_000, 10_000, SEEN), (NORMAL, 10, 29, DARU, 1.0, 10_000, 10_000, SEEN),
       (NORMAL, 10, 29, MYSTERY, 1.0, 1, 1, SEEN)]  # fmt: skip
WIKI = "(internet) https://wartune.fandom.com/wiki/Wilds"
OLD = [(NORMAL, 10, 29, GOLD, 1.0, 5_000, 10_000, f"{WIKI}: usually"),
       (NORMAL, 10, 29, KYANITE, 0.8, 500, 1_000, f"{WIKI}: usually"),
       (NORMAL, 10, 29, DARU, 0.3, 2_500, 5_000, f"{WIKI}: can drop")]  # fmt: skip
KEYS = ("boss_type", "min_level", "max_level", "template_id", "chance", "min_count", "max_count", "source")


def _drops() -> sa.TableClause:
    return sa.table("world_monster_drops", *(sa.column(k) for k in KEYS))


def _swap(add: Sequence[tuple[object, ...]], mystery_from: tuple[int, int]) -> None:
    t = _drops()
    op.execute(t.delete().where(t.c.boss_type == NORMAL, t.c.min_level == 10, t.c.max_level == 29))
    op.bulk_insert(t, [dict(zip(KEYS, row, strict=True)) for row in add])
    old, new = mystery_from
    op.execute(
        t.update()
        .where(t.c.boss_type == NORMAL, t.c.template_id == MYSTERY, t.c.min_level == old, t.c.max_level == 200)
        .values(min_level=new)
    )


def _power(values: dict[int, int]) -> None:
    t = sa.table("world_monsters", sa.column("template_id"), sa.column("fight_capacity"))
    for template_id, power in values.items():
        op.execute(t.update().where(t.c.template_id == template_id).values(fight_capacity=power))


def upgrade() -> None:
    _power(POWER)
    _swap(NEW, (1, 30))


def downgrade() -> None:
    _power({t: 0 for t in POWER})
    _swap(OLD, (30, 1))
