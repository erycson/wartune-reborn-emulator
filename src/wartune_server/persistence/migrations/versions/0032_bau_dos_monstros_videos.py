"""baú dos monstros dos Wilds, níveis 60-80: a tabela de queda lida em 35 baús de vídeos

Cada vídeo mostra o texto "Wilds Slayer Rewards: ..." ao pegar o baú; o contador "Today's Reward Attempts" confirma
o tipo (18 BOSS: 12 Lv80, 4 Lv70, 2 Lv60; 13 Elite; 5 Normal de Lv~80). As chances são a frequência vista
(amostra pequena); quantidade fixa onde todos os baús deram a mesma. Abaixo de 60 vale a 0030. A raridade de
ouro de milhões (wiki) fica: nenhum dos 35 a mostrou, o que não a desmente. Lista dos baús e vídeos em
``docs/cidade-externa.md`` (Tabela de queda).

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-18 18:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

NORMAL, ELITE, BOSS = 1, 2, 3
GOLD, DARU, KYANITE = -100, -300, -600
MYSTERY, SOUL, WHIP, FATE, RUNE, CORE, LIGHT = 2131057, 208014, 208017, 208024, 3020010, 2131056, 2131055
KEY, SHADOW, GEMS = 208005, 208012, 2060010  # Skeleton Key, Shadow Crystal, Lvl. 3 Gem Pack (dedução: o de 1 gema)
LEGENDARY = {60: 2129600, 70: 2129700, 80: 2129800}
FROM = 60
BANDS = ((60, 69), (70, 79), (80, 200))
VIDEOS = "(internet) 35 baús em vídeos do YouTube, docs/cidade-externa.md"
# (tipo, item, chance): quantidade por faixa de BANDS (None = não cai nela)
SEEN = {
    (BOSS, MYSTERY, 1.0): (8, 8, 8),
    (BOSS, MYSTERY, 0.4): (5, 6, 6),  # a 2ª pilha, mostrada separada
    (BOSS, GOLD, 1.0): (150_000, 180_000, 200_000),
    (BOSS, DARU, 0.25): (150_000, 180_000, 200_000),
    (BOSS, KYANITE, 0.3): (6_000, 8_000, 10_000),
    (BOSS, SHADOW, 0.3): (6, 7, 8),
    (BOSS, LIGHT, 0.5): (1, 1, 1),
    (BOSS, CORE, 0.3): (1, 1, 1),
    (BOSS, RUNE, 0.35): (6, 8, 10),
    (BOSS, WHIP, 0.25): (6, 7, 8),
    (BOSS, FATE, 0.15): (6, 7, 8),
    (BOSS, GEMS, 0.25): (3, 3, 3),
    (BOSS, KEY, 0.1): (3, 4, 5),
    (BOSS, SOUL, 0.1): (12, 16, 20),
    (ELITE, GOLD, 1.0): (70_000, 80_000, 100_000),
    (ELITE, MYSTERY, 0.7): (4, 5, 5),
    (ELITE, DARU, 0.4): (70_000, 80_000, 100_000),
    (ELITE, KYANITE, 0.4): (4_500, 4_500, 4_500),
    (ELITE, FATE, 0.45): (3, 3, 4),
    (ELITE, SOUL, 0.4): (5, 8, 13),
    (ELITE, CORE, 0.25): (1, 1, 1),
    (ELITE, LIGHT, 0.15): (1, 1, 1),
    (ELITE, KEY, 0.15): (3, 3, 3),
    (ELITE, SHADOW, 0.1): (6, 6, 6),
    (ELITE, RUNE, 0.1): (5, 5, 5),
    (ELITE, WHIP, 0.1): (3, 3, 3),
    (NORMAL, GOLD, 1.0): ((30_000, 40_000), (40_000, 50_000), (40_000, 50_000)),
    (NORMAL, KYANITE, 0.6): (2_500, 3_500, 3_500),
    (NORMAL, DARU, 0.2): (40_000, 50_000, 50_000),
    (NORMAL, SHADOW, 0.2): (5, 5, 5),
    (NORMAL, MYSTERY, 0.2): (2, 2, 2),
}  # fmt: skip
RARE = (2_000_000, 1_000_000)  # min_count da raridade de ouro (BOSS, ELITE) da 0030: fica em todo nível


def _rows() -> list[dict[str, object]]:
    rows = []
    for (kind, item, chance), per_band in SEEN.items():
        for (lo, hi), count in zip(BANDS, per_band, strict=True):
            a, b = count if isinstance(count, tuple) else (count, count)
            rows.append({"boss_type": kind, "min_level": lo, "max_level": hi, "template_id": item, "chance": chance,
                         "min_count": a, "max_count": b, "source": VIDEOS})  # fmt: skip
    for (lo, hi), item in zip(BANDS, LEGENDARY.values(), strict=True):
        count = 3 if lo >= 80 else 2  # (visto) x2 no 60 e no 70, x3 no 80, em todo baú de BOSS
        rows.append({"boss_type": BOSS, "min_level": lo, "max_level": hi, "template_id": item, "chance": 1.0,
                     "min_count": count, "max_count": count, "source": VIDEOS})  # fmt: skip
    return rows


def upgrade() -> None:
    drops = sa.table(
        "world_monster_drops",
        *(sa.column(c) for c in ("boss_type", "min_level", "max_level", "template_id", "min_count", "max_count")),
        sa.column("chance"),
        sa.column("source"),
    )
    keep_rare = sa.not_(sa.and_(drops.c.template_id == GOLD, drops.c.min_count.in_(RARE)))
    op.execute(drops.delete().where(drops.c.min_level >= FROM, keep_rare))
    op.execute(drops.update().where(drops.c.max_level >= FROM, keep_rare).values(max_level=FROM - 1))
    op.bulk_insert(drops, _rows())


def downgrade() -> None:
    raise NotImplementedError("a 0030 não guarda as linhas de 60+ que esta substitui; recrie o banco")
