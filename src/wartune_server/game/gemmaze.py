"""Labirinto de gemas (9508..9517): tabuleiro 5x5, troca de duas gemas vizinhas, combinação de 3 ou mais
na linha ou na coluna, gravidade e cascata. Só a regra: quem fala com o cliente é ``handlers/gemmaze.py``.

Fontes (só turco: a captura inglesa não abre o labirinto): *(visto)* ``av_askeri_ve_odul_toplama.json``: 7 trocas
e 10 passos (4923). Em cada troca,
a única vizinha que forma a combinação é a que o cliente mandou, e cada cascata bate com a gravidade
(``tests/game/test_labirinto_gemas.py``). *(visto)* replay_packets.json, personagem novo (4922): 20 movimentos, 5
ajudas, nível 0 e 0/30 de EXP. *(cliente)* ``GemMazeView.isUpon``: vizinho ortogonal, sem dar a volta na
linha; ``GemMazeView.updateMoveData``: o cliente faz a gravidade sozinho, então o servidor manda só as
gemas novas (``gemAdd``) e as que saíram (``gemDel``).
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from ..domain import gameday

SIZE = 5
CELLS = SIZE * SIZE
COLORS = 5  # cores 1..5; 0 = casa vazia
TIMES_START = 20  # (visto) movimentos do personagem novo
HELP_START = 5  # (visto) ajudas de amigos do personagem novo
MAX_EXP_START = 30  # (visto) EXP para o próximo nível no nível 0
# (visto) prêmios (item, quantidade) que saíram nos 10 passos da captura: 208014 vem sempre 2 por passo
# (115 com count 2 e 4, "Soul Crystal x 2"), os outros 1. Nenhum template liga prêmio a cor ou tamanho
# (a mesma cor 4 deu 208027 e 2060008), então o sorteio entre os três é dedução.
REWARDS = ((2060008, 1), (208027, 1), (208014, 2))
# (cliente) GemMazeBoxView.SORT_INDEX_ARRAY do CDN res134 (era 500/1000/2000/3500/6000): pontos de cada caixa
BOX_SCORES = (300, 700, 1600, 3500, 7000)
BOX_BITS = (1, 2, 4, 8, 16)  # (cliente) GemMazeBoxView.BOX_INDEX_ARR: o boxId do 9513 e o bit do boxMark
LINES = [[r * SIZE + c for c in range(SIZE)] for r in range(SIZE)] + [
    [r * SIZE + c for r in range(SIZE)] for c in range(SIZE)
]  # linhas e colunas, na ordem em que a combinação é lida


@dataclass
class Game:
    board: list[int]
    times: int = TIMES_START
    help: int = HELP_START
    level: int = 0
    exp: int = 0
    max_exp: int = MAX_EXP_START
    score: int = 0
    week: int = 0
    box: int = 0  # boxMark: bits das caixas já pegas
    day: str = ""  # dia (ISO) da última renovação; ver ``refresh``

    def dump(self) -> str:
        return json.dumps(
            {
                "board": "".join(str(g) for g in self.board),
                "times": self.times,
                "help": self.help,
                "level": self.level,
                "exp": self.exp,
                "max_exp": self.max_exp,
                "score": self.score,
                "week": self.week,
                "box": self.box,
                "day": self.day,
            },
            separators=(",", ":"),
        )

    @classmethod
    def load(cls, text: str) -> Game:
        d = json.loads(text)
        return cls(
            board=[int(ch) for ch in d["board"]],
            times=int(d["times"]),
            help=int(d["help"]),
            level=int(d["level"]),
            exp=int(d["exp"]),
            max_exp=int(d["max_exp"]),
            score=int(d["score"]),
            week=int(d["week"]),
            box=int(d.get("box", 0)),
            day=str(d.get("day", "")),
        )


def refresh(game: Game, now: datetime) -> None:
    """Renovação por dia: movimentos e ajudas voltam ao início, pontos e caixas zeram; o semanal zera na
    semana nova. Tabuleiro, nível e EXP ficam.

    *(dedução)*: na captura um personagem de nível 5 (61 EXP) abre com 20/20 movimentos, 5 ajudas e 0
    pontos, então algo renova; ``score`` e ``weekScore`` são campos separados, então ``score`` é do dia. *(cliente)*
    ``helpContent``: "Free and purchased attempts reset daily", "Points and attempts reset daily at 5 A.M."
    """
    today = gameday.game_day(now)
    if game.day == today.isoformat():
        return
    if not game.day or date.fromisoformat(game.day).isocalendar()[:2] != today.isocalendar()[:2]:
        game.week = 0
    game.times, game.help = TIMES_START, HELP_START
    game.score, game.box, game.day = 0, 0, today.isoformat()


@dataclass(frozen=True, slots=True)
class Step:
    """Um passo da cascata: o que sai (``gemDel``), o que entra no topo (``gemAdd``) e o ganho."""

    dels: tuple[int, ...]
    adds: tuple[tuple[int, int], ...]  # (marca, cor)
    points: int
    exp: int
    reward: int  # ``rewardInfo`` do passo: vai para a bolsa do labirinto
    count: int = 1  # quantidade do prêmio (``REWARDS``)


@dataclass(frozen=True, slots=True)
class Play:
    board: list[int]
    steps: tuple[Step, ...]
    times: int


def neighbors(a: int, b: int) -> bool:
    """Vizinhas na horizontal ou na vertical; a borda não dá a volta (como o cliente)."""
    return abs(a // SIZE - b // SIZE) + abs(a % SIZE - b % SIZE) == 1


def runs(board: list[int]) -> list[list[int]]:
    """Cada sequência de 3 ou mais iguais, inteira, na horizontal e na vertical."""
    out: list[list[int]] = []
    for line in LINES:
        i = 0
        while i < SIZE:
            j = i
            while j + 1 < SIZE and board[line[j + 1]] == board[line[i]] and board[line[i]]:
                j += 1
            if j - i + 1 >= 3:
                out.append(line[i : j + 1])
            i = j + 1
    return out


def fall(board: list[int], dels: Iterable[int]) -> list[int]:
    """Tira as marcas ``dels``; as gemas de cima descem na coluna e o topo fica vazio."""
    out = list(board)
    for m in dels:
        out[m] = 0
    for c in range(SIZE):
        col = [out[r * SIZE + c] for r in range(SIZE) if out[r * SIZE + c]]
        col = [0] * (SIZE - len(col)) + col
        for r in range(SIZE):
            out[r * SIZE + c] = col[r]
    return out


def _has_move(board: list[int]) -> bool:
    for a in range(CELLS):
        for b in (a + 1, a + SIZE):
            if b < CELLS and neighbors(a, b):
                swapped = list(board)
                swapped[a], swapped[b] = swapped[b], swapped[a]
                if runs(swapped):
                    return True
    return False


def new_game(rng: random.Random) -> Game:
    """Tabuleiro novo: sem combinação pronta e com ao menos uma troca que forma combinação.

    *(dedução)*: a captura só mostra tabuleiros assim (o da 4922 do login também não tem combinação).
    """
    while True:
        board: list[int] = []
        for i in range(CELLS):
            r, c = divmod(i, SIZE)
            taken = set()
            if c >= 2 and board[i - 1] == board[i - 2]:
                taken.add(board[i - 1])
            if r >= 2 and board[i - SIZE] == board[i - 2 * SIZE]:
                taken.add(board[i - SIZE])
            board.append(rng.choice([k for k in range(1, COLORS + 1) if k not in taken]))
        if _has_move(board):
            return Game(board=board)


def play(game: Game, begin: int, end: int, rng: random.Random, weights: Sequence[float] | None = None) -> Play | None:
    """Troca ``begin`` com ``end`` e resolve as combinações em cascata. ``weights``: peso de cada um de ``REWARDS``
    (``game_settings.gem_maze_reward_weights``, 0035); sem ele, uniforme.

    ``None``: pedido inválido (fora do tabuleiro, não vizinho ou sem movimento), nada muda.
    """
    if not (0 <= begin < CELLS and 0 <= end < CELLS) or not neighbors(begin, end) or game.times <= 0:
        return None
    board = list(game.board)
    board[begin], board[end] = board[end], board[begin]
    steps: list[Step] = []
    while found := runs(board):
        dels = sorted({m for run in found for m in run})
        # 3 em linha = 1 (10 pontos, 1 EXP), 4 = 2 (20, 2): captura. 5 ou mais é extrapolação.
        # ponytail: 5 ou mais em linha segue a conta de 3 e 4 (não foi capturado)
        units = sum(len(run) - 2 for run in found)
        board = fall(board, dels)
        adds: list[tuple[int, int]] = []
        for c in range(SIZE):
            for r in range(sum(1 for m in dels if m % SIZE == c)):
                color = rng.randint(1, COLORS)  # *(dedução)*: cor nova uniforme; a captura não mostra a regra
                board[r * SIZE + c] = color
                adds.append((r * SIZE + c, color))
        # ponytail: pesos dos três vistos no banco (padrão iguais); a tabela oficial precisa de captura
        reward, count = rng.choices(REWARDS, weights)[0] if weights else rng.choice(REWARDS)
        steps.append(Step(tuple(dels), tuple(adds), 10 * units, units, reward, count))
    # ponytail: troca sem combinação é aceita e gasta movimento (o cliente troca na tela e não desfaz;
    # a captura não tem esse caso, então o oficial pode devolver a gema). Confirmar gravando uma troca errada.
    return Play(board=board, steps=tuple(steps), times=game.times - 1)
