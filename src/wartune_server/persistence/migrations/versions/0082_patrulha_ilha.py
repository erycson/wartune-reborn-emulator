"""patrulha dos pets selvagens da ilha dos pets (20001)

``game_settings.npc_patrol.points`` ganha os nós da ilha (``0082_patrulha_ilha.json``, ao lado): (só turco:
peri_adasi_tp #9-#43) os 4122 da entrada, com a origem e a posição do 127 de cada nó. Só andam os masterType 91
(alguns dos 91 não andaram na captura e ficam parados). O tique e a chance são os dos mapas de campanha (dedução).

Revision ID: 0082
Revises: 0081
Create Date: 2026-10-24 06:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0082_patrulha_ilha.json")
KEY = "npc_patrol"
SOURCE = (
    "(visto) 4122 das capturas inglesas: pontos por campDataId, tique de 6 s (pedreira 20 s), chance 0,62 (0,3);"
    " (só turco: peri_adasi_tp) os nós da ilha dos pets"
)
settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _change(add: bool) -> None:
    bind = op.get_bind()
    row = bind.execute(sa.select(settings.c.value).where(settings.c.key == KEY)).first()
    if row is None:
        return
    value = json.loads(row[0])
    island = json.loads(SEED.read_text("utf-8"))
    points = value.setdefault("points", {})
    for key in island:
        points.pop(key, None)
    if add:
        points |= island
    source = SOURCE if add else SOURCE.split(";")[0]
    op.execute(settings.update().where(settings.c.key == KEY).values(value=json.dumps(value), source=source))


def upgrade() -> None:
    _change(True)


def downgrade() -> None:
    _change(False)
