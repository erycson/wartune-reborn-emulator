"""Camp Calorn (1007): allow quest 360 to collect Hexed Armor.

QuestCondictionInfos 360 requires six of item 2100006 from campaign
1007. Neither the captured first stage (0090) nor generated second
stage (0131) defines any battle drops, leaving the quest blocked.

TODO(inventado): two items per regular encounter with guaranteed chance
is a provisional gameplay value, not a captured official drop rate.

Revision ID: 0151
Revises: 0150
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0151"
down_revision = "0150"
branch_labels = None
depends_on = None

CAMPAIGN = 1007
ITEM = 2100006
NODES = ("117103", "117104", "117202", "117203")
REWARD = [ITEM, 2, 1.0]  # TODO(inventado): official quantity/chance unknown


def _apply(add: bool) -> None:
    conn = op.get_bind()
    row = conn.execute(
        sa.text("SELECT data FROM campaign_contents WHERE campaign_id = :campaign"),
        {"campaign": CAMPAIGN},
    ).first()
    if row is None:
        raise RuntimeError("Camp Calorn campaign 1007 is missing")

    data = json.loads(row[0])
    drops = data.setdefault("drops", {})
    for node in NODES:
        if node not in data.get("battles", {}):
            raise RuntimeError(f"Camp Calorn encounter {node} is missing")
        rewards = drops.setdefault(node, [])
        if add:
            if not any(int(reward[0]) == ITEM for reward in rewards):
                rewards.append(REWARD.copy())
        else:
            rewards[:] = [
                reward for reward in rewards
                if not (int(reward[0]) == ITEM and reward[1:] == REWARD[1:])
            ]
            if not rewards:
                drops.pop(node, None)
    if not drops:
        data.pop("drops", None)

    conn.execute(
        sa.text("UPDATE campaign_contents SET data = :data WHERE campaign_id = :campaign"),
        {"campaign": CAMPAIGN, "data": json.dumps(data, ensure_ascii=False)},
    )


def upgrade() -> None:
    _apply(True)


def downgrade() -> None:
    _apply(False)
