"""Salas de campanha (PvE), times e os 29 opcodes da lista: registro, corpo vazio e fluxo da sala."""

from __future__ import annotations

from pathlib import Path

from google.protobuf.message import Message

from tests.game.harness import logged_in
from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.game.router import router
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

CODES = [
    5023, 5024, 5026, 5029, 5030, 5031, 5033, 5038, 5120, 5121, 5122, 5126, 5180,
    8297, 8300, 8465, 8526, 8528, 8734, 8736, 8737, 8738, 8739, 8742,
    8752, 8753, 8754, 8755, 9504,
]  # fmt: skip
ROOM_CREATED, ROOM_LIST, PLACE, MEMBERS, TEAM_INVITE = 12, 13, 17, 120, 4620
EXIT, KILL, MASTER = 15, 28, 121  # RoomExitRspMsg (saiu), KillPlayerRspMsg (expulso), ChangeMasterRspMsg


def _body[M: Message](packets: list[Packet], code: int, msg_type: type[M]) -> M:
    return msg_type.FromString(next(p.body for p in packets if p.code == code))


def _ids(members: pb.RoomPlayerListMsg) -> list[int]:
    return sorted(p.playerId for p in members.roomPlayer)


def test_os_29_opcodes_tem_handler_e_o_5025_tambem():
    assert [code for code in CODES if router.get(code) is None] == []
    assert router.get(5025) is not None


async def test_corpo_vazio_nao_derruba_a_sessao(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as g:
        for code in [*CODES, 5025]:
            g.client.send(code)  # sem corpo
        await g.idle(0.3)
        g.client.send(5026)  # a sessão ainda responde
        got = await g.idle()
        assert any(p.code == ROOM_LIST for p in got)


async def test_sala_criar_entrar_expulsar_sair(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")

        a.client.send(5023, pb.RoomReqMsg(capacity=3))
        got_a = await a.idle()
        room = _body(got_a, ROOM_CREATED, pb.RoomMsg)
        assert room.masterId == a.user_id and room.capacity == 3
        assert _ids(_body(got_a, MEMBERS, pb.RoomPlayerListMsg)) == [a.user_id]
        room_id = room.roomId

        b.client.send(5026, pb.RoomReqMsg())
        listed = _body(await b.idle(), ROOM_LIST, pb.RoomListRspMsg)
        assert [r.roomId for r in listed.room] == [room_id]

        b.client.send(5024, pb.RoomReqMsg(roomId=room_id))
        got_b = await b.idle()
        got_a = await a.idle()
        assert ROOM_CREATED in [p.code for p in got_b]
        assert _ids(_body(got_a, MEMBERS, pb.RoomPlayerListMsg)) == sorted([a.user_id, b.user_id])

        b.client.send(5029, pb.RoomReqMsg(index=1, open=False))  # não é o dono: recusado
        got_b = await b.idle()
        assert PLACE in [p.code for p in got_b]  # volta o estado atual para quem pediu
        assert MEMBERS not in [p.code for p in await a.idle()]

        a.client.send(5029, pb.RoomReqMsg(index=2, open=False))  # dono fecha o lugar 2
        got_a = await a.idle()
        place = _body(got_a, PLACE, pb.PlaceStateRspMsg)
        assert list(place.placeState)[2] == -1  # CLOSED

        a.client.send(5031, pb.RoomReqMsg(userId=b.user_id))  # dono expulsa
        got_a = await a.idle()
        got_b = await b.idle()
        assert _ids(_body(got_a, MEMBERS, pb.RoomPlayerListMsg)) == [a.user_id]
        assert KILL in [p.code for p in got_b]

        b.client.send(5024, pb.RoomReqMsg(roomId=room_id))  # volta a entrar
        await b.idle()
        await a.idle()
        b.client.send(5120, pb.RoomExitMsg())  # sai: o dono continua
        assert EXIT in [p.code for p in await b.idle()]
        assert _ids(_body(await a.idle(), MEMBERS, pb.RoomPlayerListMsg)) == [a.user_id]

        b.client.send(5024, pb.RoomReqMsg(roomId=room_id))  # de novo, e a saída do dono dissolve
        await b.idle()
        await a.idle()
        a.client.send(5120, pb.RoomExitMsg())
        assert EXIT in [p.code for p in await a.idle()]
        got_b = await b.idle()
        assert EXIT in [p.code for p in got_b]
        b.client.send(5026, pb.RoomReqMsg())
        assert list(_body(await b.idle(), ROOM_LIST, pb.RoomListRspMsg).room) == []


async def test_convite_so_para_amigo_online(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        a.client.send(8738, pb.SimplePropertyMsg(param1=b.user_id))  # sem amizade: nada chega a b
        got_b = await b.idle()
        assert TEAM_INVITE not in [p.code for p in got_b]


async def test_queda_do_membro_avisa_quem_ficou(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        a.client.send(5023, pb.RoomReqMsg(capacity=2))
        room = _body(await a.idle(), ROOM_CREATED, pb.RoomMsg)
        b.client.send(5024, pb.RoomReqMsg(roomId=room.roomId))
        await b.idle()
        await a.idle()
        b.client.writer.close()  # desconexão: o teardown tira b da sala antes do unbind
        got_a = await a.idle(0.3)
        assert _ids(_body(got_a, MEMBERS, pb.RoomPlayerListMsg)) == [a.user_id]


async def test_dono_passa_o_comando(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        a.client.send(5023, pb.RoomReqMsg(capacity=2))
        room = _body(await a.idle(), ROOM_CREATED, pb.RoomMsg)
        b.client.send(5024, pb.RoomReqMsg(roomId=room.roomId))
        await b.idle()
        await a.idle()
        a.client.send(5030, pb.CampaignReqMsg(paraInt1=b.user_id))
        got_b = await b.idle()
        assert _body(got_b, MASTER, pb.ChangeMasterRspMsg).masterId == b.user_id
        b.client.send(5029, pb.RoomReqMsg(index=1, open=False))  # agora b é o dono: fecha o lugar 1
        assert PLACE in [p.code for p in await b.idle()]
        a.client.send(5029, pb.RoomReqMsg(index=1, open=True))  # a já não manda: recusado
        assert PLACE in [p.code for p in await a.idle()]
