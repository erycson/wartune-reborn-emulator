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


@dataclass(frozen=True)
class World:
    mines: tuple[Mine, ...] = ()
    mine_guards: Mapping[int, int] = field(default_factory=lambda: MappingProxyType({}))  # nível -> PawnTempInfos
    robots: tuple[RobotCastle, ...] = ()
    robot_names: tuple[RobotName, ...] = ()
    # mapa -> {bossType: quantos por ciclo}; template -> fightCapaity
    monster_counts: Mapping[int, Mapping[int, int]] = field(default_factory=lambda: MappingProxyType({}))
    monster_power: Mapping[int, int] = field(default_factory=lambda: MappingProxyType({}))

    def mines_on(self, map_id: int) -> list[Mine]:
        return [m for m in self.mines if m.map_id == map_id]

    def mine(self, mine_id: int) -> Mine | None:
        return next((m for m in self.mines if m.id == mine_id), None)

    def robots_on(self, map_id: int) -> list[RobotCastle]:
        return [r for r in self.robots if r.map_id == map_id]
