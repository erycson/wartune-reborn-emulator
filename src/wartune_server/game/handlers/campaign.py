"""Campanha de treino: entrar no mapa, andar, eventos dos nós, batalhas e saída para a cidade.

Sequências reproduzidas da captura oficial (``docs/tutorial.md``). O roteiro de cada nó está em
``ARRIVE_PLOT``/``CALLBACKS``/``WIN_UNLOCKS``; o conteúdo (nós, tropas, falas) em ``content``.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from ...content import dungeon, tutorial
from ...domain.models import Item, Quest
from ...protocol.messages import wartune_pb2 as pb
from ...protocol.registry import Direction
from .. import drops, rewards, rules, space
from ..battle import Battle, PlayerHero
from ..builders import login as b
from ..builders.army import castle_pawns
from ..builders.player import item_moved, quest_update
from ..campaign import (
    AGGRESSIVE,
    DISAPPEAR_DELAY,
    DONE,
    DUNGEON_FIRST,
    DUNGEON_SECOND,
    FIGHTING,
    FIRST_MAP,
    FLICKER_DELAY,
    HIDDEN,
    MONSTER,
    NORMAL,
    PANDORA,
    PET_ISLANDS,
    SECOND_MAP,
    CampaignMap,
    battle_spec,
    group_of,
    map_for,
    unlock_actions,
)
from ..castle import castle_yield
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
S_CONFIRM, S_NOTIFY, S_CARDS, S_REPORT, S_RANK = 29, 126, 135, 137, 4151
S_STANDPOS, S_FOG_UPDATE, S_TAKE_CARD = 4126, 19, 26

ENTER, PORTAL_ENTER = 1, 3  # RoomCreatedMsg.createdType
ARMY_IDLE, ARMY_FIGHTING = 0, 2
SCENE = "CAMPAIGN_MAP_SCENE"
BACK_TO_MAP = 4  # LoginStateMsg.state que o cliente manda ao voltar para o mapa
OUTER_CITY = 3  # LoginStateMsg.state: entrou na cidade externa
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
    msg.param1 = int(node.get("param1", 0)) if _map(s).dungeon else 0  # masmorra: 1 nos lobos do 1021, 500 no baú
    if fresh:
        msg.sonType = node["sonType"]
    _send(s, S_NODE, msg)


def _send_plot(s: GameSession, entry: dict[str, Any]) -> None:
    cls = s.ctx.registry.message_type(S_PLOT, Direction.SERVER_TO_CLIENT)
    assert cls is not None
    msg = ParseDict(entry["plot"], cls())
    nick = s.snapshot.character.nickname if s.snapshot else ""
    for info in getattr(msg, "info", []):
        if info.roleName == "{nick}":
            info.roleName = nick or ""
    _send(s, S_PLOT, msg, extend2=entry["extend2"])


def _plot(s: GameSession, index: int) -> None:
    _send_plot(s, tutorial()["plots"][index])


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
    if c is None or node is None or node["state"] != NORMAL or c.fighting or c.locked(msg.paraInt1):
        return
    camp = msg.paraInt1
    if c.dungeon:
        await _dungeon_arrive(s, camp, node)
        return
    if camp in ARRIVE_PLOT:
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


def player_hero(s: GameSession, spec: dict[str, object]) -> PlayerHero:
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
    spec = battle_spec(camp)
    assert spec is not None
    c.fighting = camp
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    _send(s, S_ARMY_POS, _army_brief(s, ARMY_FIGHTING))
    _node_update(s, camp, FIGHTING, user=True)

    async def finished(battle: Battle, won: bool) -> None:
        await _battle_over(s, battle, camp, won)

    s.battle = Battle(spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished)
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
        s.battle, s.hero_sp = None, battle.player_sp
        _send(s, S_BATTLE_REPORT, _report(battle, won, 0))
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))

    s.battle = Battle(spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished)
    s.log.info("batalha do chefe", battle=s.battle.id)
    s.battle.start()


def _report(battle: Battle, won: bool, gp: int, strategy: int = 0) -> pb.BattleReportMsg:
    report = pb.BattleReportMsg(battleResult=WON if won else LOST, strategyBonus=strategy, gpBonus=gp)
    report.battleScene = int(battle.spec.get("battleScene", CAMPAIGN_SCENE))
    report.failCount, report.goldBonus, report.petGpBonus = 0, 0, 0
    return report


async def _battle_over(s: GameSession, battle: Battle, camp: int, won: bool) -> None:
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    s.battle, s.hero_sp = None, battle.player_sp
    gp = int(battle.spec.get("gpBonus", 0)) if won else 0
    strategy = int(battle.spec.get("strategyBonus", 0)) if won else 0
    if gp:
        rules.add_gp(snap, s.ctx.templates, gp)
    snap.character.strategy += strategy  # "Ruh" do chefe: (visto) captura #1711, strategyBonus 72
    loot = _Loot()
    if won and s.campaign is not None and s.campaign.dungeon:
        loot = _dungeon_loot(s, battle, camp)  # antes do await: drop, missão e EXP numa save só
    if gp or strategy or loot.items or loot.quests or loot.end_quests:
        await s.ctx.characters.save(snap.character, snap.leader, *loot.items, *loot.quests, *loot.end_quests)
    s.battle_gp = gp
    await _push_player(s)
    _send(s, S_BATTLE_REPORT, _report(battle, won, gp, strategy))
    if gp:
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"{gp} EXP kazanıldı"))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    if s.campaign is None:
        return
    c = s.campaign
    c.fighting = 0
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))
    if not won:
        _node_update(s, camp, NORMAL)
        return
    if loot.items:  # (visto) captura #1360-#1374 e #1442-#1457: o drop sai antes do 128
        _send(s, S_ITEMS, rewards.items_msg(loot.items, s.player_id))
    for text in loot.texts:
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if loot.quests:
        _send(s, S_QUESTS, quest_update(loot.quests, rules.quest_bitmap(snap)))
    _node_update(s, camp, DONE, fresh=True)
    if c.dungeon:  # a masmorra manda o 4382 logo depois do 128 (replay #1060, #1720), não na volta do 5035
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=gp, gold=0, strategy=strategy))
        s.battle_gp = 0
        if _map_finished(c, camp):
            _dungeon_end(s)
            if loot.end_quests:  # (visto) captura #1215 -> #1222: o 112 do 14 sai depois do 137
                _send(s, S_QUESTS, quest_update(loot.end_quests, rules.quest_bitmap(snap)))
        else:
            _dungeon_unlock(s, camp)
        return
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
    if msg.state == BACK_TO_MAP and s.campaign is not None and s.campaign.map_id in PET_ISLANDS:
        _send(s, S_ROOM_ENTER, _room_enter(s))  # o oficial repete o 21 quando a cena termina (peri_adasi_tp #7)
    if msg.state == BACK_TO_MAP and s.battle_gp:
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=0))
        s.battle_gp = 0
    if msg.state == OUTER_CITY and s.outer_fight_over:  # replay #750 e #803: depois da luta da mina
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=0, gold=0, strategy=0))
        s.outer_fight_over = False


# -- masmorra Kurt İni (campanha 1001) --------------------------------------------------------
# Conteúdo em content/dungeon_1001.json (tools/extract_dungeon.py). Dois mapas, 1011 e 1021, cada um
# com lobos (grupo em param3), uma caixa Pandora (29, 5033) e baús de ouro. Ao cair o grupo, o
# param4 esconde ou libera nós; sem param4 o mapa acaba (fim: 137 ... 140; a carta sai no 5122, com 134).
DUNGEON_CAMPAIGN = 1001
DUNGEON_WEARY = 20  # (visto) Beden gasto por mapa ("20 can kullanıldı", #918 e #1320); nenhuma coluna do template


@router.on(5039)
async def dungeon_enter(s: GameSession, _: object) -> None:
    """Começa a masmorra no 1011; com o 1011 vencido, o 5039 leva ao 1021 (replay #908 e #1212).

    (dedução) vencido o 1021, o 5039 começa de novo no 1011: a captura não mostra repetição.
    """
    c = s.campaign
    snap = s.snapshot
    if snap is None or (c is not None and c.dungeon and not c.finished):
        return  # já está na masmorra
    if snap.character.weary < DUNGEON_WEARY:
        # ponytail: sem energia não entra e não responde; a recusa do oficial precisa de captura com Beden < 20
        s.log.info("5039 sem energia", weary=snap.character.weary)
        return
    snap.character.weary -= DUNGEON_WEARY  # antes do await: um 5039 repetido já vê o mapa novo
    _enter_dungeon(s, DUNGEON_SECOND if c is not None and c.dungeon and c.map_id == DUNGEON_FIRST else DUNGEON_FIRST)
    # (visto) 3 com weary 200 -> 180 -> 160 e 83 depois do 138/143 em cada mapa (replay #917-#918, #1319-#1320)
    await _push_player(s)
    name = (s.ctx.templates.get("Campaigns", DUNGEON_CAMPAIGN, key="CampaignId") or {}).get("CampaignName", "")
    _send(
        s,
        S_CHAT,
        pb.ChatChannelMsg(channel=3, encodeMsg=f"[{name}] haritasına girildi, {DUNGEON_WEARY} can kullanıldı."),
    )
    await s.ctx.characters.save(snap.character)


def _enter_dungeon(s: GameSession, map_id: int) -> None:
    s.campaign = CampaignMap.enter_dungeon(map_id)
    room = pb.RoomCreatedMsg(createdType=ENTER)
    room.room.campaignId = map_id
    _send(s, S_ROOM_CREATED, room)
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    _send(s, S_ROOM_ENTER, _room_enter(s))
    _send(s, S_NODES, s.campaign.node_list())
    _send(s, S_FOG, s.campaign.fog())
    _send(s, S_MOVIE, pb.PlayerMovieMsg(movieTargetType=3, targetId=0, movieType="MOVIE_MAP_NAME", delay=0))
    if map_id == DUNGEON_FIRST:
        _send_plot(s, dungeon()["plots"][0])  # diálogo da entrada (138 no #916)


async def _dungeon_arrive(s: GameSession, camp: int, node: dict[str, Any]) -> None:
    c = _map(s)
    spec = battle_spec(camp)
    if spec is not None:  # (visto) o chefe 102109 é masterType 41, não 42: vale ter luta no ``battles``
        _start_battle(s, camp)
    elif node["masterType"] == PANDORA and node.get("param3"):
        confirm = dungeon()["maps"][str(c.map_id)]["pandora"]["confirm"]
        _send(s, S_CONFIRM, ParseDict(confirm, pb.CampaignConfirmMsg()))
    elif str(camp) in dungeon()["chests"]:
        await _gold_chest(s, camp)


async def _gold_chest(s: GameSession, camp: int) -> None:
    snap = s.snapshot
    assert snap is not None
    chest = dungeon()["chests"][str(camp)]
    snap.character.gold += int(chest["gold"])  # antes de qualquer await: o único save é no fim
    # (visto) 109, 126 ou 111, 128, 83 (replay #1020-#1023, #1409-#1413; sem 126, #1475-#1477 sem espaço)
    castle_yield(s)
    text = chest["notify"] or f"Kazanılan:Altın {chest['gold']}"
    if chest["notify"]:
        _send(s, S_NOTIFY, pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=text, delay=0))
    else:
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    _node_update(s, camp, DONE)
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    await s.ctx.characters.save(snap.character)


def _buffers(s: GameSession) -> pb.CampaignBufferMsg:
    return pb.CampaignBufferMsg(
        armyId=s.player_id, bufferInfo=[pb.BufferInfoMsg(bufferTempId=b, leftTime=0) for b in _map(s).buffs]
    )


@router.on(5033)
async def pandora_confirm(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Abre a caixa Pandora (CampaignConfirmMsg 29 -> 5033): buff sorteado, nó vira DONE (replay #1120, #1563).

    (visto) a posição do 4126 é a do nó + 2 nos dois Pandoras da captura (24,24 -> 26,26).
    """
    c = s.campaign
    if c is None or not c.dungeon or not msg.paraBool1:
        return
    node = c.node(msg.paraInt2)
    pandora = dungeon()["maps"][str(c.map_id)].get("pandora", {})
    confirm = pandora.get("confirm", {})
    if node is None or node["state"] != NORMAL or c.fighting or msg.paraInt2 != confirm.get("nodeId"):
        return
    if msg.paraInt1 != confirm.get("mapId"):
        return
    snap = s.snapshot
    assert snap is not None
    c.buffs.append(int(pandora["buff"]))
    # (visto) 4126, 4165, 150, 150, 128, 111, 83 nas duas caixas (replay #1155-#1161, #1623-#1630)
    _send(s, S_STANDPOS, pb.StandPosMsg(id=s.player_id, posX=node["posX"] + 2, posY=node["posY"] + 2))
    _send(s, S_BUFFERS, _buffers(s))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _node_update(s, msg.paraInt2, DONE)
    _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=pandora["alert"]))
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=pandora["alert"]))


@router.on(5180)
async def campaign_finish(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Quadro das cartas fechado: ``paraInt1`` 1 = sair, 2 = de novo (cliente: ChestFrame.dispose/campaignAgain).

    Sem efeito: a resposta do oficial não dá para separar no relay (o S>C chega atrasado). O mapa vencido
    fica em ``s.campaign`` para o próximo 5039 levar ao 1021.
    """
    s.log.info("5180 sem efeito", p1=msg.paraInt1)


def _map_finished(c: CampaignMap, camp: int) -> bool:
    """O mapa acabou com a vitória do nó ``camp``. Lobos: só ao cair o grupo todo, e sem ``param4`` (que libera
    ou esconde nós). Chefe (sem grupo) acaba o mapa. O nó ``camp`` conta como vencido mesmo antes do 128.
    """
    node = c.node(camp)
    assert node is not None
    group = group_of(node)
    if not group:
        return True  # chefe (102109): a última luta do 1021
    if any(c.nodes[g]["state"] != DONE and g != camp for g in group):
        return False
    # (visto) captura #1186 -> #1215: o último lobo do 1011 (101109) não tem param4, o mapa acaba
    return not unlock_actions(node)


def _dungeon_unlock(s: GameSession, camp: int) -> None:
    """Grupo de lobos caído com ``param4`` (visto) captura #1593-#1605: aviso, depois esconde (0) ou mostra (1) o nó."""
    c = _map(s)
    node = c.node(camp)
    assert node is not None
    if any(c.nodes[g]["state"] != DONE for g in group_of(node)):
        return  # ainda há lobo de pé
    actions = unlock_actions(node)
    notice = dungeon()["notices"].get(str(c.map_id))
    if actions and notice:
        _send(s, S_NOTIFY, pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=notice, delay=0), extend2=25)
    for target, action in actions:
        t = c.node(target)
        assert t is not None
        if action == 0:  # DISAPPEARD: o gatilho some (replay #1595)
            movie = pb.PlayerMovieMsg(
                movieTargetType=0, targetId=t["nodeId"], movieType="DISAPPEARD", delay=DISAPPEAR_DELAY
            )
            _send(s, S_MOVIE, movie, extend2=DISAPPEAR_DELAY)
            t["state"] = HIDDEN
        else:  # FLICKER e 128 com o nó novo: o chefe aparece (replay #1597, #1605)
            movie = pb.PlayerMovieMsg(movieTargetType=0, targetId=t["nodeId"], movieType="FLICKER", delay=FLICKER_DELAY)
            _send(s, S_MOVIE, movie, extend2=FLICKER_DELAY)
            _node_update(s, target, NORMAL, fresh=True)


@dataclass
class _Loot:
    """O que uma vitória na masmorra dá: itens novos (já no snapshot), textos e missões que avançaram.

    ``end_quests`` são as que fecham no fim do mapa (14 e 31): o 112 delas sai depois do 137 do fim.
    """

    items: list[Item] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    quests: list[Quest] = field(default_factory=list)
    end_quests: list[Quest] = field(default_factory=list)


def _dungeon_loot(s: GameSession, battle: Battle, camp: int) -> _Loot:
    """Efeitos de uma vitória na masmorra que mudam o snapshot. Chamado antes de qualquer await.

    - Drop do nó (``dungeon()["drops"]``, ``tools/extract_dungeon.py``): (visto) captura #1355-#1377 (102102:
      Kurt Dişi x2 e Şans Taşı x1), #1442-#1457 (102103: x2), #1520-#1536 (102105: x3), #1578-#1592 (102106: x3).
      O chefe 102109 e os lobos do 1011 não deram item na captura. (dedução) sem chance: sai sempre.
    - Missões: condição 25 soma 1 por soldado inimigo morto do tipo ``tempId`` (PawnTempInfos); 26 conta o chefe
      morto (``heroTempId``, ex. 1011 'Çene'). No fim do mapa, 14 (passou a campanha) e 31 (cena com a
      ``Capacity`` da campanha), em ``end_quests``. (visto) captura #1215 -> #1222: o 112 do 14 sai depois do 137
      do 1011. (dedução) 14 e 31 contam em todo mapa: o 31 soma, então um 1001 inteiro dá 2.
    """
    c = _map(s)
    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    loot = _Loot()
    drops_here = [(int(t), int(n)) for t, n in dungeon().get("drops", {}).get(str(camp), [])]
    if drops_here and rewards.can_grant(snap, templates, drops_here):
        loot.items, _ = rewards.grant(snap, templates, drops_here)
        loot.texts = [rewards.text(templates, [d]) for d in drops_here]  # um aviso por item, como o oficial
    kills = Counter(int(x["tempId"]) for x in battle.spec["soldiers"] if int(x["side"]) == 2)
    events = [(rules.PAWN_KILL_CONDITION, t, n) for t, n in kills.items()]
    events += [(rules.HERO_KILL_CONDITION, int(h["tempId"]), 1) for h in battle.spec["heroes"] if int(h["side"]) == 2]
    for kind, para1, value in events:
        for q in rules.quest_event(snap, templates, kind, para1, value):
            if q not in loot.quests:
                loot.quests.append(q)
    if _map_finished(c, camp):
        campaign = templates.get("Campaigns", DUNGEON_CAMPAIGN, key="CampaignId") or {}
        end = [
            (rules.CAMPAIGN_CONDITION, DUNGEON_CAMPAIGN, 1),
            (rules.SOLO_CONDITION, int(campaign["Capacity"]), 1),
        ]
        for kind, para1, value in end:
            for q in rules.quest_event(snap, templates, kind, para1, value):
                if q not in loot.end_quests:
                    loot.end_quests.append(q)
    loot.quests = [q for q in loot.quests if q not in loot.end_quests]  # quem fecha no fim do mapa sai uma vez só
    return loot


def _dungeon_end(s: GameSession) -> None:
    """Fim do mapa: relatório e as 5 cartas viradas (replay #1215-#1226 e #1722-#1729); a carta sai no 5122.

    (visto) o 20 no meio do fim do 1011 (#1218) é a resposta do 5038 (#1165), que o cliente manda depois de
    toda luta (um 20 para cada 5038); no fim do 1021 o 20 (#1718) sai antes do 4382.
    """
    c = _map(s)
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    data = dungeon()["maps"][str(c.map_id)]
    c.finished = True
    _send(s, S_REPORT, ParseDict(data["report"], pb.CampaignReportMsg()))
    _send(s, S_RANK, ParseDict(data["rank"], pb.RankListRspMsg()))
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=data["exp_text"]))
    _send(s, S_CARDS, ParseDict(data["cards"], pb.CampaignCardsMsg()))
    c.buffs = []
    _send(s, S_BUFFERS, _buffers(s))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))


@router.on(5122)
async def take_card(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Vira a carta ``paraInt2`` do 135: item de ``drops.card`` gravado, 115, 26, 83 e 134 (replay #1227-#1243).

    (cliente) ChestFrame.as: o 5122 só sai do clique numa carta do 135 (``__clickHandler``) ou do
    ``autoChest`` (``isPay`` true) quando o tempo acaba; 8 s depois do 26 o quadro fecha e manda o 5180(1).
    (visto) o 5122 no relay (#1166) aparece antes do fim (#1215) só porque o S>C do relay chega atrasado:
    o 10007 da luta 4c4d40c7 (#1153) vem antes do 157 dela (#1186).
    """
    c = s.campaign
    snap = s.snapshot
    if c is None or snap is None or not c.dungeon or not c.finished or c.card is not None:
        s.log.info("5122 sem carta para virar", p2=msg.paraInt2)
        return  # fora do fim da masmorra, ou a carta já saiu: uma só por mapa
    count = int(dungeon()["maps"][str(c.map_id)]["cards"].get("cardCount", 0))
    if not 0 <= msg.paraInt2 < count:
        return
    # ponytail: carta paga (isPay, autoChest) tratada como a grátis: price 0 e uma só por mapa; cartas
    # pagas extras (payCardCount 5) precisam de captura de quem paga
    c.card = msg.paraInt2  # antes do await: um segundo 5122 já cai no ``c.card is not None``
    grant = drops.card(snap, s.ctx.templates, DUNGEON_CAMPAIGN, msg.paraInt2)
    if grant is not None:
        item, take, text = grant
        await s.ctx.characters.save(snap.character, item)  # um save: carta na mochila
        _send(s, S_ITEMS, rewards.items_msg([item], s.player_id))
        _send(s, S_TAKE_CARD, take)
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _send(s, S_CAMPAIGN_FINISH)  # mochila cheia: sem carta, mas o 134 fecha o quadro


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
