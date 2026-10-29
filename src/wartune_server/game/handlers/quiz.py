"""Quiz (9501 ``AnswerquestionReqMsg {type, count}``; 4907 jogador, 4908 estado, 4909 pergunta, 4910 os 10 primeiros).
Edição em ``game_settings.quiz``; sem ela, fechado (4908 ``sysState`` 0).

Idioma (``answer.view.helpHtmlTxt``): segunda, quarta e sexta, 19:30-20:00; 5 s para ler, 15 s para responder, a
resposta sai em 5 s; pontos pelo acerto e pelo tempo que sobrou, 1 ponto no erro ou sem resposta; três ajudas (VIP
ganha mais); no fim EXP pelos pontos e EXP extra para os 10 primeiros (``answer.view.rewards1``).

Cliente (``AnswerManager``, ``AnswerModel``), nível 30:

- ``sysState`` 1 antes do começo, 2 lendo, 3 respondendo, 4 resultado, 5 acabou; ``lastDate`` ms até a fase
  seguinte, ``sysAnswerCount``/``leftCount`` total e restantes;
- 4909 com ``id`` novo é a pergunta (o cliente embaralha as 4 opções; ``answer`` 0); com o mesmo ``id``: na fase 4 o
  ``answer`` é a certa (1-4), nas fases 2/3 é a ajuda (< 10 a certa, coração; > 10 os dígitos das erradas que somem,
  olho);
- pedidos: ``type`` 1 ``count`` 11/12 abre/fecha a tela, 2 ajuda (21 dobro, 22 coração, 23 olho), 3 a opção (1-4).

Banca: nem o cliente nem a internet trazem perguntas com resposta (``HeartTempInfos`` é o jogo do casamento, sem
certa). TODO(inventado): a banca ``QUESTIONS`` (a ``Option1`` é a certa: o cliente embaralha), 20 perguntas,
pontos (10 + segundos que sobraram, dobro com 21), uma ajuda de cada (duas com VIP), EXP no fim (pontos x nível x
10; extra (11 - posição) x nível x 100) só para quem está online, e o estado 1 a partir de 30 min antes.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...domain import gameday
from ...protocol.messages import wartune_pb2 as pb
from .. import rewards
from ..builders import login as b
from ..router import router
from ..session import GameContext, GameSession
from . import minijogo as mj

S_PLAYER, S_STATE, S_QUESTION, S_RANK = 4907, 4908, 4909, 4910
KEY = "quiz"
OPEN_GRADE = 30
UI, ITEM, ANSWER = 1, 2, 3
UI_OPEN, UI_CLOSE = 11, 12
DOUBLE, HEART, EYES = 21, 22, 23
CLOSED, READY, READ, ASK, RESULT, END = range(6)
READ_S, ASK_S, RESULT_S = 5, 15, 5
CYCLE = READ_S + ASK_S + RESULT_S
DEFAULTS: dict[str, Any] = {"weekdays": [0, 2, 4], "start": "19:30", "minutes": 30, "count": 20, "readyMinutes": 30}
# TODO(inventado): banca (pergunta, certa, três erradas)
QUESTIONS = [
    ("How many players can join a party?", "3", "2", "5", "10"),
    ("Which currency is used to buy items in the Mall?", "Balens", "Gold", "Daru", "Kyanite"),
    ("What do you need to learn hero skills?", "Daru", "Gold", "Kyanite", "Balens"),
    ("Which building trains troops?", "Barracks", "Temple", "Fountain", "Tavern"),
    ("Which building produces gold?", "Houses", "Barracks", "Wall", "Tavern"),
    ("How many days does a week have?", "7", "5", "6", "8"),
    ("What color is the sky on a clear day?", "Blue", "Green", "Red", "Purple"),
    ("How many hours are in a day?", "24", "12", "20", "36"),
    ("Which animal is known as the king of the jungle?", "Lion", "Tiger", "Wolf", "Bear"),
    ("Which planet is closest to the Sun?", "Mercury", "Venus", "Earth", "Mars"),
    ("How many legs does a spider have?", "8", "6", "10", "4"),
    ("What is frozen water called?", "Ice", "Steam", "Fog", "Dew"),
    ("Which is the largest ocean?", "Pacific", "Atlantic", "Indian", "Arctic"),
    ("How many minutes are in an hour?", "60", "100", "30", "90"),
    ("Which metal is liquid at room temperature?", "Mercury", "Iron", "Copper", "Silver"),
    ("What do bees make?", "Honey", "Milk", "Silk", "Wax paper"),
    ("Which season comes after winter?", "Spring", "Summer", "Autumn", "Winter"),
    ("How many sides does a triangle have?", "3", "4", "5", "6"),
    ("What is the opposite of victory?", "Defeat", "Triumph", "Glory", "Honor"),
    ("Which gas do plants absorb?", "Carbon dioxide", "Oxygen", "Helium", "Neon"),
]


@dataclass
class Player:
    nick: str
    score: int = 0
    right: int = 0
    helps: dict[int, int] = field(default_factory=dict)
    choice: int = 0  # opção da pergunta atual (0 = nenhuma)
    left: int = 0  # segundos que sobravam ao responder
    double: bool = False
    heart: bool = False
    exp: int = 0
    extra: int = 0


@dataclass
class Edition:
    start: datetime
    players: dict[int, Player] = field(default_factory=dict)
    watching: set[int] = field(default_factory=set)
    phase: tuple[int, int] = (CLOSED, -1)
    paid: bool = False


_editions: dict[int, Edition] = {}  # por id do GameContext (um por servidor)
_tickers: dict[int, asyncio.Task[None]] = {}


def _cfg(s: GameSession | GameContext) -> dict[str, Any]:
    world = s.world if isinstance(s, GameContext) else s.ctx.world
    c = world.settings.get(KEY) or {}
    return {**DEFAULTS, **c} if c else {}


def _questions(c: dict[str, Any]) -> list[Any]:
    bank = c.get("questions") or QUESTIONS
    return list(bank)[: int(c["count"])]


def _start(c: dict[str, Any], now: datetime) -> datetime | None:
    """Começo da edição de hoje (hora do jogo), se hoje é dia de quiz."""
    local = gameday.local(now)
    hour, minute = (int(x) for x in str(c["start"]).split(":"))
    if local.weekday() not in c["weekdays"]:
        return None
    return local.replace(hour=hour, minute=minute, second=0, microsecond=0)


def phase(c: dict[str, Any], now: datetime) -> tuple[int, int, int]:
    """(``sysState``, pergunta, ms até a fase seguinte)."""
    start = _start(c, now) if c else None
    if start is None:
        return CLOSED, -1, 0
    t = (gameday.local(now) - start).total_seconds()
    count = len(_questions(c))
    if -int(c["readyMinutes"]) * 60 <= t < 0:
        return READY, -1, int(-t * 1000)
    if 0 <= t < count * CYCLE:
        q, r = int(t // CYCLE), t % CYCLE
        if r < READ_S:
            return READ, q, int((READ_S - r) * 1000)
        if r < READ_S + ASK_S:
            return ASK, q, int((READ_S + ASK_S - r) * 1000)
        return RESULT, q, int((CYCLE - r) * 1000)
    if 0 <= t < int(c["minutes"]) * 60:
        return END, count - 1, int((int(c["minutes"]) * 60 - t) * 1000)
    return CLOSED, -1, 0


def _edition(ctx: GameContext, c: dict[str, Any], now: datetime) -> Edition | None:
    start = _start(c, now) if c else None
    if start is None:
        return None
    ed = _editions.get(id(ctx))
    if ed is None or ed.start != start:
        ed = _editions[id(ctx)] = Edition(start)
    return ed


def _state_msg(c: dict[str, Any], now: datetime) -> pb.SysAnswerQuestionStateMsg:
    state, q, ms = phase(c, now)
    count = len(_questions(c)) if c else 0
    msg = pb.SysAnswerQuestionStateMsg(sysState=state, sysAnswerCount=count, leftCount=max(count - q - 1, 0))
    msg.lastDate, msg.beginDate = str(ms), str(int(_start(c, now).timestamp())) if state else "0"  # type: ignore[union-attr]
    return msg


def _question(c: dict[str, Any], q: int, answer: int = 0) -> pb.singleranswerquestionMsg:
    text, *options = _questions(c)[q]
    return pb.singleranswerquestionMsg(id=q + 1, question=text, option1=options[0], option2=options[1],
                                       option3=options[2], option4=options[3], answer=answer)  # fmt: skip


def _ranking(ed: Edition) -> list[tuple[int, Player]]:
    return sorted(ed.players.items(), key=lambda kv: (-kv[1].score, kv[0]))


def _player_msg(ed: Edition, pid: int) -> pb.playeranswerquestionMsg:
    p = ed.players[pid]
    order = next(i for i, (k, _) in enumerate(_ranking(ed), start=1) if k == pid)
    return pb.playeranswerquestionMsg(
        userId=pid, curOrder=order, currentScore=p.score, getEXP=p.exp, playerAnswerSucCount=p.right,
        doubleBlessCount=p.helps[DOUBLE], wisdomHeartCount=p.helps[HEART], choiceEyesCount=p.helps[EYES],
        extraEXP=p.extra,
    )  # fmt: skip


def _rank_msg(ed: Edition) -> pb.TenAnswerQuestionOrderMsg:
    msg = pb.TenAnswerQuestionOrderMsg()
    for i, (pid, p) in enumerate(_ranking(ed)[:10], start=1):
        msg.tenAQ_Info.add(userId=pid, nickName=p.nick, curOrder=i, currentScore=p.score)
    return msg


def _join(s: GameSession, ed: Edition) -> Player:
    from .vip import vip_grade  # noqa: PLC0415  (vip importa handlers que importam este)

    snap = s.snapshot
    assert snap is not None
    if s.player_id not in ed.players:
        n = 2 if vip_grade(s, snap) > 0 else 1
        ed.players[s.player_id] = Player(snap.character.nickname or "", helps={DOUBLE: n, HEART: n, EYES: n})
    return ed.players[s.player_id]


@router.on(9501)
async def quiz(s: GameSession, msg: pb.AnswerquestionReqMsg) -> None:
    c, now, snap = _cfg(s), s.ctx.clock.now(), s.snapshot
    assert snap is not None
    state, q, _ = phase(c, now)
    ed = _edition(s.ctx, c, now)
    if ed is None or state == CLOSED or snap.character.grades < OPEN_GRADE:
        s.send(S_STATE, b.complete(pb.SysAnswerQuestionStateMsg(sysState=CLOSED)))
        return
    if msg.type == UI and msg.count == UI_CLOSE:
        ed.watching.discard(s.player_id)
        return
    p = _join(s, ed)
    if msg.type == UI:
        ed.watching.add(s.player_id)
        _ensure_ticker(s.ctx)
        s.send(S_STATE, b.complete(_state_msg(c, now)))
        if q >= 0:
            s.send(S_QUESTION, b.complete(_question(c, q, _correct(q) if state >= RESULT else 0)))
        s.send(S_PLAYER, b.complete(_player_msg(ed, s.player_id)))
        s.send(S_RANK, b.complete(_rank_msg(ed)))
    elif msg.type == ANSWER and state == ASK and p.choice == 0 and 1 <= msg.count <= 4:
        p.choice, p.left = msg.count, int(phase(c, now)[2] // 1000)
    elif msg.type == ITEM and p.helps.get(msg.count, 0) > 0 and state in (READ, ASK):
        if msg.count == DOUBLE and not p.double:
            p.double = True
        elif msg.count == HEART and state == ASK and p.choice == 0:
            p.heart, p.choice, p.left = True, _correct(q), int(phase(c, now)[2] // 1000)
            s.send(S_QUESTION, b.complete(_question(c, q, _correct(q))))
        elif msg.count == EYES and state == ASK:
            s.send(S_QUESTION, b.complete(_question(c, q, _wrong(q) * 10)))
        else:
            return
        p.helps[msg.count] -= 1
        s.send(S_PLAYER, b.complete(_player_msg(ed, s.player_id)))
    else:
        s.log.info("9501 recusado", tipo=msg.type, valor=msg.count, estado=state)


def _correct(q: int) -> int:
    return 1  # a Option1 é a certa (o cliente embaralha as opções)


def _wrong(q: int) -> int:
    return 2 + q % 3  # TODO(inventado): qual errada o olho apaga


def _ensure_ticker(ctx: GameContext) -> None:
    task = _tickers.get(id(ctx))
    if task is None or task.done():
        _tickers[id(ctx)] = asyncio.get_running_loop().create_task(_loop(ctx))


async def _loop(ctx: GameContext) -> None:
    with contextlib.suppress(asyncio.CancelledError):
        while True:
            await asyncio.sleep(1)
            if not await tick(ctx):
                return


async def tick(ctx: GameContext) -> bool:
    """Uma volta do relógio do quiz: manda as mudanças de fase a quem está com a tela aberta, pontua no resultado e
    paga a EXP no fim. False quando a edição acabou (o laço para)."""
    c, now = _cfg(ctx), ctx.clock.now()
    state, q, _ = phase(c, now)
    ed = _edition(ctx, c, now)
    if ed is None:
        return False
    if (state, q) == ed.phase:
        return state != CLOSED
    ed.phase = (state, q)
    if state == RESULT:
        for p in ed.players.values():
            ok = p.choice == _correct(q)
            p.score += (10 + p.left) * (2 if p.double else 1) if ok else 1
            p.right += ok
    elif state == READ:
        for p in ed.players.values():
            p.choice, p.left, p.double, p.heart = 0, 0, False, False
    watchers = [o for pid in ed.watching if (o := ctx.online.get(pid)) is not None]
    for o in watchers:
        o.send(S_STATE, b.complete(_state_msg(c, now)))
        if state == READ:
            o.send(S_QUESTION, b.complete(_question(c, q)))
        elif state == RESULT:
            o.send(S_QUESTION, b.complete(_question(c, q, _correct(q))))
            o.send(S_PLAYER, b.complete(_player_msg(ed, o.player_id)))
            o.send(S_RANK, b.complete(_rank_msg(ed)))
    if state == END and not ed.paid:
        ed.paid = True
        await _pay(ctx, ed)
    return state not in (CLOSED,)


async def _pay(ctx: GameContext, ed: Edition) -> None:
    for order, (pid, p) in enumerate(_ranking(ed), start=1):
        o = ctx.online.get(pid)
        if o is None or o.snapshot is None:
            continue  # TODO(inventado): quem saiu antes do fim fica sem EXP
        grade = o.snapshot.character.grades
        p.exp = p.score * grade * 10
        p.extra = (11 - order) * grade * 100 if order <= 10 else 0
        await mj.give(o, o.snapshot, [(rewards.EXP, p.exp + p.extra)])
        o.send(S_PLAYER, b.complete(_player_msg(ed, pid)))
