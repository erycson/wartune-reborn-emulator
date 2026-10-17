from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import MarriageState
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


async def test_propose_engage_marry_and_divorce(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:  # maga (feminino)
        b = await a.join("bruxo", 3)  # type: ignore[call-arg]  # mago (masculino)
        for g in (a, b):
            c = _session(g).snapshot.character  # type: ignore[union-attr]
            c.grades, c.point = 40, 20000
        await a.idle()
        await b.idle()

        b.client.send(8759, pb.MarriageOpMsg(opType=1, property1=a.user_id, property3="casa comigo?"))
        [pro] = pb.EngageMsg.FromString((await a.until(4656))[-1].body).engageInfos
        assert (pro.userIdA, pro.property5) == (b.user_id, "casa comigo?")

        a.client.send(8759, pb.MarriageOpMsg(opType=3, property1=b.user_id, property5=True))
        for g in (a, b):
            await g.until(4657)
            assert _session(g).snapshot.marriage.state == MarriageState.ENGAGED  # type: ignore[union-attr]

        b.client.send(15049, pb.MarriageOpMsg(opType=4, property1=3, payType=1))
        offer = pb.MarriageProMsg.FromString((await a.until(4658))[-1].body)
        assert (offer.property2, offer.property3) == (3, 1)
        a.client.send(8759, pb.MarriageOpMsg(opType=5, property5=True))
        await a.until(4657)
        payer = _session(b).snapshot.character  # type: ignore[union-attr]
        assert _session(a).snapshot.marriage.state == MarriageState.MARRIED  # type: ignore[union-attr]
        assert payer.point == 20000 - 3999 * 80 // 100  # desconto do noivado recente
        await b.until(148)  # presentes pelo correio

        a.client.send(8759, pb.MarriageOpMsg(opType=8, payType=1))
        await b.until(4657)
        assert _session(b).snapshot.marriage.state == MarriageState.DIVORCED  # type: ignore[union-attr]
        assert _session(a).snapshot.character.point == 20000 - 3999  # type: ignore[union-attr]


async def test_mate_shop_lists_config(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        a.client.send(9611, pb.AltarShopListMsg(op=1))
        shop = pb.AltarShopListMsg.FromString((await a.until(365))[-1].body)
        assert [i.templateId for i in shop.info] == [41001000, 41001005, 41001006, 41001007]
