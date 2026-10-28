"""masmorras em grupo 9000-9002 com captura inglesa: nós, névoa, lutas, chefes, baús e drops

Extraídas por ``tools/extract_dungeon.py`` (``0100_masmorras_grupo.json``, ao lado), as três com as cartas do fim:

- (visto) oficial_20261024-191924-1: 9000 Nether Forest (2091/2092), duas corridas (#4525 sem prêmio, #6870 com).
- (visto) oficial_20261025-232017-1: 9001 Claristun (2011/2012), troca a 0084 (só turco, só o 2011).
- (visto) oficial_20261027-152321-1: 9002 The Graveyard (2031/2032/2033).

Da 0084 (turca) a 9001 guarda só as caixas que a inglesa não abriu (o baú VIP 201110 com o custo em Kyanite).
Em grupo o oficial divide o mapa e as lutas da sala; aqui cada membro anda no seu (ver ``_group_enter``).

Revision ID: 0100
Revises: 0099
Create Date: 2026-10-29 00:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0100"
down_revision = "0099"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0100_masmorras_grupo.json")
OLD = Path(__file__).with_name("0084_campanha_9001.json")
SOURCE = "(visto) oficial_20261024-191924/20261025-232017/20261027-152321, tools/extract_dungeon.py"
OLD_SOURCE = "(visto) captura turca exp_kitabi, tools/extract_dungeon.py (0084)"
VIP = 2204  # sonType do VIP Bonus Chest (param1 -700, param2 = Kyanite)
contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))


def seed() -> dict[str, dict]:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    old = json.loads(OLD.read_text(encoding="utf-8"))["9001"]
    for k, v in old.get("confirms", {}).items():
        data["9001"].setdefault("confirms", {}).setdefault(k, v)
    vip = old["confirms"]["201110"]  # o baú VIP da 0084: cobra Kyanite (o param2 do nó) e dá as chaves
    for content in data.values():
        for m in content["maps"].values():
            for n in m["nodes"]:
                if n["sonType"] == VIP:
                    box = content.setdefault("confirms", {}).setdefault(str(n["campDataId"]), {})
                    box.setdefault("confirm", {**vip["confirm"], "body": n["param3"], "nodeId": n["campDataId"]})
                    box.setdefault("cost", [vip["cost"][0], int(n["param2"])])
                    box.setdefault("drops", vip["drops"])  # TODO(inventado) 209109/203108 não abertos: as da 201110
                    box.setdefault("notify", False)
    return data


def upgrade() -> None:
    data = seed()
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in data])))
    op.bulk_insert(
        contents,
        [{"campaign_id": int(k), "data": json.dumps(v, ensure_ascii=False), "source": SOURCE} for k, v in data.items()],
    )


def downgrade() -> None:
    op.execute(contents.delete().where(contents.c.campaign_id.in_([int(k) for k in seed()])))
    old = json.loads(OLD.read_text(encoding="utf-8"))["9001"]
    op.bulk_insert(contents, [{"campaign_id": 9001, "data": json.dumps(old, ensure_ascii=False), "source": OLD_SOURCE}])
