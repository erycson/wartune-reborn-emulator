"""Pedidos da cidade do céu e da ilha dos pets. A presença dos jogadores está em ``game/space.py``.

Nós do mapa 10000: ``MapNodeInfos`` do tempinfos.xml (``SpaceTemplateManager.nodeDic``).
"""

from __future__ import annotations

from collections.abc import Sequence

from ...content import pet_island
from ...domain.models import Quest
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import Row
from .. import rules, space
from ..builders.player import quest_update
from ..campaign import PET_ISLANDS, CampaignMap
from ..router import router
from ..session import GameSession
from .campaign import ARMY_IDLE, leave_quarry, map_sync
from .room import leave_room

MAX_PATH = 16  # o cliente manda no máximo ~7 passos; o resto é repassado a todos, então corta
MAX_USERS = 50  # 8701: jogadores por pedido
S_EVENT, S_STAND, S_QUESTS = 4601, 4126, 112  # 112: QuestUpdatedRspMsg
S_MAP_SYNC, S_ROOM_CREATED, S_ROOM_ENTER, S_NODES = 140, 125, 21, 127
PATROL, TRANSFER = "1", "171"  # MasterType: NPC que anda (o cliente resolve sozinho) e teleporte
REACH = 5  # o cliente dispara a até HandlerRange+5 tiles (SpaceArmyViewHelper.selfArmyToEnd)
ROOM_ENTER = 1  # RoomCreatedMsg.createdType ao entrar num mapa (tutorial_en #116)


def _node(s: GameSession, node_id: int) -> Row | None:
    return next(s.ctx.templates.find("MapNodeInfos", Id=str(node_id), MapId=str(space.SPACE)), None)


def _near(s: GameSession, node: Row) -> bool:
    """Perto do nó; o NPC que anda (``PATROL``) não está no ``PosX/PosY`` do template, então conta sempre."""
    if node["MasterType"] == PATROL:
        return True
    if s.space_pos is None:
        return False
    x, y = s.space_pos
    reach = int(node.get("HandlerRange") or 0) + REACH
    return abs(x - int(node["PosX"])) <= reach and abs(y - int(node["PosY"])) <= reach


def talk(s: GameSession, node_id: int, quests: Sequence[Quest] | None = None) -> list[Quest]:
    """Conversa com o NPC ``node_id``: a condição 85 cujo Para4 é "10000,nó" ganha o progresso se o jogador
    estiver perto do nó (como no 8692). ``quests`` limita às recém aceitas.

    ponytail: o fim do diálogo é local no cliente (``finishStory``); aqui conta o clique ou o aceite perto do nó.
    """
    snap, node = s.snapshot, _node(s, node_id)
    if snap is None or node is None or not _near(s, node):
        return []
    return rules.talk_event(snap, s.ctx.templates, f"{space.SPACE},{node_id}", quests)


@router.on(8688)
async def enter_space(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    if s.snapshot is not None and s.snapshot.character.novice_process >= space.POST_TUTORIAL:
        s.campaign = None  # saiu do mapa em que estava (ilha dos pets) para a cidade do céu
    space.back(s)


@router.on(8689)
async def leave_space(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    space.leave(s)  # SpaceSocketOutManager.leaveSpace: os outros recebem o 4607


@router.on(8690)
async def space_move(s: GameSession, msg: pb.SpacePlayerMoveMsg) -> None:
    # o cliente manda só o próprio jogador; o playerId dele é ignorado (vale o da sessão)
    path = [(p.x, p.y) for player in msg.players[:1] for p in player.path[:MAX_PATH] if p.x >= 0 and p.y >= 0]
    space.move(s, path)


@router.on(8692)
async def node_trigger(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Clicou num nó do space: teleporte troca de mapa; os outros abrem a janela do nó (4601)."""
    node = _node(s, msg.param1)
    if node is None or not _near(s, node):
        s.log.info("8692 recusado", no=msg.param1, pos=s.space_pos)
        return
    if node["MasterType"] == TRANSFER:
        await _transfer(s, node)
    else:
        if node["MasterType"] != PATROL:  # a patrulha o cliente abre sozinho; só a conversa conta
            s.send(S_EVENT, pb.SimplePropertyMsg(param1=msg.param1))  # SpaceSceneController.__selectNodeHandler
        changed = talk(s, msg.param1)
        from . import offer  # offer importa player, que importa este módulo

        await offer.progress(s, offer.MESSAGE, 1, msg.param1)  # "Message for Alice" (Para4 "10000,nó", Para1 = nó)
        if changed and (snap := s.snapshot) is not None:
            await s.ctx.characters.save(*changed)
            s.send(S_QUESTS, quest_update(changed, rules.quest_bitmap(snap)))


async def _transfer(s: GameSession, node: Row) -> None:
    assert s.snapshot is not None
    target, need = int(node["MoveToMapId"]), int(node.get("Param3") or 0)  # Param3 = nível mínimo
    from .. import battlefield as bf

    if s.snapshot.character.grades >= need and target == bf.MINE:  # Amethyst Mine: a mesma entrada do 8633
        from .warfield import enter_mine  # warfield importa campaign, que importa este módulo

        await enter_mine(s, None)
        return
    if s.snapshot.character.grades < need or str(target) not in pet_island()["maps"]:
        s.log.info("teleporte do space indisponível", destino=target, nivel=s.snapshot.character.grades)
        return
    enter_pet_island(s, target)


def enter_pet_island(s: GameSession, map_id: int) -> None:
    """Ilha dos pets como no oficial (só turco: peri_adasi_tp #3-#8): 140, 125, 21; o 127 e a patrulha dos pets
    selvagens (4122) saem no 5035 da cena carregada (``campaign.client_state``). Mapa por sessão com os nós da
    captura (#8). Sai pelo botão de sair (5025) ou indo ao space (8688).
    """
    data = pet_island()["maps"][str(map_id)]
    s.campaign = CampaignMap(map_id, {n["campDataId"]: dict(n) for n in data["nodes"]}, tuple(data["start"]))
    space.leave(s)  # some da cidade do céu dos outros enquanto está na ilha
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER)
    room.room.campaignId = map_id
    s.send(S_ROOM_CREATED, room)
    assert s.snapshot is not None
    me = space.room_player(s.snapshot, s.ctx.templates, s.campaign.pos, map_id, s.ctx.clock.now())
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    from .pet_defend import sync_nodes  # pet_defend importa a campanha, que importa este módulo

    s.pet_defend_nodes = None
    sync_nodes(s, send=False)  # monstros da invasão já no 127, se a janela deste andar estiver aberta


@router.on(8694)
async def enter_pet_land(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # opção de diálogo tipo 6 (DialogOptionItem); nenhum nó do 10000 a usa hoje, a entrada é pelo nó 5
    gate = next((n for n in s.ctx.templates.find("MapNodeInfos", MoveToMapId=str(msg.paraInt1))), None)
    if s.campaign is not None or gate is None or gate["MasterType"] != TRANSFER or not _near(s, gate):
        s.log.info("8694 recusado", mapa=msg.paraInt1)
        return
    await _transfer(s, gate)


@router.on(5025)
async def leave_pet_island(s: GameSession, msg: pb.RoomExitMsg) -> None:
    """Botão de sair (5025): na ilha dos pets volta para a Cloud City com 4606 (só turco:
    gokyuzu_sehrine_teleport_ve_yurume_sistemi #1);
    fora dela, sai da sala de campanha em grupo se estiver numa (``handlers/room.py``).
    """
    if s.campaign is not None and s.campaign.map_id in PET_ISLANDS:
        s.campaign = None
        space.back(s)
        return
    from .tower import leave_maze  # tower importa campaign, que importa space

    if await leave_maze(s):
        return
    if s.ctx.rooms.of(s.player_id) is not None:
        leave_room(s)
        return
    from .altar import leave as leave_altar  # altar importa space
    from .guildwar import leave_war  # guildwar importa space
    from .hangup import leave_room as leave_hook  # hangup importa space
    from .warfield import leave_field  # warfield importa space
    from .wedding import leave as leave_wedding  # wedding importa space
    from .worldboss import leave_boss  # worldboss importa space

    if leave_boss(s) or leave_altar(s) or leave_wedding(s) or leave_field(s) or leave_war(s) or leave_quarry(s):
        return
    if await leave_hook(s):
        return
    s.log.info("5025 sem ilha dos pets nem sala", mapa=s.campaign and s.campaign.map_id)


@router.on(8700)
async def check_moveable(s: GameSession, _: object) -> None:
    # resetSpacePosition: devolve o jogador ao último tile conhecido (sem chamador no cliente hoje)
    if s.space_pos is not None:
        s.send(S_STAND, pb.StandPosMsg(id=s.player_id, posX=s.space_pos[0], posY=s.space_pos[1]))


@router.on(8701)
async def space_player_info(s: GameSession, msg: pb.SpacePlayerArmyInfoReqMsg) -> None:
    """Dados de jogadores do space; não há resposta própria, vai no 4597 como os presentes."""
    wanted = set(msg.userList[:MAX_USERS])
    found = [o for o in space.others(s) if o.player_id in wanted]
    if found:
        s.send(space.S_PRESENT, pb.RoomEnterMsg(result=1, player=[space.member(o) for o in found]))


@router.on(8733)
async def collection_finished(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    # coleta só começa com um 143 "COLLECTION" do servidor, que ainda não mandamos: nada a dar
    s.log.info("8733 coleta sem coleta iniciada", no=msg.param1)
