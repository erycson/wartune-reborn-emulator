"""Lê o catálogo do mundo (tabelas ``world_*`` e ``map_boss_spawns``, semente na migração 0027)."""

from __future__ import annotations

from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..domain.world import BossSpawn, Mine, RobotCastle, RobotName, World
from .schema import map_boss_spawns, world_mine_guards, world_mines, world_robot_names, world_robots


async def load(engine: AsyncEngine) -> World:
    async with engine.connect() as conn:
        mines = await conn.execute(select(world_mines).order_by(world_mines.c.position))
        guards = await conn.execute(select(world_mine_guards))
        robots = await conn.execute(select(world_robots).order_by(world_robots.c.position))
        names = await conn.execute(select(world_robot_names).order_by(world_robot_names.c.id))
        bosses = await conn.execute(select(map_boss_spawns).order_by(map_boss_spawns.c.id))
        return World(
            mines=tuple(Mine(r.id, r.map_id, r.pos_x, r.pos_y, r.min_level, r.max_level) for r in mines),
            mine_guards=MappingProxyType({r.level: r.pawn_id for r in guards}),
            robots=tuple(RobotCastle(r.id, r.map_id, r.pos_x, r.pos_y, r.grade) for r in robots),
            robot_names=tuple(RobotName(r.name, r.prefix, r.suffix) for r in names),
            bosses=tuple(BossSpawn(r.map_id, r.template_id, r.pos_x, r.pos_y) for r in bosses),
        )
