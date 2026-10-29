"""taxas que o cliente não traz, fora do código

``game_settings.taxas``: a lógica de cada sistema é do cliente inglês, mas chances, pesos e quantidades não estão
nele (procurado no decomp inglês, nos XMLs do mirror res134, nos templates e no language
``ui/zh_cn/language.txt`` do mirror: mounts.tips02, petFrame.help02, PetAdvancedView.normalTip,
PetStrengthenView.NormalTrainTip e faterotary.* só dizem "chance", sem número). ``source`` de cada valor: ``cliente``
ou ``TODO(inventado)``; trocar com dump do oficial.

Revision ID: 0124
Revises: 0123
Create Date: 2026-10-29 12:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0124"
down_revision = "0123"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"
KEY = "taxas"

TAXAS: dict[str, Any] = {
    "mount_star_bless": 10,
    "mount_star_chance": 5,
    "fate_stone_exp": 1,
    "fate_wheel": {"1": 144, "2": 90, "3": 63, "4": 45, "10": 18},
    "pet_advance_bless_chance": 10,
    "pet_enchant_gain": [1, 10],
    "pet_skill_weights": {},
    "pet_mould_bless_reset": True,
    "offer_quality_weights": [40, 30, 15, 10, 5],
    "star_free_point": True,
    "source": {
        "mount_star_bless/chance": INV + " (MountsPromotionView.getPromotSuccessRate mostra 5 com a barra incompleta)",
        "fate_stone_exp": INV + " (EXP por Fate Stone no 8626)",
        "fate_wheel": "cliente FateRotaryModel.rndDic (graus das fatias usados como peso; dedução)",
        "pet_advance_bless_chance": INV + " (a bênção 5x do PetAdvancedView sem chance no cliente)",
        "pet_enchant_gain": INV + " (Sepulcrum: 'Randomly improves one aptitude', sem faixa)",
        "pet_skill_weights": INV + " (skillId -> peso do aprender aleatório; ausente = 1)",
        "pet_mould_bless_reset": INV + " (8644: bênção zera no sucesso)",
        "offer_quality_weights": INV + " (qualidade 1..5 do bounty)",
        "star_free_point": INV + " (o grátis do dia dá ponto de estrela)",
    },
}
SOURCE = "taxas sem fonte no cliente (decomp, mirror, templates e language.txt procurados): " + INV


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(TAXAS), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
