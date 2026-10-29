"""campanha 1007 (Camp Calorn): a 2ª etapa (1181 -> 1182) gerada

``tools/gera_masmorras.py 1007`` (``0131_campanha_1007_etapa2.json``, ao lado): a 1ª etapa é a capturada (0090) e a 2ª
segue a planta da 1201 (1291 com portal, 1292 com o chefe), com mapas e casas do cliente (``MapInfos`` 1181/1182,
``.titles`` do mirror). TODO(inventado): nós, monstros e prêmios da 2ª etapa (marcados em ``inventado``). O fim de
cada etapa (137, 135, 5122, 5180) é o mesmo das outras masmorras.

Revision ID: 0131
Revises: 0130
Create Date: 2026-10-30 00:30:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0131"
down_revision = "0130"
branch_labels = None
depends_on = None

CAMPAIGN = 1007
SEED = Path(__file__).with_name("0131_campanha_1007_etapa2.json")
OLD = Path(__file__).with_name("0090_campanha_1007.json")
SOURCE = "(visto) 1ª etapa oficial_20261024-191924-1 (0090); TODO(inventado) 2ª etapa por tools/gera_masmorras.py 1007"
OLD_SOURCE = "(visto) oficial_20261024-191924-1 #2345-#3706, tools/extract_dungeon.py; Mystery Box por dedução (0062)"
contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))


def _put(path: Path, source: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))[str(CAMPAIGN)]
    op.execute(
        contents.update()
        .where(contents.c.campaign_id == CAMPAIGN)
        .values(data=json.dumps(data, ensure_ascii=False), source=source)
    )


def upgrade() -> None:
    _put(SEED, SOURCE)


def downgrade() -> None:
    _put(OLD, OLD_SOURCE)
