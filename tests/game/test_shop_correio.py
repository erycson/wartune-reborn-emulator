"""Loja pelo correio: presente a outro jogador (BuyInfo.receiveId) e mochila cheia."""

from pathlib import Path

from tests.game.harness import Game, logged_in
from tests.game.test_mail import _inbox, _session
from tests.game.test_shop import HORN, buy, me
from wartune_server.domain.models import BagType, Item
from wartune_server.game import bag
from wartune_server.protocol.messages import wartune_pb2 as pb

FILLER = 208003  # Bullhorn (Small): só ocupa espaço


def _gift(good: int, count: int, receive_id: int) -> pb.ShopMsg:
    msg = buy(good, count)
    msg.buyInfo.receiveId = receive_id
    return msg


async def _rich(g: Game) -> int:
    c = me(g).character
    c.gift_token, c.point = 10**6, 0
    await g.server.services.characters.save(c)
    return c.gift_token


async def test_presente_cobra_quem_compra_e_vai_pelo_correio(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await b.idle()
        before = await _rich(a)

        a.client.send(5154, _gift(HORN, 2, 999999))  # destinatário inexistente: NO_PLAYER, nada cobrado
        assert pb.ShopMsg.FromString((await a.until(90))[-1].body).buyInfo.result == 2
        assert me(a).character.gift_token == before

        a.client.send(5154, _gift(HORN, 2, b.user_id))
        assert pb.ShopMsg.FromString((await a.until(90))[-1].body).buyInfo.result == 1
        mail_id = pb.MailMsg.FromString((await b.until(148))[-1].body).mailId
        assert me(a).character.gift_token < before
        assert not [i for i in me(a).items if i.template_id == 208002]
        assert 'Annex1Name="208002"' in await _inbox(b) and 'Annex1Count="2"' in await _inbox(b)

        b.client.send(5022, pb.MailMsg(mailsIdArray=[mail_id], position=[0]))
        rsp = pb.MailPickupRspMsg.FromString((await b.until(114))[-1].body)
        assert [r.result for r in rsp.pickupResult] == [True]
        assert sum(i.count for i in _session(b).snapshot.items if i.template_id == 208002) == 2  # type: ignore[union-attr]


async def test_mochila_cheia_paga_e_manda_pelo_correio(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await a.idle()
        before = await _rich(a)
        snap = me(a)
        now = a.server.services.clock.now()
        for pos in bag.free_positions(snap, now):  # enche a mochila (só em memória)
            snap.items.append(Item(a.user_id, FILLER, count=1, bag_type=BagType.BAG, pos=pos))

        a.client.send(5154, buy(HORN, 2))
        got = await a.until(90)
        assert got[0].code == 148 and 115 not in [p.code for p in got]  # 148 logo depois do commit, sem 115
        assert pb.ShopMsg.FromString(got[-1].body).buyInfo.result == 1
        assert me(a).character.gift_token < before
        assert 'Annex1Name="208002"' in await _inbox(a)
