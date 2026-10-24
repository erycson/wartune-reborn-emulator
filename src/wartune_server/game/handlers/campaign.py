"""Campanha de treino: entrar no mapa, andar, eventos dos nós, batalhas e saída para a cidade.

Sequências reproduzidas da captura oficial (``docs/tutorial.md``). O roteiro de cada nó está em
``ARRIVE_PLOT``/``CALLBACKS``/``WIN_UNLOCKS``; o conteúdo (nós, tropas, falas) em ``content``.
"""

from __future__ import annotations

import random
import uuid
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from ...content import tutorial
from ...domain.models import EventState, Item, PlayerSnapshot, Quest
from ...protocol.messages import wartune_pb2 as pb
from ...protocol.registry import Direction
from ...templates.repository import GameTemplates
from .. import bag, buffs, drops, events, outer_city, rewards, rules, space
from .. import campaign as cm
from ..battle import STATS, Battle, PlayerHero
from ..builders import login as b
from ..builders.army import castle_pawns
from ..builders.player import item_moved, quest_update
from ..campaign import (
    AGGRESSIVE,
    BOSS,
    COLLECT,
    DISAPPEAR_DELAY,
    DONE,
    FAM_MAP,
    FIGHTING,
    FIRST_MAP,
    FLICKER_DELAY,
    HIDDEN,
    MONSTER,
    NORMAL,
    PANDORA,
    PET_ISLANDS,
    SECOND_MAP,
    SHOW,
    CampaignMap,
    StageRun,
    battle_spec,
    group_of,
    map_for,
    unlock_actions,
)
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from . import pet_defend
from .login import army, player_info

S_PLAYER, S_NOVICE, S_ARMY_PAWN = 3, 1, 100
S_CHAT, S_ALERT = 83, 111
S_ROOM_ENTER, S_ROOM_CREATED, S_NODES, S_NODE, S_FOG, S_ARMY_POS = 21, 125, 127, 128, 130, 131
S_PLOT, S_MAP_SYNC, S_CAMERA, S_MOVIE, S_CAMPAIGN_FINISH = 138, 140, 142, 143, 134
S_BATTLE_REPORT, S_NPC_CHASE, S_NPC_MOVE, S_ESCORT, S_PLAYER_MOVE = 4103, 4105, 4122, 4124, 4162
S_BUFFERS, S_NODE_STAND, S_FIGHT_MOVIE = 4165, 4208, 4382
S_FULL_ARMY, S_QUESTS, S_ITEMS = 150, 112, 115
S_CONFIRM, S_NOTIFY, S_CARDS, S_REPORT, S_RANK = 29, 126, 135, 137, 4151
S_STANDPOS, S_FOG_UPDATE, S_TAKE_CARD, S_EXIT = 4126, 19, 26, 22

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
SPECIAL_BOSS = "8251"  # chave em tutorial.json["battles"]


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
    full, _fighting = army(s, snap)
    full.mountTempId, full.petTempId, full.petQuqlity, full.petName = 0, 0, 0, ""  # a campanha manda vazio
    a = b.brief_army(full, rules.job_type(snap.character.job), snap.leader.template_id, state)
    return pb.MapUpdatedMsg(updatedType=3, army=a)


def _room_enter(s: GameSession) -> pb.RoomEnterMsg:
    snap, c = s.snapshot, _map(s)
    assert snap is not None
    return pb.RoomEnterMsg(
        result=1, player=[space.room_player(snap, s.ctx.templates, c.pos, c.map_id, s.ctx.clock.now())]
    )


def _escort(s: GameSession) -> None:
    c = _map(s)
    if c.escort:
        x, y = c.pos
        _send(s, S_ESCORT, pb.NPCFollowMsg(escortId=c.escort, followId=s.player_id, curPosX=x + 1, curPosY=y + 1))


def _node_update(
    s: GameSession, camp: int, state: int, *, user: bool = False, fresh: bool = False, visited: bool = False
) -> None:
    """128. ``user``: nó em combate com este jogador; ``fresh``: nó novo (uuid e sonType); ``visited``: caixa já
    aberta por este jogador (``visitUserIds``, #2401 e #2876)."""
    node = _map(s).node(camp)
    assert node is not None
    node["state"] = state
    msg = pb.CampaignNodeUpdateMsg(nodeId=node["nodeId"], nodeState=state)
    if user:
        msg.userId = s.player_id
    if visited:
        msg.visitUserIds.append(s.player_id)
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
    me = s.snapshot.character if s.snapshot else None
    for info in getattr(msg, "info", []):
        if info.roleName == "{nick}":
            info.roleName = (me.nickname if me else None) or ""
            if me:
                info.roleId = me.job  # retrato de quem fala: o oficial manda o job (3: tutorial_en #2317)
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
    if c.hook:
        from .hangup import arrive as hook_arrive  # hangup importa player, que importa login, que importa este módulo

        hook_arrive(s, node)
        return
    if c.fam:
        from . import fam  # fam importa este módulo

        await fam.arrive(s, camp, node)
        return
    if c.world_boss:
        from .worldboss import boss_attack  # worldboss importa este módulo

        await boss_attack(s)
        return
    if c.content is not None:
        await _dungeon_arrive(s, camp, node)
        return
    if c.map_id in PET_ISLANDS:
        if node["masterType"] == pet_defend.RIOT:
            await pet_defend.attack(s, camp, node)
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
    if c.content is not None:
        await _dungeon_callback(s, camp)
        return
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
        item = Item(s.player_id, template_id, pos=rules.free_bag_pos(snap))
        item.random_skills = bag.roll_random_skills(s.ctx.templates, template_id)
        snap.items.append(item)
        await s.ctx.characters.save(item)
        _send(s, S_ITEMS, item_moved(item.bag_type, 0, item.pos, item, s.player_id))
        # (visto) inglesa #362 "Received: Templar Priest Staff"
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Received: {row.get('TemplateName', '')}"))
    _node_update(s, CHEST, DONE)
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))


async def _leave_campaign(s: GameSession) -> None:
    assert s.snapshot is not None
    _send(s, S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    _send(s, S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]))  # (visto) tutorial_en #517-#520: 4165, 150, 150, 140
    _send(s, S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    from . import events as hev  # handlers.events importa login, que importa este módulo

    await hev.leed_done(s, hev.CAMPAIGN_LEED)  # (visto) tutorial_en #520-#523: 140, 4152 (leed 4), 83, 134
    # (visto) oficial_encantar #694-#706: o 4638 vem logo depois do 4152 (e mais 5 cópias iguais depois do 83); aqui
    # vai um, depois do 83
    hev.send_serven(s)
    _send(s, S_CAMPAIGN_FINISH)
    s.campaign = None


# -- batalha -----------------------------------------------------------------------------------


def boosted(s: GameSession) -> bool:
    """O buff do contrato 7 vale nesta luta: masmorra, Catacombs ou Necropolis (``rules.BOOST_TYPES``)."""
    c, snap = s.campaign, s.snapshot
    if c is None or c.run is None or snap is None:
        return False
    kind = int(_campaign_row(s, c.run.campaign_id).get("Types") or -1)
    return kind in rules.BOOST_TYPES and events.has_contract(snap, rules.BOOST_CONTRACT, s.ctx.clock.now())


def _boost(value: int) -> int:
    return value * (100 + rules.BOOST_PCT) // 100


def player_hero(s: GameSession, spec: dict[str, object], boost: bool = False) -> PlayerHero:
    """``boost``: o buff do contrato 7 (+10% nos ataques, defesas, vida e tropa; ``boosted``). (dedução) a vida
    atual ganha o mesmo tanto que a máxima."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    leader = snap.leader
    stats = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now())
    total, live = dict(stats.total), stats.live
    hp = b.hero_hp(leader, live)
    if boost:
        total.update({k: _boost(int(total.get(k, 0))) for k in STATS})
        live, hp = _boost(live), hp + _boost(live) - live
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
        pos=outer_city.hero_pos(leader.fight_pos) if player["pos"] == outer_city.FRONT_HERO_POS else player["pos"],
        maxHp=live,
        initHp=hp,
        hp=hp,
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
        pawnTempId=int(player.get("pawnTempId", 0)),  # tutorial_en #727: a tropa que luta junto (cidade externa)
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
    runes = rune_skills(leader.rune_key, s.ctx.templates)
    msg.skillId.extend(runes)
    army, _ = outer_city.army_soldiers(snap, s.ctx.templates)
    if boost:
        for unit in army:
            unit["initHp"] = unit["hp"] = _boost(int(str(unit["hp"])))
    return PlayerHero(
        msg,
        total,
        int(tpl_row.get("DefaultSkill", 0)),
        passives=passive_skills(snap, s.ctx.templates),
        army=tuple(army),
        once=frozenset(runes),
    )


def rune_skills(rune_key: str, templates: GameTemplates) -> list[int]:
    """Runas equipadas (``runeKey`` "204,-1,") viram skills ativas do herói: RuneTempInfos.SkillTemplateId
    (9204 "Can only be used 1 time per battle", UseCount 1). (dedução) entram no ``skillId`` do 157 no fim."""
    rows = (templates.get("RuneTempInfos", k) for k in rune_key.split(",") if k and k != "-1")
    return [int(r["SkillTemplateId"]) for r in rows if r and int(r.get("SkillTemplateId") or 0)]


def passive_skills(snap: PlayerSnapshot, templates: GameTemplates) -> tuple[int, ...]:
    """Passivas fora da lista de skills: talento (``talent_script``, SkillTempInfo MasterType 10, UseWay 2) e
    destino (skill do SonType no grau, como o 4544). Os BufferIds delas viram buffers no 157 (dedução: o
    tutorial só mostra a passiva 30111 da lista de skills). Alma do dragão e cartas: sem tabela, ver batalha.md."""
    from . import systems  # systems importa este módulo

    leader = snap.leader
    assert leader is not None
    skills = [int(x) for x in leader.talent_script.split(",") if x]
    for son_type, gp in systems.fate(rules.systems(snap)).items():
        row = next(templates.find("SkillTempInfos", SonType=son_type, Grades=systems.fate_grade(templates, gp)), None)
        if row is not None:
            skills.append(int(row["TemplateId"]))
    return tuple(skills)


def _start_battle(s: GameSession, camp: int, over: Callable[[Battle, bool], Awaitable[None]] | None = None) -> None:
    """140, 131, 128 (em combate) e o 157. ``over``: o fim da luta no lugar do ``_battle_over`` (terra secreta)."""
    c = _map(s)
    spec = c.battle_like(camp) if c.content is not None else battle_spec(camp)
    assert spec is not None
    c.fighting = camp
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    _send(s, S_ARMY_POS, _army_brief(s, ARMY_FIGHTING))
    _node_update(s, camp, FIGHTING, user=True)

    async def finished(battle: Battle, won: bool) -> None:
        await (over(battle, won) if over is not None else _battle_over(s, battle, camp, won))

    s.battle = Battle(
        spec,
        player_hero(s, spec, boosted(s)),
        s.ctx.templates,
        s.ctx.clock,
        s.send,
        finished,
        settings=s.ctx.world.settings,
    )
    s.log.info("batalha", nó=camp, battle=s.battle.id)
    s.battle.start()


@router.on(8251)
async def special_boss(s: GameSession, _: object) -> None:
    """Fim do tutorial na cidade externa: retomar o castelo dos Tauren (sem nó de campanha)."""
    if s.battle is not None:
        return
    spec = tutorial()["battles"][SPECIAL_BOSS]
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))  # o oficial manda duas vezes

    async def finished(battle: Battle, won: bool) -> None:
        s.battle, s.hero_sp = None, battle.player_sp
        s.outer_fight_over = True  # tutorial_en #576-#577: o 4382 sai na volta ao castelo (8747)
        _send(s, S_BATTLE_REPORT, _report(battle, won, 0))
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))

    s.battle = Battle(
        spec,
        player_hero(s, spec, boosted(s)),
        s.ctx.templates,
        s.ctx.clock,
        s.send,
        finished,
        settings=s.ctx.world.settings,
    )
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
    # EXP Boost (2013001-4): o gpBonus capturado é a base; o 4103, o 83 e o 4382 levam a EXP com o bônus (dedução)
    gp = buffs.boost(gp, snap, buffs.EXP_BOOST, s.ctx.clock.now())
    before = snap.character.grades
    if gp:
        rules.add_gp(snap, s.ctx.templates, gp)
    loot = _Loot()
    dungeon = s.campaign is not None and s.campaign.dungeon
    # tropas mortas saem e a reserva repõe (visto #1466 -> #1511: a reserva 738 -> 650); a luta roteirizada não perde
    undying = bool(battle.spec.get("undying"))
    hit = None if undying else outer_city.lose_troops(snap, s.ctx.templates, battle.troops())
    # Daru = soldados perdidos, ganhando ou perdendo: (visto) inglesa #1466 (88 mortos, Wulfgar 88) e
    # oficial_20261023-153200-1 (a reserva cai 127, 98, 115, 121; derrotas 53, 202, 202 = o exército inteiro)
    strategy = hit[1] if hit is not None else int(battle.spec.get("strategyBonus", 0)) if won and undying else 0
    snap.character.strategy += strategy
    if not won:
        s.fail_count += 1
    if hit is not None:
        outer_city.refill(*hit)
    from .player import hero_after_fight, hp_pack  # player importa login, que importa este módulo

    healed = hero_after_fight(s, battle.player.hp if battle.player is not None else None)
    if dungeon:
        loot = _dungeon_loot(s, battle, camp, won)  # antes do await: drop, missão e EXP numa save só
    if gp or strategy or loot.items or loot.quests or loot.end_quests or loot.win or hit:
        await s.ctx.characters.save(
            snap.character, snap.leader, *snap.pawns, *loot.items, *loot.quests, *loot.end_quests
        )
    s.battle_gp = 0 if dungeon else gp  # a masmorra guarda o 4382 no mapa (``over``), com o Daru do chefe
    # masmorra: (visto) oficial_20261023-171155-1 #5318-#5325, #5532-#5543, #5780-#5790 (1004) e #2096-#2106 (1003):
    # 109 com a população depois das baixas, 3, o 83 da poção de vida, outro 3 com a EXP, 4103, 150, 100, 140, os
    # itens (115, 111) e o 112, 131, 128 e por fim o 83 da EXP; a última luta leva ``petGpBonus`` -1 (também na
    # tutorial_en #1509, #2692, #3146). Na derrota o 83 da poção vem depois do 4103 (oficial_20261023-153200-1
    # #1446-#1457: 109, 3, 4103, 83, 150, 100, 140, 131, 128). Fora da masmorra fica a ordem da tutorial_en (#906-#914).
    if dungeon and hit is not None:
        castle_yield(s)
    await _push_player(s)
    if dungeon and won:
        hp_pack(s, healed)
        if gp:
            await _push_player(s)
    report = _report(battle, won, gp, strategy)
    report.failCount = s.fail_count
    if dungeon and loot.finished:
        report.petGpBonus = -1
    if loot.fallen:
        report.signId = loot.sign
        report.baseItem.extend(pb.BaseItemMsg(templateId=t, count=n) for t, n in loot.fallen)
    _send(s, S_BATTLE_REPORT, report)
    if not dungeon or not won:
        hp_pack(s, healed)  # (visto) oficial_20261023-153200-1 #1449-#1450
    if not dungeon and gp:  # (visto) inglesa #909 "Received 35 EXP " (com o espaço no fim)
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=_exp_text(gp)))
    if snap.character.grades > before:
        from .player import push_level  # player importa login, que importa este módulo

        push_level(s, before)  # (dedução) 139, 100, 150 e 4640 como na entrega de missão
    else:
        _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
        _send(s, S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    if s.campaign is None:
        return
    c = s.campaign
    c.fighting = 0
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    if not dungeon:
        _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))
    if dungeon:
        c.over = (gp, strategy)  # (visto) inglesa #1094-#1096: o 4382 sai na volta ao mapa (5035 state 4)
    if not won:
        if dungeon:
            _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))
        c.talked.discard(camp)  # tumba/caixa perdida: o 29 volta a perguntar (dedução, sem captura de derrota)
        _node_update(s, camp, NORMAL)
        return
    if loot.items:  # (visto) inglesa #1275-#1280: 115, 111, 128 e só depois o 83
        from . import events as hev  # handlers.events importa login, que importa este módulo

        _send(s, S_ITEMS, rewards.items_msg(loot.items, s.player_id))
        hev.items_gained(s)
    for text in loot.texts:
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    if loot.quests:
        _send(s, S_QUESTS, quest_update(loot.quests, rules.quest_bitmap(snap)))
    if dungeon:  # (visto) tutorial_en #1264-#1279: 140, 115, 111, 131, 128
        _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))
    if loot.win:  # caixa do caçador: (visto) inglesa #2630-#2644: 3, 126, os nós do param4 DONE, 83
        if loot.win_paid:
            await _push_player(s)
        _send(s, S_NOTIFY, pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=loot.win, delay=0))
        for done in loot.done:
            _node_update(s, done, DONE, fresh=True)
    else:
        _node_update(s, camp, DONE, fresh=True)
    if dungeon and gp:
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=_exp_text(gp)))
    for text in [*loot.texts, *([loot.win] if loot.win else [])]:
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if dungeon:
        if loot.finished:
            c.ending = loot.end_quests  # o fim (137 ...) vai junto do 4382
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
        # o oficial repete o 21 quando a cena termina (só turco: peri_adasi_tp #7)
        _send(s, S_ROOM_ENTER, _room_enter(s))
    if msg.state == BACK_TO_MAP and s.battle_gp:
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=0))
        s.battle_gp = 0
    c = s.campaign
    if msg.state == BACK_TO_MAP and c is not None and c.fam and not c.ready:
        from . import fam  # fam importa este módulo

        fam.show_room(s)
    if msg.state == BACK_TO_MAP and c is not None and c.over is not None:
        gp, strategy = c.over
        c.over = None
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=gp, gold=0, strategy=strategy))
        if c.ending is not None:
            await _dungeon_end(s)
    if msg.state == OUTER_CITY and s.outer_fight_over:  # tutorial_en #758 e #812: depois da luta da mina
        # o Daru das perdas: oficial_20261023-153200-1 #1636 (116), #1909 (201), #2017 (106)
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=0, gold=0, strategy=s.battle_strategy))
        s.outer_fight_over, s.battle_strategy = False, 0


# -- masmorras (1001, 1002) e pedreira (6001) ----------------------------------------------------
# Conteúdo no banco (``campaign_contents``, migração 0034, ``tools/extract_dungeon.py`` da captura inglesa): mapas,
# lutas, diálogos, baús, caixas, drops, portais e coleta. Cada campanha tem etapas (``stages``): 1001 = [1011], [1021];
# 1002 = [1131 -> 1132], [1141 -> 1142] (o portal 125 tipo 3 leva ao 2º mapa). Um 5039 abre a etapa da vez; o fim
# da etapa (137 ... 140) sai no último mapa, e a carta no 5122. Detalhes em docs/salas-campanha.md.
WEARY = 20  # (visto) "Entered [Worg Lair] and deducted 20 stamina." (inglesa #853, #2320); nenhuma coluna do template
STAGE_KEY = "campaign_stage:{}"  # EventState: índice da próxima etapa (#2310 e #2788 mandam o mesmo 5039)
RANK_KEY = "campaign_rank:{}"  # EventState: melhor nota total (4151)
MATERIAL = 210  # SonType que vai direto para a mochila (Worg Tooth, Wood; inglesa #1275, #2050); o resto cai num baú


def _exp_text(gp: int) -> str:
    return f"Received {gp:,} EXP "  # (visto) inglesa #909 e #1100 ("Received 630 EXP ", espaço no fim)


def _campaign_row(s: GameSession, campaign_id: int) -> Mapping[str, Any]:
    return s.ctx.templates.get("Campaigns", campaign_id, key="CampaignId") or {}


@router.on(5039)
async def dungeon_enter(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Entrar na masmorra ``paraInt2`` (``08 01 10 e9 07`` = {paraInt1: 1, paraInt2: 1001}).

    (visto) inglesa #843 -> #853: 125 tipo 1, 140, 21, 127, 130, 143, o 138 do mapa (se houver), 3 e o 83. A etapa
    vem do estado (``campaign_stage``): o mesmo pedido levou ao 1011 e depois ao 1021 (#843, #1151), ao 1131 e depois
    ao 1141 (#2310, #2788). (dedução) depois da última etapa volta à primeira.
    """
    from .vehicle import room_start  # vehicle importa player, que importa este pacote

    if await room_start(s):  # sala de veículo: o VehicleRoomFrame manda 5039 (0, 0) ao começar
        return
    if s.ctx.vehicles.queued(s.player_id) or s.ctx.vehicles.match_of(s.player_id):
        s.log.info("5039 recusado: na fila ou na batalha de veículos")
        return
    c, snap = s.campaign, s.snapshot
    content = s.ctx.world.campaigns.get(msg.paraInt2)
    if snap is None or content is None or s.battle is not None or (c is not None and not c.finished):
        s.log.info("5039 recusado", campanha=msg.paraInt2)
        return
    stages = content["stages"]
    if "fog" not in content["maps"][str(stages[0][0])]:
        return  # a pedreira entra pelo 8258
    if snap.character.weary < WEARY:
        # ponytail: sem energia não entra e não responde; a recusa do oficial precisa de captura com estamina < 20
        s.log.info("5039 sem energia", weary=snap.character.weary)
        return
    now = s.ctx.clock.now()
    stage = events.state(snap, STAGE_KEY.format(msg.paraInt2), now).value % len(stages)
    maps = tuple(int(m) for m in stages[stage])
    snap.character.weary -= WEARY  # antes do await: um 5039 repetido já vê o mapa novo
    _enter_dungeon(s, content, maps[0], StageRun(msg.paraInt2, stage, maps, now), ENTER)
    await _push_player(s)
    name = _campaign_row(s, msg.paraInt2).get("CampaignName", "")
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Entered [{name}] and deducted {WEARY} stamina."))
    await s.ctx.characters.save(snap.character)


def _enter_dungeon(s: GameSession, content: Mapping[str, Any], map_id: int, run: StageRun | None, created: int) -> None:
    s.campaign = c = CampaignMap.enter_dungeon(content, map_id, run)
    room = pb.RoomCreatedMsg(createdType=created)
    room.room.campaignId = map_id
    _send(s, S_ROOM_CREATED, room)
    if c.quarry:  # (visto) inglesa #1805-#1809: 125, 140, 140, 21, 127; sem névoa nem nome do mapa
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_ROOM_ENTER, _room_enter(s))
        _send(s, S_NODES, c.node_list())
    elif created == PORTAL_ENTER:  # (visto) inglesa #2503-#2508: 4208 (antes), 125 tipo 3, 127, 130, 21, 131
        _send(s, S_NODES, c.node_list())
        _send(s, S_FOG, c.fog())
        _send(s, S_ROOM_ENTER, _room_enter(s))
        _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))
    else:
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_ROOM_ENTER, _room_enter(s))
        _send(s, S_NODES, c.node_list())
        _send(s, S_FOG, c.fog())
        _send(s, S_MOVIE, pb.PlayerMovieMsg(movieTargetType=3, targetId=0, movieType="MOVIE_MAP_NAME", delay=0))
        if (plot := content["maps"][str(map_id)].get("plot")) is not None:
            _send_plot(s, plot)  # (visto) inglesa #850 (Dinah no 1011), #2317 (1131)


async def _dungeon_arrive(s: GameSession, camp: int, node: dict[str, Any]) -> None:
    c = _map(s)
    if c.quarry:  # (visto) inglesa #1841-#1843: a pilha responde 143 COLLECTION com o nodeId; o 5032 colhe
        if node["masterType"] == COLLECT:
            movie = pb.PlayerMovieMsg(movieTargetType=0, targetId=node["nodeId"], movieType="COLLECTION", delay=0)
            _send(s, S_MOVIE, movie)
        return
    if (target := c.part("portals", camp)) is not None:
        _send(s, S_NODE_STAND, pb.PlayerNodeStateMsg(mapId=c.map_id, nodeId=camp, isStand=True, armyId=s.player_id))
        assert c.content is not None
        _enter_dungeon(s, c.content, int(target), c.run, PORTAL_ENTER)
    elif (plot := c.part("plots", camp)) is not None:
        _send_plot(s, plot)  # Karlan (#2666-#2667, um 138 por 5125); a luta vem no 5032 do fim do diálogo
    elif (switch := c.part("switches", camp)) is not None and node["state"] == NORMAL:
        _switch(s, camp, node, switch)
    elif (confirm := _confirm(c, camp)) is not None:
        # (visto) inglesa #1428-#1429, #2397-#2398: 29 e 4126 na posição do nó + 2
        _send(s, S_CONFIRM, ParseDict(confirm, pb.CampaignConfirmMsg()))
        _send(s, S_STANDPOS, pb.StandPosMsg(id=s.player_id, posX=node["posX"] + 2, posY=node["posY"] + 2))
    elif c.battle(camp) is not None and node["masterType"] in (MONSTER, BOSS):
        _start_battle(s, camp)  # o chefe 102109/114206 é masterType 41, não 42
    elif (chest := _chest(c, camp)) is not None:
        await _gold_chest(s, camp, chest)


async def _dungeon_callback(s: GameSession, camp: int) -> None:
    """5032 (fim do diálogo ou clique na pilha). Masmorra: o chefe com diálogo começa a luta (#2668). Pedreira:
    colhe ``collect[sonType]`` = [item, mín, máx]. (visto) inglesa #1847-#1875: 115, 111, 83 "Received: Wood x2" a
    cada 5032, e a pilha nunca vira DONE.
    """
    c, snap = _map(s), s.snapshot
    node = c.node(camp)
    assert node is not None and snap is not None
    if not c.quarry:
        if node["state"] == NORMAL and not c.fighting and c.part("plots", camp) and c.battle(camp):
            _start_battle(s, camp)
        return
    collect = c.part("collect", node["sonType"])
    if node["masterType"] != COLLECT or collect is None:
        return
    # ponytail: colheita sem limite nem espera (a captura colheu duas vezes seguidas a mesma pilha, #1847 e #1861);
    # o limite do oficial, se houver, precisa de captura de quem colhe muito
    template_id, low, high = (int(x) for x in collect)
    got = [(template_id, random.randint(low, high))]  # (visto) x2 e x3 na captura
    now = s.ctx.clock.now()
    if not bag.fits(snap, s.ctx.templates, got, now):
        return
    items = bag.add(snap, s.ctx.templates, template_id, got[0][1], now)
    await s.ctx.characters.save(*items)
    text = rewards.received(s.ctx.templates, got)
    from . import events as hev  # handlers.events importa login, que importa este módulo

    _send(s, S_ITEMS, rewards.items_msg(items, s.player_id))
    hev.items_gained(s)
    _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


async def _gold_chest(s: GameSession, camp: int, chest: Mapping[str, Any]) -> None:
    snap = s.snapshot
    assert snap is not None
    got = [(int(t), int(n)) for t, n in chest["drops"]]
    rewards.grant(snap, s.ctx.templates, got)  # só moeda (Ouro); antes de qualquer await: o único save é no fim
    # (visto) inglesa #945-#948: 109, 126 (ou 111 sem aviso), 128, 83 "Received: 500 Gold"
    castle_yield(s)
    text = rewards.received(s.ctx.templates, got)
    if chest.get("notify"):
        _send(s, S_NOTIFY, pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=text, delay=0))
    else:
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    _node_update(s, camp, DONE)
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    await s.ctx.characters.save(snap.character)


def _chest(c: CampaignMap, camp: int) -> Mapping[str, Any] | None:
    """O baú de ouro do nó. O baú de bronze do 1011 (101104) nunca foi aberto na captura inglesa: (dedução) vale o
    de mesmo ``sonType`` de outro mapa (102104, 500 de ouro sem aviso, #1295), como a Pandora em ``_confirm``.
    """
    if (own := c.part("chests", camp)) is not None:
        return own  # type: ignore[no-any-return]
    node = c.node(camp)
    if node is None or node["masterType"] != PANDORA:
        return None
    for m in (c.content or {}).get("maps", {}).values():
        for n in m["nodes"]:
            same = c.part("chests", n["campDataId"])
            if same is not None and n["sonType"] == node["sonType"]:
                return same  # type: ignore[no-any-return]
    return None


def _buffs_of(node: Mapping[str, Any]) -> list[int]:
    """Buffs da caixa Pandora (``param3`` "1301|1701"); nas tumbas e caixas do 1002 o param3 é o texto da pergunta."""
    parts = str(node.get("param3", "")).split("|")
    return [int(x) for x in parts] if all(x.isdigit() for x in parts) else []


def _confirm(c: CampaignMap, camp: int) -> dict[str, Any] | None:
    """O 29 do nó (caixa Pandora, tumba, caixa do caçador), ou ``None``. Já aberta (``talked``) não pergunta mais.

    A Pandora do 1011 (101107) nunca foi aberta na captura inglesa: (dedução) vai o 29 da Pandora de mesmo
    ``sonType`` (102107) com o nó trocado; o ``mapId`` (1824) é só eco, o 5033 não é conferido por ele.
    """
    node = c.node(camp)
    if node is None or node["masterType"] != PANDORA or camp in c.talked:
        return None
    if (own := c.part("confirms", camp)) is not None:
        return dict(own["confirm"])
    if not _buffs_of(node):
        return None  # baú de ouro (param1 500)
    for m in (c.content or {}).get("maps", {}).values():
        for n in m["nodes"]:
            same = c.part("confirms", n["campDataId"])
            if same is not None and n["sonType"] == node["sonType"]:
                return {**same["confirm"], "nodeId": camp}
    return None


def _roll(c: CampaignMap, camp: int, own: Mapping[str, Any]) -> tuple[int, list[tuple[int, int]]]:
    """Desfecho de uma caixa: o ``param5`` do nó sorteado pelo peso (``cm.outcomes``); sem ele, uma das listas de
    ``pick`` por igual ou ``drops``; sem prêmio, a luta."""
    node = c.node(camp) or {}
    if outs := cm.outcomes(node):
        kind, drops, _ = random.choices(outs, weights=[w for *_, w in outs])[0]
        return kind, drops
    if own.get("pick"):
        return cm.OUT_ITEM, [(int(t), int(n)) for t, n in random.choice(own["pick"])]
    if own.get("drops"):
        return cm.OUT_ITEM, [(int(t), int(n)) for t, n in own["drops"]]
    return cm.OUT_FIGHT, []


def _buffers(s: GameSession) -> pb.CampaignBufferMsg:
    return pb.CampaignBufferMsg(
        armyId=s.player_id, bufferInfo=[pb.BufferInfoMsg(bufferTempId=b, leftTime=0) for b in _map(s).buffs]
    )


@router.on(5033)
async def campaign_confirm(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Resposta ao 29 (``paraInt2`` = nó, ``paraBool1`` = sim). Desfechos, pelo conteúdo do nó:

    - Pandora (buffs no param3): (visto) inglesa #1433-#1438: 4165 com o buff, 150, 150, 111, 128 DONE, 83
      "Received: Rage Boost". O buff é sorteado entre os do param3 (oficial_20261023-171155-1: 1701 e 1101 no 103110).
    - Caixa com prêmio de vitória (``wins``: caixas do caçador, mina 103105): sempre luta; o param5 é o prêmio dela.
    - Os outros sorteiam o desfecho (``_roll``: param5 do nó, ou ``pick``/``drops`` do conteúdo):
    - luta (tumba): 126 com o aviso se houver (#2400), 128 com ``visitUserIds``, luta.
    - moeda (tumba): (visto) #2874-#2877: 3, 126 "Received: 5,000 Daru", 128 state 1 visitado, 83.
    - caixa com chave (Mystery Box 103108, o 29 traz ``itemTempId``): gasta a chave; (visto)
      oficial_20261023-153200-1 #914-#918: 115 da chave, 109, 128 DONE (param1 -300), 111 e 83 "Received: 5,000
      Gold"; oficial_20261023-171155-1 #2538-#2552: 115, 128, 115 do item, 111 e 83 "Received: Lvl. 2 Luck Stone x2".
    - caixa paga com ouro (Silver Treasure Chest 105110: ``param1`` -100 e ``param2`` 1000 no nó): (visto)
      oficial_20261023-171155-1 #5608-#5627: 109 já sem o ouro, 128 DONE (param1 -100), 115 do item, 111 e 83
      "Received: Lvl. 1 Luck Stone x1". Sem ouro, nada.
    """
    c, snap = s.campaign, s.snapshot
    if c is not None and c.hook:
        from .hangup import confirm  # idem

        await confirm(s, msg)
        return
    if c is None or snap is None or not c.dungeon or not msg.paraBool1 or c.fighting:
        return
    camp = msg.paraInt2
    node = c.node(camp)
    if node is None or node["state"] != NORMAL or _confirm(c, camp) is None:
        return
    own = c.part("confirms", camp) or {}
    key = int(own.get("confirm", {}).get("itemTempId") or 0)
    if key and rules.goods_count(snap, key) < int(own["confirm"].get("itemCount") or 1):
        s.log.info("5033 sem a chave", nó=camp, item=key)
        return
    price = int(node.get("param2") or 0) if not key and int(node.get("param1") or 0) == cm.GOLD else 0
    if price > snap.character.gold:
        s.log.info("5033 sem ouro", nó=camp, preço=price)
        return
    c.talked.add(camp)
    if buffs := _buffs_of(node):
        buff = random.choice(buffs)
        c.buffs.append(buff)
        row = s.ctx.templates.get("CampaignBufferTemps", buff) or {}
        text = f"Received: {row.get('TemplateName', buff)}"
        _send(s, S_BUFFERS, _buffers(s))
        _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
        _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        _node_update(s, camp, DONE)
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
        return
    kind, got = (cm.OUT_FIGHT, []) if c.part("wins", camp) is not None else _roll(c, camp, own)
    templates, now = s.ctx.templates, s.ctx.clock.now()
    if kind == cm.OUT_FIGHT and c.battle_like(camp) is not None:
        if notice := own.get("notice"):
            _send(s, S_NOTIFY, pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=notice, delay=0))
            _node_update(s, camp, NORMAL, fresh=True, visited=True)
        _start_battle(s, camp)
        return
    if not got or not rewards.can_grant(snap, templates, got, now):
        s.log.info("5033 sem prêmio ou sem espaço", nó=camp, desfecho=kind, drops=got)
        c.talked.discard(camp)
        return
    taken = rewards.take_one(snap, key) if key else None
    snap.character.gold -= price
    new, _ = rewards.grant(snap, templates, got)
    await s.ctx.characters.save(*rewards.owners(snap), *new, *([taken[0]] if taken and not taken[1] else []),
                                delete=(taken[0],) if taken and taken[1] else ())  # fmt: skip
    text = rewards.received(templates, got)
    if taken is not None or price:
        if taken is not None:
            _send(s, S_ITEMS, rewards.taken_msg(taken[0], taken[1], s.player_id))
        if price or any(t == cm.GOLD for t, _ in got):
            castle_yield(s)
        if any(t < 0 and t != cm.GOLD for t, _ in got):
            await _push_player(s)
        _node_update(s, camp, DONE)
        if new:
            _send(s, S_ITEMS, rewards.items_msg(new, s.player_id))
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    else:
        await _push_player(s)
        _send(s, S_NOTIFY, pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=text, delay=0))
        _node_update(s, camp, NORMAL, fresh=True, visited=True)
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(8282)
async def batter_count(s: GameSession, msg: pb.BatterLastInfoMsg) -> None:
    """Combo da luta que acabou (``count``): o 137 mostra o maior da etapa. (visto) o 8282 da última luta chega
    depois do 137 (#2698 -> #2705 tem 4, o 137 manda 7, o maior antes): vale o maior até ali."""
    c = s.campaign
    if c is not None and c.run is not None:
        c.run.batter = max(c.run.batter, msg.count)


@router.on(5180)
async def campaign_finish(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Quadro das cartas fechado (``paraInt1`` 1 = sair, 2 = de novo; ChestFrame.dispose/campaignAgain).
    (visto) inglesa #1124 -> #1126, #2730 -> #2731: o 134 é a resposta do 5180; o cliente volta à cidade."""
    c = s.campaign
    if c is None or not c.dungeon or not c.finished:
        s.log.info("5180 fora do fim da masmorra", p1=msg.paraInt1)
        return
    s.campaign = None
    _send(s, S_CAMPAIGN_FINISH)
    # (visto) recria a cidade do céu (4595, e o 4597 de quem está lá) só depois do tutorial: oficial_20261023-171155-1
    # #2936-#2937 e #4180-#4181 (noviceProcess 33000), oficial_20261023-215937-1 #728-#732 (35000); sem 4595 na
    # tutorial_en #1124-#3183 (24000-28000) e na oficial_encantar #726, #1581 (28500). (dedução) o corte em 30000
    # (fim do tutorial, o mesmo do login): os dados só dizem que fica entre 28500 e 33000
    if (s.snapshot.character.novice_process if s.snapshot else 0) > space.TUTORIAL_END:
        space.enter(s)


def _map_finished(c: CampaignMap, camp: int) -> bool:
    """O mapa acabou com a vitória do nó ``camp``: o chefe (masterType 41: 102109, 113205, 114206), ou o grupo de
    monstros todo caído sem ``param4`` (que libera ou esconde nós: o 1011 acaba no último lobo, #1093 -> #1096). O nó
    ``camp`` conta como vencido mesmo antes do 128. As caixas e tumbas (61) não acabam o mapa.
    """
    node = c.node(camp)
    assert node is not None
    if node["masterType"] == BOSS:
        return True
    group = group_of(node)
    if not group or any(c.nodes[g]["state"] != DONE and g != camp for g in group if g in c.nodes):
        return False
    return not unlock_actions(node)


def _dungeon_unlock(s: GameSession, camp: int) -> None:
    """Grupo caído com ``param4``: aviso (1021, #1410), depois esconde (0), mostra com FLICKER (1) ou só mostra
    (sem ação: o portal do 1131, #2470-#2471)."""
    c = _map(s)
    node = c.node(camp)
    assert node is not None
    if any(c.nodes[g]["state"] != DONE for g in group_of(node) if g in c.nodes):
        return  # ainda há monstro de pé
    actions = unlock_actions(node)
    notice = c.part("notices", c.map_id)
    if actions and notice:
        _send(s, S_NOTIFY, pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=notice, delay=25), extend2=25)
    for target, action in actions:
        t = c.node(target)
        assert t is not None
        if action == 0:  # DISAPPEARD: o gatilho some (tutorial_en #1412)
            movie = pb.PlayerMovieMsg(
                movieTargetType=0, targetId=t["nodeId"], movieType="DISAPPEARD", delay=DISAPPEAR_DELAY
            )
            _send(s, S_MOVIE, movie, extend2=DISAPPEAR_DELAY)
            t["state"] = HIDDEN
            continue
        if action == 1:  # FLICKER e 128 com o nó novo: o chefe aparece (tutorial_en #1414, #1422)
            movie = pb.PlayerMovieMsg(movieTargetType=0, targetId=t["nodeId"], movieType="FLICKER", delay=FLICKER_DELAY)
            _send(s, S_MOVIE, movie, extend2=FLICKER_DELAY)
        _node_update(s, target, NORMAL, fresh=True)


SWITCH_CAMERA, SWITCH_DISAPPEAR, SWITCH_SHOW, SWITCH_FLICKER, SWITCH_BACK = 25, 35, 75, 85, 125  # extend2 visto


def _switch(s: GameSession, camp: int, node: dict[str, Any], switch: Mapping[str, Any]) -> None:
    """Alavanca (61 com ``param4`` ``alvo,ação|...``, o Temple Hub da 1032). (visto) oficial_20261023-153200-1
    #1117-#1126: 126 com o aviso (delay 25), câmera no que some (142), DISAPPEARD, câmera no que aparece, 128 da
    alavanca DONE (``param1`` 1), FLICKER, câmera de volta (0, 0) e o 128 do nó que aparece."""
    c = _map(s)
    notice = pb.CampaignNotifyMsg(id=2, scene=SCENE, mapId=1, body=switch["notice"], delay=SWITCH_CAMERA)
    _send(s, S_NOTIFY, notice, extend2=SWITCH_CAMERA)
    actions = [(int(t), int(a or SHOW)) for t, _, a in (x.partition(",") for x in str(node["param4"]).split("|") if x)]
    shown: list[tuple[int, int]] = []
    for target, action in actions:
        t = c.node(target)
        if t is None:
            continue
        if action == 0:
            camera = pb.PlayerMoveCameraMsg(scene=SCENE, targetX=t["posX"], targetY=t["posY"])
            _send(s, S_CAMERA, camera, extend2=SWITCH_CAMERA)
            movie = pb.PlayerMovieMsg(
                movieTargetType=0, targetId=t["nodeId"], movieType="DISAPPEARD", delay=SWITCH_DISAPPEAR
            )
            _send(s, S_MOVIE, movie, extend2=SWITCH_DISAPPEAR)
            t["state"] = HIDDEN
        else:
            shown.append((target, action))
    for target, _ in shown:
        t = c.node(target)
        assert t is not None
        _send(
            s, S_CAMERA, pb.PlayerMoveCameraMsg(scene=SCENE, targetX=t["posX"], targetY=t["posY"]), extend2=SWITCH_SHOW
        )
    _node_update(s, camp, DONE)
    for target, action in shown:
        t = c.node(target)
        assert t is not None and action in (1, SHOW)
        if action == SHOW:
            continue  # só o 128, como o grupo do 1002
        movie = pb.PlayerMovieMsg(movieTargetType=0, targetId=t["nodeId"], movieType="FLICKER", delay=SWITCH_FLICKER)
        _send(s, S_MOVIE, movie, extend2=SWITCH_FLICKER)
    _send(s, S_CAMERA, pb.PlayerMoveCameraMsg(scene=SCENE, targetX=0, targetY=0), extend2=SWITCH_BACK)
    for target, _ in shown:
        _node_update(s, target, NORMAL, fresh=True)


def _win_text(templates: GameTemplates, drops: list[tuple[int, int]]) -> str:
    """Aviso da caixa do caçador: como ``rewards.received``, mas item único sem ``x1`` (oficial_encantar #1457:
    "Received: Lvl. 3 Luck Stone"; inglesa #3072: "Received: 10,000 Daru")."""
    single = [(t, n) for t, n in drops if t > 0 and n == 1]
    text = rewards.received(templates, drops)
    for t, _ in single:
        name = rewards.received(templates, [(t, 1)])[len("Received: ") :]
        text = text.replace(name, name.removesuffix(" x1"), 1)
    return text


@dataclass
class _Loot:
    """O que uma luta na masmorra dá: itens novos (já no snapshot), textos, missões que avançaram, a moeda da caixa
    (``win``: texto e os nós que fecham com ela) e se a etapa acabou.

    ``end_quests`` são as que fecham no fim da etapa (14 e 31): o 112 delas sai depois do 135 (cartas) e antes do 4165.
    """

    items: list[Item] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    quests: list[Quest] = field(default_factory=list)
    end_quests: list[Quest] = field(default_factory=list)
    win: str = ""
    win_paid: bool = False  # a caixa deu moeda: o 3 sai antes do 126 (só item: não sai, oficial_encantar #1436-#1457)
    done: list[int] = field(default_factory=list)
    finished: bool = False
    sign: str = ""  # baú da luta (``fallen``): signId e itens no 4103, pegos no 5129
    fallen: list[tuple[int, int]] = field(default_factory=list)


def _dungeon_loot(s: GameSession, battle: Battle, camp: int, won: bool) -> _Loot:
    """Efeitos de uma luta na masmorra que mudam o snapshot. Chamado antes de qualquer await.

    - Relatório: soma o dano causado/sofrido da luta e as derrotas na etapa (``StageRun``).
    - Drop do nó (``drops[nó]`` = [item, n, chance]): (visto) inglesa #1275 (102103: Worg Tooth x2); a chance 0,5
      do Luck Stone e do 1080011 é (dedução) de uma amostra só (docs/drops-masmorras.md). Material (SonType 210:
      Worg Tooth, Wood) vai direto para a mochila e empilha (``bag.add``); o resto cai num baú: ``signId`` e
      ``baseItem`` no 4103 (inglesa #2910: 1080011), pego no 5129 (``items.drop_take``).
    - Caixa do caçador (``wins[nó]``): ``drops``, ou uma das listas de ``pick`` sorteada por igual, e os nós do
      ``param4`` do nó fecham com ela (#2633-#2642). (visto) 114203: 10.000 Daru (inglesa #3057) ou Lvl. 3 Luck Stone
      (oficial_encantar #1436); a chance igual é (dedução) de uma amostra de cada.
    - Missões: 25 (soldado morto do tipo ``tempId``) e 26 (chefe morto, ``heroTempId``). No fim da etapa, 14 (passou
      a campanha) e 31 (cena com a ``Capacity`` da campanha), em ``end_quests``: (visto) inglesa #1103, #2710.
    """
    c = _map(s)
    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    now = s.ctx.clock.now()
    run = c.run
    if run is not None:
        run.wound += battle.wound
        run.hurt += battle.hurt
        run.lost += not won
    loot = _Loot()
    if not won:
        return loot
    cid = run.campaign_id if run is not None else int((c.content or {}).get("campaign", 0))
    if (win := c.part("wins", camp)) is not None:
        node = c.node(camp)
        assert node is not None
        loot.done = [int(x) for x in str(node.get("param4", "")).split("|") if x and int(x) in c.nodes] or [camp]
    drops = [
        (int(t), int(n))
        for at in loot.done or [camp]  # (visto) #3514-#3563: a mina 103105 fecha 103111 e 103112, um drop por nó
        for t, n, chance in c.part("drops", at) or []
        if random.random() < float(chance) and rules.quest_goods_wanted(snap, templates, int(t), cid)
    ]
    got = [d for d in drops if _material(templates, d[0])]
    if fallen := [d for d in drops if d not in got]:
        loot.sign, loot.fallen = str(int(now.timestamp() * 1000)), fallen  # (visto) #2910: milissegundos da luta
        while loot.sign in c.fallen:
            loot.sign = str(int(loot.sign) + 1)
        c.fallen[loot.sign] = fallen
    if got and bag.fits(snap, templates, got, now):  # confere antes; depois só muda o snapshot
        for template_id, count in got:
            loot.items += bag.add(snap, templates, template_id, count, now)  # completa a pilha que já existe
        loot.texts = [rewards.received(templates, [d]) for d in got]  # um aviso por item, como o oficial
    if win is not None:
        money = _roll(c, camp, win)[1]
        new, _ = rewards.grant(snap, templates, money)
        loot.items += new
        loot.win, loot.win_paid = _win_text(templates, money), any(t < 0 for t, _ in money)
    kills = Counter(int(x["tempId"]) for x in battle.spec["soldiers"] if int(x["side"]) == 2)
    kinds = [(rules.PAWN_KILL_CONDITION, t, n) for t, n in kills.items()]
    kinds += [(rules.HERO_KILL_CONDITION, int(h["tempId"]), 1) for h in battle.spec["heroes"] if int(h["side"]) == 2]
    for kind, para1, value in kinds:
        for q in rules.quest_event(snap, templates, kind, para1, value):
            if q not in loot.quests:
                loot.quests.append(q)
    loot.finished = _map_finished(c, camp) and (run is None or c.map_id == run.maps[-1])
    if loot.finished:
        end = [
            (rules.CAMPAIGN_CONDITION, cid, 1),
            (rules.SOLO_CONDITION, int(_campaign_row(s, cid).get("Capacity") or 0), 1),
        ]
        for kind, para1, value in end:
            for q in rules.quest_event(snap, templates, kind, para1, value):
                if q not in loot.end_quests:
                    loot.end_quests.append(q)
    loot.quests = [q for q in loot.quests if q not in loot.end_quests]  # quem fecha no fim sai uma vez só
    return loot


def _material(templates: GameTemplates, template_id: int) -> bool:
    row = templates.get("ItemTempInfos", template_id) or {}
    return int(row.get("SonType") or 0) == MATERIAL


def ranks(s: GameSession) -> pb.RankListRspMsg:
    """4151: a melhor nota de cada campanha (``campaign_rank``). (visto) inglesa #2706: 1001 e 1002, na ordem; no
    login (#94, logo depois do 6) libera os capítulos do mapa de campanhas (``checkCanChoose``)."""
    snap = s.snapshot
    assert snap is not None
    prefix = RANK_KEY.format("")
    rows = sorted((int(e.key[len(prefix) :]), e.value) for e in snap.events if e.key.startswith(prefix))
    return pb.RankListRspMsg(rankInfo=[pb.RankMsg(userId=s.player_id, campaignId=k, rank=v) for k, v in rows])


async def _dungeon_end(s: GameSession) -> None:
    """Fim da etapa, na volta ao mapa depois do 4382. (visto) inglesa #1096-#1107 e #2703-#2714: 3, 137, 4151, 83
    "Received 630 EXP ", 135, 112 (missões do fim), 4165, 150, 150, 140. A carta sai no 5122, o 134 no 5180. O 20 no
    meio é a resposta do 5038, que o cliente manda depois de toda luta.
    """
    c, snap = _map(s), s.snapshot
    assert snap is not None and snap.leader is not None and c.run is not None and c.ending is not None
    run, quests, now = c.run, c.ending, s.ctx.clock.now()
    c.ending, c.finished = None, True
    row = _campaign_row(s, run.campaign_id)
    report = cm.report(run, row, now)
    # EXP Boost: "Increases EXP received from instances by N%, ... only takes effect in campaigns and MP dungeons"
    # (cliente, ItemTempInfo 2013001-4). (dedução) o grau vai no propJoin (o "prop" do CampaignResultView)
    report.propJoin = buffs.grade(snap, buffs.EXP_BOOST, now)
    report.totalGp = buffs.boost(report.totalGp, snap, buffs.EXP_BOOST, now)
    from .vip import VIP_EXP, vip_right  # vip importa player, que importa login, que importa este módulo

    # (cliente) CampaignResultView mostra o vipJoin à parte (vip_exp), como o petGp; (dedução) o VIP soma
    # vipJoin = totalGp x para1% e o jogador ganha os dois
    report.vipJoin = report.totalGp * vip_right(s, snap, VIP_EXP) // 100
    before = snap.character.grades
    rules.add_gp(snap, s.ctx.templates, report.totalGp + report.vipJoin)
    rank = events.state(snap, RANK_KEY.format(run.campaign_id), now)
    rank.value, rank.updated_at = max(rank.value, report.totalAppraisal), now
    stage = events.state(snap, STAGE_KEY.format(run.campaign_id), now)
    stages = len((c.content or {}).get("stages", [])) or 1
    stage.value, stage.updated_at = (run.stage + 1) % stages, now
    saved: list[EventState] = [rank, stage]
    await s.ctx.characters.save(snap.character, snap.leader, *snap.pawns, *saved)
    await _push_player(s)
    _send(s, S_REPORT, report)
    _send(s, S_RANK, ranks(s))
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=_exp_text(report.totalGp + report.vipJoin)))
    cards = (c.content or {})["maps"][str(c.map_id)].get("cards") or {}
    _send(s, S_CARDS, ParseDict(cards, pb.CampaignCardsMsg()))
    if quests:
        _send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    c.buffs = []
    _send(s, S_BUFFERS, _buffers(s))
    if snap.character.grades > before:
        from .player import push_level  # player importa login, que importa este módulo

        push_level(s, before)  # (dedução) 139, 100, 150 e 4640 como na entrega de missão
    else:
        _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    from . import events as hev  # handlers.events importa login, que importa este módulo

    # (dedução) a captura só tem o leed 4 na saída do mapa do tutorial (#521); aqui vai no fim da etapa final,
    # solo ou em grupo pela Capacity da campanha
    await hev.leed_done(s, hev.MULTI_CAMPAIGN_LEED if int(row.get("Capacity") or 1) > 1 else hev.CAMPAIGN_LEED)


@router.on(5122)
async def take_card(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Vira a carta ``paraInt2`` do 135: item de ``drops.card`` gravado, 115, 26 e 83 (inglesa #1110-#1123).

    (cliente) ChestFrame.as: o 5122 só sai do clique numa carta do 135 (``__clickHandler``) ou do ``autoChest``
    (``isPay`` true) quando o tempo acaba; 8 s depois do 26 o quadro fecha e manda o 5180(1).
    """
    c = s.campaign
    snap = s.snapshot
    if c is None or snap is None or not c.dungeon or not c.finished or c.card is not None or c.run is None:
        s.log.info("5122 sem carta para virar", p2=msg.paraInt2)
        return  # fora do fim da masmorra, ou a carta já saiu: uma só por etapa
    cards = (c.content or {})["maps"][str(c.map_id)].get("cards") or {}
    if not 0 <= msg.paraInt2 < int(cards.get("cardCount", 0)):
        return
    # ponytail: carta paga (isPay, autoChest) tratada como a grátis: price 0 e uma só por etapa; cartas pagas extras
    # (payCardCount 5) precisam de captura de quem paga (nenhuma das capturas paga)
    c.card = msg.paraInt2  # antes do await: um segundo 5122 já cai no ``c.card is not None``
    cid = c.run.campaign_id
    cards = s.ctx.world.campaign_cards.get(cid, ())
    grant = drops.card(snap, s.ctx.templates, cid, msg.paraInt2, table=cards, now=s.ctx.clock.now())
    if grant is None:
        return  # mochila cheia: sem carta
    item, take, text = grant
    await s.ctx.characters.save(snap.character, item)  # um save: carta na mochila
    from . import events as hev  # handlers.events importa login, que importa este módulo

    _send(s, S_ITEMS, rewards.items_msg([item], s.player_id))
    hev.items_gained(s)  # (visto) tutorial_en #1112
    _send(s, S_TAKE_CARD, take)
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


# -- pedreira (6001): entra pelo 8258, luta no 8699, sai no 5025 -------------------------------------


async def enter_quarry(s: GameSession, campaign_id: int) -> bool:
    """8258 {param1: 6001} (botão "ir" da missão 102, TaskFrameII.as:707): a pedreira é uma campanha (Types 2) com
    conteúdo sem névoa. Falso se ``campaign_id`` não for pedreira. (visto) inglesa #1803-#1809."""
    content = s.ctx.world.campaigns.get(campaign_id)
    if content is None or campaign_id == FAM_MAP or "fog" in content["maps"][str(content["stages"][0][0])]:
        return False
    if s.battle is not None or s.campaign is not None:
        return True  # já está num mapa
    space.leave(s)
    _enter_dungeon(s, content, int(content["stages"][0][0]), None, ENTER)
    return True


async def quarry_fight(s: GameSession) -> bool:
    """8699 dentro da pedreira: a luta ``battles["8699"]`` (herói Affudda, mapTempId 1). (visto) inglesa #1928-#1930:
    140 (lutando) e 157. Falso fora da pedreira."""
    c = s.campaign
    if c is None or not c.quarry or (spec := c.battle("8699")) is None:
        return False
    if s.battle is not None:
        return True
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))

    async def finished(battle: Battle, won: bool) -> None:
        await _quarry_over(s, battle, won)

    s.battle = Battle(
        spec,
        player_hero(s, spec, boosted(s)),
        s.ctx.templates,
        s.ctx.clock,
        s.send,
        finished,
        settings=s.ctx.world.settings,
    )
    s.log.info("batalha da pedreira", battle=s.battle.id)
    s.battle.start()
    return True


async def _quarry_over(s: GameSession, battle: Battle, won: bool) -> None:
    """(visto) inglesa #2050-#2070: 115, 111 "Received: Wood x18", 140, 4103, 150, 100, 83, 4382. A luta da captura
    foi perdida (battleResult 2) e a madeira veio mesmo assim: o drop não depende do resultado."""
    c, snap = _map(s), s.snapshot
    assert snap is not None
    s.battle, s.hero_sp = None, battle.player_sp
    now = s.ctx.clock.now()
    got = [(int(t), int(n)) for t, n, chance in c.part("drops", "8699") or [] if random.random() < float(chance)]
    items: list[Item] = []
    if got and bag.fits(snap, s.ctx.templates, got, now):
        for template_id, count in got:
            items += bag.add(snap, s.ctx.templates, template_id, count, now)
        await s.ctx.characters.save(*items)
    text = rewards.received(s.ctx.templates, got) if items else ""
    if items:
        from . import events as hev  # handlers.events importa login, que importa este módulo

        _send(s, S_ITEMS, rewards.items_msg(items, s.player_id))
        hev.items_gained(s)
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    _send(s, S_BATTLE_REPORT, _report(battle, won, 0))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    if text:
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=0, gold=0, strategy=0))


def leave_quarry(s: GameSession) -> bool:
    """5025 na pedreira: (visto) inglesa #2117-#2123: 4165, 150, 150, 140, 22 e a cidade do céu (4595). A terra
    secreta sai igual (oficial_20261023-171155-1 #5163-#5169) e o 83 "Left Guild Chamber" vai no 8747 seguinte."""
    c, snap = s.campaign, s.snapshot
    if c is None or not (c.quarry or c.fam) or snap is None:
        return False
    if c.fam:
        from . import fam  # fam importa este módulo

        fam.leaving(s)
    if s.battle is not None:
        s.battle.cancel()
        s.battle = None
    _send(s, S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    s.campaign = None
    _send(s, S_EXIT, pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id))
    space.enter(s)
    return True


# -- progresso do guia -------------------------------------------------------------------------


@router.on(5017)
async def novice(s: GameSession, msg: pb.NoviceReqMsgMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    if rules.novice_step_ok(c.novice_process, msg.noviceProcess):
        c.novice_process = msg.noviceProcess
    else:
        s.log.info("5017 recusado", novice=msg.noviceProcess, atual=c.novice_process)
    changed = rules.update_novice_quests(snap, s.ctx.templates)
    await s.ctx.characters.save(c, *changed)
    if pushed := [q for q in changed if rules.novice_pushes(s.ctx.templates, q)]:
        _send(s, S_QUESTS, quest_update(pushed, rules.quest_bitmap(snap)))
    await _push_player(s)
    _send(s, S_NOVICE)
    if s.campaign is not None and s.campaign.map_id == FIRST_MAP:
        for camp in NOVICE_UNLOCKS.get(c.novice_process, []):
            node = s.campaign.node(camp)
            if node is not None and node["state"] != NORMAL:
                _node_update(s, camp, NORMAL, fresh=True)
