"""Taxas da luta, do relatório 137, do torneio de fadas e da partida do veículo em ``game_settings``

Procurado antes de inventar: decomp inglês (DebugBattleCreater, BattleModel.attackOrders, CampaignResultView,
PetInfoMsg.growthRate, VehicleAccountBottomView), ``language.txt`` do mirror (PetFrame.help01, vehicle.helpTxt01,
maze.MazeFrame.content) e os XMLs do mirror. O cliente só reproduz/mostra: nenhuma conta sai dele, exceto o nível 55
do despertar ("Before Lvl. 55, sylph awakening points increase slowly").

- ``battle_formula`` (0039) ganha as chaves que só estavam no código (despertar, resistência) e as novas: alvo
  sorteado, iniciativa e o despertar lento abaixo do 55.
- ``stage_report``: degraus das notas do 137 e a curva por nível (``game/campaign.py``).
- ``fairy_battle``: vida/ataque do pet e pontos do torneio de fadas (``game/arena.py``).
- ``vehicle_match``: regras da partida do veículo (``game/vehicles.py``).

Revision ID: 0130
Revises: 0124
Create Date: 2026-10-29 23:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0130"
down_revision = "0124"
branch_labels = None
depends_on = None

FORMULA_ADD = {
    "awake_max": 3000,
    "awake_gain": 250,
    "awake_cost": 150,
    "awake_level": 55,
    "awake_gain_low": 125,
    "resist_div": 1000,
    "resist_min": 0.5,
    "resist_max": 1.5,
    "target_random": 1.0,
    "hero_first": 0.0,
}
FORMULA_SOURCE = (
    " | (cliente) HeroRoleInfo.updateAwaken teto 3000, PetFrame.help01 nível 55; (só turco) +250/-150 do despertar; "
    "TODO(inventado) awake_gain_low, resist_*, target_random (alvo único sorteado) e hero_first (herói por último)"
)
ROWS = [
    {
        "key": "stage_report",
        "value": {"wound_steps": [0.7, 0.8, 0.9, 1.0], "hurt_steps": [0.2, 0.4, 0.6, 0.8], "level_scale": 0.02},
        "source": "(visto) notas dos 137 ingleses #1098/#1521/#2705/#3157; (dedução) degraus; "
        "TODO(inventado) level_scale (StandardDamage/StandardHurt +2% por nível acima do MinLevel)",
    },
    {
        "key": "fairy_battle",
        "value": {"hp_growth_div": 9, "attack_div": 20, "win_score": 5, "lose_score": 0},
        "source": "(só turco) peri_turnuvasi: Points +5, vida ~5% e golpe ≈ vida/40; TODO(inventado) os divisores e "
        "a perda 0",
    },
    {
        "key": "vehicle_match",
        "value": {
            "min_players": 2,
            "boxes": 12,
            "box_skills": [2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13],
            "score_damage": 10,
            "score_kill": 100,
            "score_boss": 1000,
            "boss_every_s": 5,
            "runestones": 3,
            "exp_win": 100,
            "exp_loss": 50,
            "exp_per_score": 10,
        },
        "source": "TODO(inventado) sem captura de partida (procurado: vehicle.helpTxt01, VehicleAccountBottomView, "
        "VehicleSkillTempInfo, VehicleObjectTempInfo)",
    },
]


def _formula(conn: sa.Connection) -> tuple[dict[str, float], str]:
    row = conn.execute(sa.text("SELECT value, source FROM game_settings WHERE key = 'battle_formula'")).first()
    if row is None:
        return {}, ""
    value = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    return dict(value), str(row[1] or "")


def _save(conn: sa.Connection, value: dict[str, float], source: str) -> None:
    conn.execute(
        sa.text("UPDATE game_settings SET value = :v, source = :s WHERE key = 'battle_formula'"),
        {"v": json.dumps(value), "s": source},
    )


def upgrade() -> None:
    conn = op.get_bind()
    value, source = _formula(conn)
    if value:
        _save(conn, value | FORMULA_ADD, source + FORMULA_SOURCE)
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.bulk_insert(settings, [{**r, "value": json.dumps(r["value"])} for r in ROWS])


def downgrade() -> None:
    conn = op.get_bind()
    value, source = _formula(conn)
    if value:
        _save(conn, {k: v for k, v in value.items() if k not in FORMULA_ADD}, source.replace(FORMULA_SOURCE, ""))
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key.in_([r["key"] for r in ROWS])))
