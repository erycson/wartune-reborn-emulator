"""Herói e exército: tropas, skills, talento, runas, montaria, estrelas, destino, dragão, cartas e pets."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import DATA
from wartune_server.domain.models import Item, Pet, PlayerSnapshot
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


async def test_stars_rand_pick_equip_eat_lock_and_shop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from wartune_server.game.handlers import stars

    rolls = iter(["202", "302", "4"])  # verde de ataque, verde de defesa, fonte de energia
    monkeypatch.setattr(stars, "roll", lambda t, g, s: t.get("starTempInfos", int(next(rolls))))
    monkeypatch.setattr(stars, "OPEN_NEXT", 0)
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        snap.character.gold, snap.character.grades, snap.character.point = 8000, 20, 100
        assert snap.systems is not None
        snap.systems.star_free, snap.systems.star_day = 0, "2000-01-01"  # gastou ontem e estava offline às 5h
        await g.server.services.characters.save(snap.character, snap.systems)

        g.client.send(8269, pb.StarRandReqMsg(site=0))  # grátis do dia
        got = await g.until(4180)
        assert codes(got) == [109, 3, 4180] and pb.PlayerMsg.FromString(got[1].body).startFree == 0
        for _ in range(2):
            g.client.send(8269, pb.StarRandReqMsg(site=0))
            await g.until(4180)
        assert snap.character.gold == 0  # 2 x 4000
        g.client.send(8269, pb.StarRandReqMsg(site=0))  # sem ouro
        g.client.send(8269, pb.StarRandReqMsg(site=1))  # cristal apagado
        assert await g.idle() == []

        g.client.send(8268, pb.StarPickReqMsg(dropsite=-1))
        got = await g.until(3)
        assert codes(got) == [109, 4179, 4178, 4179, 3]  # a fonte de energia vira StarPoint
        assert pb.PlayerMsg.FromString(got[-1].body).starpoint == 1000
        assert [(s.bag_type, s.pos) for s in snap.stars] == [(1, 0), (1, 1)]

        g.client.send(8267, pb.StarMoveReqMsg(beginStarType=1, beginPos=0, endStarType=2, endPos=0))
        assert codes(await g.until(150)) == [4178, 150]
        g.client.send(8267, pb.StarMoveReqMsg(beginStarType=1, beginPos=1, endStarType=2, endPos=2))  # 2 espaços
        assert await g.idle() == []
        g.client.send(8267, pb.StarMoveReqMsg(beginStarType=1, beginPos=1, endStarType=2, endPos=0, eat=True))
        got = await g.until(150)
        moved = pb.StarMoveRspMsg.FromString(got[0].body).move
        assert [(m.changeType, m.changePos, m.star_Info.gp) for m in moved] == [(1, 1, 0), (2, 0, 10)]

        g.client.send(8330, pb.StarLockReqMsg(starType=2, pos=0))
        assert pb.StarMoveRspMsg.FromString((await g.until(4178))[-1].body).move[0].star_Info.isLock

        g.client.send(8270, pb.PayTypeMsg(payType=1))
        assert pb.PlayerMsg.FromString((await g.until(3))[-1].body).starCount == 1
        g.client.send(8341, pb.StarShopMsg(goodId=1605))  # 7000 de StarPoint: não tem
        assert await g.idle() == []
        g.client.send(8341, pb.StarShopMsg(goodId=4))
        got = await g.until(3)
        assert pb.StarMoveRspMsg.FromString(got[0].body).move[0].star_Info.templateId == 4

        relogin = await g.connect()
        relogin.client.send(8224, pb.PlayerDataMsg(star=True))
        got = await relogin.until(4180)
        assert len(pb.StarMoveRspMsg.FromString(got[-2].body).move) == 2


async def test_mount_list_train_and_change(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        sy = snap.systems
        assert sy is not None
        sy.mount_avatars, sy.mount_template, sy.mount_gp = "1000,1103", 1103, "1610,270,970,1160"
        food = Item(g.user_id, 208017, pos=0, count=9)
        snap.items.append(food)
        await g.server.services.characters.save(sy, food)

        g.client.send(8530)
        got = await g.until(4426)
        assert codes(got) == [4427, 4426]
        assert pb.MountAvatarMsg.FromString(got[0].body).soulScore == 400  # igual ao login #11
        info = pb.MountInfoMsg.FromString(got[1].body)
        assert (info.power, info.intellect, info.physique, info.agility, info.levelMax) == (65, 35, 55, 60, 25)

        g.client.send(8529, pb.MountEditMsg(op=1, propertyType=0, payType=1, param1=9))
        got = await g.until(4426)
        assert codes(got) == [115, 3, 150, 4426]
        info = pb.MountInfoMsg.FromString(got[-1].body)
        assert (info.power, info.powerGp, info.mountTotalGp) == (70, 1700, 4100)  # captura de treino #90
        assert pb.ArmyArmyMsg.FromString(got[2].body).mountTempId == 1103
        g.client.send(8529, pb.MountEditMsg(op=1, propertyType=0, payType=1, param1=1))  # acabou a comida
        g.client.send(8529, pb.MountEditMsg(op=2, param1=2000))  # não possui
        assert await g.idle() == []
        g.client.send(8529, pb.MountEditMsg(op=2, param1=1000))
        assert pb.MountInfoMsg.FromString((await g.until(4426))[-1].body).mountTempId == 1000


async def test_fate_train_and_turn(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        g.client.send(8628)  # abaixo do nível 55
        assert await g.idle() == []
        snap.character.grades = 55
        stones = Item(g.user_id, 208024, pos=0, count=5)
        snap.items.append(stones)
        await g.server.services.characters.save(snap.character, stones)

        g.client.send(8628)
        fates = pb.FateListMsg.FromString((await g.until(4544))[-1].body).fateInfo
        assert [(f.templateId, f.fateTypes, f.grades) for f in fates] == [(2000, 2000, 0), (2100, 3000, 0)]
        g.client.send(8626, pb.FateEditMsg(skillSonType=2000, useItemCount=6))  # só tem 5
        assert await g.idle() == []
        g.client.send(8626, pb.FateEditMsg(skillSonType=2000, useItemCount=5))
        got = await g.until(4544)
        assert codes(got) == [115, 4544]
        assert pb.FateListMsg.FromString(got[1].body).fateInfo[0].totalGp == 5

        g.client.send(8627, pb.FateEditMsg(turnNum=1))  # grátis do dia
        got = await g.until(115)
        turn = pb.FateEditMsg.FromString(got[0].body)
        assert turn.isSuccess and turn.currCount == 1 and len(turn.count) == 1
        assert pb.ItemMovedListMsg.FromString(got[1].body).moved[0].item.templateId == 208024
        g.client.send(8627, pb.FateEditMsg(turnNum=1))  # 10 diamantes: não tem
        assert pb.FateEditMsg.FromString((await g.until(4545))[-1].body).isSuccess is False


async def test_dragon_feed_and_powcard(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        sy = snap.systems
        assert sy is not None
        snap.character.grades, sy.powcards = 40, "10001:1:12:0"
        food = Item(g.user_id, 208032, pos=0, count=20)
        snap.items.append(food)
        await g.server.services.characters.save(snap.character, sy, food)

        g.client.send(8642)
        dragon = pb.FateListMsg.FromString((await g.until(4555))[-1].body).fateInfo[0]
        assert (dragon.fateTypes, dragon.grades) == (101, 0)
        g.client.send(8641, pb.FateEditMsg(useItemCount=10))
        dragon = pb.FateListMsg.FromString((await g.until(4555))[-1].body).fateInfo[0]
        assert (dragon.grades, dragon.totalGp) == (1, 4)  # 6 para o grau 1; nível 40 para no grau 1
        g.client.send(8641, pb.FateEditMsg(useItemCount=1))
        g.client.send(8643)  # transferência só no grau 5
        assert await g.idle() == []

        g.client.send(9505, pb.PowCardReqMsg(op=1, cardId=10001))
        card = pb.PowCardSuiteListMsg.FromString((await g.until(4905))[-1].body).suites[0].cardInfos[0]
        assert (card.grade, card.gp, card.buf.bufId) == (2, 2, 3041)  # igual ao login #76
        g.client.send(9505, pb.PowCardReqMsg(op=1, cardId=10001))  # faltam 30
        assert await g.idle() == []

        relogin = await g.connect()
        relogin.client.send(8224, pb.PlayerDataMsg(powcardInfo=True))
        suite = pb.PowCardSuiteListMsg.FromString((await relogin.until(4905))[-1].body).suites[0]
        assert (suite.suiteId, suite.cardInfos[0].grade) == (1000, 2)


async def test_pets_points_fight_and_slots(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        a = Pet(g.user_id, 104103, "Pan", grade=3, power_apti=1686, pos=0)
        b = Pet(g.user_id, 101103, "Amazon", pos=1, is_fight=True)
        snap.pets.extend([a, b])
        snap.character.point = 150
        await g.server.services.characters.save(snap.character, a, b)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=2, attributes=[11, 0, 0, 0]))  # só 10 livres
        assert await g.idle() == []
        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=2, attributes=[6, 4, 0, 0]))
        info = pb.PlayerPetMsg.FromString((await g.until(4540))[-1].body).petInfo[0]
        assert (info.power, info.intel, info.remainPoints) == (10 + 6 + 3 * 1686 // 100, 14, 0)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=9))  # só um na batalha
        got = await g.until(150)
        assert codes(got) == [4540, 150]
        pets = pb.PlayerPetMsg.FromString(got[0].body).petInfo
        assert sorted((p.petName, p.isFight) for p in pets) == [("Amazon", False), ("Pan", True)]
        army = pb.ArmyArmyMsg.FromString(got[1].body)
        assert (army.petTempId, army.petName) == (104103, "Pan")

        g.client.send(8621, pb.PlayerPetOpMsg(opType=12, payType=1))
        got = await g.until(3)
        assert pb.PlayerPetMsg.FromString(got[0].body).petCount == 4 and codes(got) == [4540, 3]
        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=3, payType=1))  # 100: só restam 50
        assert await g.idle() == []

        relogin = await g.connect()
        relogin.client.send(8224, pb.PlayerDataMsg(army=True))
        pets = pb.PlayerPetMsg.FromString((await relogin.until(4540))[-1].body)
        assert [(p.petName, p.power) for p in pets.petInfo] == [("Pan", 66), ("Amazon", 10)]
