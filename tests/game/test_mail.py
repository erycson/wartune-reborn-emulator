import re
import zlib
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.game.mail import send_system_mail
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb

SMALL_BUGLE = 208003


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


async def _inbox(g: Game, **extra: str) -> str:
    form = {"userId": str(g.user_id), "key": g.key, "mailId": "0"} | extra
    response = await g.http.post("/maillist", data=form)
    return zlib.decompress(await response.read()).decode()


async def test_system_mail_with_annex_is_listed_and_picked_up_once(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        s = _session(a)
        await a.idle()
        mail = await send_system_mail(s.ctx, a.user_id, "oi", "presente", [(SMALL_BUGLE, 3)])
        assert pb.MailMsg.FromString((await a.until(148))[-1].body).mailId == mail.id

        xml = await _inbox(a)
        assert f'Id="{mail.id}"' in xml and f'Annex1Name="{SMALL_BUGLE}"' in xml
        assert 'ReadDate="2999' in xml and int(re.search(r'Annex1="(-?\d+)"', xml).group(1)) < 0  # type: ignore[union-attr]

        a.client.send(5022, pb.MailMsg(mailsIdArray=[mail.id or 0], position=[0]))
        got = await a.until(4131)
        codes = [p.code for p in got]
        assert codes[0] == 115 and codes[-4:] == [111, 83, 114, 4131]  # oficial_20261024-121659-1 #508-#535
        assert pb.ChatChannelMsg.FromString(got[-3].body).encodeMsg == "Successfully retrieved Bullhorn (Small) x3"
        rsp = pb.MailPickupRspMsg.FromString(got[-2].body)
        assert [r.result for r in rsp.pickupResult] == [True]
        assert sum(i.count for i in s.snapshot.items if i.template_id == SMALL_BUGLE) == 3  # type: ignore[union-attr]

        a.client.send(5022, pb.MailMsg(mailsIdArray=[mail.id or 0], position=[0]))
        rsp = pb.MailPickupRspMsg.FromString((await a.until(114))[-1].body)
        assert [r.result for r in rsp.pickupResult] == [False]

        a.client.send(8206, pb.MailDelReqMsg(delList=[mail.id or 0]))
        assert list(pb.MailDelReqMsg.FromString((await a.until(4132))[-1].body).delList) == [mail.id]
        assert "<Info" not in await _inbox(a)

        gold = s.snapshot.character.gold  # type: ignore[union-attr]
        coins = await send_system_mail(s.ctx, a.user_id, "ouro", "moedas", [(-100, 50)])  # -100 = ouro
        a.client.send(5022, pb.MailMsg(mailsIdArray=[coins.id or 0], position=[0]))
        rsp = pb.MailPickupRspMsg.FromString((await a.until(114))[-1].body)
        assert [r.result for r in rsp.pickupResult] == [True]
        assert s.snapshot.character.gold == gold + 50  # type: ignore[union-attr]


async def test_player_mail_costs_gold_and_notifies(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        c = _session(a).snapshot.character  # type: ignore[union-attr]
        c.grades, c.gold = 10, 150
        await b.idle()
        a.client.send(8205, pb.MailSendReqMsg(sendType=1, receiverUserId=[b.user_id], title="oi", contents="tudo bem?"))
        await b.until(148)
        assert c.gold == 50
        assert 'Title="oi"' in await _inbox(b) and 'SendNickName="Maga"' in await _inbox(b)

        bad = await a.http.post("/maillist", data={"userId": str(b.user_id), "key": a.key, "mailId": "0"})
        assert 'value="false"' in zlib.decompress(await bad.read()).decode()  # chave de outra conta
