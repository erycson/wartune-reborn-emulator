"""grupos de amigos pelo cliente inglês

``FridendsListView`` usa o ``groupId`` 3 como cabeçalho da lista negra (e tira o 3 da lista normal), e a lista de
estranhos é quem tem ``groupId`` -1. Por isso: grupos criados pelo jogador começam no 4 (os que existem sobem 1,
com os amigos dentro) e a lista negra passa a ir com o 3, para não aparecer também entre os estranhos.

Revision ID: 0042
Revises: 0041
Create Date: 2026-10-20 13:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

FRIEND, BLACKLIST = 1, 2


def upgrade() -> None:
    # em dois passos (negativo e de volta) para não bater na unique (character_id, group_id) no meio
    op.execute(sa.text("UPDATE friend_groups SET group_id = -(group_id + 1) WHERE group_id >= 3"))
    op.execute(sa.text("UPDATE friend_groups SET group_id = -group_id WHERE group_id < -3"))
    op.execute(sa.text(f"UPDATE relations SET group_id = group_id + 1 WHERE relation = {FRIEND} AND group_id >= 3"))
    op.execute(sa.text(f"UPDATE relations SET group_id = 3 WHERE relation = {BLACKLIST}"))


def downgrade() -> None:
    op.execute(sa.text(f"UPDATE relations SET group_id = -1 WHERE relation = {BLACKLIST}"))
    op.execute(sa.text(f"UPDATE relations SET group_id = group_id - 1 WHERE relation = {FRIEND} AND group_id >= 4"))
    op.execute(sa.text("UPDATE friend_groups SET group_id = -(group_id - 1) WHERE group_id >= 4"))
    op.execute(sa.text("UPDATE friend_groups SET group_id = -group_id WHERE group_id <= -3"))
