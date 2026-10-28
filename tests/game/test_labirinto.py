"""Forgotten Catacombs (game/maze.py, handlers/tower.py): entrada, luta, portal, baú e varredura contra as capturas
turcas yeralti_labirenti_ve_ilk_mob e labirent_sandik_toplama_odulu (só turco)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item, PlayerSnapshot
from wartune_server.game import battle as battle_mod
from wartune_server.game import maze as mz
from wartune_server.game import sweep as sw
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
READY = 19000


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


def _tower(g: Game) -> mz.Tower:
    s = g.server.online.get(g.user_id)
    assert s is not None
    return mz.load(_snap(g), s.ctx.clock.now())


def _set(g: Game, tower: mz.Tower) -> None:
    s = g.server.online.get(g.user_id)
    assert s is not None
    mz.store(_snap(g), tower, s.ctx.clock.now())


async def _win(g: Game, camp: int, monkeypatch: pytest.MonkeyPatch) -> list:  # type: ignore[type-arg]
    async def win(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side != 1:
                unit.hp = 0  # o personagem novo não vence os lobos
        return True

    monkeypatch.setattr(battle_mod.Battle, "_fight", win)
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
    got = await g.until(157)
    return await g.fight(pb.BattlePrepareMsg.FromString(got[-1].body)) + await g.idle()


def test_os_andares_saem_dos_templates() -> None:
    """(só turco: yeralti #37, #84) os nós do 8002/8003; o andar 5 é de chefe, com o baú; o 100 não tem portal."""
    from wartune_server.templates.repository import GameTemplates

    t = GameTemplates.parse(TEMPLATES.read_bytes())
    c = mz.content(t, mz.DEFAULT)
    nodes = {n["campDataId"]: n for n in c["maps"]["8003"]["nodes"]}
    assert nodes[800302]["nodeName"] == "Rage Worg" and nodes[800302]["param4"] == "800304"
    assert (nodes[800304]["masterType"], nodes[800304]["state"], nodes[800304]["param1"]) == (62, 16, 8004)
    assert c["portals"]["800304"] == 8004 and c["battles"]["800302"]["gpBonus"] == 1200
    assert c["battles"]["800502"]["heroes"][0]["nickName"] == "Bloodthirsty Narosa"
    assert c["maze_chests"]["800503"] == [[2050701, 2], [208009, 2]]
    assert "800104" not in c["maps"]["8100"]["nodes"][1]["param4"] and "810004" not in c["portals"]


async def test_start_luta_portal_e_varredura(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        g.client.send(8297, pb.TowerInfoReqMsg(index=0))
        info = pb.TowerInfoMsg.FromString((await g.until(4205))[-1].body)
        assert (info.towerIndex, info.maxIndex, info.campaignId, info.freeEnterCount) == (0, 0, 8001, 1)

        g.client.send(8296, pb.EnterTowerInfoMsg(campaignId=8001, chooseIndex=1, isDouble=1))
        got = await g.until(4152)
        codes = [p.code for p in got]
        # (só turco: #26-#39) sem cartas, sem 4902/4903; vida cheia, sem o 83 da poção; o 4152 do leed 23 no fim
        assert codes == [4205, 4165, 150, 150, 125, 140, 21, 3, 150, 127, 4205, 4152], codes
        assert pb.RoomCreatedMsg.FromString(got[4].body).room.campaignId == 8001
        assert _tower(g).enters == 1 and _tower(g).index == 1

        got = await _win(g, 800102, monkeypatch)
        codes = [p.code for p in got]
        report = pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103))
        assert report.battleResult == 1, (report, codes)
        assert codes.index(4373) < codes.index(131)  # (só turco: #75)
        assert _tower(g).record == 1 and _tower(g).gp > 0
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=800104, paraBool1=True))
        got = await g.until(131)
        codes = [p.code for p in got]
        assert codes[codes.index(125) :] == [125, 127, 130, 21, 4205, 131]  # (só turco: #83-#88)
        assert pb.TowerInfoMsg.FromString(got[codes.index(4205)].body).towerIndex == 2

        g.client.send(8296, pb.EnterTowerInfoMsg(campaignId=8001, chooseIndex=1))  # já dentro: nada
        assert 4205 not in [p.code for p in await g.idle()]


async def test_varredura_do_labirinto(tmp_path: Path) -> None:
    """(só turco: yeralti #2-#26) a varredura do andar 1 acelerada: 4425 status 11 com cIndex/eIndex 1, o 83 da EXP;
    o totalGp sobe 400 e o andar vai a 2."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = _snap(g)
        snap.character.gold, snap.character.point = 100_000, 100
        _set(g, mz.Tower(index=1, record=60))
        g.client.send(8528, pb.CampaignSweepReq(sweepType=2, opType=1, campaignId=8001, eIndex=1, enterType=1))
        got = await g.until(4425)
        assert [p.code for p in got][-3:] == [109, 140, 4425]
        start = pb.CampaignSweepRsp.FromString(got[-1].body)
        assert (start.status, start.sweepType, len(start.result)) == (sw.OK, 2, 0)
        g.client.send(8528, pb.CampaignSweepReq(sweepType=2, opType=2, campaignId=8001, payType=1))
        got = await g.until(83)
        done = pb.CampaignSweepRsp.FromString(next(p.body for p in got if p.code == 4425))
        assert done.status == sw.DONE and [(r.cIndex, r.eIndex, r.gp) for r in done.result] == [(1, 1, 400)]
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Received 400 EXP "
        assert (_tower(g).index, _tower(g).gp, snap.character.gold) == (2, 400, 99_000)
        g.client.send(8528, pb.CampaignSweepReq(sweepType=2, opType=1, campaignId=8001, eIndex=60))
        assert pb.CampaignSweepRsp.FromString((await g.until(4425))[-1].body).status == sw.BUSY


async def test_bau_do_chefe(tmp_path: Path) -> None:
    """(só turco: labirent_sandik #1-#18) o baú depois do chefe do andar 5: 128 DONE, 115, 111, 4205 com os itens."""
    async with logged_in(tmp_path, novice=READY) as g:
        _set(g, mz.Tower(index=5, record=60))
        g.client.send(8296, pb.EnterTowerInfoMsg(campaignId=8001, chooseIndex=0))
        await g.idle()
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None
        s.campaign.nodes[800502]["state"] = 8  # o chefe já caiu
        s.campaign.nodes[800503]["state"] = 1
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=800503, paraBool1=True))
        got = await g.until(83)
        codes = [p.code for p in got]
        assert codes[:2] == [128, 115] and codes[-3:] == [111, 4205, 83]
        assert pb.TowerInfoMsg.FromString(got[-2].body).itemTempIds == "2050701,2|208009,2"
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg.startswith("Received")
        assert {i.template_id for i in _snap(g).items if isinstance(i, Item)} >= {2050701, 208009}
