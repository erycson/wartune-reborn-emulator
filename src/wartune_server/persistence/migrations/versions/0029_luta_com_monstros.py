"""luta com os monstros dos Wilds: a unidade de cada monstro, os abates do ciclo e os contadores do dia

A unidade sai do tempinfos pelo nome (visto: mesmo nome e mesmo nível em ``PawnTempInfos`` ou ``GameHeroTemp``,
os heróis com ``AddName`` "Elite"/"BOSS"). O nome é ambíguo (o "Red Claw" de nível 20 tem 4 pawns), então
o vínculo vai explícito: normais na série 6992-6999, elites e chefes na série 2978-2999. A névoa sai do
personagem: o help diz que a Divine Light de qualquer um limpa o mapa, e 20 s não precisam de banco.

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-19 01:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

PAWNS = {210101: 6992, 210104: 6993, 210107: 6994, 210110: 6995, 210113: 6996, 210117: 6997, 210121: 6998,
         210126: 6999}  # fmt: skip
HEROES = dict(
    zip(
        (210102, 210103, 210105, 210106, 210108, 210109, 210111, 210112, 210114, 210115, 210116, 210118, 210119,
         210120, 210122, 210123, 210124, 210125, 210127, 210128, 210129, 210130),
        range(2978, 3000),
        strict=True,
    )
)  # fmt: skip
KILLS = ("kills_normal", "kills_elite", "kills_boss")


def _int(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), server_default="0", nullable=False)


def upgrade() -> None:
    op.rename_table("world_monster_power", "world_monsters")
    with op.batch_alter_table("world_monsters") as batch:
        batch.add_column(_int("pawn_id"))
        batch.add_column(_int("hero_id"))
    monsters = sa.table(
        "world_monsters",
        sa.column("template_id", sa.Integer()),
        sa.column("pawn_id", sa.Integer()),
        sa.column("hero_id", sa.Integer()),
        sa.column("fight_capacity", sa.Integer()),
    )
    op.execute(monsters.delete().where(monsters.c.template_id != 210127))
    op.execute(monsters.update().where(monsters.c.template_id == 210127).values(hero_id=HEROES[210127]))
    op.bulk_insert(monsters, [{"template_id": t, "pawn_id": p, "hero_id": 0, "fight_capacity": 0}
                              for t, p in PAWNS.items()])  # fmt: skip
    op.bulk_insert(monsters, [{"template_id": t, "pawn_id": 0, "hero_id": h, "fight_capacity": 0}
                              for t, h in HEROES.items() if t != 210127])  # fmt: skip
    op.create_table(
        "wild_monster_kills",
        sa.Column("map_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("monster_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("cycle_at", UTCDateTime(), nullable=False),
        _int("character_id"),
        sa.Column("killed_at", UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("map_id", "monster_id", "cycle_at", name=op.f("pk_wild_monster_kills")),
    )
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("fog_until")
        batch.drop_column("fog_map")
        for name in KILLS:
            batch.add_column(_int(name))


def downgrade() -> None:
    with op.batch_alter_table("characters") as batch:
        for name in reversed(KILLS):
            batch.drop_column(name)
        batch.add_column(_int("fog_map"))
        batch.add_column(sa.Column("fog_until", UTCDateTime(), nullable=True))
    op.drop_table("wild_monster_kills")
    monsters = sa.table("world_monsters", sa.column("template_id", sa.Integer()))
    op.execute(monsters.delete().where(monsters.c.template_id != 210127))
    with op.batch_alter_table("world_monsters") as batch:
        batch.drop_column("hero_id")
        batch.drop_column("pawn_id")
    op.rename_table("world_monsters", "world_monster_power")
