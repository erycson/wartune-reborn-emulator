"""Patrulha dos monstros (4122, ``game_settings.npc_patrol`` da 0079): pontos por campDataId das capturas inglesas."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import enter
from tests.test_end_to_end import TEMPLATES
from wartune_server.game.handlers import campaign as hc
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


class _Always(random.Random):
    def random(self) -> float:
        return 0.0


async def test_monstros_andam_entre_os_pontos_vistos(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1006)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None
        berserker = s.campaign.node(115105)
        assert berserker is not None
        pts = {(55, 56), (60, 59), (62, 54)}  # (visto) 231733: 115105 nesses três pontos
        for _ in range(2):
            before = (berserker["curX"], berserker["curY"])
            hc.patrol_tick(s, _Always(1))
            moves = [pb.NPCMoveMsg.FromString(p.body) for p in await g.idle() if p.code == hc.S_NPC_MOVE]
            [m] = [m for m in moves if m.id == berserker["nodeId"]]
            assert (m.curPosX, m.curPosY) in pts and (m.curPosX, m.curPosY) != before
            assert (berserker["curX"], berserker["curY"]) == (m.curPosX, m.curPosY)

        berserker["state"] = hc.FIGHTING  # lutando (ou vencido) fica parado
        hc.patrol_tick(s, _Always(1))
        assert berserker["nodeId"] not in [
            pb.NPCMoveMsg.FromString(p.body).id for p in await g.idle() if p.code == hc.S_NPC_MOVE
        ]
