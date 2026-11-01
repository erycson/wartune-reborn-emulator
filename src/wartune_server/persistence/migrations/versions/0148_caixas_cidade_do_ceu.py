"""Caixas da cidade do céu (``new_year_box``, ``handlers/historia.py``) pela captura 20261101-165308-1.

(visto) "Demon-Shattering Gold Seal" (sonType 10311 no 4811), aberto no dia 01/11 depois do Battleground (o 8994
das 12:26 não teve resposta, o das 12:43 teve); as caixas voltam a cada 30 min (4811 cheio às 13:00 e 13:30);
30 coletas por dia; prêmio sorteado: os pesos são as vezes que cada um saiu nas 30 coletas da captura.
TODO(inventado): o começo exato (12:30, a meia hora antes da 1ª resposta) e o fim do evento (ainda aberto às 13:35,
fim da captura).

Revision ID: 0148
Revises: 0147
Create Date: 2026-11-01 19:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0148"
down_revision = "0147"
branch_labels = None
depends_on = None

KEY = "new_year_box"
VALUE = {
    "begin": "2026-11-01 12:30:00",
    "end": "2026-11-08 00:00:00",
    "waveMinutes": 30,
    "dailyLimit": 30,
    "minLevel": 35,
    "name": "Demon-Shattering Gold Seal",
    "sonType": 10311,
    # [templateId, quantidade, peso]; -100 = ouro
    "prize": [
        [208023, 2, 8],  # Mahra
        [208014, 3, 6],  # Soul Crystal
        [3040001, 2, 5],  # Sylph Sepulcrum
        [21261043, 1, 5],  # Demon-Shattering Gold Seal
        [21261043, 3, 2],
        [208017, 3, 2],  # Mount Training Whip
        [-100, 50000, 2],
    ],
}
SOURCE = (
    "(visto) 20261101-165308-1: nome/sonType do 4811, levas de 30 min, 30 por dia, prêmios e pesos das 30 coletas; "
    "(cliente) nível 35; TODO(inventado) começo 12:30 e fim"
)
OLD = {
    "begin": "2026-12-31 00:00:00",
    "end": "2027-01-08 00:00:00",
    "minLevel": 35,
    "name": "New Year Box",
    "prize": [[-100, 100000], [-600, 1000]],
}
OLD_SOURCE = "(cliente) nível 35, nós MasterType 300 do 10000; TODO(inventado) janela, nome e prêmio"


def _set(value: dict[str, object], source: str) -> None:
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    op.execute(settings.update().where(settings.c.key == KEY).values(value=json.dumps(value), source=source))


def upgrade() -> None:
    _set(VALUE, SOURCE)


def downgrade() -> None:
    _set(OLD, OLD_SOURCE)
