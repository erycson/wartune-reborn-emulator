"""reforços (72) das lutas das campanhas 1002 e 1003

Quando o lado inimigo cai e a luta tem outra onda, o oficial manda o 72 ``ReinforceMsg`` com os soldados novos e a luta
segue (``battle.Battle._reinforce``). As ondas são as dos nós escondidos do grupo (``param4``, sonType 6004 em state 9).
``tools/extract_dungeon.py`` agora guarda os 72 em ``battles[nó].reinforce``; esta migração junta as ondas às lutas
já gravadas (``0077_reforcos.json``, ao lado): 1002 da ``tutorial_en`` (113203 e 114203, #2611/#3034) e 1003 da
``oficial_20261023-153200-1`` (103105). As 1005 e 1006 já vêm com elas na 0075.

(visto) a ``oficial_encantar`` teve as ondas do 114203 na ordem inversa (4 soldados, depois 2): aqui fica a ordem da
``tutorial_en``. A ordem não é fixa (171155 e 153200 também trocam no 103105): a luta sorteia
(``battle._shuffled_waves``).

Revision ID: 0077
Revises: 0076
Create Date: 2026-10-24 20:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0077_reforcos.json")


def _apply(add: bool) -> None:
    bind = op.get_bind()
    for campaign, waves in json.loads(SEED.read_text(encoding="utf-8")).items():
        row = bind.execute(
            sa.text("SELECT data FROM campaign_contents WHERE campaign_id = :c"), {"c": int(campaign)}
        ).first()
        if row is None:
            continue
        data = json.loads(row[0])
        for camp, wave in waves.items():
            battle = data.get("battles", {}).get(camp)
            if battle is None:
                continue
            if add:
                battle["reinforce"] = wave
            else:
                battle.pop("reinforce", None)
        bind.execute(
            sa.text("UPDATE campaign_contents SET data = :d WHERE campaign_id = :c"),
            {"d": json.dumps(data, ensure_ascii=False), "c": int(campaign)},
        )


def upgrade() -> None:
    _apply(True)


def downgrade() -> None:
    _apply(False)
