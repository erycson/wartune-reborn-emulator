"""campanhas no banco: o conteúdo das masmorras 1001 e 1002 e da pedreira 6001, e o sorteio das cartas do fim

O conteúdo (nós, névoa, batalhas, diálogos, baús, caixas, drops, portais, coleta) sai da captura do oficial inglês
por ``tools/extract_dungeon.py`` para ``0034_campanhas.json`` (ao lado desta migração), um JSON por campanha na
coluna ``data``. Substitui o ``content/dungeon_1001.json`` (captura turca). Cartas: peso = vezes que o item saiu
nas capturas (inglesa e turca); os itens do ``CampaignInfo.Item`` nunca vistos pesam 1. Detalhes e incertezas em
``docs/drops-masmorras.md``.

Revision ID: 0034
Revises: 0033
Create Date: 2026-10-18 22:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0034_campanhas.json")
SOURCE = "(visto) captura inglesa captures/tutorial_en.json, tools/extract_dungeon.py"
EN, TR = "captura inglesa", "captura turca replay_packets.json"
# (campanha, item, peso, fonte)
CARDS = [
    (1001, 1080012, 2.0, f"{EN} #1122 e #1544 (Banshee Plume, mago)"),
    (1001, 1080013, 1.0, f"{TR} #1241"),
    (1001, 1080002, 1.0, f"{TR} #1744"),
    (1001, 1080003, 1.0, "CampaignInfo.Item, nunca visto"),
    (1001, 2040101, 1.0, "CampaignInfo.Item, nunca visto"),
    # (visto) 2 em 2 e fora do CampaignInfo.Item: o sorteio do oficial não é a lista do template
    (1002, 2040102, 2.0, f"{EN} #2727 e #3181 (Lvl. 2 Luck Stone)"),
    *((1002, t, 1.0, "CampaignInfo.Item, nunca visto")
      for t in (1011104, 1012104, 1013104, 1011102, 1012102, 1013102, 2040101)),
]  # fmt: skip


def upgrade() -> None:
    contents = op.create_table(
        "campaign_contents",
        sa.Column("campaign_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("data", sa.Text(), server_default="", nullable=False),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("campaign_id", name=op.f("pk_campaign_contents")),
    )
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    op.bulk_insert(
        contents,
        [{"campaign_id": int(c), "data": json.dumps(d, ensure_ascii=False), "source": SOURCE} for c, d in seed.items()],
    )
    cards = op.create_table(
        "campaign_cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("campaign_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("template_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=255), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_cards")),
    )
    keys = ("campaign_id", "template_id", "weight", "source")
    op.bulk_insert(cards, [dict(zip(keys, row, strict=True)) for row in CARDS])


def downgrade() -> None:
    op.drop_table("campaign_cards")
    op.drop_table("campaign_contents")
