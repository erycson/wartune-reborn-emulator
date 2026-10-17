"""Templates estáticos do jogo (``tempinfos.xml``): heróis, itens, prédios, mapas...

É o mesmo arquivo que o cliente baixa de ``TEMPLATE_PATH``, então servidor e
cliente sempre concordam. O arquivo oficial vem comprimido em zlib; aceitamos
também o XML puro. Somente leitura depois de carregado: pode ser compartilhado
entre corrotinas sem trava.
"""

from __future__ import annotations

import asyncio
import zlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from xml.etree import ElementTree

Row = Mapping[str, str]


@dataclass(frozen=True, slots=True)
class HeroTemplate:
    template_id: int
    name: str
    job: int
    sex: int
    power: int
    agility: int
    intellect: int
    captain: int
    physique: int
    live: int
    force_hit: int
    parry: int
    skill_script: str

    @classmethod
    def from_row(cls, row: Row) -> HeroTemplate:
        return cls(
            template_id=int(row["TemplateId"]),
            name=row.get("TemplateName", ""),
            job=int(row["Job"]),
            sex=int(row["Sexs"]),
            power=int(row["Power"]),
            agility=int(row["Agility"]),
            intellect=int(row["Intellect"]),
            captain=int(row["Captain"]),
            physique=int(row["Physique"]),
            live=int(row["Live"]),
            force_hit=int(row["ForceHit"]),
            parry=int(row["Parry"]),
            skill_script=row.get("SkillScript", ""),
        )


class GameTemplates:
    def __init__(self, categories: dict[str, list[Row]]) -> None:
        self._categories = categories
        self._index: dict[tuple[str, str], dict[str, Row]] = {}
        self._heroes = {
            t.template_id: t for t in (HeroTemplate.from_row(r) for r in categories.get("GameHeroTemp", []))
        }

    @classmethod
    def parse(cls, data: bytes) -> GameTemplates:
        if data[:1] == b"\x78":  # cabeçalho zlib
            data = zlib.decompress(data)
        root = ElementTree.fromstring(data)
        categories: dict[str, list[Row]] = {}
        for category in root:
            categories[category.tag] = [MappingProxyType(dict(item.attrib)) for item in category]
        return cls(categories)

    @classmethod
    async def load(cls, path: Path) -> GameTemplates:
        data = await asyncio.to_thread(path.read_bytes)
        return await asyncio.to_thread(cls.parse, data)

    @property
    def categories(self) -> list[str]:
        return sorted(self._categories)

    def rows(self, category: str) -> list[Row]:
        return self._categories.get(category, [])

    def find(self, category: str, **attrs: object) -> Iterator[Row]:
        wanted = {k: str(v) for k, v in attrs.items()}
        for row in self.rows(category):
            if all(row.get(k) == v for k, v in wanted.items()):
                yield row

    def get(self, category: str, template_id: int, key: str = "TemplateId") -> Row | None:
        """Busca indexada pela chave (a primeira linha vence se houver repetição)."""
        index = self._index.get((category, key))
        if index is None:
            index = {}
            for row in self.rows(category):
                index.setdefault(row.get(key, ""), row)
            self._index[(category, key)] = index
        return index.get(str(template_id))

    def hero(self, template_id: int) -> HeroTemplate:
        try:
            return self._heroes[template_id]
        except KeyError:
            raise KeyError(f"template de herói {template_id} não existe") from None
