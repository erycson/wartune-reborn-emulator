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
