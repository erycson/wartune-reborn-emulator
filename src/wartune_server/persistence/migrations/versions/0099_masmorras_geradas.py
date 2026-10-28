"""masmorras solo sem captura: TODO(inventado) geradas por ``tools/gera_masmorras.py``

``0099_masmorras_geradas.json`` (ao lado): as 33 campanhas 1101-1602 que não têm todas as etapas capturadas.
1102, 1106 e 1201 guardam a 1ª etapa da captura (0098) e ganham a 2ª gerada; as outras 30 são todas geradas.
Mapas e casas andáveis do cliente (``MapInfos``, ``.titles``); planta, monstros e prêmios inventados a partir das
capturadas (ver o gerador). A chave ``inventado`` de cada campanha lista os mapas a trocar quando houver captura.

Revision ID: 0099
Revises: 0098
Create Date: 2026-10-28 23:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0099"
down_revision = "0098"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0099_masmorras_geradas.json")
CAPTURED = Path(__file__).with_name("0098_masmorras_solo.json")
SOURCE = "TODO(inventado) tools/gera_masmorras.py: planta das capturadas 1104/1201, mapas e casas do cliente"
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
    captured = json.loads(CAPTURED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
    source = "(visto) capturas, tools/extract_dungeon.py (0098)"
    op.bulk_insert(
        contents,
        [
            {"campaign_id": int(k), "data": json.dumps(captured[k], ensure_ascii=False), "source": source}
            for k in seed
            if k in captured
        ],
    )
