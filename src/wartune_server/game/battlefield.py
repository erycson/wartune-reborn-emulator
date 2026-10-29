"""Campo de batalha (campanhas 4005 e 4007) e a mina de amétista (30000): janela, nós, pontos e carrinhos.

Estado só em memória (como o chefe do mundo): o campo termina com a janela e o prêmio é gravado no personagem.
Fontes: as capturas oficiais de 24 a 27/10 (152321: 4005 #9474-#11671, 4007 #14230-#16396; mina #1917-#2312),
citadas em cada constante.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from typing import Any

from ..domain import gameday
from ..templates.repository import GameTemplates, Row
from .campaign import NORMAL

FIELDS = (4002, 4005, 4007)  # Campaigns Types 5 com OpenTime/StopTime (visto 152321 #9474, #14230; 121453 #8285)
MINE = 30000  # Campaigns Types 11, sem janela no template (visto #1917)
TEAM = 2  # o primeiro a entrar (visto 152321 #9477 e #14234 teamId 2)
ENEMY = 1
SIDES = (1, 2)  # 4252 one = time 1, two = time 2 (visto #9533: oneCount sobe com o Solo, time 1; #10096 two com o
# BooBoo3, time 2); o cliente (PvpMapTopCenterView) mostra "/ 15" por lado
SIDE_MAX = 15
INSIGNIA, SHARD = 208001, 208011  # ItemTempInfos "Insignia" e "Battleground Treasure Shard"
# fim (visto 152321 #11669): o lado vencedor 80 Insignia e 90 de honra (itemCount/winGesteCount), o perdedor 30 e 30
WIN_INSIGNIA, WIN_HONOR = 80, 90
LOSE_INSIGNIA, LOSE_HONOR = 30, 30
START_SCORE = 100  # pontos de quem entra (visto #9482 score 100; Luther e Solo com 100 no 4255 #9632)
# PvP (visto 152321): o perdedor perde 15% para cima (100->15 #9798, 115->18 #10274, 127->20 #10535; 29/10 #8689
# 110->17) e o vencedor ganha 20 + 1 a cada 20 pontos do perdedor (100->25 #9798, 115->25 #10274, 127->26 #10535,
# 30->21 #11100, 72->23 #11248) e 10 de honra (#11126 geste 862->872)
LOSS_PCT, GAIN_BASE, GAIN_STEP, KILL_HONOR = 15, 20, 20, 10
# entrega (visto #14418, #14517, #15122): pontos, honra e shards por qualidade do minério
TURN_IN = {"superior": (30, 3, 3), "normal": (20, 2, 2), "inferior": (10, 1, 1)}
QUALITIES = ("superior", "normal", "inferior")
# a qualidade sai na coleta, não no nó: o mesmo 4007007 deu inferior, superior e normal (#14517, #14611, #15122);
# o peso de cada uma vem de ``taxas.field_ore_weights`` (0140)
COLLECT = (5, 6, 7, 8, 9)  # nós 91/2380 (visto #9478)
DELIVER = {1: 11, 2: 12}  # "Resource Recovery Officer" de cada lado (param1 = time, visto #9478)
CAMP = {1: (179, 75), 2: (17, 76)}  # nascer e renascer: nós 001/002 (param1 = time); visto #9477, #9795, #9653
# guardiões vivos (state 1) na entrada: no 4002 os do time 2 (13-18, visto 121453 #8292); no 4005/4007 todos 8
# (152321 #9478, #14235). Um vivo persegue o inimigo que chega perto e puxa luta (visto #10205-#10341).
ALIVE_GUARDIANS: dict[int, tuple[int, ...]] = {4002: (13, 14, 15, 16, 17, 18)}
GUARDIAN_BATTLE = 32  # 157 battleType 32 e 4103 battleScene 11, como o PvP (visto #10211, #10336)
EXIT_GATES = (121, 122)  # morto não sai (visto #9840 "You cannot leave camp when dead!")
# mina (visto #1923-#2312): o carrinho sai no nó 3, a coleta é o nó 6 e o minério é o nó 9
CART_NODE, PICK_NODE, ORE_NODE = 3, 6, 9
CARTS_ADV = 1  # quality do carrinho avançado (visto "You received a Adv. Minecart." e quality 1, #1956)
# fora da janela o carrinho é o comum (CART_BODY: "Adv. Minecarts are available daily from 19:30-20:00");
# TODO(inventado): quality 0 para ele
CART_NORMAL = 0
PICKS_PER_CART = 5  # (visto #2135) "Collection complete. (4 / 5) collections remaining."
MINE_WINDOW = (time(19, 30), time(20, 0))  # texto do carrinho (visto #1962), horário do servidor
TOP = 3
TILE = 20
START = (44, 80)  # entrada da mina; TODO(inventado): a mina não tem posição de entrada vista
CART_POS, MINE_PICK_POS, ORE_POS = (30, 30), (34, 34), (40, 40)  # TODO(inventado): posições da mina


def pvp_loss(score: int) -> int:
    return -(-score * LOSS_PCT // 100)


def pvp_gain(loser_score: int) -> int:
    return GAIN_BASE + loser_score // GAIN_STEP


def ore(weights: dict[str, int], rng: random.Random | None = None) -> str:
    """A qualidade do minério de uma coleta, pelos pesos de ``taxas.field_ore_weights``."""
    names = [q for q in QUALITIES if weights.get(q, 0) > 0] or list(QUALITIES)
    return (rng or random).choices(names, [weights.get(q, 1) for q in names])[0]


@dataclass
class Mark:
    """Um jogador no campo: pontos pessoais, honra do campo e o minério que carrega (``None`` = nenhum)."""

    score: int = START_SCORE
    honor: int = 0
    carry: str | None = None
    wins: int = 0  # abates no PvP do campo (hitCount do 4252/4255)
    team: int = TEAM  # lado no campo (teamId do 4252/4255)
    fighting: bool = False  # numa luta do 8334 (4494 state 2)
    dead: bool = False  # esperando renascer (4175 state 1/3)
    name: str = ""  # nickName do 4255/4254 (visto #9632: todos com nome)
    server: str = ""


@dataclass
class Field:
    """Uma partida: a janela (abertura), quem já entrou (na ordem de chegada, como o 4255 #9632) e os pontos de
    cada lado. ``settled``: o fim já foi pago."""

    campaign_id: int
    opened: datetime
    marks: dict[int, Mark] = field(default_factory=dict)
    points: dict[int, int] = field(default_factory=lambda: dict.fromkeys(SIDES, 0))
    busy: set[int] = field(default_factory=set)  # guardiões numa luta (128 nodeState 4)
    settled: bool = False

    def mark(self, player_id: int) -> Mark:
        """A marca do jogador; quem chega entra no lado com menos gente, empate no 2 (coerente com #9482, #9533,
        #10096 e #10220). TODO(inventado): a regra do oficial (ele cruza servidores)."""
        if player_id not in self.marks:
            one, two = self.count(1), self.count(2)
            self.marks[player_id] = Mark(team=1 if one < two else TEAM)
        return self.marks[player_id]

    def score(self, team: int) -> int:
        """Pontos do lado: só sobem com as entregas e os ganhos no PvP (visto #9798: a perda não desconta; #9533 e
        #10096: a entrada não soma)."""
        return self.points.get(team, 0)

    def gain(self, team: int, points: int) -> None:
        self.points[team] = self.points.get(team, 0) + points

    def count(self, team: int) -> int:
        return sum(m.team == team for m in self.marks.values())

    def winner(self) -> int | None:
        """O lado com mais pontos no fim (visto #11669: 2455 x 2448, o time 2 com 80/90).
        TODO(inventado): empate sem vencedor (as duas partidas vistas tiveram vencedor)."""
        one, two = self.score(1), self.score(2)
        return None if one == two else 1 if one > two else 2


@dataclass
class Cart:
    """Carrinho da mina de um jogador: qualidade, coletas feitas e minério carregado."""

    quality: int = CARTS_ADV
    picks: int = 0


@dataclass
class WarFields:
    """Estado da memória: a partida de hoje de cada campo e os carrinhos da mina por jogador."""

    fields: dict[int, Field] = field(default_factory=dict)
    carts: dict[int, Cart] = field(default_factory=dict)


def _hm(text: str) -> time:
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def row_window(row: Row, now: datetime) -> tuple[datetime, datetime]:
    """Abertura e fechamento de hoje do campo (``OpenTime``/``StopTime`` no fuso do jogo), em UTC."""
    day = gameday.local(now)
    opened, stop = _hm(row["OpenTime"]), _hm(row["StopTime"])
    start = day.replace(hour=opened.hour, minute=opened.minute, second=0, microsecond=0)
    end = day.replace(hour=stop.hour, minute=stop.minute, second=0, microsecond=0)
    return start.astimezone(UTC), end.astimezone(UTC)


def field_row(templates: GameTemplates, campaign_id: int) -> Row | None:
    return next(templates.find("Campaigns", CampaignId=campaign_id, Types=5), None)


def state(row: Row, now: datetime) -> int:
    """0 aberto, 1 ainda não abriu hoje, 2 encerrado hoje (o que o 4248 do cliente lê)."""
    opened, stop = row_window(row, now)
    if now < opened:
        return 1
    return 0 if now < stop else 2


def is_open(row: Row, now: datetime) -> bool:
    return state(row, now) == 0


def mine_open(now: datetime) -> bool:
    """Carrinho avançado só no horário do texto da mina (visto #1962 e #2094)."""
    local = gameday.local(now).time()
    return MINE_WINDOW[0] <= local < MINE_WINDOW[1]


def current_field(ctx_fields: WarFields, campaign_id: int, opened: datetime) -> Field:
    """A partida da janela ``opened``; uma janela nova (outro dia) começa do zero."""
    cur = ctx_fields.fields.get(campaign_id)
    if cur is None or cur.opened != opened:
        cur = ctx_fields.fields[campaign_id] = Field(campaign_id, opened)
    return cur


# os 28 nós do 127 (visto 152321 #9478 no 4005 e #14235 no 4007, iguais): n, nome, masterType, sonType, state, x, y,
# resource, heroTempId, handlerRange, param1, param2, attackTypes, nameColor, toward, resetX, resetY, fixX, fixY
FIELD_NODES: tuple[tuple[Any, ...], ...] = (
    (1, "", 40, 2301, 2, 179, 75, 2, -1, 0, 1, 0, 0, 0, 0, 0, 0, 3590, 1507),
    (2, "", 40, 2301, 2, 17, 76, 2, -1, 0, 2, 0, 0, 0, 0, 0, 0, 349, 1529),
    (3, "", 53, 2375, 8, 38, 73, 2, -1, 0, 2, 0, 0, 0, 0, 34, 73, 769, 1469),
    (4, "", 53, 2375, 8, 165, 78, 2, -1, 0, 1, 0, 0, 0, 0, 169, 78, 3310, 1571),
    (5, "", 91, 2380, 1, 105, 78, 2, -1, 0, 0, 0, 0, 0, 0, 104, 79, 2109, 1569),
    (6, "", 91, 2380, 1, 107, 85, 2, -1, 0, 0, 0, 0, 0, 0, 106, 86, 2148, 1709),
    (7, "", 91, 2380, 1, 90, 83, 2, -1, 0, 0, 0, 0, 0, 0, 90, 82, 1808, 1671),
    (8, "", 91, 2380, 1, 89, 73, 2, -1, 0, 0, 0, 0, 0, 0, 90, 72, 1789, 1470),
    (9, "", 91, 2380, 1, 89, 66, 2, -1, 0, 0, 0, 0, 0, 0, 90, 65, 1788, 1328),
    (11, "Resource Recovery Officer", 161, 2175, 1, 156, 90, 1, 24999, 1, 1, 0, 0, 1, 180, 156, 86, 3128, 1809),
    (12, "Resource Recovery Officer", 161, 2409, 1, 44, 83, 1, 25000, 1, 2, 0, 0, 5, 0, 44, 80, 888, 1669),
    (13, "Knight Guardian", 42, 2124, 8, 51, 59, 1, 25001, 0, 2, 1, 1, 5, 0, 0, 0, 1029, 1188),
    (14, "Gryphon Guardian", 42, 2118, 8, 57, 44, 1, 25002, 0, 2, 1, 1, 5, 0, 0, 0, 1149, 890),
    (15, "Paladin Guardian", 42, 2125, 8, 72, 32, 1, 25003, 0, 2, 1, 1, 5, 0, 0, 0, 1448, 651),
    (16, "Knight Guardian", 42, 2124, 8, 52, 86, 1, 25004, 0, 2, 1, 1, 5, 0, 0, 0, 1049, 1729),
    (17, "Gryphon Guardian", 42, 2118, 8, 54, 102, 1, 25005, 0, 2, 1, 1, 5, 0, 0, 0, 1088, 2049),
    (18, "Paladin Guardian", 42, 2125, 8, 58, 116, 1, 25006, 0, 2, 1, 1, 5, 0, 0, 0, 1168, 2331),
    (19, "Morkan Bombardier", 42, 2158, 8, 130, 37, 1, 25007, 0, 1, 1, 1, 1, 180, 0, 0, 2608, 751),
    (20, "Morkan Archer", 42, 2156, 8, 144, 49, 1, 25008, 0, 1, 1, 1, 1, 180, 0, 0, 2889, 989),
    (21, "Morkan Knight", 42, 2157, 8, 143, 66, 1, 25009, 0, 1, 1, 1, 1, 180, 0, 0, 2870, 1329),
    (22, "Morkan Knight", 42, 2157, 8, 144, 98, 1, 25010, 0, 1, 1, 1, 1, 180, 0, 0, 2890, 1970),
    (23, "Morkan Archer", 42, 2156, 8, 147, 111, 1, 25011, 0, 1, 1, 1, 1, 180, 0, 0, 2948, 2231),
    (24, "Morkan Bombardier", 42, 2158, 8, 131, 119, 1, 25012, 0, 1, 1, 1, 1, 180, 0, 0, 2629, 2389),
    (121, "", 121, 2375, 9, 165, 78, 2, -1, 0, 1, 0, 0, 0, 0, 169, 78, 3310, 1571),
    (122, "", 121, 2375, 9, 38, 73, 2, -1, 0, 2, 0, 0, 0, 0, 34, 73, 768, 1469),
    (123, "", 131, 2375, 9, 38, 73, 2, -1, 0, 2, 0, 0, 0, 0, 42, 73, 769, 1469),
    (124, "", 131, 2375, 9, 165, 78, 2, -1, 0, 1, 0, 0, 0, 0, 161, 78, 3427, 1534),
)


def field_nodes(campaign_id: int) -> dict[int, dict[str, Any]]:
    """Os nós do 127 do campo, como vieram (``FIELD_NODES``); ``nodeId`` = ``campDataId`` (o oficial numera à parte,
    19791-19817, e o cliente só os cruza entre si)."""
    base = campaign_id * 1000
    out = {}
    alive = ALIVE_GUARDIANS.get(campaign_id, ())
    for n, name, master, son, st, x, y, res, hero, rng, p1, p2, attack, color, toward, rx, ry, fx, fy in FIELD_NODES:
        st = 1 if n in alive else st
        out[base + n] = {
            "nodeId": base + n, "campDataId": base + n, "nodeName": name, "masterType": master, "sonType": son,
            "preNodeIds": "0", "nextNodeIds": "", "state": st, "refreshSpeed": 1, "posX": x, "posY": y,
            "curX": x, "curY": y, "level": 0, "styleType": 1, "attackTypes": attack, "nameColor": color,
            "sizeType": 0, "toward": toward, "resource": res, "resetX": rx, "resetY": ry, "fixX": fx, "fixY": fy,
            "heroTempId": hero, "handlerRange": rng, "fightCapaity": 0, "param1": p1, "param2": p2, "param3": "",
            "param4": "", "param5": "",
        }  # fmt: skip
    return out


def mine_nodes() -> dict[int, dict[str, Any]]:
    """Os nós da mina (visto #1921 e #2093-#2134): o minério (9, sonType 2351), o carrinho e a coleta."""
    base = MINE * 100

    def node(n: int, master: int, son: int, pos: tuple[int, int], name: str) -> dict[str, Any]:
        x, y = pos
        return {
            "nodeId": base + n, "campDataId": base + n, "nodeName": name, "masterType": master, "sonType": son,
            "preNodeIds": "0", "nextNodeIds": "", "state": NORMAL, "refreshSpeed": 1, "posX": x, "posY": y,
            "curX": x, "curY": y, "level": 0, "styleType": 1, "attackTypes": 0, "nameColor": 0, "sizeType": 0,
            "toward": 0, "resource": 2, "resetX": 0, "resetY": 0, "fixX": x * TILE + 9, "fixY": y * TILE + 9,
            "heroTempId": -1, "handlerRange": 0, "fightCapaity": 0, "param1": 0, "param2": 0, "param3": "",
            "param4": "", "param5": "",
        }  # fmt: skip

    nodes = [
        node(ORE_NODE, 91, 2351, ORE_POS, "Amethyst Ore"),
        node(CART_NODE, 92, 2352, CART_POS, "Minecart Dispatcher"),  # TODO(inventado): tipo do carrinho
        node(PICK_NODE, 91, 2350, MINE_PICK_POS, "Amethyst Pile"),  # TODO(inventado): tipo da coleta
    ]
    return {n["campDataId"]: n for n in nodes}


def turn_in_text(quality: str, points: int, honor: int, shards: int) -> str:
    return (f"You've turned in {quality} and have received: {points} Points and {honor} Honor and "
            f"Battleground Treasure Shard x{shards}")  # fmt: skip


def win_text(insignia: int = WIN_INSIGNIA, honor: int = WIN_HONOR) -> str:
    return f"The battle has ended! You received Insignia x{insignia} and honor x{honor}! "
