"""Tutorial (mapas 10001/10002) com cliente falso: entrar, primeira batalha, missão, retomada."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import DATA
from wartune_server.game import battle as battle_mod
from wartune_server.game.campaign import DONE, NORMAL, CampaignMap
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay")


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0)


def codes(packets: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in packets]


async def test_first_map_battle_and_quest(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        c = g.client
        c.send(5012, pb.QuestAddedMsg(questId=[10]))
        assert codes(await g.until(112)) == [112]

        c.send(5127, pb.NoviceReqMsgMsg(type=1))
        got = await g.until(143)
        assert codes(got) == [125, 140, 21, 127, 130, 143]
        nodes = pb.CampaignNodeListMsg.FromString(got[3].body)
        assert {n.campDataId for n in nodes.node} >= {1000103, 1000108}
        assert pb.RoomEnterMsg.FromString(got[2].body).player[0].curPosX == 24

        c.send(5017, pb.NoviceReqMsgMsg(noviceProcess=11300))
        assert codes(await g.until(1)) == [3, 1]
        c.send(8196, pb.NodeLockReqMsg(nodeId=1000103, lock=True))
        chase = pb.NPCChaseMsg.FromString((await g.until(4105))[-1].body)
        assert chase.nodeId == 9545

        c.send(5124, pb.PosMoveMsg(mapId=10001, armyId=g.user_id, routes=[pb.RouteMsg(x=800, y=1180)]))
        c.send(5125, pb.CampaignReqMsg(paraInt1=1000103, paraBool1=True))
        got = await g.until(157)
        assert codes(got) == [140, 131, 128, 157]
        assert pb.ArmyArmyMsg.FromString(got[1].body).curPosX == 40
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        me = next(h for h in prepare.heros if h.userId == g.user_id)
        assert (me.livingId, me.maxHp, list(me.skillId)) == (1, 200, [30711, 30811])

        c.send(10007, pb.LoadOverMsg(armyId=g.user_id, battleId=prepare.battleId))
        c.send(10008, pb.UseSkillMsg(battleId=prepare.battleId, heroId=1, skillId=30711))
        got = await g.until(128)
        assert set(codes(got)[:2]) == {156, 75} and 153 in codes(got)
        tail = [x for x in codes(got) if x not in (153, 75, 156)]
        assert tail == [154, 3, 4103, 83, 150, 100, 140, 131, 128]
        report = pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body)
        assert (report.battleResult, report.gpBonus) == (1, 5)
        assert pb.CampaignNodeUpdateMsg.FromString(got[-1].body).nodeState == DONE

        c.send(5035, pb.LoginStateMsg(state=4))
        assert pb.FightOverMoiveMsg.FromString((await g.until(4382))[-1].body).gp == 5

        for value in (11400, 11600):
            c.send(5017, pb.NoviceReqMsgMsg(noviceProcess=value))
            assert codes(await g.until(1)) == [3, 1]
        c.send(5017, pb.NoviceReqMsgMsg(noviceProcess=12000))
        got = await g.until(1)
        assert codes(got) == [112, 3, 1]  # missão 10: noviceProcess passou de 11600

        c.send(5014, pb.QuestFinishedReqMsg(templateId=10))
        got = await g.until(52)
        assert codes(got) == [112, 3, 112, 83, 150, 3, 52]
        player = pb.PlayerMsg.FromString(got[-2].body)
        assert (player.grades, player.gp, player.totalGp) == (2, 5, 3005)
        assert player.questSite[1] == 0x02  # bit da missão 10
        hero = pb.ArmyArmyMsg.FromString(got[4].body).simpleHeroInfo
        assert (hero.totalIntellect, hero.intellectPoint, hero.totalLive) == (8, 3, 230)


async def test_portal_chest_and_equip(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=15300) as g:
        c = g.client
        c.send(5127, pb.NoviceReqMsgMsg(type=1))
        await g.until(143)
        c.send(5032, pb.CallBackReqMsg(mapId=10001, nodeId=1000106, cmd=2))  # 1º: batalha já vencida
        c.send(5032, pb.CallBackReqMsg(mapId=10001, nodeId=1000106, cmd=2))  # 2º: Tina segue
        assert codes(await g.until(4122)) == [128, 4124, 4122]

        c.send(5125, pb.CampaignReqMsg(paraInt1=1000108, paraBool1=True))
        got = await g.until(131)
        assert codes(got) == [4208, 125, 127, 130, 4124, 21, 131]
        assert pb.RoomCreatedMsg.FromString(got[1].body).room.campaignId == 10002

        c.send(5125, pb.CampaignReqMsg(paraInt1=1000202, paraBool1=True))
        got = await g.until(150)
        assert codes(got) == [115, 111, 128, 150]
        weapon = pb.ItemMovedListMsg.FromString(got[0].body).moved[0].item
        assert (weapon.templateId, weapon.randomSkill_1, weapon.bagType) == (1013002, 70302, 1)

        hero_id = pb.ArmyArmyMsg.FromString(got[-1].body).simpleHeroInfo.heroId
        c.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=weapon.pos, endBagType=4, endObjId=hero_id, endPos=0))
        got = await g.until(115)
        got += await g.until(115)
        assert codes(got) == [3, 150, 115, 115]
        hero = pb.ArmyArmyMsg.FromString(got[1].body)
        # arma: +24 ataque mágico e o atributo sorteado Zeka+2 (inteligência)
        assert (hero.simpleHeroInfo.totalIntellect, hero.simpleHeroInfo.baseIntellect) == (7, 5)
        assert hero.simpleHeroInfo.totalMagicAttack == 4 * 7 + 24 and hero.arm == "/wizard_arms002"


def test_resume_states() -> None:
    first = CampaignMap.enter(10001, 13000)
    assert first.node(1000104)["state"] == DONE and first.node(1000106)["state"] == NORMAL  # type: ignore[index]
    second = CampaignMap.enter(10002, 18500)
    assert second.escort == 9548 and second.node(1000206)["state"] == NORMAL  # type: ignore[index]
