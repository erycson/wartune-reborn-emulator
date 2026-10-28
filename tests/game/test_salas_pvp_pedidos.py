"""Um teste por pedido de sala PvP e senha (captura 24/10 a partir de #11533 e 27/10 #19884-#20290)."""

from __future__ import annotations

from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

ROOM_CREATED, ROOM_STATE, ROOM_EDIT = 12, 25, 32
PVP = 1


def _alerts(packets: list[Packet]) -> list[str]:
    return [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in packets if p.code == 111]


async def test_8465_sem_sala_responde_cannot_find(tmp_path: Path) -> None:
    # (visto) 24/10 #11533-#11534 e 27/10 #19884-#19885: roomId 0, tipo 1, sem sala -> 111 "Cannot find a room."
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(8465, pb.RoomReqMsg(roomId=0, roomType=PVP))
        assert _alerts(await a.idle()) == ["Cannot find a room."]


async def test_8344_senha_avisa_set_e_removed(tmp_path: Path) -> None:
    # (visto) 27/10 #20270-#20286: 32 e depois 111 com "set" (senha "11", "3424") e "removed" (senha vazia)
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(5023, pb.RoomReqMsg(roomType=PVP, capacity=3))
        room = pb.RoomMsg.FromString(next(p.body for p in await a.idle() if p.code == ROOM_CREATED))
        for pwd, aviso in (("11", "Room password has been set."), ("", "Room password has been removed.")):
            a.client.send(8344, pb.RoomEditMsg(roomId=room.roomId, roomPwd=pwd))
            got = await a.idle()
            assert [p.code for p in got] == [ROOM_EDIT, 111]
            assert pb.EditRoomRspMsg.FromString(got[0].body).passWord == pwd
            assert _alerts(got) == [aviso]


async def test_5023_pvp_abre_com_a_capacidade_pedida(tmp_path: Path) -> None:
    # (visto) 24/10 #11536-#11537 e 27/10 #20249-#20251: 5023 tipo 1 capacity 3 -> 12 com capacity 3, sem campanha
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(5023, pb.RoomReqMsg(roomType=PVP, capacity=3, password=""))
        got = await a.idle()
        room = pb.RoomMsg.FromString(next(p.body for p in got if p.code == ROOM_CREATED))
        assert (room.roomType, room.capacity, room.campaignId, room.name) == (PVP, 3, 0, "Select a campaign.")


async def test_5039_zero_procura_partida_e_5037_cancela(tmp_path: Path) -> None:
    # (visto) 27/10 #20230-#20235: 5039 (paraInt2 0) -> 25 estado 2 e 111 "Matching in progress..."; 5037 state 1 -> 25 estado 1
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(5023, pb.RoomReqMsg(roomType=PVP, capacity=3))
        await a.idle()
        a.client.send(5039, pb.CampaignReqMsg(paraInt2=0, paraBool1=False))
        got = await a.idle()
        assert [p.code for p in got] == [ROOM_STATE, 111]
        assert pb.RoomStateRspMsg.FromString(got[0].body).roomState == 2
        assert _alerts(got) == ["Matching in progress, please be patient..."]
        a.client.send(5037, pb.RoomReqMsg(state=1))
        got = await a.idle()
        assert [pb.RoomStateRspMsg.FromString(p.body).roomState for p in got if p.code == ROOM_STATE] == [1]
