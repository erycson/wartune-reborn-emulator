"""taxas: bônus do Balens na runa e prazo do reset da senha secundária

Soma em ``game_settings.taxas`` (0124): ``rune_diamond_multiplier`` (pesos do 1x/2x/5x/10x/20x da ``DiamondTipTxt``
ao dar EXP à runa com Balens) e ``vp_reset_days`` (dias até o reset da senha secundária apagar a senha). Nenhum dos
dois está no decomp inglês, no mirror nem no language.txt: ``TODO(inventado)``.

Revision ID: 0134
Revises: 0133
Create Date: 2026-10-29 15:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0134"
down_revision = "0133"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"
NEW: dict[str, Any] = {
    "rune_diamond_multiplier": {"1": 85, "2": 8, "5": 4, "10": 2, "20": 1},
    "vp_reset_days": 3,
}
SOURCES = {
    "rune_diamond_multiplier": INV + " (DiamondTipTxt diz 2x/5x/10x/20x, sem chance)",
    "vp_reset_days": INV + " (prazo do reset da senha secundária)",
}


def _settings() -> Any:
    return sa.table("game_settings", sa.column("key"), sa.column("value"))


def upgrade() -> None:
    settings, conn = _settings(), op.get_bind()
    row = conn.execute(sa.select(settings.c.value).where(settings.c.key == "taxas")).scalar()
    if row is None:
        return
    data = json.loads(row)
    data.update(NEW)
    data.setdefault("source", {}).update(SOURCES)
    conn.execute(settings.update().where(settings.c.key == "taxas").values(value=json.dumps(data)))


def downgrade() -> None:
    settings, conn = _settings(), op.get_bind()
    row = conn.execute(sa.select(settings.c.value).where(settings.c.key == "taxas")).scalar()
    if row is None:
        return
    data = json.loads(row)
    for key in NEW:
        data.pop(key, None)
        data.get("source", {}).pop(key, None)
    conn.execute(settings.update().where(settings.c.key == "taxas").values(value=json.dumps(data)))
