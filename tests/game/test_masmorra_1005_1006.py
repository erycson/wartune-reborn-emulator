"""Orc Plains (1005) e Tribal Plateau (1006): as duas etapas de cada uma, como em ``oficial_20261023-231733-1``
(conteúdo e cartas da migração 0075)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import codes, enter
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import events
from wartune_server.game.handlers.campaign import STAGE_KEY
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


@pytest.mark.parametrize(
    ("campaign", "first", "second", "card"),
    [(1005, 1071, 1081, 1043103), (1006, 1151, 1161, 208015)],  # (visto) #320/#2121, #3254/#4160; #1313, #3908
)
async def test_etapas_e_cartas(tmp_path: Path, campaign: int, first: int, second: int, card: int) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        got = await enter(g, campaign)
        assert 127 in codes(got)
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == first
        assert card in [t for t, _ in s.ctx.world.campaign_cards[campaign]]

        s.campaign = None
        events.state(s.snapshot, STAGE_KEY.format(campaign), s.ctx.clock.now()).value = 1  # 1ª etapa vencida
        got = await enter(g, campaign)
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == second


async def test_elite_da_1151_tem_luta(tmp_path: Path) -> None:
    """TODO(inventado) 0075: o 115116 nunca foi lutado; a luta é o herói 1062 sozinho, como o Kronos."""
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1006)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None
        spec = s.campaign.battle_like(115116)
        assert spec is not None and [h["tempId"] for h in spec["heroes"]] == [1062]
