"""campanha 1003: Perene Bone da missão 190 e a Mystery Box sorteada

Da captura ``oficial_20261023-171155-1`` (duas voltas na 1003, a 2ª com a missão 190 "The Perene Bones" aberta):

- (visto) Perene Bone (2100003) cai por nó vencido só com a missão aberta (``rules.quest_goods_wanted``): 103102 x2
  (#3296), e a mina 103105 com os dois nós que ela fecha, 103111 e 103112, x1 cada (#3514, #3540, #3560: uma luta
  só). Nenhum nas lutas depois da entrega (#3558).
  (dedução) 103103 é o mesmo Undead Warrior (sonType 2104) do 103102: x2.
- (visto) Mystery Box 103108 (chave 208005): 5.000 Gold (oficial_20261023-153200-1 #917) ou Lvl. 2 Luck Stone x2
  (#2551, #3788). (dedução) as duas por igual, de três amostras; o nó não traz param5.

Revision ID: 0062
Revises: 0061
Create Date: 2026-10-24 00:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None

PERENE = 2100003
DROPS = {
    "103102": [[PERENE, 2, 1.0]],
    "103103": [[PERENE, 2, 1.0]],
    "103105": [[PERENE, 1, 1.0]],
    "103111": [[PERENE, 1, 1.0]],
    "103112": [[PERENE, 1, 1.0]],
    # TODO(inventado): Undead Crusader (103104, 103106, 103202) e Undead Gladiator (103203, 103206) não lutaram com a
    # missão aberta; x1 cada
    "103104": [[PERENE, 1, 1.0]],
    "103106": [[PERENE, 1, 1.0]],
    "103202": [[PERENE, 1, 1.0]],
    "103203": [[PERENE, 1, 1.0]],
    "103206": [[PERENE, 1, 1.0]],
}
MYSTERY = "103108"
PICK = [[[-100, 5000]], [[2040102, 2]]]


def _table() -> sa.TableClause:
    return sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"))


def _load() -> dict[str, object] | None:
    t = _table()
    row = op.get_bind().execute(sa.select(t.c.data).where(t.c.campaign_id == 1003)).first()
    return json.loads(row[0]) if row else None


def _save(data: dict[str, object]) -> None:
    t = _table()
    op.execute(t.update().where(t.c.campaign_id == 1003).values(data=json.dumps(data, ensure_ascii=False)))


def upgrade() -> None:
    data = _load()
    if data is None:
        return
    data["drops"] = DROPS
    box = data["confirms"][MYSTERY]  # type: ignore[index]
    box.pop("drops", None)
    box["pick"] = PICK
    _save(data)


def downgrade() -> None:
    data = _load()
    if data is None:
        return
    data.pop("drops", None)
    box = data["confirms"][MYSTERY]  # type: ignore[index]
    box.pop("pick", None)
    box["drops"] = [[-100, 5000]]
    _save(data)
