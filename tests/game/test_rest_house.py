"""Rest House / Altar of Ennoblement (handlers/hangup.py, docs/salas-campanha.md#rest-house)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import events as ev
from wartune_server.game.handlers import hangup
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

ROOM = 7001
STATUE = ROOM * 100 + 2  # 2ª estátua: estado 2 no 4206


def _session(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _snap(g: Game) -> PlayerSnapshot:
    snap = _session(g).snapshot
    assert snap is not None
    return snap


def _info(got: list, code: int) -> list[pb.HangupInfoMsg]:  # type: ignore[type-arg]
    return [pb.HangupInfoMsg.FromString(p.body) for p in got if p.code == code]


async def _enter(g: Game) -> list:  # type: ignore[type-arg]
    g.client.send(8258, pb.WorldBossMsg(param1=ROOM))
    return await g.until(4206)


async def _begin(g: Game) -> list:  # type: ignore[type-arg]
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=STATUE))
    confirm = pb.CampaignConfirmMsg.FromString(next(p.body for p in await g.until(29) if p.code == 29))
    assert (confirm.type, confirm.nodeId, confirm.title) == (hangup.CONFIRM_TYPE, STATUE, "Divine Statue")
    g.client.send(5033, pb.CampaignReqMsg(paraInt1=ROOM, paraInt2=STATUE, paraBool1=True))
    return await g.until(4206)


async def test_entra_medita_e_ganha_estamina_por_tique(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.weary = 21, 100
        got = await _enter(g)
        codes = [p.code for p in got]
        assert codes.index(4199) < codes.index(125) < codes.index(21) < codes.index(127) < codes.index(4206)
        assert _info(got, 4199)[0].leftWeay == 50
        nodes = pb.CampaignNodeListMsg.FromString(next(p.body for p in got if p.code == 127)).node
        assert sorted(n.masterType for n in nodes) == [111] * 4
        assert ev.daily(snap, "leed:22", clock.now()).value == 1  # "Enter the Altar of Ennoblement"

        got = await _begin(g)
        assert _info(got, 4200)[0].isStartHangup
        state = pb.PlayerHangupStateListMsg.FromString(next(p.body for p in got if p.code == 4206))
        assert [(x.armyId, x.state) for x in state.hanupState] == [(g.user_id, 2)]

        clock.advance(250)  # dois tiques de 120 s
        await hangup.tick(_session(g))
        ticks = _info(await g.until(4235), 4235)
        ticks += _info(await g.idle(), 4235)
        assert [(t.addWeay, t.leftWeay) for t in ticks] == [(1, 49), (1, 48)]
        assert snap.character.weary == 102

        g.client.send(8292, pb.PayTypeMsg())
        end = _info(await g.until(4200), 4200)[-1]
        assert (end.isStartHangup, end.addWeay, end.leftWeay) == (False, 2, 48)

        g.client.send(5025, pb.RoomExitMsg())
        assert 22 in [p.code for p in await g.until(22)]
        assert _session(g).campaign is None


async def test_acelera_pago_e_gratis_com_lord_of_time(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _snap(g)
        c = snap.character
        c.grades, c.weary, c.point = 21, 195, 100
        await _enter(g)
        await _begin(g)
        g.client.send(8293, pb.PayTypeMsg(payType=1))
        end = _info(await g.until(4200), 4200)[-1]
        assert (end.isStartHangup, end.addWeay) == (False, 5)  # só até encher: 5 × 10 Balens
        assert (c.weary, c.point) == (200, 50)

        c.weary = 0
        stamp = datetime(2026, 2, 1, tzinfo=UTC).strftime("%Y-%m-%d %H:%M:%S")
        ev.state(snap, f"king:{hangup.LORD_OF_TIME}", clock.now()).text = stamp
        await _begin(g)
        g.client.send(8293, pb.PayTypeMsg(payType=0))
        end = _info(await g.until(4200), 4200)[-1]
        assert (end.addWeay, end.leftWeay, c.weary, c.point) == (45, 0, 45, 50)  # o resto do dia (50 - 5)

        g.client.send(5033, pb.CampaignReqMsg(paraInt1=ROOM, paraInt2=STATUE, paraBool1=True))
        refused = _info(await g.until(4200), 4200)[-1]
        assert (refused.isStartHangup, refused.leftWeay) == (False, 0)
