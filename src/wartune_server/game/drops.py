"""Carta do fim da masmorra: um item da lista ``Campaigns.Item`` da campanha (ver docs/drops-masmorras.md).

*(visto)* captura inglesa #1102-#1126 e #1526-#1547 (Worg Lair, 1001): 135 (5 cartas), 115 com o item na
mochila, 26 com a carta (``index`` escolhido no 5122, ``count`` 1, ``bind``, os ``randomSkill`` já sorteados), 83
``Received: <nome> x1`` e o 134 como resposta do 5180 (sair). Lista vazia (tutorial, chefe do mundo, guilda) =
sem carta: os 26 das capturas inglesas são só das masmorras, nenhum no fim do tutorial.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import datetime

from ..domain.models import Item, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import bag, rewards


def pool(templates: GameTemplates, campaign_id: int) -> list[int]:
    """Itens da carta da campanha. O -700 (EXP) das torres fica de fora: a EXP vem do ``BaseGp``."""
    row = templates.get("Campaigns", campaign_id, key="CampaignId") or {}
    return [t for t in (int(x) for x in str(row.get("Item", "")).split(",") if x) if t > 0]


def draw(
    templates: GameTemplates, campaign_id: int, rng: random.Random, table: Sequence[tuple[int, float]] = ()
) -> int:
    """Sorteia o template da carta sem tocar na mochila (0 = campanha sem lista)."""
    items = [t for t, _ in table] or pool(templates, campaign_id)
    weights = [w for _, w in table] if sum(w for _, w in table) > 0 else None  # tudo 0 no banco: uniforme
    return rng.choices(items, weights)[0] if items else 0


def card(
    snap: PlayerSnapshot,
    templates: GameTemplates,
    campaign_id: int,
    index: int,
    rng: random.Random | None = None,
    table: Sequence[tuple[int, float]] = (),
    *,
    now: datetime,
) -> tuple[Item, pb.CampaignTakeCardsMsg, str] | None:
    """Sorteia e põe na mochila a carta ``index``. ``None``: campanha sem lista ou mochila cheia.

    ``table``: (TemplateId, peso) do banco (``campaign_cards``, migração 0034); vazia = ``Campaigns.Item`` com
    pesos iguais. Como ``rewards.grant``, só altera o snapshot: quem chama grava o item e manda 115, 26 e 83.
    """
    # ponytail: sem filtro de classe (só turco: replay #1241/#1744, o mesmo mago tirou 1080013, Job 3, e 1080002,
    # Job 1,2; o inglês só deu 1080012, Job 3); peso = vezes visto na captura inglesa,
    # amostra pequena (docs/drops-masmorras.md); cartas em grupo (9000+) precisam de mais capturas ou vídeos
    rng = rng or random.Random()
    tid = draw(templates, campaign_id, rng, table)
    drop = [(tid, 1)] if tid else []
    if not drop or not rewards.can_grant(snap, templates, drop, now):
        return None
    new, _ = rewards.grant(snap, templates, drop)
    text = rewards.received(templates, drop)  # (visto) inglesa #1123 "Received: Banshee Plume x1"
    item = new[0]
    # inglês #1122/#1544: 1 atributo no 1080012 (RandomSkillCount 1); 3 no 1080013 só turco (replay #1241)
    item.random_skills = bag.roll_random_skills(templates, item.template_id, rng)
    s1, s2, s3, s4, s5 = item.random_skills
    msg = pb.CampaignTakeCardsMsg(
        playerId=snap.character.id or 0,
        name=snap.character.nickname or "",
        pay=False,
        index=index,
        templateId=item.template_id,
        count=item.count,
        bind=True,
        randomSkill_1=s1,
        randomSkill_2=s2,
        randomSkill_3=s3,
        randomSkill_4=s4,
        randomSkill_5=s5,
    )
    return item, msg, text
