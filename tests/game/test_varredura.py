"""Varredura (Blitz) de campanha, 8528 sweepType 1 (game/sweep.py, docs/salas-campanha.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import events as ev
from wartune_server.game import rules
from wartune_server.game import sweep as sw
from wartune_server.game.handlers import dungeon
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

CALORN = 1007  # Camp Calorn (Lv 19-21): BaseGp 1800 -> 1889 (float) e 6000 de ouro por rodada (0085)


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


def _ready(g: Game, clock: FakeClock) -> PlayerSnapshot:
    snap = _snap(g)
    c = snap.character
    c.grades, c.weary, c.gold, c.point = 20, 100, 100_000, 50
    ev.state(snap, f"campaign_rank:{CALORN}", clock.now()).value = 3  # masmorra vencida (4151)
    return snap


def _rsp(got: list) -> pb.CampaignSweepRsp:  # type: ignore[type-arg]
    return pb.CampaignSweepRsp.FromString(next(p.body for p in got if p.code == 4425))


def _start(count: int = 2) -> pb.CampaignSweepReq:
    return pb.CampaignSweepReq(sweepType=1, opType=1, campaignId=CALORN, count=count, enterType=1, payType=2)


async def test_recusa_sem_masmorra_vencida_e_sem_estamina(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.weary = 20, 100
        g.client.send(8528, _start())
        assert _rsp(await g.until(4425)).status == sw.BROKEN  # sem nota na 1007
        _ready(g, clock).character.weary = 30
        g.client.send(8528, _start())
        assert _rsp(await g.until(4425)).status == sw.NO_WEARY  # 2 rodadas pedem 40


async def test_rodadas_no_tempo_aceleracao_e_fechar(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _ready(g, clock)
        g.client.send(8528, _start(3))
        got = await g.until(4425)
        assert [p.code for p in got] == [109, 3, 140, 4425]  # (só turco: savasa_baskin #1-#4)
        start = _rsp(got)
        assert start.status == sw.OK and [(r.type, r.time) for r in start.result] == [(sw.RUNNING, 900)]
        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=1, campaignId=CALORN, count=1))
        assert _rsp(await g.until(4425)).status == sw.BUSY

        clock.advance(299)  # o cliente pergunta no fim do tempo; 1 s antes ainda acerta
        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=3, campaignId=CALORN))
        got = await g.until(4425)
        poll = _rsp(got)
        assert poll.status == sw.POLLED
        assert [(r.type, r.finishCount, r.gp) for r in poll.result] == [(1, 1, 1889), (sw.RUNNING, 1, 0)]
        # (só turco: savasa_baskin) o ouro da rodada (item -100) e a carta
        assert [(i.templateId, i.count) for i in poll.result[0].items][0] == (-100, 6000)
        assert len(poll.result[0].items) == 2
        assert 115 in [p.code for p in got] and (snap.character.weary, snap.character.gold) == (80, 101_000)
        # (só turco: savasa_baskin #5-#33) a rodada conta como campanha (leed 4), 115, 4476 e o aviso dos itens
        codes = [p.code for p in got]
        assert codes[:3] == [109, 3, 4152]  # sem missão aceita, sem o 112
        assert codes.index(4152) < codes.index(115) < codes.index(4476)
        assert codes.index(111) < codes.index(4425) and 140 not in codes  # ainda varrendo
        [text] = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 111]
        assert text.startswith("Received: ") and text.endswith(" x1")

        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=2, campaignId=CALORN, payType=1))
        got = await g.until(4425)  # faltam 601 s: ceil(601/60) = 11 Balens
        codes = [p.code for p in got]
        assert codes.index(140) < codes.index(115)  # o exército para antes dos itens (o leed 4 já contou)
        done = _rsp(got)
        assert done.status == sw.DONE and [r.finishCount for r in done.result] == [2, 3]
        assert (snap.character.point, snap.character.weary, snap.character.gold) == (39, 40, 103_000)

        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=3, campaignId=CALORN))  # (só turco: savasa #35)
        late = _rsp(await g.until(4425))
        assert (late.status, late.sweepType, len(late.result)) == (sw.POLLED, 0, 0)
        g.client.send(8528, pb.CampaignSweepReq(sweepType=1, opType=4, campaignId=CALORN))
        assert 4425 not in [p.code for p in await g.idle()]
        assert sw.load(snap) is None


async def test_contrato_5_varre_sem_ouro_e_o_login_retoma(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _ready(g, clock)
        snap.character.gold = 0
        s = g.server.online.get(g.user_id)
        assert s is not None
        # acima do MaxLevel 21: sem EXP (só turco: savasa_baskin, nível 56 na 1007)
        snap.character.total_gp = dict(rules.grade_steps(s.ctx.templates))[22]
        rules.add_gp(snap, s.ctx.templates, 0)
        end = datetime(2026, 2, 1, tzinfo=UTC).strftime("%Y-%m-%d %H:%M:%S")
        ev.state(snap, f"king:{sw.FREE_BLITZ}", clock.now()).text = end
        g.client.send(8528, _start(2))
        assert _rsp(await g.until(4425)).status == sw.OK
        clock.advance(700)  # offline: as duas rodadas vencem
        await dungeon.login_push(s)
        resume = _rsp(await g.until(4425))
        assert resume.status == sw.RESUME and [r.finishCount for r in resume.result] == [1, 2]
        assert resume.totalGp == 0 and snap.character.gold == 12_000  # contrato 5: sem custo, o ouro das 2 rodadas
