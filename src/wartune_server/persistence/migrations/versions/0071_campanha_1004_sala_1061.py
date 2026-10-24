"""campanha 1004, segunda etapa: sala 1061 (Temple of Ibalize (Inner))

O ``MapInfos`` tem dois mapas da 1004 (1051 e 1061) e as etapas giram a cada vitória (``STAGE_KEY``): (visto)
oficial_20261023-171155-1 #5250 entrou na 1051 e oficial_20261023-215937-1 #219, a segunda vez, na 1061. Conteúdo
extraído por ``tools/extract_dungeon.py`` (``0071_campanha_1004_sala_1061.json``, ao lado; #218-#727): nós, névoa,
5 lutas (o chefe no 106109), o baú de prata 106110 (1000 de ouro, Lvl. 1 Luck Stone), a Pandora 106111, a caixa
106112 (Skeleton Key, 5000 de ouro) e as 5 cartas (deu Lvl. 1 Luck Stone, #725), do mesmo baralho da 0069.

Revision ID: 0071
Revises: 0070
Create Date: 2026-10-24 13:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None

CAMPAIGN, MAP = 1004, "1061"
SEED = Path(__file__).with_name("0071_campanha_1004_sala_1061.json")


def _load() -> tuple[sa.engine.Connection, dict[str, Any] | None]:
    bind = op.get_bind()
    row = bind.execute(sa.text("SELECT data FROM campaign_contents WHERE campaign_id = :c"), {"c": CAMPAIGN}).first()
    return bind, (json.loads(row[0]) if row else None)


def _save(bind: sa.engine.Connection, data: dict[str, Any]) -> None:
    bind.execute(
        sa.text("UPDATE campaign_contents SET data = :d WHERE campaign_id = :c"),
        {"d": json.dumps(data, ensure_ascii=False), "c": CAMPAIGN},
    )


def upgrade() -> None:
    bind, data = _load()
    if data is None:
        return
    new = json.loads(SEED.read_text(encoding="utf-8"))[str(CAMPAIGN)]
    for key, value in new.items():
        if key == "stages":
            data["stages"] = [*data["stages"], *value]
        elif isinstance(value, dict):
            data.setdefault(key, {}).update(value)
    _save(bind, data)


def downgrade() -> None:
    bind, data = _load()
    if data is None:
        return
    new = json.loads(SEED.read_text(encoding="utf-8"))[str(CAMPAIGN)]
    data["stages"] = [s for s in data["stages"] if s != [int(MAP)]]
    for key, value in new.items():
        if key != "stages" and isinstance(value, dict):
            for k in value:
                data[key].pop(k, None)
    _save(bind, data)
