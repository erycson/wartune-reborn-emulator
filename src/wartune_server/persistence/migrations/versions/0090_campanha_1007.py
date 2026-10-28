"""campanha 1007 (Camp Calorn): a 1ª etapa (1171 e 1172) e a patrulha

Da captura ``oficial_20261024-191924-1`` (#2345-#3706) por ``tools/extract_dungeon.py`` (``0090_campanha_1007.json``,
ao lado): nós, névoa, exército do sistema, diálogos, lutas, a Pandora (Rage Boost, #2574), a tumba (5,000 Daru,
#2594), a bolsa de moedas (1,000 Gold, #2958) e o portal 117105 -> 1172 (#2615).

- (visto) o chefe Viscount Remus (117204) fala e luta pelo 5032 (#2992-#3003); o jogador perdeu as 4 lutas
  (#3132, #3343, #3538, #3692: ``battleResult`` 2, ``failCount`` 1-4) e saiu (5025). O fim da etapa (134/135)
  não foi visto: segue o das outras campanhas.
- (dedução) Mystery Box 117206 (sonType 2203, chave 208005): deu Lvl. 2 Luck Stone x2 (#2789), igual à 103108 da
  1003 (0062): o mesmo sorteio entre 5.000 Gold e Lvl. 2 Luck Stone x2.
- (visto) patrulha (4122): 117103, 117104, 117202, 117203; o chefe só volta ao lugar (31,24).
- A 2ª etapa (1181 e 1182 no ``MapInfos``) não foi jogada: sem conteúdo, a campanha só abre a 1ª.
  As cartas do fim já vêm da 0085.

Revision ID: 0090
Revises: 0089
Create Date: 2026-10-24 23:30:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0090"
down_revision = "0089"
branch_labels = None
depends_on = None

CAMPAIGN = 1007
SEED = Path(__file__).with_name("0090_campanha_1007.json")
SOURCE = "(visto) oficial_20261024-191924-1 #2345-#3706, tools/extract_dungeon.py; Mystery Box por dedução (0062)"
PATROL = {
    "117103": [[51, 50], [52, 55], [51, 59]],
    "117104": [[50, 39], [54, 36], [45, 35]],
    "117202": [[46, 63], [40, 62]],
    "117203": [[74, 24], [79, 31], [70, 29]],
}
settings = sa.table("game_settings", sa.column("key"), sa.column("value"))


def _patrol(change: dict[str, object]) -> None:
    row = op.get_bind().execute(sa.select(settings.c.value).where(settings.c.key == "npc_patrol")).first()
    if row is None:
        return
    value = json.loads(row[0])
    points = value["points"]
    for k, v in change.items():
        if v is None:
            points.pop(k, None)
        else:
            points[k] = v
    op.execute(settings.update().where(settings.c.key == "npc_patrol").values(value=json.dumps(value)))


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(
        contents,
        [{"campaign_id": CAMPAIGN, "data": json.dumps(seed[str(CAMPAIGN)], ensure_ascii=False), "source": SOURCE}],
    )
    _patrol(dict(PATROL))


def downgrade() -> None:
    contents = sa.table("campaign_contents", sa.column("campaign_id"))
    op.execute(contents.delete().where(contents.c.campaign_id == CAMPAIGN))
    _patrol(dict.fromkeys(PATROL))
