"""treasure_hunt: prêmio e moeda sorteados, preço pelo nível (capturas 20261029-121453-1 e 20261031-183522-1)

A 183522 (#8956-#9254, nível 34) mostra que o prêmio não é do nó: Desert of Curses deu Expert+3 (#9002) e Novice+3
(#9076), Buradoth's Grave Expert+5 (#9053) e Expert+3 (#9152). E a moeda não é do texto: a mesma caravana pede 34000
Gold (#8962) e 680 Kyanite (#8985), o fortune teller (19200 Daru na 121453) pede 20400 Daru (#9108).

- ``prizes``/``defaultPrize`` saem; ``prizeKits`` [kit, peso] e ``prizeShards`` [quantidade, peso] são a contagem das
  15 linhas 4915 das duas capturas (kit: 6 Novice 2131016, 9 Expert 2131017; shards: 2 ×6, 3 ×6, 5 ×3; o 4 nunca saiu).
- ``eventDescs`` vira só o texto com ``{cost}`` (9 textos vistos); ``coins`` [moeda, por nível, nome]: ouro 1000,
  Daru 600 e Kyanite 20 por nível (32000/19200 no 32 da 121453; 34000/20400/680 no 34 da 183522; Kyanite sai no 109
  ``crystalsCount``, #8987). Moeda sorteada uniforme (vistas 6 de ouro, 4 de Daru, 4 de Kyanite).
- Sem reset diário: a 183522 abre com seekCount 9 e o relógio de 6 h correndo (#8957).

Revision ID: 0145
Revises: 0144
Create Date: 2026-11-01 12:00:00.000000
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0145"
down_revision = "0144"
branch_labels = None
depends_on = None

CAP = "capturas 20261029-121453-1 e 20261031-183522-1"
SPEND = "<font color='#ff0000'>{cost}</font>"


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def value() -> dict[str, Any]:
    v: dict[str, Any] = _load("0137_caca_cartas_artefato").value()
    for k in ("prizes", "defaultPrize"):
        v.pop(k)
        v["source"].pop(k, None)
    texts = [str(t).replace("<font color='#ff0000'>32000 Gold</font>", SPEND) for t, _, _ in v["eventDescs"]]
    texts = [t.replace("<font color='#ff0000'>19200 Daru</font>", SPEND) for t in texts]
    v["eventDescs"] = texts + [
        "You discover temple ruins, and after extensive searching, you discover a sealed door. You cry out “Open "
        "Sesame!” and to your surprise it does. Out stumbles a wretched gnome, Sesame, who informs you that this area "
        "is gnome territory. Would you like to spend " + SPEND + " to trade with Sesame for treasure?",
        "You approach the Dragon’s Castle where legend has it a great treasure lies hidden - but you shrink back at "
        "the sight of its impenetrable castle walls. Reluctantly, you circle the castle several times before "
        "inspiration hits you!  Spend " + SPEND + " to have the Thieves Guild break into the Dragon's Castle?",
        "A horde of Undead rain spells down upon you. You are but an inch away from death when you realize they have "
        "given up and now believe you to be some kind of World BOSS. Taking out a locked treasure chest, they beg you "
        "to release them. Spend " + SPEND + " and have Priests unlock the treasure chest?",
        "You are blindsided by a colossal black dragon, who with a single breath pushes you in a secluded valley "
        "with no visible exit. Therein lies a secret treasure chest - but it’s too heavy for you to carry out. Would "
        "you like to spend " + SPEND + " and enlist Hawkmen to airlift you out of there?",
    ]
    v["coins"] = [["gold", 1000, "Gold"], ["daru", 600, "Daru"], ["kyanite", 20, "Kyanite"]]
    v["prizeKits"] = [[2131016, 6], [2131017, 9]]
    v["prizeShards"] = [[2, 6], [3, 6], [5, 3]]
    v["source"] |= {
        "eventDescs": CAP + " (121453 #453/#506/#550/#2810/#2837; 183522 #8962-#9160)",
        "coins": CAP + " (32000/19200 no nível 32; 34000/20400/680 no 34; moeda independente do texto)",
        "prizeKits/prizeShards": CAP + " 4915 (121453 #493-#2854, 183522 #8978-#9176): contagem das 15 vistas",
    }
    return v


def _put(val: dict[str, Any], source: str) -> None:
    s = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(s.delete().where(s.c.key == "treasure_hunt"))
    op.bulk_insert(s, [{"key": "treasure_hunt", "value": json.dumps(val), "source": source}])


def upgrade() -> None:
    _put(value(), _load("0136_caca_cartas_captura").SOURCE)


def downgrade() -> None:
    _put(_load("0137_caca_cartas_artefato").value(), _load("0136_caca_cartas_captura").SOURCE)
