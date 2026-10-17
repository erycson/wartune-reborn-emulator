"""Castelo: upgrade, tecnologia, filas, aceleração paga, cobrança e produção (docs/castelo.md)."""

from pathlib import Path

from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashEntry, PlayerSnapshot
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

READY = 20000  # castelo pronto: produção e fila de prédios (castle.CASTLE_READY)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _building(snap: PlayerSnapshot, template_id: int) -> int:
    return next(b.id for b in snap.buildings if b.template_id == template_id and b.id)


async def _set(g: Game, **fields: int) -> PlayerSnapshot:
    snap = _snap(g)
    for name, value in fields.items():
        setattr(snap.character, name, value)
    await g.server.services.characters.save(snap.character)
    return snap


async def test_upgrade_pays_occupies_the_order_and_quick_finish_goes_through_the_ledger(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=2, gold=1000, point=0)
        council = _building(snap, 90101)

        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=council))
        got = await g.until(83)
        assert [p.code for p in got] == [109, 109, 151, 4130, 83]
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount == 800  # 1000 - 200
        assert pb.CastleYieldMsg.FromString(got[1].body).goldYield == 280 + 140  # conselho 2 + mina 1
        order = pb.OrderInfoMsg.FromString(got[2].body)
        assert (order.orderId, order.orderType, order.remainTime) == (1, 1, 10)
        assert pb.BuildingInfoListMsg.FromString(got[3].body).building[0].templateId == 90102
        assert pb.ChatChannelMsg.FromString(got[4].body).encodeMsg == "Geliştirilen Seviye: Meclis Lv.2"
        await g.idle()

        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 10101)))  # fila ocupada
        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=1))  # sem diamante
        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=0))  # VIP: não existe aqui
        assert await g.idle() == []

        await _set(g, point=5)
        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=1))
        got = await g.until(102)
        assert [p.code for p in got] == [3, 111, 102]
        assert pb.OrderQuickRspMsg.FromString(got[2].body).orderInfo[0].remainTime == 0

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert (saved.character.gold, saved.character.point) == (800, 4)
        assert next(b for b in saved.buildings if b.id == council).template_id == 90102
        async with g.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashEntry))).scalars().all()
        assert [(e.delta_point, e.balance_point, e.reason) for e in ledger] == [(-1, 4, "order_quick")]

        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 10101)))  # fila livre de novo
        assert 4130 in [p.code for p in await g.until(83)]


async def test_refuses_without_gold_player_grade_or_someone_elses_building(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        other = await g.join("outro")
        theirs = _building(_snap(other), 90101)
        await g.idle()  # chegada do outro na cidade do céu
        snap = await _set(g, grades=2, gold=0)
        mine = _building(snap, 90101)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=mine))  # sem ouro (200)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=theirs))
        assert await g.idle() == []
        await _set(g, grades=1, gold=1000)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=mine))  # Meclis 2 pede nível 2
        assert await g.idle() == []
        assert (await g.server.services.characters.snapshot(g.user_id)).character.gold == 1000


async def test_tech_upgrade_spends_crystals_on_the_tech_order(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        snap = _snap(g)  # a academia 1 já liberou a tecnologia 1304 no nível 0 (NextTemplateId)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 130400)))
        got = await g.until(83)
        assert [p.code for p in got] == [109, 109, 151, 4130, 83]  # 1304 é de ouro: o rendimento muda
        assert pb.CastleYieldMsg.FromString(got[0].body).crystalsCount == 950
        assert pb.CastleYieldMsg.FromString(got[1].body).goldYield > 260
        assert pb.OrderInfoMsg.FromString(got[2].body).orderType == 2
        g.client.send(8202, pb.BuildingOptionReqMsg(sonType=1304))  # já existe
        g.client.send(8202, pb.BuildingOptionReqMsg(sonType=901))  # não é tecnologia
        assert await g.idle() == []
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.crystals == 950 and any(b.template_id == 130401 for b in saved.buildings)


async def test_gold_impose_and_buying_a_second_build_order(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        await _set(g, grades=14, gold=0, point=100)
        g.client.send(8327, pb.PayTypeMsg())
        got = await g.until(83)
        assert [p.code for p in got] == [109, 111, 151, 4242, 83]
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount == 120 * 6 + 140 * 3
        assert pb.GoldImposeMsg.FromString(got[3].body) == pb.GoldImposeMsg(leftImpose=1, maxImpose=5)
        g.client.send(8327, pb.PayTypeMsg())  # fila de cobrança ocupada por 1 hora
        assert await g.idle() == []

        g.client.send(5175, pb.PayTypeMsg(payType=1))
        got = await g.until(104)
        assert [p.code for p in got] == [3, 104]
        assert pb.OrderInfoMsg.FromString(got[1].body).orderType == 1
        g.client.send(5175, pb.PayTypeMsg(payType=1))  # limite de 2 filas de prédio
        assert await g.idle() == []
        g.client.send(8279, pb.PayTypeMsg())
        orders = pb.BuildOrderList.FromString((await g.until(4187))[-1].body).buildOrder
        assert sorted((o.orderId, o.orderType) for o in orders) == [(1, 1), (2, 3), (3, 2), (4, 1)]


async def test_gold_is_produced_per_hour_up_to_the_depot(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        await _set(g, gold=0)
        clock.advance(3600 + 13)  # 260/h: 13 s ainda não dão 1 de ouro
        g.client.send(5015, pb.PayTypeMsg())
        msg = pb.CastleYieldMsg.FromString((await g.until(109))[-1].body)
        assert (msg.goldYield, msg.goldTotalCount, msg.goldMax) == (260, 260, 450000)
        clock.advance(1)  # 14 s acumulados = 1,01 de ouro: a fração não se perde
        g.client.send(5015, pb.PayTypeMsg())
        assert pb.CastleYieldMsg.FromString((await g.until(109))[-1].body).goldTotalCount == 261

        await _set(g, gold=449990)
        clock.advance(3600)
        g.client.send(5015, pb.PayTypeMsg())
        assert pb.CastleYieldMsg.FromString((await g.until(109))[-1].body).goldTotalCount == 450000
        assert (await g.server.services.characters.snapshot(g.user_id)).character.gold == 450000
