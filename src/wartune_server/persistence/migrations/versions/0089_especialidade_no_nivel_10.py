"""Tropas do jogador no nível 10 ou mais ganham a 1ª especialidade do tipo

(visto) o 5158 que leva a tropa ao nível 10 já devolve o 116 com ``specialTempIds``: Lancer "100"
(oficial_20261023-171155-1 #1678), Hunter "200" (oficial_20261024-191924-1 #1318). O id é o menor
SpecialTempInfo do PawnMasterType = (SonType - 100) * 100 nas tropas 101-109. Antes desta versão o servidor não dava.

Revision ID: 0089
Revises: 0088
Create Date: 2026-10-24 22:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0089"
down_revision = "0088"
branch_labels = None
depends_on = None

pawns = sa.table("pawns", sa.column("id"), sa.column("template_id"), sa.column("specials"))


def upgrade() -> None:
    bind = op.get_bind()
    for pid, template_id, specials in bind.execute(sa.select(pawns.c.id, pawns.c.template_id, pawns.c.specials)):
        son, level = divmod(template_id, 100)
        if 101 <= son <= 109 and level >= 10 and not specials:
            op.execute(pawns.update().where(pawns.c.id == pid).values(specials=str((son - 100) * 100)))


def downgrade() -> None:
    pass  # a especialidade dada não se distingue da ganha depois no 8455/8456
