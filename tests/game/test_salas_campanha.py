"""Salas de campanha (PvE), times e os 36 opcodes da lista: registro, corpo vazio e fluxo da sala."""

from __future__ import annotations

from pathlib import Path

import pytest
from google.protobuf.message import Message

from tests.game.harness import logged_in
from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.game.router import router
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

CODES = [
    5023, 5024, 5026, 5028, 5029, 5030, 5031, 5033, 5034, 5036, 5037, 5038, 5120, 5121, 5122, 5126, 5180,
    8296, 8297, 8299, 8300, 8344, 8465, 8526, 8528, 8734, 8736, 8737, 8738, 8739, 8742,
    8752, 8753, 8754, 8755, 9504,
]  # fmt: skip
ROOM_CREATED, ROOM_LIST, PLACE, MEMBERS, TEAM_INVITE = 12, 13, 17, 120, 4620
EDIT = 32  # EditRoomRspMsg
EXIT, KILL, MASTER = 15, 28, 121  # RoomExitRspMsg (saiu), KillPlayerRspMsg (expulso), ChangeMasterRspMsg


def _body[M: Message](packets: list[Packet], code: int, msg_type: type[M]) -> M:
    return msg_type.FromString(next(p.body for p in packets if p.code == code))


def _ids(members: pb.RoomPlayerListMsg) -> list[int]:
    return sorted(p.playerId for p in members.roomPlayer)


def test_os_36_opcodes_tem_handler_e_o_5025_tambem():
    assert [code for code in CODES if router.get(code) is None] == []
    assert router.get(5025) is not None


async def test_corpo_vazio_nao_derruba_a_sessao(tmp_path: Path, capfd: pytest.CaptureFixture[str]):
    async with logged_in(tmp_path, novice=19000) as g:
        capfd.readouterr()  # descarta o log do login
        for code in [*CODES, 5025]:
            g.client.send(code)  # sem corpo
        await g.idle(0.3)
        g.client.send(5026)  # a sessão ainda responde
        got = await g.idle()
        assert any(p.code == ROOM_LIST for p in got)
        out = capfd.readouterr()
        assert "erro tratando pacote" not in out.out + out.err  # handler que levanta derruba o pacote


async def test_sala_criar_entrar_expulsar_sair(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")

        a.client.send(5023, pb.RoomReqMsg(capacity=1))  # o PVERoomListControler sempre manda 1
        got_a = await a.idle()
        # (visto) 191924 #3736-#3741: 12, 17, 32, 120 e 4186; 4 lugares e "Select a campaign."
        assert [p.code for p in got_a if p.code != 11] == [ROOM_CREATED, PLACE, EDIT, MEMBERS, 4186]  # 11: o "outro"
        room = _body(got_a, ROOM_CREATED, pb.RoomMsg)
        assert (room.masterId, room.capacity, room.name) == (a.user_id, 4, "Select a campaign.")
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


async def test_dono_escolhe_a_campanha_e_todos_recebem_o_32(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        a.client.send(5023, pb.RoomReqMsg(capacity=4))
        room_id = _body(await a.idle(), ROOM_CREATED, pb.RoomMsg).roomId
        b.client.send(5024, pb.RoomReqMsg(roomId=room_id))
        await b.idle()
        await a.idle()

        b.client.send(5034, pb.RoomReqMsg(roomId=room_id, campaignId=9001))  # não é o dono
        a.client.send(5034, pb.RoomReqMsg(roomId=room_id, campaignId=12345))  # campanha que não existe
        assert await b.idle() == [] and await a.idle() == []

        a.client.send(5034, pb.RoomReqMsg(roomId=room_id, dungeonId=1, campaignId=9001))  # InstanceSelectFrame
        for g in (a, b):
            got = await g.idle()
            assert [p.code for p in got] == [EDIT, 24]  # (visto) 191924 #3746-#3747
            edit = pb.EditRoomRspMsg.FromString(got[0].body)
            assert (edit.roomId, edit.startCampaignId, edit.masterId, edit.count) == (room_id, 9001, a.user_id, 2)
            assert edit.roomName == "Claristun"  # o CampaignName (oficial: "Nether Forest" na 9000)


async def test_pronto_senha_estado_e_convite_da_sala(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        c = await a.join("terceiro")
        a.client.send(5023, pb.RoomReqMsg(capacity=4))
        room_id = _body(await a.idle(), ROOM_CREATED, pb.RoomMsg).roomId

        a.client.send(5028, pb.RoomReqMsg(userId=b.user_id))  # InviteItem
        invite = _body(await b.idle(), 16, pb.RoomInviteMsg)
        assert (invite.roomId, invite.playerId, invite.nickName, invite.roomType) == (room_id, a.user_id, "Maga", 0)
        assert _body(await a.idle(), 111, pb.ChatChannelMsg).encodeMsg == "Invitation sent."  # (visto) 191924 #3774

        b.client.send(5024, pb.RoomReqMsg(roomId=room_id, isInvite=True))
        members = _body(await b.idle(), MEMBERS, pb.RoomPlayerListMsg)
        assert {p.playerId: p.playerState for p in members.roomPlayer} == {a.user_id: 2, b.user_id: 0}  # 0: Ready
        await a.idle()

        a.client.send(5036, pb.RoomReqMsg(state=1))  # o dono não tem "pronto"
        b.client.send(5036, pb.RoomReqMsg(state=1, isGet=True))
        for g in (a, b):
            ready = _body(await g.idle(), 24, pb.PlayerReadyRspMsg)
            assert {r.playerId: r.readyState for r in ready.readyState} == {a.user_id: 2, b.user_id: 1}

        a.client.send(8344, pb.RoomEditMsg(roomId=room_id, roomPwd="abc"))  # RoomPasswordFrame: só dígitos
        b.client.send(8344, pb.RoomEditMsg(roomId=room_id, roomPwd="123"))  # não é o dono
        assert await a.idle() == [] and await b.idle() == []
        a.client.send(8344, pb.RoomEditMsg(roomId=room_id, roomPwd="123456"))
        for g in (a, b):
            assert pb.EditRoomRspMsg.FromString((await g.until(EDIT))[-1].body).passWord == "123456"

        a.client.send(5037, pb.RoomReqMsg(state=1))
        for g in (a, b):
            assert _body(await g.idle(), 25, pb.RoomStateRspMsg).roomState == 1

        a.client.send(5028, pb.RoomReqMsg(userId=b.user_id))  # já está numa sala
        assert _body(await a.idle(), 111, pb.ChatChannelMsg).encodeMsg == "Player is in another room."  # #3770
        c.client.send(8286)  # recusa convites
        await c.idle()
        a.client.send(5028, pb.RoomReqMsg(userId=c.user_id))
        assert _body(await a.idle(), 111, pb.ChatChannelMsg).encodeMsg == "Invitations have been sent"  # #3776
        assert 16 not in [p.code for p in await b.idle()] and 16 not in [p.code for p in await c.idle()]


async def test_reset_do_labirinto_volta_o_4205_no_andar_0_e_entrar_nao_muda_nada(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8296, pb.EnterTowerInfoMsg(campaignId=8001, chooseIndex=1, isDouble=2))  # sem andares: nada
        assert await g.idle() == []
        g.client.send(8299, pb.TowerInfoReqMsg(index=1))  # MazeFrame: reset depois da confirmação
        info = _body(await g.idle(), 4205, pb.TowerInfoMsg)
        assert (info.index, info.towerIndex, info.campaignId) == (1, 0, 8101)  # aba 1: Tormented Necropolis


async def test_aba_hall_do_convite_lista_quem_esta_online_fora_de_sala(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        c = await a.join("terceiro")
        c.client.send(5023, pb.RoomReqMsg(capacity=4))  # numa sala: fora do Hall
        await c.idle()
        a.client.send(5027)  # RoomInviteFrame, aba Hall
        hall = _body(await a.idle(), 4161, pb.RoomPlayerListMsg)
        assert [(p.playerId, p.nickName, p.playerState) for p in hall.roomPlayer] == [(b.user_id, "Outro", 1)]


async def test_clicar_numa_sala_da_lista_devolve_o_4370_e_a_lista_filtra_pela_campanha(tmp_path: Path):
    """PVERoomItem só entra com ``roomState`` 1; o clique manda o 8465 e espera o 4370 (PVERoomListControler)."""
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        a.client.send(5023, pb.RoomReqMsg(capacity=2))
        room = _body(await a.idle(), 12, pb.RoomMsg)
        assert room.roomState == 1
        b.client.send(5026, pb.RoomReqMsg(nameKey="0"))
        assert [(r.roomId, r.roomState) for r in _body(await b.idle(), 13, pb.RoomListRspMsg).room] == [
            (room.roomId, 1)
        ]
        b.client.send(5026, pb.RoomReqMsg(nameKey="1001"))  # sem campanha escolhida: fora do filtro
        assert list(_body(await b.idle(), 13, pb.RoomListRspMsg).room) == []
        b.client.send(8465, pb.RoomReqMsg(roomId=room.roomId))
        assert _body(await b.idle(), 4370, pb.RoomMsg).roomId == room.roomId
        b.client.send(8465, pb.RoomReqMsg(roomId=0))  # entrada rápida: a primeira com lugar
        assert _body(await b.idle(), 4370, pb.RoomMsg).roomId == room.roomId
        b.client.send(8465, pb.RoomReqMsg(roomId=999))
        assert await b.idle() == []


async def test_convite_rapido_sai_no_mundo_como_link_da_sala(tmp_path: Path):
    """8353 (QuickInviteFrame): o 83 canal 10 ``type`` 4 com uma tag por linha (o ChatFormat.createRoomCellData lê
    ``position`` e ``name``), o leed 16 e a devoção, sem 4500 (visto 191924 #3763-#3766); sem sala não sai nada."""
    import xml.etree.ElementTree as ET

    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        lines = ["Thrills await you in [x] ", "room 1. Join now!"]
        sa = a.server.online.get(a.user_id)
        assert sa is not None and sa.snapshot is not None
        sa.snapshot.character.grades = 20  # chat: nível mínimo 6
        await a.idle()
        await b.idle()
        a.client.send(8353, pb.CaptainSpeakMsg(inviteContent=lines, type=0))
        assert await a.idle() == [] and await b.idle() == []

        a.client.send(5023, pb.RoomReqMsg(capacity=4, password="x"))
        room_id = _body(await a.idle(), ROOM_CREATED, pb.RoomMsg).roomId
        a.client.send(5034, pb.RoomReqMsg(roomId=room_id, dungeonId=1, campaignId=9001))
        await a.idle()
        a.client.send(8353, pb.CaptainSpeakMsg(inviteContent=lines, type=0))
        mine = [p.code for p in await a.idle()]
        assert mine == [83, 4152, 83] and 4500 not in mine
        chat = _body(await b.idle(), 83, pb.ChatChannelMsg)
        assert (chat.channel, chat.type, chat.otherId) == (10, 4, a.user_id)
        tags = list(ET.fromstring(f"<x>{chat.encodeMsg}</x>"))
        assert [(t.tag, t.attrib["name"]) for t in tags] == [("a", lines[0]), ("a", lines[1])]
        assert {k: v for k, v in tags[0].attrib.items() if k != "name"} == {
            "t": "6",
            "id": str(room_id),
            "campaignId": "9001",
            "islock": "0",
            "position": "0",  # com senha: trancada
            "roomType": "0",
        }
