"""Missões com mais de uma condição (condition_1..4) e os tipos de estado e conversa ligados: nível do jogador
(1), segundo dia de login (39) e falar com NPC (85). Ver docs/missoes.md."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import PlayerSnapshot, Quest
from wartune_server.game import rules
from wartune_server.game.builders.player import quest_info
from wartune_server.game.session import GameSession
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

TINA_NODE = 2  # MapNodeInfos 10000/2 (MasterType 61: o cliente manda o 8692); missão 361 pede conversa com ela
TINA_POS = (108, 88)  # PosX/PosY do nó; alcance = HandlerRange 4 + 5
JESI_NODE = 9  # MasterType 1 (anda): o cliente nunca manda o 8692 para ele
ARENA_NODE, ARENA_POS = 3, (36, 128)  # MapNodeInfos 10000/3 (Azrael, Sylph Arena); missão 922 pede conversa com ela


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None
    return session


def _snap(g: Game) -> PlayerSnapshot:
    snap = _session(g).snapshot
    assert snap is not None
    return snap


def _quest(packets: list[Packet], template_id: int) -> pb.QuestInfo:
    msg = pb.QuestUpdatedRspMsg.FromString(next(p.body for p in reversed(packets) if p.code == 112))
    return next(q for q in msg.quest if q.templateId == template_id)


def _codes(packets: list[Packet]) -> list[int]:
    return [p.code for p in packets]


async def test_missao_com_duas_condicoes_so_conclui_com_as_duas(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        templates = g.server.services.templates
        assert max(Counter(r["TemplateId"] for r in templates.rows("QuestCondictionInfos")).values()) <= 4
        now, snap = datetime.now(UTC), _snap(g)
        q = Quest(g.user_id, 764, now)  # linha 1: recrutar 200 do tipo 3; linha 2: tropa do tipo 3 no nível 5
        snap.quests.append(q)
        assert rules.talk_nodes(templates, 764) == []
        assert rules.quest_event(snap, templates, 3, 3, 200) == [q]
        assert not rules.quest_done(snap, templates, q, now)
        assert rules.quest_event(snap, templates, 10, 3, 4) == [q]
        assert not rules.quest_done(snap, templates, q, now)  # a linha 2 ainda não chegou no nível 5
        assert rules.quest_event(snap, templates, 10, 3, 5) == [q]
        assert rules.quest_done(snap, templates, q, now)
        info = quest_info(q)
        assert (info.condition_1, info.condition_2, info.condition_3) == (200, 5, 0)


async def test_nivel_do_jogador_conclui_pelo_nivel_de_agora(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        _snap(g).quests.append(Quest(g.user_id, 11, datetime.now(UTC)))  # tipo 1: Lv.20 (checkPlayerGrades)
        # a 11 venceu em 2011 (EndDate): o cliente não a aceitaria, então nasce aberta
        _snap(g).character.grades = 19
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=11))
        got = await g.until(112)
        assert not _quest(got, 11).isComplete  # nível 19: recusado, só o progresso
        assert 52 not in _codes(await g.idle())
        _snap(g).character.grades = 20
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=11))
        assert _quest(await g.until(52), 11).isComplete


async def test_segundo_dia_de_login_conclui_missao_5(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 10, 1, 12, tzinfo=UTC))
    async with logged_in(tmp_path, novice=11000, clock=clock) as g:
        _snap(g).quests.append(Quest(g.user_id, 5, clock.now()))  # tipo 39: entrar no segundo dia (checkSencondLogin)
        # a 5 venceu em 2000 (EndDate): nasce aberta, como se tivesse sido aceita antes
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=5))
        assert not _quest(await g.until(112), 5).isComplete  # ainda é o dia da aceitação
        clock.advance(24 * 3600)
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=5))
        assert _quest(await g.until(52), 5).isComplete


async def test_falar_com_npc_conta_no_aceite_perto_do_no(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        assert rules.talk_nodes(g.server.services.templates, 922) == [ARENA_NODE]
        _snap(g).character.grades = 50  # 922: nível 50, sem pré-requisito, janela aberta (a 361 já venceu)
        _session(g).space_pos = ARENA_POS
        g.client.send(5012, pb.QuestAddedMsg(questId=[922]))  # o cliente aceita no último passo do diálogo
        assert _quest(await g.until(112), 922).condition_1 == 1


async def test_falar_com_npc_pelo_8692_so_perto_e_nao_com_quem_anda(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _snap(g).quests.append(Quest(g.user_id, 361, datetime.now(UTC)))  # aberta antes de falar
        session = _session(g)
        session.space_pos = (0, 0)
        g.client.send(8692, pb.SimplePropertyMsg(param1=TINA_NODE))
        assert await g.idle() == []  # longe do nó: o 8692 é recusado
        session.space_pos = TINA_POS
        g.client.send(8692, pb.SimplePropertyMsg(param1=TINA_NODE))
        got = await g.until(112)
        assert 4601 in [p.code for p in got]  # o nó abre a janela, como antes
        assert _quest(got, 361).condition_1 == 1
        g.client.send(8692, pb.SimplePropertyMsg(param1=JESI_NODE))  # MasterType 1: recusado
        assert await g.idle() == []
