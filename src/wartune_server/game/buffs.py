"""Pergaminhos de efeito (ItemTempInfo SonType 201): Property1 = EffectTempInfo, Property2 = minutos por
unidade, Property3 = grau (o ``{Grades}`` da descrição; % nos efeitos que o servidor aplica). Um por efeito,
em ``event_states``: chave ``buff:<efeito>``, ``value`` = grau, ``text`` = item (ícone e nome no cliente) e
``updated_at`` = fim do efeito. Vencido = ``updated_at`` <= agora; não precisa de timer. Ver ``docs/itens.md``.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from ..domain.models import EventState, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import events

KEY = "buff:"
# EffectTempInfos com efeito aqui: "EXP Boost" (2013001-4), "Capacity Upgrade" (Gold Expansion Scroll 2010501,
# "Warehouse Capacity +{Grades}%") e "Population Boost" (Population Expansion Scroll 2010801)
EXP_BOOST, GOLD_MAX, POPULATION = 2030, 2008, 2005
ITEM = 2  # BufferDataMsg.type de buff de item: PlayerBufferInfo usa o ícone/nome do item e o EffectTempInfo
# Poções de atributo (EffectTempInfo.PropertyType1 -> atributo do herói, + grau pontos). Descrições dos
# EffectTempInfos: 135 "Strength", 138 "Intellect", 139 "Charisma", 140 "Stamina"/"Endurance"; (dedução) 137
# "Defense"/"Armor" = Agility (o 2141 soma "Strength, Intellect, Armor, Endurance"; o herói só tem esses 4 + Captain)
STATS = {
    135: ("Power",),
    137: ("Agility",),
    138: ("Intellect",),
    139: ("Captain",),
    140: ("Physique",),
    202: ("Power", "Intellect", "Agility", "Physique"),
}


def _live(st: EventState, now: datetime) -> bool:
    return st.updated_at > now


def grade(snap: PlayerSnapshot, effect: int, now: datetime) -> int:
    st = events.peek(snap, f"{KEY}{effect}")
    return st.value if st is not None and st.updated_at > now else 0


def boost(value: int, snap: PlayerSnapshot, effect: int, now: datetime) -> int:
    """``value`` com o efeito ``effect`` em %, se estiver ativo."""
    return value * (100 + grade(snap, effect, now)) // 100


def active(snap: PlayerSnapshot, now: datetime) -> list[EventState]:
    """Os do 4188. A trégua (2001) fica de fora: o cliente a monta só pelo 4452 (``PlayerBufferManager``)."""
    return [e for e in snap.events if e.key.startswith(KEY) and _live(e, now) and effect_of(e) != PROTECTION]


# trégua do castelo, City Protection Token (208006): o cliente conta pelo 4452 ``defenceLefttime`` (segundos, como o
# ``validityDate * 60`` dos outros) e o cancela com o 8562 (``PlayerBufferManager.removeBuffer``)
PROTECTION = 2001


def protection_left(snap: PlayerSnapshot, now: datetime) -> int:
    """Segundos de trégua que faltam (0 sem trégua)."""
    st = events.peek(snap, f"{KEY}{PROTECTION}")
    return max(0, math.ceil((st.updated_at - now).total_seconds())) if st is not None else 0


def effect_of(st: EventState) -> int:
    return int(st.key[len(KEY) :])


def stat_type(templates: GameTemplates, effect: int) -> int:
    return int((templates.get("EffectTempInfos", effect) or {}).get("PropertyType1") or 0)


def stat_bonuses(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> list[Row]:
    """Poções ativas como linhas de bônus do herói (``HeroStats.of``): somam no ``total*``, não no ``base*`` (o
    cliente marca o atributo com efeito quando ``total`` > ``base``, ``BasePropertyInfo.hasEffect``)."""
    rows: list[Row] = []
    for st in active(snap, now):
        if attrs := STATS.get(stat_type(templates, effect_of(st))):
            rows.append({a: str(st.value) for a in attrs})
    return rows


# Pergaminhos de % (EffectTempInfo.PropertyType1 -> chave do ``PlayerHero``): descrições "PATK +{Grades}%", "MATK",
# "PDEF", "MDEF", "HP", "Crit"; 37 "Defense +{Grades}%" (Student's Oatmeal) nas duas defesas (dedução). Valem na luta
# (``campaign.player_hero``). 46 "Troop Count" e 48 "Honor Received" agem fora daqui (``percent``).
PERCENT = {
    41: ("PhyAttack",),
    42: ("MagicAttack",),
    43: ("PhyDefence",),
    44: ("MagicDefence",),
    37: ("PhyDefence", "MagicDefence"),
    45: ("Live",),
    47: ("ForceHit",),
}
HONOR_BOOST = 48  # "Honor Received +{Grades}%" (Double Honor Scroll)


def percent(snap: PlayerSnapshot, templates: GameTemplates, kind: int, now: datetime) -> int:
    """% somado dos pergaminhos ativos do tipo ``kind`` (``PropertyType1``)."""
    return sum(st.value for st in active(snap, now) if stat_type(templates, effect_of(st)) == kind)


def percent_stats(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> dict[str, int]:
    """Chave do herói na luta -> % dos pergaminhos ativos."""
    out: dict[str, int] = {}
    for st in active(snap, now):
        for key in PERCENT.get(stat_type(templates, effect_of(st)), ()):
            out[key] = out.get(key, 0) + st.value
    return out


def data(st: EventState, now: datetime) -> pb.BufferDataMsg:
    """Uma linha do 4188. ``validityDate`` em minutos (o cliente multiplica por 60; <= 0 tira o ícone): arredonda
    para cima, então o relógio do cliente acaba depois do servidor e o 8283 dele chega com o efeito já vencido."""
    left = max(0, math.ceil((st.updated_at - now).total_seconds() / 60))
    return pb.BufferDataMsg(
        templateId=effect_of(st), validityDate=left, grade=st.value, type=ITEM, typeTemplateid=int(st.text or 0)
    )


def buffer_list(states: list[EventState], now: datetime) -> pb.ItemBufferRspMsg:
    """4188 (``PlayerBufferManager.__refreshItemBufferHandler``)."""
    return pb.ItemBufferRspMsg(bufferData=[data(st, now) for st in states])


def apply(
    snap: PlayerSnapshot, effect: int, item_id: int, level: int, minutes: int, now: datetime
) -> EventState | None:
    """Liga o efeito. Grau menor que o ativo: recusa (o cliente já barra, "Stronger buff already active",
    ``MulItemUseFrame``). *(dedução)* grau igual soma o tempo; maior substitui grau e tempo."""
    st = events.state(snap, f"{KEY}{effect}", now)
    live = _live(st, now)
    if live and level < st.value:
        return None
    start = st.updated_at if live and level == st.value else now
    st.value, st.text, st.updated_at = level, str(item_id), start + timedelta(minutes=minutes)
    return st


def stop(snap: PlayerSnapshot, effect: int, now: datetime) -> EventState | None:
    """Desliga (8283: fim do relógio no cliente ou o jogador tirou o ícone). Já vencido também volta: o cliente
    só apaga o ícone com o 4188 de ``validityDate`` 0."""
    st = events.peek(snap, f"{KEY}{effect}")
    if st is not None:
        st.updated_at = min(st.updated_at, now)
    return st
