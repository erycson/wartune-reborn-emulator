"""Herói e exército: tropas, skills, talento, runas, montaria, estrelas, destino, dragão, cartas e pets."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item, Pawn, Pet, PlayerSnapshot, Star
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


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
        assert codes(got) == [
            109,
            109,
            100,
            111,
        ]  # o 112 só vem com a missão 52 aberta (inglesa #653-#659: 112 da 52 em #656)
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount == 1001  # 2 de ouro por Lancer
        assert (pb.CastleYieldMsg.FromString(got[1].body).curPopulation, 900) == (900, 900)
        pawn = pb.ArmyPawnUpdatedMsg.FromString(got[2].body).armyPawn[0]
        assert (pawn.armyId, pawn.sonType, pawn.ownPawns, pawn.fightPos, len(pawn.pawnLive)) == (0, 101, 900, 3, 7)
        assert [x.tempData for x in pawn.pawnLive] == [64, 50, 0, 40, 323, 64, 0]  # igual à inglesa #658
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg == "Successfully Recruited 900 Lancer"

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
        got = await g.until(100)  # (visto) 191924-1 #20734-#20738: 3, 109, 111 (reembolso em Daru) e 100
        assert codes(got) == [3, 109, 111, 100]
        assert pb.ArmyPawnUpdatedMsg.FromString(got[3].body).armyPawn[0].ownPawns == 750
        assert pb.CastleYieldMsg.FromString(got[1].body).curPopulation == 850

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert [(p.template_id, p.castle_count, p.army_count) for p in saved.pawns] == [(10101, 750, 100)]

        relogin = await g.connect()  # o 150 do login já traz a tropa
        relogin.client.send(8224, pb.PlayerDataMsg(army=True))
        assert pb.ArmyArmyMsg.FromString((await relogin.until(150))[-1].body).armyPawn[0].ownPawns == 100
        await relogin.idle()  # o 100 e o 4544 do bloco army

        archer = Pawn(g.user_id, 10201, castle_count=30)
        snap_of(relogin).pawns.append(archer)
        await g.server.services.characters.save(archer)
        relogin.client.send(5156, pb.ArmyPawnInfoMsg(sites=0, tempateId=10201, ownPawns=30))
        got = await relogin.until(100)
        # tutorial_en #2301-#2304: o 100 leva só a tropa pedida, mesmo com o lanceiro voltando ao castelo
        assert [p.tempateId for p in pb.ArmyPawnUpdatedMsg.FromString(got[-1].body).armyPawn] == [10201]


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
        got = await g.until(83)
        assert codes(got) == [3, 116, 150, 83]  # tutorial_en #2089-#2094
        assert pb.PlayerMsg.FromString(got[0].body).strategy == 84  # 16 de Daru (UpGrade Types 1)
        assert pb.ArmyPawnInfoMsg.FromString(got[1].body).tempateId == 10102
        assert pb.ChatChannelMsg.FromString(got[3].body).encodeMsg == "Lancer successfully upgraded to Lvl. 2"
        await g.idle()

        # (visto) oficial_20261023-231733-1 #2110-#2116: herói ferido, a reserva cura e o 83 do HP pack vem por último
        assert snap.leader is not None
        barracks.template_id, snap.character.strategy, snap.leader.hp, snap.leader.blood = 40203, 10**6, 1, 10**6
        g.client.send(5158, pb.ArmyPawnInfoMsg(tempateId=10102))
        got = await g.until(83)
        got += await g.idle()
        assert codes(got) == [3, 116, 150, 83, 83]
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Used HP pack to restore HP."
        assert snap.leader.blood < 10**6


async def test_skills_second_set_and_reset(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:  # maga: skills 30711 e 30811
        snap = snap_of(g)
        cost = int(g.server.services.templates.get("ConfigInfos", "Second_SkillPoint", key="ConfigName")["ConfigValue"])
        snap.leader.grades, snap.character.point = 8, cost  # type: ignore[union-attr]
        await g.server.services.characters.save(snap.character, snap.leader)

        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=30111, type=0))
        got = await g.until(60)
        assert codes(got) == [150, 60]  # inglesa #1141-#1143
        hero = pb.ArmyArmyMsg.FromString(got[0].body).simpleHeroInfo
        assert (hero.skillScript, hero.skillPoint) == ("30711,30811,30111,", 1)  # nível 8 = 4 - 3
        skill = pb.UpdatedSkillMsg.FromString(got[1].body)
        assert (skill.templateId, skill.index, skill.type) == (30111, 2, 0)

        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=30111))  # já aprendida
        g.client.send(5185, pb.HeroAddPointReqMsg(skillTempId=10111))  # de guerreiro
        assert await g.idle() == []

        g.client.send(8479, pb.PayTypeMsg(payType=1))  # SkillView: o botão só aparece no nível 38
        assert await g.idle() == []
        snap.leader.grades = 38  # type: ignore[union-attr]
        g.client.send(8479, pb.PayTypeMsg(payType=1))
        got = await g.until(3)
        assert codes(got) == [150, 3] and pb.PlayerMsg.FromString(got[1].body).point == 0
        snap.leader.grades = 8  # type: ignore[union-attr]  # os pontos abaixo são do nível 8
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

        snap.character.point, snap.character.gift_token = 894, 0
        g.client.send(5184, pb.PayTypeMsg(payType=1, type=1))  # TalentView inglês: 895 Balens
        assert await g.idle() == []
        snap.character.point = 895
        g.client.send(5184, pb.PayTypeMsg(payType=1, type=1))
        assert codes(await g.until(3)) == [61, 150, 3] and snap.character.point == 0
        assert snap.leader.talent_script == ""  # type: ignore[union-attr]


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

        # diamante (RuneUpgradeView inglês): 50 + 10 por uso no dia, 20 EXP; count = usos (diamondIndex)
        snap.character.point, snap.character.gift_token = 110, 0
        world = g.server.services.world  # sem o bônus 2x-20x (taxas.rune_diamond_multiplier, 0134): só a base
        object.__setattr__(
            world,
            "settings",
            {**world.settings, "taxas": {**world.settings.get("taxas", {}), "rune_diamond_multiplier": {"1": 1}}},
        )
        for gp, used in ((70, 1), (90, 2)):
            g.client.send(8605, pb.HeroRuneOpMsg(opType=2, runeId=202))
            op = pb.HeroRuneOpMsg.FromString(next(p for p in await g.until(150) if p.code == 4495).body)
            assert ([(r.runeId, r.runeGp) for r in op.runeInfo.runeinfo], op.count) == ([(202, gp)], used)
        assert snap.character.point == 0


async def test_stars_rand_pick_equip_eat_lock_and_shop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from wartune_server.game.handlers import stars

    rolls = iter(["202", "302", "4"])  # verde de ataque, verde de defesa, fonte de energia
    monkeypatch.setattr(stars, "roll", lambda t, g, s, w: t.get("starTempInfos", int(next(rolls))))
    monkeypatch.setattr(stars._rng, "random", lambda: 1.0)  # nunca abre o próximo cristal
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        snap.character.gold, snap.character.grades, snap.character.point = 8000, 20, 100
        assert snap.systems is not None
        snap.systems.star_free, snap.systems.star_day = 0, "2000-01-01"  # gastou ontem e estava offline às 5h
        await g.server.services.characters.save(snap.character, snap.systems)

        g.client.send(8269, pb.StarRandReqMsg(site=0))  # grátis do dia
        got = await g.until(83)
        # 4152/83: leed 17 "Capture an Astral" (só turco: kader_sistemi #1-#8), só no 1º sorteio do dia
        # (visto) inglês 191924-1 #19350 e 1025 #6727: sem 109. (visto) turca kader_sistemi #1-#8 mandava 109 aqui: segue a inglesa
        assert codes(got) == [3, 4152, 3, 4180, 83] and pb.PlayerMsg.FromString(got[0].body).startFree == 0
        for _ in range(2):
            g.client.send(8269, pb.StarRandReqMsg(site=0))
            await g.until(4180)
        assert snap.character.gold == 0  # 2 x 4000
        g.client.send(8269, pb.StarRandReqMsg(site=0))  # sem ouro
        g.client.send(8269, pb.StarRandReqMsg(site=1))  # cristal apagado
        assert await g.idle() == []

        assert snap.systems.star_point == 3  # 1 ponto por sorteio no cristal 0 (MakeStarView)

        g.client.send(8268, pb.StarPickReqMsg(dropsite=1, way=1))  # Pick (StarIconView): way 1 recolhe
        assert codes(await g.until(4179)) == [4178, 4179]
        g.client.send(8268, pb.StarPickReqMsg(dropsite=2, way=2))  # Sell: way 2 vende o Energine (SellGold)
        assert codes(await g.until(4179)) == [109, 4179]
        g.client.send(8268, pb.StarPickReqMsg(dropsite=-1, way=1))  # venda rápida só do lixo: o verde não é
        assert await g.idle() == []
        g.client.send(8268, pb.StarPickReqMsg(dropsite=-2))  # Collect all
        assert codes(await g.until(4179)) == [4178, 4179]
        assert sorted((s.bag_type, s.pos) for s in snap.stars) == [(1, 0), (1, 1)]

        g.client.send(8267, pb.StarMoveReqMsg(beginStarType=1, beginPos=0, endStarType=2, endPos=0))
        assert codes(await g.until(4178)) == [150, 4178]  # (visto) 191924-1 #19445: 150 antes, um 4178 por casa
        assert codes(await g.idle()) == [4178]
        g.client.send(8267, pb.StarMoveReqMsg(beginStarType=1, beginPos=1, endStarType=2, endPos=2))  # 2 espaços
        assert await g.idle() == []
        g.client.send(8267, pb.StarMoveReqMsg(beginStarType=1, beginPos=1, endStarType=2, endPos=0, eat=True))
        got = await g.until(4178)
        assert codes(got) == [111, 150, 4178]  # só turco: kader_sistemi #122-#126
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg.endswith("gained 10 Astral EXP")
        moved = [*pb.StarMoveRspMsg.FromString(got[-1].body).move]
        moved += pb.StarMoveRspMsg.FromString((await g.until(4178))[-1].body).move
        assert [(m.changeType, m.changePos, m.star_Info.gp) for m in moved] == [(1, 1, 0), (2, 0, 10)]

        g.client.send(8330, pb.StarLockReqMsg(starType=2, pos=0))
        assert pb.StarMoveRspMsg.FromString((await g.until(4178))[-1].body).move[0].star_Info.isLock

        snap.character.point = 395
        g.client.send(8270, pb.PayTypeMsg(payType=1))  # uma linha de 4 por 395 (StarManager.sendBagCellBuy)
        assert pb.PlayerMsg.FromString((await g.until(3))[-1].body).starCount == 4
        assert codes(await g.until(83)) == [4152, 83]  # leed 15 (gasto de diamante)
        snap.systems.star_point = 1000
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
        assert pb.MountAvatarMsg.FromString(got[0].body).soulScore == 400  # só turco: login #11
        info = pb.MountInfoMsg.FromString(got[1].body)
        assert (info.power, info.intellect, info.physique, info.agility, info.levelMax) == (65, 35, 55, 60, 25)

        g.client.send(8529, pb.MountEditMsg(op=1, propertyType=0, payType=1, param1=9))
        got = await g.until(4426)
        got += await g.until(4426)
        # (só turco: online_odul #83-#91) 109, 115, 3, 150, 4476 da atividade 18 com o seu 4426 e o 4426 do treino
        assert codes(got) == [109, 115, 3, 150, 4476, 4426, 4426]
        info = pb.MountInfoMsg.FromString(got[-1].body)
        assert (info.power, info.powerGp, info.mountTotalGp) == (70, 1700, 4100)  # só turco: captura de treino #90
        assert pb.ArmyArmyMsg.FromString(got[3].body).mountTempId == 1103
        g.client.send(8529, pb.MountEditMsg(op=1, propertyType=0, payType=1, param1=1))  # acabou a comida
        g.client.send(8529, pb.MountEditMsg(op=2, param1=2000))  # não possui
        assert await g.idle() == []
        g.client.send(8529, pb.MountEditMsg(op=2, param1=1000))
        assert pb.MountInfoMsg.FromString((await g.until(4426))[-1].body).mountTempId == 1000

        snap.character.point, snap.character.gift_token = 30, 5  # sem chicote: 35 Balens, vinculados aceitos
        g.client.send(8529, pb.MountEditMsg(op=1, propertyType=0, payType=0, param1=1))
        await g.until(4426)
        assert (snap.character.point, snap.character.gift_token) == (0, 0)

        g.client.send(8529, pb.MountEditMsg(op=3, param1=0))  # Rest (MountsFrame)
        army = pb.ArmyArmyMsg.FromString((await g.until(150))[-1].body)
        assert army.HasField("mountTempId") and army.mountTempId == 0
        g.client.send(8529, pb.MountEditMsg(op=3, param1=1))  # Mount
        assert pb.ArmyArmyMsg.FromString((await g.until(150))[-1].body).mountTempId == 1000


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
        assert (card.grade, card.gp, card.buf.bufId) == (2, 2, 3041)  # só turco: login #76
        add = pb.PowcardFightAddMsg.FromString((await g.until(4902))[-1].body).singlefightadd
        assert [(a.campType, a.add) for a in add] == [(800, 120)]  # 3041: Vida 600 / 5
        from wartune_server.game.handlers.login import army

        session = g.server.online.get(g.user_id)
        assert session is not None
        session.send(150, army(session, snap)[0])  # todo 150 do próprio exército vem depois do 4902
        assert [p.code for p in await g.until(150)][-2:] == [4902, 150]
        session.send(150, army(session, snap)[0], cards=False)  # o do 154, da saída da campanha, da poção
        assert [p.code for p in await g.until(150)] == [150]
        g.client.send(9505, pb.PowCardReqMsg(op=1, cardId=10001))  # faltam 30
        assert await g.idle() == []

        relogin = await g.connect()
        relogin.client.send(8224, pb.PlayerDataMsg(powcardInfo=True))
        suite = pb.PowCardSuiteListMsg.FromString((await relogin.until(4905))[-1].body).suites[0]
        assert (suite.suiteId, suite.cardInfos[0].grade) == (1000, 2)


async def test_pets_points_fight_and_slots(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        a = Pet(g.user_id, 104103, "Pan", grade=3, power_apti=1686, physi_apti=1699, growth_rate=961, pos=0)
        b = Pet(g.user_id, 101103, "Amazon", pos=1, is_fight=True)
        snap.pets.extend([a, b])
        snap.character.point, snap.character.grades = 150, 3  # PetShowView: o pet ativo não passa do herói
        await g.server.services.characters.save(snap.character, a, b)

        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=2, attributes=[11, 0, 0, 0]))  # só 10 livres
        assert await g.idle() == []
        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=2, attributes=[6, 4, 0, 0]))
        info = pb.PlayerPetMsg.FromString((await g.until(4540))[-1].body).petInfo[0]
        # PetData inglês: template 10 + floor(2 x 961 / 80) = 24 de crescimento, mais os pontos
        assert (info.power, info.intel, info.remainPoints) == (10 + 24 + 6, 10 + 24 + 4, 0)
        assert info.maxHp == 1200 + 6 * (10 + 24) * 1699 // 1000  # PetData.hp

        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=9))  # só um na batalha
        got = await g.until(150)
        assert codes(got) == [4540, 150]
        pets = pb.PlayerPetMsg.FromString(got[0].body).petInfo
        assert sorted((p.petName, p.isFight) for p in pets) == [("Amazon", False), ("Pan", True)]
        army = pb.ArmyArmyMsg.FromString(got[1].body)
        assert (army.petTempId, army.petName) == (104103, "Pan")

        g.client.send(8621, pb.PlayerPetOpMsg(opType=12, payType=1, value=7))  # 6 + 7 passa do teto 12
        assert await g.idle() == []
        g.client.send(8621, pb.PlayerPetOpMsg(opType=12, payType=1, value=1))  # base 6 (PetListView), 100
        got = await g.until(83)  # + 4152/83 do leed 15 (gasto de diamante)
        assert pb.PlayerPetMsg.FromString(got[0].body).petCount == 7 and codes(got) == [4540, 3, 4152, 83]
        g.client.send(8621, pb.PlayerPetOpMsg(petId=a.id, opType=3, payType=1))  # 100: só restam 50
        assert await g.idle() == []

        relogin = await g.connect()
        relogin.client.send(8224, pb.PlayerDataMsg(army=True))
        pets = pb.PlayerPetMsg.FromString((await relogin.until(4540))[-1].body)
        assert [(p.petName, p.power) for p in pets.petInfo] == [("Pan", 40), ("Amazon", 10)]


def test_bonus_da_colecao_reproduz_o_login_76() -> None:
    """(só turco) login #76: 1000/1001/1003/1004 com 3 cartas sem bufInfos; 1002 com 4 cartas (graus 2,2,2,1) só com o
    degrau 0 (Template3s 1004, Property3 40001)."""
    from wartune_server.domain.models import PlayerSystems
    from wartune_server.game.handlers.systems import powcard_msg
    from wartune_server.templates.repository import GameTemplates

    templates = GameTemplates.parse(TEMPLATES.read_bytes())
    seen = {10001: 2, 10002: 1, 10003: 1, 10011: 2, 10012: 1, 10013: 1, 10015: 2, 10016: 2, 10017: 2,
            10018: 1, 10019: 2, 10020: 2, 10021: 1, 10023: 2, 10024: 2, 10025: 1}  # fmt: skip

    def suites(grades: dict[int, int]) -> dict[int, list[tuple[int, int, int, int]]]:
        snap = PlayerSnapshot.__new__(PlayerSnapshot)
        sy = PlayerSystems(1, powcards=",".join(f"{t}:{g}:0:0" for t, g in grades.items()))
        object.__setattr__(snap, "systems", sy)
        msg = powcard_msg(snap, templates)
        return {s.suiteId: [(b.sonType, b.bufId, b.fixValue, b.percent) for b in s.bufInfos] for s in msg.suites}

    assert suites(seen) == {1000: [], 1001: [], 1002: [(1004, 40001, 0, 0)], 1003: [], 1004: []}
    # 4 cartas no grau 3 acendem o degrau 1 (Property4)
    assert suites({10015: 3, 10016: 3, 10017: 3, 10018: 3})[1002] == [(1004, 40001, 0, 0), (1004, 40002, 0, 0)]

    # 4902 (só turco: login #3): o poder das cartas por tipo de luta, na ordem das coleções
    from types import SimpleNamespace

    from wartune_server.game.handlers.systems import fight_add_msg

    snap = PlayerSnapshot.__new__(PlayerSnapshot)
    object.__setattr__(snap, "systems", PlayerSystems(1, powcards=",".join(f"{t}:{g}:0:0" for t, g in seen.items())))
    object.__setattr__(snap, "character", SimpleNamespace(id=7, grades=31))  # abaixo do 32: sem cartas, None
    add = fight_add_msg(snap, templates)
    assert add is not None
    assert [(a.op, a.userid, a.campType, a.add) for a in add.singlefightadd] == [
        (0, 0, 800, 608),
        (0, 0, 802, 608),
        (0, 0, 806, 1521),
        (0, 0, 807, 768),
        (0, 0, 801, 768),
    ]  # fmt: skip  (userid vazio como no inglês: captura 20261029-121453-1 #4046)
    # 4903 (só turco: exp_kitabi #31 na masmorra, yeralti #36 no labirinto): os buffs do tipo do lugar
    from wartune_server.game.handlers.systems import camp_buffs_msg, camp_stats

    def bufs(camp: int) -> list[int]:
        return [b.bufId for b in camp_buffs_msg(snap, templates, camp).bufInfos]

    assert (bufs(800), bufs(802), bufs(0)) == ([3041, 3020, 3000], [4061, 4020, 4000], [])
    assert camp_stats(snap, templates, 800) == {
        "PhyAttack": 160, "PhyDefence": 80, "MagicAttack": 160, "MagicDefence": 80, "ForceHit": 0, "Parry": 0,
        "Live": 600,
    }  # fmt: skip
    object.__setattr__(snap, "systems", PlayerSystems(1))
    assert fight_add_msg(snap, templates) is None


async def test_formation_rows_and_comprehend_blessing(tmp_path: Path) -> None:
    """AllocateView inglês: fileira 1 ou 3. PawnSpecialAbilityFrame.helpContent: bênção cheia = grau acima, 100%;
    subir de grau zera a bênção."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        g.client.send(8276, pb.ArmyFightPosEditMsg(userId=g.user_id, heroPos=2, pawnPos=3))
        assert await g.idle() == []
        g.client.send(8276, pb.ArmyFightPosEditMsg(userId=g.user_id, heroPos=3, pawnPos=1))
        await g.until(150)
        assert snap.leader is not None and snap.leader.fight_pos == 3

        templates = g.server.services.templates
        grade = lambda tid: int(templates.get("SpecialTempInfos", int(tid))["Grades"])  # noqa: E731
        full = int(next(iter(templates.find("UpGradeTempInfos", Types="16", Grades=1)))["Data"])
        pawn = Pawn(g.user_id, 10101)  # tropa nível 1 (current_pawn cria igual em memória)
        snap.pawns.append(pawn)
        pawn.bless, snap.character.strategy = full - 1, 2_000_000
        g.client.send(8455, pb.ComprehendMsg(templateId=pawn.template_id))
        await g.until(116)
        assert (grade(pawn.comprehend), pawn.bless) == (2, 0)
        pawn.bless = 5
        g.client.send(8456, pb.ComprehendMsg(templateId=pawn.template_id))
        await g.until(150)
        assert (grade(pawn.specials), pawn.bless, pawn.comprehend) == (2, 0, "")


async def test_pawn_upgrade_closing_the_seven_day_task_sends_4638_before_the_army(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #1676-#1682: Lancer ao nível 10 fecha a tarefa 1 do guia de 7 dias, e o 4638
    vem entre o 116 e o 150."""
    from wartune_server.domain.models import Quest
    from wartune_server.game.handlers import events as hev

    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        s = g.server.online.get(g.user_id)
        assert s is not None and snap.leader is not None
        done = s.ctx.clock.now()
        snap.quests.append(Quest(snap.character.id or 0, hev.SERVEN_QUEST, done, completed=True, completed_at=done))
        hev.send_serven(s)
        await g.idle()
        snap.character.strategy, snap.leader.grades = 100_000, 20
        lancer = Pawn(g.user_id, 10109, castle_count=10)
        snap.pawns.append(lancer)
        barracks = next(b for b in snap.buildings if b.template_id // 100 == 402)
        barracks.template_id = 40210
        await g.server.services.characters.save(snap.character, snap.leader, lancer, barracks)

        g.client.send(5158, pb.ArmyPawnInfoMsg(tempateId=10109))
        got = await g.until(83)
        assert codes(got) == [3, 116, 4638, 150, 83]
        day1 = pb.ServenDayLeadMsg.FromString(got[2].body).singleDay[0]
        assert day1.simpleTask[0].isComplete == 1
        # (visto) no 10 a 1ª especialidade vem sozinha: Lancer "100" (171155 #1678; Hunter "200" em 191924 #1318)
        assert pb.ArmyPawnInfoMsg.FromString(got[1].body).specialTempIds == "100"
        assert lancer.specials == "100"


async def test_star_compose_says_exp_and_level(tmp_path: Path) -> None:
    """(só turco: kader_sistemi #112-#117) 111 do nível, 111 da EXP, 109 do lixo vendido, 4479, 83 do nível e 4484."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        uid = snap.character.id or 0
        made = [Star(uid, 1503, bag_type=0, pos=0)] + [Star(uid, 303, bag_type=0, pos=p) for p in (1, 2, 3)]
        made += [Star(uid, 1, bag_type=0, pos=p) for p in range(4, 16)]  # lixo: vendido; a temporária estava cheia
        snap.stars.extend(made)
        await g.server.services.characters.save(*made)
        g.client.send(8331, pb.StarComposeReqMsg(bagType=0, pos=0))
        got = await g.until(4484)
        assert codes(got) == [111, 111, 109, 4479, 83, 4484]
        texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code in (111, 83)]
        name = g.server.services.templates.get("starTempInfos", 1503)["TemplateName"]
        level = f"Astral {name} has been upgraded to Lvl. 2"
        assert texts == [level, f"Astral {name} gained 90 Astral EXP", level]  # composição: nível antes da EXP (visto)
        left = pb.StarRandRspMsg.FromString(got[3].body).starRand
        assert [(r.starInfo.templateId, r.starInfo.grade, r.starInfo.gp) for r in left] == [(1503, 2, 20)]


async def test_rare_astral_is_shouted_to_the_whole_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(visto) oficial_encantar #2753: a Profile 5 sorteada vai no 83 canal 2 para todos os online."""
    from wartune_server.game.handlers import stars

    monkeypatch.setattr(stars, "roll", lambda t, g, s, w: t.get("starTempInfos", 1405))
    async with logged_in(tmp_path, novice=19000) as g:
        other = await g.join("outro")
        await g.idle()
        await other.idle()
        snap = snap_of(g)
        snap.character.gold, snap.character.grades = 8000, 40
        g.client.send(8269, pb.StarRandReqMsg(site=0))
        await g.until(4180)
        assert codes(await g.until(83)) == [83]  # a devoção do 1º sorteio do dia (só turco: kader_sistemi #8)
        got = await g.until(83)
        assert codes(got) == [83]
        text = pb.ChatChannelMsg.FromString(got[-1].body)
        heard = pb.ChatChannelMsg.FromString([p for p in await other.until(83) if p.code == 83][-1].body)
        assert text == heard and text.channel == 2
        assert text.encodeMsg.endswith(
            ' just received the extremely rare [<a t="3" id="1405" name="Enhanced Guardian Angel" grades="1"/>] Astral!'
        )
