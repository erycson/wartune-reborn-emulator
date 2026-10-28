"""Camp Calorn (1007): a 1ª etapa como em ``oficial_20261024-191924-1`` #2345-#3706 (conteúdo da migração 0090)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import battle, codes, enter, fast_battles, won  # noqa: F401  (fixture)
from tests.test_end_to_end import TEMPLATES
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


async def test_etapa_1_ate_o_chefe(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        got = await enter(g, 1007)
        # (visto) #2346-#2353: 125 do 1171, nós, névoa e o diálogo da Elise na entrada
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == 1171
        assert {127, 130, 138} <= set(codes(got))
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None
        portal = s.campaign.node(117105)
        assert portal is not None and portal["state"] == 16  # fechado até o grupo cair

        await battle(g, 117103)
        got = await battle(g, 117104)  # (visto) #2558-#2559: o grupo cai e o portal abre
        opened = [pb.CampaignNodeUpdateMsg.FromString(p.body) for p in got if p.code == 128]
        assert (portal["nodeId"], 1) in [(n.nodeId, n.nodeState) for n in opened]

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=117105, paraBool1=True))  # (visto) #2613-#2615
        got = await g.idle()
        assert pb.RoomCreatedMsg.FromString(next(p.body for p in got if p.code == 125)).room.campaignId == 1172

        # (visto) #2989-#3003: o Viscount Remus fala no 5125 e luta no 5032 do fim do diálogo
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=117204, paraBool1=True))
        assert 138 in codes(await g.idle())
        g.client.send(5032, pb.CallBackReqMsg(mapId=s.campaign.map_id, nodeId=117204, cmd=2))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        assert prepare.mapTempId == 1172 and any(h.tempId == 1071 for h in prepare.heros)
