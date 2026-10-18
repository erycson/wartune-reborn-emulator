"""Lê o catálogo do mundo (tabelas ``world_*``, semente nas migrações 0027 e 0028)."""

from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..domain.world import Mine, MonsterTemplate, RobotCastle, RobotName, World
from .schema import (
    world_mine_guards,
    world_mines,
    world_monster_counts,
    world_monsters,
    world_robot_names,
    world_robots,
)


async def load(engine: AsyncEngine) -> World:
    async with engine.connect() as conn:
        mines = await conn.execute(select(world_mines).order_by(world_mines.c.position))
        guards = await conn.execute(select(world_mine_guards))
        robots = await conn.execute(select(world_robots).order_by(world_robots.c.position))
        names = await conn.execute(select(world_robot_names).order_by(world_robot_names.c.id))
        counts: defaultdict[int, dict[int, int]] = defaultdict(dict)
        for r in await conn.execute(select(world_monster_counts)):
            counts[r.map_id][r.boss_type] = r.quantity
        monsters = await conn.execute(select(world_monsters))
        return World(
            mines=tuple(Mine(r.id, r.map_id, r.pos_x, r.pos_y, r.min_level, r.max_level) for r in mines),
            mine_guards=MappingProxyType({r.level: r.pawn_id for r in guards}),
            robots=tuple(RobotCastle(r.id, r.map_id, r.pos_x, r.pos_y, r.grade) for r in robots),
            robot_names=tuple(RobotName(r.name, r.prefix, r.suffix) for r in names),
            monster_counts=MappingProxyType({m: MappingProxyType(c) for m, c in counts.items()}),
            monsters=MappingProxyType(
                {
                    r.template_id: MonsterTemplate(r.template_id, r.pawn_id, r.hero_id, r.fight_capacity)
                    for r in monsters
                }
            ),
        )
