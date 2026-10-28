"""Pesca (9507 ``FreshPoolMsg``; respostas 4916 ``FishPoolMsg``, 4917 ``FishResultMsg``, 4918 ``FishInfosMsg``,
4919 ``HelpOverMsg``, 4920 ``CrazyFishInfoMsg``): estado do pescador e o cardume.

Fontes: *(cliente)* ``FishManager``, ``FishModel`` (20 tentativas, 4 ferramentas, piscina de 830 px, canais),
``FishFrame`` (cd + 300 > 1800 bloqueia, custo do ⏩ ``ceil(cd/60)*3``, cesto cheio com 21), ``FishHelpFrame`` (ajuda
paga ``(3 - ajudantes)*5``), ``FishPoolInfo`` (nível pela ``UpGradeTempInfos`` tipo 40), ``FishTemplateInfos``
(canal, nível, GP, pontos, velocidade, comprimento, prêmios); *(visto)* 26/10, 27/10 e 28/10 (docs/eventos.md).

Estado em ``EventState`` ``fish`` (``text`` JSON); o cardume é da sessão (cada sessão oficial teve ids próprios:
27/10 27,10,29..., 28/10 39,30,23...). shortcut: o cardume renasce ao relogar; gravar se precisar sobreviver.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from ..domain import gameday
from ..domain.models import EventState, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import events as ev

KEY = "fish"
OPEN_GRADE = 28  # OpenGrades.FISH
MAX_COUNT = 20  # FishModel.FISHMAX e ConfigInfos Fish_Count: tentativas por dia
# ConfigInfos também traz Fish_Cd_Point 3 (o ``*3`` do ⏩), Fish_Help_Point 15 (3 ajudantes * 5) e Fish_Help_Count 3
CD_STEP, CD_MAX = 300, 1800  # FishFrame.__clickHandler: cada lançamento soma 300 s; bloqueia se passar de 1800
BASKET = 21  # FishFrame: "Fish Basket" cheio com 21 itens (bagType 23)
POOL_WIDTH = 830  # FishModel.FISHPOOLWIDTH; x = (now - beginTime) * Speed / 40
LEVEL_TYPE = 40  # UpgradeType.UPGRADE_TYPE_FISH
STAGGER = 2000  # (visto) 27/10 #172: no mesmo canal os peixes entram de 2 em 2 s
# (visto) 27/10: os 20 lugares fixos da sessão, por canal (3 rasos de obstáculo, 5, 5, 5 e 2 no fundo)
SLOTS = {1: (27, 10, 29), 2: (86, 40, 73, 71, 68), 3: (43, 44, 50, 64, 72), 4: (31, 42, 76, 94, 96), 5: (4, 79)}
NORMAL, RAGE, GONE, CAUGHT = 1, 3, 4, 5  # FishStateEnums (5: o pescado, visto 27/10 #180)
TOOL_ROLL = 100  # (visto) 4917 ``tool`` 1..98; só o 1 deu ferramenta ("Shoal Water Torpedo", tool1 0 -> 1)
# nomes: o 1 é o da captura (27/10 #200); os outros são os do toolTip do cliente: TODO(inventado) nome no alerta
TOOL_NAMES = ("Shoal Water Torpedo", "Triple Spear", "Power Spear", "Depth Torpedo")
THREE, POWER = 1, 2  # FishForkEnums: hookState das ferramentas 2 e 3
HOOK_FISH = {0: 1, THREE: 3, POWER: 20}  # peixes por lançamento: TODO(inventado) o teto da lança de força
# toolTip1: obstáculos rasos somem por 20 s; toolTip4: peixes e obstáculos rasos voltam em 3 s
TORPEDO = {1: ((1,), 20000), 4: ((1, 2, 3), 3000)}  # TODO(inventado) "raso" = canais 1-3 no torpedo fundo
RAGE_CHANCE = 0.1  # TODO(inventado): chance de um peixe dos canais 4-5 com RageId nascer enfurecido
HELPERS = 3  # FishHelpView: com 3 ajudantes a fúria acaba com prêmio
HELP_PRICE = 5  # FishHelpFrame: (3 - ajudantes) * 5 Balens
ALERT = "Received {} while fishing!"  # (visto) 27/10 #177


@dataclass
class Fisher:
    level: int = 0
    gp: int = 0  # EXP dentro do nível (FishPoolInfo: gp/maxGp do próximo nível)
    score: int = 0  # "Weekly Points"
    week: str = ""  # semana ISO do ``score``
    count: int = 0  # lançamentos com peixe hoje
    day: str = ""
    cd_end: str = ""  # fim do cd (ISO)
    tools: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    hook: int = 0  # hookState


def load(snap: PlayerSnapshot, now: datetime) -> Fisher:
    st = ev.peek(snap, KEY)
    return parse(st.text if st is not None else "", now)


def parse(text: str, now: datetime) -> Fisher:
    f = Fisher(**json.loads(text)) if text else Fisher()
    day = gameday.game_day(now)
    if f.day != day.isoformat():  # (visto) 27/10 abre com count 0 depois das 4 do dia 26
        f.count, f.day = 0, day.isoformat()
    year, num = day.isocalendar()[:2]
    week = f"{year}-{num:02d}"
    if f.week != week:  # "Weekly Points" (dedução: zera na segunda como o labirinto de gemas)
        f.score, f.week = 0, week
    return f


def weeks(states: list[EventState], now: datetime) -> list[tuple[int, Fisher]]:
    """Pescadores com pontos na semana, do maior ao menor (desempate pelo id)."""
    out = [(e.character_id, parse(e.text, now)) for e in states if e.key == KEY and e.text]
    return sorted([x for x in out if x[1].score > 0], key=lambda x: (-x[1].score, x[0]))


def position(states: list[EventState], character_id: int, now: datetime) -> int:
    """``order`` do 4916: 1 + quantos têm mais pontos na semana; 0 sem pontos. (visto) 27/10 score 24 -> order 20."""
    ranked = weeks(states, now)
    mine = next((f.score for c, f in ranked if c == character_id), 0)
    return 1 + sum(f.score > mine for _, f in ranked) if mine else 0


def store(snap: PlayerSnapshot, f: Fisher, now: datetime) -> EventState:
    st = ev.state(snap, KEY, now)
    st.text, st.updated_at = json.dumps(asdict(f)), now
    return st


def cd_left(f: Fisher, now: datetime) -> int:
    return max(0, math.ceil((datetime.fromisoformat(f.cd_end) - now).total_seconds())) if f.cd_end else 0


def add_cd(f: Fisher, now: datetime) -> None:
    """(visto) 27/10: acerto e erro somam 300 s ao que falta (cd 1481 -> 1770 no erro #398)."""
    f.cd_end = (now + timedelta(seconds=cd_left(f, now) + CD_STEP)).isoformat()


def can_cast(f: Fisher, now: datetime) -> bool:
    return cd_left(f, now) + CD_STEP <= CD_MAX and f.count < MAX_COUNT


def cool_price(f: Fisher, now: datetime) -> int:
    return math.ceil(cd_left(f, now) / 60) * 3  # FishFrame.__coolCdHandler


def levels(templates: GameTemplates) -> dict[int, int]:
    return {int(r["Grades"]): int(r["Data"]) for r in templates.find("UpGradeTempInfos", Types=str(LEVEL_TYPE))}


def add_gp(f: Fisher, templates: GameTemplates, gp: int) -> None:
    """EXP do próximo nível = ``Data`` do grau seguinte (FishPoolInfo). (dedução) a barra recomeça ao subir."""
    table = levels(templates)
    f.gp += gp
    while (need := table.get(f.level + 1)) and f.gp >= need:
        f.gp -= need
        f.level += 1
    if f.level + 1 not in table:
        f.gp = min(f.gp, table.get(f.level, f.gp))


def pool_msg(f: Fisher, now: datetime, user_id: int, order: int, helpers: list[tuple[int, str]]) -> pb.FishPoolMsg:
    t = f.tools
    msg = pb.FishPoolMsg(userId=user_id, level=f.level, gp=f.gp, score=f.score, cd=cd_left(f, now), count=f.count,
                         maxCount=MAX_COUNT, tool1=t[0], tool2=t[1], tool3=t[2], tool4=t[3], hookState=f.hook,
                         order=order)  # fmt: skip
    for hid, nick in helpers:
        msg.fishplayers.add(helpId=hid, nickName=nick)
    return msg


# --- cardume ---------------------------------------------------------------------------------------------------


@dataclass
class Fish:
    template: int
    channel: int
    point: bool  # entra pela esquerda
    begin: int  # ms
    state: int = NORMAL
    back: int = 0  # ms em que volta (estado GONE)


@dataclass
class Pool:
    fish: dict[int, Fish] = field(default_factory=dict)
    hooked: set[int] = field(default_factory=set)  # op 11 [2, id]
    rage: tuple[int, int, int] | None = None  # (fishId, ângulo, quadro) do op 11 [1, ...]
    helpers: list[tuple[int, str]] = field(default_factory=list)


def ms(now: datetime) -> int:
    return int(now.timestamp() * 1000)


def kinds(templates: GameTemplates, channel: int, level: int) -> list[Row]:
    """Templates do canal liberados pelo nível. TODO(inventado): sorteio uniforme (a captura é toda de nível 0, e os
    7 templates de nível 0 saíram em quantidades parecidas)."""
    return [r for r in templates.rows("FishTemplateInfos")
            if int(r["ChannelIds"]) == channel and int(r["Level"]) <= level]  # fmt: skip


def travel(row: Row) -> int:
    """ms até sair do outro lado: (830 + Length) * 40 / Speed (bate com as medianas de 27/10: 1001 18000 x 18552,
    1003 9470 x 9717, 1011 18600 x 19192)."""
    return (POOL_WIDTH + int(row["Length"])) * 40 // max(1, int(row["Speed"]))


def spawn(templates: GameTemplates, channel: int, level: int, begin: int, rng: random.Random) -> Fish:
    row = rng.choice(kinds(templates, channel, level))
    state = RAGE if channel >= 4 and int(row["RageId1"]) and rng.random() < RAGE_CHANCE else NORMAL
    return Fish(int(row["TemplateId"]), channel, rng.random() < 0.5, begin, state)


def new_pool(templates: GameTemplates, level: int, now: datetime, rng: random.Random) -> Pool:
    t = ms(now)
    return Pool({fid: spawn(templates, ch, level, t + STAGGER * k, rng)
                 for ch, ids in SLOTS.items() for k, fid in enumerate(ids)})  # fmt: skip


def refresh(pool: Pool, templates: GameTemplates, level: int, now: datetime, rng: random.Random) -> None:
    """Quem já atravessou, foi pescado (5) ou voltou do torpedo nasce de novo agora (visto 27/10: o novo
    ``beginTime`` é o ``now`` do 4918 seguinte). O peixe da fúria em curso fica."""
    t = ms(now)
    for fid, f in pool.fish.items():
        row = templates.get("FishTemplateInfos", f.template)
        gone = f.state == CAUGHT or (f.state == GONE and t >= f.back)
        out = f.state in (NORMAL, RAGE) and row is not None and t >= f.begin + travel(row)
        if (gone or out) and not (pool.rage and pool.rage[0] == fid):
            pool.fish[fid] = spawn(templates, f.channel, level, t, rng)
            pool.hooked.discard(fid)


def infos_msg(pool: Pool, now: datetime) -> pb.FishInfosMsg:
    t = ms(now)
    msg = pb.FishInfosMsg()
    for fid, f in pool.fish.items():
        msg.fishs.add(fishId=fid, templateId=f.template, point=f.point, beginTime=f.begin, channelId=f.channel,
                      state=f.state, now=t)  # fmt: skip
    return msg


def torpedo(pool: Pool, tool: int, now: datetime) -> None:
    channels, back = TORPEDO[tool]
    for f in pool.fish.values():
        if f.channel in channels and f.state != CAUGHT:
            f.state, f.back = GONE, ms(now) + back


def catchable(pool: Pool, templates: GameTemplates, ids: list[int]) -> list[int]:
    """Peixes vivos, sem obstáculo (IsBlock), sem repetir."""
    out: list[int] = []
    for fid in ids:
        f = pool.fish.get(fid)
        row = templates.get("FishTemplateInfos", f.template) if f else None
        if f and row and f.state in (NORMAL, RAGE) and not int(row["IsBlock"]) and fid not in out:
            out.append(fid)
    return out
