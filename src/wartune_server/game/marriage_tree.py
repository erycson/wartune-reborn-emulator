"""Árvore do casal (Marriage Tree) na fazenda: o estado e o ``MarriageTreeMsg`` (4386 ``marriageTree`` e 4678).

O estado é um JSON com os próprios nomes de campo do ``MarriageTreeMsg`` (mais ``day``, ``start`` e ``end`` em
segundos), gravado igual nas duas linhas de ``marriages``. Regras do cliente inglês (``m7/farm/marrytree/
MarryTreeView``, ``m9/marry/income/MarryTreeFosterFrame``) e do ``helpContent``:

* ``startTime`` vazio = pede rega (estado 4); a rega (1001) liga 5 h (``mar_tree_time`` 300 min), até
  ``mar_feed_count`` (2, padrão do cliente: o ConfigInfo não existe) vezes por dia;
* ``treeState``: uma condição por hora das 5 (0 nada, 1 mato, 2 praga); cada uma que já chegou e não foi limpa (1003)
  tira 10 do status (``MarryTreeView.__timerHandler``); status entre 0 e 800;
* cultivar (1002) soma ``Feed`` × quantidade dos itens da bancada, em dobro no item sorteado do lado
  (``trainAType``/``trainBType``), ``mar_tree_train_count`` (10) vezes por dia;
* depois do fim (estado 3) cada lado colhe uma vez (1004); com os dois colhidos ela volta a pedir rega ("Can be
  energized again once your spouse harvests it").
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from typing import Any

from ..domain import gameday
from ..domain.models import Character, Marriage, MarriageState
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from .builders import login as b

TREE_MAX = 800  # MarryTreeView: _progress.setData(valor, 800)
SLOTS = 5  # MarryTreeView: _totalTime / 5 por condição
PEST_CUT = 10  # MarryTreeView: -10 por condição ainda lá
BENCH = 10  # MarryTreeFosterFrame: as casas 0-9 da bancada (STORE) entram no cultivo
NO_PESTS = ",".join("0" * SLOTS)
FIELDS = set(pb.MarriageTreeMsg.DESCRIPTOR.fields_by_name)
# TODO(inventado): chance de mato ou praga em cada hora (o cliente só desenha o que vem no treeState)
PEST_CHANCE = 0.5


def load(m: Marriage | None) -> dict[str, Any]:
    return json.loads(m.tree) if m is not None and m.tree else {}


def fresh(t: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Os contadores do dia (regas e cultivos) zeram na virada; a árvore fica (o oficial manda a de ontem com
    ``feedCount`` 0: 191924 #1249)."""
    today = gameday.today(now)
    if t and t.get("day") != today:
        t |= {"day": today, "feedCount": 0, "trainACount": 0, "trainBCount": 0}
    return t


def feed_items(templates: GameTemplates) -> list[int]:
    return [int(r["TemplateId"]) for r in templates.rows("ItemTempInfos") if int(r.get("Feed") or 0) > 0]


def new(a: Character, b_: Character, templates: GameTemplates, now: datetime) -> dict[str, Any]:
    """Árvore nova do casal; ``A`` é o homem (dedução: 191924 #1249, A "Dray", B "BimboBaggins" de ``sexs`` 0)."""
    if a.sex == 0 and b_.sex != 0:
        a, b_ = b_, a
    pool = feed_items(templates)
    return {
        "userIdA": a.id, "nickNameA": a.nickname or "", "jobA": a.job,
        "userIdB": b_.id, "nickNameB": b_.nickname or "", "jobB": b_.job,
        "stateValue": 0, "feedCount": 0, "startTime": "", "endTime": "", "trainACount": 0, "trainBCount": 0,
        "trainAType": random.choice(pool), "trainBType": random.choice(pool), "isGetA": False, "isGetB": False,
        "treeState": NO_PESTS, "feedUser": 0, "day": gameday.today(now), "start": 0, "end": 0,
    }  # fmt: skip


def pests() -> str:
    return ",".join(str(random.choice((1, 2))) if random.random() < PEST_CHANCE else "0" for _ in range(SLOTS))


def passed(t: dict[str, Any], now: datetime) -> int:
    """Quantas horas (condições) já chegaram: a do índice ``i`` aparece em ``i × duração / 5``."""
    if not t.get("start"):
        return 0
    slot = (t["end"] - t["start"]) / SLOTS
    return min(SLOTS, int((now.timestamp() - t["start"]) // slot) + 1)


def value(t: dict[str, Any], now: datetime) -> int:
    """O status que o cliente mostra: o gravado menos 10 por mato/praga que já chegou e não foi limpo."""
    left = sum(1 for x in t["treeState"].split(",")[: passed(t, now)] if x != "0")
    return max(0, min(TREE_MAX, int(t["stateValue"]) - PEST_CUT * left))


def msg(t: dict[str, Any]) -> pb.MarriageTreeMsg:
    return pb.MarriageTreeMsg(**{k: v for k, v in t.items() if k in FIELDS})


def view(m: Marriage | None, now: datetime) -> pb.MarriageTreeMsg | None:
    if m is None or m.state != MarriageState.MARRIED or not m.tree:
        return None
    return msg(fresh(load(m), now))


def stamp(at: float) -> str:
    return b.fmt_time(datetime.fromtimestamp(at, UTC))  # como os outros horários (``clock.now()`` em UTC)
