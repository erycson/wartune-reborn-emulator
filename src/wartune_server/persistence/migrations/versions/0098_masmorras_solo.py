"""masmorras solo 1101-1201 com captura: nós, névoa, lutas, chefes, baús e drops

Extraídas por ``tools/extract_dungeon.py`` (``0098_masmorras_solo.json``, ao lado), como a 1007 (0090):

- (visto) oficial_20261024-191924-1: 1101 (1111), 1102 (1191/1192), 1103 (1211/1212), 1104 (1091).
- (visto) oficial_20261025-232017-1: 1105 (1231/1232), 1106 (1251/1252).
- (visto) oficial_20261026-225632-1: 1107 (1271/1272; entrou duas vezes, a revanche do chefe não conta).
- (visto) oficial_20261027-152321-1: 1201 (1291/1292).

A 2ª etapa da 1102 (1201/1202), da 1106 (1261/1262) e da 1201 (1301/1302) não foi jogada: como a 1007, só abre a
1ª. As outras 1202-1602 não têm nó em template nem em captura: ficam fechadas até uma captura (nada inventado).
Entrada, custo, estrelas, cartas (``Campaigns.Item``) e missões são os genéricos das campanhas.

Revision ID: 0098
Revises: 0097
Create Date: 2026-10-28 21:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0098"
down_revision = "0097"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0098_masmorras_solo.json")
SOURCE = "(visto) oficial_20261024-191924/20261025-232017/20261026-225632/20261027-152321, tools/extract_dungeon.py"


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(
        contents,
        [{"campaign_id": int(k), "data": json.dumps(v, ensure_ascii=False), "source": SOURCE} for k, v in seed.items()],
    )


def downgrade() -> None:
    contents = sa.table("campaign_contents", sa.column("campaign_id"))
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
