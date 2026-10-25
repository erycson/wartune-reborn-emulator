"""Castelo: upgrade, tecnologia, filas, aceleração paga, cobrança, produção, fazenda, árvore,
caixa por tempo e recompensa offline (docs/castelo.md)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, Castle, Character, FarmLand, Item, PlayerSnapshot, Relation
from wartune_server.game import castle as cs
from wartune_server.game import farm, rules, timebox
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

READY = 20000  # castelo pronto: produção e fila de prédios (castle.CASTLE_READY)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _building(snap: PlayerSnapshot, template_id: int) -> int:
    return next(b.id for b in snap.buildings if b.template_id == template_id and b.id)


async def _grow(g: Game, grades: int) -> PlayerSnapshot:
    """Nível ``grades`` com os prédios que ele libera (UpGradeTempInfos tipo 3), como o login faria."""
    snap = await _set(g, grades=grades)
    session = g.server.online.get(g.user_id)
    assert session is not None
    await g.server.services.characters.save(*cs.ensure(snap, session.ctx.templates, session.ctx.clock.now()))
    return snap


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
        # conselho 2: (visto) tutorial_en #591; a Gold Refinery só nasce no 24
        assert pb.CastleYieldMsg.FromString(got[1].body).goldYield == 280
        order = pb.OrderInfoMsg.FromString(got[2].body)
        assert (order.orderId, order.orderType, order.remainTime) == (1, 1, 10)
        built = pb.BuildingInfoListMsg.FromString(got[3].body).building[0]
        assert built.templateId == 90102
        # oficial_encantar #1595: só userId, buildingId, templateId, sonType e as duas propriedades
        assert not any(built.HasField(f) for f in ("castleId", "createdDate", "isExist"))
        assert pb.ChatChannelMsg.FromString(got[4].body).encodeMsg == "Town Hall has been upgraded to Lvl. 2"
        await g.idle()

        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 120101)))  # fila ocupada
        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=1))  # sem diamante
        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=0))  # grátis só com VIP (vip.free_cool)
        assert await g.idle() == []

        await _set(g, point=9)  # 10 s de fila: 5 (ceil(10 / 600) * 5, QueueItem)
        g.client.send(5172, pb.BuildingReqMsg(orderId=1, index=1))
        got = await g.until(102)
        # leed 15 "Consume Balens" (só turco: replay #1289); 150 e 4434 do gasto (191924 #1342-#1344)
        assert [p.code for p in got] == [3, 4152, 83, 150, 4434, 111, 102]
        assert pb.ChatChannelMsg.FromString(got[5].body).encodeMsg == "Cooldown successful."
        assert pb.OrderQuickRspMsg.FromString(got[6].body).orderInfo[0].remainTime == 0

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert (saved.character.gold, saved.character.point) == (800, 4)
        assert next(b for b in saved.buildings if b.id == council).template_id == 90102
        async with g.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.balance_point, e.reason) for e in ledger] == [(-5, 4, "order_quick")]

        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 120101)))  # fila livre de novo
        assert 4130 in [p.code for p in await g.until(83)]


async def test_barracks_level_that_unlocks_a_troop_sends_100_before_the_order(tmp_path: Path) -> None:
    """tutorial_en #2208-#2213 (Barracks Lvl. 4 libera o Hunter): 109, 100 com as tropas do castelo e o 10201 com 0,
    151, 4130, 83."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=10, gold=1000)
        council = next(b for b in snap.buildings if b.template_id == 90101)
        barracks = next(b for b in snap.buildings if b.template_id == 40201)
        council.template_id, barracks.template_id = 90104, 40203
        await g.server.services.characters.save(council, barracks)

        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=barracks.id or 0))
        got = await g.until(83)
        assert [p.code for p in got] == [109, 100, 151, 4130, 83]
        pawns = pb.ArmyPawnUpdatedMsg.FromString(got[1].body).armyPawn
        assert (10201, 0) in [(a.tempateId, a.ownPawns) for a in pawns]


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
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=mine))  # Town Hall 2 pede nível 2
        assert await g.idle() == []
        assert (await g.server.services.characters.snapshot(g.user_id)).character.gold == 1000


async def test_cottage_waits_for_the_town_hall_of_the_same_grade(tmp_path: Path) -> None:
    """``PreTemplateId``: o Cottage N pede a prefeitura N (120108 -> 90108), como a missão do Cottage 8."""
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=50, gold=10**7)
        cottage = next(b for b in snap.buildings if b.template_id // 100 == 1201)
        hall = next(b for b in snap.buildings if b.template_id // 100 == 901)
        cottage.template_id = hall.template_id + 120101 - 90101  # mesmo nível da prefeitura
        await g.server.services.characters.save(cottage)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=cottage.id or 0))
        assert await g.idle() == []  # recusado: prefeitura ainda no nível de antes
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=hall.id or 0))
        assert 4130 in [p.code for p in await g.until(83)]
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=cottage.id or 0))  # fila de prédio ocupada
        assert await g.idle() == []


async def test_tech_upgrade_spends_crystals_on_the_tech_order(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _grow(g, 18)  # a academia do 18 libera a tecnologia 1304 no nível 0 (NextTemplateId)
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=_building(snap, 130400)))
        got = await g.until(83)
        # (visto) oficial_20261023-231733-1 #3971-#3981: efeito velho e novo (110, 109, 152) entre os dois 109
        assert [p.code for p in got] == [109, 110, 109, 152, 110, 109, 152, 109, 151, 4130, 83]
        assert pb.CastleYieldMsg.FromString(got[0].body).crystalsCount == 950
        effects = [pb.PropertyUpdatedMsg.FromString(p.body) for p in got if p.code == 110]
        assert [(e.propertyType, e.value) for e in effects] == [(104, 0), (104, 60)]
        y0, y1 = (pb.CastleYieldMsg.FromString(got[i].body).goldYield for i in (0, 7))
        assert y1 == y0 + 60 and pb.CastleYieldMsg.FromString(got[5].body).goldYield == y1
        politics = [pb.CastleYieldMsg.FromString(p.body).goldYield for p in got if p.code == 152]
        assert politics[0] == politics[1]  # o 152 não conta a tecnologia
        assert pb.OrderInfoMsg.FromString(got[8].body).orderType == 2
        g.client.send(8202, pb.BuildingOptionReqMsg(sonType=1304))  # já existe
        g.client.send(8202, pb.BuildingOptionReqMsg(sonType=901))  # não é tecnologia
        assert await g.idle() == []
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.crystals == 950 and any(b.template_id == 130401 for b in saved.buildings)


async def test_gold_impose_and_buying_a_second_build_order(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=READY) as g:
        await _set(g, grades=14, gold=0, point=400)  # fila extra: 395
        g.client.send(8327, pb.PayTypeMsg())
        got = await g.until(83)
        assert [p.code for p in got] == [109, 111, 151, 4242, 83]
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount == 120 * 6
        assert pb.GoldImposeMsg.FromString(got[3].body) == pb.GoldImposeMsg(leftImpose=1, maxImpose=5)
        g.client.send(8327, pb.PayTypeMsg())  # fila de cobrança ocupada por 1 hora
        assert await g.idle() == []

        g.client.send(5175, pb.PayTypeMsg(payType=1))
        got = await g.until(104)
        assert [p.code for p in got] == [3, 104]
        assert pb.OrderInfoMsg.FromString(got[1].body).orderType == 1
        assert [p.code for p in await g.until(83)] == [4152, 83]  # leed 15 (gasto de diamante)
        g.client.send(5175, pb.PayTypeMsg(payType=1))  # limite de 2 filas de prédio
        assert await g.idle() == []
        g.client.send(8279, pb.PayTypeMsg())
        orders = pb.BuildOrderList.FromString((await g.until(4187))[-1].body).buildOrder
        assert sorted((o.orderId, o.orderType) for o in orders) == [(1, 1), (2, 3), (3, 1)]  # sem academia no 14


async def test_gold_is_produced_per_hour_up_to_the_depot(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        await _grow(g, 9)  # o depósito nasce no 9
        await _set(g, gold=0)
        clock.advance(3600 + 29)  # 120/h: 29 s ainda não dão 1 de ouro
        g.client.send(5015, pb.PayTypeMsg())
        msg = pb.CastleYieldMsg.FromString((await g.until(109))[-1].body)
        assert (msg.goldYield, msg.goldTotalCount, msg.goldMax) == (120, 120, 450000)
        clock.advance(1)  # 30 s acumulados = 1 de ouro: a fração não se perde
        g.client.send(5015, pb.PayTypeMsg())
        assert pb.CastleYieldMsg.FromString((await g.until(109))[-1].body).goldTotalCount == 121

        await _set(g, gold=449990)
        clock.advance(3600)
        g.client.send(5015, pb.PayTypeMsg())
        assert pb.CastleYieldMsg.FromString((await g.until(109))[-1].body).goldTotalCount == 450000
        assert (await g.server.services.characters.snapshot(g.user_id)).character.gold == 450000


DARU_SEED = 2160028  # [L1] Ultimate Daru Seed (Property2 -300: Daru)
EXP_SEED = 2160024  # semente de EXP (Property2 -700) da fazenda roubada em oficial_20261024-191924-1 #235
SEED = 2160001  # [L1] Gold Seed: 3000 de ouro em 60 min (rende 2400, amadurece em 59; só turco: ciftlik.json)


async def test_farm_plant_accelerate_and_pick(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        row = g.server.services.templates.get("ConfigInfos", "Farm_Accelerate_Point", key="ConfigName")
        cost = int(row["ConfigValue"])  # Farm_Accelerate_Point: 35
        snap = await _set(g, gold=0, point=cost)
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
        lands = [pb.FarmInfoRspMsg.FromString(p.body).farmLandInfo[0] for p in await g.idle()]
        assert [x.result for x in lands] == [1, 1, 1] and lands[2].userId == g.user_id + 1  # o 4387 vai com o dono
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=16, pos=-1))  # guarda: sem terra -1
        assert await g.idle() == []

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=1, pos=1, bagPos=0, templateId=SEED))
        await g.until(4387)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=7, pos=1, payType=1))
        got = await g.until(83)
        # oficial_20261024-121659-1 #205-#210: leed 15 e o 150/4434 do gasto de Balens
        assert [p.code for p in got] == [3, 4152, 150, 4434, 4387, 83]
        assert pb.PlayerMsg.FromString(got[0].body).point == 0
        assert pb.FarmInfoRspMsg.FromString(got[4].body).farmLandInfo[0].matureTime == "2026-01-01 00:29:30"  # 50%
        assert [p.code for p in await g.idle()] == []
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=7, pos=0, payType=1))  # sem diamante
        assert pb.FarmInfoRspMsg.FromString((await g.until(4387))[-1].body).farmLandInfo[0].result == 1
        clock.advance(30 * 60)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=4, pos=1))
        got = await g.until(4152) + await g.until(83)
        # (visto) oficial_20261023-171155-1 #184-#189; leed 25 "Harvest from your own farm"
        assert [p.code for p in got] == [109, 111, 83, 4387, 4152, 83]
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg.startswith("Received: ")
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount == 2400 + 120 * 30 // 60

        clock.advance(29 * 60)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=4, pos=0))
        gold = pb.CastleYieldMsg.FromString((await g.until(109))[-1].body).goldTotalCount
        assert gold == 2400 + 2400 + 120 * 59 // 60  # as duas colheitas e a produção do castelo

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.lands == [] and saved.character.gold == gold and saved.items == []
        async with g.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.reason) for e in ledger] == [(-cost, "farm_accelerate")]


async def test_daru_harvest_says_received_after_the_land(tmp_path: Path) -> None:
    """(visto) oficial_20261024-121659-1 #154-#160: 3, 111, 4387, 4152, 83 "Received: 12,000 Daru" e o 83 da
    devoção."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        snap = _snap(g)
        now = clock.now()
        land = FarmLand(g.user_id, 0, DARU_SEED, now - timedelta(hours=13), now - timedelta(minutes=1), 12000)
        snap.lands.append(land)
        await g.server.services.characters.save(land)
        await g.idle()
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=4, pos=0))
        got = await g.until(83)
        got += await g.idle()
        assert [p.code for p in got][:5] == [3, 111, 4387, 4152, 83]
        assert pb.ChatChannelMsg.FromString(got[4].body).encodeMsg == "Received: 12,000 Daru"


async def test_tree_water_has_a_cooldown_and_only_the_own_tree(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        snap = await _set(g, gold=0, grades=11)
        assert snap.castle is not None
        snap.castle.farm_grade = 11  # ouro = grau da fazenda x 20
        await g.server.services.characters.save(snap.castle)
        g.client.send(8231, pb.FriendUserIdsMsg(friendId=[g.user_id + 5]))
        states = pb.LoadFarmRsp.FromString((await g.until(4190))[-1].body).friendFarmState
        assert [(x.userId, x.isChargeEnergy) for x in states] == [(g.user_id, True), (g.user_id + 5, False)]

        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))
        got = await g.until(147)
        assert [p.code for p in got] == [109, 146, 83, 147]  # oficial_20261023-153200-1 #2227-#2230
        harvest = pb.TreeUpdateRsp.FromString(got[1].body).harvestMsg
        assert harvest == ["Energy +1", "Gold +220", "Tree of the Ancients EXP +1"]
        text = pb.ChatChannelMsg.FromString(got[2].body).encodeMsg
        assert text == "Energized Successfully,Gold +220,Energy +1,Tree of the Ancients EXP +1"
        tree = pb.TreeUpdateRsp.FromString(got[3].body).tree[0]
        assert (tree.waterCount, tree.leftTime) == (1, 600)

        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))  # 10 minutos de espera
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id + 5))  # árvore de amigo
        assert await g.idle() == []
        clock.advance(600)
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))
        assert pb.TreeUpdateRsp.FromString((await g.until(147))[-1].body).tree[0].waterCount == 2
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.castle is not None and (saved.castle.tree_water, saved.castle.farm_gp) == (2, 2)
        clock.advance(600)
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))
        third = await g.until(147)  # oficial_20261023-171155-1 #4933-#4937: a 3ª abre com o 4158
        assert [p.code for p in third] == [4158, 109, 146, 83, 147]
        assert pb.FarmLogRsp.FromString(third[0].body) == pb.FarmLogRsp(playerId=g.user_id, operUserId=g.user_id)
        clock.advance(600)
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))  # 3 por dia (help do cliente)
        assert await g.idle() == []


async def test_land_upgrade_open_lands_and_the_tree_fruit(tmp_path: Path) -> None:
    """Cliente inglês: terras pelo nível da fazenda (FarmLandLayer), op 9 (sendLandUp, LandUpTip) e a colheita da
    árvore cheia (WaterViewContainer, TreeInfo.remainPickTime)."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        snap = await _set(g, gold=0, grades=40, point=0, gift_token=18)
        assert snap.castle is not None
        snap.castle.farm_grade, snap.castle.tree_water = 30, 29  # carga cheia no 30: 30 regas (UpGrade tipo 7)
        seeds = Item(g.user_id, SEED, pos=0, count=1)
        snap.items.append(seeds)
        await g.server.services.characters.save(snap.castle, seeds)

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=0))
        info = pb.FarmInfoRspMsg.FromString((await g.until(4386))[-1].body)
        assert (len(info.farmLandInfo), info.landGrades) == (9, 1)  # 3 + 30 // 5

        g.client.send(15044, pb.FarmOperReqMsg(opType=9, payType=0))  # 18 vinculados (1 * 2 * 3 / 2 + 15)
        got = await g.until(4386)
        assert 3 in [p.code for p in got] and pb.FarmInfoRspMsg.FromString(got[-1].body).landGrades == 2
        g.client.send(15044, pb.FarmOperReqMsg(opType=9, payType=0))  # 27 sem saldo: nada (sem 4387)
        assert 4387 not in [p.code for p in await g.idle()]

        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=1, pos=8, bagPos=0, templateId=SEED))
        land = pb.FarmInfoRspMsg.FromString((await g.until(4387))[-1].body).farmLandInfo[0]
        # +3%, -2% (58,8 min -> 58 - 1); pragas tiram 2 x 300 do Property3 puro (oficial_20261024-191924-1 #266)
        assert (land.pos, land.rewardCount, land.matureTime) == (8, 3090 - 600, "2026-01-01 00:57:00")

        g.client.send(5178, pb.BuildingReqMsg(index=0))  # ainda sem fruto
        g.client.send(15017, pb.BuildingReqMsg(userId=g.user_id))
        tree = pb.TreeUpdateRsp.FromString((await g.until(147))[-1].body).tree[0]
        assert (tree.waterCount, tree.fruitCount) == (30, 1)
        g.client.send(5178, pb.BuildingReqMsg(index=0))
        got = await g.until(147)
        assert [p.code for p in got][:2] == [106, 4189]
        assert list(pb.TreeUpdateRsp.FromString(got[0].body).pickMsg) == ["Daru + 114,000", "Kyanite + 3,900"]
        tree = pb.TreeUpdateRsp.FromString(got[-1].body).tree[0]
        assert (tree.waterCount, tree.fruitCount, tree.leftPickTime) == (0, 0, 86400)
        assert tree.nextPickTime == "2026-01-02 00:00:00"
        g.client.send(5178, pb.BuildingReqMsg(index=0))
        assert await g.idle() == []

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.castle is not None and saved.castle.land_grade == 2
        assert (saved.character.gift_token, saved.character.strategy) == (0, snap.character.strategy)
        assert saved.character.strategy >= 114000 and saved.character.crystals >= 3900


async def _friends(g: Game, other: Game, gp: int = 0) -> None:
    """Amizade dos dois lados (relation 1), gravada; ``gp`` = amizade de ``g`` por ``other``."""
    mine, theirs = (
        Relation(g.user_id, other.user_id, 1, group_id=2, friend_gp=gp),
        Relation(other.user_id, g.user_id, 1),
    )
    _snap(g).relations.append(mine)
    _snap(other).relations.append(theirs)
    await g.server.services.characters.save(mine, theirs)


async def test_friend_farm_steal_exp(tmp_path: Path) -> None:
    """(visto) oficial_20261024-191924-1 #249-#253: 111, 3, 83 "Received 2,800 EXP " e o 4387."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        other = await g.join("outro")
        await g.idle()
        now = clock.now()
        steps = dict(rules.grade_steps(g.server.services.templates))
        await _set(g, grades=40, total_gp=steps[40])  # sem subir de nível com os 2.800
        owner = await _set(other, grades=40)
        await _friends(g, other, gp=33)
        land = FarmLand(other.user_id, 0, EXP_SEED, now - timedelta(hours=2), now - timedelta(minutes=30), 28000)
        owner.lands.append(land)
        await g.server.services.characters.save(land)
        g.client.send(15044, pb.FarmOperReqMsg(friendId=other.user_id, opType=5, pos=0))
        got = await g.until(4387)
        assert [p.code for p in got] == [111, 3, 83, 4387]
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Received 2,800 EXP "


async def test_friend_farm_steal_revive_pest_and_tree(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        other = await g.join("outro")
        await g.idle()
        now = clock.now()
        await _set(g, gold=0, grades=11)
        owner = await _set(other, grades=66)
        assert owner.castle is not None
        owner.castle.farm_grade = 66  # o ouro de quem rega é o grau da fazenda do dono x 20
        await g.server.services.characters.save(owner.castle)
        await _friends(g, other, gp=33)  # grau 4 (só turco: ciftlik #85, 34 depois de regar)
        lands = [
            FarmLand(other.user_id, 0, SEED, now - timedelta(hours=2), now - timedelta(minutes=30), 2400),  # madura
            FarmLand(other.user_id, 1, SEED, now - timedelta(hours=4), now - timedelta(hours=3), 2400),  # morta
            FarmLand(other.user_id, 2, SEED, now - timedelta(minutes=50), now + timedelta(minutes=50), 2400, worm=1),
        ]
        owner.lands.extend(lands)
        await g.server.services.characters.save(*lands)

        g.client.send(8231, pb.FriendUserIdsMsg(friendId=[other.user_id, g.user_id + 99]))
        states = pb.LoadFarmRsp.FromString((await g.until(4190))[-1].body).friendFarmState
        friend = states[1]
        assert (friend.userId, friend.isReap, friend.isChargeEnergy, friend.isRevive, friend.isWorm) == (
            other.user_id, True, True, True, True)  # fmt: skip
        assert (states[2].userId, states[2].isReap, states[2].isChargeEnergy) == (g.user_id + 99, False, False)

        g.client.send(15044, pb.FarmOperReqMsg(friendId=other.user_id, opType=5, pos=0))  # rouba 10%
        got = await g.until(4387)
        assert [p.code for p in got] == [109, 111, 83, 4387]  # oficial_20261024-191924-1 #244-#248
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Received: 240 Gold"
        land = pb.FarmInfoRspMsg.FromString(got[3].body).farmLandInfo[0]
        assert (land.userId, land.result, land.stolenCount, list(land.stolenUsers), land.rewardCount) == (
            other.user_id, 0, 1, [g.user_id], 2160)  # fmt: skip
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount == 240
        g.client.send(15044, pb.FarmOperReqMsg(friendId=other.user_id, opType=5, pos=0))  # já roubou esta
        assert pb.FarmInfoRspMsg.FromString((await g.until(4387))[-1].body).farmLandInfo[0].result == 1

        g.client.send(15044, pb.FarmOperReqMsg(friendId=other.user_id, opType=6, pos=1))  # reviver
        land = pb.FarmInfoRspMsg.FromString((await g.until(4387))[-1].body).farmLandInfo[0]
        assert (land.result, land.matureTime) == (0, "2025-12-31 23:59:00")  # 1 min antes de agora
        g.client.send(15044, pb.FarmOperReqMsg(friendId=other.user_id, opType=2, pos=2))  # tirar o inseto
        land = pb.FarmInfoRspMsg.FromString((await g.until(4387))[-1].body).farmLandInfo[0]
        assert (land.result, land.rewardCount) == (0, 2400 + 300)  # devolve 10% do Property3 (191924 #280)
        seen = [p for p in await other.idle() if p.code in (145, 4387, 83)]  # (visto) 215937 #1033-#1035
        assert [p.code for p in seen] == [145, 4387, 83]
        assert pb.FarmLogRsp.FromString(seen[0].body).type == 2
        shown = pb.FarmInfoRspMsg.FromString(seen[1].body).farmLandInfo[0]
        assert (shown.userId, shown.pos, shown.opType, shown.result) == (other.user_id, 2, 2, 2)
        assert pb.ChatChannelMsg.FromString(seen[2].body).encodeMsg.endswith(
            " just helped exterminate the bugs in your crops!"
        )

        leaving = g.server.online.get(other.user_id)
        assert leaving is not None
        other.client.writer.close()  # o dono sai: a árvore dele é gravada pelo banco
        await leaving.gone.wait()
        await g.idle()
        g.client.send(15017, pb.BuildingReqMsg(userId=other.user_id))
        got = await g.until(83)
        got += await g.until(83)
        # só turco: ciftlik #82-#87; os +4 sobem a fazenda para o 2 (111, 4386, 83: oficial_20261023-215937-1 #1279)
        assert [p.code for p in got] == [4158, 109, 111, 4386, 83, 147, 165, 146, 83]
        assert pb.CastleYieldMsg.FromString(got[1].body).goldTotalCount == 240 + 1320
        trees = pb.TreeUpdateRsp.FromString(got[5].body).tree
        assert [(t.userId, t.waterCount) for t in trees] == [(other.user_id, 1), (g.user_id, 0)]
        info = pb.FriendInfoMsg.FromString(got[6].body)
        assert (info.userId, info.relationGrade, info.relationGp) == (other.user_id, 4, 34)
        harvest = pb.TreeUpdateRsp.FromString(got[7].body).harvestMsg
        assert harvest == ["Tree of the Ancients EXP +4", "Gold +1,320", "Friendliness  +1"]
        text = pb.ChatChannelMsg.FromString(got[8].body).encodeMsg
        assert text == "Gold +1,320,Tree of the Ancients EXP +4,Friendliness  +1"
        g.client.send(15017, pb.BuildingReqMsg(userId=other.user_id))  # uma por dia por amigo
        assert await g.idle() == []

        mine = await g.server.services.characters.snapshot(g.user_id)
        theirs = await g.server.services.characters.snapshot(other.user_id)
        assert mine.castle is not None and theirs.castle is not None
        assert (mine.castle.farm_friend_gp, mine.castle.farm_steals, mine.castle.tree_friend_today) == (6, 1, 1)
        assert theirs.castle.tree_water == 1 and theirs.lands[0].stolen_by == str(g.user_id)
        assert [r.friend_gp for r in theirs.relations] == [1]
        g.client.send(15044, pb.FarmOperReqMsg(friendId=g.user_id, opType=0))
        own = pb.FarmInfoRspMsg.FromString((await g.until(4386))[-1].body)
        assert (own.todayFromFriendGp, own.todayStolenCount) == (6, 1)
        assert own.totalGp == farm.total_gp(mine.castle, g.server.services.templates)


def test_farm_total_gp_is_the_exp_since_level_1() -> None:
    """(visto) oficial_20261024-191924-1 #216: grau 4 com 8 = 38; #235: grau 6 com 19 = 94."""
    rows = [{"Types": "17", "Grades": str(g), "Data": str(5 * (g - 1))} for g in range(1, 10)]

    class _T:
        def find(self, table: str, **kw: object) -> list[dict[str, str]]:
            return rows

    castle = Castle(1, "", 1, 0, 0, farm_grade=4, farm_gp=8)
    assert farm.total_gp(castle, _T()) == 38  # type: ignore[arg-type]
    castle.farm_grade, castle.farm_gp = 6, 19
    assert farm.total_gp(castle, _T()) == 94  # type: ignore[arg-type]


async def test_watering_a_friend_tree_can_level_up_the_farm(tmp_path: Path) -> None:
    """(visto) oficial_20261023-215937-1 #1277-#1285: 4158, 109, 111/4386/83 "Your farm has been upgraded to level
    3!", 147, 165, 146 com ``isUpGrade`` e 83."""
    async with logged_in(tmp_path, novice=READY) as g:
        other = await g.join("outro")
        await g.idle()
        mine = await _set(g, grades=11)
        await _set(other, grades=20)
        await _friends(g, other, gp=0)
        assert mine.castle is not None
        need = next(g.server.services.templates.find("UpGradeTempInfos", Types=farm.FARM_GRADE, Grades=2))
        mine.castle.farm_grade, mine.castle.farm_gp = 1, int(need["Data"]) - 1
        g.client.send(15017, pb.BuildingReqMsg(userId=other.user_id))
        got = await g.until(83)
        got += await g.until(83)
        assert [p.code for p in got] == [4158, 109, 111, 4386, 83, 147, 165, 146, 83]
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Your farm has been upgraded to level 2!"
        assert pb.FarmInfoRspMsg.FromString(got[3].body).grades == 2
        assert pb.TreeUpdateRsp.FromString(got[7].body).isUpGrade is True

        # o dono online: (visto) oficial_20261023-215937-1 #1028-#1032
        seen = await other.idle()
        assert [p.code for p in seen] == [145, 147, 165, 83, 83]
        log = pb.FarmLogRsp.FromString(seen[0].body)
        assert (log.operUserId, log.desc, log.type) == (g.user_id, "You received energy + 1, friendliness +1", 1)
        trees = pb.TreeUpdateRsp.FromString(seen[1].body).tree
        assert [t.userId for t in trees] == [other.user_id, g.user_id]
        texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in seen[3:]]
        assert texts[0].startswith('Friendliness for you and <a t="1"') and texts[0].endswith("has increased by 1.")
        assert texts[1].endswith(" has energized your Tree of Ancients. Ancient Energy +1")


async def test_time_box_pays_each_period_once(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=READY, clock=clock) as g:
        box_rows = list(g.server.services.templates.find("TimeDrop", Grade=5))  # período 5 da caixa
        gold = int(next(r["Data"] for r in box_rows if r["TemplateId"] == "-100"))  # 50000 no inglês
        item = next(int(r["TemplateId"]) for r in box_rows if int(r["TemplateId"]) > 0)  # 2090102 no inglês
        await _set(g, gold=0)
        clock.advance(900)  # online antes do primeiro 5019: não conta (tutorial_en #1594-#1598)
        g.client.send(5019, pb.BoxBoxMsg(time=-1, operate=False))
        got = await g.until(4)
        assert [p.code for p in got] == [4250, 4] and got[0].body == bytes.fromhex("080018002000")  # #1597
        assert pb.BoxBoxMsg.FromString(got[1].body) == pb.BoxBoxMsg(time=0, operate=False, timerun=0)

        g.client.send(5019, pb.BoxBoxMsg(time=5, operate=True))  # 5 minutos ainda não passaram
        assert pb.BoxBoxMsg.FromString((await g.until(4))[-1].body).time == 0
        clock.advance(300)
        g.client.send(5019, pb.BoxBoxMsg(time=5, operate=True))
        got = await g.idle()
        assert [p.code for p in got] == [109, 115, 4476, *[4484] * 9, 111, 4250, 4, 83, 83]  # ordem de #2097-#2114
        assert pb.CastleYieldMsg.FromString(got[0].body).goldTotalCount >= gold
        text = "Received: 50,000 Gold, Moderate HP Pack x1"  # #2110: do fim da TimeDrop para o começo
        assert pb.ChatChannelMsg.FromString(got[12].body).encodeMsg == text
        assert got[13].body == bytes.fromhex("080518012000")  # #2111
        assert pb.BoxBoxMsg.FromString(got[14].body) == pb.BoxBoxMsg(time=5, operate=True, timerun=0)
        chats = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got[15:]]
        assert chats == [text, "Reward retrieval successful!"]

        clock.advance(2)
        g.client.send(5019, pb.BoxBoxMsg(time=5, operate=True))  # repetido (#2109): só o estado, sem pagar
        got = await g.until(4)
        assert [p.code for p in got] == [4]
        assert pb.BoxBoxMsg.FromString(got[0].body) == pb.BoxBoxMsg(time=5, operate=True, timerun=2)
        clock.advance(597)  # o período 10 conta do resgate: 599 s ainda não bastam
        g.client.send(5019, pb.BoxBoxMsg(time=10, operate=True))
        assert [p.code for p in await g.until(4)] == [4]
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.box_period == 5 and [i.template_id for i in saved.items] == [item]
        clock.advance(1)
        g.client.send(5019, pb.BoxBoxMsg(time=10, operate=True))
        got = await g.idle()
        assert [p.code for p in got] == [
            3,
            115,
            4476,
            *[4484] * 9,
            111,
            4250,
            4,
            83,
            83,
        ]  # Daru: 3 em vez de 109 (#3343)


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
    timebox.on_login(c, start + timedelta(hours=20))  # padrão (#131): começada, conta o tempo fora e não zera no dia
    assert (c.box_seconds, c.box_period, c.offline_seconds) == (1800 + 19.5 * 3600, 0, timebox.OFFLINE_MAX)

    old = timebox.BoxRule(count_offline=False, daily_reset=True)
    c = Character(1, 1, start)
    timebox.on_login(c, start, old)
    timebox.on_logout(c, start + timedelta(minutes=30), r=old)
    timebox.on_login(c, start + timedelta(hours=1), old)  # tempo fora não conta
    assert c.box_seconds == 1800
    timebox.on_login(c, start + timedelta(hours=20), old)  # dia seguinte: a caixa recomeça
    assert (c.box_seconds, c.box_period) == (0, 0)

    fresh = Character(1, 1, start)  # conta nova: nada antes do primeiro 5019, mesmo com count_offline
    timebox.on_login(fresh, start)
    timebox.on_login(fresh, start + timedelta(hours=2))
    assert fresh.box_seconds == 0


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


async def test_reaching_grade_14_opens_the_impose_order(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #5840: a subida ao 14 manda o 104 {orderId 2, orderType 3} antes do 150."""
    from wartune_server.game.handlers.player import push_level

    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _set(g, grades=13)
        assert [o.order_type for o in snap.orders].count(3) == 0
        session = g.server.online.get(g.user_id)
        assert session is not None
        snap.character.grades = 14
        await push_level(session, 13)
        got = await g.until(150)
        assert got[0].code == 104
        assert pb.OrderInfoMsg.FromString(got[0].body) == pb.OrderInfoMsg(orderId=2, orderType=3, remainTime=0)
        await push_level(session, 14)  # já tem a fila: sem outro 104
        assert 104 not in [p.code for p in await g.until(150)]


async def test_reaching_grade_18_builds_the_academy_and_its_tech(tmp_path: Path) -> None:
    """(visto) oficial_20261023-231733-1 #3939-#3946: 110/109/152 da tecnologia, 4130 dela, 104 da fila de
    tecnologia e 4130 da academia, antes do 150; o 9 só manda o 4130 do depósito (tutorial_en #2246)."""
    from wartune_server.game.handlers.player import push_level

    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _grow(g, 17)
        assert {b.template_id // 100 for b in snap.buildings} == {901, 402, 1201, 301}
        session = g.server.online.get(g.user_id)
        assert session is not None
        snap.character.grades = 18
        await push_level(session, 17)
        got = await g.until(150)
        assert [p.code for p in got][:6] == [110, 109, 152, 4130, 104, 4130]
        assert pb.PropertyUpdatedMsg.FromString(got[0].body) == pb.PropertyUpdatedMsg(propertyType=104, value=0)
        assert pb.BuildingInfoListMsg.FromString(got[3].body).building[0].templateId == 130400
        assert pb.OrderInfoMsg.FromString(got[4].body) == pb.OrderInfoMsg(orderId=3, orderType=2, remainTime=0)
        assert pb.BuildingInfoListMsg.FromString(got[5].body).building[0].templateId == 50101
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert {50101, 130400} <= {b.template_id for b in saved.buildings}


async def test_attribute_tech_adds_to_the_hero_and_the_troops(tmp_path: Path) -> None:
    """Hero MATK e Troop PATK (MasterType 14): Property1 x nível no herói e no ``effect_Data`` da tropa; o upgrade
    manda 110 tipo 3 (velho negativo, novo) com um 150 cada e o 109 final (só turco: teknoloji_upgrade #2-#13)."""
    from wartune_server.domain.models import Building
    from wartune_server.game import rules

    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _grow(g, 18)
        session = g.server.online.get(g.user_id)
        assert session is not None
        templates, now = session.ctx.templates, session.ctx.clock.now()
        before = rules.leader_stats(snap, templates, now).total["MagicAttack"]
        snap.character.crystals = 10**6
        hero, troop = Building(g.user_id, 144200), Building(g.user_id, 142102)  # Hero MATK 0 e Troop PATK 2
        snap.buildings.extend([hero, troop])
        await g.server.services.characters.save(snap.character, hero, troop)
        assert rules.troop_tech(snap, templates) == {"Attack": 12}
        g.client.send(8203, pb.BuildingOptionReqMsg(buildingId=hero.id or 0))
        got = await g.until(83)
        assert [p.code for p in got] == [109, 110, 150, 110, 150, 109, 151, 4130, 83]
        effects = [pb.PropertyUpdatedMsg.FromString(p.body) for p in got if p.code == 110]
        assert [(e.propertyType, e.value) for e in effects] == [(3, 0), (3, 12)]
        assert rules.leader_stats(snap, templates, now).total["MagicAttack"] == before + 12
        pawns = cs_pawns(snap, templates)
        live = pawns.armyPawn[0].pawnLive[0]  # Attack
        assert (live.effect_Data, live.base_Join) == (12, live.tempData + 12)


async def test_blessing_boosts_the_techs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cada tecnologia vale ``Property1 x nível x (100 + bênção) / 100`` (só turco: city_city_upgrade #13-#142,
    Hero PATK 444 -> 488 -> 666); o giro manda 109, os 110 da troca (velho negativo, novo), 3, 4152 e 4391."""
    from wartune_server.domain.models import Building
    from wartune_server.game import rules
    from wartune_server.game.handlers import castle

    monkeypatch.setattr(castle._bless_rng, "randint", lambda lo, hi: 40)
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _grow(g, 18)
        session = g.server.online.get(g.user_id)
        assert session is not None
        templates = session.ctx.templates
        snap.character.crystals, snap.character.seminary_effect = 10**6, 10
        troop = Building(g.user_id, 142102)  # Troop PATK 2: 12 sem a bênção
        snap.buildings.append(troop)
        await g.server.services.characters.save(snap.character, troop)
        assert rules.troop_tech(snap, templates) == {"Attack": 13}
        g.client.send(8489)
        got = await g.until(4391)
        codes = [p.code for p in got]
        assert codes[0] == 109 and codes[-3:] == [3, 4152, 4391]
        effects = [pb.PropertyUpdatedMsg.FromString(p.body) for p in got if p.code == 110]
        assert (effects[0].value, effects[-1].value) == (-13, 18)
        assert snap.character.seminary_effect == 50
        assert rules.troop_tech(snap, templates) == {"Attack": 18}


async def test_blessing_moves_the_hero_hp_through_the_reserve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(só turco: city_city_upgrade #37-#48) sem a Hero HP a vida cheia passa do máximo e o excesso volta à reserva
    (113 antes do 110 negativo); com a bênção nova a reserva enche de novo e o 83 da poção sai um passo depois."""
    from wartune_server.domain.models import Building
    from wartune_server.game import rules
    from wartune_server.game.handlers import castle
    from wartune_server.game.handlers.player import HP_PACK

    monkeypatch.setattr(castle._bless_rng, "randint", lambda lo, hi: 40)
    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _grow(g, 18)
        session = g.server.online.get(g.user_id)
        assert session is not None and snap.leader is not None
        templates, now = session.ctx.templates, session.ctx.clock.now()
        row = next(
            r
            for r in templates.find("BuildingTempInfos", MasterType="14", BuildingGrade="5")
            if (templates.get("EffectTempInfos", int(r["Property1"])) or {}).get("PropertyType1") == "145"
        )
        hp_tech = Building(g.user_id, int(row["TemplateId"]))
        snap.buildings.append(hp_tech)
        snap.character.crystals, snap.character.seminary_effect = 10**6, 10
        snap.leader.hp, snap.leader.blood = 0, 100_000
        await g.server.services.characters.save(snap.character, snap.leader, hp_tech)
        full = rules.leader_stats(snap, templates, now).live
        g.client.send(8489)
        got = await g.until(4391)
        codes = [p.code for p in got]
        assert codes.index(113) < codes.index(110)
        assert any(p.code == 83 and pb.ChatChannelMsg.FromString(p.body).encodeMsg == HP_PACK for p in got)
        live = rules.leader_stats(snap, templates, now).live
        assert live > full and snap.leader.hp == live
        assert snap.leader.blood == 100_000 - (live - full)


def cs_pawns(snap: PlayerSnapshot, templates: object) -> pb.ArmyPawnUpdatedMsg:
    from wartune_server.game.builders.army import castle_pawns

    return castle_pawns(snap, templates)  # type: ignore[arg-type]


async def test_reaching_grade_9_builds_the_depot(tmp_path: Path) -> None:
    """(visto) tutorial_en #2245-#2246: o 109 já com o teto do depósito (450000) e o 4130 do 30101."""
    from wartune_server.game.handlers.player import push_level

    async with logged_in(tmp_path, novice=READY) as g:
        snap = await _grow(g, 8)
        session = g.server.online.get(g.user_id)
        assert session is not None
        snap.character.grades = 9
        await push_level(session, 8)
        got = await g.until(150)
        assert [p.code for p in got][:2] == [109, 4130]
        assert pb.CastleYieldMsg.FromString(got[0].body).goldMax == 450000
        assert pb.BuildingInfoListMsg.FromString(got[1].body).building[0].templateId == 30101
