"""baú dos monstros dos Wilds: a tabela de queda (o que cai, com que chance e quanto) e os baús fechados

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-18 15:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

NORMAL, ELITE, BOSS = 1, 2, 3
GOLD, DARU, KYANITE = -100, -300, -600
MYSTERY, SOUL, WHIP, FATE, RUNE, CORE, LIGHT = 2131057, 208014, 208017, 208024, 3020010, 2131056, 2131055
LEGENDARY = {40: 2129400, 50: 2129500, 60: 2129600, 70: 2129700, 80: 2129800}  # Lvl. N Legendary Stone
BANDS = ((10, 29), (30, 49), (50, 69), (70, 80))  # (dedução) degraus; nenhuma fonte tem tabela por nível
WIKI = "(internet) https://wartune.fandom.com/wiki/Wilds"
R2 = "(internet) forum.r2games.com 94942-what-do-you-think-of-the-wilds-events (Wayback 2024)"
# nenhuma fonte publica a chance: as chances são (dedução) a partir de "usually"/"can drop"/"very rarely" (wiki) e
# dos relatos; as quantidades de nível 70-80 vêm dos relatos e as outras faixas são (dedução) proporcionais
SCALED = {  # (tipo, item, chance): quantidade por faixa de BANDS, fonte
    (NORMAL, GOLD, 1.0): ((5_000, 10_000), (15_000, 25_000), (30_000, 50_000), (50_000, 80_000), f"{WIKI}: usually"),
    (NORMAL, KYANITE, 0.8): ((500, 1_000), (1_000, 2_000), (2_000, 4_000), (3_000, 6_000), f"{WIKI}: usually"),
    (NORMAL, DARU, 0.3): ((2_500, 5_000), (7_500, 12_500), (15_000, 25_000), (25_000, 40_000), f"{WIKI}: can drop"),
    (ELITE, GOLD, 1.0): ((10_000, 20_000), (30_000, 50_000), (50_000, 80_000), (80_000, 120_000),
                         f"{R2} p.1: elite solo 80k gold daru"),
    (ELITE, DARU, 0.5): ((10_000, 20_000), (30_000, 50_000), (50_000, 80_000), (80_000, 120_000),
                         f"{R2} p.1: elite solo 80k gold daru"),
    (BOSS, GOLD, 1.0): ((30_000, 60_000), (80_000, 120_000), (120_000, 180_000), (180_000, 220_000),
                        f"{R2} p.2: boss Lv80 200k Gold; (internet) vídeo PaRgg2jSAHE: Spirit of Light 70 180 000"),
    (BOSS, DARU, 0.5): ((30_000, 60_000), (80_000, 120_000), (120_000, 180_000), (180_000, 220_000),
                        "(internet) vídeo PaRgg2jSAHE: Spirit of Light 70 180 000 de daru"),
    (BOSS, KYANITE, 1.0): ((2_000, 4_000), (4_000, 6_000), (6_000, 9_000), (8_000, 12_000),
                           f"{R2} p.2: boss Lv80 10k Kyanite"),
}  # fmt: skip
FLAT = [  # (tipo, item, chance, mín, máx, fonte), em todo nível
    (NORMAL, MYSTERY, 0.5, 2, 2, f"{R2} p.8: normal 'either 2 or nothing', '2-4 stones out of 5'"),
    (ELITE, MYSTERY, 0.7, 2, 5, f"{R2} p.8: elite '5 stones or nothing', 'Lv50 elite 4, Lv70 elite 2'"),
    (BOSS, MYSTERY, 1.0, 10, 14, f"{R2} p.2/p.8: boss Lv80 14; 'every boss always dropped stone'"),
    (ELITE, SOUL, 0.5, 5, 10, f"{R2} p.1: elite 8 sc; {WIKI}: can drop"),
    (BOSS, SOUL, 0.8, 20, 30, f"{R2} p.2: boss Lv80 26 Soul Crystal"),
    (ELITE, CORE, 0.15, 1, 1, f"{WIKI}: can drop"),
    (BOSS, CORE, 0.3, 1, 1, f"{WIKI}: can drop"),
    (ELITE, LIGHT, 0.1, 1, 1, f"{WIKI} rev. 24193/26635: can drop (riscado na atual)"),
    (BOSS, LIGHT, 0.2, 1, 1, f"{WIKI} rev. 24193/26635: can drop (riscado na atual)"),
    (ELITE, FATE, 0.2, 1, 3, f"{WIKI}: can drop"),
    (BOSS, FATE, 0.3, 2, 5, f"{WIKI}: can drop"),
    (ELITE, WHIP, 0.2, 1, 5, f"{WIKI}: can drop; (internet) https://wartune.fandom.com/wiki/Mount_Training_Whip"),
    (BOSS, WHIP, 0.3, 2, 5, f"{WIKI}: can drop"),
    (ELITE, RUNE, 0.2, 1, 3, f"{WIKI}: can drop"),
    (BOSS, RUNE, 0.3, 2, 5, f"{WIKI}: can drop"),
    (ELITE, GOLD, 0.005, 1_000_000, 2_000_000, f"{WIKI}: very rarely; (internet) R2 130741 p.13: elite 2 million"),
    (BOSS, GOLD, 0.01, 2_000_000, 7_000_000, f"{WIKI}: up to 7 million; {R2} p.8: 7million Lv70 boss"),
]  # fmt: skip
# (boss_type, min_level, max_level, template_id, chance, min_count, max_count, source)
DROPS = [
    (t, lo, hi, item, chance, *counts, source)
    for (t, item, chance), (*per_band, source) in SCALED.items()
    for i, counts in enumerate(per_band)
    for lo, hi in [BANDS[i]]
] + [(t, 1, 200, item, chance, a, b, source) for t, item, chance, a, b, source in FLAT] + [
    (BOSS, lvl, lvl + 9, item, 1.0, 1, 3, f"{WIKI}: Legendary Stones appropriate to their level; {R2} p.2: 3 Lvl 80")
    for lvl, item in LEGENDARY.items()
]  # fmt: skip


def _int(name: str) -> sa.Column[int]:
    return sa.Column(name, sa.Integer(), server_default="0", nullable=False)


def upgrade() -> None:
    drops = op.create_table(
        "world_monster_drops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        _int("boss_type"),
        _int("min_level"),
        _int("max_level"),
        _int("template_id"),
        sa.Column("chance", sa.Float(), nullable=False),
        _int("min_count"),
        _int("max_count"),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_world_monster_drops")),
    )
    keys = ("boss_type", "min_level", "max_level", "template_id", "chance", "min_count", "max_count", "source")
    op.bulk_insert(drops, [dict(zip(keys, row, strict=True)) for row in DROPS])
    op.create_table(
        "wild_boxes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        _int("map_id"),
        _int("pos_x"),
        _int("pos_y"),
        _int("boss_type"),
        _int("grade"),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"], ["characters.id"], name=op.f("fk_wild_boxes_character_id_characters"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wild_boxes")),
    )
    op.create_index(op.f("ix_wild_boxes_character_id"), "wild_boxes", ["character_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wild_boxes_character_id"), table_name="wild_boxes")
    op.drop_table("wild_boxes")
    op.drop_table("world_monster_drops")
