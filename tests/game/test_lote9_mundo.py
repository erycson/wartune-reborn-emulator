"""Lote 9 (mundo): buff e dublê do chefe do mundo, Master Treasure Thief da terra secreta e a coleta da cidade do céu."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_guild import _session
from tests.game.test_masmorra_1001 import _undying, back_to_map, codes
from tests.game.test_terra_secreta import _enter, _node
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import bag
from wartune_server.game import battle as battle_mod
from wartune_server.game import events as ev
from wartune_server.game.campaign import DONE, NORMAL
from wartune_server.game.handlers import worldboss as wb
from wartune_server.game.handlers.campaign import player_hero
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

OPEN_5001 = datetime(2026, 5, 21, 11, 40, tzinfo=UTC)  # 5001 aberto (11:35-12:35 no inglês)
BEFORE_5001 = datetime(2026, 5, 21, 9, 0, tzinfo=UTC)
LORD = 750133  # o primeiro Master Treasure Thief (750133-750162), na 1ª leva


@pytest.fixture(autouse=True)
def _no_info_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wb, "INFO_EVERY", 3600)


async def test_buff_do_chefe_cobra_sobe_o_grau_e_os_atributos(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        s = _session(g)
        assert s.snapshot is not None
        ch = s.snapshot.character
        ch.grades, ch.point, ch.gift_token = 20, 50, 5
        await g.idle()
        g.client.send(8258, pb.WorldBossMsg(param1=5001))
        await g.idle()
        pool = s.ctx.bosses.pools[5001]
        spec = wb.battle_spec(s, pool)
        before = player_hero(s, spec).stats["PhyAttack"]

        g.client.send(8470, pb.WorldBossBufferMsg(op=2, type=2))  # vinculado primeiro: 5 + 15 Balens
        got = await g.idle()
        [buff] = [pb.CampaignBufferMsg.FromString(p.body) for p in got if p.code == 4165]
        assert [b.bufferTempId for b in buff.bufferInfo] == [401]
        assert (ch.point, ch.gift_token) == (35, 0)
        assert wb._buff_pct(s, pool)["PhyAttack"] == 5
        assert player_hero(s, spec, pct=wb._buff_pct(s, pool)).stats["PhyAttack"] == before * 105 // 100

        g.client.send(8470, pb.WorldBossBufferMsg(op=2, type=1))
        [buff] = [pb.CampaignBufferMsg.FromString(p.body) for p in await g.idle() if p.code == 4165]
        assert [b.bufferTempId for b in buff.bufferInfo] == [402] and ch.point == 15

        st = ev.peek(s.snapshot, "boss_buff:5001")
        assert st is not None
        st.value = 20  # o último grau (420): não passa
        g.client.send(8470, pb.WorldBossBufferMsg(op=2, type=1))
        [alert] = [pb.ChatChannelMsg.FromString(p.body) for p in await g.idle() if p.code == 111]
        assert alert.encodeMsg == wb.BUFF_MAX and ch.point == 15


async def test_duble_compra_cancela_devolve_e_paga_no_fim_da_janela(tmp_path: Path) -> None:
    clock = FakeClock(BEFORE_5001)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = _session(g)
        assert s.snapshot is not None
        ch = s.snapshot.character
        ch.grades, ch.point = 20, 300
        await g.idle()
        g.client.send(8526, pb.OprateReplacemntMsg(op=1, campaignId=5001))
        [res] = [pb.OprateReplacemntMsg.FromString(p.body) for p in await g.idle() if p.code == 4424]
        assert (res.op, res.result, res.campaignId) == (1, 1, 5001) and ch.point == 165
        g.client.send(8526, pb.OprateReplacemntMsg(op=1, campaignId=5001))  # já comprado
        [res] = [pb.OprateReplacemntMsg.FromString(p.body) for p in await g.idle() if p.code == 4424]
        assert res.result == 0 and ch.point == 165

        g.client.send(8526, pb.OprateReplacemntMsg(op=2, campaignId=5001))  # antes da janela: devolve
        await g.idle()
        assert ch.point == 300
        g.client.send(8526, pb.OprateReplacemntMsg(op=1, campaignId=5001))
        await g.idle()
        g.client.send(8271)
        [state] = [pb.ReplacementMsg.FromString(p.body) for p in await g.idle() if p.code == 4423]
        assert state.stateStr == "5001,1"

        gold = ch.gold
        clock.advance(5 * 3600)  # 14:00: a janela do 5001 fechou
        g.client.send(8271)
        [state] = [pb.ReplacementMsg.FromString(p.body) for p in await g.idle() if p.code == 4423]
        cap = s.ctx.world.world_bosses[5001].battle_cap
        assert state.stateStr == "" and ch.gold == gold + cap


async def test_master_treasure_thief_do_primeiro_da_arena(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_floor_hp", _undying)
    async with logged_in(tmp_path, novice=33000) as g:
        await _enter(g)
        s = _session(g)

        async def first(_: int) -> int:
            return 1

        monkeypatch.setattr(s.ctx.characters, "arena_rank", first)
        got = await back_to_map(g)
        lords = pb.FamLordsInfoMsg.FromString(next(p.body for p in got if p.code == 4632))
        assert lords.isCanCall and not lords.isOpenLordsNode and lords.order == 1

        g.client.send(8743)
        got = await g.idle()
        lords = pb.FamLordsInfoMsg.FromString(next(p.body for p in got if p.code == 4632))
        assert lords.isOpenLordsNode and lords.currentTurns == 1 and not lords.isCanCall
        shown = [pb.CampaignNodeUpdateMsg.FromString(p.body) for p in got if p.code == 128]
        assert len([n for n in shown if n.nodeState == NORMAL]) == 10  # a 1ª leva das 3
        assert s.campaign is not None and s.campaign.nodes[LORD]["state"] == NORMAL

        g.client.send(8743)  # uma vez por dia
        assert 4632 not in codes(await g.idle())

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=LORD, paraBool1=True))
        got = await g.until(157)
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        got = await g.fight(prepare) + await g.idle()
        assert pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleResult == 1
        assert _node(got).nodeState == DONE
        texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83]
        assert any(t.endswith("has defeated a Master Treasure Thief and earned 10 guild contribution!") for t in texts)


async def test_coleta_da_cidade_do_ceu_da_o_item_do_anel(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 5, 21, 10, 0, tzinfo=UTC))
    async with logged_in(tmp_path, novice=33000, clock=clock) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        snap.character.grades = 35
        await g.idle()
        walk = pb.SpacePlayerMoveMsg()
        walk.players.add().path.extend([pb.PosMsg(x=110, y=228)])
        g.client.send(8690, walk)
        g.client.send(8692, pb.SimplePropertyMsg(param1=18))  # sem o anel "Collect Rose Lilies": só a janela
        assert 143 not in codes(await g.idle())

        ring = ev.daily(snap, "ring", clock.now())
        ring.text = json.dumps({"t": 2118})  # "Collect Rose Lilies" x10 (Para4 "10000,18")
        g.client.send(8692, pb.SimplePropertyMsg(param1=18))
        [movie] = [pb.PlayerMovieMsg.FromString(p.body) for p in await g.idle() if p.code == 143]
        assert (movie.movieType, movie.targetId) == ("COLLECTION", 18)
        g.client.send(8733, pb.SimplePropertyMsg(param1=18))  # cedo demais
        await g.idle()
        assert bag.count_of(snap, 2100027) == 0

        g.client.send(8692, pb.SimplePropertyMsg(param1=18))
        await g.idle()
        clock.advance(timedelta(seconds=2).total_seconds())
        g.client.send(8733, pb.SimplePropertyMsg(param1=18))
        await g.idle()
        assert bag.count_of(snap, 2100027) == 1
        g.client.send(8733, pb.SimplePropertyMsg(param1=18))  # sem nova coleta: nada
        await g.idle()
        assert bag.count_of(snap, 2100027) == 1
