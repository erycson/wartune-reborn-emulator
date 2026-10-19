from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.protocol.messages import wartune_pb2 as pb

FREE, PAID = 2, 3  # VehicleObjectTempInfos: Öfkeli Mayın (0 diamante), Kara Şimşek (1000, NeedGrades 365)


async def test_vehicle_garage_activate_and_choose(tmp_path: Path) -> None:
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
        ch.vehicle_exp, ch.point = 400, 999
        c.send(8619, pb.SimplePropertyMsg(param1=PAID, param2=0))  # falta 1 diamante
        assert await g.idle() == []
        ch.point = 1500
        c.send(8619, pb.SimplePropertyMsg(param1=PAID, param2=0))
        assert [p.code for p in await g.idle()] == [4516, 4515, 3, 4152, 83]  # + leed 15 (gasto de diamante)
        assert ch.point == 500

        c.send(8611, pb.CampaignReqMsg(paraInt1=PAID))
        [profile] = [pb.PlayerVehicleProfileMsg.FromString(p.body) for p in await g.idle() if p.code == 4515]
        assert profile.defaultVehicle == PAID
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert (saved.character.vehicles, saved.character.vehicle_default, saved.character.point) == (
            "1,2,3",
            PAID,
            500,
        )

        c.send(8608)  # fila sem cena de veículos: o cliente espera e cancela
        c.send(8609)
        assert await g.idle() == []
        c.send(25111, pb.WarFieldAttackMsg(userId=g.user_id))
        [state] = [pb.PlayerStateListMsg.FromString(p.body) for p in await g.idle() if p.code == 4175]
        assert state.playerState[0].armyId == g.user_id and state.playerState[0].state not in (6, 7, 8)
