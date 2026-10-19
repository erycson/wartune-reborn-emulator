import random
from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import BagType, PlayerSnapshot
from wartune_server.game import bag
from wartune_server.game.handlers import gold_tree as gt
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

OPEN_DAY = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)  # dentro da edição da 0038 (15 a 18, hora do jogo)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _last(got: list[Packet], code: int) -> bytes:
    return next(p.body for p in reversed(got) if p.code == code)


def test_wands_pay_one_activation_each_and_the_rest_is_diamond() -> None:
    assert gt.split_cost(10, 650, 65, wands=2, use_wands=True) == (2, 520)
    assert gt.split_cost(10, 650, 65, wands=2, use_wands=False) == (0, 650)
    assert gt.split_cost(1, 65, 65, wands=7, use_wands=True) == (1, 0)
    assert gt.WAREHOUSE_MAX == 90  # com 40 no armazém ainda cabe uma ativação de 50
    weights = [(1, 1, 0, 0, 0), (2, 1, 0, 0, 1)]  # peso 0 nunca sai
    assert {d[0] for d in gt.draw(weights, 50, random.Random(1))} == {2}


async def test_activate_count_box_floor_and_loot_all(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_DAY)) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None
        snap = _snap(g)
        c = snap.character
        c.grades, c.point = 11, 650
        await session.ctx.characters.save(*bag.add(snap, session.ctx.templates, gt.WAND, 2, OPEN_DAY))

        g.client.send(8604, pb.BottleOpMsg(opType=gt.SHOW))
        got = await g.idle()
        assert pb.BottleScoreMsg.FromString(_last(got, 4526)).openView is True
        assert len(pb.BottleMsg.FromString(_last(got, 4825)).playerBottle) == 5

        g.client.send(8604, pb.BottleOpMsg(opType=gt.OPEN, alterType=2, stickFirst=0))  # 10 vezes, varinhas antes
        got = await g.idle()
        score = pb.BottleScoreMsg.FromString(_last(got, 4526))
        assert (score.count, score.alterBottle, score.treeStatus) == (10, True, "0,0,0,0,0")
        assert (c.point, bag.count_of(snap, gt.WAND)) == (130, 0)  # 650 - (650 - 2 x 65)
        assert bag.in_bag(snap, BagType.BOTTLE)
        passes = [pb.BottlePassMsg.FromString(p.body) for p in got if p.code == 4497]
        assert [len(p.infos) for p in passes if p.passType == 1] == [10]  # o que eu ganhei: uma linha por sorteio
        assert all("Congratulations to" in line for p in passes for line in p.infos)

        g.client.send(8604, pb.BottleOpMsg(opType=gt.COUNT_BOX, alterType=20))  # 10 vezes ainda não
        await g.idle()
        assert bag.count_of(snap, gt.WAND) == 0
        g.client.send(8604, pb.BottleOpMsg(opType=gt.OPEN, alterType=2, stickFirst=0))  # sem diamante: recusa
        assert pb.BottleScoreMsg.FromString(_last(await g.idle(), 4526)).count == 10

        c.point = 650
        session.ctx.gold_tree[gt._cfg(session)["id"]].total = 195  # 5 vezes antes do andar 200
        g.client.send(8604, pb.BottleOpMsg(opType=gt.OPEN, alterType=2, stickFirst=0))
        got = await g.idle()
        floors = pb.BottleMsg.FromString(_last(got, 4825))
        assert floors.total == 205 and floors.playerBottle[0].userId == c.id and floors.playerBottle[0].state == 0

        g.client.send(8604, pb.BottleOpMsg(opType=gt.COUNT_BOX, alterType=20))
        got = await g.idle()
        assert pb.BottleScoreMsg.FromString(_last(got, 4526)).treeStatus == "1,0,0,0,0"
        assert bag.count_of(snap, gt.WAND) == 3

        gift = c.gift_token
        g.client.send(8604, pb.BottleOpMsg(opType=gt.FLOOR_BOX, alterType=200))  # 1000 vinculados
        got = await g.idle()
        assert c.gift_token == gift + 1000 and pb.BottleMsg.FromString(_last(got, 4825)).playerBottle[0].state == 1
        g.client.send(8604, pb.BottleOpMsg(opType=gt.FLOOR_BOX, alterType=200))  # uma vez só
        await g.idle()
        assert c.gift_token == gift + 1000

        one = bag.in_bag(snap, BagType.BOTTLE)[0]  # clique no armazém (BottleBagCellClickMediator): 5005 22 -> 1
        free = bag.free_positions(snap, OPEN_DAY)[0]
        g.client.send(5005, pb.ItemReqMsg(beginBagType=22, beginPos=one.pos, endBagType=1, endPos=free))
        await g.idle()
        assert (one.bag_type, one.pos) == (BagType.BAG, free)

        g.client.send(8604, pb.BottleOpMsg(opType=gt.LOOT_ALL))
        await g.idle()
        assert bag.in_bag(snap, BagType.BOTTLE) == []
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert bag.in_bag(saved, BagType.BOTTLE) == [] and saved.character.point == 0
