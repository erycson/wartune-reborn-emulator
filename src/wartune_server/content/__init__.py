"""Conteúdo de jogo que não está no ``tempinfos.xml`` (era do banco do servidor oficial)."""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any


@cache
def tutorial() -> dict[str, Any]:
    """Nós, batalhas e diálogos da campanha de treino (``tools/extract_tutorial.py``)."""
    text = resources.files(__package__).joinpath("tutorial.json").read_text(encoding="utf-8")
    return json.loads(text)  # type: ignore[no-any-return]


@cache
def dungeon() -> dict[str, Any]:
    """Mapas, batalhas, Pandora e fim da masmorra Kurt İni, campanha 1001 (``tools/extract_dungeon.py``)."""
    text = resources.files(__package__).joinpath("dungeon_1001.json").read_text(encoding="utf-8")
    return json.loads(text)  # type: ignore[no-any-return]


@cache
def pet_island() -> dict[str, Any]:
    """Nós da ilha dos pets (mapa 20001) como o oficial mandou no 127 (``captures/peri_adasi_tp.json`` #8).

    Textos em inglês: tempinfos (heróis 75102/20010/5101, MapNodeInfo 4 do Alice, item 2100028) e language.txt
    (PetBossInfoView.monsterText0/1, PetExchangeShopFrame.title, Mystic's Gate, Sylph Atoll); texto deduzido (sem
    fonte no cliente/captura): o "I"/"Floor 2" dos nomes, "Leave" e o diálogo do The Stranger."""
    text = resources.files(__package__).joinpath("petisland.json").read_text(encoding="utf-8")
    return json.loads(text)  # type: ignore[no-any-return]
