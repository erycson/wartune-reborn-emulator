"""Great Card Hunt (9502) e cartas sem nenhuma (9505 op 2, 4902 vazio) contra a captura 20261029-121453-1 (d29)."""

from __future__ import annotations

import random
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import bag
from wartune_server.game.handlers import treasure_hunt
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)  # dentro da "10/29 Great Card Hunt" (data/events.json)
SKIP = {4426, 4484, 4594, 112}  # montaria, títulos e missão dependem do personagem do teste


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _codes(got: list[Packet]) -> list[int]:
    return [p.code for p in got if p.code not in SKIP]


def _body(got: list[Packet], code: int) -> bytes:
    return next(p.body for p in reversed(got) if p.code == code)


async def _seek(g: Game, op: int) -> list[Packet]:
    g.client.send(9502, pb.PlayerSeekInfoMsg(op=op))
    return await g.idle()


@pytest.fixture
def rng(monkeypatch: pytest.MonkeyPatch) -> None:
    r = random.Random(1)
    r.choice = lambda seq: 12 if 12 in seq else seq[0]  # type: ignore[method-assign,assignment]
    monkeypatch.setattr(treasure_hunt, "RNG", r)


async def test_hunt_open_explore_and_treasure_follow_the_capture(tmp_path: Path, rng: None) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        assert _codes(await _seek(g, 1)) == [111]  # abaixo do 32
        snap = _snap(g)
        snap.character.grades, snap.character.gold = 32, 100000
        info = pb.PlayerSeekInfoMsg.FromString(_body(await _seek(g, 1), 4914))  # d29 #448
        assert (info.op, info.seekCount, info.nextAddTime, info.state, info.curNodeId) == (1, 3, 21600, 0, 7)
        nodes = info.seekNodeList.seekNode
        assert len(nodes) == 36 and (nodes[11].nodeName, nodes[11].pointX, nodes[11].pointY) == (
            "Roaring Wetlands",
            476,
            308,
        )
        got = await _seek(g, 3)  # d29 #450-#453: 4476 só da atividade, sem 4915
        assert _codes(got) == [4476, 4914]
        data = pb.SumActiveDataMsg.FromString(_body(got, 4476))
        assert [(d.type, d.value, d.activeCharge) for d in data.datas] == [(101, 1, 0)]
        assert all(p.getCount == 0 for p in data.datas[0].packdata)  # #450: 0, o de todas leva 10
        info = pb.PlayerSeekInfoMsg.FromString(_body(got, 4914))
        assert (info.op, info.seekCount, info.state, info.curNodeId) == (3, 2, 1, 12)
        assert "32000 Gold" in info.eventDesc
        got = await _seek(g, 4)  # d29 #552-#570, com espaço na mochila
        assert _codes(got) == [109, 115, 4476, 111, 4915, 4914, 83, 83]
        assert snap.character.gold == 100000 - 32000
        gained = "Gained Expert Summoner's Kitx1,Summoner's Shardx5 from Roaring Wetlands"
        assert pb.MessageForSeekMsg.FromString(_body(got, 4915)).info == gained
        alert = pb.ChatChannelMsg.FromString(_body(got, 111)).encodeMsg
        assert alert == "Received: Expert Summoner's Kit x1, Summoner's Shard x5"
        chats = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83]
        assert chats == [alert, gained]
        info = pb.PlayerSeekInfoMsg.FromString(_body(got, 4914))
        assert (info.op, info.state, info.curNodeId, info.eventDesc) == (4, 0, 12, "")
        assert bag.count_of(snap, 2131017) == 1 and bag.count_of(snap, 2131019) == 5
        got = await _seek(g, 4)  # d29 #514-#528: o segundo clique
        assert _codes(got) == [111]
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "Operation failed"


async def test_hunt_treasure_with_full_bag_goes_by_mail(
    tmp_path: Path, rng: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.gold = 32, 100000
        await _seek(g, 3)
        monkeypatch.setattr(bag, "fits", lambda *a, **k: False)
        got = await _seek(g, 4)  # d29 #478-#496
        assert _codes(got) == [109, 148, 111, 4915, 4914, 83, 83]
        alert = pb.ChatChannelMsg.FromString(_body(got, 111)).encodeMsg
        assert alert.endswith("Summoner's Shard x5, inventory full, please check your mail!")
        session = g.server.online.get(g.user_id)
        assert session is not None
        mails = await session.ctx.characters.read(lambda uow: uow.mails.by_receiver(g.user_id))
        hunt = [m for m in mails if m.title == "Treasure Hunt Rewards"]
        assert hunt and hunt[0].validity_days == 3 and hunt[0].send_type == 4


async def test_hunt_recharges_every_six_hours_and_exchanges(tmp_path: Path, rng: None) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades = 32
        await _seek(g, 1)
        g.server.services.clock.advance(21600 + 60)  # type: ignore[attr-defined]
        info = pb.PlayerSeekInfoMsg.FromString(_body(await _seek(g, 2), 4914))
        assert (info.seekCount, info.nextAddTime) == (4, 21600 - 60)
        shards = bag.add(snap, g.server.services.templates, 2131019, 100, NOW)
        await g.server.services.characters.save(*shards)
        await _seek(g, 6)
        assert bag.count_of(snap, 2131018) == 1 and bag.count_of(snap, 2131019) == 0


async def test_activate_without_cards_only_alerts_and_fight_add_is_empty_from_32(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        g.client.send(9505, pb.PowCardReqMsg(op=2, cardId=0))  # d29 #574-#575
        got = await g.idle()
        assert [p.code for p in got] == [111]
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "There are no cards to be activated."
        session = g.server.online.get(g.user_id)
        assert session is not None
        from wartune_server.game.handlers.player import _army

        _army(session)  # nível 31 ou menos: 150 sem 4902 (d29 #6-#160)
        assert [p.code for p in await g.idle()] == [150]
        _snap(g).character.grades = 32
        _army(session)  # do 32 em diante: 4902 vazio antes do 150 (d29 #536-#537)
        got = await g.idle()
        assert [p.code for p in got] == [4902, 150] and got[0].body == b""
        from wartune_server.game.handlers.player import push_level
        from wartune_server.game.handlers.systems import send_fight_add

        send_fight_add(session, 2)  # 5185 (#615-#617) usa 1 solto + o do 150
        assert [p.code for p in await g.idle()] == [4902, 4902]
        await push_level(session, 31)  # subida ao 32 (#422-#426): 4902 ×3 antes do 100/150, o 150 sem outro
        codes = [p.code for p in await g.idle()]
        first = codes.index(4902)
        assert codes[first : first + 3] == [4902] * 3 and codes.count(4902) == 3 and codes.index(150) > first + 2


async def test_plus_spends_an_exploration_artifact(tmp_path: Path, rng: None) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades = 32
        got = await _seek(g, 7)  # d29 #2859-#2860
        assert _codes(got) == [111]
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "Not enough Exploration Artifact!"
        await g.server.services.characters.save(*bag.add(snap, g.server.services.templates, 2131022, 1, NOW))
        got = await _seek(g, 7)  # d29 #2803-#2806: 115, 111, 4914 op 2
        assert _codes(got) == [115, 111, 4914]
        assert pb.ChatChannelMsg.FromString(_body(got, 111)).encodeMsg == "Treasure Hunt attempts increased!"
        info = pb.PlayerSeekInfoMsg.FromString(_body(got, 4914))
        assert (info.op, info.seekCount) == (2, 4) and bag.count_of(snap, 2131022) == 0


async def test_dwarf_merchant_charges_daru_in_the_player_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = random.Random(1)
    r.choice = lambda seq: 8 if 8 in seq else seq[-1]  # type: ignore[method-assign,assignment]
    monkeypatch.setattr(treasure_hunt, "RNG", r)
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.strategy, gold = 32, 20000, snap.character.gold
        info = pb.PlayerSeekInfoMsg.FromString(_body(await _seek(g, 3), 4914))
        assert "19200 Daru" in info.eventDesc and info.curNodeId == 8
        got = await _seek(g, 4)  # d29 #2838-#2857: 3 no lugar do 109
        assert _codes(got) == [3, 115, 4476, 111, 4915, 4914, 83, 83]
        assert (snap.character.strategy, snap.character.gold) == (800, gold)
        assert pb.MessageForSeekMsg.FromString(_body(got, 4915)).info.endswith("Shardx2 from Banshee Wetlands")
