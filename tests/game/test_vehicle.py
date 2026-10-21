from pathlib import Path

import pytest
from sqlalchemy import select

from tests.game.harness import logged_in
from wartune_server.domain.models import CashLedger
from wartune_server.game.handlers import vehicle
from wartune_server.protocol.messages import wartune_pb2 as pb

FREE, PAID = 2, 3  # VehicleObjectTempInfos: Mauler (0 diamante), Nightwolf (1000, NeedGrades 365)


async def test_vehicle_garage_activate_and_choose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = g.client
        c.send(8611, pb.CampaignReqMsg(paraInt1=FREE))  # ainda não tem: recusa
        assert await g.idle() == []

        c.send(8619, pb.SimplePropertyMsg(param1=FREE, param2=0))
        got = await g.idle()
        assert [p.code for p in got] == [4516, 4515]
        assert [v.templateId for v in pb.PlayerVehicleListMsg.FromString(got[0].body).vehicles] == [1, FREE]
        c.send(8619, pb.SimplePropertyMsg(param1=FREE, param2=0))  # já tem
        assert await g.idle() == []

        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        ch = session.snapshot.character
        ch.point, ch.gift_token = 1500, 300
        c.send(8619, pb.SimplePropertyMsg(param1=PAID, param2=0))  # tecnologia de tanque 0 < NeedGrades 365
        assert await g.idle() == []
        monkeypatch.setattr(vehicle, "VEHICLE_TECH", 365)
        ch.point = 699
        c.send(8619, pb.SimplePropertyMsg(param1=PAID, param2=0))  # 300 vinculados + 699: falta 1
        assert await g.idle() == []
        ch.point = 1500
        c.send(8619, pb.SimplePropertyMsg(param1=PAID, param2=0))  # param2 0 = vinculados primeiro
        assert [p.code for p in await g.idle()] == [4516, 4515, 3, 4152, 83]  # + leed 15 (gasto de diamante)
        assert (ch.point, ch.gift_token) == (800, 0)

        c.send(8611, pb.CampaignReqMsg(paraInt1=PAID))
        [profile] = [pb.PlayerVehicleProfileMsg.FromString(p.body) for p in await g.idle() if p.code == 4515]
        assert profile.defaultVehicle == PAID
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert (saved.character.vehicles, saved.character.vehicle_default, saved.character.point) == (
            "1,2,3",
            PAID,
            800,
        )
        async with g.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.delta_gift_token, e.reason) for e in ledger] == [(-700, -300, "vehicle")]

        c.send(8608)  # fora da janela ou abaixo do nível 35: só o alerta (a fila em test_veiculos.py)
        assert [p.code for p in await g.idle()] == [111]
        c.send(8609)
        for code in (8610, 8615, 8616, 8617):  # só dentro da cena VEHICLE
            c.send(code)
        assert await g.idle() == []
        c.send(25111, pb.WarFieldAttackMsg(userId=g.user_id))
        [state] = [pb.PlayerStateListMsg.FromString(p.body) for p in await g.idle() if p.code == 4175]
        assert state.playerState[0].armyId == g.user_id and state.playerState[0].state not in (6, 7, 8)
