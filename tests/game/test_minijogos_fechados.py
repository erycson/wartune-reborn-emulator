"""Minijogos do operador que as capturas só mostram fechados: abertos por ``game_settings`` (ver ``minijogo.py``)."""

import random
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game.handlers import slot as slot_mod
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
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
