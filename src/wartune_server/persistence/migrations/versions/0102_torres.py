"""torres 8200-8204 sem captura: TODO(inventado) geradas por ``tools/gera_masmorras.py torres``

``0102_torres.json`` (ao lado): Tower of Kings 8200/8202/8203/8204 (Easy/Normal/Hard/Nightmare) e The Spire 8201,
um mapa cada (``MapInfos``, casas do ``.titles`` do MapFileId 8201). Planta do fim da 9002 capturada (chefe);
monstros 4xxx e chefes 3xxx pelo ``MinLevel`` + 10 por dificuldade; a Spire com ondas de reforço (andares) na luta
do chefe. A chave ``inventado`` lista os mapas.

Revision ID: 0102
Revises: 0101
Create Date: 2026-10-29 12:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0102"
down_revision = "0101"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0102_torres.json")
SOURCE = "TODO(inventado) tools/gera_masmorras.py torres: planta do fim da 9002, mapas e casas do cliente"
contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
    op.bulk_insert(
        contents,
        [{"campaign_id": int(k), "data": json.dumps(v, ensure_ascii=False), "source": SOURCE} for k, v in seed.items()],
    )


def downgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
