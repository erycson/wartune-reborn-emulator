"""Carta do fim da masmorra: um item da lista ``Campaigns.Item`` da campanha (ver docs/drops-masmorras.md).

*(visto)* replay #1221-#1243 e #1725-#1747 (Kurt İni, 1001): 135 (5 cartas), 115 com o item na mochila,
26 com a carta (``index`` escolhido no 5122, ``count`` 1, ``bind``, os ``randomSkill`` já sorteados), 83
``Kazanılan:<nome> x1`` e 134. No inglês (#1121-#1126) o 83 é ``Received: <nome> x1`` e o 134 só vem como
resposta do 5180 (sair). Lista vazia (tutorial, chefe do mundo, guilda) = sem carta: o oficial não
manda 26 no fim do tutorial (replay #525).
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from ..domain.models import Item, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import bag, rewards


def pool(templates: GameTemplates, campaign_id: int) -> list[int]:
    """Itens da carta da campanha. O -700 (EXP) das torres fica de fora: a EXP vem do ``BaseGp``."""
    row = templates.get("Campaigns", campaign_id, key="CampaignId") or {}
    return [t for t in (int(x) for x in str(row.get("Item", "")).split(",") if x) if t > 0]


def card(
    snap: PlayerSnapshot,
    templates: GameTemplates,
    campaign_id: int,
    index: int,
    rng: random.Random | None = None,
    table: Sequence[tuple[int, float]] = (),
) -> tuple[Item, pb.CampaignTakeCardsMsg, str] | None:
    """Sorteia e põe na mochila a carta ``index``. ``None``: campanha sem lista ou mochila cheia.

    ``table``: (TemplateId, peso) do banco (``campaign_cards``, migração 0034); vazia = ``Campaigns.Item`` com
    pesos iguais. Como ``rewards.grant``, só altera o snapshot: quem chama grava o item e manda 115, 26 e 83.
    """
    # ponytail: sem filtro de classe (o mesmo mago tirou 1080013, Job 3, e 1080002, Job 1,2); peso = vezes visto,
    # amostra pequena (docs/drops-masmorras.md); cartas em grupo (9000+) precisam de mais capturas ou vídeos
    rng = rng or random.Random()
    items = [t for t, _ in table] or pool(templates, campaign_id)
    weights = [w for _, w in table] if sum(w for _, w in table) > 0 else None  # tudo 0 no banco: uniforme
    drop = [(rng.choices(items, weights)[0], 1)] if items else []
    if not drop or not rewards.can_grant(snap, templates, drop):
        return None
    new, _ = rewards.grant(snap, templates, drop)
    text = rewards.received(templates, drop)  # (visto) inglesa #1123 "Received: Banshee Plume x1"
    item = new[0]
    slots = int((templates.get("ItemTempInfos", item.template_id) or {}).get("RandomSkillCount") or 0)
    if slots:  # #1241: 3 atributos no 1080013 (RandomSkillCount 3); #1744: 1 no 1080002
        skills = bag.random_skill_pool(templates)
        item.random_skills = [rng.choice(skills) for _ in range(slots)]
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
