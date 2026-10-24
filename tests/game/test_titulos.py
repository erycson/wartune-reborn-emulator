"""Títulos: o 4484 igual ao do oficial inglês e os 9 depois de item ganho."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import titles
from wartune_server.game.handlers import events as hev
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
CAPTURES = Path(__file__).parents[2] / "captures"


def _official(name: str) -> list[bytes]:
    d = json.loads((CAPTURES / name).read_text(encoding="utf-8"))
    pk = d if isinstance(d, list) else d["packets"]
    return [bytes.fromhex(p["bodyHex"]) for p in pk if p["code"] == 4484 and not p["isClient"]]


def test_4484_byte_a_byte_com_o_oficial() -> None:
    templates = GameTemplates.parse(TEMPLATES.read_bytes())
    maga = SimpleNamespace(job=3, geste=0, consortia_total_offer=0)
    assert titles.appells_msg(maga, templates).SerializeToString() == _official("tutorial_en.json")[0]  # type: ignore[arg-type]
    # 171155: a contribuição da guilda (título 30) foi a 10
    with_offer = SimpleNamespace(job=3, geste=0, consortia_total_offer=10)
    assert titles.appells_msg(with_offer, templates).SerializeToString() in _official("oficial_20261023-171155-1.json")  # type: ignore[arg-type]
    assert titles.item_checks(templates) == 9


async def test_item_ganho_manda_4476_e_os_9_titulos(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None
        hev.items_gained(session)
        got = [p.code for p in await g.idle()]
        assert got == [4476] + [4484] * 9
        assert len(pb.AppellsMsg.FromString((await _again(g, session)).body).appells) == 221


async def _again(g, session):  # type: ignore[no-untyped-def]
    hev.send_titles(session)
    return (await g.until(4484))[-1]
