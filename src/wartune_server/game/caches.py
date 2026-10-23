"""Treasure Cache (``WildLandMsg`` type 22, "Rebel") nos mapas compartilhados: o sorteio, a luta e o prêmio.

(visto) oficial_20261023-153200-1 e oficial_20261023-171155-1, mapa 1:

- No 4129 junto das minas: ``templateId`` 2201xx (``MapPhysicsTempInfos`` MasterType 22, ``Grades`` = nível),
  ``createDate`` e ``refreshTime`` próprios de cada baú (o que falta da vida dele, em ms: 18000000 no recém-nascido
  828569 de #1938, que é o ``RefreshTime`` 18000 s do template), ``armyPawn`` com 3 guardas de ``ownPawns`` 1.
- 5160 no tile: 140 do baú em luta (state 4), 157 com ``battleType`` 3, ``mapTempId`` = o mapa, os 3 guardas nas
  posições 4, 2 e 8 com a vida de um soldado (``Live`` / 100: 840 no 6011) (#570-#574).
- Vitória (#645-#670): o item (115, 111 e 83 "Received: Lvl. 3 Luck Stone x1", com o ``x1``), 4103 com
  ``battleScene`` 0, e o baú sai do mapa (140 state 0). Derrota (#370-#381): 4103 result 2 e o baú volta a state 1.
- Um baú novo nasce em outro tile (828569, #1938) depois que um some.

Quantos e onde não dá para ver de um jogador só. O nível fica na faixa do mapa (cliente: ``MapInfos`` MinLevel e
MaxLevel, 11-20 no mapa 1 ... 51-60 no 5; os vistos são 13 a 15). O resto é ``game_settings.treasure_caches``
(migração 0063). Cada vaga do mapa tem um nível fixo e vive o ``RefreshTime`` do template; a cada vida nasce num tile
sorteado (semente: mapa, vaga, vida), então todo jogador vê os mesmos baús sem tabela de estado. O baú aberto vai para
``treasure_cache_opens`` (some para todos até a próxima vida).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

from ..domain.models import PlayerSnapshot
from ..domain.world import World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import outer_city as oc
from .mines import game_date, world_mine_at
from .rules import job_type

CACHE_TYPE = 22  # WildLandMsg.type e MapPhysicsTempInfos.MasterType
CACHE_ALIVE, CACHE_FIGHTING, CACHE_GONE = 1, 4, 0  # WildLandMsg.state
ID_BASE = 1_100_000_000  # longe dos monstros (1_000_000_000 + mapa × 10000) e das terras do oficial (8xxxxx)
EDGE = 20  # tiles da borda, como os monstros
BATTLE_TYPE, SCENE = 3, 0  # 157 e 4103 (#574, #662)
GUARD_LIVINGS = ((4, 4), (5, 2), (6, 8))  # (livingId, pos) dos 3 guardas (#574)
GUARD_FIRST, GUARD_LAST = 6001, 6099  # PawnTempInfos dos guardas vistos (6011, 6013, 6014)
LUCK_STONE, LUCK_STONE_TOP = 2040100, 9  # 2040100 + n = "Lvl. n Luck Stone" (n até 9 no tempinfos)
GEAR = "1"  # ItemTempInfos.MasterType dos equipamentos
# TODO(inventado): quantos baús por mapa (a captura só mostra a vizinhança do castelo: 7 baús em ~300 × 250 tiles do
# mapa 1, ~1 a cada 10 000 tiles; aqui 1 a cada 25 000) e o prêmio (duas amostras: Lvl. 3 Luck Stone e Elders Robe)
DEFAULT: dict[str, Any] = {
    "maps": {
        "1": {"count": 1000, "levels": [11, 20]},
        "2": {"count": 640, "levels": [21, 30]},
        "3": {"count": 250, "levels": [31, 40]},
        "4": {"count": 160, "levels": [41, 50]},
        "5": {"count": 90, "levels": [51, 60]},
    },
    "loot": {"stone_weight": 1, "gear_weight": 1, "gear_profile": 2, "gear_below": 5, "gear_above": 2},
}
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)  # origem das vidas; o deslocamento de cada vaga é sorteado


@dataclass(frozen=True, slots=True)
class Cache:
    id: int
    map_id: int
    template_id: int
    level: int
    x: int
    y: int
    born: datetime
    ends: datetime


def settings(world: World) -> dict[str, Any]:
    return dict(world.settings.get("treasure_caches") or DEFAULT)


@cache
def _levels(templates: GameTemplates) -> dict[int, tuple[int, int]]:
    return {
        int(r["Grades"]): (int(r["TemplateId"]), int(r.get("RefreshTime") or 0))
        for r in templates.find("MapPhysicsTempInfos", MasterType=str(CACHE_TYPE))
    }


def template_of(templates: GameTemplates, level: int) -> tuple[int, int]:
    """(template, RefreshTime em s) do baú de um nível."""
    return _levels(templates).get(level, (0, 0))


def on_map(world: World, templates: GameTemplates, map_id: int, now: datetime) -> list[Cache]:
    """Os baús vivos agora no mapa (nenhum fora dos mapas de ``settings``)."""
    conf, size = settings(world)["maps"].get(str(map_id)), oc.map_size(templates, map_id)
    if not conf or size is None or min(size) <= 2 * EDGE:
        return []
    low, high = conf["levels"]
    out = []
    for slot in range(int(conf["count"])):
        fixed = random.Random(f"cache:{map_id}:{slot}")
        level = fixed.randint(low, high)
        template, period = template_of(templates, level)
        if not template or period <= 0:
            continue
        offset = fixed.randrange(period)
        life = math.floor(((now - EPOCH).total_seconds() - offset) / period)
        born = EPOCH + timedelta(seconds=life * period + offset)
        rng = random.Random(f"cache:{map_id}:{slot}:{life}")
        x, y = rng.randrange(EDGE, size[0] - EDGE), rng.randrange(EDGE, size[1] - EDGE)
        while world_mine_at(world, templates, map_id, x, y) is not None:  # o tile é da mina (o 5160 acharia o baú)
            x, y = rng.randrange(EDGE, size[0] - EDGE), rng.randrange(EDGE, size[1] - EDGE)
        uid = ID_BASE + map_id * 10_000 + slot
        out.append(Cache(uid, map_id, template, level, x, y, born, born + timedelta(seconds=period)))
    return out


def at(caches: list[Cache], x: int, y: int) -> Cache | None:
    return next((c for c in caches if (c.x, c.y) == (x, y)), None)


@cache
def _guards(templates: GameTemplates) -> list[tuple[int, int]]:
    return [
        (int(p["Level"]), int(p["TemplateId"]))
        for p in templates.rows("PawnTempInfos")
        if GUARD_FIRST <= int(p["TemplateId"]) <= GUARD_LAST
    ]


def guard(templates: GameTemplates, level: int) -> int:
    """(dedução) o 1º ``PawnTempInfos`` 60xx de nível = baú + 2: 13 -> 6011, 14 -> 6013, 15 -> 6014 (os três vistos);
    sem um desse nível, o de nível mais perto abaixo."""
    pawns = _guards(templates)
    want = level + 2
    below = [p for p in pawns if p[0] <= want] or pawns
    top = max(lv for lv, _ in below)
    return min(t for lv, t in below if lv == top)


def cache_msg(templates: GameTemplates, c: Cache, now: datetime, state: int = CACHE_ALIVE) -> pb.WildLandMsg:
    """Como no 4129/140 do oficial (#1938): ``refreshTime`` = ms até o fim da vida, 3 guardas com ``ownPawns`` 1."""
    msg = pb.WildLandMsg(
        id=c.id,
        mapId=c.map_id,
        posX=c.x,
        posY=c.y,
        templateId=c.template_id,
        type=CACHE_TYPE,
        occupyPlayerId=0,
        level=c.level,
        refreshTime=max(0, int((c.ends - now).total_seconds() * 1000)),
        state=state,
        createDate=game_date(c.born),
        fightCapaity=0,
        bossType=0,
        size=0,
    )
    pawn = guard(templates, c.level)
    for i in range(len(GUARD_LIVINGS)):
        msg.armyPawn.add(id=c.id + i * 200_000_000, armyId=c.id, tempateId=pawn, ownPawns=1)  # int32
    return msg


def battle(snap: PlayerSnapshot, templates: GameTemplates, c: Cache) -> dict[str, object]:
    """Spec da luta (#574): as tropas e o herói do jogador como na mina; os 3 guardas com a vida de um soldado."""
    soldiers, pawn_tpl = oc.army_soldiers(snap, templates)
    pawn = guard(templates, c.level)
    row = templates.get("PawnTempInfos", pawn) or {}
    hp = max(1, int(row.get("Live") or 100) // 100)
    skills = [int(s) for s in (row.get("DefaultSkill", ""), row.get("HighSkill", "")) if s]
    for living, pos in GUARD_LIVINGS:
        soldiers.append({"livingId": living, "tempId": pawn, "type": 1, "side": 2, "pos": pos, "initHp": hp,
                         "hp": hp, "qteTime": 0, "castTime": 6000, "skillId": skills})  # fmt: skip
    return {
        "battleType": BATTLE_TYPE,
        "mapTempId": c.map_id,
        "attackModel": 2,
        "battleScene": SCENE,
        "soldiers": soldiers,
        "heroes": [],
        "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
    }


def loot(
    world: World, templates: GameTemplates, snap: PlayerSnapshot, c: Cache, rng: random.Random
) -> list[tuple[int, int]]:
    """Um item. TODO(inventado): pedra da sorte ``Lvl. ceil(nível / 5)`` (13 -> Lvl. 3, #661) ou um equipamento da
    classe do jogador (Elders Robe, Job 3, ``NeedGrades`` 15, ``Profile`` 2, a um mago num baú 13: #1792), com
    ``NeedGrades`` de nível - ``gear_below`` a nível + ``gear_above``; pesos em ``settings``."""
    conf = settings(world)["loot"]
    stone = LUCK_STONE + min(LUCK_STONE_TOP, max(1, math.ceil(c.level / 5)))
    job = str(job_type(snap.character.job))
    gear = [
        int(r["TemplateId"])
        for r in templates.find("ItemTempInfos", MasterType=GEAR, Job=job, Profile=str(conf["gear_profile"]))
        if c.level - int(conf["gear_below"]) <= int(r.get("NeedGrades") or 0) <= c.level + int(conf["gear_above"])
    ]
    if gear and rng.random() * (conf["stone_weight"] + conf["gear_weight"]) >= conf["stone_weight"]:
        return [(rng.choice(gear), 1)]
    return [(stone, 1)]
