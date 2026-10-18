"""Lê o catálogo do mundo (tabelas ``world_*``, semente nas migrações 0027 e 0028)."""

from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..domain.world import (
    Mine,
    MonsterDrop,
    MonsterTemplate,
    RobotCastle,
    RobotName,
    World,
    WorldBoss,
    WorldBossReward,
)
from .schema import (
    world_boss_rewards,
    world_bosses,
    world_mine_guards,
    world_mines,
    world_monster_counts,
    world_monster_drops,
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
        drops = await conn.execute(select(world_monster_drops).order_by(world_monster_drops.c.id))
        bosses = await conn.execute(select(world_bosses))
        boss_rewards = await conn.execute(select(world_boss_rewards).order_by(world_boss_rewards.c.id))
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
            monster_drops=tuple(
                MonsterDrop(r.boss_type, r.min_level, r.max_level, r.template_id, r.chance, r.min_count, r.max_count)
                for r in drops
            ),
            world_bosses=MappingProxyType(
                {r.campaign_id: WorldBoss(**{k: v for k, v in r._mapping.items() if k != "source"}) for r in bosses}
            ),
            world_boss_rewards=tuple(
                WorldBossReward(r.kind, r.rank_from, r.rank_to, r.share, r.gold, r.daru) for r in boss_rewards
            ),
        )
