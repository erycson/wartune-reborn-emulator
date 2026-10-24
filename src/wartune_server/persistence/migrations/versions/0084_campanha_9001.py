"""campanha em grupo 9001 (Claristun, mapa 2011)

Conteúdo extraído das capturas turcas ``peri_uyanis`` e ``exp_kitabi`` (a da sala e da primeira luta)
por ``tools/extract_dungeon.py`` (``0084_campanha_9001.json``, ao lado): nós, névoa e as lutas 201102 e 201104
(só turco). Sem captura inglesa da 9001:

- Nomes dos nós em inglês: (dedução) o do monstro da luta, como nas campanhas inglesas (Grassland Worg, Tauren
  Gladiator): 201102/201103 "Landos Warrior" (PawnTemp 4011), 201104/201105 "Dwarven Clubber" (4012, o turco diz
  "Hayalet Büyücü"), o chefe 201106 "Bakar" (GameHeroTemp 3011, o ``heroTempId`` do nó, como Kronos/Wulfgar). Baús:
  "Silver Treasure Chest" e "Pandora's Box" como na 0069/0075 (mesmo sonType e parâmetros); "VIP Treasure Chest"
  (dedução: "VIP Hazinesi" ao lado de "Gümüş Hazinesi" = Silver Treasure Chest), 2000 Kyanite (o turco diz "2000
  Kristal"). Os 29 em inglês são os da 0069 (prata) e da 0075 (Pandora 115113, o mesmo ``param3``).
- Prêmios: o baú de prata deu Skeleton Key x1 (só turco: peri_uyanis #11, #28); o VIP TODO(inventado) Skeleton Key x2.
- Lutas: 201103 e 201105 copiadas de 201102 e 201104 (dedução: mesmo sonType, nível e ``fightCapaity``); o chefe
  201106 TODO(inventado): Bakar com os números do GameHeroTemp 3011 (31376 de vida, ``monster008B``, ``DefaultSkill``
  40083) e dois Landos Warrior da 201104, como o 115116 da 0075.
- ``army`` do 5038: (só turco: peri_uyanis #89-#90) herói 3011, soldados 4012 e 4011.
- Cartas: ``sceneType`` CAMPAIGN_MAP_SCENE (dedução: o ``ChestFrame`` só trata o SINGLE como solo); o ``Campaigns.Item``
  com pesos iguais, como a 0069.
- Etapas: só o 2011. O ``MapInfos`` tem o 2012 na 9001, mas nenhuma captura entra nele: TODO(inventado) a etapa acaba
  quando o grupo cai (o nó 201107, masterType 62, seria o portal).
- Patrulha (``npc_patrol.points``, ``0084_patrulha_2011.json``): os 4122 das duas capturas e a origem de cada nó.

Revision ID: 0084
Revises: 0083
Create Date: 2026-10-24 10:00:00.000000
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0084"
down_revision = "0083"
branch_labels = None
depends_on = None

SEED = Path(__file__).with_name("0084_campanha_9001.json")
PATROL = Path(__file__).with_name("0084_patrulha_2011.json")
CAMPAIGN = 9001
SOURCE = (
    "(só turco: peri_uyanis, exp_kitabi) tools/extract_dungeon.py; nomes (dedução); 201106 e baú VIP TODO(inventado)"
)
CARD_SOURCE = "(dedução) o Campaigns.Item da 9001, pesos iguais (sem captura do quadro)"
POOL = (
    1991014, 1991016, 1992014, 1992016, 1993014, 1993016, 1041204, 1042204, 1043204, 1060204, 2128102, 2128104,
    2128101, 2128103, 2129001, 2040103, 1041203, 1042203, 1043203, 1060203, 1080203, 1080213,
)  # fmt: skip
settings = sa.table("game_settings", sa.column("key"), sa.column("value"), sa.column("source"))


def _patrol(add: bool) -> None:
    bind = op.get_bind()
    row = bind.execute(sa.select(settings.c.value).where(settings.c.key == "npc_patrol")).first()
    if row is None:
        return
    value = json.loads(row[0])
    extra = json.loads(PATROL.read_text("utf-8"))
    points = value.setdefault("points", {})
    for key in extra:
        points.pop(key, None)
    if add:
        points |= extra
    op.execute(settings.update().where(settings.c.key == "npc_patrol").values(value=json.dumps(value)))


def upgrade() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    contents = sa.table("campaign_contents", sa.column("campaign_id"), sa.column("data"), sa.column("source"))
    op.bulk_insert(
        contents,
        [{"campaign_id": CAMPAIGN, "data": json.dumps(seed[str(CAMPAIGN)], ensure_ascii=False), "source": SOURCE}],
    )
    cards = sa.table(
        "campaign_cards", sa.column("campaign_id"), sa.column("template_id"), sa.column("weight"), sa.column("source")
    )
    op.bulk_insert(
        cards, [{"campaign_id": CAMPAIGN, "template_id": t, "weight": 1.0, "source": CARD_SOURCE} for t in POOL]
    )
    _patrol(True)


def downgrade() -> None:
    _patrol(False)
    for name in ("campaign_contents", "campaign_cards"):
        table = sa.table(name, sa.column("campaign_id"))
        op.execute(table.delete().where(table.c.campaign_id == CAMPAIGN))
