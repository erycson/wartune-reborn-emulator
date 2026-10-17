"""Herói e exército: tropas, skills, talento, runas, montaria, estrelas, destino, dragão, cartas e pets."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import DATA
from wartune_server.domain.models import Item, PlayerSnapshot
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay")


def codes(packets: list) -> list[int]:  # type: ignore[type-arg]
    return [p.code for p in packets]


def snap_of(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def test_recruit_put_in_army_and_dismiss(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        snap.character.gold = 2801
        await g.server.services.characters.save(snap.character)

        g.client.send(5155, pb.ArmyPawnInfoMsg(tempateId=10101, ownPawns=900))
        got = await g.until(111)
        assert codes(got) == [109, 109, 100, 111]  # o 112 só vem com a missão 52 aberta (relay #643)
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount == 1001  # 2 de ouro por Er
        assert (pb.CastleYieldMsg.FromString(got[1].body).curPopulation, 900) == (900, 900)
        pawn = pb.ArmyPawnUpdatedMsg.FromString(got[2].body).armyPawn[0]
        assert (pawn.armyId, pawn.sonType, pawn.ownPawns, pawn.fightPos, len(pawn.pawnLive)) == (0, 101, 900, 3, 7)
        assert [x.tempData for x in pawn.pawnLive] == [64, 50, 0, 40, 323, 64, 0]  # igual ao relay #647
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg == "Tebrikler,900 tane Er alındı"

        g.client.send(5155, pb.ArmyPawnInfoMsg(tempateId=10101, ownPawns=1))  # casa cheia
        assert await g.idle() == []
        g.client.send(5155, pb.ArmyPawnInfoMsg(tempateId=10201, ownPawns=1))  # arqueiro: quartel nível 4
        assert await g.idle() == []

        g.client.send(5156, pb.ArmyPawnInfoMsg(sites=0, tempateId=10101, ownPawns=150))  # liderança 100
        assert await g.idle() == []
        g.client.send(5156, pb.ArmyPawnInfoMsg(sites=0, tempateId=10101, ownPawns=100))
        got = await g.until(100)
        assert codes(got) == [150, 93, 100]
        army = pb.ArmyArmyMsg.FromString(got[0].body)
        assert (army.armyPawn[0].ownPawns, army.armyPawn[0].armyId) == (100, g.user_id)
        assert pb.ArmyPawnUpdatedMsg.FromString(got[2].body).armyPawn[0].ownPawns == 800

        g.client.send(5156, pb.ArmyPawnInfoMsg(sites=0, tempateId=10101, ownPawns=5000))  # mais que tem
        assert await g.idle() == []

        g.client.send(5157, pb.ArmyPawnInfoMsg(tempateId=10101, ownPawns=50))
        got = await g.until(109)
        assert pb.ArmyPawnUpdatedMsg.FromString(got[0].body).armyPawn[0].ownPawns == 750
        assert pb.CastleYieldMsg.FromString(got[1].body).curPopulation == 850

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert [(p.template_id, p.castle_count, p.army_count) for p in saved.pawns] == [(10101, 750, 100)]

        relogin = await g.connect()  # o 150 do login já traz a tropa
        relogin.client.send(8224, pb.PlayerDataMsg(army=True))
        assert pb.ArmyArmyMsg.FromString((await relogin.until(150))[-1].body).armyPawn[0].ownPawns == 100


async def test_pawn_upgrade_costs_soul_and_needs_barracks(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        snap.character.strategy, snap.leader.grades = 100, 10  # type: ignore[union-attr]
        await g.server.services.characters.save(snap.character, snap.leader)

        g.client.send(5158, pb.ArmyPawnInfoMsg(tempateId=10101))  # quartel nível 1 não deixa ir ao 2
        assert await g.idle() == []
        barracks = next(b for b in snap.buildings if b.template_id == 40201)
        barracks.template_id = 40202
        await g.server.services.characters.save(barracks)

        g.client.send(5158, pb.ArmyPawnInfoMsg(tempateId=10101))
        got = await g.until(109)
        assert codes(got) == [3, 116, 150, 109]
        assert pb.PlayerMsg.FromString(got[0].body).strategy == 84  # 16 de Ruh (UpGrade Types 1)
        assert pb.ArmyPawnInfoMsg.FromString(got[1].body).tempateId == 10102


async def test_skills_second_set_and_reset(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:  # maga: skills 30711 e 30811
        snap = snap_of(g)
        snap.leader.grades, snap.character.point = 8, 600  # type: ignore[union-attr]
        await g.server.services.characters.save(snap.character, snap.leader)

        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=30111, type=0))
        got = await g.until(60)
        assert codes(got) == [150, 60]  # relay #1175
        hero = pb.ArmyArmyMsg.FromString(got[0].body).simpleHeroInfo
        assert (hero.skillScript, hero.skillPoint) == ("30711,30811,30111,", 1)  # nível 8 = 4 - 3
        skill = pb.UpdatedSkillMsg.FromString(got[1].body)
        assert (skill.templateId, skill.index, skill.type) == (30111, 2, 0)

        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=30111))  # já aprendida
        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=10111))  # de guerreiro
        assert await g.idle() == []

        g.client.send(8479, pb.PayTypeMsg(payType=1))
        got = await g.until(3)
        assert codes(got) == [150, 3] and pb.PlayerMsg.FromString(got[1].body).point == 0
        g.client.send(8480, pb.HeroSkillChangeMsg(index=1))
        hero = pb.ArmyArmyMsg.FromString((await g.until(150))[-1].body).simpleHeroInfo
        assert (hero.skillIndex, hero.isActiveSecond, hero.skillScript, hero.skillPoint) == (1, True, "30711,30811,", 2)

        g.client.send(8480, pb.HeroSkillChangeMsg(index=0))
        await g.until(150)
        g.client.send(5184, pb.PayTypeMsg(payType=0, type=0))  # abaixo do nível 25: grátis
        got = await g.until(150)
        assert codes(got) == [61, 150]
        assert pb.ArmyArmyMsg.FromString(got[1].body).simpleHeroInfo.skillScript == "30711,30811,"


async def test_talent_grade_and_learn(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        snap.leader.grades = 40  # type: ignore[union-attr]
        await g.server.services.characters.save(snap.leader)

        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=100101))  # talento ainda no grau 0
        assert await g.idle() == []
        g.client.send(5187, pb.TalentUpGradeMsg())
        got = await g.until(109)
        assert codes(got) == [4430, 4431, 3, 109]
        talent = pb.HeroTalentMsg.FromString(got[1].body)
        assert (talent.talentGrade, talent.talentPoint) == (1, 1)
        g.client.send(5187, pb.TalentUpGradeMsg())  # grau 2: 20.000 de ouro
        assert codes(await g.until(4430)) == [4430]

        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=100101))
        got = await g.until(60)
        hero = pb.ArmyArmyMsg.FromString(got[0].body).simpleHeroInfo
        assert (hero.talentGrade, hero.talentPoint, hero.talentSkill) == (1, 0, "100101")
        assert pb.UpdatedSkillMsg.FromString(got[1].body).type == 1


async def test_rune_learn_upgrade_and_equip(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        snap.leader.grades = 38  # type: ignore[union-attr]
        book, exp = Item(g.user_id, 3020002, pos=0), Item(g.user_id, 3020010, pos=1, count=12)
        snap.items.extend([book, exp])
        await g.server.services.characters.save(snap.leader, book, exp)

        g.client.send(8605, pb.HeroRuneOpMsg(opType=1, runeId=201, learnRunePos=0, learnRuneCount=1))
        got = await g.until(150)
        assert codes(got) == [115, 4495, 150]
        op = pb.HeroRuneOpMsg.FromString(got[1].body)
        assert op.opResult and [(r.runeId, r.runeGp) for r in op.runeInfo.runeinfo] == [(201, 0)]

        g.client.send(8605, pb.HeroRuneOpMsg(opType=2, runeId=201, count=11))  # 550 EXP: sobe ao 202
        got = await g.until(150)
        op = pb.HeroRuneOpMsg.FromString(got[1].body)
        assert [(r.runeId, r.runeGp) for r in op.runeInfo.runeinfo] == [(202, 50)]
        assert pb.ItemMovedListMsg.FromString(got[0].body).moved[0].item.count == 1

        g.client.send(8605, pb.HeroRuneOpMsg(opType=3, runeKey="202,-1,"))
        op = pb.HeroRuneOpMsg.FromString((await g.until(4495))[-1].body)
        assert (op.opResult, op.runeInfo.runeKey) == (True, "202,-1,")
        g.client.send(8605, pb.HeroRuneOpMsg(opType=3, runeKey="301,-1,"))  # não aprendida
        assert pb.HeroRuneOpMsg.FromString((await g.until(4495))[-1].body).opResult is False
