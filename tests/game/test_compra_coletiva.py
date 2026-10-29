"""Compra coletiva (8645, ``handlers/group_buy.py``): ligada pela migração 0104 (``game_settings.group_buy``)."""

from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import bag
from wartune_server.game.handlers import group_draw
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)  # edição de 2026-10-19 05:00, compra até 10-24 05:00


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _last(got: list[Packet], code: int) -> bytes:
    return next(p.body for p in reversed(got) if p.code == code)


def _set(g: Game, **cfg: Any) -> None:
    world = g.server.services.world
    object.__setattr__(
        world, "settings", MappingProxyType({**world.settings, "group_buy": {**world.settings["group_buy"], **cfg}})
    )


async def _send(g: Game, good: int, pay: int) -> list[Packet]:
    g.client.send(8645, pb.ShopMsg(payType=pay, buyInfo=pb.BuyInfo(goodId=good, count=1)))
    return await g.idle()


async def _offer(g: Game) -> pb.MainDiscountInfo:
    from wartune_server.game.handlers import shop

    s = g.server.online.get(g.user_id)
    assert s is not None
    await shop.send_offers(s)
    got = await g.idle()
    offers = [o for p in got if p.code == 4238 for o in pb.ShopMainRspMsg.FromString(p.body).discountInfo]
    return next(o for o in offers if o.type == 3)


async def test_group_buy_price_falls_limit_settles_and_wins_draw(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        cfg = g.server.services.world.settings["group_buy"]
        offer = dict(cfg["offers"][0], level1=1, level2=2, level3=99, oneDayCount=2)
        _set(g, offers=[offer])
        snap = _snap(g)
        snap.character.point = 10000
        card = await _offer(g)  # type 3 no 4238, com as datas da edição
        assert (card.id, card.beginDate, card.endDate, card.sendDate) == (
            9601,
            "2026-10-19 05:00:00",
            "2026-10-24 05:00:00",
            "2026-10-26 05:00:00",
        )
        state = pb.GrouponShopMsg.FromString(_last(await _send(g, 9601, 3), 4559))
        assert (state.curPrice, state.curCount, state.buyCount, state.frontMoney) == (389, 0, 0, 389)

        state = pb.GrouponShopMsg.FromString(_last(await _send(g, 9601, 1), 4559))
        assert (state.buyCount, state.totalPoint, state.curCount, state.count) == (1, 389, 1, 1)
        assert state.curPrice == 349 and snap.character.point == 10000 - 389  # 1 comprador: caiu para price1
        state = pb.GrouponShopMsg.FromString(_last(await _send(g, 9601, 1), 4559))
        assert (state.buyCount, state.curPrice) == (2, 309)  # 2 compradores: price2
        state = pb.GrouponShopMsg.FromString(_last(await _send(g, 9601, 1), 4559))
        assert state.buyCount == 2 and snap.character.point == 10000 - 2 * 389  # limite do dia (oneDayCount 2)
        assert group_draw.left(snap) == 2  # 1 sorteio por compra

        assert pb.GrouponShopMsg.FromString(_last(await _send(g, 9601, 2), 4559)).isReward is False  # ainda compra
        g.server.services.clock.advance(4 * 86400)  # type: ignore[attr-defined]
        shards = bag.count_of(snap, 208028)
        got = await _send(g, 9601, 2)
        check = pb.GrouponShopMsg.FromString(_last(got, 4560))
        assert (check.buyCount, check.totalPoint, check.param1) == (2, 618, 2 * 389 - 618)  # devolve a diferença
        assert snap.character.point == 10000 - 618
        assert bag.count_of(snap, 208028) - shards == 600
        assert pb.GrouponShopMsg.FromString(_last(got, 4559)).isReward is True
        await _send(g, 9601, 2)
        assert snap.character.point == 10000 - 618  # acerto só uma vez

        g.client.send(9523, pb.LeadRewardMsg(op=1))
        draw = pb.LeadRewardMsg.FromString(_last(await g.idle(), 4936))
        assert draw.templateId != 0 and draw.leadExtractTimes == 1


async def test_group_buy_auto_settles_by_mail_after_the_edition(tmp_path: Path) -> None:
    from wartune_server.game.handlers import shop

    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        cfg = g.server.services.world.settings["group_buy"]
        _set(g, offers=[dict(cfg["offers"][0], level1=1)])
        snap = _snap(g)
        snap.character.point = 1000
        await _send(g, 9601, 1)  # 1 comprador: preço final 349, sinal 389
        g.server.services.clock.advance(7 * 86400)  # type: ignore[attr-defined]  # passou do sendDate sem acertar
        s = g.server.online.get(g.user_id)
        assert s is not None
        await shop.send_offers(s)  # o login acerta
        await g.idle()
        chars = s.ctx.characters
        mails = await chars.read(lambda uow: uow.mails.by_receiver(g.user_id))
        annexes = await chars.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
        assert sorted((x.template_id, x.count) for x in annexes) == [(-400, 40), (208028, 300)]
        await shop.send_offers(s)
        await g.idle()
        assert len(await chars.read(lambda uow: uow.mails.by_receiver(g.user_id))) == len(mails)  # uma vez só
