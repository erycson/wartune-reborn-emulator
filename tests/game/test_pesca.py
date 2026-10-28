"""Pesca (9507): ordem das respostas e regras contra as capturas de 26/10, 27/10 e 28/10 (game/fishing.py)."""

import json
import random
import zlib
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import BagType, CashLedger, EventState, PlayerSnapshot
from wartune_server.game import fishing as fs
from wartune_server.game import rankings
from wartune_server.game.handlers import fishing as handler
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 27, 15, 0, tzinfo=UTC)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _send(g: Game, op: int, *paras: int) -> None:
    g.client.send(9507, pb.FreshPoolMsg(op=op, paras=list(paras)))


@pytest.fixture(autouse=True)
def _rng(monkeypatch: pytest.MonkeyPatch) -> None:
    rng = random.Random(7)
    rng.randint = lambda a, b: 45  # type: ignore[method-assign]  # (visto) 27/10 #178: tool 45, sem ferramenta
    monkeypatch.setattr(handler, "RNG", rng)
    monkeypatch.setattr(fs, "RAGE_CHANCE", 0.0)


async def _open(g: Game) -> pb.FishInfosMsg:
    _snap(g).character.grades = 30
    _send(g, handler.FISHPOOL)
    _send(g, handler.FRESH, handler.OPEN)
    got = await g.idle()
    assert [p.code for p in got] == [4916, 4918]
    return pb.FishInfosMsg.FromString(got[1].body)


def _target(infos: pb.FishInfosMsg, channel: int = 2) -> pb.FishInfo:
    return next(f for f in infos.fishs if f.channelId == channel)


async def test_open_sends_pool_and_twenty_fish_in_fixed_slots(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        _send(g, handler.FISHPOOL)
        _send(g, handler.FRESH, handler.OPEN)
        assert await g.idle() == []  # abaixo do nível 28 (OpenGrades.FISH): nada

        infos = await _open(g)
        assert [f.fishId for f in infos.fishs] == [i for ids in fs.SLOTS.values() for i in ids]
        assert {f.state for f in infos.fishs} == {fs.NORMAL}
        ch2 = [f.beginTime for f in infos.fishs if f.channelId == 2]
        assert [b - ch2[0] for b in ch2] == [0, 2000, 4000, 6000, 8000]  # (visto) de 2 em 2 s
        assert {f.templateId for f in infos.fishs if f.channelId == 1} <= {1000, 1011, 1012}

        _send(g, handler.FRESH, 1)  # peixe saiu: só o 4918
        assert [p.code for p in await g.idle()] == [4918]


async def test_catch_answers_like_the_capture_and_fills_the_basket(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        fish = _target(await _open(g))
        _send(g, handler.CRAZY, handler.TOUCH, fish.fishId)
        assert await g.idle() == []
        _send(g, handler.CATCH, fish.fishId)
        got = await g.idle()
        assert [p.code for p in got] == [115, 111, 4917, 4916, 4918, 83]  # (visto) 27/10 #176-#181
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg == "Received Gold Chest x2 while fishing!"
        result = pb.FishResultMsg.FromString(got[2].body)
        assert [(r.fishId, r.tool) for r in result.results] == [(fish.fishId, 45)]
        pool = pb.FishPoolMsg.FromString(got[3].body)
        assert (pool.level, pool.gp, pool.score, pool.cd, pool.count, pool.maxCount) == (0, 1, 2, 300, 1, 20)
        caught = next(f for f in pb.FishInfosMsg.FromString(got[4].body).fishs if f.fishId == fish.fishId)
        assert caught.state == fs.CAUGHT

        g.server.services.clock.advance(1)  # type: ignore[attr-defined]
        _send(g, handler.FRESH, 1)  # o pescado nasce de novo agora
        reborn = next(f for f in pb.FishInfosMsg.FromString((await g.idle())[0].body).fishs if f.fishId == fish.fishId)
        assert reborn.state == fs.NORMAL and reborn.beginTime == fs.ms(NOW) + 1000

        fish = _target(pb.FishInfosMsg.FromString((await _refresh(g)).body))
        _send(g, handler.CATCH, fish.fishId)
        await g.idle()
        basket = sorted((i.pos, i.template_id, i.count) for i in _snap(g).items if i.bag_type == BagType.FISH)
        assert basket == [(0, 2030101, 2), (1, 2030101, 2)]  # (visto) #176/#199: sem empilhar


async def _refresh(g: Game) -> Packet:
    _send(g, handler.FRESH, 1)
    return (await g.idle())[0]


async def test_miss_costs_cooldown_but_not_an_attempt_and_cooldown_caps_at_1800(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        await _open(g)
        for k in range(6):
            _send(g, handler.CATCH)
            got = await g.idle()
            assert [p.code for p in got] == [4917, 4916, 4918]  # (visto) 27/10 #397-#399
            assert not pb.FishResultMsg.FromString(got[0].body).results
            pool = pb.FishPoolMsg.FromString(got[1].body)
            assert (pool.count, pool.cd) == (0, 300 * (k + 1))
        _send(g, handler.CATCH)  # 1800 + 300 > 1800 (FishFrame): recusa, só o 4916
        got = await g.idle()
        assert [p.code for p in got] == [4916] and pb.FishPoolMsg.FromString(got[0].body).cd == 1800


async def test_daily_attempts_and_full_basket_refuse(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        fish = _target(await _open(g))
        snap = _snap(g)
        f = fs.load(snap, NOW)
        f.count = fs.MAX_COUNT
        fs.store(snap, f, NOW)
        _send(g, handler.CATCH, fish.fishId)
        assert [p.code for p in await g.idle()] == [4916]


async def test_tool_drop_and_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        fish = _target(await _open(g))
        monkeypatch.setattr(handler.RNG, "randint", lambda a, b: 1)
        _send(g, handler.CATCH, fish.fishId)
        got = await g.idle()
        text = pb.ChatChannelMsg.FromString(got[1].body).encodeMsg
        assert text == "Received Gold Chest x2, Shoal Water Torpedo x1 while fishing!"  # (visto) 27/10 #200
        assert pb.FishPoolMsg.FromString(got[3].body).tool1 == 1

        _send(g, handler.USETOOL, 1)  # torpedo raso: os obstáculos do canal 1 somem por 20 s
        got = await g.idle()
        assert [p.code for p in got] == [4916, 4918]
        infos = pb.FishInfosMsg.FromString(got[1].body)
        assert {f.state for f in infos.fishs if f.channelId == 1} == {fs.GONE}
        assert pb.FishPoolMsg.FromString(got[0].body).tool1 == 0

        f = fs.load(_snap(g), NOW)
        f.tools[1] = 1
        fs.store(_snap(g), f, NOW)
        _send(g, handler.USETOOL, 2)
        assert pb.FishPoolMsg.FromString((await g.idle())[0].body).hookState == fs.THREE


async def test_basket_goes_to_the_bag(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        fish = _target(await _open(g))
        _send(g, handler.CATCH, fish.fishId)
        await g.idle()
        before = sum(i.count for i in _snap(g).items if i.bag_type == BagType.BAG and i.template_id == 2030101)
        _send(g, handler.GETALL)
        got = await g.idle()
        assert [p.code for p in got] == [111, 115, 115]  # (visto) 28/10 #368-#370
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "Looted successfully!"
        assert [(m.changeType, m.changePos) for m in pb.ItemMovedListMsg.FromString(got[1].body).moved] == [(23, 0)]
        assert not [i for i in _snap(g).items if i.bag_type == BagType.FISH]
        after = sum(i.count for i in _snap(g).items if i.bag_type == BagType.BAG and i.template_id == 2030101)
        assert after == before + 2


async def test_end_cooldown_costs_three_balens_a_minute(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        await _open(g)
        _send(g, handler.CATCH)
        _send(g, handler.CATCH)
        await g.idle()
        c = _snap(g).character
        c.point, c.gift_token = 100, 0
        _send(g, handler.COOLCD, 0)
        got = await g.idle()
        assert pb.FishPoolMsg.FromString(next(p.body for p in got if p.code == 4916)).cd == 0
        assert c.point == 100 - 30  # ceil(600 / 60) * 3 (FishFrame.__coolCdHandler)
        async with g.server.services.database.sessions() as db:
            rows = (await db.execute(select(CashLedger))).scalars().all()
            assert [(r.delta_point, r.reason) for r in rows][-1] == (-30, "fish_cd")


def test_level_follows_upgrade_table_40() -> None:
    from wartune_server.templates.repository import GameTemplates

    templates = GameTemplates.parse(Path("data/templates/tempinfos.xml").read_bytes())
    f = fs.Fisher()
    fs.add_gp(f, templates, 160)  # nível 1 pede 150 (UpGradeTempInfos tipo 40)
    assert (f.level, f.gp) == (1, 10)


def test_travel_matches_the_capture_medians() -> None:
    assert fs.travel({"Length": "70", "Speed": "2"}) == 18000  # 1001: 18552 na captura
    assert fs.travel({"Length": "117", "Speed": "4"}) == 9470  # 1003: 9717


def test_weekly_position_and_ranking_file() -> None:
    def st(cid: int, score: int) -> EventState:
        e = EventState(cid, fs.KEY, NOW)
        e.text = json.dumps(asdict(fs.Fisher(score=score, week=fs.parse("", NOW).week)))
        return e

    states = [st(1, 24), st(2, 50), st(3, 0)]
    assert [fs.position(states, c, NOW) for c in (1, 2, 3)] == [2, 1, 0]
    assert zlib.decompress(rankings._xml("", "FishScores")).startswith(b"<?xml")
