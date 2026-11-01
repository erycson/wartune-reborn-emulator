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

import random
from collections.abc import Mapping
from dataclasses import dataclass, field
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
# ``game_settings.fam_tree`` (0074, 0146). (visto) 20261031-183522-1: o tique de 15 s deu 3468 de EXP (nível 34, árvore
# 6: 34 × 6 × 17) e 4162 com o buff do 8566 (× 1,2); com 13 de energia ainda 3468. Cada leva de coletas mostra 10 das
# 21 e a coleta deu 1, 5 ou 10 de contribuição (12, 19 e 13 vezes em 44). TODO(inventado): o bônus da energia
# (``power_step``/``power_rate``: só se sabe que 13 não mudou nada)
DEFAULTS: dict[str, Any] = {
    "exp_per_grade": 17, "power_step": 20, "power_rate": 0.1, "collect_offers": [[1, 12], [5, 19], [10, 13]],
    "collect_shown": 10,
}  # fmt: skip
# (visto) 183522: "The Guild Chamber is under attack!" a toda hora cheia (15:00 a 21:00, #2382-#9511) e os 3
# Invasores somem às 21:30 (#12800-#12802)
INVADER_HOURS, INVADER_MINUTES = 1, 30


@dataclass
class Invasion:
    """Onda de Invasores de uma guilda, a mesma para todos os membros (o usuário: o Invasor vencido some e só um
    luta com ele por vez; os 3 do 7501 voltam a cada onda)."""

    wave: datetime  # início da onda (hora cheia, no fuso do jogo)
    dead: set[int] = field(default_factory=set)  # campDataId vencidos nesta onda
    fighting: dict[int, int] = field(default_factory=dict)  # campDataId -> quem está lutando


def wave_start(now: datetime) -> datetime:
    at = gameday.local(now)
    return at.replace(hour=at.hour - at.hour % INVADER_HOURS, minute=0, second=0, microsecond=0)


def invasion(store: dict[int, Invasion], guild_id: int, now: datetime) -> tuple[Invasion, bool]:
    """A onda em curso; ``True`` quando ela acabou de trocar (o aviso no chat da guilda). ``store`` (onda e vencidos)
    vai para ``server_states`` e volta no arranque (``game/server_state.py``): o reinício não traz os Invasores
    vencidos de volta nem repete o aviso da onda."""
    wave = wave_start(now)
    inv = store.get(guild_id)
    if inv is not None and inv.wave == wave:
        return inv, False
    store[guild_id] = new = Invasion(wave)
    return new, inv is not None


def invaders_up(now: datetime) -> bool:
    """Os Invasores ficam à vista só na primeira meia hora da onda."""
    return gameday.local(now).minute < INVADER_MINUTES


# Master Treasure Thief (8743): (cliente) ``ConsortiaSecretCallMonsterView`` "(n/3)" com a contagem ``leftTime``.
# (visto) 183522 #11064-#12417: 3 levas a 0, 180 e 360 s da chamada; cada uma esconde os 30 nós masterType 181 e
# mostra 20 sorteados (o vencido numa leva volta na outra)
LORDS_BATCHES, LORDS_SECONDS, LORDS_SHOWN = 3, 180, 20


@dataclass
class Lords:
    """Chamada do Master Treasure Thief de uma guilda (como ``Invasion``: o vencido some, um luta por vez).
    ``wave``: a leva dos vencidos em ``dead`` (zera na leva seguinte); ``told``: a última leva avisada no chat."""

    called_at: datetime
    dead: set[int] = field(default_factory=set)
    fighting: dict[int, int] = field(default_factory=dict)
    wave: int = 0
    told: int = 0

    def batch(self, now: datetime) -> int | None:
        """Leva em curso (0..2), 3 min cada; None antes e depois.
        Decisão do usuário: a 3ª também dura 3 min (na captura todos morreram antes)."""
        if now < self.called_at or not gameday.same_day(self.called_at, now):
            return None
        k = int((now - self.called_at).total_seconds()) // LORDS_SECONDS
        return k if k < LORDS_BATCHES else None

    def open(self, now: datetime) -> bool:
        """``isOpenLordsNode``: ainda vem leva (visto: falso já na 3ª, #12366)."""
        k = self.batch(now)
        return k is not None and k < LORDS_BATCHES - 1

    def left_ms(self, now: datetime) -> int:
        """O que falta para a próxima leva, em passos de 5 s (visto 140000, 100000, 40000, 145000...)."""
        ms = LORDS_SECONDS * 1000 - int((now - self.called_at).total_seconds() * 1000) % (LORDS_SECONDS * 1000)
        return max(0, round(ms / 5000) * 5000)

    def shown(self, camps: list[int], k: int) -> set[int]:
        """Os 20 da leva ``k``, os mesmos para a guilda toda (sorteio fixo pela hora da chamada)."""
        rng = random.Random(f"{self.called_at.isoformat()}:{k}")
        return set(rng.sample(sorted(camps), min(LORDS_SHOWN, len(camps))))


def lords_of(store: dict[int, Lords], guild_id: int, now: datetime) -> Lords | None:
    """A chamada em curso da guilda; a de outro dia sai do ``store``. Leva nova: os vencidos voltam."""
    lords = store.get(guild_id)
    k = lords.batch(now) if lords is not None else None
    if lords is None or k is None:
        store.pop(guild_id, None)
        return None
    if k != lords.wave:
        lords.dead.clear()
        lords.wave = k
    return lords


def lords_drop(settings: Mapping[str, Any]) -> list[tuple[int, int]]:
    """O baú do Master Treasure Thief vencido (``game_settings.fam_lords``, 0146): (visto) 9 de 9 vitórias da 183522
    com Lvl. 1 Contribution Badge (2030801) ×3 no 4103."""
    cfg = settings.get("fam_lords") or {}
    drops = cfg.get("drops", [[2030801, 3, 1.0]])
    return [(int(t), int(n)) for t, n, chance in drops if random.random() < float(chance)]


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
    return round(grade * guild.tree_grade * int(_cfg(settings)["exp_per_grade"]) * rate_)  # 3468 × 1,2 = 4162


def collect_batch(guild: Consortia, now: datetime) -> int | None:
    """Leva de coletas da invocação em curso (0 na invocação, +1 a cada 3 min); ``None`` sem a árvore."""
    if state(guild, now) != CALLED or guild.tree_called_at is None:
        return None
    return int((now - guild.tree_called_at).total_seconds()) // COLLECT_SECONDS


def collect_key(guild: Consortia, batch: int) -> str:
    return f"{guild.tree_called_at.isoformat() if guild.tree_called_at else ''}:{batch}"


def collected(store: dict[int, tuple[str, set[int]]], guild: Consortia, batch: int) -> set[int]:
    """As coletas já pegas na leva ``batch`` da guilda (a leva velha sai do ``store``)."""
    key = collect_key(guild, batch)
    got = store.get(guild.id or 0)
    if got is None or got[0] != key:
        store[guild.id or 0] = got = (key, set())
    return got[1]


def collect_offer(settings: Mapping[str, Any]) -> int:
    offers = _cfg(settings)["collect_offers"]
    return int(random.choices([o for o, _ in offers], [w for _, w in offers])[0])


def collect_shown(guild: Consortia, batch: int, camps: list[int], settings: Mapping[str, Any]) -> set[int]:
    """As coletas da leva ``batch``, as mesmas para a guilda (sorteio fixo pela invocação)."""
    rng = random.Random(f"{guild.tree_called_at.isoformat() if guild.tree_called_at else ''}:{batch}")
    return set(rng.sample(sorted(camps), min(int(_cfg(settings)["collect_shown"]), len(camps))))
