"""fórmula de dano da batalha no banco

``game_settings.battle_formula``: os coeficientes de ``game/battle.py`` (``FORMULA``). Defesa e piso conferidos
nos 153 da captura do oficial inglês; as chances de crítico e bloqueio vêm da internet; o multiplicador do
crítico e do bloqueio são dedução da captura (poucos golpes). Como editar: ``docs/configuracao.md``.

Revision ID: 0039
Revises: 0038
Create Date: 2026-10-19 13:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

KEY = "battle_formula"
VALUE = {
    "defence_factor": 0.5,
    "floor": 0.1,
    "spread": 0.08,
    "crit_base": 0.9995,
    "crit_damage": 1.5,
    "block_base": 0.9995,
    "block_damage": 0.75,
}
SOURCE = (
    "(visto) tutorial_en 153 x 150: golpe = max((A - D) x defence_factor, A x floor) x Parameter1/100 + Parameter2, "
    "±spread; (dedução) crit_damage ~1,5 e block_damage ~0,75 de poucos golpes (extraData 1, parry); "
    "(internet) https://breezewiki.discard.no/wartune/wiki/Statistics chance = 1 - base^ForceHit/Parry"
)


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(VALUE), "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
