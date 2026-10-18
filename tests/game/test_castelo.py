"""Castelo: upgrade, tecnologia, filas, aceleração paga, cobrança, produção, fazenda, árvore,
caixa por tempo e recompensa offline (docs/castelo.md)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, Character, Item, PlayerSnapshot
from wartune_server.game import timebox
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
        assert pb.ChatChannelMsg.FromString(got[4].body).encodeMsg == "Geliştirilen Seviye: Town Hall Lv.2"
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
            ledger = (await db.execute(select(CashLedger))).scalars().all()
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


SEED = 2160001  # Ucuz Altın İnciri: 3000 de ouro em 60 min (rende 2400, amadurece em 59, ciftlik.json)


async def test_farm_plant_accelerate_and_pick(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        snap = await _set(g, gold=0, point=10)
        seeds = Item(g.user_id, SEED, pos=0, count=2)
        snap.items.append(seeds)
        await g.server.services.characters.save(seeds)

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=0))
        info = pb.FarmInfoRspMsg.FromString((await g.until(4386))[-1].body)
        assert len(info.farmLandInfo) == 3 and info.treeInfo.userId == g.user_id

        plant = pb.FarmOperReqMsg(friendId=g.user_id, opType=1, pos=0, bagPos=0, templateId=SEED)
        g.client.send(15044, plant)
        got = await g.until(4387)
        assert [p.code for p in got] == [115, 4387]
        land = pb.FarmInfoRspMsg.FromString(got[1].body).farmLandInfo[0]
        assert (land.itemTemplateId, land.rewardCount, land.result, land.HasField("param1")) == (SEED, 2400, 0, False)
        assert land.matureTime == "2026-01-01 00:59:00"

        g.client.send(15044, plant)  # terra ocupada
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=4, pos=0))  # ainda verde
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id + 1, opType=4, pos=0))  # fazenda de outro
        results = [pb.FarmInfoRspMsg.FromString(p.body).farmLandInfo[0].result for p in await g.idle()]
        assert results == [1, 1]

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=1, pos=1, bagPos=0, templateId=SEED))
        await g.until(4387)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=7, pos=1, payType=1))
        got = await g.until(4387)
        assert [p.code for p in got] == [3, 4387]
        assert pb.PlayerMsg.FromString(got[0].body).point == 0
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=4, pos=1))
        got = await g.until(109)
        assert [p.code for p in got] == [4387, 109]
        assert pb.CastleYieldMsg.FromString(got[1].body).goldTotalCount == 2400

        clock.advance(59 * 60)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=4, pos=0))
        gold = pb.CastleYieldMsg.FromString((await g.until(109))[-1].body).goldTotalCount
        assert gold == 2400 + 2400 + 260 * 59 // 60  # as duas colheitas e a produção do castelo

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.lands == [] and saved.character.gold == gold and saved.items == []
        async with g.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.reason) for e in ledger] == [(-10, "farm_accelerate")]


async def test_tree_water_has_a_cooldown_and_only_the_own_tree(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        await _set(g, gold=0, grades=11)
        g.client.send(8231, pb.FriendUserIdsMsg(friendId=[g.user_id + 5]))
        states = pb.LoadFarmRsp.FromString((await g.until(4190))[-1].body).friendFarmState
        assert [(x.userId, x.isChargeEnergy) for x in states] == [(g.user_id, True), (g.user_id + 5, False)]

        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))
        got = await g.until(147)
        assert [p.code for p in got] == [109, 83, 147]
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg.startswith("Doldurma başarılıAltın + 220,")
        tree = pb.TreeUpdateRsp.FromString(got[2].body).tree[0]
        assert (tree.waterCount, tree.leftTime) == (1, 600)

        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))  # 10 minutos de espera
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id + 5))  # árvore de amigo
        assert await g.idle() == []
        clock.advance(600)
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))
        assert pb.TreeUpdateRsp.FromString((await g.until(147))[-1].body).tree[0].waterCount == 2
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.castle is not None and (saved.castle.tree_water, saved.castle.farm_gp) == (2, 2)


async def test_time_box_pays_each_period_once(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        await _set(g, gold=0)
        g.client.send(5019, pb.BoxBoxMsg(time=-1, operate=False))
        assert pb.BoxBoxMsg.FromString((await g.until(4))[-1].body) == pb.BoxBoxMsg(time=0, operate=False, timerun=0)

        g.client.send(5019, pb.BoxBoxMsg(time=5, operate=True))  # 5 minutos ainda não passaram
        assert pb.BoxBoxMsg.FromString((await g.until(4))[-1].body).time == 0
        clock.advance(300)
        g.client.send(5019, pb.BoxBoxMsg(time=5, operate=True))
        got = await g.until(3)
        assert [p.code for p in got] == [4, 115, 109, 3]
        assert pb.BoxBoxMsg.FromString(got[0].body) == pb.BoxBoxMsg(time=5, operate=True, timerun=300)
        assert pb.CastleYieldMsg.FromString(got[2].body).goldTotalCount == 2000 + 260 * 300 // 3600

        g.client.send(5019, pb.BoxBoxMsg(time=5, operate=True))  # já recebido
        assert [p.code for p in await g.until(4)] == [4]
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.box_period == 5 and [i.template_id for i in saved.items] == [2090101]


async def test_offline_reward_gives_exp_once(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, offline_seconds=7200)
        total = snap.character.total_gp
        g.client.send(8287, pb.OfflineRewardMsg(rateCount=20))  # x2 tem preço que não conhecemos
        assert await g.idle() == []
        g.client.send(8287, pb.OfflineRewardMsg(rateCount=0))
        player = pb.PlayerMsg.FromString((await g.until(3))[-1].body)
        assert player.totalGp == total + 120 * 1
        g.client.send(8287, pb.OfflineRewardMsg(rateCount=0))
        assert await g.idle() == []


def test_offline_time_and_online_time_are_counted_apart() -> None:
    start = datetime(2026, 1, 1, 10, tzinfo=UTC)
    c = Character(1, 1, start)
    timebox.on_login(c, start)
    timebox.on_logout(c, start + timedelta(minutes=30))
    assert (c.box_seconds, c.offline_at) == (1800, start + timedelta(minutes=30))
    timebox.on_login(c, start + timedelta(hours=20))  # dia seguinte: a caixa recomeça
    assert (c.box_seconds, c.box_period, c.offline_seconds) == (0, 0, timebox.OFFLINE_MAX)


async def test_novice_set_over_http_survives_the_logout_save(tmp_path: Path) -> None:
    """A saída grava o personagem inteiro (tempo online/offline): não pode desfazer o updateplayernovice."""
    async with logged_in(tmp_path, novice=READY) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None
        http = TestClient(TestServer(g.server.http_app))
        await http.start_server()
        try:
            form = {"op": 1, "userid": g.user_id, "noviceprocess": READY + 500, "key": session.login_key or ""}
            assert await (await http.post("/updateplayernovice", data=form)).text() == str(READY + 500)
        finally:
            await http.close()
        g.client.writer.close()
        await session.gone.wait()
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.novice_process == READY + 500 and saved.character.offline_at is not None
