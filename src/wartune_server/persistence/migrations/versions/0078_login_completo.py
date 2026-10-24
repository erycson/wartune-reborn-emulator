"""avisos de atividade (4251), chaves do cliente (4422) e o teto da honra do dia (4471) do login

``game_settings.active_notices``: os 9 avisos do ``ActivityManager`` (título, textos, nível, datas), iguais em todas as
capturas inglesas (tutorial_en #84, oficial_20261023-* e oficial_encantar), inclusive os já vencidos: o oficial manda a
lista inteira. ``game_settings.switches``: as 67 chaves do ``BaseManager.__switchesUpdateHandler`` (iguais na
tutorial_en e na oficial_20261023-215937-1 #95). Os dois vêm de ``0078_login_completo.json``, ao lado.

``game_settings.closed_switches``: chaves que o oficial abre e aqui ficam fechadas porque o sistema não existe:
3006 (MINERAL_FIGHT, a mina compartilhada de ``handlers/warfield.py``) e 3031 (GOLDROAD, a estrada dourada que o
``handlers/minigames.py`` fecha no 300).

``game_settings.honor_day_max``: (visto) 215937 #105, 4471 ``param2`` 6000 (``thane.honerDayMax``).

Revision ID: 0078
Revises: 0077
Create Date: 2026-10-24 22:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0078_login_completo.json")
SOURCES = {
    "active_notices": "(visto) 4251 de todas as capturas inglesas (tutorial_en #84, oficial_20261023-215937-1 #88)",
    "switches": "(visto) 4422 da tutorial_en e da oficial_20261023-215937-1 #95",
    "closed_switches": "shortcut: mina (3006) e estrada dourada (3031) não existem aqui; abrir quando existirem",
    "honor_day_max": "(visto) oficial_20261023-215937-1 #105: 4471 param2",
}


def upgrade() -> None:
    seed = json.loads(SEED.read_text("utf-8"))
    values = {**seed, "closed_switches": [3006, 3031], "honor_day_max": 6000}
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(
        settings,
        [{"key": k, "value": json.dumps(values[k], ensure_ascii=False), "source": src} for k, src in SOURCES.items()],
    )


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_(list(SOURCES))))
