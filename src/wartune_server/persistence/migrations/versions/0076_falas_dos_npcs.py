"""falas dos NPCs nos mapas de campanha (4163) e a contribuição do Invasor vista

``game_settings.npc_chat``: o repertório do ``U_C_NPC_CHAT`` por ``sonType`` do nó, tirado das capturas inglesas
(``0076_falas_dos_npcs.json``, ao lado; ``idle`` = falas soltas, ``chase`` = a fala logo depois do 4105). Nem o cliente
nem os templates têm esses textos: só o servidor manda.

(visto) nas capturas (tutorial_en, oficial_20261023-*): cada nó fala de novo a cada 12-18 s (mediana 16 s; 123
intervalos) ou num múltiplo disso, então a cada tique ``chance`` ~0,7 de falar (dedução: 88 intervalos de 1 tique, 26
de 2, 10 de 3); a fala do chase só na 1ª perseguição do nó, em 7 de 35 (``chase_chance`` 0,2). NPC sem repertório
visto fica calado.

``game_settings.fam_invader_offer``: a fonte deixa de ser inventada; oficial_20261023-231733-1 #4104 "has defeated an
invader and earned 10 guild contribution!".

Revision ID: 0076
Revises: 0075
Create Date: 2026-10-24 19:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0076_falas_dos_npcs.json")
KEY = "npc_chat"
SOURCE = "(visto) 4163 das capturas inglesas por sonType; tique 12-18 s; chance 0,7 e chase_chance 0,2 (dedução)"
OFFER_SOURCE = "(visto) oficial_20261023-231733-1 #4104-#4105: 10 de contribuição e +10 de riqueza por Invasor"
OLD_OFFER_SOURCE = "TODO(inventado): a ajuda do cliente só diz 'additional guild contribution points'"


def upgrade() -> None:
    value = {"tick": [12, 18], "chance": 0.7, "chase_chance": 0.2, "lines": json.loads(SEED.read_text("utf-8"))}
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(value, ensure_ascii=False), "source": SOURCE}])
    op.execute(settings.update().where(settings.c.key == "fam_invader_offer").values(source=OFFER_SOURCE))


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("source"))
    op.execute(settings.delete().where(settings.c.key == KEY))
    op.execute(settings.update().where(settings.c.key == "fam_invader_offer").values(source=OLD_OFFER_SOURCE))
