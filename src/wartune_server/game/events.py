"""Estado de eventos do personagem (``EventState``) e atividades do operador (``data/events.json``).

Toda marca/contador por personagem vira uma linha ``EventState`` com chave única: assinatura,
login acumulado, atividade diária, pacotes resgatados... ``daily`` zera pelo dia (UTC, o mesmo
relógio que vai para o cliente no ``sysCurtime``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..domain import gameday
from ..domain.models import EventState, PlayerSnapshot
from ..domain.world import ExpRate, World
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


def contract_end(snap: PlayerSnapshot, cid: int) -> datetime | None:
    """Fim do contrato do rei ``cid`` (KingContracts), guardado em ``king:{cid}``; ``None`` se nunca comprado."""
    st = peek(snap, f"king:{cid}")
    return parse_time(st.text) if st and st.text else None


def has_contract(snap: PlayerSnapshot, cid: int, now: datetime) -> bool:
    end = contract_end(snap, cid)
    return end is not None and end > now


def daily(snap: PlayerSnapshot, key: str, now: datetime) -> EventState:
    """Como ``state``, mas zera ``value``/``text`` se a última mudança foi em outro dia."""
    st = state(snap, key, now)
    if not gameday.same_day(st.updated_at, now):
        st.value, st.text, st.updated_at = 0, "", now
    return st


def rate_window(r: ExpRate) -> tuple[datetime, datetime]:
    """Início e fim do evento de EXP (datas na hora do jogo). ``begin_time``/``end_time`` = segundos somados ao
    dia (0/86399 = o dia inteiro, como o PlayerBufferManager conta).

    ponytail: janela diária (outros ``begin_time``/``end_time``) vira um intervalo só; o oficial só mostrou 0/86399.
    """
    local = (datetime.strptime(t, TIME_FMT).replace(tzinfo=gameday.GAME_TZ) for t in (r.begin_day, r.end_day))
    begin, end = local
    return begin + timedelta(seconds=r.begin_time), end + timedelta(seconds=r.end_time)


def running_rates(world: World, now: datetime) -> list[ExpRate]:
    return [r for r in world.exp_rates if rate_window(r)[0] <= now <= rate_window(r)[1]]


def config(templates: GameTemplates, name: str, default: str = "") -> str:
    """``ConfigInfos.ConfigValue`` de ``name``."""
    row = templates.get("ConfigInfos", name, key="ConfigName")
    return row["ConfigValue"] if row else default


COST = 4  # SumActiveItemInfoMsg.templateType do custo da troca (tipo 10): só aparece, não é dado (tutorial_en #62)


@dataclass(frozen=True, slots=True)
class Package:
    package_id: str
    order: int
    # (conditionId, conditionValue, conditionBak..Bak4); a troca usa Bak = o item pedido (FunnyHelper.mutiMaxNum)
    condition: tuple[int, ...]
    entries: tuple[tuple[int, int, int], ...]  # (templateId, count, templateType) na ordem do oficial
    limit: int = 0  # trocas por jogador (getCount do 4476); 0 = sem limite

    @property
    def items(self) -> tuple[tuple[int, int], ...]:
        """O que o pacote dá (sem o custo da troca)."""
        return tuple((t, n) for t, n, kind in self.entries if kind != COST)


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
                        tuple(int(c) for c in p["condition"]),
                        tuple((int(e[0]), int(e[1]), int(e[2]) if len(e) > 2 else 1) for e in p["items"]),
                        int(p.get("limit", 0)),
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

    def listed(self, now: datetime) -> list[Active]:
        """As que o painel mostra: as que ainda não acabaram, também as que vão começar (tutorial_en #60 às 10-18
        manda as de 10-22 a 10-31; o cliente descarta só ``stopTime`` passado, FunnyManager.__funnyTemHandler)."""
        return [a for a in self.actives if now <= a.end]


# activeType que o servidor conta com ``count`` -> se o contador zera no dia (FunnyType do cliente; "today" no texto
# do progresso, funny.FunnyRightView.processNN, = diário; sem "today" conta o período todo, *dedução*)
ALCHEMY, REFINE_SOUL, CHALLENGE, FATE_TURN, FATE_EAT, PET_CHALLENGE = 21, 22, 26, 108, 109, 110
SPEND = 1  # "Spending Bonus": Balens gastos (condição 9), "during the event" = o período (um dia na inglesa #60)
COUNTED = {ALCHEMY: False, REFINE_SOUL: False, CHALLENGE: False, FATE_TURN: True, FATE_EAT: True, PET_CHALLENGE: True}
COUNTED |= {SPEND: False}


def count(snap: PlayerSnapshot, catalog: EventCatalog, active_type: int, now: datetime, n: int = 1) -> list[EventState]:
    """A ação que as atividades ``active_type`` contam aconteceu ``n`` vezes: soma em cada uma que está correndo.
    Devolve as linhas para quem chama gravar."""
    out = []
    for a in catalog.running(now):
        if a.active_type == active_type:
            key = f"sum:{a.active_id}"
            st = daily(snap, key, now) if COUNTED[active_type] else state(snap, key, now)
            st.value, st.updated_at = st.value + n, now
            out.append(st)
    return out
