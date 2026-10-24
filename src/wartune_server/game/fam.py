"""Regras da árvore da terra secreta (Guild Tree of Ancients, 7501); os pacotes em ``handlers/fam.py``.

(cliente) ``ConsortiaSecretInfo``: ``treeState`` 1 = invocada (dá para energizar), 2 = o líder pode invocar, 3 = sem
ação; ``remainGainTime`` = 900 s desde o ``pickTime`` (o botão do buff só aparece nesse tempo).
``ConsortiaTreeExpView``: energia até ``levels × 20 + 10``. ``ConsortiaSecretInfoView``: o EXP do nível seguinte é o
``Data`` de ``UpGradeTempInfos`` tipo 20 nesse nível. A ajuda (``helpContent``): EXP a cada 15 s por 15 min, a árvore
ganha 1 de EXP por invocação, coletas a cada 3 min. ``ConfigInfos``: ``Fam_Buffer_Price`` 200,
``FamTree_WaterMax`` 50 (energia por dia).

(dedução) a EXP zera ao subir: a guilda da oficial_20261023-171155-1 (#5064, criada 36 dias antes) tinha nível 6 com 7
de EXP, e 1+3+5+8+12+7 = 36, uma invocação por dia. (dedução) uma invocação por dia: o 4432 da captura, com a
invocação das 11:53, veio com ``treeState`` 3 às 16:16.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from ..domain import gameday
from ..domain.models import Consortia, ConsortiaMember
from ..templates.repository import GameTemplates
from . import guild as gd

CALLED, CALLABLE, NO_OPER = 1, 2, 3  # ConsortiaSecretInfo GIVE_POWER_STATE, Call_STATE, NO_OPER_STATE
TREE_SECONDS = 900  # remainGainTime
TICK_SECONDS = 15  # EXP a cada 15 s (ajuda)
COLLECT_SECONDS = 180  # coletas a cada 3 min (ajuda)
UPGRADE_TYPE = 20  # UpGradeTempInfos.Types da árvore
BUFF_RATE = 0.2  # "an extra 20% EXP in the Guild Chamber" (getBuff)
# TODO(inventado): EXP de cada tique (nível do jogador × nível da árvore × exp_per_grade × rate), o bônus da energia
# (a ajuda só diz que sobe "once the tree has been energized to a certain amount") e a contribuição de cada coleta
# ("receive guild contribution points"); ``game_settings.fam_tree`` (0074)
DEFAULTS: dict[str, Any] = {"exp_per_grade": 2, "power_step": 10, "power_rate": 0.1, "collect_offer": 5}


def _cfg(settings: Mapping[str, Any]) -> dict[str, Any]:
    return {**DEFAULTS, **(settings.get("fam_tree") or {})}


def state(guild: Consortia, now: datetime) -> int:
    at = guild.tree_called_at
    if at is not None and (now - at).total_seconds() < TREE_SECONDS:
        return CALLED
    return NO_OPER if at is not None and gameday.same_day(at, now) else CALLABLE


def max_power(guild: Consortia, templates: GameTemplates) -> int:
    return min(guild.levels * 20 + 10, gd.config(templates, "FamTree_WaterMax", 50))


def summon(guild: Consortia, templates: GameTemplates, now: datetime) -> None:
    """Invoca: energia zerada, +1 de EXP na árvore e o nível sobe quando chega ao ``Data`` do nível seguinte."""
    guild.tree_called_at, guild.tree_power = now, 0
    row = next(templates.find("UpGradeTempInfos", Types=UPGRADE_TYPE, Grades=guild.tree_grade + 1), None)
    if row is None:
        return  # nível máximo (10)
    guild.tree_gp += 1
    if guild.tree_gp >= int(row["Data"]):
        guild.tree_grade, guild.tree_gp = guild.tree_grade + 1, 0


def bought(guild: Consortia, member: ConsortiaMember) -> bool:
    return guild.tree_called_at is not None and member.fam_buff_at == guild.tree_called_at


def energized(guild: Consortia, member: ConsortiaMember) -> bool:
    return guild.tree_called_at is not None and member.fam_power_at == guild.tree_called_at


def rate(guild: Consortia, member: ConsortiaMember | None, settings: Mapping[str, Any], now: datetime) -> float:
    """Multiplicador de EXP do 4453: 1.0 sem a árvore (visto #5066); com ela, mais a energia e o buff do 8566."""
    if state(guild, now) != CALLED:
        return 1.0
    cfg = _cfg(settings)
    value = 1.0 + guild.tree_power // int(cfg["power_step"]) * float(cfg["power_rate"])
    if member is not None and bought(guild, member):
        value += BUFF_RATE
    return round(value, 1)


def ticks(guild: Consortia, since: datetime | None, now: datetime) -> tuple[int, datetime]:
    """Tiques de EXP vencidos entre ``since`` e ``now`` dentro dos 15 min da invocação, e o novo ``since``."""
    at = guild.tree_called_at
    if at is None:
        return 0, now
    start, end = max(since or at, at), min(now, at + timedelta(seconds=TREE_SECONDS))
    if end <= start:
        return 0, now
    done = int((end - at).total_seconds()) // TICK_SECONDS - int((start - at).total_seconds()) // TICK_SECONDS
    return done, end


def tick_exp(grade: int, guild: Consortia, rate_: float, settings: Mapping[str, Any]) -> int:
    return int(grade * guild.tree_grade * int(_cfg(settings)["exp_per_grade"]) * rate_)


def collect_batch(guild: Consortia, now: datetime) -> int | None:
    """Leva de coletas da invocação em curso (0 na invocação, +1 a cada 3 min); ``None`` sem a árvore."""
    if state(guild, now) != CALLED or guild.tree_called_at is None:
        return None
    return int((now - guild.tree_called_at).total_seconds()) // COLLECT_SECONDS


def collect_offer(settings: Mapping[str, Any]) -> int:
    return int(_cfg(settings)["collect_offer"])
