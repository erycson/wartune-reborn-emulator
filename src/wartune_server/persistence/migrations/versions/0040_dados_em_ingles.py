"""dados do mundo pela captura do oficial inglês (o inglês é o padrão; a captura turca só onde a inglesa não tem)

Conferido no 4129 da captura inglesa (``captures/tutorial_en.json`` #532, igual em #718, #767, #821, #1618):

- minas da 0027: mesmos ids, tiles e ordem (853876 em 16,34; 853877 em 36,34; 853874 em 71,54; 853875 em 54,64);
  níveis 10, 10, 10 e 9, guarda 6505 nos dois. O nível 8 e o guarda 6504 são só turco (replay #706): ficam.
- castelos-robô da 0027: 765958 em (44,22) e 765957 em (59,56), ambos grau 8. Iguais.
- nomes dos robôs: o inglês manda "Aillendre" (765958) e "Addyn" (765957), sem símbolos; os turcos
  (♣Chloe♣, ♫Elizabeth♫, ►Abigail◄) saem.
- cartas das masmorras (0034): o peso passa a contar só a inglesa (#1111/#1533: 1080012 na 1001; #2716/#3170:
  2040102 na 1002). O 1080013 e o 1080002 só saíram na turca, mas estão no ``CampaignInfo.Item`` da 1001: peso 1
  como os outros nunca vistos (o valor não muda, só a fonte).

Só turco (a inglesa não tem): os chefes do mapa 2 (0027 ``BOSSES``, transfer) e o poder do 210127 (0028); o
Lvl. 1 Luck Stone com chance 0,5 no 102102 da 1001 (0034_campanhas.json, ``EXTRA_DROPS`` de tools/extract_dungeon.py,
replay #1355/#1374).

Revision ID: 0040
Revises: 0039
Create Date: 2026-10-19 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

NAMES_EN = ["Aillendre", "Addyn"]  # captura inglesa #532, na ordem dos robôs (765958, 765957)
NAMES_TR = [("Chloe", "♣", "♣"), ("Elizabeth", "♫", "♫"), ("Abigail", "►", "◄")]  # 0027 (replay #706, cevre #11)
NEVER_SEEN = "CampaignInfo.Item, nunca visto na captura inglesa"
TR = "captura turca replay_packets.json"
# (campanha, item, fonte nova, fonte da 0034)
CARD_SOURCES = [(1001, 1080013, NEVER_SEEN, f"{TR} #1241"), (1001, 1080002, NEVER_SEEN, f"{TR} #1744")]

names = sa.table("world_robot_names", sa.column("name"), sa.column("prefix"), sa.column("suffix"))
cards = sa.table("campaign_cards", sa.column("campaign_id"), sa.column("template_id"), sa.column("source"))


def _names(rows: list[tuple[str, str, str]]) -> None:
    op.execute(names.delete())
    op.bulk_insert(names, [{"name": n, "prefix": a, "suffix": b} for n, a, b in rows])


def _sources(column: int) -> None:
    for row in CARD_SOURCES:
        where = (cards.c.campaign_id == row[0], cards.c.template_id == row[1])
        op.execute(cards.update().where(*where).values(source=row[column]))


def upgrade() -> None:
    _names([(n, "", "") for n in NAMES_EN])
    _sources(2)


def downgrade() -> None:
    _names(NAMES_TR)
    _sources(3)
