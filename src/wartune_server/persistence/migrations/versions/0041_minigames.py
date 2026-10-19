"""minigames: fundo normal ("Diamond Vein") no banco

``game_settings.normal_fund``: o 4612 da captura do oficial inglês (#86, ``tools/dump_capture.py
captures/tutorial_en.json``), com as datas da edição capturada (compra 2026-10-15..18, resgate 2026-10-19..23,
hora do jogo). As datas são do operador: fora delas o fundo fica fechado. ``title``/``description`` vieram em chinês
("钻石矿脉"); o cliente não mostra nenhum dos dois (``FundFrame`` usa o ``language.txt``), então vão em inglês
(tradução nossa).

Revision ID: 0041
Revises: 0035
Create Date: 2026-10-19 18:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0035"
branch_labels = None
depends_on = None

CAPTURE = "(visto) captura do oficial inglês tutorial_en"
DAY = 1440  # minutos: o interval do 4612 é minutos depois do getStartDate (cliente FundRewardItem)


def _tiers(items: list[list[int]]) -> list[list[object]]:
    """Os 5 tiers do #86: um por dia a partir do getStartDate (interval 0, 1440, ..., 5760), sempre os mesmos itens."""
    return [[DAY * n, n + 1, items] for n in range(5)]


NORMAL_FUND = {
    "activeId": "AEECCD60-F30C-8381-38D0-CD64DD26B34F",
    "title": "Diamond Vein",
    "description": "Diamond Vein event",
    "grades": 0,  # #86 manda 0
    "minGrades": 11,  # FundManager.getShowBtn: sem botão abaixo do nível 11 (cliente)
    "setStartDate": "2026-10-15 00:00:00",
    "setEndDate": "2026-10-18 23:59:59",
    "getStartDate": "2026-10-19 00:00:00",
    "getEndDate": "2026-10-23 23:59:59",
    "levels": [
        {"level": 1, "costDiamond": 1000, "tiers": _tiers([[2126025, 5], [2125059, 2], [3120003, 1]])},
        {"level": 2, "costDiamond": 2000, "tiers": _tiers([[2126025, 10], [2125059, 4], [3240101, 8]])},
        {"level": 3, "costDiamond": 10000, "tiers": _tiers([[2126025, 30], [2125059, 24], [3240102, 8]])},
    ],
}
SETTINGS = [
    (
        "normal_fund",
        NORMAL_FUND,
        f"{CAPTURE} #86 (4612): níveis, custos e tiers; datas da edição capturada (do operador); title/description "
        "traduzidos do chinês (o cliente não mostra)",
    ),
]


SETTINGS_TABLE = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def upgrade() -> None:
    op.bulk_insert(SETTINGS_TABLE, [{"key": k, "value": json.dumps(v), "source": src} for k, v, src in SETTINGS])


def downgrade() -> None:
    # pelo SQLAlchemy: ``key`` é palavra reservada no MySQL
    op.execute(SETTINGS_TABLE.delete().where(SETTINGS_TABLE.c.key.in_([k for k, _v, _s in SETTINGS])))
