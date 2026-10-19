"""Lê o catálogo do mundo (``world_*`` e ``campaign_*``: migrações 0027, 0028 e 0034) e as regras de evento (0033)."""

from __future__ import annotations

import json
from collections import defaultdict
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..domain.world import (
    ExpRate,
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
    campaign_cards,
    campaign_contents,
    exp_rate_events,
    game_settings,
    vip_wheel_prizes,
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
        settings = await conn.execute(select(game_settings))
        wheel = await conn.execute(select(vip_wheel_prizes).order_by(vip_wheel_prizes.c.position))
        rates = await conn.execute(select(exp_rate_events).order_by(exp_rate_events.c.id))
        contents = await conn.execute(select(campaign_contents))
        cards: defaultdict[int, list[tuple[int, float]]] = defaultdict(list)
        for r in await conn.execute(select(campaign_cards).order_by(campaign_cards.c.id)):
            cards[r.campaign_id].append((r.template_id, r.weight))
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
            settings=MappingProxyType({r.key: json.loads(r.value) for r in settings}),
            vip_wheel=tuple((r.template_id, r.quantity) for r in wheel),
            exp_rates=tuple(
                ExpRate(r.rate, r.begin_day, r.end_day, r.begin_time, r.end_time, r.buffer_type) for r in rates
            ),
            campaigns=MappingProxyType({r.campaign_id: json.loads(r.data) for r in contents}),
            campaign_cards=MappingProxyType({c: tuple(v) for c, v in cards.items()}),
        )
