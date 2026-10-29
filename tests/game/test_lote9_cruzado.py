"""Lote 9: assistir batalha (8985 -> 4804/157/4803) e o PvP entre servidores como fila local (8779 -> luta,
pontos ``crossScore``, 4481 e o prêmio do 8590/4482)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import arena_grupo as ag
from wartune_server.game import bag
from wartune_server.game import events as ev
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
INSIGNIA = 208001


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


def _prop(got: list[Packet], code: int) -> pb.SimplePropertyMsg:
    return pb.SimplePropertyMsg.FromString([p for p in got if p.code == code][-1].body)


async def test_fila_local_pareia_e_espectador_assiste(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        c, d = await a.join("cacador"), await a.join("druida")
        a.client.send(8779, pb.CrossGuildMsg())
        assert 111 in [p.code for p in await a.idle()]  # sozinho: espera na fila
        c.client.send(8779, pb.CrossGuildMsg())
        prepare = pb.BattlePrepareMsg.FromString((await c.until(157))[-1].body)
        assert prepare.battleType == 10
        seen = pb.BattlePrepareMsg.FromString((await a.until(157))[-1].body)  # o outro assiste a própria cópia
        assert seen.battleId == prepare.battleId

        d.client.send(8985, pb.BattleViewMsg(type=0, sonType=1, userId=c.user_id))
        assert _prop(await d.idle(), 4804).param7 is False  # há luta: o cliente pede para entrar
        d.client.send(8985, pb.BattleViewMsg(type=1, userId=c.user_id))
        assert pb.BattlePrepareMsg.FromString((await d.until(157))[-1].body).battleId == prepare.battleId
        d.client.send(8985, pb.BattleViewMsg(type=-1))
        assert _prop(await d.until(4803), 4803).param7

        got_c = await c.fight(prepare) + await c.idle()
        got_a = await a.until(4803) + await a.idle()
        won = pb.BattleReportMsg.FromString(next(p.body for p in got_c if p.code == 4103)).battleResult == 1
        assert _prop(got_a, 4803).param1 == (1 if won else 2)  # o espectador fecha a tela no fim
        assert 4103 in [p.code for p in got_a]
        pts = {g.user_id: [pb.PlayerMsg.FromString(p.body).crossScore for p in got if p.code == 3][-1]
               for g, got in ((c, got_c), (a, got_a))}  # fmt: skip
        assert pts[c.user_id if won else a.user_id] == 10

        d.client.send(8985, pb.BattleViewMsg(type=0, sonType=1, userId=c.user_id))
        assert _prop(await d.idle(), 4804).param7  # acabou


async def test_premio_dos_pontos_cruzados(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(8590, pb.ChallengeRankRewardMsg())
        assert pb.ChallengeRankRewardMsg.FromString((await a.until(4482))[-1].body).param3 == 0  # sem pontos

        snap, now = _snap(a), datetime.now(UTC)
        st = ev.state(snap, ag.KEY, now)
        st.value, st.text = 1200, ag.period(now, {})
        await a.server.services.characters.save(st)
        before = bag.count_of(snap, INSIGNIA)
        a.client.send(8590, pb.ChallengeRankRewardMsg())
        got = pb.ChallengeRankRewardMsg.FromString((await a.until(4482))[-1].body)
        assert (got.param2, got.param3, got.param4) == (1200, 1, 1)  # 1º do ranking: título
        assert bag.count_of(snap, INSIGNIA) == before + 1
        await a.idle()
        a.client.send(8590, pb.ChallengeRankRewardMsg())
        assert pb.ChallengeRankRewardMsg.FromString((await a.until(4482))[-1].body).param3 == 0  # uma vez só
