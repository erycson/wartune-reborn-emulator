"""EXP descansada e EXP do mundo: ``characters.leave_gp`` e ``game_settings.exp_bonus``

(só turco) o PlayerMsg traz ``leaveGp`` (13 milhões no nível 80) e o texto da EXP das lutas e missões divide o
ganho em base, mundo (10x a base) e descansada (base + mundo, gasta do leaveGp): transfer_kampi #17-#23, peri_uyanis
#82. O inglês (níveis 1 a 19) não tem nenhum dos dois. ``min_grade`` é TODO(inventado).

Revision ID: 0081
Revises: 0080
Create Date: 2026-10-25 01:00:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None

SOURCE = (
    "(só turco: transfer_kampi #23, peri_uyanis #82, meydan_okuma #27) world_percent 1000; "
    "TODO(inventado) min_grade 40 (o inglês até o nível 19 não tem bônus)"
)


def upgrade() -> None:
    with op.batch_alter_table("characters") as batch_op:
        batch_op.add_column(sa.Column("leave_gp", sa.Integer(), server_default="0", nullable=False))
    settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))
    value = json.dumps({"min_grade": 40, "world_percent": 1000})
    op.bulk_insert(settings, [{"key": "exp_bonus", "value": value, "source": SOURCE}])


def downgrade() -> None:
    settings = sa.table("game_settings", sa.column("key"))
    op.execute(settings.delete().where(settings.c.key == "exp_bonus"))
    with op.batch_alter_table("characters") as batch_op:
        batch_op.drop_column("leave_gp")
