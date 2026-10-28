"""Masmorras solo com captura (migração 0098): amostra da 1101, 1104, 1107 e 1201."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import battle, enter, fast_battles  # noqa: F401  (fixture)
from tests.test_end_to_end import TEMPLATES
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


@pytest.mark.parametrize(
    ("campaign", "first_map", "fight"),
    [(1101, 1111, 111102), (1104, 1091, 109102), (1107, 1271, 127102), (1201, 1291, 129102)],
)
async def test_entra_e_luta(tmp_path: Path, campaign: int, first_map: int, fight: int) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        got = await enter(g, campaign)
        # (visto) 125 do 1º mapa da captura, com os nós e a névoa
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == first_map
        assert {127, 130} <= {p.code for p in got}
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None and s.campaign.node(fight) is not None
        await battle(g, fight)  # vitória (4103 battleResult 1) checada no battle()


async def test_sem_captura_fica_fechada(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        assert 1101 in s.ctx.world.campaigns and 1602 not in s.ctx.world.campaigns
