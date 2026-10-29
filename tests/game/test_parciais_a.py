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
