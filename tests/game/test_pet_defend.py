"""Defend Sylph Atoll: janela pelo ConfigInfos, 4686 no 20008 ao abrir/fechar e os avisos (oficial_encantar #866-#868,
#2337-#2338)."""

from datetime import datetime, timedelta
from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.domain import gameday
from wartune_server.game import pet_defend as pd
from wartune_server.game.handlers.pet_defend import OPENED, OVER, SUBSIDED
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 1, 1, hour, minute, tzinfo=gameday.GAME_TZ)


async def test_window_opens_and_closes_on_the_clock(tmp_path: Path) -> None:
    clock = FakeClock(_at(6, 59))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.pet_defend_map == 0  # login: fechada
        g.client.send(20008)
        assert 4686 not in [p.code for p in await g.until(4234)]

        clock.advance(76)  # 07:00:16, como o #2337
        g.client.send(20008)
        got = await g.idle()
        state = pb.PetIslandDefendStateMsg.FromString(next(p.body for p in got if p.code == 4686))
        assert (state.leftTime, state.mapId, state.bossId, state.ragePoint) == (3584000, 20001, 5101, 0)
        assert not state.HasField("peaceMiddle")  # o cliente manteria os contadores
        chats = [pb.ChatChannelMsg.FromString(p.body) for p in got if p.code == 83]
        assert [(c.channel, c.encodeMsg, c.isCenterTip) for c in chats] == [(12, OPENED, True)]

        clock.advance(600)
        g.client.send(20008)
        assert 4686 not in [p.code for p in await g.idle()]  # mesma janela: nada

        clock.advance(3000)  # 08:00:16
        g.client.send(20008)
        got = await g.idle()
        state = pb.PetIslandDefendStateMsg.FromString(next(p.body for p in got if p.code == 4686))
        assert (state.leftTime, state.mapId, state.bossId) == (0, 0, 0) and state.HasField("ragePoint")
        assert [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83] == [SUBSIDED, OVER]


def test_window_follows_the_config_hours(tmp_path: Path) -> None:
    from wartune_server.templates.repository import GameTemplates

    templates = GameTemplates.parse(Path("data/templates/tempinfos.xml").read_bytes())
    settings = {"pet_island_defend": {"duration": 1800, "floors": [20001, 20003]}}
    assert pd.hours(templates) == [1, 4, 7, 10, 13, 16, 19, 22]
    assert pd.window(templates, settings, _at(9, 59)) is None
    start, end, floor = pd.window(templates, settings, _at(10, 29)) or (None, None, 0)
    assert (start, end - start if end and start else None) == (_at(10, 0), timedelta(minutes=30))
    assert floor in (20001, 20003) and pd.boss_id(floor) in (5101, 5103)
    assert pd.window(templates, settings, _at(10, 30)) is None
    assert pd.window(templates, {"pet_island_defend": {"floors": []}}, _at(10, 0)) is None
