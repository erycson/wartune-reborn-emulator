"""taxas: compras do torneio de fadas, força do robô, castTime padrão do inimigo e defesa no dano do veículo

Soma em ``game_settings.taxas`` (0124): ``pet_max_buy`` (compras do torneio de fadas por dia; o cliente não traz),
``robot_hp``/``robot_attack`` (fração da vida e do ataque do jogador no robô do coliseu), ``enemy_cast_ms`` (castTime
de skill inimiga fora da tabela vista). Soma em ``game_settings.vehicle_match`` (0130) ``defence_div`` (dano do
veículo = ataque × Power% - defesa / defence_div). Nenhum está no decomp inglês, no mirror nem no language.txt:
``TODO(inventado)``, aguarda dump.

Revision ID: 0135
Revises: 0134
Create Date: 2026-10-29 18:00:00.000000
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0135"
down_revision = "0134"
branch_labels = None
depends_on = None

INV = "TODO(inventado)"
NEW: dict[str, Any] = {"pet_max_buy": 10, "robot_hp": 0.35, "robot_attack": 0.15, "enemy_cast_ms": 3500}
SOURCES = {
    "pet_max_buy": INV + " (como o coliseu, MAX_BUY)",
    "robot_hp": INV + " (simulado: guerreiro e mago vencem 15/15 do 11 ao 50)",
    "robot_attack": INV + " (idem robot_hp)",
    "enemy_cast_ms": INV + " (o valor mais visto nas capturas; aguarda dump)",
}
VEHICLE = {"defence_div": 2}
VEHICLE_SOURCE = "; defence_div " + INV + " (aguarda dump)"


def _settings() -> Any:
    return sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _load(conn: sa.Connection, key: str) -> tuple[dict[str, Any], str] | None:
    s = _settings()
    row = conn.execute(sa.select(s.c.value, s.c.source).where(s.c.key == key)).first()
    if row is None:
        return None
    value = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    return dict(value), str(row[1] or "")


def _save(conn: sa.Connection, key: str, value: dict[str, Any], source: str | None = None) -> None:
    s = _settings()
    values: dict[str, Any] = {"value": json.dumps(value)}
    if source is not None:
        values["source"] = source
    conn.execute(s.update().where(s.c.key == key).values(**values))


def upgrade() -> None:
    conn = op.get_bind()
    if (taxas := _load(conn, "taxas")) is not None:
        data = taxas[0] | NEW
        data.setdefault("source", {}).update(SOURCES)
        _save(conn, "taxas", data)
    if (vm := _load(conn, "vehicle_match")) is not None:
        _save(conn, "vehicle_match", vm[0] | VEHICLE, vm[1] + VEHICLE_SOURCE)


def downgrade() -> None:
    conn = op.get_bind()
    if (taxas := _load(conn, "taxas")) is not None:
        data = taxas[0]
        for key in NEW:
            data.pop(key, None)
            data.get("source", {}).pop(key, None)
        _save(conn, "taxas", data)
    if (vm := _load(conn, "vehicle_match")) is not None:
        value = {k: v for k, v in vm[0].items() if k not in VEHICLE}
        _save(conn, "vehicle_match", value, vm[1].replace(VEHICLE_SOURCE, ""))
