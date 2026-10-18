"""Templates no banco: importar e exportar dá a mesma árvore, e o ``GameTemplates`` do banco é o do arquivo."""

import zlib
from xml.etree import ElementTree

import pytest
from sqlalchemy import func, select

from tests.test_templates import REAL_FILE, XML
from wartune_server.app import _templates
from wartune_server.config import Settings
from wartune_server.persistence.database import Database
from wartune_server.persistence.schema import template_imports, template_nodes
from wartune_server.templates import store
from wartune_server.templates.repository import GameTemplates

NESTED = b"""<root>
  <Empty/>
  <Groups><Group Kind="A"><Reward Id="1" Count="2"/><Reward Id="2"/></Group></Groups>
  <Items><ItemTempInfo TemplateId="10" Name="Espada &amp; &lt;escudo&gt;"/><ItemTempInfo TemplateId="11"/></Items>
</root>"""


def _tree(e: ElementTree.Element) -> tuple[object, ...]:
    return (e.tag, dict(e.attrib), [_tree(c) for c in e])


async def _round_trip(database: Database, data: bytes) -> None:
    await store.import_xml(database.engine, data, "teste")
    raw = zlib.decompress(data) if data[:1] == b"\x78" else data
    exported = await store.export_xml(database.engine)
    assert _tree(ElementTree.fromstring(zlib.decompress(exported))) == _tree(ElementTree.fromstring(raw))
    loaded, parsed = await store.load(database.engine), GameTemplates.parse(data)
    assert loaded.categories == parsed.categories
    assert all(list(loaded.rows(c)) == list(parsed.rows(c)) for c in parsed.categories)


async def test_volta_igual_com_aninhado_vazio_e_escape(database: Database) -> None:
    await _round_trip(database, NESTED)
    await _round_trip(database, XML)  # o segundo import troca o conjunto inteiro
    async with database.engine.connect() as conn:
        assert await conn.scalar(select(func.count()).select_from(template_imports)) == 2
        # só o segundo arquivo: GameHeroTemp (1 linha) e MapInfos (2 linhas) = 2 categorias + 3 linhas
        assert await conn.scalar(select(func.count()).select_from(template_nodes)) == 5


async def test_row_key_liga_a_linha_pelo_id(database: Database) -> None:
    assert not await store.has_templates(database.engine)
    await store.import_xml(database.engine, NESTED, "teste")
    assert await store.has_templates(database.engine)
    async with database.engine.connect() as conn:
        rows = (
            await conn.execute(select(template_nodes.c.tag, template_nodes.c.key_name, template_nodes.c.row_key))
        ).all()
    assert ("Items", "TemplateId", None) in rows and ("ItemTempInfo", None, "10") in rows
    assert ("Group", None, "A") in rows
    assert ("Reward", None, None) in rows  # o nível aninhado (TollgateReward) fica sem chave


def test_texto_dentro_do_elemento_e_recusado() -> None:
    with pytest.raises(ValueError):
        store._nodes(ElementTree.fromstring(b"<root><A><B>texto</B></A></root>"))


@pytest.mark.skipif(not REAL_FILE.exists(), reason="precisa de data/templates/tempinfos.xml")
async def test_volta_igual_com_o_tempinfos_real(database: Database) -> None:
    await _round_trip(database, REAL_FILE.read_bytes())
    async with database.engine.connect() as conn:
        item = await conn.scalar(select(template_nodes.c.attrs).where(template_nodes.c.row_key == "2100001"))
    assert item is not None and '"TemplateId":"2100001"' in item  # o Kurt Dişi da 1001, achado pelo id


async def test_servidor_le_do_banco_quando_importado_e_do_arquivo_senao(database: Database, tmp_path) -> None:  # type: ignore[no-untyped-def]
    arquivo = tmp_path / "tempinfos.xml"
    arquivo.write_bytes(XML)
    settings = Settings(templates_file=arquivo, _env_file=None)  # type: ignore[call-arg]
    assert (await _templates(database, settings)).categories == ["GameHeroTemp", "MapInfos"]  # banco vazio: arquivo
    await store.import_xml(database.engine, NESTED, "teste")
    assert (await _templates(database, settings)).categories == ["Empty", "Groups", "Items"]  # importado: banco
