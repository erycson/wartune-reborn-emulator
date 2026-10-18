"""Monstros dos Wilds (``WildLandMsg`` type 21) nos mapas compartilhados, o relógio deles e a névoa.

Relógio (visto): transfer #8/#10 (mapa 2, 4828 s às 17:39:31 UTC) e cevre #3/#9/#43/#44 (instância do
castelo, 5775 s às 17:23:44 UTC) caem no mesmo instante, 2026-05-21 19:00:00 UTC (22:00 no fuso do jogo),
em mapas diferentes; e o monstro da transfer #14 nasceu às 20:00:50. As horas são as do ``ConfigInfos
WorldMapFreshTime`` (0,8,10,...,22) no fuso do jogo, como diz o help do cliente: "Monsters will reset every
2 hours from 08:00 to 24:00" (language helpContent), "in random positions".

Os monstros de um mapa saem de um sorteio com semente (mapa, ciclo): todo jogador vê os mesmos, e um
restart no meio do ciclo não muda nada, sem tabela de estado. Quantos de cada ``bossType`` vem do catálogo
(``world_monster_counts``); o template é sorteado entre os ``MapPhysicsTempInfos`` ``MasterType`` 21 do tipo
(``Property1``), sem regra de nível por mapa (o mapa 2 tem monstros de nível 20 a 80 na transfer).

ponytail: sem luta não há abate, então nenhum monstro sai do mapa no meio do ciclo (state 4 e 0 do 140);
quando houver luta, os abates do ciclo vão para o banco e saem do sorteio. Posição: qualquer tile do mapa
a ``EDGE`` da borda, sem checar o terreno (o .maps não traz a área andável).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..domain import gameday
from ..domain.models import Character
from ..domain.world import World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import outer_city as oc
from .events import config
from .mines import game_date

MONSTER_TYPE = 21  # WildLandMsg.type e MapPhysicsTempInfos.MasterType
MONSTER_ALIVE = 1  # WildLandMsg.state visto
CHIEF = 3  # bossType dos chefes (os do painel "Current map BOSS info")
ID_BASE = 1_000_000_000  # WildLandMsg.id é int32 e não pode bater com minas (85xxxx) nem terras do oficial
EDGE = 20  # tiles
FOG_SON_TYPE = "316"  # Divine Light (ItemTempInfos 2131055)
FOG_SECONDS = 20  # só a descrição do item diz: "20 saniyeliğine"


@dataclass(frozen=True, slots=True)
class Monster:
    id: int
    map_id: int
    template_id: int
    boss_type: int
    x: int
    y: int
    born: datetime


def _marks(templates: GameTemplates, now: datetime) -> list[datetime]:
    """Horas de refresh de ontem, hoje e amanhã (``WorldMapFreshTime``), no fuso do jogo."""
    hours = sorted({int(h) for h in config(templates, "WorldMapFreshTime", "0").split(",") if h.strip()})
    day = gameday.local(now).replace(hour=0, minute=0, second=0, microsecond=0)
    return [day + timedelta(days=d, hours=h) for d in (-1, 0, 1) for h in hours or [0]]


def cycle_start(templates: GameTemplates, now: datetime) -> datetime:
    """Começo do ciclo em que ``now`` está (o último refresh já passado)."""
    return max(m for m in _marks(templates, now) if m <= now)


def refresh_left(templates: GameTemplates, now: datetime) -> int:
    """Segundos até o próximo refresh. Nunca 0: com 0 o cliente (``coolDownBossUpdate``) pede o 9525 de novo,
    e a cada segundo se a resposta voltar 0."""
    nxt = min(m for m in _marks(templates, now) if m > now)
    return max(1, int((nxt - now).total_seconds()))


def _pool(templates: GameTemplates) -> dict[int, list[Row]]:
    pool: dict[int, list[Row]] = {}
    for row in templates.find("MapPhysicsTempInfos", MasterType=str(MONSTER_TYPE)):
        pool.setdefault(int(row.get("Property1") or 0), []).append(row)
    return pool


def on_map(world: World, templates: GameTemplates, map_id: int, now: datetime) -> list[Monster]:
    """Os monstros do ciclo atual no mapa (nenhum fora dos mapas do catálogo, como a instância do castelo)."""
    counts, size = world.monster_counts.get(map_id), oc.map_size(templates, map_id)
    if not counts or size is None or min(size) <= 2 * EDGE:
        return []
    born = cycle_start(templates, now)
    rng = random.Random(f"{map_id}:{born.isoformat()}")
    pool, out = _pool(templates), list[Monster]()
    for boss_type, count in sorted(counts.items()):
        for _ in range(count if pool.get(boss_type) else 0):
            row = rng.choice(pool[boss_type])
            x, y = rng.randrange(EDGE, size[0] - EDGE), rng.randrange(EDGE, size[1] - EDGE)
            uid = ID_BASE + map_id * 10_000 + len(out)
            out.append(Monster(uid, map_id, int(row["TemplateId"]), boss_type, x, y, born))
    return out


def monster_msg(world: World, templates: GameTemplates, m: Monster) -> pb.WildLandMsg:
    """Como o 210127 da transfer #14: sem ``armyPawn``, ``refreshTime`` 0, ``size`` = ``Property2`` (10; 12 nos
    chefes), ``createDate`` = começo do ciclo. ``fightCapaity``: só o do 210127 foi visto; os outros vão 0."""
    row = templates.get("MapPhysicsTempInfos", m.template_id) or {}
    return pb.WildLandMsg(
        id=m.id,
        mapId=m.map_id,
        posX=m.x,
        posY=m.y,
        templateId=m.template_id,
        type=MONSTER_TYPE,
        occupyPlayerId=0,
        level=int(row.get("Grades") or 0),
        refreshTime=0,
        state=MONSTER_ALIVE,
        createDate=game_date(m.born),
        fightCapaity=world.monster_power.get(m.template_id, 0),
        bossType=m.boss_type,
        size=int(row.get("Property2") or 0),
    )


def fog_left(c: Character, map_id: int, now: datetime) -> int:
    """Segundos sem névoa que sobram no mapa (Divine Light), ou 0."""
    if c.fog_until is None or c.fog_map != map_id or now >= c.fog_until:
        return 0
    return math.ceil((c.fog_until - now).total_seconds())
