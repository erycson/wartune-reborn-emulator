"""Estado de eventos do personagem (``EventState``) e atividades do operador (``data/events.json``).

Toda marca/contador por personagem vira uma linha ``EventState`` com chave única: assinatura,
login acumulado, atividade diária, pacotes resgatados... ``daily`` zera pelo dia (UTC, o mesmo
relógio que vai para o cliente no ``sysCurtime``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..domain.models import EventState, PlayerSnapshot
from ..templates.repository import GameTemplates

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def parse_time(text: str) -> datetime:
    return datetime.strptime(text, TIME_FMT).replace(tzinfo=UTC)


def state(snap: PlayerSnapshot, key: str, now: datetime) -> EventState:
    """A linha ``key`` do personagem; cria (sem gravar) se não existir."""
    st = next((e for e in snap.events if e.key == key), None)
    if st is None:
        st = EventState(snap.character.id or 0, key, now)
        snap.events.append(st)
    return st


def peek(snap: PlayerSnapshot, key: str) -> EventState | None:
    return next((e for e in snap.events if e.key == key), None)


def daily(snap: PlayerSnapshot, key: str, now: datetime) -> EventState:
    """Como ``state``, mas zera ``value``/``text`` se a última mudança foi em outro dia."""
    st = state(snap, key, now)
    if st.updated_at.date() != now.date():
        st.value, st.text, st.updated_at = 0, "", now
    return st


def config(templates: GameTemplates, name: str, default: str = "") -> str:
    """``ConfigInfos.ConfigValue`` de ``name``."""
    row = templates.get("ConfigInfos", name, key="ConfigName")
    return row["ConfigValue"] if row else default


@dataclass(frozen=True, slots=True)
class Package:
    package_id: str
    order: int
    condition: tuple[int, int]  # (conditionId, conditionValue)
    items: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class Active:
    active_id: str
    active_type: int
    title: str
    detail: str
    condition_detail: str
    getway: int
    order: int
    begin: datetime
    end: datetime
    packages: tuple[Package, ...]


@dataclass(frozen=True, slots=True)
class EventCatalog:
    """Definições do operador. ``data_stamp`` sobe quando o arquivo muda (cache do cliente)."""

    data_stamp: int = 0
    actives: tuple[Active, ...] = ()

    @classmethod
    def load(cls, path: Path) -> EventCatalog:
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        actives = tuple(
            Active(
                a["activeId"],
                int(a["activeType"]),
                a.get("title", ""),
                a.get("detail", ""),
                a.get("conditionDetail", ""),
                int(a.get("getway", 3)),
                int(a.get("order", 1)),
                parse_time(a["beginDate"]),
                parse_time(a["endDate"]),
                tuple(
                    Package(
                        p["packageId"],
                        int(p.get("order", 1)),
                        (int(p["condition"][0]), int(p["condition"][1])),
                        tuple((int(t), int(n)) for t, n in p["items"]),
                    )
                    for p in a["packages"]
                ),
            )
            for a in data.get("actives", [])
        )
        return cls(int(data.get("dataStamp", 1)), actives)

    def active(self, active_id: str) -> Active | None:
        return next((a for a in self.actives if a.active_id == active_id), None)

    def running(self, now: datetime) -> list[Active]:
        return [a for a in self.actives if a.begin <= now <= a.end]
