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
}

PENDENTES = {
    310: "recompensa com atividades 4484/111/114/4131/149 de outras áreas fora da entrega de missão",
    # subida de nível: o 3 da captura traz só o grau, não o EXP atual; sem ele o servidor não sobe de nível igual ao oficial
    400: "subida de nível (100/150): EXP atual do personagem não está no 3 decodificado, só o grau",
    430: "subida de nível (100/150): EXP atual do personagem não está no 3 decodificado, só o grau",
    480: "subida de nível (100/150): EXP atual do personagem não está no 3 decodificado, só o grau",
    570: "subida de nível (100/150): EXP atual do personagem não está no 3 decodificado, só o grau",
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
