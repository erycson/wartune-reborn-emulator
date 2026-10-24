"""Orc Plains (1005) e Tribal Plateau (1006): as duas etapas de cada uma, como em ``oficial_20261023-231733-1``
(conteúdo e cartas da migração 0075)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import codes, enter, fast_battles, won  # noqa: F401  (fixture)
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import events
from wartune_server.game.campaign import CampaignMap
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


async def test_elise_passa_a_seguir_o_jogador(tmp_path: Path) -> None:
    """(visto) oficial_20261023-231733-1 #1116-#1123: 5125 na Elise (107302) abre o diálogo e o 5032 do fim dele
    responde 128 state 2 e 4124 com a posição do exército."""
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1005)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None and s.campaign.content is not None
        s.campaign = CampaignMap.enter_dungeon(s.campaign.content, 1073, s.campaign.run)  # a 3ª cena da etapa 1
        c = s.campaign
        elise = c.node(107302)
        assert elise is not None and elise["heroTempId"] == 1051
        g.client.send(5032, pb.CallBackReqMsg(mapId=c.map_id, nodeId=107302, cmd=2))
        got = await g.idle()
        assert codes(got) == [128, 4124]
        node = pb.CampaignNodeUpdateMsg.FromString(got[0].body)
        follow = pb.NPCFollowMsg.FromString(got[1].body)
        assert (node.nodeId, node.nodeState) == (elise["nodeId"], 2)
        assert (follow.escortId, follow.followId, (follow.curPosX, follow.curPosY)) == (
            elise["nodeId"], g.user_id, tuple(c.pos))  # fmt: skip
        g.client.send(5032, pb.CallBackReqMsg(mapId=c.map_id, nodeId=107302, cmd=2))  # já segue
        assert await g.idle() == []


async def test_reforcos_do_gladiador(tmp_path: Path) -> None:
    """(visto) 231733: o 115102 (Tauren Gladiator, grupo de 3 nós) traz duas ondas pelo 72, como o #4459."""
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1006)
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=115102, paraBool1=True))
        assert codes(await g.idle()) == [138]  # o gladiador fala antes
        g.client.send(5032, pb.CallBackReqMsg(mapId=3240, nodeId=115102, cmd=2))
        got = await won(g)
        waves = [pb.ReinforceMsg.FromString(p.body) for p in got if p.code == 72]
        assert [[x.tempId for x in w.soldiers] for w in waves] == [[2061, 2061], [2061, 2061]]
        assert codes(got).index(72) < codes(got).index(4103)
        # (visto) 231733 #3389-#3390: um 4149 por onda logo depois do 156
        start = codes(got).index(156)
        assert codes(got)[start + 1 : start + 3] == [4149, 4149]
        res = [pb.ArmyResMsg.FromString(p.body) for p in got if p.code == 4149]
        assert [(list(r.loadRes[0].soldierTempId), r.reinforceCount, r.reinforceType) for r in res] == [
            ([2061, 2061], 3, 1), ([2061, 2061], 3, 1)]  # fmt: skip
        assert [[x.livingId for x in w.soldiers] for w in waves][0] == sorted(
            x.livingId for w in waves for x in w.soldiers
        )[:2]
