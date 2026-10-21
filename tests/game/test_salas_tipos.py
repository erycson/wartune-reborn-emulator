"""Salas por tipo (PvE e veículo; PvP não existe aqui), link de sala no chat (9504 -> 4913) e pré-carga do mapa (5038 -> 20)."""

from __future__ import annotations

from pathlib import Path

from google.protobuf.message import Message

from tests.game.harness import logged_in
from wartune_server.game import handlers  # noqa: F401  (registra os handlers)
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

ROOM_CREATED, ROOM_LIST = 12, 13
ROOM_STATE, SYSTEM_ARMY = 4913, 20  # SimplePropertyMsg da sala no link (9504), SystemArmyMsg da pré-carga (5038)
TOWER_INFO = 4205  # TowerInfoMsg (8297)


def _body[M: Message](packets: list[Packet], code: int, msg_type: type[M]) -> M:
    return msg_type.FromString(next(p.body for p in packets if p.code == code))


async def test_sala_de_outro_tipo_nao_existe_aqui(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("outro")
        a.client.send(5023, pb.RoomReqMsg(capacity=2, roomType=1))  # PvP: recusado, não vira sala PvE
        assert ROOM_CREATED not in [p.code for p in await a.idle()]
        a.client.send(5023, pb.RoomReqMsg(capacity=2))  # PvE (tipo 0): cria
        room = _body(await a.idle(), ROOM_CREATED, pb.RoomMsg)
        b.client.send(5026, pb.RoomReqMsg(roomType=1))  # lista PvP: vazia, mesmo com sala PvE aberta
        assert list(_body(await b.idle(), ROOM_LIST, pb.RoomListRspMsg).room) == []
        b.client.send(8465, pb.RoomReqMsg(roomType=1, roomId=room.roomId))
        assert await b.idle() == []
        b.client.send(5024, pb.RoomReqMsg(roomId=room.roomId, roomType=1))  # entrar com tipo errado: recusado
        assert ROOM_CREATED not in [p.code for p in await b.idle()]
        b.client.send(5026, pb.RoomReqMsg(roomType=0))  # lista PvE: a sala está lá
        assert [r.roomId for r in _body(await b.idle(), ROOM_LIST, pb.RoomListRspMsg).room] == [room.roomId]


async def test_link_de_sala_no_chat_devolve_o_estado(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(5023, pb.RoomReqMsg(capacity=2))
        room = _body(await a.idle(), ROOM_CREATED, pb.RoomMsg)
        a.client.send(9504, pb.SimplePropertyMsg(param1=room.roomId))
        state = _body(await a.idle(), ROOM_STATE, pb.SimplePropertyMsg)
        assert (state.param1, state.param2, state.param7) == (room.roomId, 0, False)  # sem campanha, fora de campanha
        a.client.send(9504, pb.SimplePropertyMsg(param1=999_999))  # sala que não existe: sem resposta
        assert ROOM_STATE not in [p.code for p in await a.idle()]


async def test_pre_carga_do_mapa_vem_da_captura(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(5038, pb.CampaignReqMsg(paraInt1=1011))  # inglesa #874-#876: 20 com soldado 2011, sem herói
        army = _body(await a.idle(), SYSTEM_ARMY, pb.SystemArmyMsg)
        assert list(army.soldierTemplated) == [2011] and list(army.heroTemplated) == []
        a.client.send(5038, pb.CampaignReqMsg(paraInt1=2011))  # só turco: peri_uyanis, herói 3011 e dois soldados
        army = _body(await a.idle(), SYSTEM_ARMY, pb.SystemArmyMsg)
        assert list(army.heroTemplated) == [3011] and list(army.soldierTemplated) == [4012, 4011]
        a.client.send(5038, pb.CampaignReqMsg(paraInt1=9999))  # mapa sem captura: lista vazia
        army = _body(await a.idle(), SYSTEM_ARMY, pb.SystemArmyMsg)
        assert not army.soldierTemplated and not army.heroTemplated


async def test_info_da_torre_tem_as_entradas_da_captura(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(8297, pb.TowerInfoReqMsg(index=0))  # capturas: 1 entrada livre de 1, nenhuma feita
        info = _body(await a.idle(), TOWER_INFO, pb.TowerInfoMsg)
        assert (info.campaignId, info.enterCount, info.freeEnterCount, info.maxEnterCount) == (8001, 0, 1, 1)


async def test_info_da_torre_ecoa_o_indice_e_nao_inventa_andar(tmp_path: Path):
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(8297, pb.TowerInfoReqMsg(index=1))  # index é o pedido; towerIndex é o andar atual
        info = _body(await a.idle(), TOWER_INFO, pb.TowerInfoMsg)
        assert (info.index, info.towerIndex, info.campaignId) == (1, 0, 8101)  # aba Tormented Necropolis; andar 0
        assert info.maxIndex == 0  # recorde: com 60 a missão 6 (tipo 38, Para2 2) fecharia sem jogar (checkMazeRecord)
