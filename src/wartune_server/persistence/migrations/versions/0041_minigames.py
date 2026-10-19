"""minigames: fundo normal ("Diamond Vein") e árvore dourada ("Sacred Gold Tree") no banco

``game_settings.gold_tree``: o 295 do #72 (70 itens, 5 baús de vezes, 5 de andar e o fim da edição). Início da
edição e pesos do sorteio não foram capturados (dedução, configuráveis).

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
# 295 #72: (item, quantidade, isShow, isNewItems, peso). O peso não está em lugar nenhum: 1 = uniforme (dedução).
# O BottleItems do tempinfos (58 linhas, outra geração de equipamento) não é lido pelo cliente: vale a lista do 295.
DROPS = [
    (2125059, 100, 0, 0, 1), (3120003, 1, 0, 0, 1), (3120604, 1, 0, 0, 1), (3120504, 1, 0, 0, 1),
    (2125057, 10, 0, 0, 1), (208017, 10, 0, 0, 1), (208023, 10, 0, 0, 1), (2100035, 10, 0, 0, 1),
    (3120102, 1, 0, 0, 1), (3120202, 1, 0, 0, 1), (2125059, 10, 0, 0, 1), (2031303, 1, 0, 0, 1),
    (2030502, 3, 0, 0, 1), (2190004, 1, 0, 0, 1), (208014, 50, 0, 0, 1), (3020001, 1, 0, 0, 1),
    (3020002, 1, 0, 0, 1), (3020003, 1, 0, 0, 1), (3020009, 1, 0, 0, 1), (3020004, 1, 0, 0, 1),
    (3020006, 1, 0, 0, 1), (3020008, 1, 0, 0, 1), (3020005, 1, 0, 0, 1), (3020007, 1, 0, 0, 1),
    (2060066, 1, 0, 0, 1), (208021, 1, 0, 0, 1), (2125059, 5, 0, 0, 1), (2030501, 5, 0, 0, 1),
    (208005, 3, 0, 0, 1), (2014501, 2, 0, 0, 1), (2014701, 2, 0, 0, 1), (3061001, 1, 0, 0, 1),
    (3063001, 1, 0, 0, 1), (208017, 5, 0, 0, 1), (208023, 5, 0, 0, 1), (208024, 3, 0, 0, 1),
    (2040109, 1, 0, 0, 1), (2060064, 1, 0, 0, 1), (2060065, 1, 0, 0, 1), (2013002, 1, 0, 0, 1),
    (2160052, 2, 0, 0, 1), (2160048, 2, 0, 0, 1), (208028, 10, 0, 0, 1), (2130005, 1, 0, 0, 1),
    (2050603, 2, 0, 0, 1), (3040001, 3, 0, 0, 1), (2050602, 1, 0, 0, 1), (2031001, 3, 0, 0, 1),
    (208012, 3, 0, 0, 1), (208017, 3, 0, 0, 1), (1108274, 1, 0, 1, 1), (208008, 1, 0, 0, 1),
    (2030102, 10, 0, 0, 1), (208023, 3, 0, 0, 1), (2127002, 1, 0, 0, 1), (2030102, 5, 0, 0, 1),
    (208024, 3, 0, 0, 1), (208045, 3, 0, 0, 1), (3040002, 3, 0, 0, 1), (2125123, 10, 0, 0, 1),
    (2125124, 10, 0, 0, 1), (1118274, 1, 0, 1, 1), (2125125, 5, 0, 0, 1), (3120006, 1, 0, 0, 1),
    (3240103, 10, 1, 1, 1), (3065005, 1, 1, 1, 1), (2183370, 1, 1, 1, 1), (1098274, 1, 1, 1, 1),
    (1128274, 1, 1, 1, 1), (3290105, 1, 1, 1, 1),
]  # fmt: skip
GOLD_TREE = {
    "id": "2026-10-15",  # edição: muda = vezes, baús e andares começam do zero
    "startDate": "2026-10-15 00:00:00",  # (dedução) o 295 só traz o fim; mesmo início da compra do fundo (#86)
    "endDate": "2026-10-18 23:59:59",  # #72 endTime 1792393199000 = 23:59:59 do dia 18 no horário do Pacífico
    "minGrades": 11,  # TopToolsBar.showBottleBtn (cliente)
    "drops": DROPS,
    # [param, item, quantidade] na ordem do #72 (o cliente ordena): 208022 = Golden Wand
    "score": [[50, 208022, 7], [20, 208022, 3], [500, 208022, 70], [150, 208022, 20], [1000, 208022, 100]],
    "storey": [[2000, 2125125, 5], [500, 2125123, 10], [200, -500, 1000], [1000, 2125124, 10], [3500, 2183370, 1]],
}
SETTINGS = [
    (
        "normal_fund",
        NORMAL_FUND,
        f"{CAPTURE} #86 (4612): níveis, custos e tiers; datas da edição capturada (do operador); title/description "
        "traduzidos do chinês (o cliente não mostra)",
    ),
    (
        "gold_tree",
        GOLD_TREE,
        f"{CAPTURE} #72 (295): itens, baús de vezes e de andar, fim; início e pesos (1 = uniforme) são dedução; "
        "datas do operador",
    ),
]


SETTINGS_TABLE = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def upgrade() -> None:
    op.bulk_insert(SETTINGS_TABLE, [{"key": k, "value": json.dumps(v), "source": src} for k, v, src in SETTINGS])


def downgrade() -> None:
    # pelo SQLAlchemy: ``key`` é palavra reservada no MySQL
    op.execute(SETTINGS_TABLE.delete().where(SETTINGS_TABLE.c.key.in_([k for k, _v, _s in SETTINGS])))
