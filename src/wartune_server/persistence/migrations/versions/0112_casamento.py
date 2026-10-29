"""salões do casamento 4301-4303: TODO(inventado) gerados por ``tools/gera_masmorras.py casamento``

``0112_casamento.json`` (ao lado): casas andáveis do ``.titles`` (cliente); entrada, padre (``param1`` 3) e criado
(``param1`` 8) inventados.

``wedding_room`` (``handlers/wedding.py``): TODO(inventado) pontos do casal por ação do criado (bolo, champanhe,
flores, doces), o preço dos fogos em diamantes quando falta o ConfigInfo ``marriage_fireworks`` e as falas do voto.

Revision ID: 0112
Revises: 0111
Create Date: 2026-10-29 23:30:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0112"
down_revision = "0111"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0112_casamento.json")
SOURCE = "TODO(inventado) tools/gera_masmorras.py casamento: casas do cliente, entrada e NPCs inventados"
contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
ROOM = {
    "action_happy": 10,
    "fireworks": 2000,
    "oath": [
        "We are gathered here today to witness the union of {a} and {b}.",
        "{a}, do you take {b} to be your beloved?",
        "I do.",
        "{b}, do you take {a} to be your beloved?",
        "I do.",
        "I now pronounce you married!",
    ],
}


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
    op.bulk_insert(
        contents,
        [{"campaign_id": int(k), "data": json.dumps(v, ensure_ascii=False), "source": SOURCE} for k, v in seed.items()],
    )
    op.bulk_insert(settings, [{"key": "wedding_room", "value": json.dumps(ROOM), "source": "TODO(inventado)"}])


def downgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed])))
    op.execute(settings.delete().where(settings.c.key == "wedding_room"))
