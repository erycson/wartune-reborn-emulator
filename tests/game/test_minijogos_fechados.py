"""Minijogos do operador que as capturas só mostram fechados: abertos por ``game_settings`` (ver ``minijogo.py``)."""

import random
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game.handlers import group_draw
from wartune_server.game.handlers import slot as slot_mod
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services import ledger
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
DAY = 86400


def _open(g: Game, key: str, cfg: dict[str, Any]) -> None:
    world = g.server.services.world
    object.__setattr__(world, "settings", MappingProxyType({**world.settings, key: cfg}))


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _last(got: list[Packet], code: int) -> bytes:
    return next(p.body for p in reversed(got) if p.code == code)


def _fixed(monkeypatch: pytest.MonkeyPatch, module: Any, value: int) -> None:
    rng = random.Random(1)
    rng.randint = lambda a, b: value  # type: ignore[method-assign]
    monkeypatch.setattr(module, "RNG", rng)


# ---------------------------------------------------------------- caça-níquel


SLOT = {"begin": "2026-10-20 05:00:00", "end": "2026-10-23 05:00:00", "rewardTemplateId": -100, "findCost": 10}


async def _slot(g: Game, op: int) -> pb.SlotActiveMsg:
    g.client.send(9500, pb.SlotActiveRequest(op=op))
    return pb.SlotActiveMsg.FromString(_last(await g.idle(), 4901))


async def test_slot_draws_one_digit_a_day_restores_missed_day_and_pays_the_number(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fixed(monkeypatch, slot_mod, 7)
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        assert (await _slot(g, 1)).open is False  # sem edição: fechado
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
    "end": "2026-10-23 05:00:00",
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
        g.client.send(8750)
        assert [p.code for p in await g.idle()] == [4637]  # sem edição: só o fechado
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
