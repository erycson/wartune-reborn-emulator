"""coliseu: desceu no ranking é negativo

``challenge_logs.forward``: o ``ColosseumEventItem`` lê > 0 como "ranking rose to" e < 0 como "ranking dropped to";
o 2 de antes mostrava "subiu" para quem caiu. Passa os 2 gravados para -1.

Revision ID: 0045
Revises: 0044
Create Date: 2026-10-20 23:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("update challenge_logs set forward = -1 where forward = 2")


def downgrade() -> None:
    op.execute("update challenge_logs set forward = 2 where forward = -1")
