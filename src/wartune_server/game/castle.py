"""Regras do castelo sobre o ``PlayerSnapshot``: produção de ouro, armazém, população, filas de
construção e templates de prédio. Quem chama grava as entidades alteradas numa ``save`` só.

Produção: o ouro rende ``goldYield`` por hora (conselho 901 + mina 101 + tecnologia de ouro) até o
teto do armazém (301); ouro ganho por outras fontes pode passar do teto, e aí a produção só para
(captura do tutorial: 200872 com teto 10000). O rendimento é acumulado sob demanda (``settle``):
quem gasta ouro chama ``settle`` antes e grava personagem + castelo juntos.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from datetime import datetime, timedelta

from ..domain.models import Building, BuildOrder, Castle, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from .builders import login as b
from .session import GameSession

S_CASTLE_YIELD = 109
COUNCIL, MINE, DEPOT, HOUSE, ACADEMY = 901, 101, 301, 1201, 501
GOLD_TECH = ("13",)  # MasterType das tecnologias de ouro (1304, 2304): EffectTempInfos.Property1 por nível
TECH = ("13", "14")  # MasterType das tecnologias: usam a fila de tecnologia
BASE_GOLD_MAX = 10000  # teto sem armazém (captura do tutorial, antes de existir o 301)
BUILD, TECH_ORDER, IMPOSE = 1, 2, 3  # OrderInfoMsg.orderType
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
    # ponytail: sem terras selvagens (goldWildLandYield) nem bônus de guilda/efeitos; o oficial soma +30
    # que não sabemos de onde vem (login.json: 8550 = 8220 dos prédios + 300 da tecnologia + 30)
    return total


def gold_max(snap: PlayerSnapshot, templates: GameTemplates) -> int:
    depot = by_son_type(snap, templates, DEPOT)
    row = template(templates, depot.template_id) if depot else None
    return int(row["Property2"]) if row else BASE_GOLD_MAX


def max_population(snap: PlayerSnapshot, templates: GameTemplates) -> int:
    house = by_son_type(snap, templates, HOUSE)
    row = template(templates, house.template_id) if house else None
    return int(row["Property2"]) if row else 0


def pending_gold(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> tuple[int, datetime | None]:
    """Ouro produzido desde ``produced_at`` e o novo marco (guarda a fração de hora que sobrou)."""
    castle, gold = snap.castle, snap.character.gold
    if castle is None or castle.produced_at is None:
        return 0, None
    per_hour, cap = gold_yield(snap, templates), gold_max(snap, templates)
    if per_hour <= 0 or gold >= cap or now <= castle.produced_at:
        return 0, max(now, castle.produced_at)
    gain = int(per_hour * (now - castle.produced_at).total_seconds() // 3600)
    if gold + gain >= cap:
        return cap - gold, now
    return gain, castle.produced_at + timedelta(seconds=gain * 3600 / per_hour)


def settle(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> None:
    """Acumula a produção no ouro do personagem (grave personagem e castelo juntos)."""
    gain, mark = pending_gold(snap, templates, now)
    if snap.castle is not None and mark is not None:
        snap.character.gold += gain
        snap.castle.produced_at = mark


def start_production(snap: PlayerSnapshot, now: datetime) -> None:
    if snap.castle is not None and snap.castle.produced_at is None:
        snap.castle.produced_at = now


def yield_msg(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> pb.CastleYieldMsg:
    gain, _ = pending_gold(snap, templates, now)
    return pb.CastleYieldMsg(
        goldYield=gold_yield(snap, templates),
        goldTotalCount=snap.character.gold + gain,
        goldMax=gold_max(snap, templates),
        # ponytail: população ocupada = soldados do exército (sistema de tropas); 0 até ele existir
        curPopulation=0,
        maxPopulation=max_population(snap, templates),
        crystalsCount=snap.character.crystals,
    )


def castle_yield(s: GameSession) -> None:
    """109: ouro, teto, população e cristais (o cliente atualiza a barra de recursos)."""
    assert s.snapshot is not None
    s.send(S_CASTLE_YIELD, yield_msg(s.snapshot, s.ctx.templates, s.ctx.clock.now()))


def politics_msg(snap: PlayerSnapshot, templates: GameTemplates) -> pb.CastleYieldMsg:
    """152 (conselho): o rendimento dos prédios, sem terras selvagens."""
    total = gold_yield(snap, templates)
    msg = pb.CastleYieldMsg(goldYield=total, goldWildLandYield=0, goldTechnology=0, goldWonder=0)
    msg.goldTotalCount = total
    return msg


def energy_max(templates: GameTemplates) -> int:
    """Teto da energia de teleporte: Property2 do prédio de transferência (1511, id -11 no cliente)."""
    # ponytail: sem o bônus de raça/efeitos do limite (PlayerEffect.getTransferPowerLimitAddition)
    row = first_grade(templates, TRANSFER)
    return int(row["Property2"]) if row else 500


def impose_used(castle: Castle, now: datetime) -> int:
    """Cobranças de ouro (8327) já feitas hoje; o contador zera na virada do dia."""
    if castle.imposed_at is None or castle.imposed_at.date() != now.date():
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
    """``QueueBar.coolItem``: 1 diamante a cada 10 minutos (ou fração) que faltam."""
    return math.ceil(remain / 600)


def order_info(order: BuildOrder, now: datetime) -> pb.OrderInfoMsg:
    return pb.OrderInfoMsg(orderId=order.order_id, orderType=order.order_type, remainTime=order.remain(now))


def order_full(order: BuildOrder, now: datetime) -> pb.OrderInfoMsg:
    """Com dono, início e duração: 4155 (login) e 4187 (8279)."""
    msg = order_info(order, now)
    msg.userId, msg.beginTime, msg.needTime = order.character_id, b.fmt_time(order.begin_at), order.need_time
    return msg


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
    pulou o tutorial) recebe aqui. Os números seguem o oficial: 1 prédio, 2 cobrança, 3 tecnologia.
    """
    changed: list[object] = []
    ready = snap.character.novice_process >= CASTLE_READY
    for order_type, number in ((IMPOSE, 2), (TECH_ORDER, 3)) + (((BUILD, 1),) if ready else ()):
        if next(orders_of(snap, order_type), None) is None:
            taken = any(o.order_id == number for o in snap.orders)
            changed.append(new_order(snap, order_type, now, None if taken else number))
    for building in list(snap.buildings):
        changed += unlock(snap, templates, building)
    if ready and snap.castle is not None and snap.castle.produced_at is None:
        start_production(snap, now)
        changed.append(snap.castle)
    return changed
