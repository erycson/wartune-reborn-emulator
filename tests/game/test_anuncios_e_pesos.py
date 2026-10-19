import random
from collections import Counter
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from wartune_server.domain import gameday
from wartune_server.domain.world import Announcement
from wartune_server.game import announcements, drops, gemmaze
from wartune_server.game.handlers import vip
from wartune_server.protocol.messages import wartune_pb2 as pb

PRE = datetime(2026, 10, 18, 15, 54, 30, tzinfo=UTC)  # 18:54:30 em UTC+3 (o fuso do harness): 30 s antes das 18:55


def _notice(times: str, weekdays: frozenset[int] = frozenset(), id: int = 1) -> Announcement:
    return Announcement(id, tuple(time.fromisoformat(t) for t in times.split(",")), weekdays, 12, 1, False, f"a{id}")


def test_dispara_so_no_horario_e_uma_vez(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gameday, "GAME_TZ", UTC)
    a, b = _notice("18:55", id=1), _notice("18:55,21:55", id=2)
    at = datetime(2026, 10, 18, 18, 55, tzinfo=UTC)
    clock = announcements.Announcer()
    assert clock.tick([a, b], at - timedelta(seconds=30)) == []  # primeiro relógio: só marca
    assert clock.tick([a, b], at - timedelta(seconds=1)) == []  # ainda não
    assert clock.tick([a, b], at + timedelta(seconds=29)) == [a, b]  # na ordem do id
    assert clock.tick([a, b], at + timedelta(seconds=40)) == []  # outro jogador no mesmo minuto: não repete
    assert clock.tick([a, b], at + timedelta(hours=1)) == []  # fora do horário
    # ninguém online das 19:55 às 21:58: o 21:55 passou do LATE e não sai atrasado
    assert clock.tick([b], datetime(2026, 10, 18, 21, 58, tzinfo=UTC)) == []


def test_meia_noite_e_dias_da_semana(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gameday, "GAME_TZ", UTC)
    midnight = _notice("00:00")
    since, now = datetime(2026, 10, 18, 23, 59, 30, tzinfo=UTC), datetime(2026, 10, 19, 0, 0, 30, tzinfo=UTC)
    assert announcements.due([midnight], since, now) == [midnight]
    monday = _notice("12:00", frozenset({1}))  # 2026-10-19 é segunda
    noon = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    assert announcements.due([monday], noon - timedelta(minutes=1), noon) == [monday]
    tuesday = noon + timedelta(days=1)
    assert announcements.due([monday], tuesday - timedelta(minutes=1), tuesday) == []


async def test_sylph_atoll_vai_para_todos_os_online_como_no_oficial(tmp_path: Path) -> None:
    from wartune_server.services.clock import FakeClock

    clock = FakeClock(PRE)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        b = await g.join("outro")
        await g.idle()
        await b.idle()
        g.client.send(20008)
        assert 83 not in [p.code for p in await g.idle()]  # 18:54:30: ainda não
        clock.advance(60)  # 18:55:30
        g.client.send(20008)
        for game in (g, b):
            chats = [pb.ChatChannelMsg.FromString(p.body) for p in await game.idle() if p.code == 83]
            assert [(m.channel, m.otherId, m.userType, m.isCenterTip, m.name) for m in chats] == [
                (12, -1, 1, True, ""),
                (12, -1, 1, False, ""),
            ]  # #3029 e #3030, nessa ordem
            assert chats[0].encodeMsg == "Sylph Atoll echoes, “Humans, how foolish you are!”" + " " * 36
            assert chats[1].encodeMsg.startswith("Defend Sylph Atoll event is starting soon.")
        b.client.send(20008)  # o relógio do outro no mesmo minuto não repete
        assert 83 not in [p.code for p in await b.idle()]
        assert 83 not in [p.code for p in await g.idle()]
        clock.advance(5 * 60)  # 19:00:30: o início
        b.client.send(20008)
        [start] = [pb.ChatChannelMsg.FromString(p.body) for p in await g.idle() if p.code == 83]
        assert start.encodeMsg == "Defend Sylph Atoll event has started."


def test_roleta_vip_respeita_o_peso() -> None:
    rng = random.Random(3)
    assert {vip.wheel_pick([0, 0, 5, 0], [], rng) for _ in range(50)} == {2}  # peso 0 nunca sai
    assert {vip.wheel_pick([1, 0, 1], [0], rng) for _ in range(50)} == {2}  # o que já saiu fica de fora
    assert vip.wheel_pick([0, 1], [1], rng) is None  # só sobrou peso 0: giro recusado
    seeded = random.Random(0)
    got = Counter(vip.wheel_pick([1, 9], [], seeded) for _ in range(1000))
    assert 850 < got[1] < 950  # 90%


def test_labirinto_sorteia_pelo_peso() -> None:
    board = [1, 1, 2, 1, 3, 2, 3, 4, 5, 2, 3, 4, 5, 1, 3, 4, 5, 1, 2, 4, 5, 1, 2, 3, 5]  # troca 2<->3 faz 1,1,1
    got = gemmaze.play(gemmaze.Game(board=list(board)), 2, 3, random.Random(2), [0, 0, 1])
    assert got is not None and got.steps
    assert {(s.reward, s.count) for s in got.steps} == {(208014, 2)}


async def test_pesos_vem_do_banco(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        world, templates = g.server.services.world, g.server.services.templates
        assert world.vip_wheel_weights == (1.0,) * 18  # 0035: padrão igual (uniforme, como antes)
        assert world.settings["star_open_next"] == 0.3 and world.settings["gem_maze_reward_weights"] == [1, 1, 1]
        assert set(world.settings["star_weights"]) == {"1", "2", "3", "4", "5", "6", "7"}
        assert [a.text[:12] for a in world.announcements] == ["Sylph Atoll ", "Defend Sylph", "Defend Sylph"] + [
            "Defend Sylph"
        ]
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        got = drops.card(session.snapshot, templates, 1002, 0, random.Random(1), table=[(2040102, 0.0)], now=session.ctx.clock.now())
        assert got is not None and got[0].template_id == 2040102  # tudo 0 no banco: uniforme, sem erro
