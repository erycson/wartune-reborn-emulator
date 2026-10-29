"""treasure_hunt: o "+" gasta Exploration Artifact e cada evento tem a sua moeda (captura 20261029-121453-1 #2801-#2860)

- op 7 (#2803-#2806, #2830-#2833, #2859-#2860): tira 1 Exploration Artifact (2131022): 115, 111 "Treasure Hunt
  attempts increased!" e 4914 op 2 com seekCount + 1; sem o item, só 111 "Not enough Exploration Artifact!". Não há
  preço em Balens: ``addCost``/``noMoneyText`` (inventados na 0103/0136) saem.
- ``eventDescs`` vira [texto, moeda, valor]: 4 de ouro (32000, pago no 109) e o Dwarf Merchant de Daru (19200, pago
  no 3: strategy 3375968 -> 3356768 em #2788/#2839, sem 109). Mais os prêmios dos nós 6 (#2826) e 8 (#2854).

Revision ID: 0137
Revises: 0136
Create Date: 2026-10-29 22:00:00.000000
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0137"
down_revision = "0136"
branch_labels = None
depends_on = None

CAP = "captura 20261029-121453-1"


def _m0136() -> Any:
    spec = importlib.util.spec_from_file_location("m0136", Path(__file__).with_name("0136_caca_cartas_captura.py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def value() -> dict[str, Any]:
    old = _m0136()
    v: dict[str, Any] = json.loads(json.dumps(old.TREASURE_HUNT))
    for k in ("addCost", "noMoneyText"):
        v.pop(k)
        v["source"].pop(k, None)
    v["eventDescs"] = [[t, "gold", 32000] for t in v["eventDescs"]] + [
        [
            "You happen across a fortune teller who has seen the treasure you’re looking for. You try to pry the "
            "location from him but to no avail; he’s down on his luck and needs his palm greased. Spend <font "
            "color='#ff0000'>32000 Gold</font> to learn the location?",
            "gold",
            32000,
        ],
        [
            "You nearly fall over a Dwarf Merchant, who are well-known for carrying and selling rare treasures via "
            "raffle.“Gambling!  This is brazen gambling! ” you shout at him in anger, before submitting to his "
            "dwarvish retail therapy. Would you like to spend <font color='#ff0000'>19200 Daru</font> to enter in "
            "the Dwarf Merchant’s raffle?",
            "daru",
            19200,
        ],
    ]
    v.pop("goldCost")
    v["prizes"] |= {"6": [[2131017, 1], [2131019, 5]], "8": [[2131017, 1], [2131019, 2]]}
    v["addItem"] = 2131022
    v["addOkText"] = "Treasure Hunt attempts increased!"
    v["addNoItemText"] = "Not enough Exploration Artifact!"
    v["source"].pop("eventDescs/goldCost", None)
    v["source"] |= {
        "eventDescs": CAP + " #453, #506, #550, #2810 (ouro, 109 #508/#2812) e #2837 (Daru, 3 #2839)",
        "prizes": CAP + " 4915 #493 (12), #524 (7), #567 (3), #2826 (6), #2854 (8)",
        "addItem/addOkText/addNoItemText": CAP + " #2803-#2806, #2859-#2860",
        "defaultPrize": v["source"]["defaultPrize"].replace("três vistos", "cinco vistos"),
    }
    return v


def _put(val: dict[str, Any], source: str) -> None:
    s = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(s.delete().where(s.c.key == "treasure_hunt"))
    op.bulk_insert(s, [{"key": "treasure_hunt", "value": json.dumps(val), "source": source}])


def upgrade() -> None:
    _put(value(), _m0136().SOURCE)


def downgrade() -> None:
    old = _m0136()
    _put(old.TREASURE_HUNT, old.SOURCE)
