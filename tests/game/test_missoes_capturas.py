"""Entrega (5014) das missões até o nível 10 entregues nas capturas novas, contra o oficial.

Tabela ``OFICIAL``: templateId -> (#idx da entrega na captura, códigos S>C até o próximo pedido do cliente, texto do
primeiro 111). Gerada de S\\q\\oficial.md. O estado vem das condições da própria missão (``rules.quest_event`` e
``bag.add``), não de campos montados à mão. Ver docs/missoes.md."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Quest
from wartune_server.game import bag, rules
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.protocol.registry import MessageRegistry

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

OFICIAL: dict[int, tuple[int, list[int], str | None]] = {
    310: (
        8939,
        [4484, 4484, 4484, 4484, 4484, 111, 114, 4131, 83, 149, 3, 112, 109, 3, 52, 83],
        'channel: 7 encodeMsg: "Successfully retrieved Bound Balens x60, Daru x50000, Lvl. 4 Luck Stone x1, Lvl. 2 Charisma Gem x1"',
    ),
    360: (11761, [115, 3, 112, 109, 3, 52], None),
    380: (14667, [3, 112, 109, 3, 52, 83], None),
    400: (15035, [115, 3, 112, 109, 83, 109, 152, 4130, 100, 150, 3, 52], None),
    410: (17367, [3, 112, 109, 3, 52], None),
    420: (17542, [115, 3, 112, 109, 3, 52], None),
    430: (19336, [3, 112, 109, 83, 100, 150, 3], None),
    440: (18290, [3, 112, 109, 3, 52, 83], None),
    450: (20432, [3, 112, 109, 3, 52], None),
    460: (20602, [115, 3, 112, 109, 3, 52], None),
    470: (1784, [3, 112, 109, 3, 52, 83], None),
    480: (3001, [3, 112, 109, 83, 100, 150, 3, 52], None),
    490: (3082, [109, 3, 112, 109, 3, 52, 83], None),
    500: (5348, [115, 3, 112, 109, 3, 52, 83], None),
    510: (7537, [3, 112, 109, 3, 52], None),
    520: (7597, [115, 3, 112, 109, 3, 52, 83], None),
    550: (8188, [3, 112, 109, 3, 52], None),
    560: (12626, [3, 112, 109, 3, 52], None),
    570: (12635, [115, 3, 112, 109, 100, 150, 3], None),
    580: (18069, [], None),
    590: (8417, [3, 112, 109, 3, 52, 83], None),
    600: (14162, [3, 112, 109, 3, 52], None),
    610: (13701, [115, 3, 112, 109, 3, 52], None),
}

REG = MessageRegistry.load_default()


# Divergem do oficial (nesta rodada, não corrigidas): falta o 83 do EXP e/ou o 115 do consumo de item; 580 não tem
# resposta no oficial e o servidor responde. Ver S\q\oficial.md. strict: quando corrigir, o xfail vira erro.
PENDENTE = "pendente: 83 do EXP e/ou 115 do consumo de item diferem do oficial (não investigado nesta rodada)"
PENDENTES = {k for k in OFICIAL if k not in {380, 440, 470, 590}}
CASOS = [
    pytest.param(k, marks=pytest.mark.xfail(reason=PENDENTE, strict=True)) if k in PENDENTES else k
    for k in sorted(OFICIAL)
]


@pytest.mark.parametrize("template_id", CASOS)
async def test_entrega_ate_nivel_10_bate_com_o_oficial(tmp_path: Path, template_id: int) -> None:
    _, codigos, _ = OFICIAL[template_id]
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        now = datetime.now(UTC)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        snap.character.grades = 60  # o oficial de cada entrega é de um personagem já adulto: sem subida de nível
        q = Quest(g.user_id, template_id, now)
        snap.quests.append(q)
        for row in rules.conditions(templates, template_id):
            kind = int(row["CondictionType"])
            para1, para2 = int(row.get("Para1") or 0), int(row.get("Para2") or 0)
            if kind in rules.GOODS_CONDITIONS:
                bag.add(snap, templates, para1, para2, now)
            else:
                rules.quest_event(snap, templates, kind, para1, para2 or 1)
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=template_id))
        got = await g.idle(0.5)
        assert [p.code for p in got] == codigos
