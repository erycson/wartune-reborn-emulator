"""Tutorial (mapas 10001/10002) com cliente falso: entrar, primeira batalha, missão, retomada."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import battle as battle_mod
from wartune_server.game.campaign import DONE, NORMAL, CampaignMap
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)


def codes(packets: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in packets]


async def test_first_map_battle_and_quest(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        c = g.client  # a missão 10 já nasce com o personagem (captura EN #81, sem 5012)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        assert [q.template_id for q in session.snapshot.quests] == [10]

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
        assert chase.nodeId == 14037

        c.send(5124, pb.PosMoveMsg(mapId=10001, armyId=g.user_id, routes=[pb.RouteMsg(x=800, y=1180)]))
        c.send(5125, pb.CampaignReqMsg(paraInt1=1000103, paraBool1=True))
        got = await g.until(157)
        assert codes(got) == [140, 131, 128, 157]
        assert pb.ArmyArmyMsg.FromString(got[1].body).curPosX == 40
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        me = next(h for h in prepare.heros if h.userId == g.user_id)
        assert (me.livingId, me.maxHp, list(me.skillId)) == (1, 200, [30711, 30811])

        got = await g.fight(prepare)
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
        assert codes(got) == [112, 3, 112, 150, 3, 52]  # captura EN #211-#216; o 83 da EXP vem depois do 52 (#218)
        progress = pb.QuestUpdatedRspMsg.FromString(got[0].body).quest[0]
        assert (progress.condition_1, progress.isComplete) == (12000, False)  # tipo 23: o noviceProcess (#211)
        assert pb.PlayerMsg.FromString(got[1].body).grades == 1  # o 3 antes da recompensa
        exp = await g.until(83)
        assert pb.ChatChannelMsg.FromString(exp[-1].body).encodeMsg == "Received 3,000 EXP "
        player = pb.PlayerMsg.FromString(got[-2].body)
        assert (player.grades, player.gp, player.totalGp) == (2, 5, 3005)
        assert player.questSite[1] == 0x02  # bit da missão 10
        hero = pb.ArmyArmyMsg.FromString(got[3].body).simpleHeroInfo
        assert (hero.totalIntellect, hero.intellectPoint, hero.totalLive) == (8, 3, 230)
        assert hero.grade == 2  # sem isso o cliente zera o nível e não aceita missões (NeedMinLevel)


async def test_portal_chest_and_equip(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=15300) as g:
        c = g.client
        c.send(5127, pb.NoviceReqMsgMsg(type=1))
        await g.until(143)
        c.send(5032, pb.CallBackReqMsg(mapId=10001, nodeId=1000106, cmd=2))  # urso já vencido: Tina segue
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
    assert second.escort == 14040 and second.node(1000206)["state"] == NORMAL  # type: ignore[index]


async def test_second_map_to_castle(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=18000) as g:
        c = g.client
        c.send(5127, pb.NoviceReqMsgMsg(type=1))
        assert codes(await g.until(143)) == [125, 140, 21, 127, 130, 4124, 143]

        c.send(5125, pb.CampaignReqMsg(paraInt1=1000208, paraBool1=True))
        got = await g.until(128)
        assert codes(got) == [4162, 128]
        assert (
            pb.PlayerMoveMsg.FromString(got[0].body).tarX,
            pb.PlayerMoveMsg.FromString(got[0].body).ismoveCamera,
        ) == (32, True)

        c.send(5125, pb.CampaignReqMsg(paraInt1=1000205, paraBool1=True))
        assert codes(await g.until(138)) == [138]
        c.send(5032, pb.CallBackReqMsg(mapId=878, nodeId=1000205, cmd=2))
        got = await g.until(157)
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert prepare.battleType == 18 and any(h.tempId == 1005 for h in prepare.heros)  # Tina aliada
        got = await g.fight(prepare)
        updates = [pb.CampaignNodeUpdateMsg.FromString(p.body) for p in got if p.code == 128]
        assert [(u.nodeId, u.nodeState) for u in updates] == [(14047, 8), (14048, 1), (14049, 1)]

        c.send(5017, pb.NoviceReqMsgMsg(noviceProcess=18600))
        await g.until(1)
        c.send(5125, pb.CampaignReqMsg(paraInt1=1000206, paraBool1=True))
        assert codes(await g.until(134)) == [4165, 150, 140, 4152, 83, 134]  # inglesa #517-#523: devoção do leed 4

        c.send(9525, pb.MapBossQuestMsg(mapId=1))
        assert codes(await g.until(4938)) == [4938]
        c.send(8201, pb.PhysicUpdateReqMsg(reqGrid="0_0", mapId=1))
        got = await g.until(169)
        assert pb.PhysicListUpdateMsg.FromString(got[0].body).baseCastle[0].occupyPlayerId == g.user_id

        c.send(8251)
        got = await g.until(157)
        assert codes(got) == [140, 140, 157]
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert prepare.battleType == 15
        got = await g.fight(prepare)
        report = pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body)
        assert (report.battleResult, report.battleScene) == (1, 1)
        assert [x for x in codes(got) if x not in (153, 75, 156)][-4:] == [154, 4103, 140, 140]

        c.send(8747, pb.SimplePropertyMsg(param7=True))
        assert codes(await g.until(4382)) == [4382]
        c.send(8281)
        got = await g.until(104)
        assert codes(got) == [109, 109, 100, 4130, 104]
        # replay #578: o Er vem com 0 e libera o "Asker Al" do quartel (canRecruit no cliente)
        pawn = pb.ArmyPawnUpdatedMsg.FromString(got[2].body).armyPawn
        assert [(p.tempateId, p.ownPawns) for p in pawn] == [(10101, 0)]


@pytest.mark.parametrize("callbacks", [0, 1])
async def test_escort_survives_relog(tmp_path: Path, callbacks: int) -> None:
    """Relogou no 15300: a Tina já vem seguindo, com ou sem o cliente repetir o 5032."""
    async with logged_in(tmp_path, novice=15300) as g:
        g.client.send(5127, pb.NoviceReqMsgMsg(type=1))
        got = await g.until(143)
        assert codes(got) == [125, 140, 21, 127, 130, 4124, 143]
        assert pb.NPCFollowMsg.FromString(got[5].body).escortId == 14040
        for _ in range(callbacks):
            g.client.send(5032, pb.CallBackReqMsg(mapId=10001, nodeId=1000106, cmd=2))
            assert codes(await g.until(4122)) == [128, 4124, 4122]


async def test_chest_gives_weapon_once(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=16500) as g:
        for _ in range(2):  # relogar antes do 16700 reabre o baú
            g.client.send(5127, pb.NoviceReqMsgMsg(type=1))
            await g.until(143)
            g.client.send(5125, pb.CampaignReqMsg(paraInt1=1000202, paraBool1=True))
            got = await g.until(150)
        assert codes(got) == [128, 150]
