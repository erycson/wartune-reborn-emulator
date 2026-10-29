"""Campo de batalha (campanhas 4005 e 4007) e a mina de amétista (30000): janela, nós, pontos e carrinhos.

Estado só em memória (como o chefe do mundo): o campo termina com a janela e o prêmio é gravado no personagem.
Sem outros servidores, o campo tem só a nossa equipe (time 2, visto #14238); o time 1 fica sem pontos.
Fontes: as capturas oficiais de 24 a 27/10 (campo #9474-#16437, mina #1917-#2312), citadas em cada constante.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from typing import Any

from ..domain import gameday
from ..templates.repository import GameTemplates, Row
from .campaign import NORMAL

FIELDS = (4005, 4007)  # Campaigns Types 5 com OpenTime/StopTime (visto #9474 e #14230)
MINE = 30000  # Campaigns Types 11, sem janela no template (visto #1917)
TEAM = 2  # time do nosso jogador (visto #14238 teamId 2)
ENEMY = 1
INSIGNIA, SHARD = 208001, 208011  # ItemTempInfos "Insignia" e "Battleground Treasure Shard"
WIN_INSIGNIA, WIN_HONOR = 80, 90  # (visto #16396) "You received Insignia x80 and honor x90!"
# entrega (visto #14418, #14517, #15122): pontos, honra e shards por qualidade do minério
TURN_IN = {"superior": (30, 3, 3), "normal": (20, 2, 2), "inferior": (10, 1, 1)}
# nó de coleta do campo, pelo sufixo do campDataId (4007006 superior visto #14330-#14418)
COLLECT = {6: "superior", 7: "normal", 8: "inferior"}  # TODO(inventado): 7 e 8 não vistos como entrega
DELIVER, DECOR = 12, 24  # campDataId = campanha * 1000 + n (visto 4005012, 4007012, 4007024)
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
# posição de entrada e de entrega (visto #14389 STANDPOS 44,80); os nós de coleta sem posição vista: TODO(inventado)
START = (44, 80)
COLLECT_POS = {6: (60, 60), 7: (70, 50), 8: (50, 70)}  # TODO(inventado): posições dos nós de coleta
CART_POS, MINE_PICK_POS, ORE_POS = (30, 30), (34, 34), (40, 40)  # TODO(inventado): posições da mina


@dataclass
class Mark:
    """Um jogador no campo: pontos pessoais, honra e o minério que carrega (``None`` = nenhum)."""

    score: int = 0
    honor: int = 0
    carry: str | None = None
    wins: int = 0  # vitórias no PvP do campo (hitCount do 4252)
    team: int = TEAM  # lado no campo (teamId do 4252/4255)
    fighting: bool = False  # numa luta do 8334 (4494 state 2)


@dataclass
class Field:
    """Uma partida: a janela (abertura) e quem já entrou. ``settled``: o fim já foi pago."""

    campaign_id: int
    opened: datetime
    marks: dict[int, Mark] = field(default_factory=dict)
    settled: bool = False

    def mark(self, player_id: int) -> Mark:
        """A marca do jogador; quem chega entra no lado com menos gente (o primeiro no 2, visto #14238).
        TODO(inventado): o equilíbrio dos lados (o oficial cruza servidores; não há captura de dois lados)."""
        if player_id not in self.marks:
            ours = sum(m.team == TEAM for m in self.marks.values())
            self.marks[player_id] = Mark(team=TEAM if ours <= len(self.marks) - ours else ENEMY)
        return self.marks[player_id]

    def score(self, team: int) -> int:
        return sum(m.score for m in self.marks.values() if m.team == team)

    def count(self, team: int) -> int:
        return sum(m.team == team for m in self.marks.values())

    def winner(self) -> int | None:
        """O lado com mais pontos no fim; empate (ou ninguém pontuou) não tem vencedor."""
        ours, theirs = self.score(TEAM), self.score(ENEMY)
        return None if ours == theirs else TEAM if ours > theirs else ENEMY


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


def field_nodes(campaign_id: int) -> dict[int, dict[str, Any]]:
    """Os nós do 127 do campo (visto #9478, #14235): a decoração, a entrega e as coletas."""
    base = campaign_id * 1000

    def node(n: int, master: int, son: int, pos: tuple[int, int], name: str = "", **extra: Any) -> dict[str, Any]:
        x, y = pos
        return {
            "nodeId": base + n, "campDataId": base + n, "nodeName": name, "masterType": master, "sonType": son,
            "preNodeIds": "0", "nextNodeIds": "", "state": NORMAL, "refreshSpeed": 1, "posX": x, "posY": y,
            "curX": x, "curY": y, "level": 0, "styleType": 1, "attackTypes": 0, "nameColor": 0, "sizeType": 0,
            "toward": 0, "resource": 2, "resetX": 0, "resetY": 0, "fixX": x * TILE + 9, "fixY": y * TILE + 9,
            "heroTempId": -1, "handlerRange": 0, "fightCapaity": 0, "param1": 0, "param2": 0, "param3": "",
            "param4": "", "param5": "", **extra,
        }  # fmt: skip

    nodes = [node(DECOR, 42, 2158, (131, 119), "Morkan Bombardier")]  # visto #9478 (sonType 2158)
    nodes.append(node(DELIVER, 40, 2301, START, "Delivery Point"))  # TODO(inventado): nome e tipo da entrega
    nodes += [node(n, 91, 2350 + (n % 2), pos, "Battleground Resource", resource=1) for n, pos in COLLECT_POS.items()]
    return {n["campDataId"]: n for n in nodes}


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


def win_text(insignia: int = WIN_INSIGNIA) -> str:
    honor = WIN_HONOR * insignia // WIN_INSIGNIA
    return f"The battle has ended! You received Insignia x{insignia} and honor x{honor}! "
