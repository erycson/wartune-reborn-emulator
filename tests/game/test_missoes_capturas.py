"""Entrega (5014) das missões até o nível 10 entregues nas capturas novas, contra o oficial.

``OFICIAL``: templateId -> (#idx da entrega, códigos S>C da janela oficial, textos do 83). A janela vai do 5014 até o
próximo pedido do cliente, mais o 83 "Received N EXP" logo depois dele (S\\q\\oficial.md). ``GRAU``: o grau do
personagem no 3 que vem antes do 5014 (captura). O estado vem das condições da própria missão (``rules.quest_event``,
``rules.update_state_quests`` para o mapa, ``bag.add`` para a bolsa), não de campos montados à mão.
Ver docs/missoes.md."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Quest
from wartune_server.game import bag, rules
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

# 490: o 109 que abre a janela é o ciclo do castelo (goldTotalCount sobe entre #3083 e #3086), não a entrega.
OFICIAL: dict[int, tuple[int, list[int], list[str]]] = {
    310: (
        8939,
        [4484, 4484, 4484, 4484, 4484, 111, 114, 4131, 83, 149, 3, 112, 109, 3, 52, 83],
        [
            '"Successfully retrieved Bound Balens x60, Daru x50000, Lvl. 4 Luck Stone x1, Lvl. 2 Charisma Gem x1"',
            '"Received 15,000 EXP "',
        ],
    ),
    360: (11761, [115, 3, 112, 109, 3, 52, 83], ['"Received 18,000 EXP "']),
    380: (14667, [3, 112, 109, 3, 52, 83], ['"Received 13,000 EXP "']),
    400: (15035, [115, 3, 112, 109, 83, 109, 152, 4130, 100, 150, 3, 52], ['"Received 20,000 EXP "']),
    410: (17367, [3, 112, 109, 3, 52, 83], ['"Received 24,000 EXP "']),
    420: (17542, [115, 3, 112, 109, 3, 52, 83], ['"Received 24,000 EXP "']),
    430: (19336, [3, 112, 109, 83, 100, 150, 3], ['"Received 42,000 EXP "']),
    440: (18290, [3, 112, 109, 3, 52, 83], ['"Received 42,000 EXP "']),
    450: (20432, [3, 112, 109, 3, 52, 83], ['"Received 42,000 EXP "']),
    460: (20602, [115, 3, 112, 109, 3, 52, 83], ['"Received 42,000 EXP "']),
    470: (1784, [3, 112, 109, 3, 52, 83], ['"Received 48,000 EXP "']),
    480: (3001, [3, 112, 109, 83, 100, 150, 3, 52], ['"Received 48,000 EXP "']),
    490: (3082, [3, 112, 109, 3, 52, 83], ['"Received 48,000 EXP "']),
    500: (5348, [115, 3, 112, 109, 3, 52, 83], ['"Received 54,000 EXP "']),
    510: (7537, [3, 112, 109, 3, 52, 83], ['"Received 54,000 EXP "']),
    520: (7597, [115, 3, 112, 109, 3, 52, 83], ['"Received 54,000 EXP "']),
    550: (8188, [3, 112, 109, 3, 52, 83], ['"Received 60,000 EXP "']),
    560: (12626, [3, 112, 109, 3, 52, 83], ['"Received 64,000 EXP "']),
    570: (12635, [115, 3, 112, 109, 100, 150, 3, 83], ['"Received 64,000 EXP "']),
    580: (18069, [3, 112, 109, 3, 52, 83], ['"Received 25,000 EXP "']),
    590: (8417, [3, 112, 109, 3, 52, 83], ['"Received 72,000 EXP "']),
    600: (14162, [3, 112, 109, 3, 52, 83], ['"Received 72,000 EXP "']),
    610: (13701, [115, 3, 112, 109, 3, 52, 83], ['"Received 72,000 EXP "']),
    223: (
        1759,
        [4484, 4484, 111, 2, 3, 83, 112, 3, 112, 3, 115, 4476, 4426, 4484, 4484, 4484],
        [
            '"Received: Bloodforged Staff x1, Dakan Walker\\\'s Robe x1, Spirit Covenant x1, Lvl. 25 Starter Pack x1, Minor HP Pack x5"'
        ],
    ),
    241: (
        1965,
        [3, 112, 109, 109, 3, 83, 4152, 52, 83],
        ['"Received 12,000 EXP "', '"Your devotion level has increased to 38."'],
    ),
    271: (295, [3, 112, 109, 3, 115, 4476], []),
    312: (8089, [112, 3, 112, 109, 3, 52, 83], ['"Received 10,000 EXP "']),
    313: (14068, [4594], []),
    350: (7778, [3, 112, 109, 3, 52, 83], ['"Received 15,000 EXP "']),
    351: (8099, [112, 3, 112, 109, 3, 52, 83], ['"Received 10,000 EXP "']),
    371: (
        8821,
        [4484, 4484, 4484, 4484, 4484, 111, 52, 83, 3, 112, 83],
        ['"Received: VIP Token x30"', '"Received 28,500 EXP "'],
    ),
    391: (8109, [112, 3, 112, 109, 3, 52, 83], ['"Received 10,000 EXP "']),
    411: (5586, [3, 112, 109, 3, 52, 83], ['"Received 10,000 EXP "']),
    412: (8996, [112, 3, 112, 109, 100, 150, 3, 83], ['"Received 10,000 EXP "']),
    421: (20153, [3, 112, 109, 3, 52, 83], ['"Received 8,000 EXP "']),
    422: (20591, [3, 112, 109, 3, 3, 115, 4476, 4426, 4484, 4484, 4484, 4484, 4484, 4484, 4484, 4484, 4484, 4484], []),
    441: (9536, [112, 3, 112, 109, 3, 52, 83], ['"Received 10,000 EXP "']),
    461: (9546, [112, 3, 112, 109, 3, 52, 83], ['"Received 5,000 EXP "']),
    472: (9557, [112, 3, 112, 109, 3, 52, 83], ['"Received 10,000 EXP "']),
    761: (8530, [3, 112, 109, 3, 52], []),
    764: (11418, [112, 3, 112, 3, 52], []),
    765: (1946, [3, 112, 3, 3, 4152, 52, 83], ['"Received 14,000 EXP "']),
    768: (2274, [4484, 4260, 111, 83, 3, 112, 109, 52], ['"Recycling Succeeded!"']),
    769: (8028, [3, 112, 109, 52], []),
}

# grau do personagem antes do 5014 (3 da captura)
GRAU: dict[int, int] = {
    310: 22,
    360: 23,
    380: 23,
    400: 23,
    410: 24,
    420: 24,
    430: 24,
    440: 24,
    450: 25,
    460: 25,
    470: 25,
    480: 25,
    490: 26,
    500: 26,
    510: 26,
    520: 26,
    550: 28,
    560: 28,
    570: 28,
    580: 31,
    590: 30,
    600: 30,
    610: 30,
    223: 20,
    241: 20,
    271: 25,
    312: 22,
    313: 23,
    350: 22,
    351: 22,
    371: 27,
    391: 22,
    411: 26,
    412: 22,
    421: 31,
    422: 31,
    441: 23,
    461: 23,
    472: 23,
    761: 28,
    764: 23,
    765: 20,
    768: 20,
    769: 22,
}

EXERC = "subida de nível: o servidor reabastece o exército (104/110/152/4130) antes do 150; o oficial não manda. Teste monta exército de novato, estado da captura não reproduzido"

PENDENTES = {
    310: "recompensa com atividades 4484/111/114/4131/149 de outras áreas fora da entrega de missão",
    400: EXERC,
    412: EXERC,
    430: EXERC,
    480: EXERC,
    570: EXERC,
    223: "recompensa com 4484/111 (pacote inicial) e 115 de itens: janela mistura outras áreas",
    241: "bênção do altar (tipo 30): 109 duplicado e 83 de devoção; ordem não conferida, gancho em altar.py",
    271: "árvore (tipo 20): 115 e 4476 fora da entrega; o teste não monta a árvore regada",
    313: "tipo 31 (cena com 1 jogador): janela só com 4594 de evento; gancho em campaign.py, não reproduzido",
    371: "tipo 31 (cena com 2 jogadores): janela com 4484/111 do pacote de VIP; gancho em campaign.py",
    422: "arena (tipo 16): gancho em arena.py; 3 duplicado na janela, causa não confirmada",
    765: "atacar cidade (tipo 8): gancho em outer_city.py, não reproduzido no teste",
    768: "reciclagem (tipo 46): gancho em forge.py; a janela tem 4484/4260/111 de outras ações",
    769: "refino (tipo 47): gancho em forge.py; oficial sem 83 da EXP, causa não confirmada",
}
CASOS = [
    pytest.param(k, marks=pytest.mark.xfail(reason=PENDENTES[k], strict=True)) if k in PENDENTES else k
    for k in sorted(OFICIAL)
]


@pytest.mark.parametrize("template_id", CASOS)
async def test_entrega_ate_nivel_10_bate_com_o_oficial(tmp_path: Path, template_id: int) -> None:
    _, codigos, textos_83 = OFICIAL[template_id]
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        now = datetime.now(UTC)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        snap.character.grades = GRAU[template_id]
        if 150 in codigos:  # subida de nível no oficial: EXP logo abaixo do limite do próximo grau (UpGradeTempInfos)
            snap.character.total_gp = dict(rules.grade_steps(templates))[GRAU[template_id] + 1] - 1
        q = Quest(g.user_id, template_id, now)
        snap.quests.append(q)
        for row in rules.conditions(templates, template_id):
            kind = int(row["CondictionType"])
            para1, para2 = int(row.get("Para1") or 0), int(row.get("Para2") or 0)
            if kind in rules.GOODS_CONDITIONS:
                bag.add(snap, templates, para1, para2, now)
            elif kind == rules.MAP_CONDITION:  # o personagem estava no mapa da condição (checkMapId)
                assert snap.castle is not None
                snap.castle.map_id = para2
                rules.update_state_quests(snap, templates, [q])
            else:
                rules.quest_event(snap, templates, kind, para1, para2 or 1)
        await g.server.services.characters.save(*snap.items)  # o item da bolsa precisa existir no banco (como no jogo)
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=template_id))
        got = await g.idle(0.5)
        # texto do 83 entre aspas, como na tabela (o encodeMsg cru do pacote)
        textos = [f'"{pb.ChatChannelMsg.FromString(p.body).encodeMsg}"' for p in got if p.code == 83]
        assert [p.code for p in got] == codigos
        assert textos == textos_83
