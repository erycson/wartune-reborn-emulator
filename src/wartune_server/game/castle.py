"""Regras do castelo sobre o ``PlayerSnapshot``: produção de ouro, armazém, população, filas de
construção e templates de prédio. Quem chama grava as entidades alteradas numa ``save`` só.

Produção: o ouro rende ``goldYield`` por hora (conselho 901 + mina 101 + tecnologia de ouro) até o
teto do armazém (301); ouro ganho por outras fontes pode passar do teto, e aí a produção só para
(captura inglesa #1562: 56724 com teto 10000). O rendimento é acumulado sob demanda (``settle``):
quem gasta ouro chama ``settle`` antes e grava personagem + castelo juntos.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from datetime import datetime, timedelta

from ..domain import gameday
from ..domain.models import Building, BuildOrder, Castle, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import buffs, mines, rules
from .builders import login as b
from .session import GameSession

S_CASTLE_YIELD = 109
COUNCIL, MINE, DEPOT, HOUSE, ACADEMY = 901, 101, 301, 1201, 501
GOLD_TECH = ("13",)  # MasterType das tecnologias de ouro (1304, 2304): EffectTempInfos.Property1 por nível
TECH = ("13", "14")  # MasterType das tecnologias: usam a fila de tecnologia
BASE_GOLD_MAX = 10000  # teto sem armazém (inglês #124, antes de existir o 301)
BUILD, TECH_ORDER, IMPOSE = 1, 2, 3  # OrderInfoMsg.orderType
# (cliente) LevyView: cobrança a partir do 14. (visto) oficial_20261023-171155-1: o 4187 antes do 14 só tem a fila 1, e
# a missão 230 que levou ao 14 mandou o 104 {orderId 2, orderType 3} (#5840)
IMPOSE_GRADE = 14
BUILD_ORDER_LIMIT = 2  # BuildingModel.buildOrderLimit
TRANSFER = 1511
CASTLE_READY = 20000  # noviceProcess logo depois do 8281 (prédios e fila iniciais)


def template(templates: GameTemplates, template_id: int) -> Row | None:
    return templates.get("BuildingTempInfos", template_id)


def grade_of(templates: GameTemplates, building: Building) -> int:
    row = template(templates, building.template_id)
    return int(row["BuildingGrade"]) if row else 0


def by_son_type(snap: PlayerSnapshot, templates: GameTemplates, son_type: int) -> Building | None:
    for building in snap.buildings:
        row = template(templates, building.template_id)
        if row is not None and int(row["SonType"]) == son_type:
            return building
    return None


def first_grade(templates: GameTemplates, son_type: int) -> Row | None:
    """``getMinGradeBuildingTemplete``: o nível 1 do tipo (o que o 8202 constrói)."""
    return next(templates.find("BuildingTempInfos", SonType=son_type, BuildingGrade=1), None)


def missing_requirements(snap: PlayerSnapshot, templates: GameTemplates, target: Row) -> list[str]:
    """``PreTemplateId`` ("50101,90105"): cada pré-requisito precisa existir com nível suficiente."""
    missing = []
    for pre_id in filter(None, target.get("PreTemplateId", "").split(",")):
        pre = template(templates, int(pre_id))
        if pre is None:
            continue
        own = by_son_type(snap, templates, int(pre["SonType"]))
        if own is None or grade_of(templates, own) < int(pre["BuildingGrade"]):
            missing.append(pre_id)
    return missing


def gold_yield(snap: PlayerSnapshot, templates: GameTemplates) -> int:
    total = 0
    for building in snap.buildings:
        row = template(templates, building.template_id)
        if row is None:
            continue
        if int(row["SonType"]) in (COUNCIL, MINE):
            total += int(row["Property1"])
        elif row["MasterType"] in GOLD_TECH:
            effect = templates.get("EffectTempInfos", int(row["Property1"])) or {}
            total += int(effect.get("Property1", 0)) * int(row["BuildingGrade"])
    # a captura inglesa bate exato com prefeitura + minas (#579 120, #591 280, #772 1040, #2744 2280), sem guilda;
    # TODO(inventado): a habilidade "Gold Boost" da guilda ("Gold Production +N%") sobre o total (nenhuma captura)
    total += mines.mine_gold(snap, templates)
    boost = rules.guild_skills(snap.character, templates).get(rules.GUILD_GOLD, 0)
    return total * (100 + boost) // 100


def gold_max(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> int:
    """Teto do armazém (301), + o Gold Expansion Scroll ("Warehouse Capacity +{Grades}%", ``buffs.GOLD_MAX``)."""
    depot = by_son_type(snap, templates, DEPOT)
    row = template(templates, depot.template_id) if depot else None
    return buffs.boost(int(row["Property2"]) if row else BASE_GOLD_MAX, snap, buffs.GOLD_MAX, now)


def pending_gold(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> tuple[int, datetime | None]:
    """Ouro produzido desde ``produced_at`` e o novo marco (guarda a fração de hora que sobrou)."""
    castle, gold = snap.castle, snap.character.gold
    if castle is None or castle.produced_at is None:
        return 0, None
    per_hour, cap = gold_yield(snap, templates), gold_max(snap, templates, now)
    if per_hour <= 0 or gold >= cap or now <= castle.produced_at:
        return 0, max(now, castle.produced_at)
    gain = int(per_hour * (now - castle.produced_at).total_seconds() // 3600)
    if gold + gain >= cap:
        return cap - gold, now
    return gain, castle.produced_at + timedelta(seconds=gain * 3600 / per_hour)


def settle(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> None:
    """Acumula a produção no ouro do personagem (grave personagem e castelo juntos). Passou o refresh de
    12 h das minas: o ouro até o fim do ciclo sai com a taxa delas e o ciclo novo começa (``mines.next_cycle``:
    ``now`` no mapa do castelo, o do mundo num mapa do mundo), sem ocupação (``mines.occupied`` só vale no ciclo
    atual)."""
    if snap.castle is not None:
        snap.castle.mines_at = mines.cycle_start(snap)  # castelo de antes da 0018 fixa o ciclo
        if now >= mines.cycle_end(snap):
            _settle(snap, templates, mines.cycle_end(snap))
            snap.castle.mines_at = mines.next_cycle(snap, now)
    _settle(snap, templates, now)


def _settle(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> None:
    gain, mark = pending_gold(snap, templates, now)
    if snap.castle is not None and mark is not None:
        snap.character.gold += gain
        snap.castle.produced_at = mark


def start_production(snap: PlayerSnapshot, now: datetime) -> None:
    if snap.castle is not None and snap.castle.produced_at is None:
        snap.castle.produced_at = now


def yield_msg(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> pb.CastleYieldMsg:
    gain, _ = pending_gold(snap, templates, now)
    used, top = rules.population(snap, templates, now)
    return pb.CastleYieldMsg(
        goldYield=gold_yield(snap, templates),
        goldTotalCount=snap.character.gold + gain,
        goldMax=gold_max(snap, templates, now),
        curPopulation=used,
        maxPopulation=top,
        crystalsCount=snap.character.crystals,
    )


def castle_yield(s: GameSession) -> None:
    """109: ouro, teto, população e cristais (o cliente atualiza a barra de recursos)."""
    assert s.snapshot is not None
    s.send(S_CASTLE_YIELD, yield_msg(s.snapshot, s.ctx.templates, s.ctx.clock.now()))


def politics_msg(snap: PlayerSnapshot, templates: GameTemplates) -> pb.CastleYieldMsg:
    """152 (conselho): o rendimento dos prédios e uma linha por mina ocupada. Como no inglês (#751,
    #804), ``goldYield`` e ``goldTotalCount`` ficam só com os prédios e ``goldWildLandYield`` em 0."""
    total = gold_yield(snap, templates) - mines.mine_gold(snap, templates)
    msg = pb.CastleYieldMsg(goldYield=total, goldWildLandYield=0, goldTechnology=0, goldWonder=0)
    msg.goldTotalCount = total
    msg.wildYield.extend(mines.mine_yield(snap, templates))
    return msg


def energy_max(templates: GameTemplates) -> int:
    """Teto da energia de teleporte: Property2 do prédio de transferência (1511, id -11 no cliente)."""
    # ponytail: sem o bônus de raça/efeitos do limite (PlayerEffect.getTransferPowerLimitAddition)
    row = first_grade(templates, TRANSFER)
    return int(row["Property2"]) if row else 500


def impose_used(castle: Castle, now: datetime) -> int:
    """Cobranças de ouro (8327) já feitas hoje; o contador zera na virada do dia."""
    if not gameday.same_day(castle.imposed_at, now):
        return 0
    return castle.impose_used


# --- filas ---------------------------------------------------------------------------------------


def orders_of(snap: PlayerSnapshot, order_type: int) -> Iterator[BuildOrder]:
    return (o for o in snap.orders if o.order_type == order_type)


def free_order(snap: PlayerSnapshot, order_type: int, now: datetime) -> BuildOrder | None:
    return next((o for o in orders_of(snap, order_type) if o.remain(now) <= 0), None)


def order_type_for(row: Row) -> int:
    return TECH_ORDER if row["MasterType"] in TECH else BUILD


def new_order(snap: PlayerSnapshot, order_type: int, now: datetime, order_id: int | None = None) -> BuildOrder:
    number = order_id or max((o.order_id for o in snap.orders), default=0) + 1
    order = BuildOrder(snap.character.id or 0, number, order_type, now)
    snap.orders.append(order)
    return order


def quick_cost(remain: int) -> int:
    """(cliente inglês) ``QueueItem`` (clique na fila): 5 diamantes a cada 10 minutos (ou fração) que faltam."""
    return math.ceil(remain / 600) * 5


def order_info(order: BuildOrder, now: datetime) -> pb.OrderInfoMsg:
    return pb.OrderInfoMsg(orderId=order.order_id, orderType=order.order_type, remainTime=order.remain(now))


def order_full(order: BuildOrder, now: datetime) -> pb.OrderInfoMsg:
    """Com dono, início e duração: 4155 (login) e 4187 (8279)."""
    msg = order_info(order, now)
    msg.userId, msg.beginTime, msg.needTime = order.character_id, b.fmt_time(order.begin_at), order.need_time
    return msg


def impose_order(snap: PlayerSnapshot, now: datetime) -> BuildOrder | None:
    """Cria a fila de cobrança (número 2) quem chegou ao ``IMPOSE_GRADE`` e ainda não tem; ``None`` se não criou."""
    if snap.character.grades < IMPOSE_GRADE or next(orders_of(snap, IMPOSE), None) is not None:
        return None
    taken = any(o.order_id == 2 for o in snap.orders)
    return new_order(snap, IMPOSE, now, None if taken else 2)


def order_list(snap: PlayerSnapshot, now: datetime) -> pb.BuildOrderList:
    return pb.BuildOrderList(buildOrder=[order_full(o, now) for o in snap.orders])


# --- carga ---------------------------------------------------------------------------------------


def unlock(snap: PlayerSnapshot, templates: GameTemplates, building: Building) -> list[Building]:
    """``NextTemplateId`` libera outro prédio (academia nível N -> tecnologia nível 0, quartel 2 -> casa).

    Olha todos os níveis até o atual, para completar personagens antigos.
    """
    row = template(templates, building.template_id)
    if row is None:
        return []
    new = []
    for level in templates.find("BuildingTempInfos", SonType=row["SonType"]):
        target = template(templates, int(level.get("NextTemplateId") or 0))
        if target is None or int(level["BuildingGrade"]) > int(row["BuildingGrade"]):
            continue
        if by_son_type(snap, templates, int(target["SonType"])) is None:
            new.append(Building(snap.character.id or 0, int(target["TemplateId"])))
            snap.buildings.append(new[-1])
    return new


def ensure(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> list[object]:
    """No login: filas de tecnologia e de cobrança, e o que já devia ter sido liberado.

    A fila de prédios (1) e a produção nascem no 8281 do tutorial; quem já passou dele (ou
    pulou o tutorial) recebe aqui. Os números seguem o oficial: 1 prédio, 2 cobrança, 3 tecnologia. A de cobrança
    só do ``IMPOSE_GRADE`` em diante (``impose_order`` na subida de nível). (dedução) a de tecnologia nasce no login:
    nenhuma captura mostra quando o oficial a cria.
    """
    changed: list[object] = []
    ready = snap.character.novice_process >= CASTLE_READY
    if (order := impose_order(snap, now)) is not None:
        changed.append(order)
    for order_type, number in ((TECH_ORDER, 3),) + (((BUILD, 1),) if ready else ()):
        if next(orders_of(snap, order_type), None) is None:
            taken = any(o.order_id == number for o in snap.orders)
            changed.append(new_order(snap, order_type, now, None if taken else number))
    for building in list(snap.buildings):
        changed += unlock(snap, templates, building)
    if ready and snap.castle is not None and snap.castle.produced_at is None:
        start_production(snap, now)
        changed.append(snap.castle)
    return changed
