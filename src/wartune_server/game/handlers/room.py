"""Salas em grupo (campanha PvE e veículo): criar, listar, procurar, entrar, lugares, dono, expulsar e sair.

Estado em ``GameContext.rooms`` (``game/rooms.py``). Sequência vista numa sala da campanha 9001 (Claristun) (só turco:
exp_kitabi_kullanim_kahraman_sarayi_ve_ek_sahne_giris_ek_sahne_mob #17-#23): 5023 -> 12 RoomMsg,
17 PlaceStateRspMsg, 32 EditRoomRspMsg, 120 RoomPlayerListMsg. O dono escolhe a campanha no 5034; começar a
campanha da sala (125/21) ver docs/salas-campanha.md. A sala de veículo (``VehicleRoomFrame``) começa no 5039 e
cancela a procura no 5037 (``handlers/vehicle.py``).
"""

from __future__ import annotations

from google.protobuf.message import Message

from ...protocol.messages import wartune_pb2 as pb
from .. import rules, space
from .. import vehicles as vh
from ..rooms import IN_USE, MAX_SEATS, NAME_NEW, PVE, VEHICLE, Room
from ..router import router
from ..session import GameSession

S_ROOM, S_ROOM_LIST, S_PLACE, S_EDIT, S_MEMBERS = 12, 13, 17, 32, 120
S_FOUND = 4370  # RoomMsg: o PVERoomListControler entra sozinho (5024) ou abre a senha (U_C_ROOM_FIND_RESULT)
S_EXIT, S_KILL, S_MASTER = 15, 28, 121
S_INVITE, S_READY, S_STATE = 16, 24, 25  # RoomInviteMsg, PlayerReadyRspMsg, RoomStateRspMsg
S_HALL = 4161  # RoomPlayerListMsg: aba Hall do RoomInviteFrame (U_C_INVITE_PLAYER_LIST)
S_WAITING = 11  # RoomPlayerListMsg: PlayerManager.watingList, a lista de jogadores da sala de veículo
LEFT, JOINED = 0, 1  # state do 11: 1 entra na lista, 0 sai (PlayerManager.__playerListHandler)
ONLINE = 1  # playerState da aba Hall: o cliente só lista com state != 0 (SimplePlayerInfo.isOnline)
S_REFUSE_INVITE = 4194  # RefuseFriendRspMsg: estado da recusa de convites (8286)
S_ALERT = 111
S_ROOM_STATE = 4913  # SimplePropertyMsg: sala do link no chat (9504), BaseManager.__mulityCampaignRequestHandler
# playerState/readyState: 0 sem "pronto" (o RoomRightView mostra o botão Ready), 1 pronto (5036 state 1; o
# PVPRoomPlayerFigure desenha 0 e 1), 2 o dono (só turco, #20)
NOT_READY, READY, OWNER = 0, 1, 2
PASSWORD_MAX = 6  # RoomPasswordFrame: maxChars 6, restrict "0-9"


def _name(s: GameSession, room: Room) -> str:
    """Nome da sala: o ``CampaignName`` da campanha escolhida (visto 191924 #3746 e #3762 "Nether Forest"), ou
    NAME_NEW antes da escolha (#3737)."""
    row = s.ctx.templates.get("Campaigns", room.campaign, key="CampaignId") if room.campaign else None
    return row["CampaignName"] if row else NAME_NEW


def _room_msg(s: GameSession, room: Room) -> pb.RoomMsg:
    return pb.RoomMsg(
        roomId=room.id,
        campaignId=room.campaign,
        masterId=room.master,
        name=_name(s, room),
        count=len(room.members),
        capacity=room.capacity,
        roomType=room.type,
        isSetPassword=bool(room.password),
        roomState=room.state,
    )


def _list_msg(s: GameSession, rooms: list[Room]) -> pb.RoomListRspMsg:
    return pb.RoomListRspMsg(room=[_room_msg(s, r) for r in rooms])


def _of_type(msg: pb.RoomReqMsg, rooms: list[Room]) -> list[Room]:
    """Só as salas do tipo pedido (PvP não tem sala aqui: vem vazio)."""
    return [r for r in rooms if r.type == msg.roomType]


def _members_msg(s: GameSession, room: Room) -> pb.RoomPlayerListMsg:
    out = pb.RoomPlayerListMsg()
    for index, pid in enumerate(room.seats):
        other = s.ctx.online.get(pid) if pid > 0 else None
        if other is None or other.snapshot is None or other.snapshot.leader is None:
            continue  # offline some da lista; a sessão dele já saiu pelo on_disconnect
        snap = other.snapshot
        entry = space.room_player(
            snap,
            s.ctx.templates,
            other.space_pos or (0, 0),
            room.campaign,
            s.ctx.clock.now(),
            cloth=rules.cloth_avatar(snap, s.ctx.templates),
        )
        entry.roomId, entry.count, entry.currentRoomIndex, entry.playerState = (
            room.id,
            len(room.members),
            index,
            _ready_state(room, pid),
        )
        out.roomPlayer.extend([entry])
    return out


def _edit_msg(s: GameSession, room: Room) -> pb.EditRoomRspMsg:
    return pb.EditRoomRspMsg(
        roomId=room.id,
        startCampaignId=room.campaign,
        masterId=room.master,
        count=len(room.members),
        capacity=room.capacity,
        passWord=room.password,
        roomName=_name(s, room),
    )


def _ready_state(room: Room, pid: int) -> int:
    return OWNER if pid == room.master else READY if pid in room.ready else NOT_READY


def _to_room(s: GameSession, room: Room, code: int, msg: Message) -> None:
    for pid in room.members:
        if (other := s.ctx.online.get(pid)) is not None:
            other.send(code, msg)


def _sync(s: GameSession, room: Room) -> None:
    """Estado da sala para quem está nela: lugares, dono/senha e jogadores."""
    place = pb.PlaceStateRspMsg(placeState=room.seats)
    edit = _edit_msg(s, room)
    members = _members_msg(s, room)
    for pid in room.members:
        other = s.ctx.online.get(pid)
        if other is not None:
            other.send(S_PLACE, place)
            other.send(S_EDIT, edit)
            other.send(S_MEMBERS, members)


def _master_room(s: GameSession) -> Room | None:
    room = s.ctx.rooms.of(s.player_id)
    return room if room is not None and room.master == s.player_id else None


def _refuse(s: GameSession, room: Room | None) -> None:
    """Pedido recusado: manda o estado atual de volta a quem pediu, para a tela não ficar diferente."""
    if room is not None:
        s.send(S_PLACE, pb.PlaceStateRspMsg(placeState=room.seats))


def _exit_notice(s: GameSession, to: list[int], player_id: int) -> None:
    """15 RoomExitRspMsg: o cliente de ``player_id`` sai da sala (RoomManager.__returnRoomHandler)."""
    for pid in to:
        other = s.ctx.online.get(pid)
        if other is not None:
            other.send(S_EXIT, pb.RoomExitRspMsg(playerId=player_id))


def leave_room(s: GameSession) -> None:
    """Sai da sala (5025/5120 ou desconexão). Quem sai recebe o 15 com o próprio id (o cliente volta à lista).

    O dono sair dissolve a sala: cada um dos que estavam nela recebe o 15 com o próprio id.
    """
    mine = s.ctx.rooms.of(s.player_id)
    # sala de veículo procurando: a sala inteira sai da fila (a fila solo do 8608 não é daqui)
    queued = s.ctx.vehicles.dequeue(s.player_id) if mine is not None and mine.type == VEHICLE else None
    left = s.ctx.rooms.leave(s.player_id)
    if left is None:
        return
    room, dissolved = left
    if queued is not None and not dissolved:
        room.state = IN_USE
        _to_room(s, room, S_STATE, pb.RoomStateRspMsg(roomState=IN_USE))
    if dissolved:  # o registro já tirou todos; ``room.members`` ainda lista quem estava
        for pid in room.members:
            _exit_notice(s, [pid], pid)
    else:
        _exit_notice(s, [*room.members, s.player_id], s.player_id)
        _sync(s, room)


@router.on(5023)
async def create_room(s: GameSession, msg: pb.RoomReqMsg) -> None:
    if msg.roomType not in (PVE, VEHICLE):  # PvP (1) não tem sala aqui: recusa, sem criar sala de outro tipo
        s.log.info("5023 recusado: tipo de sala sem sistema", tipo=msg.roomType)
        return
    if s.ctx.rooms.of(s.player_id) is not None:
        s.log.info("5023 recusado: já está numa sala")
        return
    # o capacity do pedido não são lugares: o PVERoomListControler manda 1 e o oficial abre a sala com 4 (visto
    # 191924 #3736-#3738); fechar lugares é o 5029
    room = s.ctx.rooms.create(s.player_id, MAX_SEATS, msg.password, msg.roomType)
    if room.type == VEHICLE:
        room.campaign = vh.CAMPAIGN  # a sala de veículo só leva à batalha de tanques
    s.send(S_ROOM, _room_msg(s, room))
    _sync(s, room)
    if room.type == PVE:
        from .army import S_TEAM_POS, team_pos  # army importa player, que importa este módulo

        s.send(S_TEAM_POS, team_pos(s))  # (visto) #3741: 4186 depois do 120


@router.on(5024)
async def enter_room(s: GameSession, msg: pb.RoomReqMsg) -> None:
    room = s.ctx.rooms.get(msg.roomId)
    if room is None or room.type != msg.roomType or s.ctx.rooms.of(s.player_id) is not None:
        s.log.info("5024 recusado", sala=msg.roomId)
        return
    if room.password and room.password != msg.password:
        s.log.info("5024 senha errada", sala=msg.roomId)
        return
    if not s.ctx.rooms.join(room, s.player_id):  # sala cheia
        s.log.info("5024 sala cheia", sala=msg.roomId)
        return
    s.send(S_ROOM, _room_msg(s, room))
    _sync(s, room)


@router.on(5026)
async def list_rooms(s: GameSession, msg: pb.RoomReqMsg) -> None:
    """``nameKey`` é a campanha do filtro da lista (``RoomListSocketOutManager.requestRoomList``; "0" = todas)."""
    key = int(msg.nameKey) if msg.nameKey.isdigit() else 0
    rooms = [r for r in _of_type(msg, s.ctx.rooms.visible()) if not key or r.campaign == key]
    s.send(S_ROOM_LIST, _list_msg(s, rooms))


@router.on(8465)
async def find_room(s: GameSession, msg: pb.RoomReqMsg) -> None:
    """Clicar numa sala da lista ou procurar pelo número (``PVERoomItem``, ``PVERoomSearchFrame``): 4370 com a sala,
    e o cliente manda o 5024 ou abre a senha. ``roomId`` 0 (entrada rápida do ``PVPPlayerListView``): a primeira com
    lugar livre (*dedução*). Sala que não existe fica sem resposta (o oficial não foi capturado)."""
    rooms = _of_type(msg, s.ctx.rooms.visible())
    room = next((r for r in rooms if r.id == msg.roomId or (not msg.roomId and len(r.members) < r.capacity)), None)
    if room is None:
        s.log.info("8465 sem sala", sala=msg.roomId)
        return
    s.send(S_FOUND, _room_msg(s, room))


@router.on(5029)
async def place_state(s: GameSession, msg: pb.RoomReqMsg) -> None:
    room = s.ctx.rooms.of(s.player_id)
    if room is None or room.master != s.player_id or not s.ctx.rooms.toggle_seat(room, msg.index, msg.open):
        s.log.info("5029 recusado", lugar=msg.index)
        _refuse(s, room)
        return
    _sync(s, room)


@router.on(5030)
async def change_master(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    room = _master_room(s)
    if room is None or not s.ctx.rooms.hand_over(room, msg.paraInt1):
        s.log.info("5030 recusado", novo=msg.paraInt1)
        return
    for pid in room.members:
        other = s.ctx.online.get(pid)
        if other is not None:
            other.send(S_MASTER, pb.ChangeMasterRspMsg(roomId=room.id, masterId=room.master))
    _sync(s, room)


@router.on(5031)
async def kick_member(s: GameSession, msg: pb.RoomReqMsg) -> None:
    room = _master_room(s)
    if room is None or msg.userId == s.player_id or msg.userId not in room.members:
        s.log.info("5031 recusado", alvo=msg.userId)
        return
    # 28 KillPlayerRspMsg: o expulso também recebe, e o cliente dele volta à lista (__campaingkillOutHandler)
    kill = pb.KillPlayerRspMsg(roomId=room.id, killedPlayerId=msg.userId)
    for pid in room.members:
        other = s.ctx.online.get(pid)
        if other is not None:
            other.send(S_KILL, kill)
    s.ctx.rooms.leave(msg.userId)  # alvo não é o dono (checado acima): só tira o lugar
    _sync(s, room)


@router.on(5034)
async def edit_room(s: GameSession, msg: pb.RoomReqMsg) -> None:
    """Campanha da sala: ``InstanceSelectFrame`` -> ``RoomSocketOuterManager.updateRoomInfo`` (``roomId``,
    ``dungeonId``, ``campaignId``). Só o dono, com campanha do ``Campaigns``. Todos da sala recebem o 32
    (``RoomManager.__updateRoomInfoHandler`` lê ``startCampaignId``, dono, contagem e senha)."""
    room = _master_room(s)
    known = s.ctx.templates.get("Campaigns", msg.campaignId, key="CampaignId") is not None
    if room is None or room.id != msg.roomId or not known:
        s.log.info("5034 recusado", sala=msg.roomId, campanha=msg.campaignId)
        return
    room.campaign = msg.campaignId
    _to_room(s, room, S_EDIT, _edit_msg(s, room))
    _send_ready(s, room)  # (visto) #3746-#3747: 32 e o 24 com o estado de cada um (o dono 2)


@router.on(8344)
async def room_password(s: GameSession, msg: pb.RoomEditMsg) -> None:
    """Senha da sala (cadeado do ``RoomRightView`` -> ``RoomPasswordFrame``: até 6 dígitos; vazio tira). Só o dono;
    todos recebem o 32 com o ``passWord`` (``RoomManager.__updateRoomInfoHandler``)."""
    room = _master_room(s)
    pwd = msg.roomPwd
    if room is None or room.id != msg.roomId or len(pwd) > PASSWORD_MAX or not (pwd.isdigit() or pwd == ""):
        s.log.info("8344 recusado", sala=msg.roomId)
        return
    room.password = pwd
    _to_room(s, room, S_EDIT, _edit_msg(s, room))


@router.on(5036)
async def player_ready(s: GameSession, msg: pb.RoomReqMsg) -> None:
    """Pronto (``state`` 1) ou cancelar (0) de quem não é o dono (``RoomRightView.sendPlayerReady``/``_cancelClick``).
    Todos da sala recebem o 24 com o estado de cada um (``RoomManager.__updateReaderStateHandler``). O ``isGet``
    (receber o prêmio da campanha) só vale quando a campanha da sala começar."""
    room = s.ctx.rooms.of(s.player_id)
    if room is None or room.master == s.player_id or msg.state not in (NOT_READY, READY):
        s.log.info("5036 recusado", estado=msg.state)
        return
    if msg.state == READY:
        room.ready.add(s.player_id)
    else:
        room.ready.discard(s.player_id)
    if msg.state == READY and msg.isGet:
        room.rewarded.add(s.player_id)
    else:
        room.rewarded.discard(s.player_id)
    _send_ready(s, room)


def _send_ready(s: GameSession, room: Room) -> None:
    states = [pb.PlayerreadyrspmsgPlayerReady(playerId=pid, readyState=_ready_state(room, pid)) for pid in room.members]
    _to_room(s, room, S_READY, pb.PlayerReadyRspMsg(readyState=states))


@router.on(5037)
async def room_state(s: GameSession, msg: pb.RoomReqMsg) -> None:
    """Estado da sala (PvP e veículo mandam 1 ao começar: ``PVPRoomRightView``, ``VehicleRoomFrame``). Só o dono;
    todos recebem o 25 (``RoomManager.__updateRoomStateHandler``). Na sala de veículo o 1 é o Cancel do dono
    procurando (``VehicleRoomFrame.__cancelClickHandler``): a sala sai da fila."""
    room = _master_room(s)
    if room is None:
        s.log.info("5037 recusado", estado=msg.state)
        return
    if room.type == VEHICLE and msg.state == IN_USE:
        s.ctx.vehicles.dequeue(s.player_id)
    room.state = msg.state
    _to_room(s, room, S_STATE, pb.RoomStateRspMsg(roomState=room.state))


@router.on(5028)
async def invite(s: GameSession, msg: pb.RoomReqMsg) -> None:
    """Convite para a sala (``InviteItem``/``InviteItemButton`` -> ``sendRoomInvite(userId)``): o convidado recebe o 16
    (``BaseManager.__roomInviteHandler``). ``signStr`` é a senha que o aceite manda no 5024 (``InviteFrame``); ``name``
    a campanha escolhida (vazio: o cliente põe o texto padrão); ``tempId`` a campanha (aviso de estamina). Quem está
    offline, já numa sala ou recusa convites (8286) não recebe.

    Quem convida recebe um 111 (visto 191924 #3769-#3806): "Player is in another room." com o alvo numa sala,
    "Invitation sent." ou "Invitations have been sent". (dedução) o primeiro quando o convite chega ao alvo e o segundo
    quando não chega: só o 191 recebeu o primeiro, e os outros (110, 216, 331, 6) nunca entraram.
    """
    room = s.ctx.rooms.of(s.player_id)
    if room is None:
        s.log.info("5028 recusado: sem sala", alvo=msg.userId)
        return
    if s.ctx.rooms.of(msg.userId) is not None:
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Player is in another room."))
        return
    other = s.ctx.online.get(msg.userId)
    target = other.snapshot.character if other is not None and other.snapshot is not None else None
    if target is None or target.refuse_invite:
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Invitations have been sent"))
        return
    assert other is not None and s.snapshot is not None
    row = s.ctx.templates.get("Campaigns", room.campaign, key="CampaignId") if room.campaign else None
    other.send(S_INVITE, pb.RoomInviteMsg(
        roomId=room.id, playerId=s.player_id, nickName=s.snapshot.character.nickname or "",
        name=(row or {}).get("CampaignName", ""), signStr=room.password, roomType=room.type, tempId=room.campaign,
        position=0,
    ))  # fmt: skip
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Invitation sent."))


@router.on(5120)
async def exit_room(s: GameSession, _: pb.RoomExitMsg) -> None:
    leave_room(s)


@router.on(9504)
async def multi_campaign(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Link de sala no chat (``sendSearchRoomState``, ``param1`` = roomId): responde 4913 com a sala.

    (cliente) BaseManager.__mulityCampaignRequestHandler: ``param1`` é o id, ``param2`` a campanha (0 = sem
    campanha). ``param7`` vai para ``isInCampaign``, que troca o alerta de entrada (``EnterCampaignTips``, em
    ``confirmBack``). (dedução) ``param7`` = quem pediu está numa campanha, lido de ``s.campaign``; o cliente
    tem a mesma leitura em ``SwitchPageHelp.isInCampaign`` (cena do pedidor). ``WorldBossHelper.getCampaignTips``
    não serve de fonte: só cobre mapas especiais. Leitura alternativa (sala iniciada -> False) não se separa
    aqui, porque salas não iniciam no servidor. Sala inexistente fica sem resposta (dedução, sem captura).
    """
    room = s.ctx.rooms.get(msg.param1)
    if room is None:
        s.log.info("9504 sala inexistente", sala=msg.param1)
        return
    s.send(S_ROOM_STATE, pb.SimplePropertyMsg(param1=room.id, param2=room.campaign, param7=s.campaign is not None))


@router.on(5027)
async def invite_hall(s: GameSession, _: object) -> None:
    """Aba Hall do convite da sala (``RoomInviteFrame``, aberto pelo botão de convite da sala PvE, PvP ou de veículo):
    o cliente lê o 4161 e lista quem está online, fora da lista negra (``relation`` 2) e não é ele. "Hall" aqui é
    quem está online e fora de uma sala (*dedução*, sem captura); o ``FreedomTeamInviteFrame`` (times) também manda,
    mas na aba 2 que não existe."""
    hall = pb.RoomPlayerListMsg()
    for other in s.ctx.online.sessions():
        snap = other.snapshot
        if other is s or snap is None or snap.leader is None or s.ctx.rooms.of(other.player_id) is not None:
            continue
        mine = s.ctx.guilds.of(other.player_id)
        entry = space.room_player(
            snap, s.ctx.templates, other.space_pos or (0, 0), 0, s.ctx.clock.now(), guild=mine[0] if mine else None
        )
        entry.sex, entry.playerState = snap.character.sex, ONLINE
        hall.roomPlayer.extend([entry])
    s.send(S_HALL, hall)


def _waiting_entry(other: GameSession) -> pb.RoomPlayerMsg:
    """Os campos do oficial (oficial_20261023-215937-1 #102), nada além: o cliente só lê esses."""
    from .vip import is_vip, vip_type  # vip importa este módulo

    snap = other.snapshot
    assert snap is not None and snap.leader is not None
    c, mine = snap.character, other.ctx.guilds.of(other.player_id)
    return pb.RoomPlayerMsg(
        playerState=other.chat_state,
        playerId=c.id,
        grades=c.grades,
        nickName=c.nickname or "",
        sex=c.sex,
        templateId=snap.leader.template_id,
        fightingCapacity=rules.leader_stats(snap, other.ctx.templates, other.ctx.clock.now()).fighting_capacity,
        consortiaId=mine[0].id if mine else 0,
        consortiaName=mine[0].name if mine else "",
        isVip=is_vip(snap, other.ctx.clock.now()),
        vipType=vip_type(snap),
    )


def waiting_login(s: GameSession) -> None:
    """11 no login: quem já está online, de uma vez (state 1), e o recém-chegado para cada um deles. (visto)
    oficial_20261023-231733-1: a lista inteira logo depois do 4151 (#105), e depois um 11 com um só jogador a cada
    entrada (state 1) ou saída (state 0) de outro, por todo o servidor. (dedução) é a presença online."""
    others = [o for o in s.ctx.online.sessions() if o is not s and o.snapshot is not None and o.snapshot.leader]
    if others:
        s.send(S_WAITING, pb.RoomPlayerListMsg(state=JOINED, roomPlayer=[_waiting_entry(o) for o in others]))
    waiting_broadcast(s, JOINED, others)


def waiting_broadcast(s: GameSession, state: int, others: list[GameSession] | None = None) -> None:
    """O 11 de um jogador só para todos os outros online (entrada ou saída)."""
    if s.snapshot is None or s.snapshot.leader is None:
        return
    msg = pb.RoomPlayerListMsg(state=state, roomPlayer=[_waiting_entry(s)])
    for other in others if others is not None else s.ctx.online.sessions():
        if other is not s and other.snapshot is not None:
            other.send(S_WAITING, msg)


@router.on(8286)
async def refuse_invite(s: GameSession, _: object) -> None:
    """Alterna a recusa de convites (``PlayerMsg.refuseInvite``). Quem recusa não recebe convite de guilda nem de
    sala (5028)."""
    assert s.snapshot is not None
    c = s.snapshot.character
    c.refuse_invite = not c.refuse_invite
    await s.ctx.characters.save(c)
    s.send(S_REFUSE_INVITE, pb.RefuseFriendRspMsg(result=c.refuse_invite))
