import zlib
from pathlib import Path
from xml.etree import ElementTree

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from wartune_server.templates.repository import GameTemplates

XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<root>
  <GameHeroTemp>
    <GameHeroTempInfo TemplateId="6" TemplateName="Maga" Job="3" Sexs="0" Power="1" Agility="1" Intellect="5"
      Captain="100" Physique="5" Live="90" ForceHit="10" Parry="10" SkillScript="30711,30811"/>
  </GameHeroTemp>
  <MapInfos><MapInfo Id="1" Name="A"/><MapInfo Id="2" Name="B"/></MapInfos>
</root>"""

REAL_FILE = Path("data/templates/tempinfos.xml")


def test_parses_zlib_and_plain() -> None:
    for data in (XML, zlib.compress(XML)):
        t = GameTemplates.parse(data)
        assert t.hero(6).intellect == 5
        assert [r["Name"] for r in t.find("MapInfos", Id=2)] == ["B"]


def test_unknown_hero_raises() -> None:
    with pytest.raises(KeyError):
        GameTemplates.parse(XML).hero(99)


@pytest.mark.skipif(not REAL_FILE.exists(), reason="tempinfos.xml real ausente (rode wartune-server templates update)")
async def test_real_file_has_the_six_starting_heroes() -> None:
    t = await GameTemplates.load(REAL_FILE)
    assert len(t.categories) > 50
    assert [t.hero(i).job for i in range(1, 7)] == [1, 2, 3, 1, 2, 3]
    assert [t.hero(i).sex for i in range(1, 7)] == [1, 1, 1, 0, 0, 0]


async def test_download_replaces_local_file_only_when_valid(tmp_path: Path) -> None:
    cache = tmp_path / "xml" / "tempinfos.xml"

    async def good(_: web.Request) -> web.Response:
        return web.Response(body=zlib.compress(XML))

    async def broken(_: web.Request) -> web.Response:
        return web.Response(body=b"<root")

    app = web.Application()
    app.router.add_get("/xml/tempinfos.xml", good)
    app.router.add_get("/broken.xml", broken)
    async with TestServer(app) as cdn:
        t = await GameTemplates.download(str(cdn.make_url("/xml/tempinfos.xml")), cache)
        assert t.hero(6).intellect == 5 and zlib.decompress(cache.read_bytes()) == XML
        with pytest.raises(ElementTree.ParseError):  # arquivo quebrado não substitui o bom
            await GameTemplates.download(str(cdn.make_url("/broken.xml")), cache)
        with pytest.raises(aiohttp.ClientResponseError):
            await GameTemplates.download(str(cdn.make_url("/nada.xml")), cache)
    assert zlib.decompress(cache.read_bytes()) == XML
