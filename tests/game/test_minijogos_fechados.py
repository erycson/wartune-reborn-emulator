"""Minijogos do operador que as capturas só mostram fechados: ligados pela migração 0103 (``game_settings``, ver ``minijogo.py``)."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, PlayerSnapshot
from wartune_server.game import bag
from wartune_server.game.handlers import group_draw, minigames, ore, quiz
from wartune_server.game.handlers import minijogo as mj
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services import ledger
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
DAY = 86400


def _open(g: Game, key: str, cfg: dict[str, Any]) -> None:
    """Troca parâmetros da chave semeada (o resto fica como a migração deixou)."""
    world = g.server.services.world
    seeded = world.settings.get(key) or _closed[key]
    object.__setattr__(world, "settings", MappingProxyType({**world.settings, key: {**seeded, **cfg}}))


_closed: dict[str, Any] = {}  # o que ``_close`` tirou


def _close(g: Game, key: str) -> None:
    world = g.server.services.world
    _closed[key] = world.settings[key]
    object.__setattr__(world, "settings", MappingProxyType({k: v for k, v in world.settings.items() if k != key}))


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _last(got: list[Packet], code: int) -> bytes:
    return next(p.body for p in reversed(got) if p.code == code)


# ---------------------------------------------------------------- caça-níquel


SLOT = {"begin": "2026-10-20 05:00:00", "cycleDays": 3, "digitWeights": [0, 0, 0, 0, 0, 0, 0, 1, 0, 0]}  # sempre 7


async def _slot(g: Game, op: int) -> pb.SlotActiveMsg:
    g.client.send(9500, pb.SlotActiveRequest(op=op))
    return pb.SlotActiveMsg.FromString(_last(await g.idle(), 4901))


async def test_slot_draws_one_digit_a_day_restores_missed_day_and_pays_the_number(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        assert (await _slot(g, 1)).open is True  # ligado pela migração
        _close(g, "slot_machine")
        assert (await _slot(g, 1)).open is False  # sem a chave: fechado
        _open(g, "slot_machine", SLOT)
        info = await _slot(g, 1)
        assert (info.open, info.op, info.slot, info.type, info.status, info.findcost) == (True, 1, "*--", 2, 0, 10)
        assert (await _slot(g, 2)).slot == "7--"
        assert (await _slot(g, 2)).op == 1  # sem sorteio hoje: só atualiza
        g.server.services.clock.advance(2 * DAY)  # type: ignore[attr-defined]
        assert (await _slot(g, 1)).slot == "7+*"
        assert (await _slot(g, 2)).slot == "7+7"
        snap = _snap(g)
        snap.character.point = 100
        info = await _slot(g, 11)
        assert (info.op, info.slot, info.status) == (11, "777", 1) and snap.character.point == 90
        gold = snap.character.gold
        info = await _slot(g, 3)
        assert (info.op, info.status) == (3, 2) and snap.character.gold == gold + 777
        assert (await _slot(g, 2)).op == 1  # resgatado: não sorteia mais


# ---------------------------------------------------------------- loteria


LOTTERY = {
    "begin": "2026-10-20 05:00:00",
    "cycleDays": 3,
    "onceNeedPoint": 100,
    "dayMaxCount": 2,
    "items": [[-100, 5000], [208009, 3]],
    "weights": [0, 1],
}


async def _spend(g: Game, point: int) -> None:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    c = session.snapshot.character
    c.point += point
    entry = ledger.spend(c, point, "teste", session.ctx.clock.now(), bound=False)
    assert entry is not None
    await session.ctx.characters.save(c, entry)


async def test_lottery_turns_balens_spent_into_capped_daily_spins(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        _close(g, "lottery")
        g.client.send(8750)
        assert [p.code for p in await g.idle()] == [4637]  # sem a chave: só o fechado
        _open(g, "lottery", LOTTERY)
        await _spend(g, 350)  # 3 tentativas, mas o teto do dia é 2
        g.client.send(8750)
        got = await g.idle()
        assert [p.code for p in got] == [4637, 4636, 4641, 4639]
        info = pb.LotteryMsg.FromString(_last(got, 4636))
        assert (info.payedPoint, info.dayAddCount, info.totalCount, info.leftCount) == (350, 2, 2, 2)
        assert [i.tempId for i in pb.VipRouletteMsg.FromString(_last(got, 4641)).leftItem] == [-100, 208009]
        for left in (1, 0):
            g.client.send(8748)
            res = pb.SimplePropertyMsg.FromString(_last(await g.idle(), 4642))
            assert (res.param1, res.param2, res.param3) == (208009, left, 3)
        g.client.send(8748)
        assert pb.SimplePropertyMsg.FromString(_last(await g.idle(), 4642)).param1 == 0  # acabou
        assert sum(i.count for i in _snap(g).items if i.template_id == 208009) == 6
        g.client.send(8750)
        assert "Maga obtained" in pb.LotteryMsg.FromString(_last(await g.idle(), 4639)).property3[0]


# ---------------------------------------------------------------- sorteio de grupo


async def test_group_draw_spends_chances_won_by_group_buys(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        _open(g, "group_draw", {"items": [[208009, 2], [-100, 100]], "weights": [1, 0]})
        g.client.send(9523, pb.LeadRewardMsg(op=1))
        assert pb.LeadRewardMsg.FromString(_last(await g.idle(), 4936)).templateId == 0  # sem sorteio
        snap = _snap(g)
        await g.server.online.get(g.user_id).ctx.characters.save(group_draw.add_chance(snap, NOW))  # type: ignore[union-attr]
        g.client.send(9523, pb.LeadRewardMsg(op=3))
        roulette = pb.VipRouletteMsg.FromString(_last(await g.idle(), 338))
        assert roulette.leftCount == 1 and [(i.tempId, i.count) for i in roulette.leftItem] == [
            (208009, 2),
            (-100, 100),
        ]
        g.client.send(9523, pb.LeadRewardMsg(op=1))
        got = pb.LeadRewardMsg.FromString(_last(await g.idle(), 4936))
        assert (got.templateId, got.count, got.leadExtractTimes) == (208009, 2, 0)
        assert sum(i.count for i in snap.items if i.template_id == 208009) == 2


# ---------------------------------------------------------------- cadeiras


CHAIRS = {
    "begin": "2026-10-20 05:00:00",
    "cycleDays": 3,
    "chairsNeedPoints": 100,
    "rewardNeedChairs": 2,
    "luckyCount": 1,
    "comfortItems": ["208009|1"],
    "luckyItems": ["-100|1000"],
}


async def test_chairs_turn_recharges_into_comfort_rewards_and_the_lucky_one(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        _close(g, "chairs")
        g.client.send(9638, pb.ChairsListMsg(op=1))
        got = await g.idle()
        assert [p.code for p in got] == [414, 415] and pb.SimplePropertyMsg.FromString(got[0].body).param7 is False
        _open(g, "chairs", CHAIRS)
        session = g.server.online.get(g.user_id)
        assert session is not None
        await session.ctx.characters.save(CashLedger(g.user_id, 250, 0, 250, 0, "recharge", "teste", NOW))
        g.client.send(9638, pb.ChairsListMsg(op=1))
        got = await g.idle()
        assert pb.SimplePropertyMsg.FromString(_last(got, 414)).param7 is True
        info = pb.ChairsListMsg.FromString(_last(got, 415))
        assert (info.currentChairs, info.rewardCounts, info.leftPoint, info.totalChairsCount) == (2, 2, 50, 2)
        assert list(info.luckyNickName) == ["Maga"]
        gold = _snap(g).character.gold
        g.client.send(9638, pb.ChairsListMsg(op=2))
        info = pb.ChairsListMsg.FromString(_last(await g.idle(), 415))
        assert info.rewardCounts == 0 and _snap(g).character.gold == gold + 1000
        assert sum(i.count for i in _snap(g).items if i.template_id == 208009) == 2


# ---------------------------------------------------------------- caça ao tesouro


# caça ao tesouro: tests/game/test_card_hunt.py (pela captura 20261029-121453-1)


# ---------------------------------------------------------------- minério de Stokes


ORE = {
    "begin": "2026-10-20 05:00:00",
    "cycleDays": 3,
    "dailyTurns": 12,
    "finds": [[208009, 1, 1]],
    "special": [[2, [[208014, 3]]], [4, [[208017, 1]]], [6, [[208017, 1]]], [8, [[3020010, 1]]]],
}


async def _ore(g: Game, op: int, prop: bool = False) -> list[Packet]:
    g.client.send(9645, pb.OreActiveClientOpMsg(opType=op, isUseProp=prop), extend1=minigames.ORE_OP)
    return await g.idle()


async def test_stokes_ore_mines_the_shared_vein_with_special_floors(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        _open(g, "stokes_ore", ORE)
        got = await _ore(g, 3)
        assert [p.code for p in got] == [188, 189, 187]
        base = pb.OreActiveBaseInfoMsg.FromString(_last(got, 188))
        assert [r.specialFloorNum for r in base.rewards] == [0, 2, 4, 6, 8]
        snap = _snap(g)
        snap.character.point = 1000
        got = await _ore(g, 2)
        mine = pb.OreMineRespMsg.FromString(_last(got, 187))
        assert (mine.passType, mine.count, list(mine.floors)) == (1, 8, [2, 4, 6])  # 3 especiais por dia
        window = pb.OreWindowMsg.FromString(_last(got, 189))
        assert (window.curSeq, window.todayRemainTurns, window.spRewardRemainTimes, window.countDown) == (8, 4, 0, 60)
        assert snap.character.point == 1000 - 80 and bag.count_of(snap, 208014) == 3
        assert pb.OreWindowMsg.FromString(_last(await _ore(g, 1), 189)).todayRemainTurns == 4  # veio esgotado: espera
        g.server.services.clock.advance(61)  # type: ignore[attr-defined]
        got = await _ore(g, 1)
        assert pb.OreWindowMsg.FromString(_last(got, 189)).curSeq == 1
        luck = pb.OreMineRespMsg.FromString(_last(await _ore(g, 3), 187))
        assert luck.passType == 2 and "Maga reached floor 6" in luck.infos[0]


# ---------------------------------------------------------------- quiz


QUIZ_DAY = datetime(2026, 10, 19, 19, 29, tzinfo=UTC)  # segunda-feira


async def _quiz(g: Game, kind: int, value: int) -> list[Packet]:
    g.client.send(9501, pb.AnswerquestionReqMsg(type=kind, count=value))
    return await g.idle()


async def _tick(g: Game, seconds: float) -> list[Packet]:
    g.server.services.clock.advance(seconds)  # type: ignore[attr-defined]
    session = g.server.online.get(g.user_id)
    assert session is not None
    await quiz.tick(session.ctx)
    return await g.idle()


def _state(got: list[Packet]) -> int:
    return pb.SysAnswerQuestionStateMsg.FromString(_last(got, 4908)).sysState


async def test_quiz_runs_the_schedule_scores_answers_helps_and_pays_exp(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(QUIZ_DAY)) as g:
        _snap(g).character.grades = 30
        _close(g, "quiz")
        assert _state(await _quiz(g, 1, 11)) == 0  # sem a chave
        _open(g, "quiz", {"count": 2})
        got = await _quiz(g, 1, 11)
        assert (
            _state(got) == 1 and pb.playeranswerquestionMsg.FromString(_last(got, 4907)).wisdomHeartCount == 2
        )  # VIP: duas
        got = await _tick(g, 61)  # 19:30:01
        assert _state(got) == 2
        question = pb.singleranswerquestionMsg.FromString(_last(got, 4909))
        assert (question.id, question.answer) == (1, 0) and question.option1
        assert _state(await _tick(g, 5)) == 3  # 19:30:06: 14 s sobrando
        got = await _quiz(g, 2, 22)  # coração: a certa vem no 4909
        assert pb.singleranswerquestionMsg.FromString(_last(got, 4909)).answer == 1
        got = await _tick(g, 15)  # 19:30:21 resultado
        player = pb.playeranswerquestionMsg.FromString(_last(got, 4907))
        assert (_state(got), player.currentScore, player.playerAnswerSucCount, player.wisdomHeartCount) == (4, 24, 1, 1)
        assert [r.nickName for r in pb.TenAnswerQuestionOrderMsg.FromString(_last(got, 4910)).tenAQ_Info] == ["Maga"]
        await _tick(g, 5)
        await _tick(g, 5)  # 19:30:31 respondendo a 2ª
        await _quiz(g, 3, 2)  # errada
        got = await _tick(g, 15)
        assert pb.playeranswerquestionMsg.FromString(_last(got, 4907)).currentScore == 25
        got = await _tick(g, 5)  # fim: EXP
        assert _state(got) == 5
        player = pb.playeranswerquestionMsg.FromString(_last(got, 4907))
        assert (player.getEXP, player.extraEXP) == (25 * 30 * 10, 10 * 30 * 100)


async def test_stokes_ore_concurrent_hits_do_not_overwrite_the_vein(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None
        _snap(g).character.point = 1000
        hit = pb.OreActiveClientOpMsg(opType=1)
        await asyncio.gather(ore.operate(session, hit), ore.operate(session, hit))  # o lock serializa
        await g.idle()
        assert (await mj.shared(session, ore.VEIN))["seq"] == 2
