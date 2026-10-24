"""EXP base das lutas da 9001: 6, não 132

(só turco: peri_uyanis #97, #100) o 4103 levou ``gpBonus`` 132 = 6 + 60 de EXP do mundo + 66 descansada ("132 EXP
kazanıldı(Dahil60 Dünya EXP,66 çevrimdışı EXP)"); o extrator guardou o total, e o servidor soma os bônus de novo
(``rules.exp_bonus``). A base é 6.

Revision ID: 0086
Revises: 0085
Create Date: 2026-10-24 13:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None

CAMPAIGN = 9001
contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"))


def _set(gp: int) -> None:
    row = op.get_bind().execute(sa.select(contents.c.data).where(contents.c.campaign_id == CAMPAIGN)).first()
    if row is None:
        return
    data = json.loads(row[0])
    for battle in data["battles"].values():
        battle["gpBonus"] = gp
    value = json.dumps(data, ensure_ascii=False)
    op.execute(contents.update().where(contents.c.campaign_id == CAMPAIGN).values(data=value))


def upgrade() -> None:
    _set(6)


def downgrade() -> None:
    _set(132)
