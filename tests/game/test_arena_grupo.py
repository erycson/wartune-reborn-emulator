"""Arena em grupo: duas salas PvP de 2 procuram partida (5039 com ``paraInt2`` 0), emparelham e lutam; resultado,
prêmio (só quem pediu), missão 421 (tipo 16) e o contador ``match``. Sequência vista em
oficial_20261027-152321-1 #19909-#19995 (ver handlers/arena_grupo.py)."""

import zlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot, Quest
from wartune_server.game import bag
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
PVP, INSIGNIA, QUEST = 1, 208001, 421


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


async def _room(master: Game, mate: Game, no_prize: bool) -> int:
    master.client.send(5023, pb.RoomReqMsg(roomType=PVP, capacity=2))
    room = pb.RoomMsg.FromString(next(p.body for p in await master.idle() if p.code == 12)).roomId
    mate.client.send(5024, pb.RoomReqMsg(roomId=room, roomType=PVP))
    await mate.idle()
    mate.client.send(5036, pb.RoomReqMsg(state=1, isGet=no_prize))
    await master.idle()
    return room


def _result(got: list[Packet]) -> int:
    return pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleResult


async def test_duas_salas_emparelham_lutam_e_premiam(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b, c, d = await a.join("bruxa"), await a.join("cacador"), await a.join("druida")
        for g in (a, b, c, d):
            _snap(g).quests.append(Quest(g.user_id, QUEST, datetime.now(UTC)))
        await _room(a, b, no_prize=False)
        await _room(c, d, no_prize=True)
        for g in (a, b, c, d):
            await g.idle()

        a.client.send(5039, pb.CampaignReqMsg(paraInt2=0, paraBool1=False))
        got = await a.idle()
        assert [p.code for p in got] == [25, 111]  # sem adversário: espera

        c.client.send(5039, pb.CampaignReqMsg(paraInt2=0, paraBool1=False))
        prepare = pb.BattlePrepareMsg.FromString((await c.until(157))[-1].body)
        assert (prepare.battleType, prepare.side) == (10, 1)
        assert sorted((h.side, h.userId) for h in prepare.heros) == sorted(
            [(1, c.user_id), (1, d.user_id), (2, a.user_id), (2, b.user_id)]
        )
        seen = pb.BattlePrepareMsg.FromString((await a.until(157))[-1].body)
        assert seen.side == 2 and seen.battleId == prepare.battleId  # o lado 2 vê do seu lado

        got = {c.user_id: await c.fight(prepare)}
        for g in (a, b, d):
            got[g.user_id] = await g.until(4103) + await g.idle()
        got[c.user_id] += await c.idle()
        res = {pid: _result(p) for pid, p in got.items()}
        assert res[a.user_id] == res[b.user_id] != res[c.user_id] == res[d.user_id]

        for g in (a, b, c, d):
            quest = next(q for q in _snap(g).quests if q.template_id == QUEST)
            assert quest.progress == 1
            assert 4413 in [p.code for p in got[g.user_id]]
            assert [p.code for p in got[g.user_id]][-1] == 25  # a sala volta a esperar
        lose_or_win = {1: 20, 2: 10}
        assert bag.count_of(_snap(a), INSIGNIA) == lose_or_win[res[a.user_id]]
        assert bag.count_of(_snap(b), INSIGNIA) == lose_or_win[res[b.user_id]]
        assert bag.count_of(_snap(c), INSIGNIA) == lose_or_win[res[c.user_id]]
        assert bag.count_of(_snap(d), INSIGNIA) == 0  # pediu sem prêmio (isNoGet)


async def test_dono_que_conduz_cai_e_o_outro_volta_a_sala(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        c = await a.join("cacador")
        for g in (a, c):
            g.client.send(5023, pb.RoomReqMsg(roomType=PVP, capacity=2))
            await g.idle()
            g.client.send(5039, pb.CampaignReqMsg(paraInt2=0, paraBool1=False))
        await c.until(157)
        await a.until(157)
        c.client.writer.close()  # quem conduz a luta cai
        got = await a.until(25) + await a.idle()
        assert _result(got) == 1  # derrota de quem saiu
        assert pb.RoomStateRspMsg.FromString([p for p in got if p.code == 25][-1].body).roomState == 1
        assert bag.count_of(_snap(a), INSIGNIA) == 20  # prêmio vem da migração 0107


async def test_duas_lutas_somam_pontos_e_ranking(tmp_path: Path) -> None:
    from wartune_server.game import arena_grupo as ag
    from wartune_server.game import rankings

    async with logged_in(tmp_path, novice=19000) as a:
        c = await a.join("cacador")
        for g in (a, c):
            g.client.send(5023, pb.RoomReqMsg(roomType=PVP, capacity=2))
            await g.idle()
        expected = {a.user_id: 0, c.user_id: 0}
        for _ in range(2):
            a.client.send(5039, pb.CampaignReqMsg(paraInt2=0, paraBool1=False))
            await a.idle()
            c.client.send(5039, pb.CampaignReqMsg(paraInt2=0, paraBool1=False))
            prepare = pb.BattlePrepareMsg.FromString((await c.until(157))[-1].body)
            got_c = await c.fight(prepare) + await c.idle()
            got_a = await a.until(25) + await a.idle()
            for g, got in ((a, got_a), (c, got_c)):
                won = _result(got) == 1
                expected[g.user_id] = max(0, expected[g.user_id] + (10 if won else -5))
                texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83]
                assert any(t.startswith("Points ") for t in texts)
                score = [pb.PlayerMsg.FromString(p.body).crossScore for p in got if p.code == 3][-1]
                assert score == expected[g.user_id]
        now = datetime.now(UTC)
        states = [e for g in (a, c) for e in _snap(g).events if e.key == ag.KEY]
        order = sorted(expected, key=lambda pid: -expected[pid])
        ranked = ag.ranked(states, now, {})
        assert [p for _, p in ranked] == sorted([v for v in expected.values() if v], reverse=True)
        if expected[order[0]] != expected[order[1]]:
            assert ag.position(states, order[0], now, {}) == 1
        sv = a.server.services
        xml = zlib.decompress(await rankings.cross_order(sv.characters, sv.guilds, 1, sv.clock)).decode()
        assert xml.count("<CrossScoreTotalAdd ") == len(ranked)


def test_ranking_desempata_por_quem_chegou_antes_e_nao_fica_negativo() -> None:
    from datetime import timedelta

    from wartune_server.domain.models import EventState
    from wartune_server.game import arena_grupo as ag

    now = datetime(2026, 10, 29, 12, tzinfo=UTC)
    week = ag.period(now, {})
    late = EventState(1, ag.KEY, now, value=10, text=week)
    early = EventState(2, ag.KEY, now - timedelta(hours=1), value=10, text=week)
    old = EventState(3, ag.KEY, now, value=99, text="2000-01")  # semana passada: zerou
    assert ag.ranked([late, early, old], now, {}) == [(2, 10), (1, 10)]
    assert ag.position([late, early, old], 1, now, {}) == 2
