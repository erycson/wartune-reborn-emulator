"""Altar do demônio da guilda (Divine Altar, mapa 7601): entrada (8542), as ondas, a luta, o buff (8550), as
habilidades da guilda (8593), o reviver pago em contribuição (8264) e o fim (4449).

Sem captura do altar: o protocolo é do cliente (``ConsortiaManager``: 4437 ``AltarCampaignReportMsg``, 4449 fim com
``PropertyMsg``, 4485 habilidade usada; ``ConsortiaDemonInfo``: as 2 habilidades com 300 s de espera, o buff quando
``buffType > userBuffType``) e as regras são da ajuda (``ConsortiaDemonWoundView.helpContent``): 1 min de preparo, o
evento acaba no tempo (21 min, ``guild.ALTAR_SECONDS``) ou com a vida do altar em 0, quem passa de certa pontuação
dá um buff a todos, e uma onda nova vem quando a anterior morre ou depois de 5 min. Os preços são dos ConfigInfos
(``AltarLive_Offer``, ``ConsortiaAltarBufferNeedOffer``, ``ConsortiaAltarSceneNeedOffe_Live``/``_Fix``,
``ConsortiaAltarSceneLive``) e os buffs os ``CampaignBufferTemps`` 511-530 (``Types=5``, "only applied in the Divine
Altar"). A luta reaproveita o chefe do mundo (``worldboss.battle_spec``, ``boss_fight.Pool`` e ``SharedHp``): cada onda
é um demônio de vida compartilhada pela guilda, com a vida do ``GameHeroTemp`` do herói da config.

TODO(inventado) (``game_settings.altar_demon``, migração 0110): o herói da onda, o multiplicador da vida, a vida do
altar e quanto uma onda que escapa tira, as posições no mapa, o passo da pontuação do buff e o prêmio do correio do fim.
"""

from __future__ import annotations

import asyncio
import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ...domain.models import Consortia, Mail, MailType, WorldBossFight
from ...protocol.messages import wartune_pb2 as pb
from .. import boss_fight, space
from .. import guild as gd
from .. import mail as mailbox
from ..battle import Battle, SharedHp
from ..builders import login as b
from ..campaign import DONE, NORMAL, CampaignMap
from ..router import router
from ..session import GameContext, GameSession
from . import worldboss as wb
from .campaign import ARMY_FIGHTING, ARMY_IDLE, CAMPAIGN_SCENE, map_sync, player_hero
from .guild.common import _mine, _push_info, _refuse
from .login import army, player_info
from .player import alert

ALTAR_MAP = 7601
S_REPORT, S_END, S_SKILL = 4437, 4449, 4485
PREP, WAVE_EVERY, FREEZE = timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=2)  # ajuda; Time Freeze 2 min
SKILL_CD = 300  # ConsortiaDemonInfo.maxCdTimer
LIVE, FIX = 1, 2  # AltarCampaignSkillMsg.templateId (ConsortiaDemonInfo: 1 = _Live, 2 = _Fix)
BUFF_BASE = 510  # CampaignBufferTemps 511-530: grau N = 510 + N
BUFF_MAX = 20
NOT_OPEN = "The Divine Altar is not open."
NO_OFFER = "Not enough contribution."
REWARD_TITLE = (
    "Divine Altar Rewards"  # TODO(inventado): título e texto do correio (a ajuda só diz "check your mailbox")
)
REWARD_TEXT = "The Divine Altar is over. {waves} waves were defeated and you ranked #{rank}."
DEFAULTS: dict[str, Any] = {
    "hero": 1042, "hp_mult": 50, "durability": 100, "leak": 20, "start": [20, 120], "node": [100, 75],
    "buff_step": 100000, "reward_per_wave": 10000,
}  # fmt: skip


@dataclass
class Run:
    """O altar aberto de uma guilda (memória: o evento dura 21 min)."""

    guild_id: int
    opened: datetime
    pool: boss_fight.Pool
    durability: int
    wave: int = 0
    wave_hp: int = 0
    wave_at: datetime | None = None
    killed: int = 0  # ondas vencidas
    frozen_until: datetime | None = None
    skills: dict[int, datetime] = field(default_factory=dict)  # habilidade -> quando foi usada
    got_buff: dict[int, int] = field(default_factory=dict)  # personagem -> grau do buff comprado
    over: bool = False


def cfg(ctx: GameContext) -> dict[str, Any]:
    return {**DEFAULTS, **(ctx.world.settings.get("altar_demon") or {})}


def _run(s: GameSession, guild: Consortia) -> Run | None:
    """O altar da guilda aberto agora (cria na primeira entrada); None fora da janela."""
    ctx, now = s.ctx, s.ctx.clock.now()
    if gd.altar_state(guild, now) != gd.ALTAR_OPEN or guild.altar_at is None:
        return None
    runs = ctx.guilds.altars
    run: Run | None = runs.get(guild.id or 0)
    if run is not None and run.opened == guild.altar_at:
        return run
    base = ctx.world.world_bosses.get(5001) or next(iter(ctx.world.world_bosses.values()), None)
    if base is None:
        return None
    c = cfg(ctx)
    (sx, sy), (nx, ny) = c["start"], c["node"]
    boss = dataclasses.replace(base, campaign_id=ALTAR_MAP, hero_id=int(c["hero"]), start_x=sx, start_y=sy,
                               node_x=nx, node_y=ny, gate_x=0, gate_y=0, portal_x=0, portal_y=0)  # fmt: skip
    pool = boss_fight.Pool(boss, WorldBossFight(ALTAR_MAP, guild.altar_at, 0))
    run = runs[guild.id or 0] = Run(guild.id or 0, guild.altar_at, pool, int(c["durability"]))
    return run


def _wave_hp(ctx: GameContext, wave: int) -> int:
    """A vida do template (``GameHeroTemp.Live`` do herói) vezes o multiplicador e o número da onda."""
    hero = ctx.templates.get("GameHeroTemp", int(cfg(ctx)["hero"])) or {}
    return max(1, int(hero.get("Live") or 1) * int(cfg(ctx)["hp_mult"]) * wave)


def _spawn(ctx: GameContext, run: Run, now: datetime) -> None:
    """Onda nova: a vida da anterior (se sobrou) some; ``total_hp`` acumula para o dano seguir somando como pontos."""
    run.wave += 1
    run.wave_hp = _wave_hp(ctx, run.wave)
    dealt = sum(w.wound for w in run.pool.wounds.values())
    run.pool.fight.total_hp = dealt + run.wave_hp
    run.pool.fight.killer_id = 0
    run.wave_at = now


def here(ctx: GameContext, guild_id: int) -> list[GameSession]:
    return [o for o in gd.online_members(ctx, guild_id) if o.campaign is not None and o.campaign.altar]


def _buff_grade(ctx: GameContext, run: Run) -> int:
    top = max((w.wound for w in run.pool.wounds.values()), default=0)
    return min(BUFF_MAX, top // max(1, int(cfg(ctx)["buff_step"])))


def _skill_msgs(run: Run, now: datetime) -> list[pb.AltarCampaignSkillMsg]:
    return [pb.AltarCampaignSkillMsg(templateId=t, cDTimer=max(0, SKILL_CD - int((now - at).total_seconds())))
            for t, at in sorted(run.skills.items())]  # fmt: skip


def report(ctx: GameContext, run: Run, s: GameSession) -> pb.AltarCampaignReportMsg:
    now = ctx.clock.now()
    inside = {o.player_id for o in here(ctx, run.guild_id)}
    msg = pb.AltarCampaignReportMsg(
        altarDurability=run.durability, waveNum=run.wave, monsterCount=int(run.wave > 0 and run.pool.hp > 0),
        buffType=_buff_grade(ctx, run), userBuffType=run.got_buff.get(s.player_id, 0),
        leftStartTime=max(0, int((run.opened + PREP - now).total_seconds() * 1000)),
    )  # fmt: skip
    for w in run.pool.ranking():
        msg.hurtOrder.add(userId=w.character_id, hurt=w.wound, isInAltar=w.character_id in inside)
    msg.skill.extend(_skill_msgs(run, now))
    return msg


def _tell(ctx: GameContext, run: Run) -> None:
    for o in here(ctx, run.guild_id):
        o.send(S_REPORT, report(ctx, run, o))


def _demon_state(run: Run) -> int:
    return NORMAL if run.wave > 0 and run.pool.hp > 0 else DONE


def _nodes(run: Run) -> dict[int, dict[str, Any]]:
    row = {"CampaignName": "Divine Altar"}
    nodes = wb.boss_nodes(row, run.pool.boss, True)
    keep = {wb._camp(ALTAR_MAP, wb.ENTRY), wb._camp(ALTAR_MAP, wb.BOSS_NODE)}
    out = {k: v for k, v in nodes.items() if k in keep}
    out[wb._camp(ALTAR_MAP, wb.BOSS_NODE)]["state"] = _demon_state(run)
    return out


def _node_push(ctx: GameContext, run: Run) -> None:
    msg = pb.CampaignNodeUpdateMsg(nodeId=wb.BOSS_NODE, nodeState=_demon_state(run), param1=0)
    for o in here(ctx, run.guild_id):
        if o.campaign is not None and (n := o.campaign.nodes.get(wb._camp(ALTAR_MAP, wb.BOSS_NODE))) is not None:
            n["state"] = msg.nodeState
        o.send(wb.S_NODE, msg)


@router.on(8542)
async def enter(s: GameSession, _: object) -> None:
    """Entrar: membro de guilda com o altar aberto (``ConsortiaSocketOutManager`` só manda com ele aberto), fora de
    luta e de outro mapa. Como o chefe do mundo: 125, 140, 21, 127, 4165, 150 e o 4437 do altar."""
    mine, snap = _mine(s), s.snapshot
    run = _run(s, mine[0]) if mine is not None else None
    if run is None or snap is None or run.over or s.battle is not None or s.campaign is not None:
        _refuse(s, 8542, "altar fechado ou já num mapa", guilda=mine and mine[0].id)
        if run is None:
            alert(s, NOT_OPEN)
        return
    ctx, now = s.ctx, s.ctx.clock.now()
    await clock(s)
    boss = run.pool.boss
    s.campaign = CampaignMap(ALTAR_MAP, _nodes(run), (boss.start_x, boss.start_y), altar=True)
    space.leave(s)
    room = pb.RoomCreatedMsg(createdType=wb.ROOM_ENTER)
    room.room.campaignId = ALTAR_MAP
    s.send(wb.S_ROOM_CREATED, room)
    s.send(wb.S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    me = space.room_player(snap, ctx.templates, s.campaign.pos, ALTAR_MAP, now)
    others = [o for o in here(ctx, run.guild_id) if o is not s]
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, ALTAR_MAP, now)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(wb.S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    for o in others:
        o.send(wb.S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    s.send(wb.S_NODES, s.campaign.node_list())
    s.send(wb.S_BUFF, _buff_msg(s, run))
    s.send(wb.S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _tell(ctx, run)


def _buff_msg(s: GameSession, run: Run) -> pb.CampaignBufferMsg:
    msg = pb.CampaignBufferMsg(armyId=s.player_id)
    if grade := run.got_buff.get(s.player_id, 0):
        msg.bufferInfo.add(bufferTempId=BUFF_BASE + grade, leftTime=0)
    return msg


async def clock(s: GameSession) -> None:
    """No relógio (20008) e na entrada: o preparo acaba (1ª onda), a onda que passou de 5 min escapa (tira vida do
    altar e vem a seguinte; parada enquanto o Time Freeze vale) e o fim (tempo ou altar em 0)."""
    mine = _mine(s)
    if mine is None:
        return
    ctx, now = s.ctx, s.ctx.clock.now()
    run = ctx.guilds.altars.get(mine[0].id or 0)
    if run is None or run.over:
        return
    changed = False
    if run.wave == 0 and now >= run.opened + PREP:
        _spawn(ctx, run, now)
        changed = True
    frozen = run.frozen_until is not None and now < run.frozen_until
    if run.wave and run.wave_at is not None and not frozen and now - run.wave_at >= WAVE_EVERY:
        if run.pool.hp > 0:
            run.durability = max(0, run.durability - int(cfg(ctx)["leak"]))
        _spawn(ctx, run, now)
        changed = True
    if run.durability <= 0 or (now - run.opened).total_seconds() >= gd.ALTAR_SECONDS:
        await finish(s, mine[0], run)
        return
    if changed:
        _node_push(ctx, run)
        _tell(ctx, run)


async def finish(s: GameSession, guild: Consortia, run: Run) -> None:
    """Fim: o altar fica encerrado hoje, 4449 (``param1`` posição no dano, 0 = sem posição; ``param2`` ondas
    vencidas; ``param3`` o estado novo) a todos os membros online, o prêmio pelo correio e quem está no mapa sai."""
    if run.over:
        return
    run.over = True
    ctx, now = s.ctx, s.ctx.clock.now()
    guild.altar_state = gd.ALTAR_ENDED
    await ctx.characters.save(guild)
    ranking = [w.character_id for w in run.pool.ranking()]
    per_wave = int(cfg(ctx)["reward_per_wave"])
    for o in gd.online_members(ctx, run.guild_id):
        rank = ranking.index(o.player_id) + 1 if o.player_id in ranking else 0
        o.send(S_END, pb.SimplePropertyMsg(param1=rank, param2=run.killed, param3=gd.ALTAR_ENDED))
    for rank, cid in enumerate(ranking, 1):
        gold = per_wave * max(1, run.killed) // rank
        mail = Mail(cid, now, REWARD_TITLE, REWARD_TEXT.format(waves=run.killed, rank=rank),
                    mail_type=MailType.SYSTEM, send_type=mailbox.SYSTEM_SENDER)  # fmt: skip
        await mailbox.deliver(ctx.characters, ctx.online, mail, [(wb.GOLD, gold), (wb.DARU, gold)])
    for timer in run.pool.timers.values():
        timer.cancel()
    for o in here(ctx, run.guild_id):
        if o.battle is None:
            leave(o)
    _push_info(s, guild)


def leave(s: GameSession) -> bool:
    """Sai do altar (5025, fim ou desconexão): 22 para todos no mapa, o próprio também."""
    c, snap = s.campaign, s.snapshot
    if c is None or not c.altar or snap is None:
        return False
    if s.battle is not None:
        s.battle.cancel()
        s.battle = None
    mine = _mine(s)
    msg = pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id, serverName=snap.server.name)
    for o in here(s.ctx, mine[0].id or 0) if mine is not None else []:
        if o is not s:
            o.send(wb.S_EXIT, msg)
    s.campaign = None
    s.send(wb.S_EXIT, msg)
    if mine is not None and (run := s.ctx.guilds.altars.get(mine[0].id or 0)) is not None:
        _tell(s.ctx, run)
    return True


def _state_msg(s: GameSession, run: Run) -> pb.PlayerStateListMsg:
    return wb._state_msg(s, run.pool, s.player_id)


def _revive(s: GameSession, run: Run) -> None:
    run.pool.dead.pop(s.player_id, None)
    if (timer := run.pool.timers.pop(s.player_id, None)) is not None:
        timer.cancel()
    if s.campaign is not None and s.campaign.altar and not s.gone.is_set():
        s.send(wb.S_PLAYER_STATE, _state_msg(s, run))


async def attack(s: GameSession, node: dict[str, Any]) -> None:
    """5125 no demônio: a luta do chefe do mundo contra a vida compartilhada da onda."""
    ctx, snap, c = s.ctx, s.snapshot, s.campaign
    mine = _mine(s)
    assert snap is not None and c is not None
    run = ctx.guilds.altars.get(mine[0].id or 0) if mine is not None else None
    if node["campDataId"] != wb._camp(ALTAR_MAP, wb.BOSS_NODE) or run is None or run.over:
        return
    pool = run.pool
    if run.wave == 0 or pool.hp <= 0 or s.battle is not None or c.fighting:
        return
    if pool.is_dead(s.player_id, ctx.clock.now()):
        s.send(wb.S_PLAYER_STATE, _state_msg(s, run))
        return
    ch = snap.character
    cid, nick, job = s.player_id, ch.nickname or "", ch.job
    link = SharedHp(wb.BOSS_LIVING, lambda: pool.hp, lambda v: pool.hit(cid, nick, job, v, ctx.clock.now()))
    spec = wb.battle_spec(s, pool)
    spec["heroes"][0]["maxHp"] = run.wave_hp  # a vida cheia é a da onda (``total_hp`` acumula as ondas)
    c.fighting = wb.BOSS_NODE
    s.send(wb.S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))

    async def finished(battle: Battle, won: bool) -> None:
        await _over(s, battle, won, run, link)

    s.battle = Battle(spec, player_hero(s, spec), ctx.templates, ctx.clock, s.send, finished, shared=link,
                      settings=ctx.world.settings)  # fmt: skip
    s.battle.start()


async def _over(s: GameSession, battle: Battle, won: bool, run: Run, link: SharedHp) -> None:
    """Fim da luta: ouro e Daru pelo dano (``battle_reward``, como no chefe), 3, 4103, 150 e 140; onda vencida chama a
    seguinte; perdeu: morto por ``revive_seconds`` (4175)."""
    snap, ctx = s.snapshot, s.ctx
    assert snap is not None
    s.hero_sp, s.battle = battle.player_sp, None
    if s.campaign is not None:
        s.campaign.fighting = 0
    ch = snap.character
    reward = run.pool.battle_reward(link.dealt)
    ch.gold += reward
    ch.strategy += reward
    await ctx.characters.save(ch)
    s.send(wb.S_PLAYER, b.complete(player_info(s, snap)))
    rep = pb.BattleReportMsg(battleResult=1 if won else 2, strategyBonus=reward, gpBonus=0, battleScene=CAMPAIGN_SCENE)
    rep.failCount, rep.goldBonus, rep.petGpBonus = 0, reward, 0
    s.send(wb.S_REPORT, rep)
    s.send(wb.S_FULL_ARMY, b.complete(army(s, snap)[0]))
    s.send(wb.S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    if run.wave and run.pool.hp <= 0 and not run.over:
        run.killed += 1
        _spawn(ctx, run, ctx.clock.now())
        _node_push(ctx, run)
    elif not won:
        secs = run.pool.boss.revive_seconds
        run.pool.dead[s.player_id] = ctx.clock.now() + timedelta(seconds=secs)
        run.pool.timers[s.player_id] = asyncio.get_running_loop().call_later(secs, _revive, s, run)
        s.send(wb.S_PLAYER_STATE, _state_msg(s, run))
    _tell(ctx, run)


def _here_run(s: GameSession) -> tuple[Consortia, Run] | None:
    mine = _mine(s)
    if mine is None or s.campaign is None or not s.campaign.altar:
        return None
    run = s.ctx.guilds.altars.get(mine[0].id or 0)
    return (mine[0], run) if run is not None and not run.over else None


async def revive_paid(s: GameSession) -> bool:
    """8264 no altar (``RiverView`` tipo 2): ``AltarLive_Offer`` de contribuição e volta vivo. False: não é o altar."""
    found, snap = _here_run(s), s.snapshot
    if found is None or snap is None:
        return False
    run = found[1]
    cost = gd.config(s.ctx.templates, "AltarLive_Offer", 50)
    if not run.pool.is_dead(s.player_id, s.ctx.clock.now()) or snap.character.consortia_offer < cost:
        alert(s, NO_OFFER if snap.character.consortia_offer < cost else wb.UNAVAILABLE)
        return True
    snap.character.consortia_offer -= cost
    await s.ctx.characters.save(snap.character)
    s.send(wb.S_PLAYER, b.complete(player_info(s, snap)))
    _revive(s, run)
    return True


@router.on(8550)
async def buy_buff(s: GameSession, _: object) -> None:
    """O buff do grau atual (``canGetBuff``: ``buffType > userBuffType``) por ``ConsortiaAltarBufferNeedOffer``."""
    found, snap = _here_run(s), s.snapshot
    cost = gd.config(s.ctx.templates, "ConsortiaAltarBufferNeedOffer", 200)
    if found is None or snap is None:
        _refuse(s, 8550, "fora do mapa do altar")
        return
    run = found[1]
    grade = _buff_grade(s.ctx, run)
    if grade <= run.got_buff.get(s.player_id, 0) or snap.character.consortia_offer < cost:
        _refuse(s, 8550, "sem buff novo ou sem contribuição", grau=grade)
        return
    snap.character.consortia_offer -= cost
    run.got_buff[s.player_id] = grade
    await s.ctx.characters.save(snap.character)
    s.send(wb.S_PLAYER, b.complete(player_info(s, snap)))
    s.send(wb.S_BUFF, _buff_msg(s, run))
    s.send(S_REPORT, report(s.ctx, run, s))


@router.on(8593)
async def skill(s: GameSession, msg: pb.ConsortiaAltarOpenReqMsg) -> None:
    """Habilidade da guilda (riqueza): 1 reza (altar +``ConsortiaAltarSceneLive``), 2 Time Freeze (as ondas param
    2 min); 300 s de espera cada. 4485 a todos os membros online (o cliente põe no chat), depois o 4437."""
    found = _here_run(s)
    if found is None or msg.altarType not in (LIVE, FIX) or s.snapshot is None:
        _refuse(s, 8593, "fora do mapa do altar ou habilidade inválida", tipo=msg.altarType)
        return
    guild, run = found
    ctx, now = s.ctx, s.ctx.clock.now()
    name = "ConsortiaAltarSceneNeedOffe_Live" if msg.altarType == LIVE else "ConsortiaAltarSceneNeedOffe_Fix"
    cost = gd.config(ctx.templates, name, 10000)
    used = run.skills.get(msg.altarType)
    if guild.offer < cost or (used is not None and (now - used).total_seconds() < SKILL_CD):
        _refuse(s, 8593, "sem riqueza ou em espera", riqueza=guild.offer)
        return
    guild.offer -= cost
    run.skills[msg.altarType] = now
    if msg.altarType == LIVE:
        top = int(cfg(ctx)["durability"])
        run.durability = min(top, run.durability + gd.config(ctx.templates, "ConsortiaAltarSceneLive", 20))
    else:
        run.frozen_until = now + FREEZE
        if run.wave_at is not None:
            run.wave_at += FREEZE  # o relógio da onda para durante o congelamento
    await ctx.characters.save(guild)
    c = s.snapshot.character
    out = pb.AltarCampaignSkillMsg(templateId=msg.altarType, cDTimer=SKILL_CD, userId=s.player_id,
                                   nickName=c.nickname or "", consortiaId=guild.id or 0)  # fmt: skip
    for o in gd.online_members(ctx, guild.id or 0):
        o.send(S_SKILL, out)
    _push_info(s, guild)
    _tell(ctx, run)


@router.on(8549)
async def arrive_altar(s: GameSession, msg: pb.ArriveAltarReqMsg) -> None:
    """O exército chegou ao altar (``ArriveAltarReqMsg``): o cliente só avisa; o estado vem no 4437."""
    found = _here_run(s)
    if found is None:
        _refuse(s, 8549, "fora do mapa do altar", no=msg.nodeId)
        return
    s.send(S_REPORT, report(s.ctx, found[1], s))
