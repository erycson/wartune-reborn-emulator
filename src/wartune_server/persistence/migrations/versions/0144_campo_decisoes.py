"""taxas do campo: minério uniforme e o alcance do guardião conferido nas capturas

field_ore_weights: decisão do usuário, sorteio uniforme (as 26 entregas vistas são poucas para pesos).
field_guardian_range: (visto) 121453, as duas perseguições do campo (4105 do guardião 1795, Paladin 72,32):
#10205 com o jogador em 96,31 (24 casas, fim do 5124 #10203 vindo de 109,32) e #10435 em 98,32 (26 casas, começo do
5124 #10434). A 109 (37) não perseguiu; o oficial confere nas pontas do trecho, então 26 é o menor alcance que cobre
os dois. A 152321 não tem perseguição no campo.

Revision ID: 0144
Revises: 0143
Create Date: 2026-10-29 23:45:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0144"
down_revision = "0143"
branch_labels = None
depends_on = None

NEW: dict[str, Any] = {"field_ore_weights": {"superior": 1, "normal": 1, "inferior": 1}, "field_guardian_range": 26}
OLD: dict[str, Any] = {"field_ore_weights": {"superior": 12, "normal": 5, "inferior": 9}, "field_guardian_range": 26}
SOURCES = {
    "field_ore_weights": "decisão do usuário: uniforme",
    "field_guardian_range": "(visto) 121453 4105 #10205 a 24 e #10435 a 26 casas (Chebyshev) do guardião 72,32",
}
OLD_SOURCES = {
    "field_ore_weights": "(visto) contagem das 26 entregas",
    "field_guardian_range": "(visto) 121453 #10205/#10435 a 24 e 26 casas; TODO(inventado) o alcance",
}


def _settings() -> Any:
    return sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _load(conn: sa.Connection) -> dict[str, Any] | None:
    s = _settings()
    row = conn.execute(sa.select(s.c.value).where(s.c.key == "taxas")).first()
    if row is None:
        return None
    return dict(row[0] if isinstance(row[0], dict) else json.loads(row[0]))


def _save(conn: sa.Connection, value: dict[str, Any]) -> None:
    s = _settings()
    conn.execute(s.update().where(s.c.key == "taxas").values(value=json.dumps(value)))


def _apply(values: dict[str, Any], sources: dict[str, str]) -> None:
    conn = op.get_bind()
    if (data := _load(conn)) is not None:
        data |= values
        data.setdefault("source", {}).update(sources)
        _save(conn, data)


def upgrade() -> None:
    _apply(NEW, SOURCES)


def downgrade() -> None:
    _apply(OLD, OLD_SOURCES)
