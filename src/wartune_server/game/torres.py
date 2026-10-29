"""Torres 8200-8204: Tower of Kings (``SonTypes`` 300, ``DifficultyGrade`` 1-4) e The Spire (8201, ``SonTypes`` 301).

As duas são masmorras em grupo (``Capacity`` 4, sala) com mapa gerado (migração 0102). Do cliente:

- Tower of Kings: uma entrada por dia (``KingTowerInfo.maxKingCount`` 1; "Already entered the Tower of Kings
  today!"); a dificuldade N só abre com a N-1 vencida ("Clear {0} to enter"); ``KingTowerInfoMsg`` (4900) com
  ``enterCount``, ``maxIndex`` (a maior dificuldade vencida), e no fim ``currentStep`` (a dificuldade),
  ``currentIndex`` (o andar, "Tower of Kings L{1}") e ``rewardCount`` ("obtained REWARD x{2}").
- The Spire: "Each player may only challenge the Spire once per day" (``PlayerMsg.trialCount``/``trialMaxCount``);
  "rewarded according to the stages you've completed"; o andar é a onda da luta (``battle.layer``).
- Prêmio: a coluna ``Item`` da campanha (``-700`` EXP e o baú: 2131002-2131005 dos reis, 2060045 da Spire).

- Spire Runes (``ConfigInfos.TrialSkill`` "skill,X,X,preço": 101-104): 4468 ``PlayerTrialMsg`` com a loja, 8582
  compra (``TrialInfoMsg``: ``param1`` 0 = Balens vinculados primeiro, alerta USEBINDPOINT), 4467 de volta
  (``count`` = compradas hoje, ``param1`` != 0 = deu certo), cargas no ``HeroMsg.trials`` e uso pelo 10507.

Internet (docs/fontes-internet.md, wiki da Tower of Kings e da Spire): um baú da dificuldade por luta vencida na
King; na Spire, EXP e baús por chefe vencido (andar). Sem carta no fim: o prêmio é o baú por luta.
Internet também: 24 chefes na Spire, 300.000 EXP e 7 Spire Chests por chefe; as cargas grátis das Spire Runes (3, 3,
3 e 1) batem com o 1º X da ``TrialSkill``. TODO(inventado): o 2º X é a cota diária de compra (a wiki não diz).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ..domain import gameday
from ..domain.models import EventState, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..services import ledger
from ..templates.repository import GameTemplates
from . import events as ev

KING, SPIRE = 300, 301  # Campaigns.SonTypes
MAX_PER_DAY = 1  # KingTowerInfo.maxKingCount; PlayerMsg.trialMaxCount (builders/login)
SPIRE_LEED = 28  # LeedTemp "Enter the Spire" (PassCount 1): a devoção da entrada (handlers/events.leed_done)
KING_KEY, KING_MAX_KEY = "king_tower", "king_tower:max"  # entradas de hoje; maior dificuldade vencida
DAILY = {KING: KING_KEY, SPIRE: "spire"}  # EventState diário (``recover`` lê o "spire": Recuperar EXP sonType 5)
SPIRE_TOTAL = "spire:total"  # entradas na Spire desde sempre (guia de 7 dias, condição 23 ENTER_CAMPAIGN)
TRIAL_SKILL = "TrialSkill"  # ConfigInfos: "101,3,3,45|102,3,3,45|104,3,3,45|103,1,1,95"
SPIRE_EXP, SPIRE_CHESTS = 300_000, 7  # internet: EXP e baús por chefe (andar) da Spire
SHOP_KEY = "spire_shop"  # EventState diário: JSON {skill: compradas hoje}


def son(row: Mapping[str, Any]) -> int:
    """300/301 nas torres, 0 fora delas."""
    kind = int(row.get("SonTypes") or 0)
    return kind if kind in DAILY else 0


def used(snap: PlayerSnapshot, kind: int, now: datetime) -> int:
    """Entradas de hoje na torre ``kind``."""
    st = ev.peek(snap, DAILY[kind])
    return st.value if st is not None and gameday.same_day(st.updated_at, now) else 0


def best(snap: PlayerSnapshot) -> int:
    st = ev.peek(snap, KING_MAX_KEY)
    return st.value if st is not None else 0


def unlocked(snap: PlayerSnapshot, row: Mapping[str, Any]) -> bool:
    """Tower of Kings: a dificuldade N pede a N-1 vencida ("Clear {0} to enter"); a Spire abre sempre."""
    return son(row) != KING or best(snap) >= int(row.get("DifficultyGrade") or 1) - 1


def enter(snap: PlayerSnapshot, row: Mapping[str, Any], now: datetime) -> tuple[bool, list[EventState]]:
    """Gasta a entrada do dia se ainda houver. Devolve (com prêmio?, linhas a gravar)."""
    kind = son(row)
    st = ev.daily(snap, DAILY[kind], now)
    if st.value >= MAX_PER_DAY:
        return False, []
    st.value, st.updated_at = st.value + 1, now
    rows = [st]
    if kind == SPIRE:
        total = ev.state(snap, SPIRE_TOTAL, now)
        total.value, total.updated_at = total.value + 1, now
        rows.append(total)
    return True, rows


def chest(row: Mapping[str, Any]) -> int:
    """O baú da coluna ``Item`` (``-700,2131002``)."""
    return next((int(x) for x in str(row.get("Item", "")).split(",") if x and int(x) > 0), 0)


def prize(row: Mapping[str, Any], floors: int) -> list[tuple[int, int]]:
    """Baús por andar vencido (internet): 1 por luta na King, 7 por chefe na Spire."""
    per = SPIRE_CHESTS if son(row) == SPIRE else 1
    return [(tid, floors * per)] if floors > 0 and (tid := chest(row)) else []


def finish(snap: PlayerSnapshot, row: Mapping[str, Any], now: datetime) -> list[EventState]:
    """King vencida: grava a maior dificuldade."""
    if son(row) != KING:
        return []
    st = ev.state(snap, KING_MAX_KEY, now)
    st.value, st.updated_at = max(st.value, int(row.get("DifficultyGrade") or 1)), now
    return [st]


def king_msg(snap: PlayerSnapshot, now: datetime, **end: int) -> pb.KingTowerInfoMsg:
    """4900: entradas de hoje e a maior dificuldade; ``end`` (currentIndex, currentStep, rewardCount) no fim."""
    return pb.KingTowerInfoMsg(enterCount=used(snap, KING, now), maxIndex=best(snap), **end)


def shop(templates: GameTemplates) -> list[tuple[int, int, int, int]]:
    """(skill, cargas grátis, cota diária, preço em Balens) da ``TrialSkill``, na ordem da loja (índice 0-3)."""
    row = templates.get("ConfigInfos", TRIAL_SKILL, key="ConfigName") or {}
    out = []
    for part in str(row.get("ConfigValue", "")).split("|"):
        if part:
            skill, free, quota, price = (int(x) for x in part.split(","))
            out.append((skill, free, quota, price))
    return out


def bought(snap: PlayerSnapshot, now: datetime) -> dict[int, int]:
    st = ev.daily(snap, SHOP_KEY, now)
    return {int(k): v for k, v in json.loads(st.text or "{}").items()}


def trials(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> list[pb.TrialInfoMsg]:
    """``HeroMsg.trials`` da luta da Spire: as cargas de cada Spire Rune (grátis + compradas hoje) e a recarga
    (``param4``, ``SkillTempInfos.CoolDown``)."""
    got = bought(snap, now)
    out = []
    for i, (skill, free, _, _) in enumerate(shop(templates)):
        cool = int((templates.get("SkillTempInfos", skill) or {}).get("CoolDown") or 0)
        out.append(pb.TrialInfoMsg(index=i, skillId=skill, count=free + got.get(skill, 0), param4=cool))
    return out


def shop_msg(snap: PlayerSnapshot, templates: GameTemplates, now: datetime, layer: int = 0) -> pb.PlayerTrialMsg:
    """4468: andar atual, EXP e baús que ele vale (``rewardExp``/``rewardBox``) e a loja (compradas, cota, preço)."""
    got = bought(snap, now)
    msg = pb.PlayerTrialMsg(
        userId=snap.character.id or 0, param1=layer, param2=layer * SPIRE_EXP, param3=layer * SPIRE_CHESTS
    )
    for i, (skill, _, quota, price) in enumerate(shop(templates)):
        msg.trialInfos.add(index=i, skillId=skill, param1=got.get(skill, 0), param2=quota, param3=price)
    return msg


def buy(
    snap: PlayerSnapshot, templates: GameTemplates, skill: int, bind: bool, now: datetime
) -> tuple[int, list[object]] | None:
    """Compra uma carga para hoje. Devolve (compradas hoje, linhas a gravar) ou ``None`` (fora da loja, cota
    cheia ou sem saldo)."""
    row = next((r for r in shop(templates) if r[0] == skill), None)
    got = bought(snap, now)
    if row is None or got.get(skill, 0) >= row[2]:
        return None
    entry = ledger.pay(snap.character, row[3], bind=bind, reason="spire_rune", ref=str(skill), now=now)
    if entry is None:
        return None
    got[skill] = got.get(skill, 0) + 1
    st = ev.daily(snap, SHOP_KEY, now)
    st.text, st.updated_at = json.dumps({str(k): v for k, v in got.items()}), now
    return got[skill], [snap.character, st, entry]


# -- sombras da Tower of Kings ---------------------------------------------------------------------------------------
# (internet) "challenged by a party of four Shadow Souls. These are shadows of the top 16 players in ... strength
# rankings (Rank 1-4 ... Nightmare, 5-8 Hard, 9-12 Normal, 13-16 Easy) ... five levels ... The Shadows keep getting
# stronger after each level". A cópia é a do coliseu (``arena.copy_hero``).
SHADOW_TOP, SHADOW_PARTY = 16, 4
SHADOW_POS = (5, 1, 7, 3)  # posições do lado 2 (5, 1 e 7 vistas nas lutas da 9002); TODO(inventado) a 3
SHADOW_GROWTH = 0.10  # TODO(inventado): +10% de vida e ataque por nível vencido ("keep getting stronger")
KING_LEVELS = 5  # (internet) "There are a total of five levels"


def shadow_slice(grade: int) -> slice:
    """As posições do ranking de força de cada dificuldade: Easy 13-16 ... Nightmare 1-4 (índices 0-based)."""
    top = (4 - grade) * SHADOW_PARTY
    return slice(top, top + SHADOW_PARTY)


def with_shadows(spec: dict[str, Any], shadows: list[dict[str, Any]], level: int) -> dict[str, Any]:
    """A luta da King contra as sombras: os inimigos da planta saem e entram as cópias, mais fortes a cada nível."""
    k = 1 + SHADOW_GROWTH * (level - 1)
    heroes = []
    for i, shadow in enumerate(shadows[:SHADOW_PARTY]):
        h = dict(shadow, livingId=20 + i, pos=SHADOW_POS[i], hasShadow=True)
        h["maxHp"] = h["initHp"] = h["hp"] = round(int(shadow["hp"]) * k)
        h["attack"] = round(int(shadow.get("attack", 0)) * k)
        heroes.append(h)
    mine = [u for u in spec["soldiers"] if int(u["side"]) == 1]
    return spec | {"heroes": heroes, "soldiers": mine, "reinforce": []}
