"""Coliseu, torneio de fadas, eventos fechados e pacotes de batalha do PvP."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Arena, ArenaRank, BagType, CashLedger, Item, PlayerSnapshot, Quest
from wartune_server.domain.models import Pet as OwnedPet
from wartune_server.game import arena as A
from wartune_server.game import battle as battle_mod
from wartune_server.game import events as ev
from wartune_server.game.battle import Battle
from wartune_server.game.handlers import arena as arena_handlers
from wartune_server.protocol.messages import wartune_pb2 as pb


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.004)  # 10x: a luta não leva segundos


def codes(packets: list[Any]) -> list[int]:
    return [p.code for p in packets]


def snap_of(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def body(packets: list[Any], code: int, cls: type[Any]) -> Any:
    return cls.FromString(next(p for p in packets if p.code == code).body)


def bag_count(snap: PlayerSnapshot, template_id: int) -> int:
    return sum(i.count for i in snap.items if i.template_id == template_id)


async def info(g: Game) -> pb.ChallengeInfoMsg:
    g.client.send(8256, pb.ChallengeRequestMsg(type=0))
    return body(await g.until(4169), 4169, pb.ChallengeInfoMsg)


async def fight(g: Game, target: int) -> list[Any]:
    g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=target, payType=0))
    got = await g.until(157)
    prepare = body(got, 157, pb.BattlePrepareMsg)
    return got + await g.fight(prepare, skill=30711) + await g.idle()


async def test_colosseum_against_a_robot_enters_the_ranking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    weak = A.robot_spec

    def harmless(robot: A.Robot, templates: Any, *args: Any) -> Any:  # robô de 1 de vida: vitória certa
        soldiers, heroes = weak(robot, templates, *args)
        for unit in soldiers + heroes:
            unit.update(hp=1, initHp=1, maxHp=1)
        return soldiers, heroes

    monkeypatch.setattr(A, "robot_spec", harmless)
    async with logged_in(tmp_path, novice=30001) as g:
        first = await info(g)
        assert (first.curRank, first.challengeCount, first.totalCount, first.leftDay > 0) == (0, 0, 10, True)
        robots = [p.userId for p in first.simplePlayer]
        assert len(robots) == 4 and all(A.is_robot(u) for u in robots)

        got = await fight(g, robots[0])
        prepare = body(got, 157, pb.BattlePrepareMsg)
        enemy = next(h for h in prepare.heros if h.side == 2)
        assert (prepare.battleType, enemy.type, enemy.userId, enemy.nickName) == (
            16,
            2,
            0,
            first.simplePlayer[0].nickName,
        )
        report = body(got, 4103, pb.BattleReportMsg)
        assert (report.battleResult, report.battleScene, report.gpBonus) == (1, 7, 60)
        cool = body(got, 4176, pb.ChallengeCoolTimeMsg)
        assert (cool.type, cool.challengeCount, cool.leftTime) == (0, 1, 600)
        assert 75 in codes(got)  # o herói inimigo anuncia a skill
        # (visto) oficial_20261023-215937-1 #1163-#1181: sem 150 no fim; o VIP Token (0072) depois do 4176
        tail = codes(got)[codes(got).index(4103) - 1 :]
        assert [c for c in tail if c in (3, 150, 4103, 83, 140, 4176, 115, 111)] == [
            3,
            4103,
            83,
            140,
            4176,
            115,
            111,
            83,
        ]
        assert bag_count(snap_of(g), 208015) + bag_count(snap_of(g), 2040103) == 1  # um dos dois do sorteio
        live = g.server.online.get(g.user_id)
        assert live is not None
        now = live.ctx.clock.now()
        assert arena_handlers._prize(live, snap_of(g), True, now) is None  # daily 1: a 2ª vitória do dia não dá
        ev.daily(snap_of(g), arena_handlers.PRIZE_KEY, now).value = 0
        assert arena_handlers._prize(live, snap_of(g), False, now) is None  # win_only: derrota não dá

        after = await info(g)
        assert (after.curRank, after.lastWinCount, after.challengeCount) == (1, 1, 1)
        assert after.challengeLog[0].result == 1 and after.challengeLog[0].forward == 1

        g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=after.simplePlayer[0].userId))  # ainda em espera
        assert codes(await g.idle()) == [4176]

        # zerar a espera: ceil(600/60)*5 = 50 diamantes
        snap = snap_of(g)
        snap.character.point = 60
        g.client.send(8265, pb.PayTypeMsg(payType=1, type=0))
        cool = body(await g.until(4176), 4176, pb.ChallengeCoolTimeMsg)
        assert cool.leftTime == 0 and snap.character.point == 10

        session = g.server.online.get(g.user_id)
        assert session is not None
        arena_handlers._arena(session).cool_until = session.ctx.clock.now() + timedelta(minutes=10)
        st = ev.state(snap, "vip", session.ctx.clock.now())
        st.value, st.text = 0, "2999-01-01 00:00:00"  # VIP nível 1: vipCoolPrivilege
        g.client.send(8265, pb.PayTypeMsg(payType=0, type=0))  # ColosseumFrame com VIP: sem quadro de custo
        got = await g.until(4176)
        assert body(got, 4176, pb.ChallengeCoolTimeMsg).leftTime == 0 and snap.character.point == 10
        assert 3 not in codes(got)  # nada pago
        async with g.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.balance_point, e.reason) for e in ledger] == [(-50, 10, "arena_cool")]  # só o pago

        # recompensa da posição 1, uma vez por período
        g.client.send(8329)
        taken = body(await g.until(4243), 4243, pb.ChallengeRankRewardMsg)
        assert (taken.param1, taken.param2, taken.param3) == (1, 300000, 3000)
        g.client.send(8329)
        again = body(await g.until(4243), 4243, pb.ChallengeRankRewardMsg)
        assert (again.param1, again.param2) == (1, 0)


async def test_colosseum_start_counts_quest_35_before_the_battle(tmp_path: Path) -> None:
    """(visto) oficial_20261023-215937-1 #1129-#1133: 140, 112 (missão 188 "Challenge", tipo 35), 4152 e 157."""
    async with logged_in(tmp_path, novice=30001) as g:
        robots = [p.userId for p in (await info(g)).simplePlayer]
        quest = Quest(g.user_id, 188, datetime.now(UTC))
        snap_of(g).quests.append(quest)
        g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=robots[0], payType=0))
        assert [c for c in codes(await g.until(157)) if c in (140, 112, 4152, 157)] == [140, 112, 4152, 157]
        assert quest.progress == 1


async def test_colosseum_copy_of_a_player_can_beat_you_and_wins_swap_places(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_copy = A.copy_hero
    strength: dict[str, int] = {}

    def copy(snap: PlayerSnapshot, templates: Any, now: Any) -> Any:
        hero = real_copy(snap, templates, now)
        hero.update(strength)
        return hero

    monkeypatch.setattr(A, "copy_hero", copy)
    async with logged_in(tmp_path, novice=30001) as g:
        other = await g.join("outro")
        chars = g.server.services.characters
        await chars.save(ranks=(ArenaRank(other.user_id, 1), ArenaRank(g.user_id, 2)))

        listed = await info(g)
        assert listed.curRank == 2
        assert [(p.userId, p.challengeRank) for p in listed.simplePlayer][0] == (other.user_id, 1)

        strength.update(attack=1_000_000, hp=1_000_000, maxHp=1_000_000, initHp=1_000_000)  # a cópia vence
        got = await fight(g, other.user_id)
        enemy = next(h for h in body(got, 157, pb.BattlePrepareMsg).heros if h.side == 2)
        assert (enemy.type, enemy.userId, enemy.nickName) == (2, 0, "Outro")
        assert body(got, 4103, pb.BattleReportMsg).battleResult == 2  # o jogador perde de verdade
        assert (await chars.arena_rank(g.user_id), await chars.arena_rank(other.user_id)) == (2, 1)
        defended = await chars.challenge_logs(other.user_id, A.COLOSSEUM, 10)
        assert [(log.is_attack, log.won, log.target_id) for log in defended] == [(False, True, g.user_id)]

        snap_of(g).arena.cool_until = None  # type: ignore[union-attr]
        strength.clear()
        strength.update(hp=1, maxHp=1, initHp=1)  # agora a cópia cai no primeiro golpe
        await info(g)
        got = await fight(g, other.user_id)
        assert body(got, 4103, pb.BattleReportMsg).battleResult == 1
        assert (await chars.arena_rank(g.user_id), await chars.arena_rank(other.user_id)) == (1, 2)


async def test_colosseum_refusals(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=A.ROBOT_BASE + 5))  # fora da lista
        assert codes(await g.idle()) == [4176]

        robot = (await info(g)).simplePlayer[0].userId
        snap = snap_of(g)
        assert snap.arena is not None
        snap.arena.challenge_count, snap.character.point, snap.character.gift_token = 10, 0, 1
        g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=robot, payType=0))  # 11ª custa 2 diamantes
        assert codes(await g.idle()) == [4176]
        assert snap.arena.challenge_count == 10 and snap.character.gift_token == 1

        snap.character.point = 1
        g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=robot, payType=0))  # 1 vinculado + 1 diamante
        assert 157 in codes(await g.until(157))
        assert (snap.arena.challenge_count, snap.character.point, snap.character.gift_token) == (11, 0, 0)


async def test_daily_reset_zeroes_counters_and_sends_4202(tmp_path: Path) -> None:
    arena = Arena(1, day="2000-01-01", challenge_count=5, pet_count=2)
    assert A.roll_day(arena, datetime(2026, 1, 1, 5, tzinfo=UTC)) is True  # 08:00 em UTC+3: dia 1
    assert (arena.day, arena.challenge_count, arena.pet_count) == ("2026-01-01", 0, 0)
    assert A.roll_day(arena, datetime(2026, 1, 1, 23, tzinfo=UTC)) is False

    async with logged_in(tmp_path, novice=30001) as g:
        snap = snap_of(g)
        assert snap.arena is not None
        snap.arena.day, snap.arena.challenge_count = "2000-01-01", 4
        g.client.send(8256, pb.ChallengeRequestMsg(type=0))
        got = await g.until(4169)
        reset = body(got, 4202, pb.DataResetMsg)
        assert (reset.challengeCount, reset.weary) == (0, snap.character.weary)
        assert body(got, 4169, pb.ChallengeInfoMsg).challengeCount == 0


async def test_pet_tournament_without_pets(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        g.client.send(8256, pb.ChallengeRequestMsg(type=1))
        listed = body(await g.until(4611), 4611, pb.PetChallengeInfoMsg)
        assert (listed.playerInfo.score, listed.playerInfo.order, listed.playerInfo.challengeCount) == (1000, 0, 10)
        assert len(listed.playerPets) == 4 and all(len(p.petInfo) == 3 for p in listed.playerPets)

        g.client.send(8724, pb.PlayerChallengeMsg(tarUserId=listed.playerPets[0].userId))  # sem pets
        assert codes(await g.idle()) == [4176]
        g.client.send(8725, pb.PlayerPetMsg(chaPos="123,-1,-1"))  # pet que não é dele
        assert await g.idle() == []
        g.client.send(8725, pb.PlayerPetMsg(chaPos="-1,-1,-1,-1,-1,-1"))
        assert body(await g.until(4540), 4540, pb.PlayerPetMsg).chaPos == "-1,-1,-1,-1,-1,-1"
        g.client.send(8728, pb.RankRewardMsg(type=1, opType=1))  # fora do ranking: nada
        assert await g.idle() == []

        snap = snap_of(g)
        snap.character.gold = 60000
        g.client.send(5021, pb.PlayerChallengeMsg(tarArmyId=1, type=1))
        got = await g.until(4176)
        assert body(got, 4176, pb.ChallengeCoolTimeMsg).challengeCount == 11 and snap.character.gold == 10000
        g.client.send(5021, pb.PlayerChallengeMsg(tarArmyId=1, type=1))  # sem ouro
        assert body(await g.until(4176), 4176, pb.ChallengeCoolTimeMsg).challengeCount == 11


async def give_pet(g: Game, template: int, grade: int, name: str = "Pan") -> int:
    """Pet gravado no banco (o servidor ainda não cria pets) e no snapshot da sessão, se estiver
    online. Devolve o id."""
    pet = OwnedPet(g.user_id, template, name, grade=grade, quality=7)
    await g.server.services.characters.save(pet)
    snap_of(g).pets.append(pet)
    return pet.id or 0


async def test_pet_tournament_battle_is_automatic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(A, "PET_NOTICE_FRAME", 150)
    async with logged_in(tmp_path, novice=30001) as g:
        pet_id = await give_pet(g, 104101, 60)
        snap = snap_of(g)
        snap.character.grades = 55
        g.client.send(8725, pb.PlayerPetMsg(chaPos=f"{pet_id},-1,-1"))
        await g.until(4540)
        g.client.send(8256, pb.ChallengeRequestMsg(type=1))
        listed = body(await g.until(4611), 4611, pb.PetChallengeInfoMsg)
        assert listed.playerInfo.order == 1

        g.client.send(8724, pb.PlayerChallengeMsg(tarUserId=listed.playerPets[0].userId))
        got = await g.until(157)
        prepare = body(got, 157, pb.BattlePrepareMsg)
        assert prepare.battleType == 35 and not prepare.heros
        mine = [p for p in prepare.pets if p.side == 1]
        assert [(p.userId, p.headId, p.pos, p.tempId, p.grade) for p in mine] == [(g.user_id, pet_id, 1, 104101, 60)]
        assert len(prepare.pets) == 4
        g.client.send(10007, pb.LoadOverMsg(armyId=g.user_id, battleId=prepare.battleId))
        got = await g.until(4103)
        assert 75 not in codes(got) and 4361 in codes(got)  # sem ordens; o dano sobe no meio
        notice = body(got, 4361, pb.BattleNoticeMsg)
        assert (notice.countDown, notice.damageImprove) == (60000, 50)
        report = body(got, 4103, pb.BattleReportMsg)
        assert report.battleScene == 19
        assert body(got, 4176, pb.ChallengeCoolTimeMsg).leftTime == 300
        assert snap.arena is not None and snap.arena.pet_count == 1
        assert snap.arena.pet_score == (1005 if report.battleResult == 1 else 1000)
        rest = got + await g.idle()
        click = body(rest, 4413, pb.ClickDatasRspMsg).info  # (só turco: peri_turnuvasi #53)
        assert [(c.keys, c.keyData) for c in click] == [("pet", 1)]
        g.client.send(8518)
        listed_clicks = body(await g.until(4412), 4412, pb.ClickDatasRspMsg).info
        assert [(c.keys, c.keyData) for c in listed_clicks] == [("pet", 1)]


@pytest.mark.parametrize("online", [True, False])
async def test_pet_tournament_fights_the_real_pets_of_the_opponent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, online: bool
) -> None:
    """Os pets dos dois lados são os gravados: o do oponente vem da sessão dele ou, offline, do banco."""
    monkeypatch.setattr(A, "PET_NOTICE_FRAME", 150)
    async with logged_in(tmp_path, novice=30001) as g:
        mine_id = await give_pet(g, 104101, 60)
        snap_of(g).character.grades = 55
        g.client.send(8725, pb.PlayerPetMsg(chaPos=f"{mine_id},-1,-1"))
        await g.until(4540)

        other = await g.join("outro")
        their_id = await give_pet(other, 102102, 42, "Liris")
        other.client.send(8725, pb.PlayerPetMsg(chaPos=f"{their_id},-1,-1"))
        await other.until(4540)
        if not online:
            session = g.server.online.get(other.user_id)
            assert session is not None
            g.server.online.unbind(other.user_id, session)
            assert g.server.online.get(other.user_id) is None  # daqui para frente lê do banco

        g.client.send(8256, pb.ChallengeRequestMsg(type=1))
        listed = body(await g.until(4611), 4611, pb.PetChallengeInfoMsg)
        theirs = next(p for p in listed.playerPets if p.userId == other.user_id)
        assert [(i.petId, i.templateId, i.curGrade) for i in theirs.petInfo] == [(their_id, 102102, 42)]

        g.client.send(8724, pb.PlayerChallengeMsg(tarUserId=other.user_id))
        prepare = body(await g.until(157), 157, pb.BattlePrepareMsg)
        foes = [p for p in prepare.pets if p.side == 2]
        assert [(p.tempId, p.grade) for p in foes] == [(102102, 42)]
        g.client.send(10007, pb.LoadOverMsg(armyId=g.user_id, battleId=prepare.battleId))
        assert body(await g.until(4103), 4103, pb.BattleReportMsg).battleScene == 19


async def test_pet_battle_end_early_needs_an_active_vip_3(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """8727 "encerrar já": só VIP ativo com nível >= 3 (``Pet_BattleOver_Grade``). VIP vencido não vale."""
    ended: list[str] = []
    finish = Battle.finish

    def spy(self: Battle) -> None:
        ended.append(self.id)
        finish(self)

    monkeypatch.setattr(Battle, "finish", spy)
    async with logged_in(tmp_path, novice=30001) as g:
        pet_id = await give_pet(g, 104101, 60)
        snap = snap_of(g)
        snap.character.grades = 55
        g.client.send(8725, pb.PlayerPetMsg(chaPos=f"{pet_id},-1,-1"))
        await g.until(4540)
        g.client.send(8256, pb.ChallengeRequestMsg(type=1))
        listed = body(await g.until(4611), 4611, pb.PetChallengeInfoMsg)
        g.client.send(8724, pb.PlayerChallengeMsg(tarUserId=listed.playerPets[0].userId))
        prepare = body(await g.until(157), 157, pb.BattlePrepareMsg)  # a luta só anda com o 10007

        def set_vip(value: int, text: str) -> None:
            state = ev.state(snap, "vip", datetime.now(UTC))
            state.value, state.text = value, text

        g.client.send(8727, pb.BattleReqMsg(battleId=prepare.battleId))  # sem VIP
        assert await g.idle() == [] and ended == []
        set_vip(310, "2000-01-01 00:00:00")  # nível 3, mas vencido
        g.client.send(8727, pb.BattleReqMsg(battleId=prepare.battleId))
        assert await g.idle() == [] and ended == []
        set_vip(0, "2999-01-01 00:00:00")  # ativo, nível 1
        g.client.send(8727, pb.BattleReqMsg(battleId=prepare.battleId))
        assert await g.idle() == [] and ended == []

        snap.character.point = 400
        g.client.send(8513, pb.VipOpenInfoMsg(days=31))  # 310 de vipGp: nível 3 ativo
        await g.until(4416)
        g.client.send(8727, pb.BattleReqMsg(battleId=prepare.battleId))
        await g.idle()
        assert ended == [prepare.battleId]
        g.client.send(10007, pb.LoadOverMsg(armyId=g.user_id, battleId=prepare.battleId))
        assert body(await g.until(4103), 4103, pb.BattleReportMsg).battleScene == 19


async def test_pet_battle_finish_resolves_without_more_attacks() -> None:
    from wartune_server.services.clock import SystemClock
    from wartune_server.templates.repository import GameTemplates

    templates = await GameTemplates.load(Path("data/templates/tempinfos.xml"))
    sent: list[int] = []
    ended: list[bool] = []

    async def on_end(battle: Battle, won: bool) -> None:
        ended.append(won)

    mine = [A.pet_unit(104101, 60, 7, 1, 1, 1, 42, 77, templates)]
    spec = A.pet_spec(mine, A.pet_robot_units(templates, 2))
    battle = Battle(spec, None, templates, SystemClock(), lambda code, msg: sent.append(code), on_end)
    battle.start()
    battle.load_over()
    while 153 not in sent:  # noqa: ASYNC110  (o send da batalha é síncrono; 10 ms não importam)
        await asyncio.sleep(0.01)
    battle.finish()
    for _ in range(200):
        if ended:
            break
        await asyncio.sleep(0.01)
    assert ended and sent[-1] == 154
    attacks = sent.count(153)
    await asyncio.sleep(0.05)
    assert sent.count(153) == attacks


async def test_closed_events_and_battle_extras(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        g.client.send(8711)
        assert body(await g.until(4529), 4529, pb.LordsOrderListMsg).param1 == 0
        g.client.send(8714)
        assert codes(await g.until(4536)) == [4530, 4536]
        g.client.send(8979)
        assert body(await g.until(4799), 4799, pb.MateLordsListMsg).isOpen is False
        g.client.send(8715)
        await g.until(4531)
        g.client.send(8337)
        await g.until(4255)
        for code in (8332, 8334, 8338, 8599, 8633, 8717, 8720, 8635, 10015, 8282, 8283, 10003):
            g.client.send(code)
        assert await g.idle() == []
        g.client.send(8590)
        assert body(await g.until(4482), 4482, pb.ChallengeRankRewardMsg).isTake is False
        g.client.send(8985, pb.BattleViewMsg(type=1, userId=5))
        assert body(await g.until(4804), 4804, pb.SimplePropertyMsg).param7 is True

        # pacotes de batalha: só respondem com a batalha certa
        robot = (await info(g)).simplePlayer[0].userId
        g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=robot))
        prepare = body(await g.until(157), 157, pb.BattlePrepareMsg)
        g.client.send(10016, pb.AttackModeMsg(battleId=prepare.battleId, mode=2))
        assert body(await g.until(77), 77, pb.AttackModeMsg).mode == 2
        g.client.send(10499, pb.BattleItemMsg(battleId=prepare.battleId, userId=3, skillTempId=9204))
        assert body(await g.until(158), 158, pb.ItemUseResultMsg).result == 1
        g.client.send(10018, pb.LoadOverMsg(battleId=prepare.battleId))  # reforço: conta como carregado
        assert 156 in codes(await g.until(156))


async def test_login_sends_challenge_state(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        snap = snap_of(g)
        assert snap.arena is not None
        snap.arena.cool_until = datetime.now(UTC) + timedelta(seconds=100)
        g.client.send(8224, pb.PlayerDataMsg(sys=True, challReward=True))
        got = await g.until(4244)
        cools = [pb.ChallengeCoolTimeMsg.FromString(p.body) for p in got if p.code == 4176]
        assert [(c.type, c.challengeCount) for c in cools] == [(0, 0), (1, 10)] and 90 < cools[0].leftTime <= 100
        assert {4776, 4248} <= set(codes(got)) and 4535 not in codes(got)  # tutorial_en #104-#106: sem 4535
        assert body(got, 4244, pb.ChallengeRankRewardMsg).isTake is False  # fora do ranking


def test_rank_rewards_and_costs() -> None:
    assert A.rank_reward(1) == (300000, 3000) and A.rank_reward(0) == (0, 0)
    assert [A.buy_cost(n) for n in range(6)] == [2, 4, 6, 8, 10, 10]
    assert A.cool_cost(600) == 50 and A.cool_cost(61) == 10
    assert A.Robot(A.ROBOT_BASE + 7, 13).name == A.Robot(A.ROBOT_BASE + 7, 40).name
    assert A.Robot(A.ROBOT_BASE + 7, 40).hero_template == 11030
    assert arena_handlers._forward(0, 5) == 1 and arena_handlers._forward(5, 3) == 1
    assert arena_handlers._forward(3, 5) == -1 and arena_handlers._forward(4, 4) == 0  # < 0: "ranking dropped"


async def test_colosseum_is_closed_during_the_tutorial(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8256, pb.ChallengeRequestMsg(type=0))
        assert await g.idle() == []
        g.client.send(8253, pb.PlayerChallengeMsg(tarUserId=A.ROBOT_BASE))
        assert codes(await g.idle()) == [4176]


async def test_estado_dos_campos_de_batalha_pela_agenda_como_a_captura(tmp_path: Path) -> None:
    from wartune_server.game.handlers import warfield

    async with logged_in(tmp_path, novice=19000) as g:
        templates = g.server.services.templates
        at = datetime(2026, 10, 18, 18, 24, tzinfo=UTC)  # tutorial_en #104
        got = [(i.campaignId, i.state) for i in warfield.states(templates, at).worldBossInfo]
        assert got == [(c, 2) for c in range(4001, 4008)] + [(4008, 3)] + [(c, 1) for c in range(4009, 4012)]
        at = datetime(2026, 10, 18, 19, 0, tzinfo=UTC)  # #3110: o oficial abre (0); aqui fica 3, sem o mapa
        assert dict((i.campaignId, i.state) for i in warfield.states(templates, at).worldBossInfo)[4009] == 3


async def test_colosseum_avatar_carries_the_leaders_fashion(tmp_path: Path) -> None:
    """ColosseumControler lê do ``avater`` a arma, a armadura e a moda (asa, arma, roupa, chapéu) do líder."""
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None and s.snapshot.leader is not None
        snap, leader = s.snapshot, s.snapshot.leader
        for tid in (1090000, 1100101, 1110101, 1120101):
            snap.items.append(Item(g.user_id, tid, bag_type=BagType.HERO, object_id=leader.id or 0))
        msg = pb.ChallengeInfoMsg()
        arena_handlers._avatars(msg, snap, s)
        [a] = msg.avater
        fashion = (a.fashionWingTempId, a.fashionHeadTempId, a.fashionArmTempId, a.fashionClothTempId)
        assert a.userId == g.user_id and fashion == (1090000, 1100101, 1110101, 1120101)
        leader.hide_fashion = True
        msg = pb.ChallengeInfoMsg()
        arena_handlers._avatars(msg, snap, s)
        assert msg.avater[0].fashionWingTempId == 0
