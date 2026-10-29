"""minijogos do operador ligados por padrão

``game_settings`` de caça-níquel, loteria, sorteio de grupo, cadeiras, caça ao tesouro, minério de Stokes e quiz,
com todos os parâmetros explícitos (os handlers não têm padrão no código). ``source`` de cada valor dentro da chave:
``cliente`` (ActionScript decompilado), ``idioma`` (language.txt inglês do mirror) ou ``TODO(inventado)`` (sem
captura: as capturas oficiais só mostram estes jogos fechados).

Janelas: ``cycleDays`` repete a edição a partir de ``begin`` (hora do jogo); o quiz segue a agenda do idioma.

Revision ID: 0103
Revises: 0102
Create Date: 2026-10-29 18:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0103"
down_revision = "0102"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"

SLOT: dict[str, Any] = {
    "begin": "2026-01-05 05:00:00",
    "cycleDays": 7,
    "type": 2,
    "rewardTemplateId": -100,
    "findCost": 10,
    "digitWeights": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    "noMoneyText": "Insufficient Balens",
    "source": {
        "cycleDays": 'idioma slot.slotHelpFrame.describe ("duration is 7 days")',
        "type": "cliente SlotFrame (2 = Other servers: recuperar pagando)",
        "rewardTemplateId": "cliente SlotFrame.setRewardIcon (-100/-300/-500/-600); " + INV + " qual",
        "findCost": INV + " (idioma: 'a few Balens')",
        "digitWeights": INV,
        "begin": INV,
        "noMoneyText": INV,
    },
}

LOTTERY: dict[str, Any] = {
    "begin": "2026-01-01 05:00:00",
    "cycleDays": 1,
    "onceNeedPoint": 100,
    "dayMaxCount": 5,
    "items": [
        [-100, 50000],
        [-300, 50000],
        [-600, 100],
        [-500, 10],
        [208009, 5],
        [208014, 5],
        [208017, 2],
        [208023, 2],
        [3020010, 2],
        [3040001, 2],
        [3270101, 2],
        [2120043, 2],
        [2131019, 10],
        [2131016, 1],
        [2131017, 1],
        [2131018, 1],
    ],
    "weights": [12, 10, 8, 8, 10, 8, 6, 6, 6, 6, 5, 5, 5, 3, 1.5, 0.5],
    "noticeText": "{nick} obtained {item} x{count}",
    "notices": 10,
    "source": {
        "onceNeedPoint/dayMaxCount": "idioma lottery.LotteryFrame.describe (os nomes); " + INV + " os valores",
        "items": "cliente LotteryFrame (até 16 casas); " + INV + " quais",
        "weights": INV,
        "cycleDays": INV + " (diária: o limite do idioma é por dia)",
        "noticeText": INV,
        "notices": INV,
    },
}

GROUP_DRAW: dict[str, Any] = {
    "items": [
        [-100, 20000],
        [-300, 20000],
        [208009, 3],
        [208014, 3],
        [3020010, 1],
        [2131019, 5],
        [2131016, 1],
        [-600, 50],
        [2131017, 1],
    ],
    "weights": [20, 20, 15, 12, 10, 10, 6, 5, 2],
    "source": {"items": "cliente GroupLuckFrame (9 casas); " + INV + " quais", "weights": INV},
}

CHAIRS: dict[str, Any] = {
    "begin": "2026-01-05 05:00:00",
    "cycleDays": 7,
    "chairsNeedPoints": 100,
    "rewardNeedChairs": 100,
    "luckyCount": 3,
    "comfortItems": ["208009|2", "-100|10000"],
    "luckyItems": ["2131018|1", "-600|500"],
    "emptyText": "No rewards to claim.",
    "source": {
        "campos": "cliente PublicChairsFrame (chairsNeedPoints, rewardNeedChairs, itens 'TemplateId|quantidade')",
        "regra e valores": INV + " (sem captura nem idioma)",
    },
}

TREASURE_HUNT: dict[str, Any] = {
    "openGrade": 32,
    "maxCount": 10,
    "interval": 1800,
    "addCost": 10,
    "shard": 2131019,
    "kit": 2131018,
    "shardsPerKit": 100,
    "nodes": [
        [1, "Whispering Woods", 120, 330],
        [2, "Old Watchtower", 230, 210],
        [3, "Misty Lake", 350, 300],
        [4, "Ruined Temple", 470, 180],
        [5, "Dragon Bones", 560, 320],
        [6, "Crystal Cave", 650, 200],
    ],
    "finds": [[2131019, 5, 50], [2131019, 10, 25], [2131016, 1, 15], [2131017, 1, 8], [2131018, 1, 2]],
    "eventDesc": "you found a buried chest!",
    "arriveText": "You arrived at {node}.",
    "lowLevelText": "Must be at least level 32 to claim.",
    "noMoneyText": "Insufficient Balens",
    "source": {
        "openGrade": "cliente TreasureHuntControler; idioma hunt.TreasureHuntFrame.gotoSeekLimit",
        "maxCount": "idioma hunt.TreasureHuntFrame.huntcountFull (10)",
        "shard/kit/shardsPerKit": "idioma hunt.TreasureHuntFrame.exchangeBtnTipData; templates 2131019/2131018",
        "lowLevelText": "idioma hunt.TreasureHuntFrame.gotoSeekLimit",
        "interval/addCost/nodes/finds/eventDesc/arriveText/noMoneyText": INV,
    },
}

STOKES_ORE: dict[str, Any] = {
    "begin": "2026-01-01 05:00:00",
    "cycleDays": 1,
    "oncePrice": 10,
    "tenPrice": 95,
    "dailyTurns": 50,
    "dailySpecial": 3,
    "cooldown": 60,
    "pickItem": 208523,
    "finds": [[208009, 1, 50], [208014, 1, 30], [3020010, 1, 15], [2131019, 1, 5]],
    "special": [[25, [[208017, 2]]], [50, [[208017, 5]]], [75, [[2131018, 1]]], [100, [[2131023, 1]]]],
    "findLine": "Received {item} x{count}",
    "luckLine": "{nick} reached floor {floor} and received {item} x{count}",
    "luckKeep": 10,
    "noMoneyText": "Insufficient Balens",
    "source": {
        "pickItem": "cliente StokesOreFrame.sendOpen (208523)",
        "special": "cliente StokesOreModel (4 andares, o último é o fundo); " + INV + " números e prêmios",
        "o resto": INV,
    },
}

QUIZ: dict[str, Any] = {
    "weekdays": [0, 2, 4],
    "start": "19:30",
    "minutes": 30,
    "readyMinutes": 30,
    "readSeconds": 5,
    "askSeconds": 15,
    "resultSeconds": 5,
    "openGrade": 30,
    "count": 20,
    "wrongPoints": 1,
    "rightBase": 10,
    "doubleFactor": 2,
    "helps": 1,
    "vipHelps": 2,
    "expPerPoint": 10,
    "topCount": 10,
    "topExp": 100,
    "questions": [
        ["How many players can join a party?", "3", "2", "5", "10"],
        ["Which currency is used to buy items in the Mall?", "Balens", "Gold", "Daru", "Kyanite"],
        ["What do you need to learn hero skills?", "Daru", "Gold", "Kyanite", "Balens"],
        ["Which building trains troops?", "Barracks", "Temple", "Fountain", "Tavern"],
        ["Which building produces gold?", "Houses", "Barracks", "Wall", "Tavern"],
        ["How many days does a week have?", "7", "5", "6", "8"],
        ["What color is the sky on a clear day?", "Blue", "Green", "Red", "Purple"],
        ["How many hours are in a day?", "24", "12", "20", "36"],
        ["Which animal is known as the king of the jungle?", "Lion", "Tiger", "Wolf", "Bear"],
        ["Which planet is closest to the Sun?", "Mercury", "Venus", "Earth", "Mars"],
        ["How many legs does a spider have?", "8", "6", "10", "4"],
        ["What is frozen water called?", "Ice", "Steam", "Fog", "Dew"],
        ["Which is the largest ocean?", "Pacific", "Atlantic", "Indian", "Arctic"],
        ["How many minutes are in an hour?", "60", "100", "30", "90"],
        ["Which metal is liquid at room temperature?", "Mercury", "Iron", "Copper", "Silver"],
        ["What do bees make?", "Honey", "Milk", "Silk", "Wax paper"],
        ["Which season comes after winter?", "Spring", "Summer", "Autumn", "Winter"],
        ["How many sides does a triangle have?", "3", "4", "5", "6"],
        ["What is the opposite of victory?", "Defeat", "Triumph", "Glory", "Honor"],
        ["Which gas do plants absorb?", "Carbon dioxide", "Oxygen", "Helium", "Neon"],
    ],
    "source": {
        "weekdays/start/minutes": "idioma answer.view.helpHtmlTxt (Monday, Wednesday, Friday 19:30-20:00)",
        "readSeconds/askSeconds/resultSeconds": "idioma answer.view.helpHtmlTxt (5/15/5 s)",
        "wrongPoints": "idioma answer.view.helpHtmlTxt (1 point)",
        "topCount": "idioma answer.view.helpHtmlTxt (top 10)",
        "openGrade": "cliente AnswerManager.OPEN_GRADE",
        "questions": INV + " (Option1 = certa; o cliente embaralha). HeartTempInfos não tem certa; internet sem banca",
        "readyMinutes/count/rightBase/doubleFactor/helps/vipHelps/expPerPoint/topExp": INV,
    },
}

SEEDS = {
    "slot_machine": SLOT,
    "lottery": LOTTERY,
    "group_draw": GROUP_DRAW,
    "chairs": CHAIRS,
    "treasure_hunt": TREASURE_HUNT,
    "stokes_ore": STOKES_ORE,
    "quiz": QUIZ,
}
SOURCE = "minijogos (handlers/slot, lottery, group_draw, chairs, treasure_hunt, ore, quiz): cliente + idioma + " + INV


def upgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(settings.delete().where(settings.c.key.in_(list(SEEDS))))
    op.bulk_insert(settings, [{"key": k, "value": json.dumps(v), "source": SOURCE} for k, v in SEEDS.items()])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_(list(SEEDS))))
