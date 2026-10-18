"""Monstros dos Wilds (``WildLandMsg`` type 21) nos mapas compartilhados: o relógio, o sorteio, a luta, os
abates e a névoa.

Relógio (visto): transfer #8/#10 (mapa 2, 4828 s às 17:39:31 UTC) e cevre #3/#9/#43/#44 (instância do
castelo, 5775 s às 17:23:44 UTC) caem no mesmo instante, 2026-05-21 19:00:00 UTC (22:00 no fuso do jogo),
em mapas diferentes; e o monstro da transfer #14 nasceu às 20:00:50. As horas são as do ``ConfigInfos
WorldMapFreshTime`` (0,8,10,...,22) no fuso do jogo, como diz o help do cliente: "Monsters will reset every
2 hours from 08:00 to 24:00" (language helpContent), "in random positions".

Os monstros de um mapa saem de um sorteio com semente (mapa, ciclo): todo jogador vê os mesmos, e um
restart no meio do ciclo não muda nada, sem tabela de estado. Quantos de cada ``bossType`` vem do catálogo
(``world_monster_counts``); o template é sorteado entre os ``MapPhysicsTempInfos`` ``MasterType`` 21 do tipo
(``Property1``), sem regra de nível por mapa (o mapa 2 tem monstros de nível 20 a 80 na transfer).

O que muda no ciclo fica fora do sorteio: o abate vai para o banco (``wild_monster_kills``, chave com o
começo do ciclo, porque o id se repete) e quem está em luta e a névoa ficam em ``Wilds``, só no processo.

Help do cliente (language ``map.outercity.view.helpFrame.helpContent``): o limite do dia é de prêmio ("killing
a certain number of monsters gives rich rewards", reset às 5h), não de ataque; monstro 15 níveis abaixo do
jogador não dá prêmio nem gasta o limite; elite e BOSS são para equipe; a Divine Light de qualquer um limpa
a névoa. ponytail: prêmio 0 (nenhuma fonte; ver docs/cidade-externa.md) e luta sozinho (o state 4 deixa
entrar, sem captura de como). Posição: qualquer tile do mapa a ``EDGE`` da borda, sem checar o terreno
(o .maps não traz a área andável).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from ..domain import gameday
from ..domain.models import Character, PlayerSnapshot
from ..domain.world import World
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import outer_city as oc
from .arena import npc_hero
from .events import config
from .mines import game_date

if TYPE_CHECKING:
    from .battle import Battle

MONSTER_TYPE = 21  # WildLandMsg.type e MapPhysicsTempInfos.MasterType
MONSTER_ALIVE, MONSTER_FIGHTING, MONSTER_GONE = 1, 4, 0  # WildLandMsg.state e BossMsg.type (cliente)
CHIEF = 3  # bossType dos chefes (os do painel "Current map BOSS info")
ID_BASE = 1_000_000_000  # WildLandMsg.id é int32 e não pode bater com minas (85xxxx) nem terras do oficial
EDGE = 20  # tiles
FOG_SON_TYPE = "316"  # Divine Light (ItemTempInfos 2131055)
FOG_SECONDS = 20  # só a descrição do item diz: "disperse the Wilds’ dark fog for 20 seconds"
NO_REWARD_GAP = 15  # help: monstro 15 níveis abaixo do jogador não dá prêmio nem conta
KILL_FIELDS = {1: "kills_normal", 2: "kills_elite", 3: "kills_boss"}  # bossType -> Character
BATTLE_TYPE = 2  # NPC_WILDLAND_BATTLE (cliente)
ENEMY = {"livingId": 4, "side": 2, "pos": 5}  # como o guarda da mina (replay #718)


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


def monster_msg(world: World, templates: GameTemplates, m: Monster, state: int = MONSTER_ALIVE) -> pb.WildLandMsg:
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
        state=state,
        createDate=game_date(m.born),
        fightCapaity=unit.fight_capacity if (unit := world.monsters.get(m.template_id)) else 0,
        bossType=m.boss_type,
        size=int(row.get("Property2") or 0),
    )


@dataclass
class Wilds:
    """O que vive só no processo: a névoa de cada mapa (20 s) e os monstros em luta (state 4). A luta é
    guardada com o ciclo (o id se repete) e só conta enquanto roda: a de uma sessão que caiu se desfaz sozinha."""

    fog: dict[int, datetime] = field(default_factory=dict)  # mapa -> fim da Divine Light
    fighting: dict[tuple[int, int, datetime], Battle] = field(default_factory=dict)  # (mapa, id, ciclo)

    def clear_fog(self, map_id: int, now: datetime) -> None:
        self.fog[map_id] = now + timedelta(seconds=FOG_SECONDS)

    def fog_left(self, map_id: int, now: datetime) -> int:
        """Segundos sem névoa que sobram no mapa, ou 0."""
        until = self.fog.get(map_id)
        return math.ceil((until - now).total_seconds()) if until is not None and now < until else 0

    def state(self, m: Monster, killed: set[int]) -> int:
        if m.id in killed:
            return MONSTER_GONE
        fight = self.fighting.get((m.map_id, m.id, m.born))
        return MONSTER_FIGHTING if fight is not None and fight.running else MONSTER_ALIVE


def at(monsters: list[Monster], x: int, y: int) -> Monster | None:
    """O monstro no tile clicado (5160 manda o tile do monstro, como nas minas)."""
    return next((m for m in monsters if (m.x, m.y) == (x, y)), None)


def level(templates: GameTemplates, m: Monster) -> int:
    return int((templates.get("MapPhysicsTempInfos", m.template_id) or {}).get("Grades") or 0)


def kill_limits(templates: GameTemplates) -> list[int]:
    """Abates do dia que dão prêmio, por bossType 1, 2 e 3 (``ConfigInfos WorldMapKill`` 5,3,1)."""
    limits = [int(n) for n in config(templates, "WorldMapKill", "5,3,1").split(",") if n.strip()]
    return (limits + [0, 0, 0])[:3]


def kills(c: Character) -> list[int]:
    return [getattr(c, KILL_FIELDS[t]) for t in (1, 2, 3)]


def count_kill(c: Character, templates: GameTemplates, m: Monster) -> bool:
    """Conta o abate no limite do dia, se ainda cabe e o monstro não está 15 níveis abaixo. True se contou."""
    if c.grades - level(templates, m) >= NO_REWARD_GAP:
        return False
    name = KILL_FIELDS[m.boss_type]
    if getattr(c, name) >= kill_limits(templates)[m.boss_type - 1]:
        return False
    setattr(c, name, getattr(c, name) + 1)
    return True


def loot(world: World, boss_type: int, grade: int, rng: random.Random) -> list[tuple[int, int]]:
    """O que sai do baú: cada linha de ``world_monster_drops`` do tipo e da faixa de nível, sorteada sozinha."""
    return [
        (d.template_id, rng.randint(d.min_count, d.max_count))
        for d in world.monster_drops
        if d.boss_type == boss_type and d.min_level <= grade <= d.max_level and rng.random() < d.chance
    ]


def battle(snap: PlayerSnapshot, world: World, templates: GameTemplates, m: Monster) -> dict[str, object] | None:
    """Spec da luta (battleType 2): as tropas e o herói do jogador como na mina; o normal é uma pilha do pawn
    dele, a elite e o chefe são o herói NPC com a vida do template. (dedução) posições, ``mapTempId`` = o mapa e
    a vida do normal (a de um soldado, como o guarda: o 4129 do monstro não traz ``armyPawn``). None sem
    unidade no catálogo."""
    unit = world.monsters.get(m.template_id)
    if unit is None or not (unit.pawn_id or unit.hero_id):
        return None
    soldiers, pawn_tpl = oc.army_soldiers(snap, templates)
    heroes: list[dict[str, object]] = []
    if unit.pawn_id:
        row = templates.get("PawnTempInfos", unit.pawn_id) or {}
        hp = max(1, int(row.get("Live") or 100) // 100)
        soldiers.append({**ENEMY, "tempId": unit.pawn_id, "type": 1, "initHp": hp, "hp": hp, "qteTime": 0,
                         "castTime": 6000})  # fmt: skip
    else:
        row = templates.get("GameHeroTemp", unit.hero_id) or {}
        hp = max(1, int(row.get("Live") or 1))
        heroes.append(npc_hero(**ENEMY, tempId=unit.hero_id, nickName=row.get("TemplateName", ""),
                               grade=int(row.get("Grades") or 0), maxHp=hp, initHp=hp, hp=hp,
                               fightCapacity=unit.fight_capacity))  # fmt: skip
    return {
        "battleType": BATTLE_TYPE,
        "mapTempId": m.map_id,
        "attackModel": 2,
        "battleScene": 4,
        "soldiers": soldiers,
        "heroes": heroes,
        "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
        "lethal": True,  # (internet) dá para perder: vídeo https://www.youtube.com/watch?v=Cn6cQpeImEM
    }
