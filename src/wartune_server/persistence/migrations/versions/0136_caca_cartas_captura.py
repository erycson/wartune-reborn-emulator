"""treasure_hunt (Great Card Hunt) pela captura inglesa 20261029-121453-1 (d29 #447-#575)

Troca a semente da 0103 (nós, achados, 30 min e textos inventados) pelo que o oficial mandou: os 36 nós do 4914 op 1
(#448), 3 explorações na primeira abertura com ``nextAddTime`` 21600 (#448), o nó inicial 7, os três ``eventDesc``
(#453, #506, #550), 32000 de ouro por tesouro (109 de #508/#552), o prêmio por nó (4915 de #493, #524, #567), os
textos do 111/4915/83 e o correio "Treasure Hunt Rewards" (4131 #606: validade 3, sendType 4). Continua
``TODO(inventado)``: o preço do "+" (op 7; ``TreasureHuntFrame._addSeekCountClick`` manda sem confirmação, o
``treasurehunt.xml`` não tem dica e o language.txt não tem preço; a captura não tem op 7), o prêmio dos nós fora
da captura e o texto de ouro insuficiente.

Revision ID: 0136
Revises: 0135
Create Date: 2026-10-29 20:00:00.000000
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0136"
down_revision = "0135"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"
CAP = "captura 20261029-121453-1"
KIT, SHARD = 2131017, 2131019  # Expert Summoner's Kit (115 #479), Summoner's Shard (115 #553)

TREASURE_HUNT: dict[str, Any] = {
    "openGrade": 32,
    "maxCount": 10,
    "startCount": 3,
    "startNode": 7,
    "interval": 21600,
    "addCost": 10,
    "goldCost": 32000,
    "shard": SHARD,
    "kit": 2131018,
    "shardsPerKit": 100,
    "nodes": [
        [1, "Nightmare Ruins", 248, 127],
        [2, "Forest of Chaos", 304, 66],
        [3, "Blood Moorland", 345, 138],
        [4, "Desert of Palms", 256, 204],
        [5, "Soul Trials", 476, 64],
        [6, "Demon's Rill", 428, 114],
        [7, "Serpent's Den", 407, 202],
        [8, "Banshee Wetlands", 543, 133],
        [9, "Bretheran Abyss", 380, 265],
        [10, "Duskin Arena", 472, 249],
        [11, "Termini Cliff", 566, 222],
        [12, "Roaring Wetlands", 476, 308],
        [13, "Forest of Doom", 578, 328],
        [14, "Edena Village", 627, 282],
        [15, "Worg Lair", 159, 308],
        [16, "Baylon Plains", 130, 366],
        [17, "Temple of lbalize (Outer)", 191, 450],
        [18, "Orc Plains", 272, 369],
        [19, "Camp Calorn", 327, 317],
        [20, "Tribal Plateu", 368, 386],
        [21, "Temple of lbalize (Inner)", 309, 452],
        [22, "Swamp of the Undead", 665, 223],
        [23, "Delphinian Swamp", 672, 158],
        [24, "Boneyard", 772, 83],
        [25, "Shrine of Sakaiya", 822, 144],
        [26, "Serenity Lake", 751, 191],
        [27, "Immortal Ruins", 806, 233],
        [28, "Blazing Desert", 741, 266],
        [29, "Desert of Curses", 700, 324],
        [30, "Desert of Despair", 666, 386],
        [31, "Reaper's Illusion", 579, 430],
        [32, "The Forgotten Dunes", 839, 307],
        [33, "Gods Relics", 775, 346],
        [34, "Buradoth's Grave", 791, 406],
        [35, "Ukiah Sands", 740, 462],
        [36, "Twilight Arena", 654, 471],
    ],
    "prizes": {"12": [[KIT, 1], [SHARD, 5]], "7": [[KIT, 1], [SHARD, 3]], "3": [[KIT, 1], [SHARD, 2]]},
    "defaultPrize": [[KIT, 1], [SHARD, 3]],
    "eventDescs": [
        "You find Elven tracks and follow them for 7 days before realizing you’re running in circles. A passing "
        "caravan takes pity on you’re crazed state and lets you hitch a ride. Looking around, you realize that the "
        "caravan’s cargo is none other than the treasure! Spend <font color='#ff0000'>32000 Gold</font> to trade "
        "for the treasure?",
        "After long nights of battle, you are taken captive by demons. Impressed with your resilience in battle, "
        "the Demonlord breaks down and becomes your sworn comrade. And his vaults happen to hold the very treasure "
        "you’re looking for! Would you like to spend <font color='#ff0000'>32000 Gold</font> and trade for treasure "
        "with the Demonlord?",
        "You come across Goddess Lagoon and are convinced that the Treasure Cache you’re seeking lies here. You "
        "begin practicing diving for days, until you realize that the lagoon is actually only knee-deep. Would you "
        "like to spend <font color='#ff0000'>32000 Gold</font> to have the Mercenaries Guild dredge the lagoon for "
        "treasure?",
    ],
    "failText": "Operation failed",
    "mailSuffix": ", inventory full, please check your mail!",
    "gainedText": "Gained {items} from {node}",
    "mailTitle": "Treasure Hunt Rewards",
    "mailDays": 3,
    "mailSendType": 4,
    "noGoldText": "Operation failed",
    "lowLevelText": "Must be at least level 32 to claim.",
    "noMoneyText": "Insufficient Balens",
    "source": {
        "openGrade": "cliente TreasureHuntControler; idioma hunt.TreasureHuntFrame.gotoSeekLimit",
        "maxCount": "cliente TreasureHuntFrame (seekCount < 10); idioma hunt.TreasureHuntFrame.huntcountFull",
        "startCount/startNode/interval/nodes": CAP + " #448 (4914 op 1: seekCount 3, nextAddTime 21600, nó 7)",
        "eventDescs/goldCost": CAP + " #453, #506, #550 (texto) e 109 #508/#552 (-32000)",
        "prizes": CAP + " 4915 #493 (nó 12), #524 (nó 7), #567 (nó 3)",
        "defaultPrize": INV + " (nós fora da captura; o kit x1 é igual nos três vistos; procurado sem achar: "
        "ItemTempInfos 2131016-2131019 só dizem a chance de carta do kit e '100 shards por Master Kit', "
        "language.txt hunt.* e funny.*101 sem prêmio, TreasureHuntFrame/HunterDialogFrame sem tabela)",
        "failText/mailSuffix/gainedText": CAP + " 111 #528/#492, 4915 #493",
        "mailTitle/mailDays/mailSendType": CAP + " 4131 #606",
        "noGoldText": INV + " (sem captura de ouro insuficiente)",
        "addCost": INV + " (op 7 sem confirmação no TreasureHuntFrame; sem dica no treasurehunt.xml nem preço "
        "no language.txt; sem op 7 na captura)",
        "shard/kit/shardsPerKit": "idioma hunt.TreasureHuntFrame.exchangeBtnTipData; templates 2131019/2131018",
        "lowLevelText": "idioma hunt.TreasureHuntFrame.gotoSeekLimit",
    },
}
SOURCE = "treasure_hunt (handlers/treasure_hunt): " + CAP + " + cliente; ver source"


def _settings() -> Any:
    return sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _put(value: dict[str, Any], source: str) -> None:
    s = _settings()
    op.execute(s.delete().where(s.c.key == "treasure_hunt"))
    op.bulk_insert(s, [{"key": "treasure_hunt", "value": json.dumps(value), "source": source}])


def upgrade() -> None:
    _put(TREASURE_HUNT, SOURCE)


def downgrade() -> None:
    spec = importlib.util.spec_from_file_location("m0103", Path(__file__).with_name("0103_minijogos.py"))
    assert spec is not None and spec.loader is not None
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    _put(old.TREASURE_HUNT, old.SOURCE)
