"""masmorras em grupo sem captura: TODO(inventado) geradas por ``tools/gera_masmorras.py grupo``

``0101_masmorras_grupo_geradas.json`` (ao lado): as 20 campanhas 9003-9013 e 9104-9112 (pesadelo), uma etapa com
os mapas do ``MapInfos`` e as casas andáveis do ``.titles``. Planta da 9002 capturada (0100): 2031 nos mapas do
meio (portal), 2033 no último (chefe, cartas); monstros 4xxx e chefes 3xxx pelo ``MinLevel``. O pesadelo tem o
mesmo ``MinLevel`` da normal: TODO(inventado) sai com os mesmos monstros. A chave ``inventado`` lista os mapas.

Revision ID: 0101
Revises: 0100
Create Date: 2026-10-29 00:10:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0101"
down_revision = "0100"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0101_masmorras_grupo_geradas.json")
SOURCE = "TODO(inventado) tools/gera_masmorras.py grupo: planta da 9002, mapas e casas do cliente"
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
