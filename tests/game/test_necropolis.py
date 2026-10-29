"""Tormented Necropolis (8101): a torre de 30 andares que abre com o recorde 100 das Catacombs (game/maze.py
``NECROPOLIS``). Fontes: cliente (``checkMaze2``, ``towerInfo2``, varredura até 29) e templates (``MapInfos``
8101-8130, ``GameHeroTemp`` 8001-8030); sem captura."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain import gameday
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import maze as mz
from wartune_server.game import recover
from wartune_server.game.handlers import tower as tw
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
READY = 19000
N = mz.NECROPOLIS


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


def _set(g: Game, tower: mz.Tower, kind: mz.Kind = N) -> None:
    s = g.server.online.get(g.user_id)
    assert s is not None
    mz.store(_snap(g), tower, s.ctx.clock.now(), kind)


def _tower(g: Game) -> mz.Tower:
    s = g.server.online.get(g.user_id)
    assert s is not None
    return mz.load(_snap(g), s.ctx.clock.now(), N)


def test_andares_saem_dos_guardioes() -> None:
    """Andar k = mapa 8100 + k com o "Level k Guardian" (GameHeroTemp 8000 + k) como chefe; o 30 é o último."""
    from wartune_server.templates.repository import GameTemplates

    t = GameTemplates.parse(TEMPLATES.read_bytes())
    c = mz.content(t, mz.settings(None, N), N)
    assert c["campaign"] == 8101 and sorted(c["maps"]) == [str(8100 + k) for k in range(1, 31)]
    hero = c["battles"]["810102"]["heroes"][0]
    assert (hero["tempId"], hero["initHp"]) == (8001, 180000)
    nodes = {n["campDataId"]: n for n in c["maps"]["8101"]["nodes"]}
    assert nodes[810102]["nodeName"] == "Level 1 Guardian" and nodes[810102]["heroTempId"] == 8001
    assert c["portals"]["810104"] == 8102 and "813004" not in c["portals"]
    assert c["battles"]["810102"]["gpBonus"] == 400 * 101  # TODO(inventado) continua a curva das Catacombs
    assert (mz.kind_of(8130), mz.kind_of(8100), mz.kind_of(8001)) == (N, mz.CATACOMBS, mz.CATACOMBS)
    assert mz.floor_of(8105) == 5


async def test_fechada_sem_recorde_100_e_aberta_depois(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        g.client.send(8296, pb.EnterTowerInfoMsg(campaignId=8101, chooseIndex=1))
        assert 21 not in [p.code for p in await g.idle()]
        assert _tower(g).enters == 0

        _set(g, mz.Tower(record=100), mz.CATACOMBS)
        g.client.send(8297, pb.TowerInfoReqMsg(index=1))
        info = pb.TowerInfoMsg.FromString((await g.until(4205))[-1].body)
        assert (info.campaignId, info.index, info.towerIndex, info.freeEnterCount) == (8101, 1, 0, 1)

        g.client.send(8296, pb.EnterTowerInfoMsg(campaignId=8101, chooseIndex=1))
        got = await g.until(21)
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == 8101
        assert (_tower(g).enters, _tower(g).index) == (1, 1)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None and s.campaign.map_id == 8101
        assert mz.load(_snap(g), s.ctx.clock.now()).enters == 0  # as Catacombs não gastam entrada

        tw.floor_entered(s, 8102)
        assert (_tower(g).index, _tower(g).record) == (2, 2)
        await s.ctx.characters.save(tw.died(s))
        assert pb.TowerDiedMsg.FromString((await g.until(4207))[-1].body).msg == "0"
        assert _tower(g).dead and not mz.load(_snap(g), s.ctx.clock.now()).dead


async def test_varredura_usa_a_torre_da_necropolis(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        _set(g, mz.Tower(record=100), mz.CATACOMBS)
        _set(g, mz.Tower(record=15))
        _snap(g).character.gold = 10**7
        g.client.send(8528, pb.CampaignSweepReq(sweepType=2, opType=1, campaignId=8101, eIndex=12))
        rsp = pb.CampaignSweepRsp.FromString((await g.until(4425))[-1].body)
        assert rsp.status == 1
        from wartune_server.game import sweep as sw

        sweep = sw.load(_snap(g))
        assert sweep is not None and sweep.campaign_id == 8101


async def test_recuperar_conta_as_entradas_de_ontem(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        now = s.ctx.clock.now()
        snap = _snap(g)
        assert recover._used_yesterday(snap, recover.NECROPOLIS, now) == 1 << 30  # fechada
        _set(g, mz.Tower(record=100), mz.CATACOMBS)
        assert recover._used_yesterday(snap, recover.NECROPOLIS, now) == 0
        _set(g, mz.Tower(enters=1, day=gameday.today(now - timedelta(days=1))))
        assert recover._used_yesterday(snap, recover.NECROPOLIS, now) == 1
        # open_at vem do game_settings como o resto
        assert recover._used_yesterday(snap, recover.NECROPOLIS, now, {"necropolis": {"open_at": 101}}) == 1 << 30


def test_primeiro_abate_e_o_primeiro_do_ranking() -> None:
    from wartune_server.domain.models import EventState

    def st(c: int, rec: int, at: str) -> EventState:
        return EventState(
            character_id=c,
            key=N.key,
            updated_at=datetime(2026, 10, 28),
            text=f'{{"record": {rec}, "record_at": "{at}"}}',
        )

    states = [st(1, 20, "b"), st(2, 20, "a"), st(3, 9, "0"), st(4, 0, "")]
    assert mz.first_kill(states, N) == 2 and mz.first_kill(states) == 0
    cfg = mz.settings(None, N)
    msg = mz.info(mz.Tower(), cfg, N, first=(2, "Bia"))
    assert (msg.firstHitId, msg.firstHitName) == (2, "Bia")
    assert mz.info(mz.Tower(), cfg | {"first_kill": False}, N, first=(2, "Bia")).firstHitId == 0


async def test_info_manda_o_primeiro_abate(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        await s.ctx.characters.save(mz.store(_snap(g), mz.Tower(record=3, record_at="x"), s.ctx.clock.now(), N))
        g.client.send(8297, pb.TowerInfoReqMsg(index=1))
        info = pb.TowerInfoMsg.FromString((await g.until(4205))[-1].body)
        assert info.firstHitId == g.user_id and info.firstHitName == _snap(g).character.nickname
