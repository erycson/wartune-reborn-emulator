"""SumActive além do login (13) e do presente online (14): devoção (12) e os tipos que o servidor conta por ação
(alquimia 21/22, coliseu 26, destino 108/109, torneio de fadas 110). Os outros ficam em status 3. Ver docs/eventos.md."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.game import events as ev
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

START = datetime(2026, 10, 18, 12, tzinfo=UTC)
CAN, TAKEN, NOT_YET = 1, 2, 3


def _active(active_type: int, condition: int, values: tuple[int, ...]) -> ev.Active:
    packages = tuple(
        ev.Package(f"P{active_type}-{i}", i, (condition, v), ((-100, 1000, 1),)) for i, v in enumerate(values, 1)
    )
    end = START + timedelta(days=7)
    return ev.Active(f"A{active_type}", active_type, "t", "d", "c", 3, 1, START, end, packages)


CATALOG = ev.EventCatalog(
    9,
    (
        _active(12, 13, (5, 10)),  # devoção do dia: o login dá 5
        _active(21, 21, (1, 2)),  # Gold Alchemy, período todo
        _active(110, 110, (1,)),  # Sylph Arena, diário
        _active(1, 9, (100,)),  # Balens gastos no período (condição 9)
    ),
)


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


async def _data(g: Game) -> dict[str, tuple[int, list[int]]]:
    g.client.send(8586, pb.SumActiveGetPackageMsg(type=1))
    got = await g.until(4476)
    msg = pb.SumActiveDataMsg.FromString(got[-1].body)
    return {d.activeId: (d.value, [p.status for p in d.packdata]) for d in msg.datas}


async def test_devocao_contadores_e_tipos_sem_regra(tmp_path: Path) -> None:
    clock = FakeClock(START)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        s.ctx = replace(s.ctx, events=CATALOG)
        data = await _data(g)
        assert data["A12"][1] == [CAN, NOT_YET]  # devoção 5 do login (tutorial_en #16)
        assert data["A21"] == (0, [NOT_YET, NOT_YET]) and data["A1"][1] == [NOT_YET]

        snap.character.point = 100
        g.client.send(8321)  # alquimia de ouro conta 1
        await g.until(4224)
        assert (await _data(g))["A21"] == (1, [CAN, NOT_YET])
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId="A21", packageId="P21-1", count=1))
        assert 111 in [p.code for p in await g.idle()]  # "Gift pack retrieval successful."
        assert (await _data(g))["A21"][1] == [TAKEN, NOT_YET]

        await s.ctx.characters.save(*ev.count(snap, s.ctx.events, ev.PET_CHALLENGE, clock.now()))
        assert (await _data(g))["A110"] == (1, [CAN])
        clock.advance(timedelta(days=1).total_seconds())  # diário: zera no dia seguinte; o período todo não
        data = await _data(g)
        assert data["A110"] == (0, [NOT_YET]) and data["A21"] == (1, [TAKEN, NOT_YET])
