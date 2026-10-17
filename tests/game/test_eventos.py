from datetime import timedelta
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.game import events as ev
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb

LOGIN = "A0000013-0000-0000-0000-000000000001"  # data/events.json
ONLINE = "A0000014-0000-0000-0000-000000000001"


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


def _packs(got: list, active: str) -> list[tuple[int, int]]:  # type: ignore[type-arg]
    data = pb.SumActiveDataMsg.FromString(next(p for p in reversed(got) if p.code == 4476).body)
    [d] = [d for d in data.datas if d.activeId == active]
    return [(p.status, p.countDown) for p in d.packdata]


def _alerts(got: list) -> list[str]:  # type: ignore[type-arg]
    return [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 111]


async def test_login_and_online_gift_activities(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = _session(g)
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=1))
        got = await g.until(4476)
        assert _packs(got, LOGIN) == [(1, 0), (3, 0), (3, 0), (3, 0), (3, 0), (3, 0), (3, 0)]  # 1º dia de login
        online = _packs(got, ONLINE)
        assert online[0][0] == 3 and 595 <= online[0][1] <= 600

        gold = s.snapshot.character.gold  # type: ignore[union-attr]
        pkg = "B0000013-0000-0000-0000-000000000001"
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=pkg, count=1))
        got = await g.idle()
        assert [p.code for p in got] == [111, 4476, 3, 109, 115, 83, 4476]
        assert _alerts(got) == ["Hediye Paketi başarıyle alındı"]
        assert _packs(got, LOGIN)[0] == (2, 0)
        assert s.snapshot.character.gold == gold + 200000  # type: ignore[union-attr]

        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=pkg, count=1))  # de novo
        pkg2 = "B0000013-0000-0000-0000-000000000002"
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=pkg2, count=1))  # dia 2
        first = "B0000014-0000-0000-0000-000000000001"
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=ONLINE, packageId=first, count=1))  # 10 min
        assert await g.idle() == []

        assert s.online_since is not None
        s.online_since -= timedelta(seconds=601)
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=ONLINE, packageId=first, count=1))
        got = await g.idle()
        assert _packs(got, ONLINE)[:2] == [(2, 0), (3, 1800)]  # o próximo conta do zero

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert ev.peek(saved, f"sum:{LOGIN}:{pkg}") is not None and saved.character.gold == gold + 210000


async def test_sign_relogin_and_daily_activity(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        g.client.send(8266)
        sign = pb.PlayerSignRspMsg.FromString((await g.until(4177))[-1].body)
        assert sign.signTimes == 1 and sign.signSite.bit_count() == 1
        g.client.send(8266)  # já assinou hoje: só repete o estado, sem prêmio
        assert [p.code for p in await g.idle()] == [4177]

        # dia 1 do login acumulado: ReloginDrops 24001 (10.000 ouro, 20 diamantes vinculados); o 2 ainda não
        g.client.send(8496, pb.TakeLoginReward(index=2))
        g.client.send(8496, pb.TakeLoginReward(index=1))
        got = await g.until(3)
        player = pb.PlayerMsg.FromString(got[-1].body)
        assert (player.reloginProcess, player.giftToken, player.reloginCount) == (1, 20, 1)
        g.client.send(8496, pb.TakeLoginReward(index=1))
        assert [p.code for p in await g.idle()] == [109, 83]  # só o fim do anterior; nada novo

        # atividade diária: o login (leed 1) vale 5; o baú 1 precisa de 10
        g.client.send(8235, pb.LeedFinishedReqMsg(site=1))
        assert pb.LeedFinishedRspMsg.FromString((await g.until(4150))[-1].body).result is False
        g.client.send(8322, pb.ClientReqMsg(templateId=4))  # "Tek Kişilik Sahneyi Geç", Num 5
        leeds = pb.LeedUpdatedRspMsg.FromString((await g.until(4152))[-1].body)
        assert leeds.totalNum == 10
        g.client.send(8235, pb.LeedFinishedReqMsg(site=1))
        got = await g.until(83)
        box = pb.LeedFinishedRspMsg.FromString(next(p for p in got if p.code == 4150).body)
        assert (box.result, box.leedProcess) == (True, 2)
        assert _alerts(got) == ["Kazanılan:Orta Ruh İncisi x5"]  # LeedDrop site 1, como o oficial

        g.client.send(8749, pb.GetRewardMsg(day=1))  # guia de 7 dias: tarefas do dia 1 não feitas
        assert await g.idle() == []

        again = await g.connect()  # relogin no mesmo dia: não conta outro dia
        g.client.writer.close()
        again.client.send(8224, pb.PlayerDataMsg(sys=True))
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert ev.peek(saved, "login").value == 1  # type: ignore[union-attr]
        assert ev.peek(saved, "relogin").value == 1  # type: ignore[union-attr]
