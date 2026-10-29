"""Campanha de treino: entrar no mapa, andar, eventos dos nós, batalhas e saída para a cidade.

Sequências reproduzidas da captura oficial (``docs/tutorial.md``). O roteiro de cada nó está em
``ARRIVE_PLOT``/``CALLBACKS``/``WIN_UNLOCKS``; o conteúdo (nós, tropas, falas) em ``content``.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from google.protobuf.json_format import ParseDict
from google.protobuf.message import Message

from ...content import tutorial
from ...domain import gameday
from ...domain.models import EventState, Item, PlayerSnapshot, Quest
from ...protocol.messages import wartune_pb2 as pb
from ...protocol.registry import Direction
from ...templates.repository import GameTemplates
from .. import bag, buffs, drops, events, outer_city, rewards, rules, space, torres
from .. import campaign as cm
from .. import maze as mz
from ..battle import STATS, TEAM_POS, Battle, PlayerHero
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
    FOLLOWING,
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
from ..rooms import PLAYING, PVE, PVP, Room
from ..router import router
from ..session import GameSession
from . import pet_defend
from .login import S_KING_TOWER, army, player_info

S_PLAYER, S_NOVICE, S_ARMY_PAWN = 3, 1, 100
S_CHAT, S_ALERT = 83, 111
S_ROOM_ENTER, S_ROOM_CREATED, S_NODES, S_NODE, S_FOG, S_ARMY_POS = 21, 125, 127, 128, 130, 131
S_MOVE = 4185  # PosMoveMsg: o caminho de outro do mapa (U_C_ARMYPOS_BROAD)
S_PLOT, S_MAP_SYNC, S_CAMERA, S_MOVIE, S_CAMPAIGN_FINISH = 138, 140, 142, 143, 134
S_BATTLE_REPORT, S_NPC_CHASE, S_NPC_MOVE, S_ESCORT, S_PLAYER_MOVE = 4103, 4105, 4122, 4124, 4162
S_BUFFERS, S_NODE_STAND, S_FIGHT_MOVIE = 4165, 4208, 4382
S_FULL_ARMY, S_QUESTS, S_ITEMS = 150, 112, 115
S_TRIAL_BUY, S_TRIAL_INFO = 4467, 4468  # loja da Spire (U_BUY_TRIAL_RESULT, U_HERO_TRIAL_IFNO)
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


# -- falas dos NPCs (4163) ----------------------------------------------------------------------------------------
# (visto) o repertório por sonType das capturas inglesas e o ritmo: cada nó fala a cada 12-18 s ou num múltiplo disso,
# também durante a luta; a fala do chase sai logo depois do 1º 4105 do nó. Na terra secreta ninguém fala
# (oficial_20261023-171155-1 #5057-#5172). ``game_settings.npc_chat`` (0076).
S_NPC_CHAT = 4163


def _talk_cfg(s: GameSession) -> Mapping[str, Any]:
    cfg: Mapping[str, Any] = s.ctx.world.settings.get("npc_chat") or {}
    return cfg


def _say(s: GameSession, node: Mapping[str, Any], kind: str, rnd: Any = None) -> bool:
    pool = _talk_cfg(s).get("lines", {}).get(str(node["sonType"]), {}).get(kind)
    if not pool:
        return False
    _send(s, S_NPC_CHAT, pb.NPCChatMsg(id=node["nodeId"], content=(rnd or random).choice(pool)))
    return True


def talk_tick(s: GameSession, rnd: Any = None) -> None:
    """Um tique: cada NPC vivo (à vista ou lutando) com repertório fala com ``chance``."""
    c, r = s.campaign, rnd or random
    if c is None or c.fam:
        return
    chance = float(_talk_cfg(s).get("chance", 0.7))
    for node in c.nodes.values():
        if node["state"] in (NORMAL, FIGHTING) and r.random() < chance:
            _say(s, node, "idle", r)


async def _talk_loop(s: GameSession) -> None:
    try:
        while s.campaign is not None and not s.campaign.fam:
            lo, hi = _talk_cfg(s).get("tick", (12, 18))
            await asyncio.sleep(random.uniform(float(lo), float(hi)))
            talk_tick(s)
    finally:
        s.npc_talk = None


def start_talk(s: GameSession) -> None:
    if s.npc_talk is None and s.campaign is not None and not s.campaign.fam and _talk_cfg(s).get("lines"):
        s.npc_talk = asyncio.create_task(_talk_loop(s), name=f"npc-talk-{s.player_id}")


# -- patrulha dos monstros (4122) ---------------------------------------------------------------------------------
# (visto) os nós com pontos em ``game_settings.npc_patrol`` (0079) andam para outro ponto a cada tique com ``chance``;
# o 1º tique ~6,5 s depois da entrada. O nó vencido ou lutando fica parado.


def _patrol_cfg(s: GameSession) -> Mapping[str, Any]:
    cfg: Mapping[str, Any] = s.ctx.world.settings.get("npc_patrol") or {}
    return cfg


def patrol_tick(s: GameSession, rnd: Any = None) -> None:
    c, r, cfg = s.campaign, rnd or random, _patrol_cfg(s)
    if c is None or c.fam:
        return
    chance = float(cfg.get("quarry_chance" if c.quarry else "chance", 0.62))
    for node in c.nodes.values():
        pts = [tuple(p) for p in cfg.get("points", {}).get(str(node["campDataId"]), ())]
        if not pts or node["state"] != NORMAL or r.random() >= chance:
            continue
        if len(pts) == 1:  # (dedução) visto um passo só (o nó morreu antes): volta para a origem
            pts.append((node["posX"], node["posY"]))
        here = (node["curX"], node["curY"])
        node["curX"], node["curY"] = r.choice([p for p in pts if p != here] or pts)
        _send(s, S_NPC_MOVE, pb.NPCMoveMsg(id=node["nodeId"], curPosX=node["curX"], curPosY=node["curY"]))


async def _patrol_loop(s: GameSession) -> None:
    try:
        while (c := s.campaign) is not None and not c.fam:
            await asyncio.sleep(float(_patrol_cfg(s).get("quarry_tick" if c.quarry else "tick", 6)))
            patrol_tick(s)
    finally:
        s.npc_patrol = None


def start_patrol(s: GameSession) -> None:
    if s.npc_patrol is None and s.campaign is not None and not s.campaign.fam and _patrol_cfg(s).get("points"):
        s.npc_patrol = asyncio.create_task(_patrol_loop(s), name=f"npc-patrol-{s.player_id}")


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
        if s.campaign.is_warfield:
            from .warfield import broadcast_move  # warfield importa este módulo

            broadcast_move(s, msg)
        if s.campaign.gvg:
            from .guildwar import moved  # guildwar importa este módulo

            moved(s, msg)
        for mate in mates(s):  # (visto) 232017 #7875: 4185 com o caminho do outro da sala (armyId 10)
            mate.send(S_MOVE, pb.PosMoveMsg(mapId=s.campaign.map_id, armyId=s.player_id, routes=msg.routes))


@router.on(8196)
async def node_lock(s: GameSession, msg: pb.NodeLockReqMsg) -> None:
    node = s.campaign.node(msg.nodeId) if s.campaign else None
    if node is not None and msg.lock and node["attackTypes"] == AGGRESSIVE and node["state"] == NORMAL:
        c = _map(s)
        x, y = c.pos
        _send(s, S_NPC_CHASE, pb.NPCChaseMsg(nodeId=node["nodeId"], armyId=s.player_id, curPosX=x, curPosY=y))
        if node["campDataId"] not in c.chased:
            c.chased.add(node["campDataId"])
            if random.random() < float(_talk_cfg(s).get("chase_chance", 0.2)):
                _say(s, node, "chase")


@router.on(5125)
async def arrive(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    c = s.campaign
    node = c.node(msg.paraInt1) if c else None
    if c is not None and node is not None and c.gvg:  # as torres tomadas (16/17) e o acampamento (9) também
        from .guildwar import arrive as war_arrive  # guildwar importa este módulo

        await war_arrive(s, msg.paraInt1, node)
        return
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

        await boss_attack(s, node)
        return
    if c.is_warfield:
        from .warfield import arrive as field_arrive  # warfield importa este módulo

        await field_arrive(s, camp, node)
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
    if c.is_warfield:
        from .warfield import callback as field_callback  # warfield importa este módulo

        await field_callback(s, msg)
        return
    if c.fam:
        from . import fam  # fam importa este módulo

        await fam.callback(s, camp, msg.cmd)
        return
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
        from . import events as hev  # handlers.events importa login, que importa este módulo

        hev.items_gained(s)
        # (visto) tutorial_en #351-#363: 115, 4476, 4484 ×9, 111 "Received: Templar Priest Staff", 128; o 150 do #364
        # é o dos 5 min (``player._army_refresh``)
        _send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Received: {row.get('TemplateName', '')}"))
    _node_update(s, CHEST, DONE)


async def _leave_campaign(s: GameSession) -> None:
    assert s.snapshot is not None
    from . import systems  # systems importa este módulo

    systems.send_camp_buffs(s, 0)  # com cartas, o 4903 vazio
    _send(s, S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    # (visto) tutorial_en #517-#520: 4165, 150, 150, 140; sem 4902 (só turco: online_odul #6-#8, exp_kitabi #33-#35)
    s.send(S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]), cards=False)
    s.send(S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]), cards=False)
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


def pvp_fight(
    s: GameSession, target: PlayerSnapshot, battle_type: int, scene: int,
    on_end: Callable[[bool], Awaitable[None]], boost: bool = False,
) -> None:  # fmt: skip
    """Luta PvP num mapa (campo de batalha 8334, guerra de guildas 8548) contra a cópia do herói do alvo, no motor
    do coliseu; ``on_end(venceu)`` roda com ``s.battle`` já liberada (o 4103 fica com quem chama)."""
    from .. import arena as A  # noqa: PLC0415  (game.arena é pesado e só serve aqui)

    spec = A.colosseum_spec([], [A.copy_hero(target, s.ctx.templates, s.ctx.clock.now())])
    spec.update(battleType=battle_type, mapTempId=1, battleScene=scene)

    async def finished(battle: Battle, won: bool) -> None:
        s.battle, s.hero_sp = None, battle.player_sp
        await on_end(won)

    hero = player_hero(s, spec, boost)
    s.battle = Battle(spec, hero, s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings)
    s.battle.start()


def player_hero(s: GameSession, spec: dict[str, object], boost: bool = False) -> PlayerHero:
    """``boost``: o buff do contrato 7 (+10% nos ataques, defesas, vida e tropa; ``boosted``). (dedução) a vida
    atual ganha o mesmo tanto que a máxima."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    leader = snap.leader
    stats = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now())
    total, live = dict(stats.total), stats.live
    hp = b.hero_hp(leader, live)
    from . import systems  # systems importa este módulo

    c = s.campaign
    if c is not None and c.run is not None:  # buffs das cartas do lugar (o 4903 da entrada)
        cards = systems.camp_stats(snap, s.ctx.templates, systems.camp_type(_campaign_row(s, c.run.campaign_id)))
        total.update({k: int(total.get(k, 0)) + v for k, v in cards.items() if k != "Live"})
        live, hp = live + cards.get("Live", 0), hp + cards.get("Live", 0)
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
        awake=leader.awake,
        livingId2=0,  # a batalha põe o livingId do mascote
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
    pet = fighting_pet(s, msg)
    if spec.get("trial"):  # Spire: as cargas das Spire Runes (game/torres)
        msg.trials.extend(torres.trials(snap, s.ctx.templates, s.ctx.clock.now()))

    def on_awake(value: int) -> None:
        leader.awake = value  # vai para o banco com o herói (o fim da luta grava a vida dele)

    return PlayerHero(
        msg,
        total,
        int(tpl_row.get("DefaultSkill", 0)),
        passives=passive_skills(snap, s.ctx.templates),
        army=tuple(army),
        once=frozenset(runes),
        pet=pet,
        on_awake=on_awake,
    )


MORPH_GRADE = 55  # cliente PetData.MORPH_OPEN_GRADE


def fighting_pet(s: GameSession, msg: pb.HeroMsg) -> dict[str, Any] | None:
    """O mascote em batalha (``isFight``) luta junto, como entrada do ``pets`` (visto peri_uyanis #50: tempId 104101,
    side 1, maxHp 7173 igual ao 4540, skillId = followSkills + changeSkills, headId = petId, petQuality 7). Do nível
    ``MORPH_GRADE`` em diante o herói leva as skills ativas do modo mascote no ``changeSkillId`` (735101,731001,733101;
    a passiva 731201 fica fora)."""
    from .. import arena as A  # noqa: PLC0415  (arena importa handlers)
    from . import pets as P  # noqa: PLC0415  (pets importa shop, que importa este módulo)

    snap = s.snapshot
    assert snap is not None
    pet = next((p for p in snap.pets if p.is_fight), None)
    if pet is None:
        return None
    templates = s.ctx.templates
    info = P.pet_info(pet, templates, P.pet_items(snap, pet))
    follow = [int(x) for x in pet.follow_skills.split(",") if x]
    change = [int(x) for x in pet.change_skills.split(",") if x]
    entry = A.pet_unit(pet.template_id, pet.grade, info.quality, 0, 1, 0, s.player_id, pet.id or 0, templates)
    hp = info.maxHp or entry["hp"]
    entry |= {"skillId": follow + change, "maxHp": hp, "initHp": hp, "hp": hp, "castTime": 14000}
    entry |= {"follow": [x for x in follow if (templates.get("SkillTempInfos", x) or {}).get("UseWay") != "2"]}
    entry["change"] = change
    if pet.grade >= MORPH_GRADE:
        msg.changeSkillId.extend(x for x in change if (templates.get("SkillTempInfos", x) or {}).get("UseWay") != "2")
    return entry


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
    if c.run is not None and c.run.shadows:  # Tower of Kings: as sombras, mais fortes a cada nível
        spec = torres.with_shadows(spec, c.run.shadows, c.run.floors + 1)
    c.fighting = camp
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    _send(s, S_ARMY_POS, _army_brief(s, ARMY_FIGHTING))
    _node_update(s, camp, FIGHTING, user=True)

    team = [m for m in mates(s) if m.battle is None and m.campaign is not None and not m.campaign.fighting]
    if team:
        spec = _with_team(s, spec, team)
        for m in team:  # (visto) 232017 #7911-#7913: o 128 em combate com o userId de quem atacou e o 157 para todos
            assert m.campaign is not None
            m.campaign.fighting = camp
            _send(m, S_MAP_SYNC, map_sync(m, ARMY_FIGHTING))
            node = m.campaign.node(camp)
            if node is not None:
                node["state"] = FIGHTING
                _send(
                    m, S_NODE, pb.CampaignNodeUpdateMsg(nodeId=node["nodeId"], nodeState=FIGHTING, userId=s.player_id)
                )

    def send(code: int, msg: Message) -> None:
        s.send(code, msg)
        for m in team:
            m.send(code, msg)

    async def finished(battle: Battle, won: bool) -> None:
        await (over(battle, won) if over is not None else _battle_over(s, battle, camp, won))
        for m in [*team, *battle.joined]:  # (visto) 232017 #7928: o 4103 com a EXP também para quem não atacou
            if m.snapshot is not None and m.campaign is not None:
                await _battle_over(m, battle, camp, won, mate=True)

    s.battle = Battle(
        spec,
        player_hero(s, spec, boosted(s)),
        s.ctx.templates,
        s.ctx.clock,
        send,
        finished,
        settings=s.ctx.world.settings,
    )
    s.log.info("batalha", nó=camp, battle=s.battle.id, time=[m.player_id for m in team])
    s.battle.start()


@router.on(8255)
async def player_reinforce(s: GameSession, msg: pb.CampaignNodeMsg) -> None:
    """Reforço (cliente ``CampaignArmyViewHelper``: nó em luta, estado 4, numa campanha com ``Capacity`` > 1): o
    herói entra na luta de quem está no nó (``Battle.join``), luta o resto e leva o prêmio (``_battle_over`` com
    ``mate``) como os que entraram no começo."""
    c = s.campaign
    node = c.by_runtime(msg.campDataId) if c is not None else None
    camp = int(node["campDataId"]) if node is not None else 0
    owner = next((m for m in mates(s) if m.battle is not None and m.campaign and m.campaign.fighting == camp), None)
    if c is None or owner is None or s.battle is not None or c.fighting or owner.battle is None:
        s.log.info("8255 reforço recusado", node=msg.campDataId)
        return
    if not owner.battle.join(team_hero(s, s), s):
        s.log.info("8255 reforço recusado", node=msg.campDataId, motivo="luta acabando ou sem lugar")
        return
    c.fighting = camp  # como os do time em ``_start_battle``: o 128 em combate com o userId de quem atacou
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    assert node is not None
    node["state"] = FIGHTING
    _send(s, S_NODE, pb.CampaignNodeUpdateMsg(nodeId=node["nodeId"], nodeState=FIGHTING, userId=owner.player_id))


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


def team_hero(s: GameSession, m: GameSession) -> dict[str, Any]:
    """O herói de ``m`` na luta de outro: cópia (``arena.copy_hero``) com o ``userId`` dele, que o cliente de cada um
    usa para achar o seu herói. Luta sozinho (automático)."""
    from .. import arena as A  # noqa: PLC0415  (arena importa handlers)

    assert m.snapshot is not None
    hero = A.copy_hero(m.snapshot, s.ctx.templates, s.ctx.clock.now())
    hero.update(side=1, type=1, userId=m.player_id, heroId=m.player_id)
    return hero


def _with_team(s: GameSession, spec: dict[str, Any], team: list[GameSession]) -> dict[str, Any]:
    """Os outros da sala entram na luta como heróis do lado 1 (``arena.copy_hero``, com o ``userId`` deles: o
    cliente de cada um acha o seu herói). Lutam sozinhos (automático): o 157 vai para todos, as ordens não."""
    used = [u["livingId"] for k in ("soldiers", "heroes") for u in spec.get(k, [])]
    used += [u["livingId"] for w in spec.get("reinforce", []) for u in w] + [spec["player"]["livingId"]]
    taken = {u["pos"] for u in spec.get("soldiers", []) if u.get("side") == 1} | {spec["player"]["pos"]}
    free = [p for p in TEAM_POS if p not in taken]
    heroes = list(spec.get("heroes", []))
    for i, m in enumerate(team[: len(free)]):
        heroes.append(team_hero(s, m) | {"livingId": max(used) + 1 + i, "pos": free[i]})
    return spec | {"heroes": heroes}


def _report(battle: Battle, won: bool, gp: int, strategy: int = 0) -> pb.BattleReportMsg:
    report = pb.BattleReportMsg(battleResult=WON if won else LOST, strategyBonus=strategy, gpBonus=gp)
    report.battleScene = int(battle.spec.get("battleScene", CAMPAIGN_SCENE))
    report.failCount, report.goldBonus, report.petGpBonus = 0, 0, 0
    return report


async def _battle_over(s: GameSession, battle: Battle, camp: int, won: bool, *, mate: bool = False) -> None:
    """``mate``: outro da sala que lutou junto (herói NPC na luta de quem atacou): ganha o mesmo, sem perder tropa
    nem vida (o herói dele não é o ``battle.player``)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    if not mate:
        s.battle, s.hero_sp = None, battle.player_sp
    gp = int(battle.spec.get("gpBonus", 0)) * max(1, battle.layer) if won and _rewarded(s) else 0  # Spire: por andar
    # EXP Boost (2013001-4): o gpBonus capturado é a base; o 4103, o 83 e o 4382 levam a EXP com o bônus (dedução)
    gp = buffs.boost(gp, snap, buffs.EXP_BOOST, s.ctx.clock.now())
    maze = s.campaign is not None and mz.is_floor(s.campaign.map_id)
    if maze:
        from . import tower  # tower importa este módulo nas funções

        gp = tower.doubled(s, gp)
    before = snap.character.grades
    gp, world, rested = rules.exp_bonus(snap.character, s.ctx.world.settings, gp)
    if gp:
        rules.add_gp(snap, s.ctx.templates, gp)
    from . import pets as P  # noqa: PLC0415  (pets importa shop, que importa este módulo)

    # (só turco: peri_uyanis #73, #78) o mascote que lutou ganha a mesma EXP e o 4540 sai logo depois do 3
    pet = P.share_gp(s, gp) if battle.pet_id and not mate else None
    loot = _Loot()
    dungeon = s.campaign is not None and s.campaign.dungeon
    # tropas mortas saem e a reserva repõe (visto #1466 -> #1511: a reserva 738 -> 650); a luta roteirizada não perde
    undying = bool(battle.spec.get("undying"))
    hit = None if undying or mate else outer_city.lose_troops(snap, s.ctx.templates, battle.troops())
    # Daru = soldados perdidos, ganhando ou perdendo: (visto) inglesa #1466 (88 mortos, Wulfgar 88) e
    # oficial_20261023-153200-1 (a reserva cai 127, 98, 115, 121; derrotas 53, 202, 202 = o exército inteiro)
    strategy = hit[1] if hit is not None else int(battle.spec.get("strategyBonus", 0)) if won and undying else 0
    snap.character.strategy += strategy
    if not won:
        s.fail_count += 1
    if hit is not None:
        outer_city.refill(*hit)
    from .player import hero_after_fight, hp_pack  # player importa login, que importa este módulo

    healed = hero_after_fight(s, battle.player.hp if battle.player is not None and not mate else None)
    chests: list[Item] = []
    letters: list[Any] = []
    if dungeon:
        loot = _dungeon_loot(s, battle, camp, won)  # antes do await: drop, missão e EXP numa save só
        trun = s.campaign.run if s.campaign is not None else None
        trow = _campaign_row(s, trun.campaign_id) if trun is not None else {}
        if won and trun is not None and torres.son(trow):
            floors = battle.layer or 1  # andares das torres (a Spire conta as ondas)
            trun.floors += floors
            if trun.rewarded:  # (internet) o baú sai depois de cada luta (King) / chefe (Spire)
                from .shop import place  # shop importa este módulo

                chests, letters = place(s, snap, s.player_id, torres.prize(trow, floors), s.ctx.clock.now())
            if battle.layer:  # o TrailView mostra o andar e o que ele vale
                s.send(S_TRIAL_INFO, torres.shop_msg(snap, s.ctx.templates, s.ctx.clock.now(), trun.floors))
    if chests or letters:
        from .shop import save_with_mail  # shop importa este módulo

        await save_with_mail(s, letters, *chests)
        if chests:
            _send(s, S_ITEMS, rewards.items_msg(chests, s.player_id))
    if gp or strategy or loot.items or loot.quests or loot.end_quests or loot.win or hit:
        await s.ctx.characters.save(
            snap.character, snap.leader, *snap.pawns, *loot.items, *loot.quests, *loot.end_quests,
            *([pet] if pet is not None else []),
        )  # fmt: skip
    s.battle_gp = 0 if dungeon else gp  # a masmorra guarda o 4382 no mapa (``over``), com o Daru do chefe
    # masmorra: (visto) oficial_20261023-171155-1 #5318-#5325, #5532-#5543, #5780-#5790 (1004) e #2096-#2106 (1003):
    # 109 com a população depois das baixas, 3, o 83 da poção de vida, outro 3 com a EXP, 4103, 150, 100, 140, os
    # itens (115, 111) e o 112, 131, 128 e por fim o 83 da EXP; a última luta leva ``petGpBonus`` -1 (também na
    # tutorial_en #1509, #2692, #3146). Na derrota o 83 da poção vem depois do 4103 (oficial_20261023-153200-1
    # #1446-#1457: 109, 3, 4103, 83, 150, 100, 140, 131, 128). Fora da masmorra fica a ordem da tutorial_en (#906-#914).
    if dungeon and hit is not None:
        castle_yield(s)
    await _push_player(s)
    if pet is not None:
        P.send_gained(s, pet)
    if dungeon and won:
        hp_pack(s, healed)
        if gp:
            await _push_player(s)
    report = _report(battle, won, gp, strategy)
    report.failCount = s.fail_count
    if pet is not None:
        report.petGpBonus = gp
    if dungeon and loot.finished:
        report.petGpBonus = -1
    if loot.fallen:
        report.signId = loot.sign
        report.baseItem.extend(pb.BaseItemMsg(templateId=t, count=n) for t, n in loot.fallen)
    _send(s, S_BATTLE_REPORT, report)
    if not dungeon or not won:
        hp_pack(s, healed)  # (visto) oficial_20261023-153200-1 #1449-#1450
    if not dungeon and gp:  # (visto) inglesa #909 "Received 35 EXP " (com o espaço no fim)
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=rules.exp_text(gp, world, rested)))
    if snap.character.grades > before:
        from .player import push_level  # player importa login, que importa este módulo

        await push_level(s, before)  # (dedução) 139, 100, 150 e 4640 como na entrega de missão
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
        if maze:  # (visto) 10/25 #10587 derrota, #10592 140 e #10593 4207 (o msg é o custo do reviver)
            await s.ctx.characters.save(tower.died(s))
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
    if maze:
        await s.ctx.characters.save(tower.floor_won(s, c.map_id, gp))
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
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=rules.exp_text(gp, world, rested)))
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
    island = msg.state == BACK_TO_MAP and s.campaign is not None and s.campaign.map_id in PET_ISLANDS
    if island:
        # (só turco: peri_adasi_tp #7-#27) o oficial repete o 21 quando a cena termina, manda o 127 e logo os 4122
        # da patrulha (19 nós de uma vez: o primeiro tique sem esperar, dedução)
        _send(s, S_ROOM_ENTER, _room_enter(s))
        _send(s, S_NODES, _map(s).node_list())
        patrol_tick(s)
    if msg.state == BACK_TO_MAP and s.battle_gp:
        _send(s, S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=0))
        s.battle_gp = 0
    c = s.campaign
    if msg.state == BACK_TO_MAP and c is not None and c.world_boss:
        from .worldboss import scene_loaded  # worldboss importa este módulo

        await scene_loaded(s)
    if msg.state == BACK_TO_MAP:
        start_talk(s)
        start_patrol(s)
    if msg.state == BACK_TO_MAP and c is not None and c.fam and not c.ready:
        from . import fam  # fam importa este módulo

        fam.show_room(s)
    if msg.state == BACK_TO_MAP and c is not None and c.gvg and not c.ready:
        from .guildwar import show_map  # guildwar importa este módulo

        show_map(s)
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
    mine = s.ctx.rooms.of(s.player_id)
    if msg.paraInt2 == 0 and mine is not None and mine.type == PVP and mine.master == s.player_id:
        from .room import start_matching  # room importa este pacote

        start_matching(s, mine)  # (visto) 27/10 #20230: 5039 com paraInt2 0 na sala PvP procura partida
        return
    c, snap = s.campaign, s.snapshot
    content = s.ctx.world.campaigns.get(msg.paraInt2)
    if snap is None or content is None or s.battle is not None or (c is not None and not c.finished):
        s.log.info("5039 recusado", campanha=msg.paraInt2)
        return
    stages = content["stages"]
    if "fog" not in content["maps"][str(stages[0][0])]:
        return  # a pedreira entra pelo 8258
    room = s.ctx.rooms.of(s.player_id)
    if room is not None and room.type == PVE and msg.paraInt1 != 1:
        await _group_start(s, room, content, msg)
        return
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
    from . import systems  # systems importa este módulo

    systems.send_camp_buffs(s, systems.camp_type(_campaign_row(s, msg.paraInt2)))
    name = _campaign_row(s, msg.paraInt2).get("CampaignName", "")
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Entered [{name}] and deducted {WEARY} stamina."))
    await s.ctx.characters.save(snap.character)


# (visto) 191924 #4537 "1/1" (paraBool1 true, não gasta) e #6886 "0/1" (false, gastou na entrada: o 3 #6874)
GROUP_TEXT = "Entered [{}]. You still have {}/{} multi-player dungeon attempts available."


async def _group_start(s: GameSession, room: Room, content: Mapping[str, Any], msg: pb.CampaignReqMsg) -> None:
    """Start da sala (``RoomRightView._startClick`` -> ``sendStartCampaignScene``: 5039 com ``paraInt2`` = campanha e
    ``paraBool1`` = ``isNoGet``, sem prêmio: (visto) 191924 #4525 true dá gpBonus 0 e não gasta; #6870 false gasta e
    dá EXP). Só o dono, com a campanha da sala e todos prontos (``allPlayerReader``).
    (só turco: exp_kitabi #24-#40) 24 com o dono em 2 e cada um entra (``_group_enter``)."""
    from .room import S_READY, _ready_state, _to_room  # room importa space, que este pacote também usa

    others = [p for p in room.members if p != room.master]
    if room.master != s.player_id or room.campaign != msg.paraInt2 or any(p not in room.ready for p in others):
        s.log.info("5039 recusado: sala", sala=room.id, campanha=msg.paraInt2)
        return
    assert s.snapshot is not None
    if not torres.unlocked(s.snapshot, _campaign_row(s, msg.paraInt2)):
        s.log.info("5039 recusado: dificuldade da torre fechada", campanha=msg.paraInt2)  # "Clear {0} to enter"
        return
    states = [pb.PlayerreadyrspmsgPlayerReady(playerId=p, readyState=_ready_state(room, p)) for p in room.members]
    _to_room(s, room, S_READY, pb.PlayerReadyRspMsg(readyState=states))
    room.state = PLAYING
    for pid in room.members:
        other = s.ctx.online.get(pid)
        if other is None or other.snapshot is None or other.battle is not None:
            continue
        if other.campaign is not None and not other.campaign.finished:
            continue
        await _group_enter(
            other, room, content, msg.paraInt2, not msg.paraBool1 if pid == room.master else pid in room.rewarded
        )
    # (visto) 232017 #7687: depois da névoa, outro 21 com todos da sala no mapa (434 e 11)
    inside = [o for p in room.members if (o := s.ctx.online.get(p)) is not None and o.campaign is not None]
    for o in inside:
        enter = _room_enter(o)
        for mate in mates(o):
            enter.player.append(_room_enter(mate).player[0])
        _send(o, S_ROOM_ENTER, enter)


def mates(s: GameSession) -> list[GameSession]:
    """Os outros da sala em grupo no mesmo mapa da masmorra: o oficial divide o mapa (191924, 232017, 152321):
    o caminho (4185), os nós (128) e as lutas (157 com o time) chegam a todos."""
    c = s.campaign
    room = s.ctx.rooms.of(s.player_id)
    if c is None or c.run is None or room is None or room.state != PLAYING:
        return []
    out = []
    for pid in room.members:
        o = s.ctx.online.get(pid)
        if o is not None and o is not s and o.campaign is not None and o.campaign.map_id == c.map_id:
            out.append(o)
    return out


async def _group_enter(s: GameSession, room: Room, content: Mapping[str, Any], cid: int, use: bool) -> None:
    """Entrada de um da sala. (só turco: exp_kitabi #25-#40) 125 com a sala inteira (``roomState`` 3), 140, 21 com
    o lugar, 3, 150, 4903, 3 (a entrada gasta), 4165, 150, 150, 127, 130, 143, o 83 da poção e o 83 das entradas.
    Sem estamina (o aviso do cliente só fala das entradas). Sem entrada ou sem ``use``: entra sem prêmio
    (cliente: "You can complete the quest but cannot obtain rewards", ``RoomRightView.incomePrompt``)."""
    from . import systems  # systems importa este módulo
    from .player import hp_pack  # player importa login, que importa este módulo

    snap, now, templates = s.snapshot, s.ctx.clock.now(), s.ctx.templates
    assert snap is not None
    c_ = snap.character
    stages = content["stages"]
    stage = events.state(snap, STAGE_KEY.format(cid), now).value % len(stages)
    maps = tuple(int(m) for m in stages[stage])
    count, top = c_.multi_copies(rules.copies_base(templates), now)
    row = _campaign_row(s, cid)
    tower = torres.son(row)
    tower_rows: list[EventState] = []
    if tower and use:  # as torres têm a entrada do dia delas, não a das masmorras em grupo
        use, tower_rows = torres.enter(snap, row, now)
    run = StageRun(cid, stage, maps, now, rewarded=use and (bool(tower) or count > 0))
    if tower == torres.KING:
        run.shadows = await _king_shadows(s, int(row.get("DifficultyGrade") or 1))
    s.campaign = c = CampaignMap.enter_dungeon(content, maps[0], run)
    name = row.get("CampaignName", "")
    created = pb.RoomCreatedMsg(createdType=ENTER)
    created.room.CopyFrom(
        pb.RoomMsg(
            roomId=room.id, campaignId=maps[0], masterId=room.master, name=name, count=len(room.members),
            capacity=room.capacity, roomState=room.state, roomType=room.type, isSetPassword=bool(room.password),
        )
    )  # fmt: skip
    _send(s, S_ROOM_CREATED, created)
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    enter = _room_enter(s)
    me = enter.player[0]
    me.roomId, me.count, me.currentRoomIndex = room.id, len(room.members), room.seats.index(s.player_id)
    me.playerState = 2 if s.player_id == room.master else 1  # (só turco: #27) o dono em 2, como o 24
    _send(s, S_ROOM_ENTER, enter)
    await _push_player(s)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    systems.send_camp_buffs(s, systems.camp_type(row))
    if run.rewarded and not tower:
        count -= 1
        c_.multi_copy_count, c_.multi_copy_max, c_.multi_copy_day = count, top, gameday.today(now)
    if tower == torres.KING:
        s.send(S_KING_TOWER, torres.king_msg(snap, now))
    await _push_player(s)
    _send(s, S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]), cards=False)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]), cards=False)
    _send(s, S_NODES, c.node_list())
    _send(s, S_FOG, c.fog())
    _send(s, S_MOVIE, pb.PlayerMovieMsg(movieTargetType=3, targetId=0, movieType="MOVIE_MAP_NAME", delay=0))
    healed = rules.heal_hero(snap, templates, now) if snap.leader is not None else 0
    hp_pack(s, healed)  # (só turco: #39) a poção enche a vida na entrada
    # TODO(captura): o texto de entrada das torres; o "Entered [X]..." é do servidor (nenhuma chave no language.txt)
    # e fala das entradas de masmorra em grupo, que as torres não gastam
    if not tower:
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=GROUP_TEXT.format(name, count, top)))
    await s.ctx.characters.save(c_, *([snap.leader] if snap.leader is not None else []), *tower_rows)
    if tower == torres.SPIRE and tower_rows:
        from . import events as hev  # handlers.events importa login, que importa este módulo
        from .army import count_quest

        await hev.leed_done(s, torres.SPIRE_LEED)  # LeedTemp 28 "Enter the Spire"
        await count_quest(s, rules.SPIRE_CONDITION)  # 799; TODO(inventado): a posição do 112
    if tower == torres.SPIRE:  # a loja e o andar do TrailView (CampaignSocketManger.__trailPropInfoHandler)
        s.send(S_TRIAL_INFO, torres.shop_msg(snap, templates, now))


@router.on(8582)
async def buy_trial(s: GameSession, msg: pb.TrialInfoMsg) -> None:
    """Compra de Spire Rune (``TrailShopItem.confirmBack``): ``param1`` 0 paga com Balens vinculados primeiro. 4467
    com ``count`` = compradas hoje e ``param1`` 1; recusa com ``param1`` 0 (o quadro não muda)."""
    snap = s.snapshot
    if snap is None:
        return
    done = torres.buy(snap, s.ctx.templates, msg.skillId, msg.param1 == 0, s.ctx.clock.now())
    if done is None:
        s.send(S_TRIAL_BUY, pb.TrialInfoMsg(skillId=msg.skillId, count=0, param1=0))
        return
    count, rows = done
    await s.ctx.characters.save(*rows)
    await _push_player(s)
    s.send(S_TRIAL_BUY, pb.TrialInfoMsg(skillId=msg.skillId, count=count, param1=1))


async def _king_shadows(s: GameSession, grade: int) -> list[dict[str, Any]]:
    """As sombras da dificuldade (internet: os 16 mais fortes do ranking de força, 4 por dificuldade), cópias de
    combate do coliseu. Servidor com menos jogadores: os que houver do fim da faixa para cima; sem nenhum, a luta
    fica com os monstros gerados (TODO(inventado))."""
    from .. import arena as A  # noqa: PLC0415  (game.arena é pesado e só serve aqui)

    snap = s.snapshot
    assert snap is not None
    server = snap.server.id
    top = await s.ctx.characters.read(lambda uow: uow.characters.strongest(server, torres.SHADOW_TOP))
    ids = [c.id for c in top if c.id is not None]
    band = ids[torres.shadow_slice(grade)] or ids[-torres.SHADOW_PARTY :]
    out = []
    for cid in band:
        other = s.ctx.online.get(cid)
        shadow = other.snapshot if other is not None else await s.ctx.characters.snapshot(cid)
        if shadow is not None and shadow.leader is not None:
            out.append(A.copy_hero(shadow, s.ctx.templates, s.ctx.clock.now()))
    return out


def _rewarded(s: GameSession) -> bool:
    c = s.campaign
    return c is None or c.run is None or c.run.rewarded


def _enter_dungeon(
    s: GameSession, content: Mapping[str, Any], map_id: int, run: StageRun | None, created: int
) -> list[Any]:
    """Entra num mapa da masmorra. No labirinto, pelo portal, devolve as linhas a gravar (torre e missões)."""
    s.campaign = c = CampaignMap.enter_dungeon(content, map_id, run)
    rows: list[Any] = []
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
        if mz.is_floor(map_id):
            from . import tower  # tower importa este módulo nas funções

            rows = tower.floor_entered(s, map_id)
        _send(s, S_ARMY_POS, _army_brief(s, ARMY_IDLE))
    else:
        _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        _send(s, S_ROOM_ENTER, _room_enter(s))
        _send(s, S_NODES, c.node_list())
        _send(s, S_FOG, c.fog())
        _send(s, S_MOVIE, pb.PlayerMovieMsg(movieTargetType=3, targetId=0, movieType="MOVIE_MAP_NAME", delay=0))
        if (plot := content["maps"][str(map_id)].get("plot")) is not None:
            _send_plot(s, plot)  # (visto) inglesa #850 (Dinah no 1011), #2317 (1131)
    return rows


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
        if rows := _enter_dungeon(s, c.content, int(target), c.run, PORTAL_ENTER):
            await s.ctx.characters.save(*rows)
    elif (plot := c.part("plots", camp)) is not None:
        _send_plot(s, plot)  # Karlan (#2666-#2667, um 138 por 5125); a luta vem no 5032 do fim do diálogo
    elif (switch := c.part("switches", camp)) is not None and node["state"] == NORMAL:
        _switch(s, camp, node, switch)
    elif (confirm := _confirm(c, camp)) is not None:
        # (visto) inglesa #1428-#1429, #2397-#2398: 29 e 4126 na posição do nó + 2
        _send(s, S_CONFIRM, ParseDict(confirm, pb.CampaignConfirmMsg()))
        _send(s, S_STANDPOS, pb.StandPosMsg(id=s.player_id, posX=node["posX"] + 2, posY=node["posY"] + 2))
    elif (box := c.part("maze_chests", camp)) is not None:
        from . import tower  # tower importa este módulo nas funções

        await tower.open_chest(s, camp, box)
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
        elif node["state"] == NORMAL and int(node.get("heroTempId", 0)) > 0 and not c.battle(camp):
            # NPC que passa a seguir o jogador (a Elise da 1005, herói 1051): (visto) oficial_20261023-231733-1
            # #1121-#1123, 128 state 2 e um 4124 só, na posição do exército
            _node_update(s, camp, FOLLOWING)
            c.escort = node["nodeId"]
            x, y = c.pos
            _send(s, S_ESCORT, pb.NPCFollowMsg(escortId=c.escort, followId=s.player_id, curPosX=x, curPosY=y))
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
    if c is not None and c.gvg:
        from .guildwar import confirm as war_confirm  # guildwar importa este módulo

        await war_confirm(s, msg)
        return
    if c is not None and snap is not None and c.is_warfield:
        from .warfield import confirm as field_confirm  # warfield importa este módulo

        await field_confirm(s, msg)
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
    coin = rewards.CURRENCIES[cm.GOLD]
    if cost := own.get("cost"):  # baú VIP da 9001: 2000 Kyanite (o texto do 29)
        coin, price = rewards.CURRENCIES[int(cost[0])], int(cost[1])
    if price > getattr(snap.character, coin):
        s.log.info("5033 sem moeda", nó=camp, preço=price, moeda=coin)
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
    setattr(snap.character, coin, getattr(snap.character, coin) - price)
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
    return not [a for a in unlock_actions(node) if not _dead_gate(c, a[0])]


def _dead_gate(c: CampaignMap, camp: int) -> bool:
    """Portal escondido sem mapa no conteúdo: TODO(inventado) a etapa acaba no grupo caído (9001: o 201107
    levaria ao 2012, que nenhuma captura mostra). O 113201 do 1132 (62 à vista) não é portal."""
    node = c.node(camp)
    hidden = node is not None and node["masterType"] == cm.GATE and node["state"] == HIDDEN
    return hidden and c.part("portals", camp) is None


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
    if run is not None and not run.rewarded:
        drops = []  # sem a entrada do dia: sem drop (cliente, ``incomePrompt``); as missões contam
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
    tower = torres.son(row)
    if tower and run.rewarded:
        saved += torres.finish(snap, row, now)
    await s.ctx.characters.save(snap.character, snap.leader, *snap.pawns, *saved)
    if tower == torres.KING and run.rewarded:  # os baús já saíram em cada luta
        end = {"currentIndex": run.floors, "currentStep": int(row.get("DifficultyGrade") or 1)}
        reward = sum(n for _, n in torres.prize(row, run.floors))
        s.send(S_KING_TOWER, torres.king_msg(snap, now, **end, rewardCount=reward))
        run.rewarded = False  # o fim (4900 e a dificuldade) vale uma vez por corrida
    await _push_player(s)
    _send(s, S_REPORT, report)
    _send(s, S_RANK, ranks(s))
    _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=_exp_text(report.totalGp + report.vipJoin)))
    if not tower:  # torres: sem carta, o prêmio é o baú por luta (internet, docs/fontes-internet.md)
        cards = (c.content or {})["maps"][str(c.map_id)].get("cards") or {}
        _send(s, S_CARDS, ParseDict(cards, pb.CampaignCardsMsg()))
    if quests:
        _send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    c.buffs = []
    _send(s, S_BUFFERS, _buffers(s))
    if snap.character.grades > before:
        from .player import push_level  # player importa login, que importa este módulo

        await push_level(s, before)  # (dedução) 139, 100, 150 e 4640 como na entrega de missão
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
    if not c.run.rewarded:
        s.log.info("5122 sem prêmio: campanha em grupo sem a entrada do dia")
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
    secreta sai igual (oficial_20261023-171155-1 #5163-#5169) mais o 83 "Left Guild Chamber" logo depois do 4595
    (oficial_20261024-121659-1 #655-#656)."""
    c, snap = s.campaign, s.snapshot
    if c is None or not (c.quarry or c.fam) or snap is None:
        return False
    fam_room = c.fam
    if fam_room:
        from . import fam  # fam importa este módulo

        fam.leaving(s)
    if s.battle is not None:
        s.battle.cancel()
        s.battle = None
    exit_to_city(s)
    if fam_room:
        _send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg="Left Guild Chamber"))
    return True


def exit_to_city(s: GameSession) -> None:
    """Sai da sala de campanha para a cidade do céu: 4165, 150, 150, 140, 22 e o 4595 (``space.enter``)."""
    snap = s.snapshot
    assert snap is not None
    _send(s, S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _send(s, S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    s.campaign = None
    _send(s, S_EXIT, pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id))
    space.enter(s)


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
