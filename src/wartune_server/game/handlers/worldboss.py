"""Chefe do mundo: agenda (8271 -> 4182), entrada (8258), reviver pago (8264), buff (8470) e info (8259).

Regras e fontes em ``docs/boss-eventos.md``. O mapa do chefe (5001/5003) tem um nó só, montado da config no
banco (``world_bosses``); a vida compartilhada está em ``game/boss_fight.py``.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import structlog

from ...domain.models import Mail, MailType
from ...domain.repositories import UnitOfWork
from ...domain.world import WorldBoss
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates
from .. import boss_fight, space, worldboss
from .. import mail as mailbox
from .. import outer_city as oc
from ..arena import config as arena_config
from ..arena import npc_hero
from ..battle import Battle, SharedHp
from ..builders import login as b
from ..campaign import NORMAL, CampaignMap
from ..router import router
from ..session import GameContext, GameSession
from .campaign import ARMY_FIGHTING, ARMY_IDLE, CAMPAIGN_SCENE, map_sync, player_hero
from .login import army, player_info
from .player import alert

S_BOSS_STATE, S_BOSS_INFO, S_MILESTONES = 4182, 4174, 4369
S_PLAYER, S_ROOM_ENTER, S_EXIT, S_ROOM_CREATED, S_NODES, S_FOG = 3, 21, 22, 125, 127, 130
S_MAP_SYNC, S_FULL_ARMY, S_REPORT = 140, 150, 4103
ROOM_ENTER = 1  # RoomCreatedMsg.createdType
BOSS_NODE, BOSS_MASTER = 1, 41  # nodeId do único nó; masterType do chefe (como o 102109 da masmorra)
BOSS_LIVING, BATTLE_TYPE = 4, 17  # o chefe na luta (como o da masmorra); battleType do chefe do mundo (cliente)
TILE = 20
NO_MAP = "This World Boss has no battle map yet."
NOT_OPEN = "World Boss is not open now."
NO_DIAMONDS = "Not enough Diamonds."
REVIVE_COST = 3  # sem a linha no template; ConfigInfos Live_Fight_Pay é 15 nos templates EN
S_PLAYER_STATE, S_BOSS_REPORT = 4175, 4203
REPORT_TYPE = 1  # WorldBossReportMsg.type: o popup do fim (WorldBossManager)
DEFEATED = "World Boss has been defeated."
MAIL_TITLE = "World Boss"
GOLD, DARU = -100, -300  # anexos de moeda (rewards.CURRENCIES)
MAIL_TEXT = "World Boss rewards: {gold:,} Gold and {daru:,} Daru."  # (dedução) o cliente não tem o texto
CLOSE_EVERY = timedelta(seconds=60)
log = structlog.get_logger(__name__)
UNAVAILABLE = "This action is not available now."  # reviver e buff: o cliente só pede dentro do mapa do chefe


@router.on(8535)
async def cancel_transport(s: GameSession, _: object) -> None:
    """Cancela o transporte do jogador morto no mapa de PvP do chefe (ExtraBufferItem, tipo 5). Esse estado de
    morte vem do mapa da batalha compartilhada, que não existe aqui: nada para cancelar, e o cliente não espera
    resposta. Só registramos."""
    s.log.info("8535 sem transporte de morte: não há mapa de PvP do chefe")


@router.on(8271)
async def boss_state(s: GameSession, _: object) -> None:
    """Agenda de hoje dos dois chefes. O cliente pede isso uma vez, no login (``WorldBossManager.setup``)."""
    templates, now = s.ctx.templates, s.ctx.clock.now()
    defeated = s.ctx.bosses.defeated(templates, now)
    s.boss_states = worldboss.states(templates, now, defeated)
    s.send(S_BOSS_STATE, worldboss.states_msg(templates, now, defeated))


def push_states(s: GameSession) -> None:
    """No relógio (20008): manda o 4182 de novo quando um chefe abre ou fecha. O 8258 só passa no cliente com
    ``worldbossState`` ligado, e só o 4182 com ``state`` 0 liga (``WorldBossManager``)."""
    if s.boss_states is None:
        return  # o cliente ainda não pediu (8271)
    templates, now = s.ctx.templates, s.ctx.clock.now()
    defeated = s.ctx.bosses.defeated(templates, now)
    if (states := worldboss.states(templates, now, defeated)) != s.boss_states:
        s.boss_states = states
        s.send(S_BOSS_STATE, worldboss.states_msg(templates, now, defeated))


@router.on(8259)
async def boss_info(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Info por mapa: ``reqWorldBossCmd`` não tem chamador no cliente, então não há o que responder."""
    s.log.info("pedido de info do chefe ignorado", pedido=str(msg))


@router.on(8258)
async def enter_boss(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Entrar no chefe (``param1`` = campanha): 125, 4369, 21, 127, 130 e 4174.

    (cliente) o 4369 tem de chegar antes da view do mapa, senão o quadro dos degraus não aparece; o mapa é a
    própria campanha (``MapInfos`` 5001/5003, 1600x1700) e ``checkFogMap`` ignora a névoa nele, mas o 130 abre a
    view. Os outros jogadores do mapa recebem o 21 de quem entrou (``CampaignManager.readMember`` soma um a um).
    """
    if (why := _refusal(s, msg.param1)) is not None:
        alert(s, why)
        return
    ctx = s.ctx
    pool = await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, msg.param1, ctx.clock.now())
    if pool is None:
        alert(s, NO_MAP if msg.param1 not in ctx.world.world_bosses else NOT_OPEN)
        return
    if not pool.alive:
        alert(s, DEFEATED)
        return
    if s.battle is not None or s.campaign is not None:
        return  # entrou em outro lugar durante o await
    snap = s.snapshot
    assert snap is not None
    boss = pool.boss
    node = boss_node(ctx.templates, boss)
    s.campaign = CampaignMap(boss.campaign_id, {node["campDataId"]: node}, (boss.start_x, boss.start_y),
                             world_boss=True)  # fmt: skip
    space.leave(s)
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER)
    room.room.campaignId = boss.campaign_id
    s.send(S_ROOM_CREATED, room)
    s.send(S_MILESTONES, boss_fight.milestones(ctx.world, pool, s.player_id))
    me = space.room_player(snap, ctx.templates, s.campaign.pos, boss.campaign_id)
    others = on_map(s, boss.campaign_id)
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, boss.campaign_id)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    for other in others:
        other.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    s.send(S_NODES, s.campaign.node_list())
    s.send(S_FOG, s.campaign.fog())
    s.send(S_BOSS_INFO, pool.info(ctx.templates, s.player_id, ctx.clock.now()))
    if pool.is_dead(s.player_id, ctx.clock.now()):  # saiu morto e voltou: a contagem continua
        s.send(S_PLAYER_STATE, _state_msg(s, pool, s.player_id))


def boss_node(templates: GameTemplates, boss: WorldBoss) -> dict[str, Any]:
    """O nó do chefe no 127, no molde do chefe da masmorra (102109, ``dungeon_1001.json``): masterType 41,
    ``heroTempId`` do ``GameHeroTemp`` (o cliente monta o herói por ele) e o avatar em ``swf/npc/<sonType>``."""
    hero = templates.get("GameHeroTemp", boss.hero_id) or {}
    x, y = boss.node_x, boss.node_y
    return {
        "nodeId": BOSS_NODE, "campDataId": boss.campaign_id * 100 + 1, "nodeName": hero.get("TemplateName", ""),
        "masterType": BOSS_MASTER, "sonType": boss.son_type, "preNodeIds": "0", "nextNodeIds": "", "state": NORMAL,
        "refreshSpeed": 1, "posX": x, "posY": y, "curX": x, "curY": y, "level": int(hero.get("Grades") or 0),
        "styleType": 1, "attackTypes": 0, "nameColor": 5, "sizeType": 1, "toward": 180, "resource": 1,
        "resetX": 0, "resetY": 0, "fixX": x * TILE, "fixY": y * TILE, "heroTempId": boss.hero_id,
        "handlerRange": 0, "fightCapaity": 0, "param1": 0, "param2": 0, "param3": "", "param4": "", "param5": "",
    }  # fmt: skip


def players_on(ctx: GameContext, campaign_id: int) -> list[GameSession]:
    """Os jogadores no mapa do chefe ``campaign_id``."""
    return [o for o in ctx.online.sessions()
            if o.campaign is not None and o.campaign.world_boss and o.campaign.map_id == campaign_id
            and o.snapshot is not None]  # fmt: skip


def on_map(s: GameSession, campaign_id: int) -> list[GameSession]:
    """Os outros jogadores no mapa do chefe ``campaign_id``."""
    return [o for o in players_on(s.ctx, campaign_id) if o is not s]


def leave_boss(s: GameSession) -> bool:
    """Sai do mapa do chefe (5025 ou desconexão): 22 para todos no mapa, o próprio também (o cliente volta com
    ``exitBack``; os outros tiram o exército, ``CampaignSocketManger.__campaignExitHandler``)."""
    c, snap = s.campaign, s.snapshot
    if c is None or not c.world_boss or snap is None:
        return False
    if s.battle is not None:
        s.battle.cancel()
        s.battle = None
    msg = pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id, serverName=snap.server.name)
    for other in on_map(s, c.map_id):
        other.send(S_EXIT, msg)
    s.campaign = None
    s.send(S_EXIT, msg)
    return True


def battle_spec(s: GameSession, pool: boss_fight.Pool) -> dict[str, Any]:
    """Luta com o chefe: battleType 17, o chefe é herói ``type`` 3 com a vida que resta na janela (``maxHp`` = a
    cheia), as tropas e o herói do jogador como na masmorra; o ``killTurn``-ésimo golpe do chefe mata o lado do
    jogador inteiro (internet: o 6º golpe mata), antes disso ele não morre ("HP e tropas não se esgotam")."""
    snap = s.snapshot
    assert snap is not None
    boss, templates = pool.boss, s.ctx.templates
    hero = templates.get("GameHeroTemp", boss.hero_id) or {}
    soldiers, pawn_tpl = oc.army_soldiers(snap, templates)
    hp = pool.hp
    enemy = npc_hero(livingId=BOSS_LIVING, side=2, pos=5, type=3, tempId=boss.hero_id,
                     nickName=hero.get("TemplateName", ""), grade=int(hero.get("Grades") or 0),
                     maxHp=pool.fight.total_hp, initHp=hp, hp=hp, captain=int(hero.get("Captain") or 0),
                     res=hero.get("ResPath", ""), castTime=4000)  # fmt: skip
    return {
        "battleType": BATTLE_TYPE, "mapTempId": boss.campaign_id, "attackModel": 2, "battleScene": CAMPAIGN_SCENE,
        "soldiers": soldiers, "heroes": [enemy], "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
        "killTurn": boss.kill_turn,
    }  # fmt: skip


async def boss_attack(s: GameSession) -> None:
    """5125 no nó do chefe: luta contra a vida compartilhada (``SharedHp``). O nó não muda de estado: todos
    batem nele ao mesmo tempo."""
    ctx, snap, c = s.ctx, s.snapshot, s.campaign
    assert snap is not None and c is not None
    pool = await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, c.map_id, ctx.clock.now())
    if pool is None or not pool.alive or s.battle is not None or s.campaign is not c or c.fighting:
        return
    if pool.is_dead(s.player_id, ctx.clock.now()):
        s.send(S_PLAYER_STATE, _state_msg(s, pool, s.player_id))  # o cliente volta a mostrar a contagem
        return
    ch = snap.character
    cid, nick, job = s.player_id, ch.nickname or "", ch.job
    link = SharedHp(BOSS_LIVING, lambda: pool.hp, lambda v: pool.hit(cid, nick, job, v, ctx.clock.now()),
                    bonus=pool.inspire() * boss_fight.INSPIRE_BONUS)  # fmt: skip
    spec = battle_spec(s, pool)
    c.fighting = BOSS_NODE
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))

    async def finished(battle: Battle, won: bool) -> None:
        await _boss_over(s, battle, won, pool, link)

    s.battle = Battle(spec, player_hero(s, spec), ctx.templates, ctx.clock, s.send, finished, shared=link)
    s.log.info("batalha com o chefe do mundo", chefe=c.map_id, vida=pool.hp, battle=s.battle.id)
    s.battle.start()


async def _boss_over(s: GameSession, battle: Battle, won: bool, pool: boss_fight.Pool, link: SharedHp) -> None:
    """Fim da luta: ouro e daru pelo dano desta luta (``battle_reward``), gravados com o dano acumulado da
    janela; 3, 4103, 150 e 140; o 4174 novo vai a todos no mapa."""
    snap = s.snapshot
    assert snap is not None
    s.battle, s.hero_sp = None, battle.player_sp
    if s.campaign is not None:
        s.campaign.fighting = 0
    ch = snap.character
    reward = pool.battle_reward(link.dealt)
    ch.gold += reward
    ch.strategy += reward  # daru = "strategy" (como o strategyBonus da masmorra)
    rows: list[object] = [ch]
    if (wound := pool.wounds.get(s.player_id)) is not None:
        rows.append(wound)
    if pool.fight.killer_id == s.player_id:
        rows.append(pool.fight)
    async with pool.lock:
        await s.ctx.characters.save(*rows)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    report = pb.BattleReportMsg(battleResult=1 if won else 2, strategyBonus=reward, gpBonus=0,
                                battleScene=CAMPAIGN_SCENE)  # fmt: skip
    report.failCount, report.goldBonus, report.petGpBonus = 0, reward, 0
    s.send(S_REPORT, report)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    broadcast_info(s, pool)
    if not pool.alive:
        await settle(s.ctx, pool)  # o último golpe (ou a janela fechou durante a luta)
        if s.campaign is not None and s.campaign.world_boss:  # o settle só tira quem estava fora de luta
            _report_and_kick(s, pool)
    elif not won:
        _kill(s, pool)


async def settle(ctx: GameContext, pool: boss_fight.Pool) -> None:
    """Fim da janela (chefe morto ou ``StopTime``), uma vez só: os prêmios do fim pelo correio (top 10 da classe,
    degrau da fração do dano, último golpe; ``end_rewards``), a vida da próxima janela (``next_hp``) e o dano de
    todos, numa transação. Quem está no mapa e fora de luta recebe o 4203 e sai (22); quem está em luta, no fim
    dela (``_boss_over``)."""
    now = ctx.clock.now()
    async with pool.lock:
        if pool.fight.settled:
            return
        pool.fight.settled = True
        pool.fight.next_hp = boss_fight.next_hp(pool.boss, pool.fight)
        prizes = {cid: p for cid, p in boss_fight.end_rewards(ctx.world, pool).items() if any(p)}
        mails = {cid: Mail(cid, now, MAIL_TITLE, MAIL_TEXT.format(gold=g, daru=d), mail_type=MailType.SYSTEM,
                           send_type=mailbox.SYSTEM_SENDER) for cid, (g, d) in prizes.items()}  # fmt: skip

        async def change(uow: UnitOfWork) -> None:
            await uow.save(pool.fight)
            for wound in pool.wounds.values():
                await uow.save(wound)
            for cid, mail in mails.items():
                gold, daru = prizes[cid]
                await mailbox.stage(uow, mail, [(t, n) for t, n in ((GOLD, gold), (DARU, daru)) if n])

        await ctx.characters.write(change)
    log.info("chefe do mundo encerrado", chefe=pool.boss.campaign_id, vida=pool.hp, killer=pool.fight.killer_id,
             proxima=pool.fight.next_hp, premiados=len(mails))  # fmt: skip
    for mail in mails.values():
        mailbox.notify(ctx.online, mail)
    for timer in pool.timers.values():
        timer.cancel()
    pool.timers.clear()
    pool.dead.clear()
    for o in players_on(ctx, pool.boss.campaign_id):
        if o.battle is None:
            _report_and_kick(o, pool)


def _report_and_kick(s: GameSession, pool: boss_fight.Pool) -> None:
    """4203 (posição, ouro e daru do fim, o dano total) e 22: o chefe acabou para este jogador."""
    ranking = [w.character_id for w in pool.ranking()]
    gold, daru = boss_fight.end_rewards(s.ctx.world, pool).get(s.player_id, (0, 0))
    mine = pool.wounds.get(s.player_id)
    s.send(S_BOSS_REPORT, pb.WorldBossReportMsg(
        campaignId=pool.boss.campaign_id, order=ranking.index(s.player_id) + 1 if s.player_id in ranking else 0,
        gold=gold, strengy=daru, totalWound=mine.wound if mine else 0, type=REPORT_TYPE))  # fmt: skip
    leave_boss(s)


async def close_windows(s: GameSession) -> None:
    """No relógio (20008), no máximo uma vez por minuto no servidor: paga as janelas que passaram do
    ``StopTime``, as da memória e as que ficaram no banco sem fim pago (o servidor caiu no meio)."""
    ctx, now = s.ctx, s.ctx.clock.now()
    bosses = ctx.bosses
    if bosses.checked_at is not None and now - bosses.checked_at < CLOSE_EVERY:
        return
    bosses.checked_at = now
    pools = [p for p in bosses.pools.values() if not p.fight.settled]
    for pool in pools + await bosses.stale(ctx.world, ctx.characters):
        row = worldboss.boss(ctx.templates, pool.boss.campaign_id)
        if row is not None and now >= worldboss.window(row, pool.fight.opened_at)[1]:
            await settle(ctx, pool)


def _state_msg(s: GameSession, pool: boss_fight.Pool, character_id: int) -> pb.PlayerStateListMsg:
    """4175: morto (1) com o tempo até reviver em ms, ou vivo (0)."""
    until, now = pool.dead.get(character_id), s.ctx.clock.now()
    left = int((until - now).total_seconds() * 1000) if until is not None and now < until else 0
    server = s.snapshot.server.name if s.snapshot is not None else ""
    msg = pb.PlayerStateListMsg()
    msg.playerState.add(armyId=character_id, state=int(left > 0), leftTime=left, serverName=server)
    return msg


def _send_state(s: GameSession, pool: boss_fight.Pool) -> None:
    msg = _state_msg(s, pool, s.player_id)
    for o in [s, *on_map(s, pool.boss.campaign_id)]:
        o.send(S_PLAYER_STATE, msg)


def _kill(s: GameSession, pool: boss_fight.Pool) -> None:
    """Perdeu a luta (o ``killTurn``): morto por ``revive_seconds`` (internet: 30 s), depois revive sozinho."""
    cid = s.player_id
    pool.dead[cid] = s.ctx.clock.now() + timedelta(seconds=pool.boss.revive_seconds)
    if (old := pool.timers.pop(cid, None)) is not None:
        old.cancel()
    pool.timers[cid] = asyncio.get_running_loop().call_later(pool.boss.revive_seconds, revive, s, pool)
    _send_state(s, pool)


def revive(s: GameSession, pool: boss_fight.Pool) -> None:
    pool.dead.pop(s.player_id, None)
    if (timer := pool.timers.pop(s.player_id, None)) is not None:
        timer.cancel()
    if s.campaign is not None and s.campaign.world_boss and not s.gone.is_set():
        _send_state(s, pool)


def broadcast_info(s: GameSession, pool: boss_fight.Pool) -> None:
    """O 4174 de cada um (o ``myWound`` muda) a todos no mapa do chefe."""
    now = s.ctx.clock.now()
    for o in [s, *on_map(s, pool.boss.campaign_id)]:
        if o.campaign is not None and o.campaign.world_boss:
            o.send(S_BOSS_INFO, pool.info(o.ctx.templates, o.player_id, now))


def _refusal(s: GameSession, campaign_id: int) -> str | None:
    row = worldboss.boss(s.ctx.templates, campaign_id)
    if row is None:
        if next(s.ctx.templates.find("Campaigns", CampaignId=campaign_id), None) is not None:
            return UNAVAILABLE  # (cliente) TaskFrameII.as:707-708: o botão ir manda 8258 com a campanha 6001 (Types 2)
        return "Invalid World Boss."
    snap = s.snapshot
    assert snap is not None
    if worldboss.state(row, s.ctx.clock.now()) != worldboss.OPEN:
        return NOT_OPEN
    if snap.character.grades < int(row["MinLevel"]):
        return f"World Boss requires level {row['MinLevel']}."
    if s.battle is not None or s.campaign is not None:
        return "Finish your current battle or map first."
    return None


@router.on(8264)
async def revive_or_fight(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Reviver já e voltar à luta, pagando (``Live_Fight_Pay``, 15 nos templates EN; payType 0 = vinculado
    primeiro, 1 = só diamante). O botão existe na ``RiverView`` tipo 1, depois de morrer no chefe. ``Live_Pay``
    (2) não tem botão no chefe. Fora do mapa do chefe ou vivo: aviso, nada cobrado.

    ponytail: o mesmo 8264 é o reviver do altar de guilda (``RiverView`` tipo 2, paga em contribuição);
    quem fizer o mapa do altar tem de separar pelo mapa do jogador.
    """
    ctx, c, snap = s.ctx, s.campaign, s.snapshot
    pool = ctx.bosses.pools.get(c.map_id) if c is not None and c.world_boss else None
    if pool is None or snap is None or not pool.is_dead(s.player_id, ctx.clock.now()):
        s.log.info("reviver pago recusado (não está morto no chefe)", pedido=str(msg))
        alert(s, UNAVAILABLE)
        return
    cost = arena_config(ctx.templates, "Live_Fight_Pay", REVIVE_COST)
    entry = ledger.pay(snap.character, cost, bind=msg.payType == 0, reason="world_boss_revive",
                       ref=str(c.map_id), now=ctx.clock.now())  # type: ignore[union-attr]  # fmt: skip
    if entry is None:
        alert(s, NO_DIAMONDS)
        return
    revive(s, pool)  # antes do await: um segundo 8264 já vê vivo
    await ctx.characters.save(snap.character, entry)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(8470)
async def buy_buff(s: GameSession, msg: pb.WorldBossBufferMsg) -> None:
    """Buff do chefe (``CampaignBufferTemps`` ``Types=4``, ``WorldBossBuyBuffModel.BUFFER_TYPE``): só se compra
    dentro do mapa do chefe. Nada é cobrado."""
    s.log.info("buff do chefe recusado (sem mapa do chefe)", pedido=str(msg))
    alert(s, UNAVAILABLE)
