"""alma do dragão na luta pelo cliente: ``dragon_vocation_bonus`` (0116, inventado) vira vazio

(cliente) ``DragonSoulView.buildSkillPropertyTip``: o bônus da alma é a soma das ``SkillPropertyTempInfos`` das skills
de cada grau (``UpGradeTempInfo.ActiveObject``: 7101-7105, SonType 32) e, depois da transferência, as do Dragon Soul
Heart (SonType 33, 7201-7208). Agora elas entram como passivas na luta (``campaign.passive_skills`` e
``Battle._property``); o % inventado da 0116 somaria por cima.

Revision ID: 0133
Revises: 0132
Create Date: 2026-10-30 01:30:00.000000
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0133"
down_revision = "0132"
branch_labels = None
depends_on = None

KEY = "dragon_vocation_bonus"
OLD = {"PhyAttack": 1, "MagicAttack": 1}
OLD_SOURCE = "TODO(inventado): % por grau de vocação do dragão na luta (DragonSoulView só mostra o nome)"
SOURCE = "(cliente) vazio: o bônus vem das SkillPropertyTempInfos das skills SonType 32/33 (DragonSoulView)"
settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def upgrade() -> None:
    op.execute(settings.update().where(settings.c.key == KEY).values(value=json.dumps({}), source=SOURCE))


def downgrade() -> None:
    op.execute(settings.update().where(settings.c.key == KEY).values(value=json.dumps(OLD), source=OLD_SOURCE))
