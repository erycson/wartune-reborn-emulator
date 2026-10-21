"""eventos de guilda antigos: tipo 0

O ``ConsortiaEventItem`` parte o ``remark`` por "|" e monta pelo tipo; o tipo 1 junta 4 partes, então as frases
prontas gravadas antes saíam com "undefined". O tipo 0 (``default``) mostra a frase inteira.

Revision ID: 0046
Revises: 0045
Create Date: 2026-10-20 23:30:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("update consortia_events set type = 0 where remark not like '%|%'")


def downgrade() -> None:
    op.execute("update consortia_events set type = 1 where type = 0")
