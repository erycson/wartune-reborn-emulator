"""Templates do jogo no banco: o ``tempinfos.xml`` inteiro, nó por nó, para gerar o XML de volta e cruzar com o
que cada jogador tem ou comprou (``template_nodes.row_key`` = ``TemplateId``/``Id`` da linha).

O arquivo é uma árvore rasa: ``<root>`` > categoria (``ItemTempInfos``) > linha (``ItemTempInfo``, atributos) e, só
no ``TollgateReward``, mais um nível. Cada elemento abaixo da raiz vira uma linha de ``template_nodes`` com o pai, a
posição, a tag e os atributos (JSON na ordem do arquivo). Importar troca o conjunto inteiro numa transação.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from xml.etree import ElementTree

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ..persistence.schema import template_imports, template_nodes
from .repository import GameTemplates, Row

BATCH = 5000


@dataclass(frozen=True, slots=True)
class ImportResult:
    categories: int
    nodes: int
    sha256: str


def _key_name(rows: list[ElementTree.Element]) -> str | None:
    """Coluna id da categoria: o primeiro atributo da primeira linha, se estiver em todas e não repetir."""
    if not rows or not rows[0].attrib:
        return None
    name = next(iter(rows[0].attrib))
    values = [r.get(name) for r in rows]
    return name if None not in values and len(set(values)) == len(values) else None


def _nodes(root: ElementTree.Element) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def walk(element: ElementTree.Element, parent: int | None, key: str | None) -> None:
        """``key``: o atributo que vira ``row_key`` dos filhos (só as linhas de uma categoria têm)."""
        for position, child in enumerate(element):
            if (child.text or "").strip():
                raise ValueError(f"<{child.tag}> com texto: o formato do tempinfos só usa atributos")
            node_id = len(out) + 1
            child_key = _key_name(list(child)) if parent is None else None
            out.append(
                {
                    "id": node_id,
                    "parent_id": parent,
                    "position": position,
                    "tag": child.tag,
                    "key_name": child_key,
                    "row_key": child.get(key) if key else None,
                    "attrs": json.dumps(dict(child.attrib), ensure_ascii=False, separators=(",", ":")),
                }
            )
            walk(child, node_id, child_key)

    walk(root, None, None)
    return out


async def import_xml(engine: AsyncEngine, data: bytes, source: str) -> ImportResult:
    """Troca os templates do banco pelos do arquivo (zlib como o oficial, ou XML puro)."""
    raw = zlib.decompress(data) if data[:1] == b"\x78" else data
    root = ElementTree.fromstring(raw)
    if root.attrib:
        raise ValueError("<root> com atributos: formato inesperado")
    nodes = _nodes(root)
    digest = hashlib.sha256(raw).hexdigest()
    async with engine.begin() as conn:
        await conn.execute(delete(template_nodes))
        for start in range(0, len(nodes), BATCH):
            await conn.execute(insert(template_nodes), nodes[start : start + BATCH])
        await conn.execute(
            insert(template_imports).values(
                source=source[:255], sha256=digest, nodes=len(nodes), imported_at=datetime.now(UTC)
            )
        )
    return ImportResult(categories=len(root), nodes=len(nodes), sha256=digest)


async def _all(engine: AsyncEngine) -> list[tuple[int, int | None, str, str]]:
    query = select(template_nodes.c.id, template_nodes.c.parent_id, template_nodes.c.tag, template_nodes.c.attrs)
    async with engine.connect() as conn:
        rows = await conn.execute(query.order_by(template_nodes.c.parent_id, template_nodes.c.position))
        return [(r.id, r.parent_id, r.tag, r.attrs) for r in rows]


def _children(nodes: list[tuple[int, int | None, str, str]]) -> dict[int | None, list[tuple[int, str, str]]]:
    tree: dict[int | None, list[tuple[int, str, str]]] = {}
    for node_id, parent, tag, attrs in nodes:
        tree.setdefault(parent, []).append((node_id, tag, attrs))
    return tree


async def has_templates(engine: AsyncEngine) -> bool:
    async with engine.connect() as conn:
        return bool(await conn.scalar(select(func.count()).select_from(template_nodes)))


async def load(engine: AsyncEngine) -> GameTemplates:
    """``GameTemplates`` igual ao de ``GameTemplates.parse`` do arquivo importado (linhas na mesma ordem)."""
    tree = _children(await _all(engine))
    categories: dict[str, list[Row]] = {}
    for node_id, tag, _ in tree.get(None, []):
        categories[tag] = [MappingProxyType(json.loads(attrs)) for _, _, attrs in tree.get(node_id, [])]
    return GameTemplates(categories)


async def export_xml(engine: AsyncEngine) -> bytes:
    """O ``tempinfos.xml`` do banco, comprimido em zlib como o oficial (o cliente descomprime)."""
    tree = _children(await _all(engine))
    root = ElementTree.Element("root")

    def build(parent: ElementTree.Element, node_id: int | None) -> None:
        for child_id, tag, attrs in tree.get(node_id, []):
            build(ElementTree.SubElement(parent, tag, json.loads(attrs)), child_id)

    build(root, None)
    ElementTree.indent(root, space="  ")
    return zlib.compress(ElementTree.tostring(root, encoding="utf-8", xml_declaration=True), 9)
