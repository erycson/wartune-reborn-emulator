"""pet island defend

``game_settings.pet_island_defend``: o que o ``ConfigInfos`` não tem da invasão da ilha dos pets (Defend Sylph Atoll).
Horas, tetos de prêmio e fúria continuam no ``ConfigInfos`` (``pet_island_defend_*``), que o cliente também lê.

Desativa os dois anúncios deduzidos da 0035 ("has started." na hora e "has ended" 30 min depois): o oficial manda
outros textos na abertura e no fechamento, que agora saem com o 4686 (``handlers/pet_defend.py``; oficial_encantar
#866-#868, #2337-#2338), e a janela é de 1 h. Os dois de 5 min antes (#3029/#3030, vistos) ficam.

Revision ID: 0057
Revises: 0056
Create Date: 2026-10-23 21:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None

KEY = "pet_island_defend"
CFG = {
    "duration": 3600,  # (visto) #43 e #2337: fecha na hora cheia seguinte
    "floors": [20001],  # o oficial sorteou 20002 e 20004; só o 20001 tem nós (content/petisland.json)
    # (inventado) prêmio por vitória, até ``pet_island_defend_reward_count`` por dia: avançado, sofisticado, chefe
    "rewards": {
        "middle": [[2100038, 2]],
        "high": [[2100038, 5]],
        "boss": [[2100038, 20], [2060489, 1]],
    },
}
SOURCE = (
    "(visto) oficial_encantar #43, #866, #2337 (janela de 1 h, andares 20002/20004); "
    "(inventado) andares e prêmios: sem fonte no cliente, na captura nem na internet"
)


DEDUCED = ("Defend Sylph Atoll event has started.", "Defend Sylph Atoll event has ended")


def _deduced(active: bool) -> None:
    ann = sa.table("scheduled_announcements", sa.column("name"), sa.column("text"), sa.column("active"))
    op.execute(ann.update().where(ann.c.name == "sylph_atoll", ann.c.text.in_(DEDUCED)).values(active=active))


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{"key": KEY, "value": json.dumps(CFG), "source": SOURCE}])
    _deduced(False)


def downgrade() -> None:
    _deduced(True)
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == KEY))
