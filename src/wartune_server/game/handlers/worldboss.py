"""Chefe do mundo: agenda (8271 -> 4182), avisos e nascimento no relógio, entrada (8258), luta, reviver pago (8264),
buff (8470) e info (8259).

Regras e fontes em ``docs/boss-eventos.md``. O mapa do chefe (5001/5003) tem 4 nós (entrada, chefe, portal e a
barreira que some quando ele nasce), montados da config no banco (``world_bosses``); a vida compartilhada está em
``game/boss_fight.py``. (visto) a luta inteira: oficial_20261027-152321-1 #1355-#3265 (5001) e
oficial_20261026-225632-1 #7393-#10900 (5003).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog

from ...domain.models import Mail, MailType
from ...domain.repositories import UnitOfWork
from ...domain.world import WorldBoss
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import Row
from .. import boss_fight, rules, space, titles, worldboss
from .. import events as ev
from .. import mail as mailbox
from .. import outer_city as oc
from ..announcements import LATE
from ..arena import config as arena_config
from ..arena import npc_hero
from ..battle import Battle, SharedHp
from ..builders import login as b
from ..builders.player import quest_update
from ..campaign import NORMAL, CampaignMap
from ..router import router
from ..session import GameContext, GameSession
from . import lottery
from .campaign import ARMY_FIGHTING, ARMY_IDLE, CAMPAIGN_SCENE, enter_quarry, map_sync, player_hero
from .hangup import enter_room
from .login import army, player_info
from .player import alert, balens_changed

S_BOSS_STATE, S_BOSS_INFO, S_LEFT_TIME, S_TIME_JUDGE, S_LOADED = 4182, 4174, 4381, 4371, 4413
S_PLAYER, S_ROOM_ENTER, S_EXIT, S_ROOM_CREATED, S_NODES, S_NODE = 3, 21, 22, 125, 127, 128
S_MAP_SYNC, S_FULL_ARMY, S_REPORT, S_BUFF, S_STAND, S_ALERT, S_CHAT = 140, 150, 4103, 4165, 4126, 111, 83
ROOM_ENTER = 1  # RoomCreatedMsg.createdType
# os 4 nós (visto #1399): campDataId = campanha * 100 + n
ENTRY, BOSS_NODE, PORTAL, GATE = 1, 2, 3, 4
GONE = 8  # nodeState do 128: a barreira no nascimento (#1669), o chefe na morte (#3219)
BOSS_LIVING, BATTLE_TYPE = 4, 17  # o chefe na luta (como o da masmorra); battleType do chefe do mundo (cliente)
TILE = 20
INSPIRE_BUFF = 700  # CampaignBufferTemps 701-720: a moral de grau N é o buff 700 + N (visto #1867, #2083)
INFO_EVERY = 8  # segundos entre os 4174 (visto #1415, #1420, #1430: ~8 s)
NO_MAP = "This World Boss has no battle map yet."
NOT_STARTED = "The current battle hasn't started yet."
NO_DIAMONDS = "You don't have enough Balens!"  # language EN Auction.ResultAlert11
REVIVE_COST = 3  # sem a linha no template; ConfigInfos Live_Fight_Pay é 15 nos templates EN
S_PLAYER_STATE, S_BOSS_REPORT = 4175, 4203
REPORT_TYPE = 1  # WorldBossReportMsg.type: o popup do fim (WorldBossManager)
DEFEATED = "World Boss has been defeated."
# textos (visto, 5001 e 5003)
OPEN_TEXT = "The World Boss battle is now open, enter to participate in the battle!"  # #8248
COUNTDOWN_TEXT = "World Boss {name} will appear in {n} minutes! Get ready for the battle of a lifetime!"  # #1438
SPAWN_TEXT = "World Boss {name} has spawned!"  # #1670
INSPIRE_TEXT = "{link} has dealt {k}k in total damage! All players have been granted lvl. {grade} Inspiration!" + (
    "\t" * 6 + " "
)  # #1870, com os tabs do oficial
LAST_HIT_TEXT = "{link} struck the final blow to defeat the World Boss {name} and has been rewarded with {gold:,} Gold!"
TOP_TEXT = "The top 3 players in terms of total damage dealt to Boss {name} are:{list}"  # #3235
CLASS_TOP_TEXT = "{cls}The top 3 players to deal the most damage to the BOSS are:{list}"  # #3236-#3239
TOP = 3
# correios do fim (visto #3260: sendType 4, Daru no anexo 1 e ouro no 2)
BOSS_SENDER = 4
GOLD, DARU = -100, -300  # anexos de moeda (rewards.CURRENCIES)
MAILS = {
    "apollo": ("World Boss Award: Apollo Prize",
               "You received {cls} damage in battle! Your stunning performance has earned you {rank} and bonus "
               "rewards!"),
    "warrior": ("World Boss Award: Warrior Prize",
                "Your stellar performance in the World Boss battle has earned you a bonus reward!"),
    # só se quem deu o golpe saiu antes do fim pago (o normal é direto, ``settle``); TODO(inventado): o texto
    "lucky": ("World Boss Award: Lucky Prize",
              "You struck the final blow to defeat the World Boss! Here is your bonus reward!"),
}  # fmt: skip
CLOSE_EVERY = timedelta(seconds=60)
log = structlog.get_logger(__name__)
UNAVAILABLE = "This action is not available now."  # reviver e buff: o cliente só pede dentro do mapa do chefe
S_QUESTS = 112
S_GUILDWAR, S_LOTTERY, S_UNKNOWN_462, S_CROSS_ICON, S_CROSS_STATE, S_CROSS_FIRST = 4451, 4637, 462, 4741, 4683, 4685
QUEST_JOIN, QUEST_INSTANT, QUEST_DAMAGE = 40, 66, 41  # QuestCondictionInfos: lutar, luta paga (8264), dano total


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
    # (visto) 215937 #118-#128 e tutorial_en, logo depois do 4182: guerra de guilda (4451) fechada, loteria (4637)
    # fechada, o 462 que o cliente não escuta (corpo 38 00, igual em todas as capturas) e a guilda entre servidores
    # (4741 ícone 0, 4683 fechada, 4685 vazio): nenhum desses sistemas existe aqui
    s.send(S_GUILDWAR, pb.GuildMsg(param5=False))
    s.send(S_LOTTERY, lottery.state_msg(s))  # aberta só com game_settings.lottery
    s.send(S_UNKNOWN_462, pb.SimplePropertyMsg(param7=False))
    s.send(S_CROSS_ICON, pb.SimplePropertyMsg(param1=0))
    s.send(S_CROSS_STATE, pb.GuildMsg(param5=False))
    s.send(S_CROSS_FIRST)


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


def _online(ctx: GameContext) -> list[GameSession]:
    return [o for o in ctx.online.sessions() if o.snapshot is not None]


def _chat(text: str, channel: int = 12, *, tip: bool = False, job: int = 0) -> pb.ChatChannelMsg:
    """83 do sistema (visto #1670: ``otherId`` -1, ``userType`` 1; os de destaque com ``isCenterTip``/``isBigTip``)."""
    return pb.ChatChannelMsg(channel=channel, encodeMsg=text, otherId=-1, userType=1, isCenterTip=tip, isBigTip=tip,
                             job=job)  # fmt: skip


def _say_map(ctx: GameContext, campaign_id: int, text: str) -> None:
    """111 no meio da tela e 83 canal 3 para quem está no mapa do chefe (visto #1438/#1439, #1870/#1871)."""
    for o in players_on(ctx, campaign_id):
        o.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        o.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


async def boss_clock(s: GameSession) -> None:
    """No relógio (20008), uma vez por servidor: os avisos de cada chefe (4381 com os minutos, o mapa aberto, a
    contagem "will appear") e o nascimento (128 da barreira e o 83). Marco perdido há mais de ``LATE`` não sai.

    (dedução) o 4381 e os 83 de canal 12 vão a todos os online (chegaram fora do mapa, #583); a contagem (111 e 83
    canal 3) só a quem está no mapa (só foi vista lá dentro).
    """
    ctx, now = s.ctx, s.ctx.clock.now()
    bosses = ctx.bosses
    since = max(bosses.told_at or now - LATE, now - LATE)
    bosses.told_at = now
    if since >= now:
        return
    defeated = bosses.defeated(ctx.templates, now)
    for row in worldboss.bosses(ctx.templates):
        cid = int(row["CampaignId"])
        boss = ctx.world.world_bosses.get(cid)
        if boss is None or cid in defeated:
            continue
        name = row["CampaignName"]
        for kind, n in worldboss.events(row, since, now):
            if kind == "notice":
                for o in _online(ctx):
                    o.send(S_LEFT_TIME, pb.WorldBossInfoLoadMsg(campaignId=cid, leftTime=n))
                    if n == worldboss.OPEN_NOTICE:
                        push_states(o)
                        o.send(S_CHAT, _chat(OPEN_TEXT, tip=True))
            elif kind == "countdown":
                _say_map(ctx, cid, COUNTDOWN_TEXT.format(name=name, n=n))
            else:
                for o in players_on(ctx, cid):
                    o.campaign.nodes[_camp(cid, GATE)]["state"] = GONE  # type: ignore[union-attr]
                    o.send(S_NODE, pb.CampaignNodeUpdateMsg(nodeId=GATE, nodeState=GONE, param1=0))
                for o in _online(ctx):
                    o.send(S_CHAT, _chat(SPAWN_TEXT.format(name=name), tip=True))


@router.on(8259)
async def boss_info(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Info por mapa: ``reqWorldBossCmd`` não tem chamador no cliente, então não há o que responder."""
    s.log.info("pedido de info do chefe ignorado", pedido=str(msg))


@router.on(8258)
async def enter_boss(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Entrar no chefe (``param1`` = campanha): 125, 140, 21, 127, 4165 e 150 (visto #1396-#1404, #8268-#8274).

    Os outros jogadores do mapa recebem o 21 de quem entrou (``CampaignManager.readMember`` soma um a um). O 4174
    vem no tique de 8 s (``_tick``). (visto) #1386: 8258 de um chefe fechado não tem resposta.
    """
    if await enter_quarry(s, msg.param1):  # 6001: o botão "ir" da missão 102 usa o mesmo 8258
        return
    if await enter_room(s, msg.param1):  # 7001-7009: Rest House (HookFrame)
        return
    row = worldboss.boss(s.ctx.templates, msg.param1)
    if row is not None and worldboss.state(row, s.ctx.clock.now()) != worldboss.OPEN:
        s.log.info("8258 com o chefe fechado (o oficial não responde)", chefe=msg.param1)
        return
    if (why := _refusal(s, msg.param1)) is not None:
        alert(s, why)
        return
    ctx = s.ctx
    pool = await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, msg.param1, ctx.clock.now())
    if pool is None:
        alert(s, NO_MAP)
        return
    if not pool.alive:
        alert(s, DEFEATED)
        return
    if s.battle is not None or s.campaign is not None:
        return  # entrou em outro lugar durante o await
    snap = s.snapshot
    assert snap is not None
    boss, now = pool.boss, ctx.clock.now()
    assert row is not None
    s.campaign = CampaignMap(boss.campaign_id, boss_nodes(row, boss, worldboss.spawned(row, now)),
                             (boss.start_x, boss.start_y), world_boss=True)  # fmt: skip
    space.leave(s)
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER)
    room.room.campaignId = boss.campaign_id
    s.send(S_ROOM_CREATED, room)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    me = space.room_player(snap, ctx.templates, s.campaign.pos, boss.campaign_id, now)
    others = on_map(s, boss.campaign_id)
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, boss.campaign_id, now)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    for other in others:
        other.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    s.send(S_NODES, s.campaign.node_list())
    s.send(S_BUFF, _buff_msg(s, pool))
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    if pool.is_dead(s.player_id, now):  # saiu morto e voltou: a contagem continua
        s.send(S_PLAYER_STATE, _state_msg(s, pool, s.player_id))
    if pool.ticker is None or pool.ticker.done():
        pool.ticker = asyncio.get_running_loop().create_task(_tick(ctx, pool))


async def scene_loaded(s: GameSession) -> None:
    """O primeiro 5035 ``state`` 4 no mapa do chefe (os da volta das lutas não respondem: visto #1406-#3243): 4371
    (``syncErrorTime``, a diferença do relógio do cliente em segundos; o nosso cliente usa o relógio do servidor,
    então 0) e 4413 com o contador do dia do chefe no painel de atividades (visto #1407: keys "5001", keyData 1)."""
    from . import events  # events importa login, que importa a campanha

    c, snap = s.campaign, s.snapshot
    if c is None or snap is None or c.ready:
        return
    c.ready = True
    s.send(S_TIME_JUDGE, pb.TimeJudgeMsg(isAdd=True, secondCount=0))
    clicked = ev.click(snap, str(c.map_id), s.ctx.clock.now())
    await s.ctx.characters.save(clicked)
    s.send(S_LOADED, pb.ClickDatasRspMsg(info=[events.click_info(clicked)]))


async def _tick(ctx: GameContext, pool: boss_fight.Pool) -> None:
    """O 4174 a cada ``INFO_EVERY`` para quem está no mapa, até a janela acabar ou o mapa esvaziar."""
    while not pool.fight.settled and players_on(ctx, pool.boss.campaign_id):
        await asyncio.sleep(INFO_EVERY)
        broadcast_info(ctx, pool)


def _camp(campaign_id: int, n: int) -> int:
    return campaign_id * 100 + n


def boss_nodes(row: Row, boss: WorldBoss, spawned: bool) -> dict[int, dict[str, Any]]:
    """Os 4 nós do 127 (visto #1399, #8271): entrada (masterType 40, estado 2), o chefe (42, ``heroTempId`` do
    herói, o cliente monta o desenho por ``sonType``), o portal (61) e a barreira (53, some no nascimento)."""

    def node(n: int, master: int, son: int, x: int, y: int, **extra: Any) -> dict[str, Any]:
        return {
            "nodeId": n, "campDataId": _camp(boss.campaign_id, n), "nodeName": "", "masterType": master,
            "sonType": son, "preNodeIds": "0", "nextNodeIds": "", "state": NORMAL, "refreshSpeed": 1, "posX": x,
            "posY": y, "curX": x, "curY": y, "level": 0, "styleType": 1, "attackTypes": 0, "nameColor": 0,
            "sizeType": 0, "toward": 0, "resource": 2, "resetX": 0, "resetY": 0, "fixX": x * TILE + 9,
            "fixY": y * TILE + 9, "heroTempId": -1, "handlerRange": 0, "fightCapaity": 0, "param1": 0, "param2": 0,
            "param3": "", "param4": "", "param5": "", **extra,
        }  # fmt: skip

    nodes = [
        node(ENTRY, 40, 2301, boss.start_x, boss.start_y, state=2, sizeType=1),
        node(BOSS_NODE, 42, boss.son_type, boss.node_x, boss.node_y, nodeName=row["CampaignName"], nameColor=5,
             sizeType=2, resource=1, heroTempId=boss.hero_id, handlerRange=6, fightCapaity=boss.fight_capacity),
        node(PORTAL, 61, 2336, boss.portal_x, boss.portal_y),
        node(GATE, 53, 2376, boss.gate_x, boss.gate_y, resetX=boss.gate_back_x, resetY=boss.gate_back_y,
             state=GONE if spawned else NORMAL),
    ]  # fmt: skip
    return {n["campDataId"]: n for n in nodes}


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
    pool = s.ctx.bosses.pools.get(c.map_id)
    if pool is not None and pool.ticker is not None and not players_on(s.ctx, c.map_id):
        pool.ticker.cancel()
        pool.ticker = None
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
        "killTurn": boss.kill_turn, "undying": True,
    }  # fmt: skip


async def boss_attack(s: GameSession, node: dict[str, Any]) -> None:
    """5125 num nó do mapa do chefe. Antes do nascimento, a barreira e o chefe respondem 111 "hasn't started" e o
    4126 empurra o exército para trás da barreira (visto #1411-#1414). Depois, o chefe é a luta contra a vida
    compartilhada (``SharedHp``); o nó não muda de estado: todos batem nele ao mesmo tempo."""
    ctx, snap, c = s.ctx, s.snapshot, s.campaign
    assert snap is not None and c is not None
    n = node["campDataId"] - c.map_id * 100
    if n not in (BOSS_NODE, GATE):
        s.log.info("5125 num nó do chefe sem ação", no=node["campDataId"])
        return
    pool = await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, c.map_id, ctx.clock.now())
    if pool is None or not pool.alive or s.battle is not None or s.campaign is not c or c.fighting:
        return
    row = worldboss.boss(ctx.templates, c.map_id)
    if row is not None and not worldboss.spawned(row, ctx.clock.now()):
        alert(s, NOT_STARTED)
        c.pos = (pool.boss.gate_back_x, pool.boss.gate_back_y)
        s.send(S_STAND, pb.StandPosMsg(id=s.player_id, posX=pool.boss.gate_back_x, posY=pool.boss.gate_back_y))
        return
    if n != BOSS_NODE:
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

    s.battle = Battle(
        spec, player_hero(s, spec), ctx.templates, ctx.clock, s.send, finished, shared=link, settings=ctx.world.settings
    )
    s.log.info("batalha com o chefe do mundo", chefe=c.map_id, vida=pool.hp, battle=s.battle.id)
    s.battle.start()
    from . import events  # handlers.events importa login, que importa a campanha

    # (dedução) LeedTemp 18 "Fight a World BOSS" já no ataque, como o 10 no castelo-robô (tutorial_en #1649)
    await events.leed_done(s, events.WORLD_BOSS_LEED)


async def _boss_over(s: GameSession, battle: Battle, won: bool, pool: boss_fight.Pool, link: SharedHp) -> None:
    """Fim da luta: ouro e daru pelo dano desta luta (``battle_reward``), gravados com o dano acumulado da
    janela; 3, 4103, 150 e 140; o 4174 novo e a moral nova vão a todos no mapa."""
    snap = s.snapshot
    assert snap is not None
    s.hero_sp = battle.player_sp
    if s.campaign is not None:
        s.campaign.fighting = 0
    ch = snap.character
    reward = pool.battle_reward(link.dealt)
    ch.gold += reward
    ch.strategy += reward  # daru = "strategy" (como o strategyBonus da masmorra)
    # missão tipo 40 "Participate in a World BOSS Battle" (759 x10, 761 x1): uma por luta (dedução: luta, não entrada)
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_JOIN, 0, 1)
    # tipo 41 "Total Damage Dealt" (762: 50000): o dano de cada luta soma
    quests += [q for q in rules.quest_event(snap, s.ctx.templates, QUEST_DAMAGE, 0, link.dealt) if q not in quests]
    rows: list[object] = [ch, *quests]
    if (wound := pool.wounds.get(s.player_id)) is not None:
        rows.append(wound)
    if pool.fight.killer_id == s.player_id:
        rows += [pool.fight, titles.count(snap, titles.BOSS_BLOW, s.ctx.clock.now())]  # título "Mortal Blow"
    async with pool.lock:
        await s.ctx.characters.save(*rows)
    # só agora: durante a gravação o último golpe de outro jogador roda o ``settle``, que tira (4203, 22) quem está
    # fora de luta; sem a luta ainda marcada, este sairia antes do próprio 4103/140
    s.battle = None
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    report = pb.BattleReportMsg(battleResult=1 if won else 2, strategyBonus=reward, gpBonus=0,
                                battleScene=CAMPAIGN_SCENE)  # fmt: skip
    report.failCount, report.goldBonus, report.petGpBonus = 0, reward, 0
    s.send(S_REPORT, report)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    broadcast_info(s.ctx, pool)
    _inspire(s.ctx, pool)
    if not pool.alive:
        await settle(s.ctx, pool)  # o último golpe (ou a janela fechou durante a luta)
        if s.campaign is not None and s.campaign.world_boss:  # o settle só tira quem estava fora de luta
            _report_and_kick(s, pool)
    elif not won:
        _kill(s, pool)


def _link(ctx: GameContext, character_id: int, nickname: str) -> str:
    """Link de jogador no chat, como ``social.player_link`` (visto #1870: ``consortiaId`` é a guilda)."""
    guild = ctx.guilds.of(character_id)
    gid = guild[0].id if guild else 0
    return f'<a t="1" id="{character_id}" name="{nickname}" consortiaId="{gid}" serverName="" grades="0" />'


def _buff_msg(s: GameSession, pool: boss_fight.Pool) -> pb.CampaignBufferMsg:
    """4165: os buffs do exército no mapa do chefe, a moral (701+) quando há (visto #1402 vazio, #1867 com 701)."""
    msg = pb.CampaignBufferMsg(armyId=s.player_id)
    if grade := pool.inspire():
        msg.bufferInfo.add(bufferTempId=INSPIRE_BUFF + grade, leftTime=0)
    return msg


def _inspire(ctx: GameContext, pool: boss_fight.Pool) -> None:
    """A moral subiu (a cada 500 mil do maior dano): 4165 com o buff novo, 111 e 83 para todos no mapa, um por grau
    (visto #1867-#1871)."""
    grade = pool.inspire()
    ranking = pool.ranking()
    while pool.told_inspire < grade and ranking:
        pool.told_inspire += 1
        top = ranking[0]
        k = pool.told_inspire * boss_fight.INSPIRE_STEP // 1000
        text = INSPIRE_TEXT.format(link=_link(ctx, top.character_id, top.nickname), k=k, grade=pool.told_inspire)
        for o in players_on(ctx, pool.boss.campaign_id):
            o.send(S_BUFF, _buff_msg(o, pool))
        _say_map(ctx, pool.boss.campaign_id, text)


def _end_texts(ctx: GameContext, pool: boss_fight.Pool, name: str) -> list[pb.ChatChannelMsg]:
    """Os 83 do fim com o chefe morto (visto #3234-#3239): o último golpe, o top 3 geral e o top 3 de cada classe,
    com a porcentagem do dano total."""
    ranking = pool.ranking()
    total = sum(w.wound for w in ranking) or 1

    def top(rows: list[Any]) -> str:
        return ",".join(f"{_link(ctx, w.character_id, w.nickname)}({w.wound * 100 / total:.2f}%)" for w in rows[:TOP])

    killer = pool.wounds.get(pool.fight.killer_id)
    out = []
    if killer is not None:
        out.append(_chat(LAST_HIT_TEXT.format(link=_link(ctx, killer.character_id, killer.nickname), name=name,
                                              gold=pool.boss.last_hit_gold), tip=True))  # fmt: skip
    out.append(_chat(TOP_TEXT.format(name=name, list=top(ranking))))
    for cls in (1, 2, 0):
        rows = [w for w in ranking if boss_fight.job_class(w.job) == cls]
        if rows:
            out.append(_chat(CLASS_TOP_TEXT.format(cls=boss_fight.CLASS_NAMES[cls], list=top(rows)),
                             job=boss_fight.CLASS_JOB[cls]))  # fmt: skip
    return out


def _prize_mail(prize: boss_fight.Prize, now: datetime) -> Mail:
    title, text = MAILS[prize.kind]
    text = text.format(cls=boss_fight.CLASS_NAMES.get(prize.cls, ""), rank=prize.rank)
    return Mail(prize.character_id, now, title, text, mail_type=MailType.SYSTEM, send_type=BOSS_SENDER)


async def settle(ctx: GameContext, pool: boss_fight.Pool) -> None:
    """Fim da janela (chefe morto ou ``StopTime``), uma vez só: um correio por prêmio do fim, só com o chefe morto
    (Apollo, Warrior e Lucky; ``end_prizes``), a vida da próxima janela (``next_hp``) e o dano de todos, numa
    transação. Com o chefe morto: 4182 encerrado a todos, 128 do chefe e os textos do fim (visto #3218-#3239). Quem
    está no mapa e fora de luta sai (22) e recebe o 4203; quem está em luta, no fim dela (``_boss_over``)."""
    now = ctx.clock.now()
    async with pool.lock:
        if pool.fight.settled:
            return
        pool.fight.settled = True
        pool.fight.next_hp = boss_fight.next_hp(pool.boss, pool.fight)
        prizes = [p for p in boss_fight.end_prizes(ctx.world, pool) if p.gold or p.daru]
        # o último golpe vai direto a quem o deu ("has been rewarded with 800,000 Gold", #3234); o 83 sai depois
        killer = next((o for o in _online(ctx) if o.player_id == pool.fight.killer_id), None)
        lucky = [p for p in prizes if p.kind == "lucky"] if killer is not None else []
        mails = [(_prize_mail(p, now), p) for p in prizes if p not in lucky]

        async def change(uow: UnitOfWork) -> None:
            if killer is not None and killer.snapshot is not None and lucky:
                ch = killer.snapshot.character
                ch.gold += sum(p.gold for p in lucky)
                ch.strategy += sum(p.daru for p in lucky)
                await uow.save(ch)
            await uow.save(pool.fight)
            for wound in pool.wounds.values():
                await uow.save(wound)
            for mail, p in mails:
                await mailbox.stage(uow, mail, [(t, n) for t, n in ((DARU, p.daru), (GOLD, p.gold)) if n])

        await ctx.characters.write(change)
    log.info("chefe do mundo encerrado", chefe=pool.boss.campaign_id, vida=pool.hp, killer=pool.fight.killer_id,
             proxima=pool.fight.next_hp, premios=len(mails))  # fmt: skip
    for timer in pool.timers.values():
        timer.cancel()
    pool.timers.clear()
    pool.dead.clear()
    if pool.ticker is not None:
        pool.ticker.cancel()
        pool.ticker = None
    cid = pool.boss.campaign_id
    if killer is not None and killer.snapshot is not None and lucky:
        killer.send(S_PLAYER, b.complete(player_info(killer, killer.snapshot)))
    if pool.fight.killer_id:
        row = worldboss.boss(ctx.templates, cid)
        name = row["CampaignName"] if row is not None else ""
        for o in _online(ctx):
            push_states(o)
        for o in players_on(ctx, cid):
            o.send(S_NODE, pb.CampaignNodeUpdateMsg(nodeId=BOSS_NODE, nodeState=GONE, param1=0))
        texts = _end_texts(ctx, pool, name)
        for o in _online(ctx):
            for text in texts:
                o.send(S_CHAT, text)
    for mail, _ in mails:
        mailbox.notify(ctx.online, mail)
    for o in players_on(ctx, cid):
        if o.battle is None:
            _report_and_kick(o, pool)


def _report_and_kick(s: GameSession, pool: boss_fight.Pool) -> None:
    """22, 4165 sem buff e 4203 (visto #3241-#3251): a posição no dano, o ouro e o Daru de todas as lutas (o dano
    total // ``damage_per_gold``: #3251 185775 -> 37155) e o dano total."""
    ranking = [w.character_id for w in pool.ranking()]
    mine = pool.wounds.get(s.player_id)
    wound = mine.wound if mine else 0
    earned = wound // max(1, pool.boss.damage_per_gold)
    leave_boss(s)
    s.send(S_BUFF, pb.CampaignBufferMsg(armyId=s.player_id))
    s.send(S_BOSS_REPORT, pb.WorldBossReportMsg(
        campaignId=pool.boss.campaign_id, order=ranking.index(s.player_id) + 1 if s.player_id in ranking else 0,
        gold=earned, strengy=earned, totalWound=wound, type=REPORT_TYPE))  # fmt: skip


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
    """4175: morto (1) com o tempo até reviver em ms, ou vivo (0). (visto #1725) sem ``serverName``."""
    until, now = pool.dead.get(character_id), s.ctx.clock.now()
    left = int((until - now).total_seconds() * 1000) if until is not None and now < until else 0
    msg = pb.PlayerStateListMsg()
    msg.playerState.add(armyId=character_id, state=int(left > 0), leftTime=left)
    return msg


def _send_state(s: GameSession, pool: boss_fight.Pool) -> None:
    msg = _state_msg(s, pool, s.player_id)
    for o in [s, *on_map(s, pool.boss.campaign_id)]:
        o.send(S_PLAYER_STATE, msg)


def _kill(s: GameSession, pool: boss_fight.Pool) -> None:
    """Perdeu a luta (o ``killTurn``): morto por ``revive_seconds`` (visto #1725 -> #1762: 30 s), depois revive."""
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


def broadcast_info(ctx: GameContext, pool: boss_fight.Pool) -> None:
    """O 4174 de cada um (o ``myWound`` muda) a todos no mapa do chefe."""
    now = ctx.clock.now()
    players = players_on(ctx, pool.boss.campaign_id)
    for o in players:
        o.send(S_BOSS_INFO, pool.info(o.player_id, len(players), now))


def _refusal(s: GameSession, campaign_id: int) -> str | None:
    row = worldboss.boss(s.ctx.templates, campaign_id)
    if row is None:
        if next(s.ctx.templates.find("Campaigns", CampaignId=campaign_id), None) is not None:
            return UNAVAILABLE  # campanha sem conteúdo de pedreira no banco (a 6001 entra antes, ``enter_quarry``)
        return "Invalid World Boss."
    snap = s.snapshot
    assert snap is not None
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
    pool.dead.pop(s.player_id, None)  # antes do await: um segundo 8264 já vê vivo
    # missão tipo 66 (183 "Spend Balens to begin the battle instantly ... 3 times"): é este reviver pago
    quests = rules.quest_event(snap, ctx.templates, QUEST_INSTANT, 0, 1)
    await ctx.characters.save(snap.character, entry, *quests)
    # (visto) oficial_20261026-225632-1 #8629-#8638: 3, 150, 4434, 4175 vivo e a luta começa na hora (140, 157)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    balens_changed(s)
    revive(s, pool)
    if c is not None and (node := c.nodes.get(_camp(c.map_id, BOSS_NODE))) is not None:
        await boss_attack(s, node)


@router.on(8470)
async def buy_buff(s: GameSession, msg: pb.WorldBossBufferMsg) -> None:
    """Buff do chefe (``CampaignBufferTemps`` ``Types=4``, ``WorldBossBuyBuffModel.BUFFER_TYPE``): só se compra
    dentro do mapa do chefe. Nada é cobrado."""
    s.log.info("buff do chefe recusado (sem mapa do chefe)", pedido=str(msg))
    alert(s, UNAVAILABLE)
