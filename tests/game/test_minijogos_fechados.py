"""Minijogos do operador que as capturas só mostram fechados: abertos por ``game_settings`` (ver ``minijogo.py``)."""

import random
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, PlayerSnapshot
from wartune_server.game import bag
from wartune_server.game.handlers import group_draw, treasure_hunt
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


# ---------------------------------------------------------------- cadeiras


CHAIRS = {
    "begin": "2026-10-20 05:00:00",
    "end": "2026-10-23 05:00:00",
    "chairsNeedPoints": 100,
    "rewardNeedChairs": 2,
    "luckyCount": 1,
    "comfortItems": ["208009|1"],
    "luckyItems": ["-100|1000"],
}


async def test_chairs_turn_recharges_into_comfort_rewards_and_the_lucky_one(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
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


async def _seek(g: Game, op: int) -> pb.PlayerSeekInfoMsg:
    g.client.send(9502, pb.PlayerSeekInfoMsg(op=op))
    return pb.PlayerSeekInfoMsg.FromString(_last(await g.idle(), 4914))


async def test_treasure_hunt_explores_opens_recharges_and_exchanges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rng = random.Random(1)
    rng.choices = lambda items, weights=None: [items[0]]  # type: ignore[method-assign,assignment]
    monkeypatch.setattr(treasure_hunt, "RNG", rng)
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        g.client.send(9502, pb.PlayerSeekInfoMsg(op=1))
        assert [p.code for p in await g.idle()] == [111]  # abaixo do 32
        _snap(g).character.grades = 32
        info = await _seek(g, 1)
        assert (info.op, info.seekCount, info.state, info.nextAddTime) == (1, 10, 0, 0)
        assert len(info.seekNodeList.seekNode) == 6
        info = await _seek(g, 3)
        assert (info.op, info.seekCount, info.state) == (3, 9, 1) and info.curNodeId != 1 and info.eventDesc
        g.client.send(9502, pb.PlayerSeekInfoMsg(op=4))
        got = await g.idle()
        assert pb.PlayerSeekInfoMsg.FromString(_last(got, 4914)).state == 0
        assert "Summoner's Shard x5" in pb.MessageForSeekMsg.FromString(_last(got, 4915)).info
        g.server.services.clock.advance(1800 + 60)  # type: ignore[attr-defined]
        info = await _seek(g, 2)
        assert (info.seekCount, info.nextAddTime) == (10, 0)
        await _seek(g, 3)
        assert (await _seek(g, 1)).nextAddTime == 1800
        snap = _snap(g)
        shards = bag.add(snap, g.server.services.templates, treasure_hunt.SHARD, 95, NOW)
        await g.server.services.characters.save(*shards)
        await _seek(g, 6)
        assert bag.count_of(snap, treasure_hunt.MASTER_KIT) == 1 and bag.count_of(snap, treasure_hunt.SHARD) == 0
