"""Coliseu (desafio por ranking, battleType 16) e torneio de fadas (só pets, battleType 35).

O oponente nunca joga ao vivo: é a cópia de combate de outro jogador (snapshot do banco ou da
sessão dele) ou um robô gerado do id. Fluxo, capturas e fontes em ``docs/pvp.md``; regras em
``game/arena.py``.
"""

from __future__ import annotations

import random
from typing import Any

from ...domain.errors import NotFoundError
from ...domain.models import ArenaRank, BagType, ChallengeLog, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from .. import arena as A
from .. import bag, rules
from .. import events as ev
from ..battle import Battle
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .campaign import map_sync, player_hero
from .login import army, player_info
from .player import push_level
from .vip import is_vip, vip_grade

S_PLAYER, S_CHAT, S_ALERT, S_ITEMS, S_FULL_ARMY, S_MAP_SYNC = 3, 83, 111, 115, 150, 140
S_INFO, S_COOL, S_RESET, S_TAKE, S_IS_TAKE, S_CROSS = 4169, 4176, 4202, 4243, 4244, 4482
S_PET_LIST, S_PET_TOP, S_PET_REWARD, S_PET_INFO, S_BATTLE_REPORT = 4611, 4619, 4613, 4540, 4103
S_QUESTS = 112  # QuestUpdatedRspMsg
QUEST_PET_TOURNAMENT = 87  # QuestCondictionInfos: participar do torneio de fadas (Para2 1)
S_MATCH = 4201  # MatchStateMsg: liga o botão de PvP (playerInfo.isPVPStart)
PVP_GRADE = 22  # TopToolsBar: o botão de PvP só aparece a partir do nível 22
ARMY_IDLE, ARMY_FIGHTING = 0, 2
WON, LOST = 1, 2  # BattleReportMsg.battleResult e ChallengeLogMsg.result
OPPONENTS = 4
PET_DAY, PET_WEEK = 1, 2  # RankRewardMsg.type
CLAIMABLE, CLAIMED = 0, 1  # RankRewardMsg.status
PET_TOP = 10
PET_ROBOT_ORDER = 500  # posição mostrada para os robôs (só turco: peri_turnuvasi #3, 500-502)
GOD_ARRIVE = 2  # ChallengeMsg.type do 5021 da "chegada dos deuses" (outro sistema)
COLOSSEUM_NOVICE = 30000  # o cliente só abre o coliseu com noviceProcess acima disso (gotoColosseumFrame)


def _arena(s: GameSession) -> Any:
    """Arena do jogador com o dia em dia; se o dia virou com a tela aberta, avisa o cliente (4202)."""
    snap = s.snapshot
    assert snap is not None and snap.arena is not None
    if A.roll_day(snap.arena, s.ctx.clock.now()):
        s.send(S_RESET, A.data_reset(snap, s.ctx.clock.now()))
    return snap.arena


def _cool(s: GameSession, kind: int) -> None:
    s.send(S_COOL, A.cool_time(_arena(s), kind, s.ctx.clock.now(), s.ctx.templates))


def login(s: GameSession, msg: pb.PlayerDataMsg) -> None:
    """Partes do 8224 que são deste sistema (a 4176 de tipo 0 conta como um passo da carga).
    O dia vira em silêncio: a 4202 no meio da carga viria antes da 4176. Fica só na memória; o
    próximo save grava, e sem save a virada se repete igual no próximo login."""
    snap = s.snapshot
    assert snap is not None and snap.arena is not None
    A.roll_day(snap.arena, s.ctx.clock.now())
    _cool(s, A.COLOSSEUM)
    _cool(s, A.PETS)


async def login_rewards(s: GameSession, msg: pb.PlayerDataMsg) -> None:
    """4244 (pode resgatar a recompensa do coliseu), 4613 (do torneio) e 4481 (entre servidores)."""
    arena, now = _arena(s), s.ctx.clock.now()
    if msg.challReward:
        rank = await s.ctx.characters.arena_rank(s.player_id)
        s.send(S_IS_TAKE, pb.ChallengeRankRewardMsg(isTake=A.can_claim(arena, rank, now)))
    if msg.petChallengeReward:
        order = await _pet_order(s)
        if order:
            if arena.pet_reward_day != A.today(now):
                s.send(S_PET_REWARD, pb.RankRewardMsg(type=PET_DAY, status=CLAIMABLE, rank=order, opType=0))
            if arena.pet_reward_week != A.week(now):
                s.send(S_PET_REWARD, pb.RankRewardMsg(type=PET_WEEK, status=CLAIMABLE, rank=order, opType=0))
    if msg.crossScoreReward:
        s.send(4481, pb.ChallengeRankRewardMsg(isTake=False))  # sem servidores cruzados


async def _snapshot(s: GameSession, user_id: int) -> PlayerSnapshot | None:
    """Outro jogador do mesmo servidor: o da sessão (mais novo) ou o do banco."""
    other = s.ctx.online.get(user_id)
    if other is not None and other.snapshot is not None:
        snap = other.snapshot
    else:
        try:
            snap = await s.ctx.characters.snapshot(user_id)
        except NotFoundError:
            return None
    ok = snap.character.active and snap.server.id == s.snapshot.server.id and snap.leader is not None  # type: ignore[union-attr]
    return snap if ok else None


def _avatars(msg: pb.ChallengeInfoMsg, snap: PlayerSnapshot, s: GameSession) -> None:
    """``avater``: arma e armadura equipadas, pelo template (o cliente busca a arte)."""
    for item in snap.items:
        if item.bag_type != BagType.HERO:
            continue
        son = (s.ctx.templates.get("ItemTempInfos", item.template_id) or {}).get("SonType")
        if son == rules.WEAPON:
            msg.avater.add(userId=snap.character.id or 0, armTempId=item.template_id)
        elif son == rules.CLOTH:
            msg.avater.add(userId=snap.character.id or 0, clothTempId=item.template_id)


def _log_msg(log: ChallengeLog, owner: int) -> pb.ChallengeLogMsg:
    return pb.ChallengeLogMsg(
        userId=owner,
        result=WON if log.won else LOST,
        tarUserId=log.target_id,
        tarNickName=log.target_name,
        isAttack=log.is_attack,
        logDate=b.fmt_time(log.created_at),
        curRankResult=log.rank,
        grades=log.target_grades,
        gpOrder=0,
        gp=0,
        job=log.target_job,
        forward=log.forward,
    )


# -- coliseu ---------------------------------------------------------------------------------------


def _novice(s: GameSession) -> bool:
    """Coliseu liberado: o tutorial já passou do ponto em que o cliente abre a tela."""
    assert s.snapshot is not None
    if s.snapshot.character.novice_process > COLOSSEUM_NOVICE:
        return True
    s.log.info("coliseu antes do tutorial", novice=s.snapshot.character.novice_process)
    return False


async def _colosseum_info(s: GameSession) -> None:
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    server, me = snap.server.id, s.player_id
    rank = await s.ctx.characters.arena_rank(me)
    msg = pb.ChallengeInfoMsg(lastWinCount=arena.win_streak, challengeCount=arena.challenge_count, curRank=rank)
    offer: dict[int, int] = {}
    if rank:
        # acima de mim, espaçados como no oficial (só turco: meydan_okuma #46, 1693 via 1637, 1590, 1576, 1523);
        # o 1º vê os de baixo
        step = max(1, rank // 30)
        low, high = (max(1, rank - OPPONENTS * step), rank - 1) if rank > 1 else (2, 1 + OPPONENTS)
        rows = [r for r in await s.ctx.characters.arena_ranks(server, low, high) if r.character_id != me]
        for row in sorted(random.sample(rows, min(OPPONENTS, len(rows))), key=lambda r: -r.rank):
            other = await _snapshot(s, row.character_id)
            if other is not None:
                msg.simplePlayer.append(A.snapshot_player(other, s.ctx.templates, row.rank, s.ctx.clock.now()))
                _avatars(msg, other, s)
                offer[row.character_id] = 0
    grade = snap.character.grades
    for robot in A.robots(f"{me}:{arena.day}:{arena.challenge_count}", OPPONENTS - len(offer), grade):
        msg.simplePlayer.append(A.robot_player(robot, s.ctx.templates))
        offer[robot.id] = robot.grade
    s.arena_offer = offer
    for log in await s.ctx.characters.challenge_logs(me, A.COLOSSEUM, A.LOGS):
        msg.challengeLog.append(_log_msg(log, me))
    msg.noticMsg, msg.leftDay = "", A.period(now)[1]
    msg.totalCount, msg.totalBuyCount = A.FREE_COUNT, A.MAX_BUY
    s.send(S_INFO, b.complete(msg))


@router.on(8256)
async def challenge_info(s: GameSession, msg: pb.ChallengeRequestMsg) -> None:
    """Lista de oponentes: 0 coliseu (4169), 1 torneio de fadas (4611), 2 os melhores do torneio (4619)."""
    if msg.type == A.COLOSSEUM:
        if _novice(s):
            await _colosseum_info(s)
    elif msg.type == A.PETS:
        await _pet_info(s)
    else:
        await _pet_top(s)


@router.on(8253)
async def challenge(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """Desafia um oponente da última lista; além das 10 grátis, a tentativa custa diamantes."""
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    target = msg.tarUserId
    reason = (
        "tutorial"
        if not _novice(s)
        else "fora da lista"
        if target not in s.arena_offer
        else "em espera"
        if A.left(arena.cool_until, now)
        else "sem tentativas"
        if arena.challenge_count >= A.FREE_COUNT + A.MAX_BUY
        else ""
    )
    other = None
    if not reason and not A.is_robot(target) and (other := await _snapshot(s, target)) is None:
        reason = "oponente sumiu"
    # daqui em diante sem await até gravar: outro 8253 não passa no meio
    bought = arena.challenge_count >= A.FREE_COUNT
    if not reason and s.battle is not None:
        reason = "em batalha"
    cost = A.buy_cost(arena.challenge_count - A.FREE_COUNT) if bought else 0
    if not reason and bought and not A.pay_diamonds(snap, cost, bind_ok=msg.payType == 0):
        reason = "sem diamantes"
    if reason:
        s.log.info("8253 recusado", motivo=reason, alvo=target)
        _cool(s, A.COLOSSEUM)
        return
    arena.challenge_count += 1
    arena.cool_until = A.cool_until(now, A.COLOSSEUM_COOL)
    hero = player_hero(s, A.colosseum_spec([], []))
    if other is not None:
        soldiers: list[dict[str, Any]] = []
        heroes = [A.copy_hero(other, s.ctx.templates, s.ctx.clock.now())]
        name, grade, job = other.character.nickname or "", other.character.grades, rules.job_type(other.character.job)
    else:
        robot = A.Robot(target, s.arena_offer[target])
        soldiers, heroes = A.robot_spec(robot, s.ctx.templates, hero.msg.hp, hero.attack)
        name, grade, job = robot.name, robot.grade, 1
    spec = A.colosseum_spec(soldiers, heroes)

    async def finished(battle: Battle, won: bool) -> None:
        await _colosseum_over(s, battle, won, target, name, grade, job)

    s.battle = Battle(spec, hero, s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings)
    # gasta antes da luta: cair não devolve; a atividade "Solo Arena" (tipo 26) conta a participação, como o leed 19
    counted = ev.count(snap, s.ctx.events, ev.CHALLENGE, s.ctx.clock.now())
    await s.ctx.characters.save(snap.character, arena, *counted)
    s.log.info("coliseu", alvo=target, battle=s.battle.id)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    s.battle.start()
    if bought:
        s.send(S_PLAYER, b.complete(player_info(s, snap)))
    from . import events  # handlers.events importa login, que importa este módulo

    await events.leed_done(s, events.CHALLENGE_LEED)  # LeedTemp 19 "Challenge another player" (PassCount 10)


async def _colosseum_over(
    s: GameSession, battle: Battle, won: bool, target: int, name: str, grade: int, job: int
) -> None:
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None and snap.character.id is not None
    s.battle, s.hero_sp = None, battle.player_sp
    me, robot, before = snap.character.id, A.is_robot(target), snap.character.grades
    async with A.RANK_LOCK:  # posições relidas aqui: outra luta pode ter mexido nelas durante esta
        mine = await s.ctx.characters.arena_rank(me)
        theirs = 0 if robot else await s.ctx.characters.arena_rank(target)
        ranks: list[ArenaRank] = []
        if won and not mine:  # a primeira vitória entra no fim do ranking
            mine_new = theirs or await s.ctx.characters.arena_last_rank(snap.server.id) + 1
            ranks.append(ArenaRank(me, mine_new))
            if theirs:
                ranks.append(ArenaRank(target, await s.ctx.characters.arena_last_rank(snap.server.id) + 1))
        elif won and theirs and theirs < mine:  # venceu alguém acima: trocam de lugar
            ranks += [ArenaRank(me, theirs), ArenaRank(target, mine)]
        new_mine = next((r.rank for r in ranks if r.character_id == me), mine)
        new_theirs = next((r.rank for r in ranks if r.character_id == target), theirs)
        arena.win_streak = arena.win_streak + 1 if won else 0
        # a espera conta do fim (só turco: meydan_okuma #29, 600)
        arena.cool_until = A.cool_until(now, A.COLOSSEUM_COOL)
        gp = A.battle_gp(snap.character.grades, won)
        rules.add_gp(snap, s.ctx.templates, gp)
        logs = [
            ChallengeLog(me, A.COLOSSEUM, now, target, name, True, won, new_mine, _forward(mine, new_mine), grade, job)
        ]
        if not robot:  # o atacado também vê a luta no histórico (a cópia dele defendeu)
            c = snap.character
            forward = _forward(theirs, new_theirs)
            jt = rules.job_type(c.job)
            logs.append(
                ChallengeLog(
                    target, A.COLOSSEUM, now, me, c.nickname or "", False, not won, new_theirs, forward, c.grades, jt
                )
            )
        await s.ctx.characters.save(snap.character, snap.leader, *snap.pawns, arena, *logs, ranks=tuple(ranks))
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    if snap.character.grades > before:
        push_level(s, before)  # (dedução) como na entrega de missão
    else:
        s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    report = pb.BattleReportMsg(battleResult=WON if won else LOST, strategyBonus=0, gpBonus=gp)
    report.battleScene, report.failCount, report.goldBonus, report.petGpBonus = 7, 0, 0, 0
    s.send(S_BATTLE_REPORT, report)
    if gp:
        # texto do oficial inglês (83, tutorial_en: "Received 3,000 EXP ", com o espaço)
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Received {gp:,} EXP "))
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    _cool(s, A.COLOSSEUM)


def _forward(before: int, after: int) -> int:
    return 0 if before == after else 1 if before == 0 or after < before else 2


@router.on(8265)
async def quick_cool(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Zera a espera do coliseu (type 0) ou do torneio (1) por diamantes; payType 2 aceita vinculado."""
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    kind = A.PETS if msg.type == A.PETS else A.COLOSSEUM
    attr = "pet_cool_until" if kind == A.PETS else "cool_until"
    seconds = A.left(getattr(arena, attr), now)
    if seconds and A.pay_diamonds(snap, A.cool_cost(seconds), bind_ok=msg.payType == 2):
        setattr(arena, attr, None)
        await s.ctx.characters.save(snap.character, arena)
        s.send(S_PLAYER, b.complete(player_info(s, snap)))
    else:
        s.log.info("8265 recusado", espera=seconds, pedido=str(msg))
    _cool(s, kind)


@router.on(8329)
async def take_reward(s: GameSession, _: object) -> None:
    """Recompensa da posição no coliseu (uma por período): ouro e Daru, popup do 4243."""
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    rank = await s.ctx.characters.arena_rank(s.player_id)
    key, days = A.period(now)
    gold = strategy = 0
    if A.can_claim(arena, rank, now):
        gold, strategy = A.rank_reward(rank)
        arena.reward_day = key
        snap.character.gold += gold
        snap.character.strategy += strategy
        await s.ctx.characters.save(snap.character, arena)
        castle_yield(s)
        s.send(S_PLAYER, b.complete(player_info(s, snap)))
    else:
        s.log.info("8329 recusado", rank=rank, resgatado=arena.reward_day)
    s.send(S_TAKE, pb.ChallengeRankRewardMsg(isTake=False, param1=rank, param2=gold, param3=strategy, param4=days))


@router.on(8590)
async def cross_score_reward(s: GameSession, _: object) -> None:
    """Pontos da arena entre servidores: não há servidores cruzados, então "sem direito" (4482)."""
    s.send(S_CROSS, pb.ChallengeRankRewardMsg(isTake=False, param1=0, param2=0, param3=0, param4=0))


@router.on(8635)
async def challenge_self(s: GameSession, msg: pb.QuestInfo) -> None:
    """Lutar contra a própria cópia: ação de missão com condição tipo 92, que não existe no tempinfos."""
    s.log.info("8635 recusado (nenhuma missão tipo 92)", quest=msg.templateId)


@router.on(5021)
async def add_attack_count(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """Compra tentativa: type 1 é o torneio de fadas (ouro, ``Jion_pet_challenge``); type 2 é a
    chegada dos deuses (outro sistema). O coliseu compra pelo próprio 8253."""
    snap = s.snapshot
    assert snap is not None
    if msg.type != A.PETS:
        s.log.info("5021 sem efeito aqui", pedido=str(msg))
        return
    arena = _arena(s)
    count = max(1, msg.tarArmyId)
    cost = A.config(s.ctx.templates, "Jion_pet_challenge", 50000) * count
    # ponytail: limite de compras do torneio não está no cliente nem nos templates; 10/dia como no coliseu
    if arena.pet_buy_count + count > A.MAX_BUY or snap.character.gold < cost:
        s.log.info("5021 recusado", ouro=snap.character.gold, compradas=arena.pet_buy_count)
    else:
        snap.character.gold -= cost
        arena.pet_buy_count += count
        await s.ctx.characters.save(snap.character, arena)
        castle_yield(s)
    _cool(s, A.PETS)


# -- torneio de fadas ------------------------------------------------------------------------------


async def _pet_order(s: GameSession) -> int:
    snap = s.snapshot
    assert snap is not None and snap.arena is not None
    if not A.formation(snap.arena, snap):
        return 0
    return await s.ctx.characters.pet_order(snap.server.id, snap.arena.pet_score)


def _pet_player(other: PlayerSnapshot, order: int) -> pb.PlayerPetMsg:
    assert other.arena is not None
    msg = pb.PlayerPetMsg(userId=other.character.id or 0, nickName=other.character.nickname or "")
    msg.order, msg.score = order, other.arena.pet_score
    for pet in A.formation(other.arena, other):
        msg.petInfo.add(
            petId=pet.id, templateId=pet.template, petName=pet.name, curGrade=pet.grade, quality=pet.quality
        )
    return msg


async def _pet_info(s: GameSession) -> None:
    """4611: eu (pontos e posição; o cliente monta a própria linha), oponentes e histórico."""
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    me, server = s.player_id, snap.server.id
    order = await _pet_order(s)
    remaining = max(0, A.pet_total(arena, s.ctx.templates) - arena.pet_count)
    msg = pb.PetChallengeInfoMsg()
    msg.playerInfo.leftTime, msg.playerInfo.challengeCount = A.left(arena.pet_cool_until, now), remaining
    msg.playerInfo.totalCount, msg.playerInfo.score, msg.playerInfo.order = 0, arena.pet_score, order
    offer: dict[int, int] = {}
    # os de pontos mais perto acima (o próprio jogador não vai: apareceria duas vezes)
    above = [a for a in await s.ctx.characters.pet_board(server, PET_TOP * 5) if a.character_id != me]
    above = sorted((a for a in above if a.pet_score >= arena.pet_score), key=lambda a: a.pet_score)[:OPPONENTS]
    for row in above:
        other = await _snapshot(s, row.character_id)
        if other is not None and A.formation(row, other):
            msg.playerPets.append(_pet_player(other, await s.ctx.characters.pet_order(server, row.pet_score)))
            offer[row.character_id] = 0
    seed = f"pet:{me}:{arena.day}:{arena.pet_count}"
    for i, robot in enumerate(A.robots(seed, OPPONENTS - len(offer), A.PET_ROBOT_GRADE, A.PET_ROBOT_BASE)):
        info = A.pet_robot_info(robot, s.ctx.templates)
        info.order = PET_ROBOT_ORDER + i
        msg.playerPets.append(info)
        offer[robot.id] = robot.grade
    s.pet_offer = offer
    for log in await s.ctx.characters.challenge_logs(me, A.PETS, A.LOGS):
        entry = msg.challengeLog.add(
            userId=me, tarUserId=log.target_id, tarNickName=log.target_name, result=WON if log.won else LOST
        )
        entry.isAttack, entry.logDate, entry.score = log.is_attack, b.fmt_time(log.created_at), log.rank
    s.send(S_PET_LIST, b.complete(msg))


async def _pet_top(s: GameSession) -> None:
    snap = s.snapshot
    assert snap is not None
    msg = pb.PetChallengeInfoMsg()
    for row in await s.ctx.characters.pet_board(snap.server.id, PET_TOP):
        other = await _snapshot(s, row.character_id)
        if other is not None and A.formation(row, other):
            msg.playerPets.append(_pet_player(other, await s.ctx.characters.pet_order(snap.server.id, row.pet_score)))
    s.send(S_PET_TOP, b.complete(msg))


@router.on(8724)
async def challenge_pet(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """Desafio do torneio: luta automática dos pets da formação contra os do oponente."""
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    target = msg.tarUserId
    mine = A.formation(arena, snap)
    remaining = A.pet_total(arena, s.ctx.templates) - arena.pet_count
    reason = (
        "em batalha"
        if s.battle is not None
        else "nível"
        if snap.character.grades < A.config(s.ctx.templates, "Pet_Challenge_Grade", 55)
        else "formação vazia"
        if not mine
        else "fora da lista"
        if target not in s.pet_offer
        else "em espera"
        if A.left(arena.pet_cool_until, now)
        else "sem tentativas"
        if remaining <= 0
        else ""
    )
    other = None
    if not reason and not A.is_robot(target):
        other = await _snapshot(s, target)
        if other is None or other.arena is None or not A.formation(other.arena, other):
            reason = "oponente sem pets"
    if reason or s.battle is not None:
        s.log.info("8724 recusado", motivo=reason or "em batalha", alvo=target)
        _cool(s, A.PETS)
        return
    me = s.player_id
    units = [
        A.pet_unit(p.template, p.grade, p.quality, i + 1, 1, p.slot + 1, me, p.id, s.ctx.templates, p.skills)
        for i, p in enumerate(mine)
    ]
    if other is not None and other.arena is not None:
        theirs = [
            A.pet_unit(p.template, p.grade, p.quality, len(units) + i + 1, 2, i + 3, 0, 0, s.ctx.templates, p.skills)
            for i, p in enumerate(A.formation(other.arena, other))
        ]
        name = other.character.nickname or ""
    else:
        theirs = A.pet_robot_units(s.ctx.templates, len(units) + 1)
        name = A.Robot(target, A.PET_ROBOT_GRADE).name
    spec = A.pet_spec(units, theirs)
    arena.pet_count += 1  # o gasto só depois de montar a luta: um erro antes não come a tentativa
    arena.pet_cool_until = A.cool_until(now, A.PET_COOL)

    async def finished(battle: Battle, won: bool) -> None:
        await _pet_over(s, won, target, name)

    s.battle = Battle(spec, None, s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings)
    await s.ctx.characters.save(arena)
    s.log.info("torneio de fadas", alvo=target, battle=s.battle.id)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    s.battle.start()


async def _pet_over(s: GameSession, won: bool, target: int, name: str) -> None:
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None and snap.character.id is not None
    s.battle = None
    delta = A.PET_WIN_SCORE if won else -A.PET_LOSE_SCORE
    arena.pet_score = max(0, arena.pet_score + delta)
    arena.pet_cool_until = A.cool_until(now, A.PET_COOL)
    me, c = snap.character.id, snap.character
    logs = [ChallengeLog(me, A.PETS, now, target, name, True, won, delta)]
    if not A.is_robot(target):  # só o histórico do atacado muda; os pontos dele não (não observado)
        logs.append(ChallengeLog(target, A.PETS, now, me, c.nickname or "", False, not won, 0))
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_PET_TOURNAMENT, 0, 1)  # participar conta, ganhando ou não
    counted = ev.count(snap, s.ctx.events, ev.PET_CHALLENGE, now)  # atividade "Sylph Arena" (tipo 110), idem
    await s.ctx.characters.save(arena, *logs, *quests, *counted)
    _cool(s, A.PETS)
    report = pb.BattleReportMsg(battleResult=WON if won else LOST, strategyBonus=0, gpBonus=0)
    report.battleScene, report.failCount, report.goldBonus, report.petGpBonus = 19, 0, 0, 0
    s.send(S_BATTLE_REPORT, report)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    if delta:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Puan  {delta:+d}"))


@router.on(8725)
async def pet_formation(s: GameSession, msg: pb.PlayerPetMsg) -> None:
    """Formação do torneio: ``chaPos`` com ids de pets do jogador e -1 nos espaços vazios."""
    snap = s.snapshot
    assert snap is not None
    if not msg.HasField("chaPos"):  # os Senhores mandam o 8725 vazio
        return
    arena = _arena(s)
    owned = {p.id for p in A.pets_of(snap)}
    try:
        ids = [int(x) for x in msg.chaPos.split(",")]
    except ValueError:
        ids = []
    used = [i for i in ids if i != -1]
    if not ids or len(ids) > 6 or len(set(used)) != len(used) or not set(used) <= owned:
        s.log.info("8725 recusado", chaPos=msg.chaPos)
        return
    arena.pet_formation = ",".join(map(str, ids)) if used else ""
    await s.ctx.characters.save(arena)
    s.send(S_PET_INFO, pb.PlayerPetMsg(userId=s.player_id, chaPos=",".join(map(str, ids))))


@router.on(8726)
async def pet_skills(s: GameSession, msg: pb.PetInfoMsg) -> None:
    """Skills do pet no torneio (``chaSkillIndexs``): o pet tem de ser do jogador; sem pets, recusa."""
    snap = s.snapshot
    assert snap is not None
    if msg.petId not in {p.id for p in A.pets_of(snap)}:
        s.log.info("8726 recusado (pet não é do jogador)", pet=msg.petId)
        return
    s.send(
        S_PET_INFO,
        pb.PlayerPetMsg(
            userId=s.player_id, petInfo=[pb.PetInfoMsg(petId=msg.petId, chaSkillIndexs=msg.chaSkillIndexs)]
        ),
    )


@router.on(8727)
async def pet_end_battle(s: GameSession, msg: pb.BattleReqMsg) -> None:
    """Botão "Encerrar já" do torneio (``Battle.finish``). O cliente só mostra o botão para VIP ativo
    com nível >= ``Pet_BattleOver_Grade`` (BattleUIView: ``IsVipAndNoExpirt`` e ``VipGrade`` >= 3)."""
    snap, battle, now = s.snapshot, s.battle, s.ctx.clock.now()
    assert snap is not None
    need = A.config(s.ctx.templates, "Pet_BattleOver_Grade", 3)
    vip = is_vip(snap, now) and vip_grade(s, snap) >= need  # VIP vencido não conta, mesmo com o nível
    if battle is None or battle.id != msg.battleId or battle.spec["battleType"] != 35 or not vip:
        s.log.info("8727 recusado", vip=vip)
        return
    battle.finish()


@router.on(8728)
async def pet_rank_reward(s: GameSession, msg: pb.RankRewardMsg) -> None:
    """Recompensa diária (type 1) ou semanal (2) pela posição no torneio (``PetChallengeRewards``)."""
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    kind = PET_WEEK if msg.type == PET_WEEK else PET_DAY
    attr, key = ("pet_reward_week", A.week(now)) if kind == PET_WEEK else ("pet_reward_day", A.today(now))
    order = await _pet_order(s)
    goods = A.pet_rewards(s.ctx.templates, kind, order) if order else []
    free = len(bag.free_positions(snap, now))
    if not goods or getattr(arena, attr) == key or len(goods) > free:
        s.log.info("8728 recusado", tipo=kind, posição=order, resgatado=getattr(arena, attr))
        return
    setattr(arena, attr, key)
    new = []
    for template, count in goods:
        item = Item(s.player_id, template, count=count, pos=rules.free_bag_pos(snap))
        snap.items.append(item)
        new.append(item)
    await s.ctx.characters.save(arena, *new)
    for item in new:
        s.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
    s.send(S_PET_REWARD, pb.RankRewardMsg(type=kind, status=CLAIMED, rank=order, opType=1))


@router.on(8294)
async def match_state(s: GameSession, _: object) -> None:
    """Estado do botão de PvP (``TopToolsBar.sendMatch``: no login com nível 22 e ao chegar nele). O login turco
    (login.json #82, nível 56) manda 4201 falso; o inglês (tutorial_en #24-#136, nível 1) não manda nenhum; o
    cliente só pede daí em diante."""
    assert s.snapshot is not None
    s.send(S_MATCH, b.complete(pb.MatchStateMsg(matchState=s.snapshot.character.grades >= PVP_GRADE)))
