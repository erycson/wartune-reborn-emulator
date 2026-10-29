"""Coliseu (desafio por ranking, battleType 16) e torneio de fadas (só pets, battleType 35).

O oponente nunca joga ao vivo: é a cópia de combate de outro jogador (snapshot do banco ou da
sessão dele) ou um robô gerado do id. Fluxo, capturas e fontes em ``docs/pvp.md``; regras em
``game/arena.py``.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from ...domain.errors import NotFoundError
from ...domain.models import ArenaRank, BagType, ChallengeLog, EventState, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import arena as A
from .. import arena_grupo as ag
from .. import bag, rewards, rules, taxas, titles
from .. import events as ev
from ..battle import Battle
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .campaign import map_sync, player_hero
from .events import click_info, items_gained
from .login import player_info
from .player import push_level
from .vip import free_cool, is_vip, vip_grade

S_PLAYER, S_CHAT, S_ALERT, S_ITEMS, S_FULL_ARMY, S_MAP_SYNC = 3, 83, 111, 115, 150, 140
S_INFO, S_COOL, S_RESET, S_TAKE, S_IS_TAKE, S_CROSS = 4169, 4176, 4202, 4243, 4244, 4482
S_PET_LIST, S_PET_TOP, S_PET_REWARD, S_PET_INFO, S_BATTLE_REPORT = 4611, 4619, 4613, 4540, 4103
S_QUESTS = 112  # QuestUpdatedRspMsg
S_CLICK_ADD = 4413  # ClickDatasRspMsg: um contador do painel de atividades subiu
PRIZE_KEY = "arena:prize"  # event_states: prêmios do coliseu no dia (``_prize``)
QUEST_CHALLENGE = 35  # QuestCondictionInfos 2/4/188 "Challenge" (Para1 1): cada desafio do coliseu conta
QUEST_PET_TOURNAMENT = 87  # QuestCondictionInfos: participar do torneio de fadas (Para2 1)
S_MATCH = 4201  # MatchStateMsg: liga o botão de PvP (playerInfo.isPVPStart)
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
    if msg.crossScoreReward:  # (cliente) LoginInitDataAccept.__pvpTakeHandler: isTake liga o botão
        assert s.snapshot is not None
        cfg = dict(s.ctx.world.settings.get("arena_party") or {})
        ok = ag.can_claim(s.snapshot, now, cfg, s.ctx.world.settings.get("cross_score") or {})
        s.send(4481, pb.ChallengeRankRewardMsg(isTake=ok))


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


AVATAR_FIELDS = {rules.WEAPON: "armTempId", rules.CLOTH: "clothTempId", rules.WING: "fashionWingTempId"}
AVATAR_FIELDS |= {rules.FASHION_ARM: "fashionArmTempId", rules.FASHION_CLOTH: "fashionClothTempId"}
AVATAR_FIELDS[rules.HAT] = "fashionHeadTempId"


def _avatars(msg: pb.ChallengeInfoMsg, snap: PlayerSnapshot, s: GameSession) -> None:
    """``avater`` (``ColosseumControler``): os templates equipados no líder, arma, armadura e a moda (asa, arma,
    roupa, chapéu), e o cliente busca a arte. Com a moda escondida vão só arma e armadura (*dedução*)."""
    leader = snap.leader
    if leader is None:
        return
    entry = msg.avater.add(userId=snap.character.id or 0)
    for item in snap.items:
        if item.bag_type != BagType.HERO or item.object_id != leader.id:
            continue
        son = (s.ctx.templates.get("ItemTempInfos", item.template_id) or {}).get("SonType")
        name = AVATAR_FIELDS.get(son or "")
        if name and not (leader.hide_fashion and son not in (rules.WEAPON, rules.CLOTH)):
            setattr(entry, name, item.template_id)


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
    elif msg.type == A.PETS:  # (só turco: peri_turnuvasi #2-#3 e #57-#58) 4176 tipo 1 e 4611
        _cool(s, A.PETS)
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
    spent = None
    if not reason and bought:
        spent = ledger.pay(snap.character, cost, bind=msg.payType == 0, reason="arena_count", ref="", now=now)
        reason = "" if spent is not None else "sem diamantes"
    if reason:
        s.log.info("8253 recusado", motivo=reason, alvo=target)
        _cool(s, A.COLOSSEUM)
        return
    arena.challenge_count += 1
    arena.cool_until = A.cool_until(now, A.COLOSSEUM_COOL)
    hero = player_hero(s, A.colosseum_spec([], []), camp=806)  # cartas da arena (systems.CAMP_ARENA)
    if other is not None:
        soldiers: list[dict[str, Any]] = []
        heroes = [A.copy_hero(other, s.ctx.templates, s.ctx.clock.now())]
        name, grade, job = other.character.nickname or "", other.character.grades, rules.job_type(other.character.job)
    else:
        robot = A.Robot(target, s.arena_offer[target])
        soldiers, heroes = A.robot_spec(robot, s.ctx.templates, hero.msg.hp, hero.attack, s.ctx.world.settings)
        name, grade, job = robot.name, robot.grade, 1
    spec = A.colosseum_spec(soldiers, heroes)

    async def finished(battle: Battle, won: bool) -> None:
        await _colosseum_over(s, battle, won, target, name, grade, job)

    s.battle = Battle(spec, hero, s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings)
    # gasta antes da luta: cair não devolve; a atividade "Solo Arena" (tipo 26) conta a participação, como o leed 19
    counted = ev.count(snap, s.ctx.events, ev.CHALLENGE, s.ctx.clock.now())
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_CHALLENGE, 1, 1)
    await s.ctx.characters.save(snap.character, arena, *counted, *quests, *([spent] if spent else []))
    s.log.info("coliseu", alvo=target, battle=s.battle.id, missoes=[q.template_id for q in quests])
    # (visto) oficial_20261023-215937-1 #1129-#1133: 140, 112 (missão 188), 4152 (leed 19) e só então 157
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    from . import events  # handlers.events importa login, que importa este módulo

    await events.leed_done(s, events.CHALLENGE_LEED)  # LeedTemp 19 "Challenge another player" (PassCount 10)
    s.battle.start()
    if bought:
        s.send(S_PLAYER, b.complete(player_info(s, snap)))


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
        gp, world, rested = rules.exp_bonus(
            snap.character, s.ctx.world.settings, A.battle_gp(snap.character.grades, won)
        )
        rules.add_gp(snap, s.ctx.templates, gp)
        from .pets import share_gp  # noqa: PLC0415  (pets importa shop, que importa este módulo)

        pet = share_gp(s, gp)  # (só turco: meydan_okuma #22, #26) petGpBonus = gpBonus e o 4540 depois do 3
        prize = _prize(s, snap, won, now)
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
        changed = [*prize[0], prize[2]] if prize else []
        if won:  # título "Prize Fighter" (Accumulated 1000 Arena wins)
            changed.append(titles.count(snap, titles.ARENA_WINS, now))
        await s.ctx.characters.save(
            snap.character, snap.leader, *snap.pawns, arena, *logs, *changed, *([pet] if pet else []),
            ranks=tuple(ranks),
        )  # fmt: skip
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    if pet is not None:
        from .pets import send_gained  # noqa: PLC0415

        send_gained(s, pet)
    if snap.character.grades > before:
        await push_level(s, before)  # (dedução) como na entrega de missão
    # (visto) oficial_20261023-215937-1 #1163-#1167: sem o 150 entre o 3 e o 4103 (sem mascote; com ele, o do 4540)
    report = pb.BattleReportMsg(battleResult=WON if won else LOST, strategyBonus=0, gpBonus=gp)
    report.battleScene, report.failCount, report.goldBonus, report.petGpBonus = 7, 0, 0, gp if pet else 0
    s.send(S_BATTLE_REPORT, report)
    if gp:
        # texto do oficial inglês (83, tutorial_en: "Received 3,000 EXP ", com o espaço)
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=rules.exp_text(gp, world, rested)))
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    _cool(s, A.COLOSSEUM)
    if prize:  # (visto) oficial_20261023-215937-1 #1168-#1181: 115, 4476, 4426, 4484 ×9, 111, 83
        s.send(S_ITEMS, bag.moved(prize[0], s.player_id))
        items_gained(s)
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=prize[1]))
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=prize[1]))


def _prize(s: GameSession, snap: PlayerSnapshot, won: bool, now: datetime) -> tuple[list[Item], str, EventState] | None:
    """``game_settings.arena_challenge_items`` (migração 0072): um item sorteado de ``pool`` ([[templateId,
    quantidade], ...]) na mochila ao fim da luta do coliseu, ``win_only`` e no máximo ``daily`` vezes por dia
    (0 = sem limite). Depois do 4176 de uma vitória, a 1ª do dia nas duas: (visto) oficial_20261023-215937-1
    #1168-#1181, 115 (VIP Token 208015), 111 e 83 "Received: VIP Token x1"; (só turco: meydan_okuma #30-#45) Lvl. 3
    Luck Stone x1 (2040103), "Kazanılan:Şans Taşı Lv.3 x1". Nada no cliente nem na internet (wiki Arena: só ouro e
    Daru pela posição).
    TODO(inventado): o conjunto além dos dois vistos, pesos iguais, ``win_only`` true e ``daily`` 1.
    Sem espaço na mochila não dá nada."""
    cfg = s.ctx.world.settings.get("arena_challenge_items", {})
    pool = [(int(t), int(n)) for t, n in cfg.get("pool", [])]
    goods = [random.choice(pool)] if pool else []
    count = ev.daily(snap, PRIZE_KEY, now)
    limit = int(cfg.get("daily", 0))
    if not goods or (cfg.get("win_only", True) and not won) or (limit and count.value >= limit):
        return None
    if not bag.fits(snap, s.ctx.templates, goods, now):
        s.log.info("coliseu sem espaço para o prêmio", premio=goods)
        return None
    changed: list[Item] = []
    for tid, n in goods:
        changed += [i for i in bag.add(snap, s.ctx.templates, tid, n, now) if i not in changed]
    count.value, count.updated_at = count.value + 1, now
    s.log.info("coliseu prêmio", premio=goods, hoje=count.value)
    return changed, rewards.received(s.ctx.templates, goods), count


def _forward(before: int, after: int) -> int:
    # ColosseumEventItem.initRestult: > 0 "ranking rose to", < 0 "ranking dropped to", 0 sem mudança
    return 0 if before == after else 1 if before == 0 or after < before else -1


@router.on(8265)
async def quick_cool(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Zera a espera do coliseu (type 0) ou do torneio (1) por diamantes; payType 2 aceita vinculado. Com VIP
    (``vipCoolPrivilege``) é de graça: o cliente nem abre o quadro do custo (``ColosseumFrame``,
    ``PetChallengeCDView``), como no 5172 index 0."""
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None
    kind = A.PETS if msg.type == A.PETS else A.COLOSSEUM
    attr = "pet_cool_until" if kind == A.PETS else "cool_until"
    seconds = A.left(getattr(arena, attr), now)
    free = bool(seconds) and free_cool(s, snap)
    cost, bind = A.cool_cost(seconds), msg.payType == 2
    spent = (
        None
        if free or not seconds
        else ledger.pay(snap.character, cost, bind=bind, reason="arena_cool", ref="", now=now)
    )
    if seconds and (free or spent is not None):
        setattr(arena, attr, None)
        await s.ctx.characters.save(*([snap.character, spent] if spent else []), arena)
        if not free:
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
    if gold or strategy:  # (visto) 191924-1 #9064-#9069: 109, 3, 4243, 111 e 83 com o mesmo texto; recusa sem captura
        text = f"Retrieve Ranking Rewards: Golds x{gold:,}, Daru x{strategy:,}."
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(8590)
async def cross_score_reward(s: GameSession, _: object) -> None:
    """Prêmio dos pontos PvP (fila local, ``handlers/cruzado.py``): 4482 (cliente ``TopToolsBar.__pvpTakeHandler``)
    ``param2`` pontos, ``param3`` Warrior's Mark (0: "didn't earn") e ``param4`` 1 = título Road Warrior.
    Regra do ``pvpHeroFrame.rewardTip``: 1000 pontos dão a marca; top 20 com 1000, o título.
    O título é o ``AppellInfos`` 25 (CondtionType 21, ``titles.CROSS``): sai pela posição no ranking da fila local e
    vai no 4484 logo depois. TODO(inventado): os itens (``game_settings.cross_score``, migração 0121)."""
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    cfg = dict(s.ctx.world.settings.get("arena_party") or {})
    cross = s.ctx.world.settings.get("cross_score") or {}
    pts = ag.points(ev.peek(snap, ag.KEY), now, cfg)
    marks = title = 0
    drops = [(int(t), int(n)) for t, n in cross.get("mark", [])]
    if ag.can_claim(snap, now, cfg, cross) and rewards.can_grant(snap, s.ctx.templates, drops, now):
        new, text = rewards.grant(snap, s.ctx.templates, drops)
        done = ev.state(snap, ag.REWARD_KEY, now)
        done.text = ag.period(now, cfg)
        await s.ctx.characters.save(*new, done)
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
        items_gained(s)
        marks = sum(n for _, n in drops)
        server = snap.server.id or 0
        states = await s.ctx.characters.read(lambda uow: uow.events.by_prefix(server, ag.KEY))
        place = ag.position(states, s.player_id, now, cfg)
        title = int(0 < place <= int(cross.get("top", ag.TITLE_TOP)))
        if title:  # Road Warrior (AppellInfos 25, CondtionType 21 "Top 20 in Cross-Server PvP"): posição já relida
            from . import events as hev  # noqa: PLC0415  (events importa login, que importa este módulo)

            await hev.title_ranks(s)
            hev.send_titles(s)
    else:
        s.log.info("8590 sem prêmio", pontos=pts)
    s.send(S_CROSS, pb.ChallengeRankRewardMsg(isTake=False, param1=0, param2=pts, param3=marks, param4=title))


@router.on(8635)
async def challenge_self(s: GameSession, msg: pb.QuestInfo) -> None:
    """Lutar contra a própria cópia: ação de missão com condição tipo 92, que não existe no tempinfos."""
    s.log.info("8635 recusado (nenhuma missão tipo 92)", quest=msg.templateId)


@router.on(5021)
async def add_attack_count(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """Compra tentativa: type 1 é o torneio de fadas (ouro, ``Jion_pet_challenge``); type 2 é a
    chegada dos deuses (``tollgate.add_time``). O coliseu compra pelo próprio 8253."""
    snap = s.snapshot
    assert snap is not None
    if msg.type == GOD_ARRIVE:
        from . import tollgate  # noqa: PLC0415  (tollgate importa campaign, que importa este pacote)

        await tollgate.add_time(s, msg)
        return
    if msg.type != A.PETS:
        s.log.info("5021 sem efeito aqui", pedido=str(msg))
        return
    arena = _arena(s)
    count = max(1, msg.tarArmyId)
    cost = A.config(s.ctx.templates, "Jion_pet_challenge", 50000) * count
    # limite de compras do torneio: não está no cliente nem nos templates, taxas.pet_max_buy (0135)
    limit = int(taxas.get(s.ctx.world.settings, "pet_max_buy"))
    if arena.pet_buy_count + count > limit or snap.character.gold < cost:
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


def _pet_team(s: GameSession) -> None:
    """4540 só com o que o painel do torneio lê dos pets da formação, e o ``chaPos``: (só turco: peri_turnuvasi #1,
    a resposta da formação por dedução: é o único 4540 com ``chaPos`` e não se repete no 8256 de #57)."""
    from .pets import pet_star  # noqa: PLC0415  (pets importa shop, que importa este módulo)

    snap, arena = s.snapshot, _arena(s)
    assert snap is not None
    team = {p.id for p in A.formation(arena, snap)}
    if not team:
        return
    msg = pb.PlayerPetMsg(userId=s.player_id, chaPos=arena.pet_formation)
    for p in snap.pets:
        if p.id in team:
            tpl = s.ctx.templates.get("PetTempInfos", p.template_id) or {}
            msg.petInfo.add(
                petId=p.id or 0, templateId=p.template_id, petName=p.name, curGrade=p.grade,
                quality=pet_star(p, tpl), chaSkillIndexs=p.cha_skills,
            )  # fmt: skip
    s.send(S_PET_INFO, msg)


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
    me, cfg, t = s.player_id, s.ctx.world.settings.get("fairy_battle"), s.ctx.templates
    units = [
        A.pet_unit(p.template, p.grade, p.quality, i + 1, 1, p.slot + 1, me, p.id, t, p.skills, cfg)
        for i, p in enumerate(mine)
    ]
    if other is not None and other.arena is not None:
        theirs = [
            A.pet_unit(p.template, p.grade, p.quality, len(units) + i + 1, 2, i + 3, 0, 0, t, p.skills, cfg)
            for i, p in enumerate(A.formation(other.arena, other))
        ]
        name = other.character.nickname or ""
    else:
        theirs = A.pet_robot_units(t, len(units) + 1, cfg)
        name = A.Robot(target, A.PET_ROBOT_GRADE).name
    spec = A.pet_spec(units, theirs)
    arena.pet_count += 1  # o gasto só depois de montar a luta: um erro antes não come a tentativa
    arena.pet_cool_until = A.cool_until(now, A.PET_COOL)
    # atividade "Sylph Arena" (tipo 110): participar conta, ganhando ou não; (só turco: peri_turnuvasi #4-#6) na
    # entrada, com o 4476 e o 4426 entre o 140 e o 157
    counted = ev.count(snap, s.ctx.events, ev.PET_CHALLENGE, now)

    async def finished(battle: Battle, won: bool) -> None:
        await _pet_over(s, won, target, name)

    s.battle = Battle(spec, None, s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings)
    await s.ctx.characters.save(arena, *counted)
    s.log.info("torneio de fadas", alvo=target, battle=s.battle.id)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    from .events import progress  # noqa: PLC0415  (events importa login, que importa este módulo)

    progress(s)
    s.battle.start()


async def _pet_over(s: GameSession, won: bool, target: int, name: str) -> None:
    snap, arena, now = s.snapshot, _arena(s), s.ctx.clock.now()
    assert snap is not None and snap.character.id is not None
    s.battle = None
    fairy = A.FAIRY | dict(s.ctx.world.settings.get("fairy_battle") or {})
    delta = int(fairy["win_score"]) if won else -int(fairy["lose_score"])
    arena.pet_score = max(0, arena.pet_score + delta)
    arena.pet_cool_until = A.cool_until(now, A.PET_COOL)
    me, c = snap.character.id, snap.character
    logs = [ChallengeLog(me, A.PETS, now, target, name, True, won, delta)]
    if not A.is_robot(target):  # só o histórico do atacado muda; os pontos dele não (não observado)
        logs.append(ChallengeLog(target, A.PETS, now, me, c.nickname or "", False, not won, 0))
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_PET_TOURNAMENT, 0, 1)  # participar conta, ganhando ou não
    clicked = ev.click(snap, "pet", now)
    await s.ctx.characters.save(arena, *logs, *quests, clicked)
    _cool(s, A.PETS)
    report = pb.BattleReportMsg(battleResult=WON if won else LOST, strategyBonus=0, gpBonus=0)
    report.battleScene, report.failCount, report.goldBonus, report.petGpBonus = 19, 0, 0, 0
    s.send(S_BATTLE_REPORT, report)
    team = {p.id for p in A.formation(arena, snap)}
    if team:  # (só turco: peri_turnuvasi #47-#51) 4540 do time (sem EXP: petGpBonus 0), 4387 e 150 depois do 4103
        from .pets import send_gained  # noqa: PLC0415

        send_gained(s, *(p for p in snap.pets if p.id in team))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    # (só turco: peri_turnuvasi #53) {keys "pet", keyData 1, changeTime} entre o 112 e o 140
    s.send(S_CLICK_ADD, pb.ClickDatasRspMsg(info=[click_info(clicked)]))
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    if delta:
        text = f"Points  {delta:+d}"  # (só turco: "Puan  +5"; "Points" por dedução)
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
        # (só turco: peri_turnuvasi #70) o mesmo texto no 111; lá saiu depois, no meio da entrega da 504 (a ordem é
        # dedução: o oficial parece segurar o aviso enquanto o resultado está na tela)
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))


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
    if used:
        _pet_team(s)
    else:
        s.send(S_PET_INFO, pb.PlayerPetMsg(userId=s.player_id, chaPos=",".join(map(str, ids))))


@router.on(8726)
async def pet_skills(s: GameSession, msg: pb.PetInfoMsg) -> None:
    """Skills do pet no torneio (``chaSkillIndexs``): 3 índices na lista ``changeSkills`` do pet, -1 = vazio, sem
    repetir (``PetChallengeTeamItemView`` troca de lugar a que já estava). Fica gravado no pet (``cha_skills``)."""
    snap = s.snapshot
    assert snap is not None
    pet = next((p for p in snap.pets if p.id == msg.petId), None)
    raw = msg.chaSkillIndexs.split(",")
    picks = [int(x) for x in raw if x.strip().lstrip("-").isdigit()]
    skills = len([x for x in pet.change_skills.split(",") if x.strip()]) if pet else 0
    chosen = [i for i in picks if i >= 0]
    if (
        pet is None
        or len(picks) != 3
        or len(raw) != 3
        or any(not -1 <= i < skills for i in picks)
        or len(set(chosen)) < len(chosen)
    ):
        s.log.info("8726 recusado", pet=msg.petId, skills=msg.chaSkillIndexs)
        return
    pet.cha_skills = ",".join(map(str, picks))
    await s.ctx.characters.save(pet)
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
    """Estado do PvP (``TopToolsBar.sendMatch``: no login com nível 22 e ao chegar nele). ``matchState`` é a janela
    aberta (``A.match_open``); o botão só aparece com nível 22 e ela aberta (``TopToolsBar.showPVP``). O login
    turco (login.json #82, nível 56) manda 4201 falso; o inglês (tutorial_en #24-#136, nível 1) não manda nenhum."""
    s.match_open = A.match_open(s.ctx.world.settings, s.ctx.clock.now())
    s.send(S_MATCH, b.complete(pb.MatchStateMsg(matchState=s.match_open)))


def push_match(s: GameSession) -> None:
    """No relógio (20008): o 4201 vai sozinho a todos quando a janela abre ou fecha (oficial_20261023-153200-1
    #2231, nível 12). O primeiro tique só guarda o estado."""
    now_open = A.match_open(s.ctx.world.settings, s.ctx.clock.now())
    if s.match_open is not None and now_open != s.match_open:
        s.send(S_MATCH, b.complete(pb.MatchStateMsg(matchState=now_open)))
    s.match_open = now_open
