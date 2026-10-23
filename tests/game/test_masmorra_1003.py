"""Temple of Ibalize (Outer), campanha 1003 (salas 1031 e 1032): entrada, alavanca do Temple Hub e o chefe.

Ordem e textos de ``captures/oficial_20261023-153200-1.json``; conteúdo da migração 0058.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import codes, enter, fast_battles, take  # noqa: F401  (fixture)
from tests.test_end_to_end import TEMPLATES
from wartune_server.game.campaign import DONE, HIDDEN, NORMAL
from wartune_server.game.handlers import campaign as handlers
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

HUB, GATE, BOSS = 103204, 103205, 103207


async def test_1003_entra_e_a_alavanca_mostra_o_chefe(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        got = await enter(g, 1003)
        assert 125 in codes(got) and 127 in codes(got)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.campaign is not None
        c = session.campaign
        assert c.map_id == 1031 and c.run is not None and c.run.maps == (1031, 1032)

        handlers._enter_dungeon(session, c.content or {}, 1032, c.run, handlers.PORTAL_ENTER)  # o portal 103107
        await g.idle()
        c = session.campaign
        assert c is not None and c.node(BOSS)["state"] == 9  # type: ignore[index]

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=HUB, paraBool1=True))
        got = await g.idle()
        # (visto) #1119-#1126: 126, 142, 143 DISAPPEARD, 142, 128 da alavanca, 143 FLICKER, 142 (0, 0), 128 do chefe
        assert codes(got) == [126, 142, 143, 142, 128, 143, 142, 128]
        assert pb.CampaignNotifyMsg.FromString(got[0].body).body == "Successfully open the outer temple."
        assert [p.extend2 for p in got] == [25, 25, 35, 75, 0, 85, 125, 0]
        assert pb.PlayerMovieMsg.FromString(got[2].body).movieType == "DISAPPEARD"
        assert (c.node(HUB)["state"], c.node(GATE)["state"], c.node(BOSS)["state"]) == (DONE, HIDDEN, NORMAL)  # type: ignore[index]
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=HUB, paraBool1=True))
        assert await g.idle() == []  # a alavanca já foi

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=BOSS, paraBool1=True))
        got = await g.idle()
        assert 138 in codes(got)  # o diálogo do chefe antes da luta (plots[103207])
