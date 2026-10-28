"""guerra de guildas (mapa 4501): conteúdo do mapa e o time da guerra no membro

Conteúdo extraído por ``tools/extract_dungeon.py`` da sessão 20261026-225632-1 #2464-#6250
(``0097_guerra_de_guildas.json``, ao lado): os 30 nós do 127 (#2470), as entradas de cada lado (vermelho 20,100;
azul 373,102, #3868), o exército do sistema (26002, 26003, #2494), a luta da Ward Tower (battleType 20, herói 26003,
#2945) e os 4 buffs do 4440 (#2472).

``consortia_members.gvg_out``/``gvg_role``: (cliente) ``GvgEnterWarFrameI``/``GvgEnterWar*Item`` mandam o 8473 com
op 0 (pôr na lista), 1 (tirar) e 2 (papel, ``param1``); o 4133 devolve ``isTeamPlayer`` e ``role``. Todos começam na
lista: (visto) oficial_20261023-171155-1 #4572 tem ``isTeamPlayer`` em todas as 98 linhas.

Revision ID: 0097
Revises: 0096
Create Date: 2026-10-28 20:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0097"
down_revision = "0096"
branch_labels = None
depends_on = None

CAMPAIGN = 4501
SEED = Path(__file__).with_name("0097_guerra_de_guildas.json")
SOURCE = "(visto) 20261026-225632-1 #2464-#6250 (tools/extract_dungeon.py)"


def upgrade() -> None:
    data = json.loads(SEED.read_text(encoding="utf-8"))[str(CAMPAIGN)]
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(
        contents, [{"campaign_id": CAMPAIGN, "data": json.dumps(data, ensure_ascii=False), "source": SOURCE}]
    )
    with op.batch_alter_table("consortia_members") as batch:
        batch.add_column(sa.Column("gvg_out", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column("gvg_role", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("consortia_members") as batch:
        batch.drop_column("gvg_role")
        batch.drop_column("gvg_out")
    contents = sa.table("campaign_contents", sa.column("campaign_id"))
    op.execute(contents.delete().where(contents.c.campaign_id == CAMPAIGN))
