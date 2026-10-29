"""lote 7: 9113 Elemental Forest montada pelos mapas do cliente e a patrulha dos agressivos sem captura

``0117_floresta_elemental.json``: ``tools/gera_masmorras.py floresta``. A 9113 (em grupo, MapInfos 2281) ficou fora
da faixa 9000-9112 da 0101; os nós vão para as casas andáveis do ``.titles`` do mirror (os ``.maps`` só trazem
decoração). TODO(inventado): a planta (a da 9002), monstros e prêmios.

``npc_patrol.guess_step``: o monstro agressivo (masterType 42, attackTypes 1) sem pontos capturados anda entre a
origem e ``guess_step`` tiles para cada lado. TODO(inventado): 4 tiles (os pontos vistos ficam a 3-7 tiles).

Revision ID: 0117
Revises: 0116
Create Date: 2026-10-29 09:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0117"
down_revision = "0116"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0117_floresta_elemental.json")
SOURCE = "TODO(inventado) tools/gera_masmorras.py floresta: planta da 9002, mapa e casas do cliente"
STEP = 4
contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _patrol(step: int | None) -> None:
    conn = op.get_bind()
    raw = conn.execute(sa.select(settings.c.value).where(settings.c.key == "npc_patrol")).scalar()
    if raw is None:
        return
    value = json.loads(raw)
    if step is None:
        value.pop("guess_step", None)
    else:
        value["guess_step"] = step
    conn.execute(settings.update().where(settings.c.key == "npc_patrol").values(value=json.dumps(value)))


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
    op.bulk_insert(
        contents,
        [{"campaign_id": int(k), "data": json.dumps(v, ensure_ascii=False), "source": SOURCE} for k, v in seed.items()],
    )
    _patrol(STEP)


def downgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
    _patrol(None)
