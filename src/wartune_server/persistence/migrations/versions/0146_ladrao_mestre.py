"""terra secreta: a luta e o baú do Master Treasure Thief, coletas e EXP da árvore (captura 20261031-183522-1)

- ``campaign_contents`` 7501 ganha ``battles["750144"]``: o 157 de #11143 (o nó que o jogador atacou em #11139),
  battleType 39, mapTempId 1, um herói só (72004 "Master Treasure Thief", nível 30, 15000 de vida, ``monster030``,
  skills 60131/60419/60420/60999) e battleScene 15 no 4103. Vale para os 30 nós (sonType 2189, ``battle_like``).
- ``game_settings.fam_lords``: o baú de cada vitória, Lvl. 1 Contribution Badge (2030801) ×3 (9 de 9 vitórias).
- ``game_settings.fam_tree``: ``exp_per_grade`` 17 (tique de 3468 no nível 34 com a árvore 6), as coletas dão 1, 5 ou
  10 de contribuição (12, 19 e 13 das 44 vistas) e mostram 10 das 21 por leva. TODO(inventado): ``power_step`` 20
  (só se sabe que 13 de energia não mudou o tique) e ``power_rate``.

Revision ID: 0146
Revises: 0145
Create Date: 2026-11-01 18:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0146"
down_revision = "0145"
branch_labels = None
depends_on = None

CAMPAIGN, CAMP = 7501, "750144"
CAP = "(visto) captura 20261031-183522-1"
_TROOP = {"tempId": 10432, "type": 1, "side": 1, "initHp": 3913, "hp": 3913, "qteTime": 0, "castTime": 4000}
BATTLE: dict[str, Any] = {
    "battleType": 39,
    "mapTempId": 1,
    "attackModel": 2,
    "soldiers": [
        _TROOP | {"livingId": 1, "pos": 1, "skillId": [40, 41] * 5},
        _TROOP | {"livingId": 2, "pos": 7, "skillId": [40, 41] * 5},
    ],
    "heroes": [
        {
            "heroId": 1300000000, "livingId": 4, "userId": 0, "userPics": 0, "tempId": 72004, "type": 3,
            "nickName": "Master Treasure Thief", "grade": 30, "side": 2, "pos": 5, "maxHp": 15000, "initHp": 15000,
            "hp": 15000, "sp": 0, "captain": 3, "res": "monster030", "qteTime": 0, "castTime": 5000,
            "skillId": [60131, 60419, 60420, 60999],
        }
    ],
    "player": {"livingId": 3, "pos": 6},
    "map": CAMPAIGN,
    "gpBonus": 0,
    "strategyBonus": 0,
    "battleScene": 15,
}  # fmt: skip
LORDS = {"drops": [[2030801, 3, 1.0]]}
TREE_OLD = {"exp_per_grade": 2, "power_step": 10, "power_rate": 0.1, "collect_offer": 5}
TREE = {
    "exp_per_grade": 17, "power_step": 20, "power_rate": 0.1, "collect_offers": [[1, 12], [5, 19], [10, 13]],
    "collect_shown": 10,
}  # fmt: skip
TREE_SOURCE = CAP + " (tique 3468/4162, coletas 1/5/10 e 10 de 21); TODO(inventado) power_step e power_rate"
TREE_OLD_SOURCE = "TODO(inventado): a ajuda do cliente não dá os valores (EXP por tique, bônus da energia, coleta)"
contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"))
settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _battles(change: Any) -> None:
    bind = op.get_bind()
    raw = bind.execute(sa.select(contents.c.data).where(contents.c.campaign_id == CAMPAIGN)).scalar()
    if raw is None:
        return
    data = json.loads(raw)
    change(data.setdefault("battles", {}))
    op.execute(
        contents.update().where(contents.c.campaign_id == CAMPAIGN).values(data=json.dumps(data, ensure_ascii=False))
    )


def _put(key: str, value: Any, source: str) -> None:
    op.execute(settings.delete().where(settings.c.key == key))
    op.bulk_insert(settings, [{"key": key, "value": json.dumps(value), "source": source}])


def upgrade() -> None:
    _battles(lambda b: b.__setitem__(CAMP, BATTLE))
    _put("fam_lords", LORDS, CAP + " #11215-#12738: 2030801 ×3 em todas as 9 vitórias")
    _put("fam_tree", TREE, TREE_SOURCE)


def downgrade() -> None:
    _battles(lambda b: b.pop(CAMP, None))
    op.execute(settings.delete().where(settings.c.key == "fam_lords"))
    _put("fam_tree", TREE_OLD, TREE_OLD_SOURCE)
