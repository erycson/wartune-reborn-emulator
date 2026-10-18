"""Catálogo do mundo: o que existe em cada mapa (minas, castelos-robô, quantos monstros). Vem do banco
(``persistence/world_store.py``), carregado uma vez ao subir; o estado de cada jogador fica no snapshot."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Mine:
    """Mina de ouro (``WildLandMsg`` type 20). O nível é sorteado a cada ciclo entre ``min_level`` e
    ``max_level``."""

    id: int
    map_id: int
    x: int
    y: int
    min_level: int
    max_level: int

    @property
    def levels(self) -> range:
        return range(self.min_level, self.max_level + 1)


@dataclass(frozen=True, slots=True)
class RobotCastle:
    id: int
    map_id: int
    x: int
    y: int
    grade: int


@dataclass(frozen=True, slots=True)
class RobotName:
    name: str
    prefix: str
    suffix: str

    def __str__(self) -> str:
        return f"{self.prefix}{self.name}{self.suffix}"


@dataclass(frozen=True, slots=True)
class MonsterTemplate:
    """Monstro dos Wilds (``MapPhysicsTempInfos`` ``MasterType`` 21): a unidade da luta (pawn do normal ou herói
    da elite e do chefe) e o ``fightCapaity`` do 4129."""

    template_id: int
    pawn_id: int
    hero_id: int
    fight_capacity: int


@dataclass(frozen=True, slots=True)
class MonsterDrop:
    """Uma linha da tabela de queda do baú dos Wilds: para o ``boss_type`` entre ``min_level`` e ``max_level``
    (nível do monstro), ``template_id`` (``ItemTempInfos``, ou moeda < 0) cai com ``chance`` (0 a 1), em
    ``min_count`` a ``max_count``. Cada linha é sorteada sozinha."""

    boss_type: int
    min_level: int
    max_level: int
    template_id: int
    chance: float
    min_count: int
    max_count: int


@dataclass(frozen=True, slots=True)
class WorldBoss:
    """Config de um chefe do mundo (``world_bosses``, campanha ``Types=1``): herói da luta, desenho e nó no
    mapa, vida e como ela muda de uma janela para a outra, a luta e os prêmios por golpe e do último golpe."""

    campaign_id: int
    hero_id: int
    son_type: int
    node_x: int
    node_y: int
    start_x: int
    start_y: int
    base_hp: int
    min_hp: int
    fast_seconds: int  # morto em menos que isso: a vida da próxima janela cresce grow_pct
    grow_pct: int
    shrink_pct: int  # não morreu na janela: cai shrink_pct (até min_hp)
    kill_turn: int  # golpe do chefe que mata o lado do jogador (os anteriores não matam)
    revive_seconds: int
    damage_per_gold: int  # ouro e daru por luta = dano // isto
    battle_cap: int
    last_hit_gold: int
    last_hit_daru: int


@dataclass(frozen=True, slots=True)
class WorldBossReward:
    """Prêmio do fim da janela (``world_boss_rewards``): ``rank`` = posição de rank_from a rank_to no dano da
    classe; ``share`` = fez pelo menos essa fração do dano total (vale o maior degrau alcançado)."""

    kind: str
    rank_from: int
    rank_to: int
    share: float
    gold: int
    daru: int


@dataclass(frozen=True)
class World:
    mines: tuple[Mine, ...] = ()
    mine_guards: Mapping[int, int] = field(default_factory=lambda: MappingProxyType({}))  # nível -> PawnTempInfos
    robots: tuple[RobotCastle, ...] = ()
    robot_names: tuple[RobotName, ...] = ()
    # mapa -> {bossType: quantos por ciclo}
    monster_counts: Mapping[int, Mapping[int, int]] = field(default_factory=lambda: MappingProxyType({}))
    monsters: Mapping[int, MonsterTemplate] = field(default_factory=lambda: MappingProxyType({}))
    monster_drops: tuple[MonsterDrop, ...] = ()
    world_bosses: Mapping[int, WorldBoss] = field(default_factory=lambda: MappingProxyType({}))  # campanha ->
    world_boss_rewards: tuple[WorldBossReward, ...] = ()

    def mines_on(self, map_id: int) -> list[Mine]:
        return [m for m in self.mines if m.map_id == map_id]

    def mine(self, mine_id: int) -> Mine | None:
        return next((m for m in self.mines if m.id == mine_id), None)

    def robots_on(self, map_id: int) -> list[RobotCastle]:
        return [r for r in self.robots if r.map_id == map_id]
