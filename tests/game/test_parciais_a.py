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
