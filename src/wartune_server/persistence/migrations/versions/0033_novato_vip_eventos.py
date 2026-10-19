"""novato, VIP e eventos: regras do oficial inglês que não estão no cliente

``game_settings`` guarda cada regra como JSON (nível do chat World, custo dos giros da roleta VIP, fundo novato);
``vip_wheel_prizes`` os 18 prêmios da roleta; ``exp_rate_events`` o evento de EXP (4247) com as datas. Fonte de
cada valor na coluna ``source`` (``#N`` = linha de ``tools/dump_capture.py captures/tutorial_en.json``).

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-18 22:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

CAPTURE = "(visto) captura do oficial inglês tutorial_en"
GIFT, DIAMOND = -500, -400


def _tiers(gift: tuple[int, ...], diamond: tuple[int, int]) -> list[list[object]]:
    """Tiers do 4640: [nível mínimo ("interval"), vez, itens]; os dois primeiros trazem diamante."""
    return [
        [10 * n, n, [[GIFT, g], [DIAMOND, diamond[n - 1]]] if n <= 2 else [[GIFT, g]]] for n, g in enumerate(gift, 1)
    ]


NOVICE_FUND = {
    "activeId": "-1234567890",
    "minGrades": 11,  # FundBuyItem: compra a partir do nível 11 (cliente)
    "openGrades": 6,  # #639: o primeiro 4640 sai ao chegar no nível 6; o login no nível 1 não manda
    "endDate": "2099-12-31 23:59:59",
    "levels": [
        {"level": 1, "costDiamond": 500, "tiers": _tiers((25, 25, 25, 50, 125), (250, 250))},
        {"level": 2, "costDiamond": 5000, "tiers": _tiers((450, 450, 700, 700, 1500), (2500, 2500))},
        {"level": 3, "costDiamond": 30000, "tiers": _tiers((3000, 3000, 4500, 4500, 15000), (15000, 15000))},
    ],
}
SETTINGS = [
    ("world_chat_min_grade", 20, f"{CAPTURE} #2779-#2782: 111 'Requires character Level of 20' no nível 14"),
    (
        "vip_wheel_costs",
        [1, 2, 3, 4, 5, 6, 7, 8],
        f"{CAPTURE} #3325/#3335: needVipItem 1 -> 3 e VIP Token 5 -> 2 em dois giros (o giro k custa k); "
        "(dedução) a sequência depois do 2º giro; 8 giros = VipBoxFrame (cliente)",
    ),
    ("novice_fund", NOVICE_FUND, f"{CAPTURE} #639, #2784 (4640): custos 500/5000/30000 e tiers"),
]
# 4414 #3325, na ordem do oficial (o openIndex do 4415 é a posição 0..17 nesta lista)
WHEEL = [
    (2050506, 1), (2050507, 1), (2160018, 1), (208005, 5), (-100, 500000), (-100, 20000), (2090102, 1),
    (-300, 20000), (2050306, 1), (2160040, 1), (-100, 60000), (2050502, 1), (208017, 5), (2160048, 1),
    (2160050, 1), (2040106, 1), (2160046, 1), (2160036, 1),
]  # fmt: skip


def upgrade() -> None:
    settings = op.create_table(
        "game_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=1000), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_game_settings")),
    )
    op.bulk_insert(settings, [{"key": k, "value": json.dumps(v), "source": src} for k, v, src in SETTINGS])
    wheel = op.create_table(
        "vip_wheel_prizes",
        sa.Column("position", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("template_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("position", name=op.f("pk_vip_wheel_prizes")),
    )
    src = f"{CAPTURE} #3325 (4414 leftItem); sem probabilidades: sorteio uniforme (dedução)"
    op.bulk_insert(
        wheel, [{"position": i, "template_id": t, "quantity": n, "source": src} for i, (t, n) in enumerate(WHEEL)]
    )
    rates = op.create_table(
        "exp_rate_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rate", sa.Integer(), server_default="0", nullable=False),
        sa.Column("begin_day", sa.String(length=19), nullable=False),  # hora do jogo (fuso do servidor)
        sa.Column("end_day", sa.String(length=19), nullable=False),
        sa.Column("begin_time", sa.Integer(), server_default="0", nullable=False),
        sa.Column("end_time", sa.Integer(), server_default="0", nullable=False),
        sa.Column("buffer_type", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exp_rate_events")),
    )
    op.bulk_insert(
        rates,
        [
            {
                "rate": 100,
                "begin_day": "2026-10-08 00:00:00",
                "end_day": "2026-10-21 00:00:00",
                "begin_time": 0,
                "end_time": 86399,
                "buffer_type": 0,
                "source": f"{CAPTURE} #45 (4247)",
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("exp_rate_events")
    op.drop_table("vip_wheel_prizes")
    op.drop_table("game_settings")
