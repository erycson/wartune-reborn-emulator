"""Devoção (atividade diária, ``LeedTemp``): o 4152 só com o leed que mudou, o 83 "Your devotion level has increased
to N." quando o total sobe, a missão diária 863 "Increasing Devotion" (tipo 63, Para2 20) do aceite à entrega e a
volta dela no dia seguinte do jogo. Ver docs/eventos.md e docs/missoes.md."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Quest
from wartune_server.game.handlers import events as hev
from wartune_server.game.session import GameSession
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

DEVOTION, VIP_TOKEN = 863, 208015  # QuestGoods da 863: VIP Token x10
START = datetime(2026, 10, 18, 12, tzinfo=UTC)  # 15h no fuso dos testes (+03:00); o dia do jogo vira às 5h


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


def _texts(got: list[Packet]) -> list[str]:
    return [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83]


def _leed(got: list[Packet]) -> pb.LeedUpdatedRspMsg:
    return pb.LeedUpdatedRspMsg.FromString(next(p.body for p in got if p.code == 4152))


def _quest(got: list[Packet], template_id: int) -> pb.QuestInfo:
    msg = pb.QuestUpdatedRspMsg.FromString(next(p.body for p in reversed(got) if p.code == 112))
    return next(q for q in msg.quest if q.templateId == template_id)


async def test_ganho_manda_so_o_leed_e_o_83_quando_o_total_sobe(tmp_path: Path) -> None:
    """Leed 20 "Complete a daily quest" tem PassCount 3 e Num 5: os dois primeiros passos só mandam o 4152; o terceiro
    completa, o total vai de 5 (login) a 10 e vem o 83. Depois do PassCount não muda mais nada."""
    async with logged_in(tmp_path, novice=19000) as g:
        s = _session(g)
        for count in (1, 2):
            await hev.leed_done(s, hev.DAILY_QUEST_LEED)
            got = await g.idle()
            assert [p.code for p in got] == [4152]
            leed = _leed(got)
            assert [(x.templateId, x.currentCount, x.isComplete) for x in leed.leed] == [(20, count, False)]
            assert leed.totalNum == 5
        await hev.leed_done(s, hev.DAILY_QUEST_LEED)
        got = await g.idle()
        assert [p.code for p in got] == [4152, 83] and _leed(got).totalNum == 10
        assert _texts(got) == ["Your devotion level has increased to 10."]  # tutorial_en #522
        await hev.leed_done(s, hev.DAILY_QUEST_LEED)
        assert await g.idle() == []


async def test_entrega_de_diaria_conta_o_leed_20(tmp_path: Path) -> None:
    """183 "Intense Battle (Daily)" (TemplateType 1): a entrega soma 1 no leed 20, depois do 52."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _session(g).snapshot
        assert snap is not None
        snap.character.grades = 40
        snap.quests.append(Quest(g.user_id, 183, START, progress=3))
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=183))
        got = await g.until(4152)
        assert 52 in [p.code for p in got]
        assert [(x.templateId, x.currentCount) for x in _leed(got).leed] == [(20, 1)]


async def test_missao_863_completa_entrega_e_volta_no_dia_seguinte(tmp_path: Path) -> None:
    """Aceite com condition_1 0 mesmo com a devoção do login (tutorial_en #3199); cada ganho grava o total; com 20 a
    5014 entrega (VIP Token x10). No mesmo dia não aceita de novo; no dia seguinte do jogo reabre zerada, e o login do
    dia novo já leva o total (5) para a missão."""
    clock = FakeClock(START)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        snap.character.grades = 10  # NeedMinLevel 10
        await g.server.services.characters.save(snap.character)
        g.client.send(5012, pb.QuestAddedMsg(questId=[DEVOTION]))
        assert _quest(await g.until(112), DEVOTION).condition_1 == 0

        moved: list[Packet] = []
        for leed, total in ((hev.CAMPAIGN_LEED, 10), (hev.PLUNDER_LEED, 15), (hev.BLESS_LEED, 15)):
            await hev.leed_done(s, leed)
            got = await g.idle()
            assert _leed(got).totalNum == total
            moved += got
        assert _quest(moved, DEVOTION).condition_1 == 15 and not _quest(moved, DEVOTION).isComplete
        assert 112 not in [p.code for p in got]  # a 1ª bênção (PassCount 2) não muda o total: sem 112
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=DEVOTION))
        assert _quest(await g.until(112), DEVOTION).condition_1 == 15  # recusa: falta devoção

        await hev.leed_done(s, hev.BLESS_LEED)  # PassCount 2: a segunda bênção completa (+5)
        got = await g.idle()
        assert _texts(got) == ["Your devotion level has increased to 20."]  # tutorial_en #1652
        assert _quest(got, DEVOTION).condition_1 == 20
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=DEVOTION))
        got = await g.until(52)
        assert pb.QuestFinishedRspMsg.FromString(got[-1].body).templateId == DEVOTION
        assert _texts(await g.idle()) == ["Received: VIP Token x10"]  # TemplateType 3: não conta o leed 20
        assert sum(i.count for i in snap.items if i.template_id == VIP_TOKEN) == 10

        g.client.send(5012, pb.QuestAddedMsg(questId=[DEVOTION]))  # mesmo dia do jogo: não reabre
        assert await g.idle() == []

        clock.advance(timedelta(days=1).total_seconds())
        snap.character.grades = 10  # a entrega recalcula o nível pelo EXP (0 aqui)
        g.client.send(5012, pb.QuestAddedMsg(questId=[DEVOTION]))
        reopened = _quest(await g.until(112), DEVOTION)
        assert (reopened.condition_1, reopened.isComplete) == (0, False)
        g.client.send(8322, pb.ClientReqMsg(templateId=4))  # o dia virou: a devoção de ontem zera
        assert pb.LeedUpdatedRspMsg.FromString((await g.until(4152))[-1].body).totalNum == 0

        # primeiro login do dia novo, como o 20001 faz (a sessão HTTP do harness não sobrevive a um dia de relógio):
        # o leed 1 (+5) entra na missão
        touched = hev.touch_login(snap, clock.now(), s.ctx.events)
        assert touched and [q.template_id for q in hev.devotion_quests(s)] == [DEVOTION]
        assert next(q.progress for q in snap.quests if q.template_id == DEVOTION) == 5
