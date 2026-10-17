"""Salas de campanha em grupo (PvE): criar, listar, procurar, entrar, lugares, dono, expulsar e sair.

Estado em ``GameContext.rooms`` (``game/rooms.py``). Sequência vista na captura da sala "Büyük Kristal"
(exp_kitabi...ek_sahne): 5023 -> 12 RoomMsg, 17 PlaceStateRspMsg, 32 EditRoomRspMsg, 120 RoomPlayerListMsg.
Escolher a campanha da sala e começar a campanha (125/21) dependem de um pedido ainda não identificado
no cliente decompilado; ver docs/salas-campanha.md.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from .. import rules, space
from ..rooms import MAX_SEATS, NAME_NEW, PVE, Room
from ..router import router
from ..session import GameSession

S_ROOM, S_ROOM_LIST, S_PLACE, S_EDIT, S_MEMBERS = 12, 13, 17, 32, 120
S_EXIT, S_KILL, S_MASTER = 15, 28, 121
S_REFUSE_INVITE = 4194  # RefuseFriendRspMsg: estado da recusa de convites (8286)
PLAYER_READY = 2  # playerState do dono na captura; os demais ainda não foram vistos, usam o mesmo valor


def _room_msg(room: Room) -> pb.RoomMsg:
    return pb.RoomMsg(
        roomId=room.id,
        campaignId=room.campaign,
        masterId=room.master,
        name=NAME_NEW,  # o nome da campanha escolhida só aparece quando a escolha existir (dependência)
        count=len(room.members),
        capacity=room.capacity,
        roomType=PVE,
        isSetPassword=bool(room.password),
    )


def _list_msg(rooms: list[Room]) -> pb.RoomListRspMsg:
    return pb.RoomListRspMsg(room=[_room_msg(r) for r in rooms])


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
            cloth=rules.cloth_avatar(snap, s.ctx.templates),
        )
        entry.roomId, entry.count, entry.currentRoomIndex, entry.playerState = (
            room.id,
            len(room.members),
            index,
            PLAYER_READY,
        )
        out.roomPlayer.extend([entry])
    return out


def _sync(s: GameSession, room: Room) -> None:
    """Estado da sala para quem está nela: lugares, dono/senha e jogadores."""
    place = pb.PlaceStateRspMsg(placeState=room.seats)
    edit = pb.EditRoomRspMsg(
        roomId=room.id,
        startCampaignId=room.campaign,
        masterId=room.master,
        count=len(room.members),
        capacity=room.capacity,
        passWord=room.password,
        roomName=NAME_NEW,
    )
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
    left = s.ctx.rooms.leave(s.player_id)
    if left is None:
        return
    room, dissolved = left
    if dissolved:  # o registro já tirou todos; ``room.members`` ainda lista quem estava
        for pid in room.members:
            _exit_notice(s, [pid], pid)
    else:
        _exit_notice(s, [*room.members, s.player_id], s.player_id)
        _sync(s, room)


@router.on(5023)
async def create_room(s: GameSession, msg: pb.RoomReqMsg) -> None:
    if s.ctx.rooms.of(s.player_id) is not None:
        s.log.info("5023 recusado: já está numa sala")
        return
    capacity = msg.capacity if msg.HasField("capacity") else MAX_SEATS
    room = s.ctx.rooms.create(s.player_id, capacity, msg.password)
    s.send(S_ROOM, _room_msg(room))
    _sync(s, room)


@router.on(5024)
async def enter_room(s: GameSession, msg: pb.RoomReqMsg) -> None:
    room = s.ctx.rooms.get(msg.roomId)
    if room is None or s.ctx.rooms.of(s.player_id) is not None:
        s.log.info("5024 recusado", sala=msg.roomId)
        return
    if room.password and room.password != msg.password:
        s.log.info("5024 senha errada", sala=msg.roomId)
        return
    if not s.ctx.rooms.join(room, s.player_id):  # sala cheia
        s.log.info("5024 sala cheia", sala=msg.roomId)
        return
    s.send(S_ROOM, _room_msg(room))
    _sync(s, room)


@router.on(5026)
async def list_rooms(s: GameSession, _: pb.RoomReqMsg) -> None:
    s.send(S_ROOM_LIST, _list_msg(s.ctx.rooms.visible()))


@router.on(8465)
async def find_room(s: GameSession, msg: pb.RoomReqMsg) -> None:
    """Procurar sala: lista só a de ``roomId``; sem id, todas. Sem captura do pedido: só o filtro."""
    rooms = [r for r in s.ctx.rooms.visible() if not msg.roomId or r.id == msg.roomId]
    s.send(S_ROOM_LIST, _list_msg(rooms))


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


@router.on(5120)
async def exit_room(s: GameSession, _: pb.RoomExitMsg) -> None:
    leave_room(s)


@router.on(9504)
async def multi_campaign(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    # campanha multi (4913 SimplePropertyMsg): o pedido e o formato da resposta não foram identificados
    s.log.info("9504 sem resposta (dependência)", p1=msg.param1)


@router.on(5027)
async def invite_hall(s: GameSession, _: object) -> None:
    # FreedomTeamInviteFrame: o botão de atualizar só lista na aba 2, mas a aba de guilda é 0 e a de amigos 1,
    # então a aba 2 não existe na tela. Nada no cliente escuta resposta: só registramos.
    s.log.info("5027 sem efeito (aba inexistente no cliente)")


@router.on(8286)
async def refuse_invite(s: GameSession, _: object) -> None:
    """Alterna a recusa de convites (``PlayerMsg.refuseInvite``). Quem recusa não recebe convite de guilda."""
    assert s.snapshot is not None
    c = s.snapshot.character
    c.refuse_invite = not c.refuse_invite
    await s.ctx.characters.save(c)
    s.send(S_REFUSE_INVITE, pb.RefuseFriendRspMsg(result=c.refuse_invite))
