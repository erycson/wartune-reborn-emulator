"""Campanha de treino: entrar no mapa, andar, eventos dos nós, batalhas e saída para a cidade.

Sequências reproduzidas da captura oficial (``docs/tutorial.md``). O roteiro de cada nó está em
``ARRIVE_PLOT``/``CALLBACKS``/``WIN_UNLOCKS``; o conteúdo (nós, tropas, falas) em ``content``.
"""

from __future__ import annotations

import uuid

from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from ...content import tutorial
from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...protocol.registry import Direction
from .. import rules, space
from ..battle import Battle, PlayerHero
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..campaign import AGGRESSIVE, DONE, FIGHTING, FIRST_MAP, MONSTER, NORMAL, SECOND_MAP, CampaignMap, map_for
from ..router import router
from ..session import GameSession
from .login import army, player_info

S_PLAYER, S_NOVICE, S_ARMY_PAWN = 3, 1, 100
S_CHAT, S_ALERT = 83, 111
S_ROOM_ENTER, S_ROOM_CREATED, S_NODES, S_NODE, S_FOG, S_ARMY_POS = 21, 125, 127, 128, 130, 131
S_PLOT, S_MAP_SYNC, S_CAMERA, S_MOVIE, S_CAMPAIGN_FINISH = 138, 140, 142, 143, 134
S_BATTLE_REPORT, S_NPC_CHASE, S_NPC_MOVE, S_ESCORT, S_PLAYER_MOVE = 4103, 4105, 4122, 4124, 4162
S_BUFFERS, S_NODE_STAND, S_FIGHT_MOVIE = 4165, 4208, 4382
S_FULL_ARMY, S_QUESTS, S_ITEMS = 150, 112, 115

ENTER, PORTAL_ENTER = 1, 3  # RoomCreatedMsg.createdType
ARMY_IDLE, ARMY_FIGHTING = 0, 2
SCENE = "CAMPAIGN_MAP_SCENE"
BACK_TO_MAP = 4  # LoginStateMsg.state que o cliente manda ao voltar para o mapa
CAMPAIGN_SCENE = 3  # BattleReportMsg.battleScene
WON, LOST = 1, 2
TILE = 20  # PosMoveMsg.routes vem em pixels

# roteiro (campDataId). Diálogos pelo índice em tutorial.json["plots"]; o fim do diálogo faz o
# cliente mandar 5032 (evento SESSION_OVER ... command:2) e a reação depende de quantos já vieram.
ARRIVE_PLOT = {1000110: 0, 1000106: 2, 1000205: 3}
FLICKER_PLOT = 1  # 1º 5032 do gatilho 1000110: câmera na Tina, urso pisca, diálogo 1
CHASE_TRIGGER = 1000110  # 2º 5032: jogador anda até param4 sozinho
WALK_TRIGGER = 1000208  # chegada: anda até param4 com a câmera
TINA = 1000107
# 5032 nesses nós: ainda de pé abre a batalha; já derrotado (só o 1000106, depois do 15300) faz a
# Tina seguir o jogador. Pelo estado, não pela contagem: depois de relogar a contagem recomeça.
BATTLE_CALLBACK = {1000106, 1000205}
ESCORT_CALLBACK = 1000106
WIN_UNLOCKS = {1000106: [1000109], 1000205: [1000206, 1000207]}
NOVICE_UNLOCKS = {14000: [1000108]}  # portal aparece quando o guia chega nesse ponto
PORTAL = {1000108: SECOND_MAP}
CHEST = 1000202  # param3: arma por job ("1011002|1012002|1013002|..."), índice job-1
EXIT = 1000206
RETURN_PORTAL = 62  # masterType do portal de chegada que leva de volta à cidade do céu
BOSS = "8251"  # chave em tutorial.json["battles"]


def _send(s: GameSession, code: int, msg: Message | None = None, extend2: int = 0) -> None:
    s.send(code, msg, extend2=extend2)


def _uuid() -> str:
    return str(uuid.uuid4())


def _map(s: GameSession) -> CampaignMap:
    assert s.campaign is not None
    return s.campaign


def _army_brief(s: GameSession, state: int) -> pb.ArmyArmyMsg:
    c = _map(s)
    return pb.ArmyArmyMsg(armyId=s.player_id, playerId=s.player_id, curPosX=c.pos[0], curPosY=c.pos[1], state=state)


def map_sync(s: GameSession, state: int) -> pb.MapUpdatedMsg:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None and snap.leader is not None
    full, fighting = army(s, snap)
    a = pb.ArmyArmyMsg(
        armyId=full.armyId,
        playerId=full.playerId,
        nickName=full.nickName,
        mapId=full.mapId,
        curPosX=full.curPosX,
        curPosY=full.curPosY,
        state=state,
        type=full.type,
        consortiaId=0,
        consortiaName="",
        fightingCapacity=fighting,
        gpOrder=0,
        grades=full.grades,
        arm=full.arm,
        cloth="",
        job=rules.job_type(snap.character.job),
        changeSharp=0,
        heroTempId=snap.leader.template_id,
        geste=0,
        isVip=False,
        vipType=0,
        mountTempId=0,
        mountGrade=0,
        wing="",
        hat="",
        fashionArm="",
        fashionCloth="",
        hide=False,
        appellid=0,
        fateSkills="",
        petTempId=0,
        petQuqlity=0,
        petName="",
    )
    return pb.MapUpdatedMsg(updatedType=3, army=a)


def _room_enter(s: GameSession) -> pb.RoomEnterMsg:
    snap, c = s.snapshot, _map(s)
    assert snap is not None
    return pb.RoomEnterMsg(result=1, player=[space.room_player(snap, s.ctx.templates, c.pos, c.map_id)])


def _escort(s: GameSession) -> None:
    c = _map(s)
    if c.escort:
        x, y = c.pos
        _send(s, S_ESCORT, pb.NPCFollowMsg(escortId=c.escort, followId=s.player_id, curPosX=x + 1, curPosY=y + 1))


def _node_update(s: GameSession, camp: int, state: int, *, user: bool = False, fresh: bool = False) -> None:
    """128. ``user``: nó em combate com este jogador; ``fresh``: nó novo (uuid e sonType)."""
    node = _map(s).node(camp)
    assert node is not None
    node["state"] = state
    msg = pb.CampaignNodeUpdateMsg(nodeId=node["nodeId"], nodeState=state)
    if user:
        msg.userId = s.player_id
    if fresh:
        msg.uuId = _uuid()
    msg.param1 = 0
    if fresh:
        msg.sonType = node["sonType"]
    _send(s, S_NODE, msg)


def _plot(s: GameSession, index: int) -> None:
    entry = tutorial()["plots"][index]
    cls = s.ctx.registry.message_type(S_PLOT, Direction.SERVER_TO_CLIENT)
    assert cls is not None
    msg = ParseDict(entry["plot"], cls())
    nick = s.snapshot.character.nickname if s.snapshot else ""
    for info in getattr(msg, "info", []):
        if info.roleName == "{nick}":
            info.roleName = nick or ""
    _send(s, S_PLOT, msg, extend2=entry["extend2"])


def _player_move(s: GameSession, camp: int, camera: bool) -> None:
    node = _map(s).node(camp)
    assert node is not None
    x, y = (int(v) for v in node["param4"].split(","))
    _send(
        s,
        S_PLAYER_MOVE,
        pb.PlayerMoveMsg(userId=s.player_id, mapId=_map(s).map_id, tarX=x, tarY=y, ismoveCamera=camera),
    )
    _node_update(s, camp, DONE)


async def _push_player(s: GameSession) -> None:
    assert s.snapshot is not None
    _send(s, S_PLAYER, b.complete(player_info(s, s.snapshot)))


# -- entrar no mapa ---------------------------------------------------------------------------


def _enter_map(s: GameSession, map_id: int, created: int) -> None:
    assert s.snapshot is not None
    s.campaign = CampaignMap.enter(map_id, s.snapshot.character.novice_process)
    room = pb.RoomCreatedMsg(createdType=created)
    room.room.campaignId = map_id
    _send(s, S_ROOM_CREATED, room)
    if created == ENTER:
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_ROOM_ENTER, _room_enter(s))
        _send(s, S_NODES, s.campaign.node_list())
        _send(s, S_FOG, s.campaign.fog())
        _escort(s)
        _send(s, S_MOVIE, pb.PlayerMovieMsg(movieTargetType=3, targetId=0, movieType="MOVIE_MAP_NAME", delay=0))
    else:  # pelo portal: sem 140/143, a Tina já vem seguindo
        _send(s, S_NODES, s.campaign.node_list())
        _send(s, S_FOG, s.campaign.fog())
        _escort(s)
        _send(s, S_ROOM_ENTER, _room_enter(s))
        _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))


@router.on(5127)
async def campaign_training(s: GameSession, msg: pb.NoviceReqMsgMsg) -> None:
    assert s.snapshot is not None
    _enter_map(s, map_for(s.snapshot.character.novice_process), ENTER)


@router.on(5124)
async def sync_pos(s: GameSession, msg: pb.PosMoveMsg) -> None:
    if s.campaign is not None and msg.routes:
        last = msg.routes[-1]
        s.campaign.pos = (last.x // TILE, last.y // TILE)


@router.on(8196)
async def node_lock(s: GameSession, msg: pb.NodeLockReqMsg) -> None:
    node = s.campaign.node(msg.nodeId) if s.campaign else None
    if node is not None and msg.lock and node["attackTypes"] == AGGRESSIVE and node["state"] == NORMAL:
        x, y = _map(s).pos
        _send(s, S_NPC_CHASE, pb.NPCChaseMsg(nodeId=node["nodeId"], armyId=s.player_id, curPosX=x, curPosY=y))


@router.on(5125)
async def arrive(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    c = s.campaign
    node = c.node(msg.paraInt1) if c else None
    if c is None or node is None or node["state"] != NORMAL or c.fighting:
        return
    camp = msg.paraInt1
    if node["masterType"] == RETURN_PORTAL and c.map_id not in (FIRST_MAP, SECOND_MAP):
        s.campaign = None  # portal de volta (ilha dos pets): cidade do céu com 4606
        space.back(s)
    elif camp in ARRIVE_PLOT:
        if camp not in c.talked:  # o cliente repete o 5125 enquanto anda sobre o nó
            c.talked.add(camp)
            _plot(s, ARRIVE_PLOT[camp])
    elif camp == WALK_TRIGGER:
        _player_move(s, camp, camera=True)
    elif camp == CHEST:
        await _open_chest(s, node)
    elif camp in PORTAL:
        _send(s, S_NODE_STAND, pb.PlayerNodeStateMsg(mapId=c.map_id, nodeId=camp, isStand=True, armyId=s.player_id))
        _enter_map(s, PORTAL[camp], PORTAL_ENTER)
    elif camp == EXIT:
        await _leave_campaign(s)
    elif node["masterType"] == MONSTER and str(camp) in tutorial()["battles"]:
        _start_battle(s, camp)


@router.on(5032)
async def callback(s: GameSession, msg: pb.CallBackReqMsg) -> None:
    c = s.campaign
    if c is None or c.node(msg.nodeId) is None:
        return
    camp = msg.nodeId
    c.callbacks[camp] += 1
    n = c.callbacks[camp]
    if camp == CHASE_TRIGGER and n == 1:
        tina, bear = c.node(TINA), c.node(1000106)
        assert tina is not None and bear is not None
        _send(s, S_CAMERA, pb.PlayerMoveCameraMsg(scene=SCENE, targetX=tina["posX"], targetY=tina["posY"]))
        movie = pb.PlayerMovieMsg(movieTargetType=0, targetId=bear["nodeId"], movieType="FLICKER", delay=10)
        _send(s, S_MOVIE, movie, extend2=10)
        _plot(s, FLICKER_PLOT)
    elif camp == CHASE_TRIGGER and n == 2:
        _player_move(s, camp, camera=False)
    elif camp in BATTLE_CALLBACK and c.node(camp)["state"] == NORMAL:  # type: ignore[index]
        _start_battle(s, camp)
    elif camp == ESCORT_CALLBACK and c.node(camp)["state"] == DONE:  # type: ignore[index]
        tina = c.node(TINA)
        assert tina is not None
        _node_update(s, TINA, 2)
        c.escort = tina["nodeId"]
        x, y = c.pos
        _send(s, S_ESCORT, pb.NPCFollowMsg(escortId=c.escort, followId=s.player_id, curPosX=x, curPosY=y))
        _send(s, S_NPC_MOVE, pb.NPCMoveMsg(id=c.escort, curPosX=x, curPosY=y))


# -- baú, saída --------------------------------------------------------------------------------


async def _open_chest(s: GameSession, node: dict[str, object]) -> None:
    snap = s.snapshot
    assert snap is not None
    weapons = str(node["param3"]).split("|")
    template_id = int(weapons[(snap.character.job - 1) % len(weapons)])
    row = s.ctx.templates.get("ItemTempInfos", template_id)
    assert row is not None
    # reaberto depois de relogar antes do 16700: o baú volta, a arma não
    if not any(i.template_id == template_id for i in snap.items):
        skill = int(row.get("DefaultSkill", 0))
        item = Item(s.player_id, template_id, pos=rules.free_bag_pos(snap), random_skill=skill)
        snap.items.append(item)
        await s.ctx.characters.save(item)
        _send(s, S_ITEMS, item_moved(item.bag_type, 0, item.pos, item, s.player_id))
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Kazanılan {row.get('TemplateName', '')}"))
    _node_update(s, CHEST, DONE)
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))


async def _leave_campaign(s: GameSession) -> None:
    assert s.snapshot is not None
    _send(s, S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    _send(s, S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    _send(s, S_CAMPAIGN_FINISH)
    s.campaign = None


# -- batalha -----------------------------------------------------------------------------------


def _player_hero(s: GameSession, spec: dict[str, object]) -> PlayerHero:
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    leader = snap.leader
    stats = rules.leader_stats(snap, s.ctx.templates)
    tpl_row = s.ctx.templates.get("GameHeroTemp", leader.template_id) or {}
    player = spec["player"]
    assert isinstance(player, dict)
    msg = pb.HeroMsg(
        heroId=leader.id,
        livingId=player["livingId"],
        userId=s.player_id,  # o cliente acha o próprio herói por userId == playerId
        userPics=snap.character.icon,
        tempId=leader.template_id,
        type=1,
        nickName=leader.nickname,
        grade=leader.grades,
        side=1,
        pos=player["pos"],
        maxHp=stats.live,
        initHp=stats.live,
        hp=stats.live,
        hp2=0,
        sp=s.hero_sp,
        slotAvata=rules.arm_avatar(snap, s.ctx.templates),
        clothAvate="",
        cloakPath="",
        hairPath="",
        captain=stats.total["ConatArmy"],
        res="",
        qteTime=0,
        castTime=4500,
        pawnTempId=0,
        headId=0,
        isShow=False,
        serverName=snap.server.name,
        wingAvata="",
        fashionArmAvata="",
        fashionClothAvata="",
        awake=0,
        livingId2=0,
        fateSkillTempIds="",
        isChange=False,
        fightCapacity=stats.fighting_capacity,
        hasShadow=False,
        mateId=0,
        curturn=0,
    )
    msg.skillId.extend(int(x) for x in leader.skill_script.split(",") if x)
    magic = rules.job_type(snap.character.job) == 3
    attack = stats.total["MagicAttack"] if magic else stats.total["PhyAttack"]
    return PlayerHero(msg, attack, int(tpl_row.get("DefaultSkill", 0)))


def _start_battle(s: GameSession, camp: int) -> None:
    c = _map(s)
    spec = tutorial()["battles"][str(camp)]
    c.fighting = camp
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    _send(s, S_ARMY_POS, _army_brief(s, ARMY_FIGHTING))
    _node_update(s, camp, FIGHTING, user=True)

    async def finished(battle: Battle, won: bool) -> None:
        await _battle_over(s, battle, camp, won)

    s.battle = Battle(spec, _player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished)
    s.log.info("batalha", nó=camp, battle=s.battle.id)
    s.battle.start()


@router.on(8251)
async def special_boss(s: GameSession, _: object) -> None:
    """Fim do tutorial na cidade externa: retomar o castelo dos Boğa Başlı (sem nó de campanha)."""
    if s.battle is not None:
        return
    spec = tutorial()["battles"][BOSS]
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))  # o oficial manda duas vezes

    async def finished(battle: Battle, won: bool) -> None:
        s.battle, s.hero_sp = None, battle.player.sp
        _send(s, S_BATTLE_REPORT, _report(battle, won, 0))
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))

    s.battle = Battle(spec, _player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished)
    s.log.info("batalha do chefe", battle=s.battle.id)
    s.battle.start()


def _report(battle: Battle, won: bool, gp: int) -> pb.BattleReportMsg:
    report = pb.BattleReportMsg(battleResult=WON if won else LOST, strategyBonus=0, gpBonus=gp)
    report.battleScene = int(battle.spec.get("battleScene", CAMPAIGN_SCENE))
    report.failCount, report.goldBonus, report.petGpBonus = 0, 0, 0
    return report


async def _battle_over(s: GameSession, battle: Battle, camp: int, won: bool) -> None:
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    s.battle, s.hero_sp = None, battle.player.sp
    gp = int(battle.spec.get("gpBonus", 0)) if won else 0
    if gp:
        rules.add_gp(snap, s.ctx.templates, gp)
        await s.ctx.characters.save(snap.character, snap.leader)
    s.battle_gp = gp
    await _push_player(s)
    _send(s, S_BATTLE_REPORT, _report(battle, won, gp))
    if gp:
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"{gp} EXP kazanıldı"))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_ARMY_PAWN, pb.ArmyPawnUpdatedMsg())
    if s.campaign is None:
        return
    s.campaign.fighting = 0
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))
    if not won:
        _node_update(s, camp, NORMAL)
        return
    _node_update(s, camp, DONE, fresh=True)
    for unlocked in WIN_UNLOCKS.get(camp, []):
        _node_update(s, unlocked, NORMAL, fresh=True)


def _battle(s: GameSession, battle_id: str) -> Battle | None:
    return s.battle if s.battle is not None and s.battle.id == battle_id else None


@router.on(10007)
async def load_over(s: GameSession, msg: pb.LoadOverMsg) -> None:
    if (battle := _battle(s, msg.battleId)) is not None:
        battle.load_over()


@router.on(10008)
async def use_skill(s: GameSession, msg: pb.UseSkillMsg) -> None:
    if (battle := _battle(s, msg.battleId)) is not None:
        battle.order(msg.heroId, msg.skillId)


@router.on(10010)
async def battle_pause(s: GameSession, msg: pb.BattleReqMsg) -> None:
    if (battle := _battle(s, msg.battleId)) is not None:
        battle.pause()


@router.on(10022)
async def battle_resume(s: GameSession, msg: pb.BattleReqMsg) -> None:
    if (battle := _battle(s, msg.battleId)) is not None:
        battle.resume()


@router.on(10020)
async def attack_mode(s: GameSession, msg: pb.AttackModeMsg) -> None:
    if (battle := _battle(s, msg.battleId)) is not None:
        battle.set_auto(msg.mode == 1)  # o oficial não responde


@router.on(5035)
async def client_state(s: GameSession, msg: pb.LoginStateMsg) -> None:
    if msg.state == BACK_TO_MAP and s.battle_gp:
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=0))
        s.battle_gp = 0


# -- progresso do guia -------------------------------------------------------------------------


@router.on(5017)
async def novice(s: GameSession, msg: pb.NoviceReqMsgMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    if msg.noviceProcess > c.novice_process:
        c.novice_process = msg.noviceProcess
    changed = rules.update_novice_quests(snap, s.ctx.templates)
    await s.ctx.characters.save(c, *changed)
    if changed:
        _send(s, S_QUESTS, quest_update(changed, rules.quest_bitmap(snap)))
    await _push_player(s)
    _send(s, S_NOVICE)
    if s.campaign is not None and s.campaign.map_id == FIRST_MAP:
        for camp in NOVICE_UNLOCKS.get(c.novice_process, []):
            node = s.campaign.node(camp)
            if node is not None and node["state"] != NORMAL:
                _node_update(s, camp, NORMAL, fresh=True)
