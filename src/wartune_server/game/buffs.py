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
from . import events

KEY = "buff:"
# EffectTempInfos com efeito aqui: "EXP Boost" (2013001-4), "Capacity Upgrade" (Gold Expansion Scroll 2010501,
# "Warehouse Capacity +{Grades}%") e "Population Boost" (Population Expansion Scroll 2010801)
EXP_BOOST, GOLD_MAX, POPULATION = 2030, 2008, 2005
ITEM = 2  # BufferDataMsg.type de buff de item: PlayerBufferInfo usa o ícone/nome do item e o EffectTempInfo


def _live(st: EventState, now: datetime) -> bool:
    return st.updated_at > now


def grade(snap: PlayerSnapshot, effect: int, now: datetime) -> int:
    st = events.peek(snap, f"{KEY}{effect}")
    return st.value if st is not None and st.updated_at > now else 0


def boost(value: int, snap: PlayerSnapshot, effect: int, now: datetime) -> int:
    """``value`` com o efeito ``effect`` em %, se estiver ativo."""
    return value * (100 + grade(snap, effect, now)) // 100


def active(snap: PlayerSnapshot, now: datetime) -> list[EventState]:
    return [e for e in snap.events if e.key.startswith(KEY) and _live(e, now)]


def effect_of(st: EventState) -> int:
    return int(st.key[len(KEY) :])


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
