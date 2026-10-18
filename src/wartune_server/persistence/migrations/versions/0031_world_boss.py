"""World Boss: a config de cada chefe e dos prêmios, e o estado de cada janela (vida, dano, último golpe)

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-18 20:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

WIKI = "(internet) https://wartune.fandom.com/wiki/World_BOSS"
# (cliente) PreLoadWorldBoss.as: os mapas 5001 e 5003 usam o herói 2001 (o nome das campanhas diria 2002/2003)
# (dedução) son_type 2145 (o lobo-chefe da masmorra, arte no CDN), nó no centro de cima e entrada embaixo do mapa
# 1600x1700 (80x85 tiles); crescer 20%/cair 10% (a wiki só diz que sobe com abate rápido e desce com lento)
BOSS = {
    "hero_id": 2001, "son_type": 2145, "node_x": 40, "node_y": 30, "start_x": 40, "start_y": 70,
    "base_hp": 2_000_000, "min_hp": 2_000_000, "fast_seconds": 600, "grow_pct": 20, "shrink_pct": 10,
    "kill_turn": 6, "revive_seconds": 30, "damage_per_gold": 5, "battle_cap": 10_000_000,
    "last_hit_gold": 1_500_000, "last_hit_daru": 0,
    "source": f"hero_id/base_hp: cliente (PreLoadWorldBoss.as, GameHeroTemp Live); {WIKI}: 'under 10 minutes' "
    "(Doly reflecting-on-world-boss-in-dec-2016), 'kill you on the sixth', 'wait 30 seconds', 'ratio of 1:5', "
    "10M por luta (Patch 7.8), último golpe 'e.g. 1.5 million or 1.7 million gold'; son_type, nó e % (dedução)",
}  # fmt: skip
# (kind, rank_from, rank_to, share, gold, daru, source): rank = top 10 da classe; share = fração do dano total
REWARDS = [
    ("rank", 1, 1, 0.0, 300_000, 300_000, f"{WIKI}: Apollo Prize 300,000 1st (por classe)"),
    ("rank", 2, 2, 0.0, 270_000, 270_000, f"{WIKI}: 270,000 2nd"),
    ("rank", 3, 3, 0.0, 240_000, 240_000, f"{WIKI}: 240,000 3rd"),
    ("rank", 4, 10, 0.0, 180_000, 180_000, f"{WIKI}: 180,000 4th to 10th"),
    ("share", 0, 0, 0.003, 60_000, 60_000, f"{WIKI}?oldid=19424: 0.3% = 60k gold and daru"),
    ("share", 0, 0, 0.005, 120_000, 120_000, f"{WIKI}?oldid=19424: 0.5% = 120k"),
    ("share", 0, 0, 0.008, 180_000, 180_000, f"{WIKI}?oldid=19424: 0.8% = 180k"),
]


def _int(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), server_default="0", nullable=False)


def upgrade() -> None:
    bosses = op.create_table(
        "world_bosses",
        sa.Column("campaign_id", sa.Integer(), autoincrement=False, nullable=False),
        *(_int(name) for name in BOSS if name != "source"),
        sa.Column("source", sa.String(length=1000), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("campaign_id", name=op.f("pk_world_bosses")),
    )
    op.bulk_insert(bosses, [{"campaign_id": c, **BOSS} for c in (5001, 5003)])
    rewards = op.create_table(
        "world_boss_rewards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        _int("rank_from"),
        _int("rank_to"),
        sa.Column("share", sa.Float(), server_default="0", nullable=False),
        _int("gold"),
        _int("daru"),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_boss_rewards")),
    )
    keys = ("kind", "rank_from", "rank_to", "share", "gold", "daru", "source")
    op.bulk_insert(rewards, [dict(zip(keys, row, strict=True)) for row in REWARDS])
    op.create_table(
        "world_boss_fights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _int("campaign_id"),
        sa.Column("opened_at", UTCDateTime(), nullable=False),
        _int("total_hp"),
        _int("killer_id"),
        sa.Column("killed_at", UTCDateTime(), nullable=True),
        sa.Column("settled", sa.Boolean(), server_default="0", nullable=False),
        _int("next_hp"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_boss_fights")),
        sa.UniqueConstraint("campaign_id", "opened_at", name=op.f("uq_world_boss_fights_campaign_id_opened_at")),
    )
    op.create_table(
        "world_boss_wounds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _int("fight_id"),
        _int("character_id"),
        sa.Column("nickname", sa.String(length=64), server_default="", nullable=False),
        _int("job"),
        _int("wound"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_boss_wounds")),
        sa.UniqueConstraint("fight_id", "character_id", name=op.f("uq_world_boss_wounds_fight_id_character_id")),
    )


def downgrade() -> None:
    op.drop_table("world_boss_wounds")
    op.drop_table("world_boss_fights")
    op.drop_table("world_boss_rewards")
    op.drop_table("world_bosses")
