"""caixa do caçador sorteada

``campaign_contents`` 1002 (Baylon Plains), ``wins["114203"]``: além dos 10.000 Daru (captura inglesa #3057), a caixa
deu Lvl. 3 Luck Stone x1 (oficial_encantar #1436, #1457). Vira ``pick``: uma das listas, sorteada por igual
(``handlers.campaign._dungeon_loot``).

Revision ID: 0052
Revises: 0051
Create Date: 2026-10-23 13:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None

CAMPAIGN, NODE = 1002, "114203"
PICK = [[[-300, 10000]], [[2040103, 1]]]  # Daru; Lvl. 3 Luck Stone


def _patch(pick: list[object] | None) -> None:
    bind = op.get_bind()
    row = bind.execute(sa.text("SELECT data FROM campaign_contents WHERE campaign_id = :c"), {"c": CAMPAIGN}).first()
    if row is None:
        return
    data = json.loads(row[0])
    win = data["wins"][NODE]
    if pick is None:
        win.pop("pick", None)
    else:
        win["pick"] = pick
    bind.execute(
        sa.text("UPDATE campaign_contents SET data = :d WHERE campaign_id = :c"),
        {"d": json.dumps(data, ensure_ascii=False), "c": CAMPAIGN},
    )


def upgrade() -> None:
    _patch(PICK)


def downgrade() -> None:
    _patch(None)
