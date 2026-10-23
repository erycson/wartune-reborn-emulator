"""Minas de ouro dos mapas do mundo (1 a 5)

``world_mines``: as 60 minas vistas no mapa 1 (id e tile do oficial; o nível é sorteado a cada ciclo na faixa do mapa).
``world_mine_guards``: guarda por nível de 11 a 60. ``wild_lands``: o mapa, o ciclo do mundo (uma ocupação por mina e
ciclo: ``uq_wild_lands_wild_id_cycle_at``) e o poder de quem ocupou (o ``fightCapaity`` que os outros veem).
``game_settings.world_mines``: a hora do ciclo, as grades vistas, quantas minas por grade e o limite de 2 minas.

(visto) oficial_20261023-153200-1 e oficial_20261023-171155-1: minas 2004xx de nível 11 a 20 no mapa 1, guardas 11 a
20, createDate 01:15:41 e 13:15:52 (ciclo do mundo), minas de outros jogadores (Alt29). (cliente) 2 minas por jogador
(``MapPhysicsField``: "Max number of occupiable resource quarries"). TODO(inventado): guardas 21 a 60 (o 1º 65xx de
nível >= o da mina depois do anterior) e as minas das grades não vistas (sorteio pela contagem das vistas).

Revision ID: 0064
Revises: 0063
Create Date: 2026-10-24 03:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

from wartune_server.persistence.schema import UTCDateTime

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

KEY = "world_mines"
# (visto) id e tile das minas do mapa 1 (4129 das duas capturas; tools/extract_world.py)
MINES = [
    (804793, 2396, 2637), (804794, 2373, 2644), (804795, 2392, 2550), (804799, 2353, 2595), (804801, 2374, 2723),
    (804807, 2378, 2675), (804826, 2391, 2781), (806735, 2487, 2611), (806736, 2487, 2632), (806760, 2452, 2569),
    (806930, 2472, 2769), (806931, 2481, 2780), (806961, 2480, 2701), (806963, 2482, 2727), (806964, 2474, 2738),
    (806984, 2456, 2651), (807289, 2633, 2639), (807290, 2649, 2639), (807304, 2600, 2581), (811264, 2526, 2621),
    (811265, 2511, 2625), (811266, 2546, 2627), (811269, 2544, 2570), (811277, 2549, 2663), (811279, 2517, 2682),
    (811280, 2547, 2697), (812925, 2237, 4908), (812940, 2219, 4885), (816477, 2590, 2563), (816636, 2580, 2662),
    (816640, 2562, 2609), (816641, 2581, 2619), (816642, 2557, 2623), (816643, 2574, 2642), (816644, 2560, 2648),
    (816653, 2586, 2723), (820701, 2319, 2670), (820704, 2333, 2696), (820765, 2347, 2767), (820768, 2302, 2791),
    (828560, 2405, 2593), (828572, 2439, 2673), (828576, 2422, 2611), (828577, 2443, 2630), (828578, 2425, 2633),
    (828588, 2427, 2721), (828589, 2419, 2731), (835130, 2106, 4900), (835136, 2104, 4963), (835352, 2149, 4829),
    (835360, 2146, 4887), (840701, 2280, 2638), (840702, 2268, 2643), (840718, 2291, 2665), (840725, 2297, 2727),
    (843607, 2165, 4905), (843611, 2150, 4935), (843657, 2169, 4981), (849924, 2062, 4872), (849931, 2070, 4937),
]  # fmt: skip
# (visto) guarda de cada nível nas duas capturas
GUARDS_SEEN = [(11, 6506), (12, 6509), (13, 6511), (14, 6513), (15, 6514), (16, 6516), (17, 6517), (18, 6520),
               (19, 6521), (20, 6522)]  # fmt: skip
# TODO(inventado): o 1º PawnTempInfos 65xx de nível >= o da mina com id maior que o do nível anterior
GUARDS_INVENTED = [
    (21, 6523), (22, 6524), (23, 6525), (24, 6527), (25, 6528), (26, 6534), (27, 6536), (28, 6537), (29, 6540),
    (30, 6541), (31, 6543), (32, 6544), (33, 6546), (34, 6547), (35, 6549), (36, 6550), (37, 6555), (38, 6556),
    (39, 6563), (40, 6564), (41, 6565), (42, 6566), (43, 6567), (44, 6568), (45, 6569), (46, 6570), (47, 6571),
    (48, 6572), (49, 6573), (50, 6574), (51, 6581), (52, 6582), (53, 6583), (54, 6584), (55, 6585), (56, 6586),
    (57, 6590), (58, 6591), (59, 6594), (60, 6595),
]  # fmt: skip
# (visto) as grades do mapa 1 que o cliente pediu nas capturas: nelas só existem as minas vistas (7 sem nenhuma)
SEEN_GRIDS = [
    "41_96", "41_97", "41_98", "42_96", "42_97", "42_98", "42_99", "43_96", "43_97", "43_98", "43_99", "44_97",
    "44_98", "45_52", "45_53", "45_54", "46_52", "46_53", "46_54", "46_55", "47_51", "47_52", "47_53", "47_54",
    "47_55", "48_51", "48_52", "48_53", "48_54", "48_55", "49_51", "49_52", "49_53", "49_54", "49_55", "50_51",
    "50_52", "50_53", "50_54", "51_51", "51_52", "51_53", "51_54", "52_51", "52_52",
]  # fmt: skip
SOURCE = (
    "(visto) oficial_20261023-153200-1/171155-1: anchor (createDate 01:15:41 e 13:15:52 no fuso do jogo), seen_grids; "
    "(cliente) max_held 2 (MapPhysicsField fieldDic >= 2); (dedução) per_grid = quantas minas as 45 grades vistas "
    "têm; TODO(inventado): as minas das grades não vistas saem desse sorteio"
)
VALUE = {
    "anchor": "01:15:41",
    "maps": [1, 2, 3, 4, 5],
    "seen_grids": {"1": SEEN_GRIDS},
    "per_grid": {"0": 7, "1": 23, "2": 10, "3": 4, "5": 1},
    "max_held": 2,
}


def upgrade() -> None:
    with op.batch_alter_table("wild_lands") as batch:
        batch.add_column(sa.Column("map_id", sa.Integer(), server_default="100", nullable=False))
        batch.add_column(sa.Column("cycle_at", UTCDateTime(), nullable=True))
        batch.add_column(sa.Column("capacity", sa.Integer(), server_default="0", nullable=False))
        batch.create_unique_constraint("uq_wild_lands_wild_id_cycle_at", ["wild_id", "cycle_at"])
    mines = sa.table(
        "world_mines",
        sa.column("id"), sa.column("position"), sa.column("map_id"), sa.column("pos_x"), sa.column("pos_y"),
        sa.column("min_level"), sa.column("max_level"),
    )  # fmt: skip
    op.bulk_insert(mines, [
        {"id": i, "position": 100 + n, "map_id": 1, "pos_x": x, "pos_y": y, "min_level": 11, "max_level": 20}
        for n, (i, x, y) in enumerate(MINES)
    ])  # fmt: skip
    guards = sa.table("world_mine_guards", sa.column("level"), sa.column("pawn_id"))
    op.bulk_insert(guards, [{"level": lv, "pawn_id": p} for lv, p in GUARDS_SEEN + GUARDS_INVENTED])
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    guards = sa.table("world_mine_guards", sa.column("level"))
    op.execute(guards.delete().where(guards.c.level > 10))
    mines = sa.table("world_mines", sa.column("map_id"))
    op.execute(mines.delete().where(mines.c.map_id == 1))
    with op.batch_alter_table("wild_lands") as batch:
        batch.drop_constraint("uq_wild_lands_wild_id_cycle_at", type_="unique")
        batch.drop_column("capacity")
        batch.drop_column("cycle_at")
        batch.drop_column("map_id")
