"""Defend Sylph Atoll: janela pelo ConfigInfos, 4686 no 20008 ao abrir/fechar e os avisos (oficial_encantar #866-#868,
#2337-#2338)."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

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


def _riot(session: object, hero: int) -> int:
    """O primeiro nó 1003 do herói (o vencido conta: fica DONE)."""
    nodes = session.campaign.nodes  # type: ignore[attr-defined]
    return next(camp for camp, n in nodes.items() if n["masterType"] == 1003 and n["heroTempId"] == hero)


def _open_riot(session: object, hero: int) -> int:
    nodes = session.campaign.nodes  # type: ignore[attr-defined]
    return next(c for c, n in nodes.items() if n["masterType"] == 1003 and n["heroTempId"] == hero and n["state"] == 1)


async def test_riot_fights_count_rage_and_bring_the_boss(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from wartune_server.game.handlers.space import enter_pet_island
    from wartune_server.templates.repository import GameTemplates

    real = GameTemplates.get

    def weak(self: GameTemplates, table: str, value: object, **kw: object) -> object:
        row = real(self, table, value, **kw)  # type: ignore[arg-type]
        if table == "GameHeroTemp" and value in (75112, 75122, 5101) and row is not None:
            return {**row, "Live": "1", "Attack": "1", "MagicAttack": "1"}  # vence no primeiro golpe
        return row

    monkeypatch.setattr(GameTemplates, "get", weak)

    clock = FakeClock(_at(7, 0))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.grades = 50
        await g.idle()
        enter_pet_island(session, 20001)
        await g.idle()
        nodes = session.campaign.nodes  # type: ignore[union-attr]
        riots = [n for n in nodes.values() if n["masterType"] == 1003]
        assert {n["state"] for n in riots if n["heroTempId"] != 5101} == {1}  # janela aberta: à vista
        assert {n["state"] for n in riots if n["heroTempId"] == 5101} == {8}  # chefe só com a fúria cheia

        async def fight(camp: int) -> list[object]:
            g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp))
            prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
            assert prepare.battleType == 6
            got = await g.fight(prepare)
            return got + await g.idle()

        got = await fight(_riot(session, 75112))
        [report] = [pb.BattleReportMsg.FromString(p.body) for p in got if p.code == 4103]  # type: ignore[attr-defined]
        assert report.battleResult == 1
        state = pb.PetIslandDefendStateMsg.FromString([p.body for p in got if p.code == 4686][-1])  # type: ignore[attr-defined]
        assert (state.peaceMiddle, state.peaceHigh, state.peaceBoss, state.ragePoint) == (1, 0, 0, 2)
        assert any(i.template_id == 2100038 and i.count == 2 for i in session.snapshot.items)
        first = _riot(session, 75112)
        assert nodes[first]["state"] == 8  # vencido: some para quem venceu
        assert sum(n["state"] == 1 for n in riots if n["heroTempId"] == 75112) == 36  # os outros seguem à vista

        start = _at(7, 0)
        session.ctx.pet_rage[start] = 95
        got = await fight(_open_riot(session, 75122))  # +5: a fúria enche
        assert session.ctx.pet_rage[start] == 100
        assert {n["state"] for n in riots if n["heroTempId"] == 5101} == {1}
        got = await fight(_open_riot(session, 5101))
        state = pb.PetIslandDefendStateMsg.FromString([p.body for p in got if p.code == 4686][-1])  # type: ignore[attr-defined]
        assert (state.peaceMiddle, state.peaceHigh, state.peaceBoss, state.ragePoint) == (1, 1, 1, 100)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert sum(i.count for i in saved.items if i.template_id == 2100038) == 2 + 5 + 20

        clock.advance(3600)  # 08:00: tudo some
        g.client.send(20008)
        await g.idle()
        assert {n["state"] for n in riots} == {8}
