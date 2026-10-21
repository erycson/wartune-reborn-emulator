from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Quest
from wartune_server.domain.world import ExpRate
from wartune_server.game import events as ev
from wartune_server.game.handlers import events as hev
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

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
        assert _packs(got, LOGIN) == [(1, 0), (3, 0)]  # tutorial_en #68: o normal já pode; o VIP só com VIP
        online = _packs(got, ONLINE)
        assert online[0][0] == 3 and 595 <= online[0][1] <= 600

        gold = s.snapshot.character.gold  # type: ignore[union-attr]
        pkg = "B0000013-0000-0000-0000-000000000001"
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=pkg, count=1))
        got = await g.idle()
        assert [p.code for p in got] == [3, 109, 115, 4476, 111, 4476, 83]  # tutorial_en #2753-#2772
        assert _alerts(got) == ["Gift pack retrieval successful."]  # tutorial_en #2770
        assert _packs(got, LOGIN)[0] == (2, 0)
        assert s.snapshot.character.gold == gold + 10000  # type: ignore[union-attr]

        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=pkg, count=1))  # de novo
        pkg2 = "B0000013-0000-0000-0000-000000000002"
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=pkg2, count=1))  # VIP: não é
        first = "B0000014-0000-0000-0000-000000000001"
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=ONLINE, packageId=first, count=1))  # 10 min
        assert await g.idle() == []

        assert s.online_since is not None
        s.online_since -= timedelta(seconds=601)
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=ONLINE, packageId=first, count=1))
        got = await g.idle()
        assert _packs(got, ONLINE)[:2] == [(2, 0), (3, 1800)]  # o próximo conta do zero

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert ev.peek(saved, f"sum:{LOGIN}:{pkg}") is not None and saved.character.gold == gold + 20000


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

        # dia 1 do login acumulado: ReloginDrops 24001 (10.000 ouro e Worn Weapon x1, sem diamante vinculado); o 2 ainda não
        g.client.send(8496, pb.TakeLoginReward(index=2))
        g.client.send(8496, pb.TakeLoginReward(index=1))
        got = await g.until(3)
        player = pb.PlayerMsg.FromString(got[-1].body)
        assert (player.reloginProcess, player.giftToken, player.reloginCount) == (1, 0, 1)
        g.client.send(8496, pb.TakeLoginReward(index=1))
        assert [p.code for p in await g.idle()] == [
            109,
            115,
            4476,
            83,
        ]  # só o fim do anterior (ouro, item e o 4476 do ganho); nada novo

        # atividade diária: o login (leed 1) vale 5; o baú 1 precisa de 10
        g.client.send(8235, pb.LeedFinishedReqMsg(site=1))
        assert pb.LeedFinishedRspMsg.FromString((await g.until(4150))[-1].body).result is False
        g.client.send(8322, pb.ClientReqMsg(templateId=4))  # o cliente não conta: só devolve o estado
        assert pb.LeedUpdatedRspMsg.FromString((await g.until(4152))[-1].body).totalNum == 5
        snap.character.grades = 20  # chat World: nível 20 (banco)
        g.client.send(8198, pb.ChatChannelMsg(channel=10, encodeMsg="oi"))  # leed 16 "Speak in world chat"
        leeds = pb.LeedUpdatedRspMsg.FromString((await g.until(4152))[-1].body)
        assert leeds.totalNum == 10 and [x.templateId for x in leeds.leed] == [16]  # só o que mudou (tutorial_en #521)
        devotion = pb.ChatChannelMsg.FromString((await g.until(83))[-1].body)
        assert (devotion.channel, devotion.encodeMsg) == (3, "Your devotion level has increased to 10.")
        g.client.send(8235, pb.LeedFinishedReqMsg(site=1))
        got = await g.until(83)
        box = pb.LeedFinishedRspMsg.FromString(next(p for p in got if p.code == 4150).body)
        assert (box.result, box.leedProcess) == (True, 2)
        assert _alerts(got) == ["Received: 50,000 Gold"]  # LeedDrop site 1 (50000 de ouro no inglês), como o oficial

        g.client.send(8749, pb.GetRewardMsg(day=1))  # guia de 7 dias: tarefas do dia 1 não feitas
        assert await g.idle() == []

        again = await g.connect()  # relogin no mesmo dia: não conta outro dia
        g.client.writer.close()
        again.client.send(8224, pb.PlayerDataMsg(sys=True))
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert ev.peek(saved, "login").value == 1  # type: ignore[union-attr]
        assert ev.peek(saved, "relogin").value == 1  # type: ignore[union-attr]


def test_exp_rate_window_is_whole_days_in_game_time() -> None:
    rate = ExpRate(100, "2026-10-08 00:00:00", "2026-10-21 00:00:00", 0, 86399, 0)  # tutorial_en #45
    begin, end = ev.rate_window(rate)
    assert begin == datetime(2026, 10, 8, tzinfo=ev.gameday.GAME_TZ)
    assert end == datetime(2026, 10, 21, 23, 59, 59, tzinfo=ev.gameday.GAME_TZ)


async def test_exp_rate_4247_only_inside_the_window(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 10, 9, tzinfo=UTC))  # dentro da linha semeada na 0033
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = _session(g)
        await g.idle()
        [rate] = s.ctx.world.exp_rates
        end = ev.rate_window(rate)[1]
        hev.send_rate(s)
        [p] = await g.idle()
        info = pb.RateUpdateReqMsg.FromString(p.body).rateInfo[0]
        assert (p.code, info.rate, info.beginDay, info.endTime) == (4247, 100, rate.begin_day, 86399)
        clock.advance((end - clock.now()).total_seconds() + 1)
        hev.send_rate(s)
        assert await g.idle() == []


async def test_seven_day_guide_starts_at_quest_130(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        hev.send_serven(s)  # personagem novo: o login não manda 4638 (tutorial_en)
        assert await g.idle() == []
        done = datetime(2026, 10, 18, 12, tzinfo=UTC)
        snap.quests.append(Quest(snap.character.id or 0, hev.SERVEN_QUEST, done, completed=True, completed_at=done))
        hev.send_serven(s)
        [p] = await g.idle()
        assert p.code == 4638 and pb.ServenDayLeadMsg.FromString(p.body).beginTime == hev.b.fmt_time(done)


async def test_login_pages_actives_by_size_and_then_sends_their_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = _session(g)
        running = s.ctx.events.running(s.ctx.clock.now())
        hev._send_actives(s)  # o que o login manda (tutorial_en #60-#68)
        got = await g.idle()
        assert [p.code for p in got] == [4475, 4476]  # as atividades de teste cabem numa página
        assert len(pb.SumActivesMsg.FromString(got[0].body).actives) == len(running) >= 2

        monkeypatch.setattr(hev, "PAGE_BYTES", 1)  # página menor que uma atividade: uma por página
        hev._send_actives(s)
        got = await g.idle()
        pages = [pb.SumActivesMsg.FromString(p.body) for p in got if p.code == 4475]
        assert [p.code for p in got] == [4475] * len(running) + [4476]
        assert [(p.curPage, p.maxPage, len(p.actives)) for p in pages] == [
            (n, len(running), 1) for n in range(1, len(running) + 1)
        ]


async def test_login_bonus_is_daily_and_the_vip_pack_needs_vip(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 10, 20, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        snap = _session(g).snapshot
        assert snap is not None
        normal, vip_pkg = "B0000013-0000-0000-0000-000000000001", "B0000013-0000-0000-0000-000000000002"
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=normal, count=1))
        await g.until(83)
        vip = ev.state(snap, "vip", clock.now())  # VIP por 3 dias (o fim fica em vip.text)
        vip.text = hev.b.fmt_time(clock.now() + timedelta(days=3))
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=1))
        assert _packs(await g.until(4476), LOGIN) == [(2, 0), (1, 0)]  # tutorial_en #3268: o VIP abre
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId=LOGIN, packageId=vip_pkg, count=1))
        assert _packs(await g.until(83), LOGIN) == [(2, 0), (2, 0)]

        clock.advance(24 * 3600)  # "Claim them once everyday."
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=1))
        assert _packs(await g.until(4476), LOGIN) == [(1, 0), (1, 0)]
