"""Monstros dos Wilds (``WildLandMsg`` type 21) nos mapas compartilhados: o relógio, o sorteio, a luta, os
abates e a névoa.

Relógio (visto): o 4938 da captura inglesa #526 (instância do castelo, 5449 s às 01:29:12 UTC) cai às 20:00
do Pacífico. Só turco (transfer #8/#10 no mapa 2 e cevre #3/#9/#43/#44): o mesmo instante em mapas diferentes,
e o monstro da transfer #14 nasceu às 20:00:50. As horas são as do ``ConfigInfos
WorldMapFreshTime`` (0,8,10,...,22) no fuso do jogo, como diz o help do cliente: "Monsters will reset every
2 hours from 08:00 to 24:00" (language helpContent), "in random positions".

Os monstros de um mapa saem de um sorteio com semente (mapa, ciclo): todo jogador vê os mesmos, e um
restart no meio do ciclo não muda nada, sem tabela de estado. Quantos de cada ``bossType`` vem do catálogo
(``world_monster_counts``); o template é sorteado entre os ``MapPhysicsTempInfos`` ``MasterType`` 21 do tipo
(``Property1``), sem regra de nível por mapa (só turco: o mapa 2 tem monstros de nível 20 a 80 na transfer).

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
from .npc_castles import tile_taken

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
BATTLE_TYPE, SCENE = 3841, 5  # (visto) oficial_20261023-171155-1 #6920 (BattleType.WORLD_MAP_NPC), 4103 #6949
# (visto) #6920, #7228, #7422: o normal vem em pilhas de um soldado (2 até o nível 49 nas pos 2 e 8; 4 do 50 em diante
# nas 3, 9, 2 e 8; dedução: a fronteira entre o 40 e o 50 vistos), a elite e o chefe são o herói NPC na pos 5;
# os inimigos pegam os primeiros livingIds e o herói do jogador o seguinte, sem tropa
STACK_POS = {2: (2, 8), 4: (3, 9, 2, 8)}
BIG_STACK_LEVEL = 50
PAWN_ARMY_BASE, PAWN_BASE = 1_300_000_000, 1_301_000_000  # ids das pilhas no 4129 (o oficial usa 13007xxxxx/13011xxxxx)


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
            while tile_taken(world, templates, map_id, x, y):  # mina ou castelo NPC
                x, y = rng.randrange(EDGE, size[0] - EDGE), rng.randrange(EDGE, size[1] - EDGE)
            uid = ID_BASE + map_id * 10_000 + len(out)
            out.append(Monster(uid, map_id, int(row["TemplateId"]), boss_type, x, y, born))
    return out


def stacks(templates: GameTemplates, m: Monster) -> int:
    """Quantas pilhas de um soldado o monstro normal tem (0 na elite e no chefe)."""
    return 0 if m.boss_type != 1 else 4 if level(templates, m) >= BIG_STACK_LEVEL else 2


def monster_msg(
    world: World, templates: GameTemplates, m: Monster, state: int = MONSTER_ALIVE, army_id: int = 0
) -> pb.WildLandMsg:
    """(visto) oficial_20261023-171155-1 #6919, #6954, #7420: ``refreshTime`` 0, ``size`` = ``Property2`` (10; 12 nos
    chefes), ``createDate`` = começo do ciclo, um ``armyPawn`` por pilha do normal (``ownPawns`` 1; elite e chefe sem
    nenhum) e, em luta, ``curArmyId`` = o exército de quem ataca. ``fightCapaity`` do ``world_monsters``."""
    row = templates.get("MapPhysicsTempInfos", m.template_id) or {}
    unit = world.monsters.get(m.template_id)
    army, pawn_id = PAWN_ARMY_BASE + m.id - ID_BASE, unit.pawn_id if unit is not None else 0
    pawns = [
        pb.ArmyPawnInfoMsg(id=PAWN_BASE + (m.id - ID_BASE) * 4 + i, armyId=army, tempateId=pawn_id, ownPawns=1)
        for i in range(stacks(templates, m) if pawn_id else 0)
    ]
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
        armyPawn=pawns,
        curArmyId=[army_id] if army_id and state == MONSTER_FIGHTING else [],
        fightCapaity=unit.fight_capacity if unit is not None else 0,
        bossType=m.boss_type,
        size=int(row.get("Property2") or 0),
    )


@dataclass
class Wilds:
    """O que vive só no processo: a névoa de cada mapa (20 s) e os monstros em luta (state 4). A luta é
    guardada com o ciclo (o id se repete) e só conta enquanto roda: a de uma sessão que caiu se desfaz sozinha."""

    fog: dict[int, datetime] = field(default_factory=dict)  # mapa -> fim da Divine Light
    fighting: dict[tuple[int, int, datetime], Battle] = field(default_factory=dict)  # (mapa, id, ciclo)
    # castelo NPC vencido -> fim da proteção (118); (0, id) no castelo do mundo, (jogador, id) no robô da instância.
    # shortcut: só em memória (2 h), um restart tira a proteção; gravar se a proteção ficar longa
    shields: dict[tuple[int, int], datetime] = field(default_factory=dict)

    def shield(self, key: tuple[int, int], now: datetime, seconds: int) -> None:
        self.shields[key] = now + timedelta(seconds=seconds)

    def shield_left(self, key: tuple[int, int], now: datetime) -> int:
        """Segundos de proteção que sobram no castelo, ou 0."""
        until = self.shields.get(key)
        return math.ceil((until - now).total_seconds()) if until is not None and now < until else 0

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
    """Spec da luta (visto: oficial_20261023-171155-1 #6920, #7228, #7422): battleType 3841 no mapa, só o herói do
    jogador (sem tropa: o exército não perde soldado nem ganha Daru) na fileira dele (pos 3 com ``fightPos`` 3); o
    normal em pilhas de um soldado com ``Live`` / 100 de vida (350 do 6992), a elite e o chefe como herói NPC com a
    vida do ``GameHeroTemp`` (4.000.000 do 2997) e ``fightCapacity`` 0. None sem unidade no catálogo."""
    unit = world.monsters.get(m.template_id)
    if unit is None or not (unit.pawn_id or unit.hero_id) or snap.leader is None:
        return None
    soldiers: list[dict[str, object]] = []
    heroes: list[dict[str, object]] = []
    if unit.pawn_id:
        row = templates.get("PawnTempInfos", unit.pawn_id) or {}
        hp = max(1, int(row.get("Live") or 100) // 100)
        for i, pos in enumerate(STACK_POS[stacks(templates, m)]):
            soldiers.append({"livingId": i + 1, "side": 2, "pos": pos, "tempId": unit.pawn_id, "type": 1,
                             "initHp": hp, "hp": hp, "qteTime": 0, "castTime": 6000})  # fmt: skip
    else:
        row = templates.get("GameHeroTemp", unit.hero_id) or {}
        hp = max(1, int(row.get("Live") or 1))
        heroes.append(npc_hero(livingId=1, side=2, pos=5, tempId=unit.hero_id, nickName=row.get("TemplateName", ""),
                               grade=int(row.get("Grades") or 0), maxHp=hp, initHp=hp, hp=hp,
                               fightCapacity=0))  # fmt: skip
    return {
        "battleType": BATTLE_TYPE,
        "mapTempId": m.map_id,
        "attackModel": 2,
        "battleScene": SCENE,
        "soldiers": soldiers,
        "heroes": heroes,
        "player": {"livingId": len(soldiers) + len(heroes) + 1, "pos": oc.column(snap.leader.fight_pos) or 1,
                   "pawnTempId": 0},
    }  # fmt: skip
