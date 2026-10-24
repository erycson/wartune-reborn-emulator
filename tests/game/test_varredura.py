"""Varredura (Blitz) de campanha, 8528 sweepType 1 (game/sweep.py, docs/salas-campanha.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import events as ev
from wartune_server.game import sweep as sw
from wartune_server.game.handlers import dungeon
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

WORG = 1001  # Worg Lair: BaseGp 600 -> 630 por rodada


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


def _ready(g: Game, clock: FakeClock) -> PlayerSnapshot:
    snap = _snap(g)
    c = snap.character
    c.grades, c.weary, c.gold, c.point = 20, 100, 100_000, 50
    ev.state(snap, f"campaign_rank:{WORG}", clock.now()).value = 3  # masmorra vencida (4151)
    return snap


def _rsp(got: list) -> pb.CampaignSweepRsp:  # type: ignore[type-arg]
    return pb.CampaignSweepRsp.FromString(next(p.body for p in got if p.code == 4425))


def _start(count: int = 2) -> pb.CampaignSweepReq:
    return pb.CampaignSweepReq(sweepType=1, opType=1, campaignId=WORG, count=count, enterType=1, payType=2)


async def test_recusa_sem_masmorra_vencida_e_sem_estamina(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.weary = 20, 100
        g.client.send(8528, _start())
        assert _rsp(await g.until(4425)).status == sw.BROKEN  # sem nota na 1001
        _ready(g, clock).character.weary = 30
        g.client.send(8528, _start())
        assert _rsp(await g.until(4425)).status == sw.NO_WEARY  # 2 rodadas pedem 40


async def test_rodadas_no_tempo_aceleracao_e_fechar(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _ready(g, clock)
        g.client.send(8528, _start(3))
        start = _rsp(await g.until(4425))
        assert start.status == sw.OK and [(r.type, r.time) for r in start.result] == [(sw.RUNNING, 900)]
        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=1, campaignId=WORG, count=1))
        assert _rsp(await g.until(4425)).status == sw.BUSY

        clock.advance(299)  # o cliente pergunta no fim do tempo; 1 s antes ainda acerta
        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=3, campaignId=WORG))
        got = await g.until(4425)
        poll = _rsp(got)
        assert poll.status == sw.POLLED
        assert [(r.type, r.finishCount, r.gp) for r in poll.result] == [(1, 1, 630), (sw.RUNNING, 1, 0)]
        assert len(poll.result[0].items) == 1  # a carta da rodada
        assert 115 in [p.code for p in got] and (snap.character.weary, snap.character.gold) == (80, 95_000)
        # (só turco: savasa_baskin #10-#31) a rodada conta como campanha (leed 4), 4476 e o aviso dos itens
        codes = [p.code for p in got]
        assert codes.index(115) < codes.index(4152) and 4476 in codes
        [text] = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 111]
        assert text.startswith("Received items: ") and text.endswith(" x1")

        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=2, campaignId=WORG, payType=1))
        done = _rsp(await g.until(4425))  # faltam 601 s: ceil(601/60) = 11 Balens
        assert done.status == sw.DONE and [r.finishCount for r in done.result] == [2, 3]
        assert (snap.character.point, snap.character.weary, snap.character.gold) == (39, 40, 85_000)

        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=4, campaignId=WORG))
        assert 4425 not in [p.code for p in await g.idle()]
        assert sw.load(snap) is None


async def test_contrato_5_varre_sem_ouro_e_o_login_retoma(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _ready(g, clock)
        snap.character.gold = 0
        end = datetime(2026, 2, 1, tzinfo=UTC).strftime("%Y-%m-%d %H:%M:%S")
        ev.state(snap, f"king:{sw.FREE_BLITZ}", clock.now()).text = end
        g.client.send(8528, _start(2))
        assert _rsp(await g.until(4425)).status == sw.OK
        clock.advance(700)  # offline: as duas rodadas vencem
        s = g.server.online.get(g.user_id)
        assert s is not None
        await dungeon.login_push(s)
        resume = _rsp(await g.until(4425))
        assert resume.status == sw.RESUME and [r.finishCount for r in resume.result] == [1, 2]
        assert resume.totalGp == 1260 and snap.character.gold == 0
