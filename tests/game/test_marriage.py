from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, Item, MarriageState
from wartune_server.game.handlers import marriage
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


async def _ring(g: Game) -> Item:
    ring = Item(g.user_id, marriage.RING, pos=0)
    _session(g).snapshot.items.append(ring)  # type: ignore[union-attr]
    await g.server.services.characters.save(ring)
    return ring


async def _engage(a: Game, b: Game) -> None:
    for g in (a, b):
        c = _session(g).snapshot.character  # type: ignore[union-attr]
        c.grades, c.point = 40, 20000
    await a.idle()
    await b.idle()
    b.client.send(8759, pb.MarriageOpMsg(opType=1, property1=a.user_id, property3="casa comigo?"))
    assert [p.code for p in await b.until(111)] == [111]  # sem o Engagement Ring: "You don't have..."
    ring = await _ring(b)

    b.client.send(8759, pb.MarriageOpMsg(opType=1, property1=a.user_id, property3="casa comigo?"))
    [pro] = pb.EngageMsg.FromString((await a.until(4656))[-1].body).engageInfos
    # property1 true = pedido novo (MarryModel.updateProposeList); 3 nível, 6 cabeça (MarryAnswerFrame)
    assert (pro.userIdA, pro.property1, pro.property3, pro.property5) == (b.user_id, True, 40, "casa comigo?")
    assert pro.property6 == _session(b).snapshot.character.icon  # type: ignore[union-attr]

    a.client.send(8759, pb.MarriageOpMsg(opType=3, property1=b.user_id, property5=True))
    [gone] = pb.EngageMsg.FromString((await a.until(4656))[-1].body).engageInfos
    assert (gone.userIdA, gone.property1) == (b.user_id, False)  # sai da lista de quem respondeu
    got = await b.until(4656)
    [open_] = pb.EngageMsg.FromString(got[-1].body).engageInfos
    assert (open_.userIdA, open_.property1, open_.property7) == (a.user_id, False, 1)  # abre o QUALITY_SELECT
    assert ring not in _session(b).snapshot.items  # type: ignore[union-attr]  # o anel sai de quem pediu
    for g in (a, b):
        await g.idle()
        assert _session(g).snapshot.marriage.state == MarriageState.ENGAGED  # type: ignore[union-attr]


async def test_propose_engage_marry_and_divorce(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:  # maga (feminino)
        b = await a.join("bruxo", 3)  # type: ignore[call-arg]  # mago (masculino)
        await _engage(a, b)

        b.client.send(15049, pb.MarriageOpMsg(opType=4, property1=3, payType=1))
        offer = pb.MarriageProMsg.FromString((await a.until(4658))[-1].body)
        assert (offer.property2, offer.property3) == (3, 1)
        a.client.send(8759, pb.MarriageOpMsg(opType=5, property5=True))
        a.client.send(8759, pb.MarriageOpMsg(opType=5, property5=False))  # o MarryConfirmFrame manda os dois
        info = pb.MarriageMsg.FromString((await a.until(4657))[-1].body)
        payer = _session(b).snapshot.character  # type: ignore[union-attr]
        assert _session(a).snapshot.marriage.state == MarriageState.MARRIED  # type: ignore[union-attr]
        assert payer.point == 20000 - 3999  # noivo não tem marTime: o cliente mostra e cobra o preço cheio
        assert len(info.marTime) == 19 and info.speTemplateId == 0  # "YYYY-MM-DD hh:mm:ss" (MarryInfo)
        await b.until(148)  # presentes pelo correio
        await a.idle()
        await b.idle()

        b.client.send(15049, pb.MarriageOpMsg(opType=4, property1=3, payType=1))  # casado, nas 72 h: desconto
        await a.until(4658)
        a.client.send(8759, pb.MarriageOpMsg(opType=5, property5=True))
        await b.until(3)  # PlayerMsg de quem pagou
        await b.idle()
        assert payer.point == 20000 - 3999 - (-(-3999 * 80 // 100))  # ceil: 3200

        a.client.send(8759, pb.MarriageOpMsg(opType=8, payType=1))
        await b.until(4657)
        assert _session(b).snapshot.marriage.state == MarriageState.DIVORCED  # type: ignore[union-attr]
        assert _session(a).snapshot.character.point == 20000 - 3999  # type: ignore[union-attr]
        async with a.server.services.database.sessions() as db:
            ledger = (await db.execute(select(CashLedger))).scalars().all()
        assert [(e.delta_point, e.reason) for e in ledger] == [
            (-3999, "wedding"),
            (-3200, "wedding"),
            (-3999, "divorce"),
        ]


async def test_engagement_expires_after_20_days(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxo", 3)  # type: ignore[call-arg]
        await _engage(a, b)
        m = _session(a).snapshot.marriage  # type: ignore[union-attr]
        assert m is not None
        m.since -= timedelta(days=marriage.ENGAGE_DAYS, seconds=1)
        a.client.send(8759, pb.MarriageOpMsg(opType=10))  # qualquer pedido confere o prazo, sem custo
        for g in (a, b):
            await g.until(4657)
            assert _session(g).snapshot.marriage.state == MarriageState.ENGAGE_CANCELLED  # type: ignore[union-attr]
        assert _session(a).snapshot.character.point == 20000  # type: ignore[union-attr]


async def test_mate_shop_lists_config(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(9611, pb.AltarShopListMsg(op=1))
        shop = pb.AltarShopListMsg.FromString((await a.until(365))[-1].body)
        assert [i.templateId for i in shop.info] == [41001000, 41001005, 41001006, 41001007]
