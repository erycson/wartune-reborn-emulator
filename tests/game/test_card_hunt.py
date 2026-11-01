"""Great Card Hunt (9502) e cartas sem nenhuma (9505 op 2, 4902 vazio) contra a captura 20261029-121453-1 (d29)."""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import bag
from wartune_server.game.events import EventCatalog
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
    r.choices = lambda seq, weights=None, k=1: [seq[-1]]  # type: ignore[method-assign,assignment]  # Expert, x5
    monkeypatch.setattr(treasure_hunt, "RNG", r)


async def test_hunt_open_explore_and_treasure_follow_the_capture(tmp_path: Path, rng: None) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        assert _codes(await _seek(g, 1)) == [111]  # abaixo do 32
        snap = _snap(g)
        snap.character.grades, snap.character.gold = 32, 100000
        session = g.server.online.get(g.user_id)
        assert session is not None
        session.ctx = replace(session.ctx, events=EventCatalog.load(Path("data/events.json")))  # a do d29
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
    r.choice = lambda seq: 8 if 8 in seq else seq[1]  # type: ignore[method-assign,assignment]  # Daru
    r.choices = lambda seq, weights=None, k=1: [seq[0]]  # type: ignore[method-assign,assignment]  # Novice, x2
    monkeypatch.setattr(treasure_hunt, "RNG", r)
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.strategy, gold = 32, 20000, snap.character.gold
        info = pb.PlayerSeekInfoMsg.FromString(_body(await _seek(g, 3), 4914))
        assert "19200 Daru" in info.eventDesc and info.curNodeId == 8
        got = await _seek(g, 4)  # d29 #2838-#2857: 3 no lugar do 109
        assert _codes(got) == [3, 115, 4476, 111, 4915, 4914, 83, 83]
        assert (snap.character.strategy, snap.character.gold) == (800, gold)
        line = pb.MessageForSeekMsg.FromString(_body(got, 4915)).info
        assert line == "Gained Novice Summoner's Kitx1,Summoner's Shardx2 from Banshee Wetlands"


async def test_kyanite_price_follows_the_level_and_leaves_in_the_castle_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """183522 #8985-#9003 (nível 34): a caravana pede 680 Kyanite; sai no 109 ``crystalsCount``."""
    r = random.Random(1)
    r.choice = lambda seq: 14 if 14 in seq else seq[-1]  # type: ignore[method-assign,assignment]  # Kyanite
    r.choices = lambda seq, weights=None, k=1: [seq[1]]  # type: ignore[method-assign,assignment]  # Expert, x3
    monkeypatch.setattr(treasure_hunt, "RNG", r)
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades, snap.character.crystals, gold = 34, 1000, snap.character.gold
        info = pb.PlayerSeekInfoMsg.FromString(_body(await _seek(g, 3), 4914))
        assert "<font color='#ff0000'>680 Kyanite</font>" in info.eventDesc
        got = await _seek(g, 4)
        assert _codes(got)[0] == 109 and (snap.character.crystals, snap.character.gold) == (320, gold)
        assert pb.CastleYieldMsg.FromString(_body(got, 109)).crystalsCount == 320
        line = pb.MessageForSeekMsg.FromString(_body(got, 4915)).info
        assert line == "Gained Expert Summoner's Kitx1,Summoner's Shardx3 from Edena Village"


async def test_plus_with_ten_refuses_without_spending(tmp_path: Path, rng: None) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades = 32
        await g.server.services.characters.save(*bag.add(snap, g.server.services.templates, 2131022, 8, NOW))
        for _ in range(7):
            await _seek(g, 7)
        got = await _seek(g, 7)  # 10 explorações: huntcountFull, o item fica
        assert _codes(got) == [111] and "Treasure Hunt limit" in pb.ChatChannelMsg.FromString(got[0].body).encodeMsg
        assert bag.count_of(snap, 2131022) == 1


async def test_expert_kits_give_one_card_each_and_cards_enter_the_collection(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades = 32
        templates = g.server.services.templates
        kits = bag.add(snap, templates, 2131017, 5, NOW)
        await g.server.services.characters.save(*kits)
        g.client.send(5006, pb.ItemUseMsg(pos=kits[0].pos, count=5, bagType=1))  # d31 #4024-#4040
        got = await g.idle()
        assert _codes(got) == [115, 115, 4476, 111, 3, 83]
        cards = [i for i in bag.in_bag(snap) if templates.get("ItemTempInfos", i.template_id).get("SonType") == "600"]
        assert sum(i.count for i in cards) == 5
        assert all(templates.get("ItemTempInfos", i.template_id)["Profile"] in ("2", "3") for i in cards)

        for i in list(cards):
            snap.items.remove(i)
        lancer, velus = bag.add(snap, templates, 6000002, 1, NOW), bag.add(snap, templates, 6000012, 1, NOW)
        await g.server.services.characters.save(*lancer, *velus)
        g.client.send(5006, pb.ItemUseMsg(pos=lancer[0].pos, count=1, bagType=1))  # d31 #4043-#4053
        got = await g.idle()
        assert _codes(got) == [115, 111, 4902, 150, 4903, 83, 83, 4905, 4902, 3]
        texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83]
        assert texts == [
            "Congrats! You just received the 1st card, [Tauren Tribe].",
            "Card Tauren Lancer · Karlan has been successfully activated!",
        ]
        add = pb.PowcardFightAddMsg.FromString(_body(got, 4902)).singlefightadd
        assert [(a.userid, a.campType, a.add) for a in add] == [(0, 800, 160)]
        g.client.send(5006, pb.ItemUseMsg(pos=velus[0].pos, count=1, bagType=1))  # d31 #4057-#4067
        got = await g.idle()
        suites = pb.PowCardSuiteListMsg.FromString(_body(got, 4905)).suites
        assert [(c.tempId, c.buf.bufId, c.isActive) for s in suites for c in s.cardInfos] == [
            (10002, 3020, 0),
            (10012, 4020, 1),
        ]
        add = pb.PowcardFightAddMsg.FromString(_body(got, 4902)).singlefightadd
        assert [(a.campType, a.add) for a in add] == [(800, 160), (802, 160)]
        g.client.send(9505, pb.PowCardReqMsg(op=2))  # d31 #4119-#4120: nenhuma carta na mochila
        assert [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in await g.idle()] == [
            "There are no cards to be activated."
        ]


async def test_repeated_card_stays_in_the_bag_and_op3_burns_it_up_to_the_next_grade(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        sy = snap.systems
        assert sy is not None
        templates = g.server.services.templates
        sy.powcards = "10001:1:8:0"  # grau 1 -> 2 pede 10 (UpGradeTempInfos Types 29 + Profile)
        held = bag.add(snap, templates, 6000001, 5, NOW)
        await g.server.services.characters.save(sy, *held)
        g.client.send(5006, pb.ItemUseMsg(pos=held[0].pos, count=1, bagType=1))  # repetida: não entra
        await g.idle()
        assert sy.powcards == "10001:1:8:0"
        assert sum(i.count for i in bag.in_bag(snap) if i.template_id == 6000001) == 5

        g.client.send(9505, pb.PowCardReqMsg(op=3))  # card.cardHelper.content01: engole até o Data do grau 2
        got = await g.idle()
        assert _codes(got)[0] == 115
        card = pb.PowCardSuiteListMsg.FromString(_body(got, 4905)).suites[0].cardInfos[0]
        assert (card.grade, card.gp) == (1, 10)  # taxa card_burn_gp 1: duas cópias
        assert sum(i.count for i in bag.in_bag(snap) if i.template_id == 6000001) == 3
        g.client.send(9505, pb.PowCardReqMsg(op=1, cardId=10001))
        card = pb.PowCardSuiteListMsg.FromString((await g.until(4905))[-1].body).suites[0].cardInfos[0]
        assert (card.grade, card.gp) == (2, 0)


async def test_activate_all_and_burn_follow_the_183522_capture(tmp_path: Path) -> None:
    """183522 #9217-#9250: op 2 abre uma cópia de cada carta nova da mochila, op 3 engole as repetidas."""
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades = 34
        sy = snap.systems
        assert sy is not None
        templates = g.server.services.templates
        sy.powcards = "10002:1:0:0,10012:1:0:0,10015:1:0:0,10016:1:0:0,10017:1:0:0,10024:1:0:0"  # 4905 #9233
        held = [i for tid, n in ((6000015, 1), (6000016, 2), (6000020, 2), (6000001, 3), (6000023, 1))
                for i in bag.add(snap, templates, tid, n, NOW)]  # fmt: skip
        await g.server.services.characters.save(sy, *held)
        g.client.send(9505, pb.PowCardReqMsg(op=2))
        got = await g.idle()
        assert _codes(got) == [115, 115, 115, 111, 4902, 150, 83, 83, 4903, 83, 83, 4905, 4902]
        assert pb.ChatChannelMsg.FromString(_body(got, 111)).encodeMsg == "3 cards have been successfully activated."
        assert [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83] == [
            "Congrats! You just received the 1st card, [Abyssal Souls].",
            "Card Dark Priestess · Teska has been successfully activated!",
            "Card Tauren Knight · Karfa has been successfully activated!",
            "Card Godslayer · Orcus Razor has been successfully activated!",
        ]
        suites = pb.PowCardSuiteListMsg.FromString(_body(got, 4905)).suites
        active = {c.tempId for s in suites for c in s.cardInfos if c.isActive}
        assert active == {10001, 10020, 10023}
        g.client.send(9505, pb.PowCardReqMsg(op=3))
        got = await g.idle()
        assert _codes(got) == [115] * 4 + [111, 4902, 150, 4903, 4905, 4902, 83, 83, 83, 83]
        assert pb.ChatChannelMsg.FromString(_body(got, 111)).encodeMsg == "4 cards have been successfully upgraded"
        assert sorted(pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83) == [
            "Dark Priestess · Teska gained 1 points of Card EXP.",
            "Shining Paladin · Lucia gained 2 points of Card EXP.",
            "Shining Warrior · Claudius gained 1 points of Card EXP.",
            "Tauren Knight · Karfa gained 2 points of Card EXP.",
        ]
        suites = pb.PowCardSuiteListMsg.FromString(_body(got, 4905)).suites
        assert not any(c.isActive for s in suites for c in s.cardInfos)
        assert not [i for i in bag.in_bag(snap) if 6000000 < i.template_id < 6000100]


async def test_hunt_activity_counts_per_day(tmp_path: Path, rng: None) -> None:
    """A atividade "Great Card Hunt" (101) zera no outro dia: 121453 fecha o 29/10 em 5, 183522 abre o 31/10 em 0."""
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        snap = _snap(g)
        snap.character.grades = 32
        session = g.server.online.get(g.user_id)
        assert session is not None
        session.ctx = replace(session.ctx, events=EventCatalog.load(Path("data/events.json")))
        await _seek(g, 3)
        await _seek(g, 5)
        g.server.services.clock.advance(86400)  # type: ignore[attr-defined]
        got = await _seek(g, 3)
        assert [d.value for d in pb.SumActiveDataMsg.FromString(_body(got, 4476)).datas] == [1]
