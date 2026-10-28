"""Chefe do mundo como o oficial: os 4 nós do mapa (entrada, chefe, portal e a barreira que some quando ele nasce), o
herói, a vida e o último golpe das capturas

Revision ID: 0092
Revises: 0091
Create Date: 2026-10-28 12:00:00.000000

(visto) oficial_20261027-152321-1 #1399 (5001) e oficial_20261026-225632-1 #8271 (5003): o 127; a vida no primeiro
4174 (#1415, #8288); o último golpe no 83 do fim (#3234 "800,000 Gold", #10894 "1,000,000 Gold").
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0092"
down_revision = "0091"
branch_labels = None
depends_on = None

# (visto) a vida começa no Live do herói (GameHeroTemp 2002/2003: 2.000.000) e sobe 50% a cada abate, em qualquer
# tempo dentro da janela (fast_seconds = a janela inteira)
GROWTH = {"base_hp": 2_000_000, "min_hp": 2_000_000, "grow_pct": 50, "fast_seconds": 3600}
NEW = ("gate_x", "gate_y", "gate_back_x", "gate_back_y", "portal_x", "portal_y", "fight_capacity")
BOSSES = {
    5001: {"hero_id": 2002, "son_type": 2411, "node_x": 51, "node_y": 21, "start_x": 39, "start_y": 54,
           "gate_x": 45, "gate_y": 43, "gate_back_x": 45, "gate_back_y": 46, "portal_x": 32, "portal_y": 69,
           "fight_capacity": 441705, **GROWTH, "last_hit_gold": 800_000},
    5003: {"hero_id": 2003, "son_type": 2176, "node_x": 56, "node_y": 26, "start_x": 44, "start_y": 62,
           "gate_x": 44, "gate_y": 48, "gate_back_x": 44, "gate_back_y": 51, "portal_x": 54, "portal_y": 77,
           "fight_capacity": 441705, **GROWTH, "last_hit_gold": 1_000_000},
}  # fmt: skip
SOURCE = (
    "nós, herói, vida e último golpe: capturas oficiais 23/10, 25/10, 26/10 e 27/10. Vida = Live do herói "
    "(2M) x 1,5 a cada abate: 15.187.500 = 2M x 1,5^5 (5001, 27/10), 34.171.875 = 2M x 1,5^7 (5003, 26/10); "
    "abates em 16,5 a 23 min, todos cresceram. Último golpe fixo por chefe (800k com killer nível 60 e 48, "
    "1M com nível 36 e 52). Cair sem abate (10%): internet"
)
OLD = {"hero_id": 2001, "son_type": 2145, "node_x": 40, "node_y": 30, "start_x": 40, "start_y": 70,
       "base_hp": 2_000_000, "last_hit_gold": 1_500_000, "grow_pct": 20, "fast_seconds": 600}  # fmt: skip


def _table() -> sa.TableClause:
    return sa.table("world_bosses", sa.column("campaign_id"), sa.column("source"),
                    *(sa.column(c) for c in {*NEW, *BOSSES[5001]}))  # fmt: skip


def upgrade() -> None:
    with op.batch_alter_table("world_bosses", schema=None) as batch_op:
        for name in NEW:
            batch_op.add_column(sa.Column(name, sa.Integer(), server_default="0", nullable=False))
    t = _table()
    for campaign_id, values in BOSSES.items():
        op.execute(t.update().where(t.c.campaign_id == campaign_id).values(**values, source=SOURCE))
    # as janelas antigas (vida de 2 milhões) não passam a vida para a próxima: ela começa do base_hp novo
    fights = sa.table("world_boss_fights", sa.column("next_hp"))
    op.execute(fights.update().values(next_hp=0))


def downgrade() -> None:
    t = _table()
    op.execute(t.update().values(**OLD))
    with op.batch_alter_table("world_bosses", schema=None) as batch_op:
        for name in NEW:
            batch_op.drop_column(name)
