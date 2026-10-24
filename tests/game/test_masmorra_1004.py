"""Temple of Ibalize (Inner), campanha 1004 (sala 1051): entrada, baú de prata pago com ouro e as cartas do fim.

Ordem e textos de ``captures/oficial_20261023-171155-1.json`` (#5249-#5831); conteúdo da migração 0069.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import codes, enter, fast_battles, won  # noqa: F401  (fixture)
from tests.game.test_masmorra_1002_pedreira import confirm, text
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import rules
from wartune_server.game.campaign import DONE
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

SILVER, LUCK, STATUE = 105110, 2040101, 105103


async def test_1004_entra_na_sala_1051(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        got = await enter(g, 1004)
        assert 125 in codes(got) and 127 in codes(got)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.campaign is not None
        assert session.campaign.map_id == 1051
        # (visto) #5828: a carta deu Skeleton Key, fora do Campaigns.Item
        assert 208005 in [t for t, _ in session.ctx.world.campaign_cards[1004]]


async def test_bau_de_prata_cobra_1000_de_ouro(tmp_path: Path) -> None:
    """(visto) #5608-#5627: 109 sem o ouro, 128 DONE (param1 -100), 115 da Lvl. 1 Luck Stone, 111 e 83."""
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1004)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None and session.campaign is not None
        c, snap = session.campaign, session.snapshot

        snap.character.gold = 999
        assert codes(await confirm(g, SILVER)) == []  # sem ouro: nada
        snap.character.gold = 5000
        got = await confirm(g, SILVER)
        assert codes(got) == [109, 128, 115, 111, 83]
        node = pb.CampaignNodeUpdateMsg.FromString(got[1].body)
        assert (node.nodeState, node.param1) == (DONE, -100)
        assert text(got[3]) == text(got[4]) == "Received: Lvl. 1 Luck Stone x1"
        assert snap.character.gold == 4000 and rules.goods_count(snap, LUCK) == 1
        assert c.node(SILVER)["state"] == DONE  # type: ignore[index]


@pytest.mark.usefixtures("fast_battles")
async def test_fim_de_luta_na_ordem_da_1004(tmp_path: Path) -> None:
    """(visto) #5318-#5325: 3, 3 (o Daru e a EXP), 4103, 150, 100, 140, 131, 128 e o 83 "Received 81 EXP " no fim."""
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1004)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=STATUE, paraBool1=True))
        got = await won(g)
        end = [c for c in codes(got) if c in (3, 4103, 150, 100, 140, 131, 128, 83)]
        start = end.index(4103) - 2
        assert end[start : start + 9] == [3, 3, 4103, 150, 100, 140, 131, 128, 83]
        exp = pb.ChatChannelMsg.FromString([p for p in got if p.code == 83][-1].body).encodeMsg
        assert exp == "Received 81 EXP "
        report = pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103))
        assert report.petGpBonus == 0
