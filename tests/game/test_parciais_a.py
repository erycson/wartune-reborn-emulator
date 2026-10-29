"""Linhas parciais: taxas sem fonte no cliente em ``game_settings.taxas`` (migração 0124)."""

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

from tests.game.harness import Game, logged_in
from wartune_server.game import taxas
from wartune_server.game.handlers import offer


def _taxas(g: Game, **cfg: Any) -> None:
    world = g.server.services.world
    object.__setattr__(
        world, "settings", MappingProxyType({**world.settings, "taxas": {**world.settings["taxas"], **cfg}})
    )


async def test_taxas_seeded_with_sources(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        taxas = g.server.services.world.settings["taxas"]
        keys = set(taxas) - {"source"}
        assert keys == {
            k
            for name in taxas["source"]
            for k in name.replace("mount_star_bless/chance", "mount_star_bless mount_star_chance").split()
        }
        assert taxas["fate_wheel"] == {"1": 144, "2": 90, "3": 63, "4": 45, "10": 18}


async def test_offer_quality_follows_config(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _taxas(g, offer_quality_weights=[0, 0, 0, 0, 1])
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        st = offer._roll(s, s.snapshot, s.ctx.clock.now())
        assert set(json.loads(st.text)["q"]) <= {5}


def test_taxas_default_without_row() -> None:
    assert taxas.get({}, "fate_stone_exp") == 1 and taxas.get({"taxas": {"fate_stone_exp": 3}}, "fate_stone_exp") == 3


async def test_lucky_exchange_spends_fills_luck_and_gives_rare(tmp_path: Path) -> None:
    """Troca da sorte (9610): edição do tutorial_en #88 em 0132; cada troca soma 1 de sorte, cheia dá o raro e zera."""
    from datetime import UTC, datetime

    from wartune_server.domain.models import Item
    from wartune_server.game.handlers import minigames
    from wartune_server.protocol.messages import wartune_pb2 as pb
    from wartune_server.services.clock import FakeClock

    async with logged_in(tmp_path, novice=19000, clock=FakeClock(datetime(2026, 10, 25, 12, tzinfo=UTC))) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        snap = s.snapshot
        ed = next(e for e in g.server.services.world.settings["lucky_exchange"]["editions"] if e["luckValue"] == 10)
        coin = Item(g.user_id, ed["consumeItemId"], pos=5, count=11)
        snap.items.append(coin)
        await s.ctx.characters.save(coin)
        g.client.send(9610, pb.LuckExchangeOpMsg(exchangeId=ed["id"], exchangeCount=11))
        await g.idle()
        assert coin.count == 11  # passa da sorte que falta: recusa
        g.client.send(9610, pb.LuckExchangeOpMsg(exchangeId=ed["id"], exchangeCount=10))
        got = await g.until(364)
        info = pb.LuckExchangeInfoListMsg.FromString(got[-1].body)
        assert coin.count == 1 and [i.currentLuckValue for i in info.luckExchangeInfo if i.exchangeId == ed["id"]] == [
            10
        ]
        luck, prize = minigames.lucky_roll(ed, 10, {})
        assert luck == 0 and prize == [(21261042, 2)]  # o único raro da edição


def test_pet_is_born_unbound() -> None:
    """72bb0e1: language PetAdvancedView.useBindPointTip/useBindGoodsTip: o vínculo vem do uso, não do nascimento."""
    from wartune_server.domain.models import Pet

    assert Pet(1, 101103, "Amazon").is_bind is False


async def test_player_hero_uses_suite_slots_from_settings(tmp_path: Path, monkeypatch: Any) -> None:
    """40ac553: o bônus de coleção na luta usa os degraus de ``powcard_suite_slots`` do banco."""
    from wartune_server.game.handlers import campaign, systems

    seen: list[Any] = []

    def fake(snap: Any, templates: Any, camp: int, slots: Any = None) -> dict[str, int]:
        seen.append(slots)
        return {}

    monkeypatch.setattr(systems, "camp_stats", fake)
    async with logged_in(tmp_path, novice=19000) as g:
        world = g.server.services.world
        object.__setattr__(world, "settings", MappingProxyType({**world.settings, "powcard_suite_slots": [[1, 1]]}))
        s = g.server.online.get(g.user_id)
        assert s is not None
        campaign.player_hero(s, {"player": {"livingId": 1, "pos": 0}}, camp=systems.CAMP_ARENA)
        assert seen == [[[1, 1]]]


async def test_fund_harvest_items_are_bound(tmp_path: Path) -> None:
    """language fund.FundFrame.helpFrame.helpContent: "Items obtained during the event are bound"."""
    from wartune_server.protocol.messages import wartune_pb2 as pb

    async with logged_in(tmp_path, novice=19000) as g:
        world = g.server.services.world
        fund = {
            **world.settings["novice_fund"],
            "levels": [{"level": 1, "costDiamond": 10, "tiers": [[1, 1, [[208017, 2]]]]}],
        }
        object.__setattr__(world, "settings", MappingProxyType({**world.settings, "novice_fund": fund}))
        s = g.server.online.get(g.user_id)
        assert s is not None and s.snapshot is not None
        s.snapshot.character.point = 100
        s.snapshot.character.grades = max(s.snapshot.character.grades, int(fund.get("minGrades", 0)))
        g.client.send(8751, pb.DepositActiveMsg(opType=1, opParam=1))
        await g.idle()
        g.client.send(8751, pb.DepositActiveMsg(opType=2, opParam=1))
        await g.idle()
        got = [i for i in s.snapshot.items if i.template_id == 208017]
        assert got and all(i.is_binds for i in got)


def test_vice_reset_days_from_taxas() -> None:
    """0134: o prazo do reset da senha secundária vem de ``taxas.vp_reset_days``."""
    from datetime import UTC, datetime, timedelta

    from wartune_server.domain.models import Character
    from wartune_server.game.handlers import account

    now = datetime(2026, 10, 29, tzinfo=UTC)
    c = Character(account_id=1, server_id=1, created_at=now)
    c.vice_password, c.vice_reset_at = "135790", now - timedelta(days=2)
    assert not account.expire_vice_reset(c, now, {"taxas": {"vp_reset_days": 3}})
    assert account.expire_vice_reset(c, now, {"taxas": {"vp_reset_days": 1}}) and c.vice_password == ""
