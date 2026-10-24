"""guilda: anúncios de recrutamento por dia (8335, ``speakTimes``)

(visto) oficial_20261023-171155-1 #4944: ``speakTimes`` 5; o cliente inglês diz que os anúncios voltam às 5h. A guilda
grava quantos usou no dia do jogo (``speak_day``/``speak_count``).

Revision ID: 0068
Revises: 0067
Create Date: 2026-10-24 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consortias") as batch:
        batch.add_column(sa.Column("speak_day", sa.String(10), server_default="", nullable=False))
        batch.add_column(sa.Column("speak_count", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("consortias") as batch:
        batch.drop_column("speak_count")
        batch.drop_column("speak_day")
