"""Pedidos do cliente sem resposta conferida com a captura (auditoria "SEM DONO"): a sequência de códigos
tem que sair igual à do oficial, com os mesmos textos 111/83."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import ArenaRank
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def codes(packets: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in packets]


async def test_take_reward_sequence_matches_capture(tmp_path: Path) -> None:
    """(visto) 191924-1 #9064-#9069 (oficial 20261025-232017-1): 109, 3, 4243, 111 e 83 com o mesmo texto."""
    async with logged_in(tmp_path, novice=30011) as g:
        await g.server.services.characters.save(ranks=(ArenaRank(g.user_id, 1),))
        g.client.send(8329)
        got = await g.until(83)
        assert codes(got) == [109, 3, 4243, 111, 83]
        text = "Retrieve Ranking Rewards: Golds x"
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg.startswith(text)
        assert (
            pb.ChatChannelMsg.FromString(got[4].body).encodeMsg == pb.ChatChannelMsg.FromString(got[3].body).encodeMsg
        )


async def test_disband_refunds_daru_and_sends_capture_sequence(tmp_path: Path) -> None:
    """(visto) 191924-1 #20734-#20738: 3, 109, 111 "Disband Successful. You gained 51 Daru." e 100."""
    async with logged_in(tmp_path, novice=30012) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        snap.character.gold = 2801
        await g.server.services.characters.save(snap.character)
        g.client.send(5155, pb.ArmyPawnInfoMsg(tempateId=10101, ownPawns=900))
        await g.until(111)
        await g.idle()
        before = snap.character.strategy

        g.client.send(5157, pb.ArmyPawnInfoMsg(tempateId=10101, ownPawns=100))
        got = await g.until(100)
        assert codes(got) == [3, 109, 111, 100]
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Disband Successful. You gained 20 Daru."
        assert snap.character.strategy == before + 20
