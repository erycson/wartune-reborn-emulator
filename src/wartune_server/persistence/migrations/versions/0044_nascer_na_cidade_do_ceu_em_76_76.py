"""nascer na cidade do céu em 76,76

``characters.space_x``/``space_y``: o personagem novo do oficial inglês nasce em 76,76 (tutorial_en #7, o 4595 do
primeiro login, e #2123); o 72,74 de antes era do turco. Quem ainda está no 72,74 nunca andou lá (é o padrão
antigo) e vai para o 76,76.

Revision ID: 0044
Revises: 0043
Create Date: 2026-10-20 20:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def _move(old: tuple[int, int], new: tuple[int, int]) -> None:
    with op.batch_alter_table("characters") as batch:
        batch.alter_column("space_x", existing_type=sa.Integer(), server_default=str(new[0]), existing_nullable=False)
        batch.alter_column("space_y", existing_type=sa.Integer(), server_default=str(new[1]), existing_nullable=False)
    op.execute(
        sa.text("update characters set space_x = :nx, space_y = :ny where space_x = :ox and space_y = :oy").bindparams(
            nx=new[0], ny=new[1], ox=old[0], oy=old[1]
        )
    )


def upgrade() -> None:
    _move((72, 74), (76, 76))


def downgrade() -> None:
    _move((76, 76), (72, 74))
