"""Entrega de missões (5014) e as regras que ela usa: condição de bolsa (27, 28, 32, 49), recompensas (RewardStrategy,
RewardCrystal, ofertas e bônus diário), aceite (nível, janela, pré-requisito em E, guilda), repetição pelo dia do jogo
(vira às 5h) e passo do novice (5017). Ver docs/missoes.md."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import DATA
from wartune_server.domain.models import BagType, Item, PlayerSnapshot, Quest
from wartune_server.game import bag, rules
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.templates.repository import Row

pytestmark = pytest.mark.skipif(not (DATA / "xml/tempinfos.xml").exists(), reason="precisa de data/overlay")

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
PILE_90 = 2100001  # condição da 90: 8 unidades (replay #1609: a pilha de 10 foi a zero na entrega)
PILE_9 = 2125010  # condição da 9: 10 unidades; a 9 venceu em 2012, então nasce aberta nestes testes
FILLER = 2040101  # item qualquer para encher a mochila (como em test_drops)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


def _row(g: Game, template_id: int) -> Row:
    row = g.server.services.templates.get("QuestTemps", template_id)
    assert row is not None
    return row


async def _put(g: Game, *items: Item) -> None:
    _snap(g).items.extend(items)
    await g.server.services.characters.save(*items)


def _codes(packets: list[Packet]) -> list[int]:
    return [p.code for p in packets]


def _quest(packets: list[Packet], template_id: int) -> pb.QuestInfo:
    msg = pb.QuestUpdatedRspMsg.FromString(next(p.body for p in reversed(packets) if p.code == 112))
    return next(q for q in msg.quest if q.templateId == template_id)


# --- condição de bolsa (27) ------------------------------------------------------------------------


async def test_contagem_de_bolsa_so_conta_a_mochila(tmp_path: Path) -> None:
    """Bolsa (27/28/32/49): conta a mochila, não a bancada (cliente: GoodsManager.countGoods, só BAG)."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _put(
            g,
            Item(g.user_id, PILE_90, pos=0, count=3),
            Item(g.user_id, PILE_90, bag_type=BagType.STORE, pos=0, count=5),
        )
        snap = _snap(g)
        assert rules.goods_count(snap, PILE_90) == 3
        assert rules.goods_to_take(snap, g.server.services.templates, 90) == [(PILE_90, 3)]


async def test_entrega_consome_a_pilha_e_conclui(tmp_path: Path) -> None:
    """90 (CT27 2100001 Para2 8, RewardStrategy 1000): a entrega gasta a pilha inteira (10, visto no replay #1609),
    conclui com o 52 e paga a RewardStrategy."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _put(g, Item(g.user_id, PILE_90, pos=0, count=10))
        snap = _snap(g)
        strategy = snap.character.strategy
        snap.quests.append(Quest(g.user_id, 90, NOW))  # aberta; o pré-requisito (70) só o aceite confere
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=90))
        got = await g.until(52)
        assert _quest(got, 90).isComplete
        assert {112, 115, 52} <= set(_codes(got))
        assert rules.goods_count(snap, PILE_90) == 0
        assert snap.character.strategy == strategy + 1000


async def test_entrega_com_pouco_recusa_e_responde_o_progresso(tmp_path: Path) -> None:
    """Com 7 de 8 da 90 o 5014 não conclui: o 112 volta com o progresso (7) e isComplete falso, sem 52, e nada é gasto."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _put(g, Item(g.user_id, PILE_90, pos=0, count=7))
        snap = _snap(g)
        snap.quests.append(Quest(g.user_id, 90, NOW))
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=90))
        got = await g.until(112)
        assert _quest(got, 90).condition_1 == 7
        assert not _quest(got, 90).isComplete
        assert 52 not in _codes(await g.idle())
        assert rules.goods_count(snap, PILE_90) == 7


async def test_missao_sem_linhas_de_condicao_nao_conclui(tmp_path: Path) -> None:
    """Sem linha em QuestCondictionInfos a missão não conclui: o cliente a acharia pronta sem nada a cumprir."""
    async with logged_in(tmp_path, novice=19000) as g:
        q = Quest(g.user_id, 999999, NOW)
        assert not rules.quest_done(_snap(g), g.server.services.templates, q, NOW)


# --- entrega com a mochila (9: duas recompensas, 10 unidades) --------------------------------------


async def test_entrega_sem_espaco_para_a_recompensa_recusa(tmp_path: Path) -> None:
    """9 (CT27 2125010 Para2 10; QuestGoods 2060013 e 208005 x2): com a mochila cheia, a pilha entregue libera 1
    espaço e a recompensa pede 2. Recusa com o aviso "Çantanız dolu." e não gasta nada."""
    async with logged_in(tmp_path, novice=19000) as g:
        now = datetime.now(UTC)
        cap = bag.capacity(_snap(g).character, now)
        await _put(
            g, Item(g.user_id, PILE_9, pos=0, count=10), *(Item(g.user_id, FILLER, pos=p) for p in range(1, cap))
        )
        snap = _snap(g)
        snap.quests.append(Quest(g.user_id, 9, now))
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=9))
        got = await g.until(112)
        assert not _quest(got, 9).isComplete
        assert 111 in _codes(got)  # o aviso
        assert 52 not in _codes(await g.idle())
        assert rules.goods_count(snap, PILE_9) == 10


async def test_entrega_cabe_quando_a_pilha_libera_espaco(tmp_path: Path) -> None:
    """Mesma 9 com uma casa livre: a pilha entregue libera a sua, e as duas recompensas (2060013 e 208005 x2) cabem."""
    async with logged_in(tmp_path, novice=19000) as g:
        now = datetime.now(UTC)
        cap = bag.capacity(_snap(g).character, now)
        await _put(
            g, Item(g.user_id, PILE_9, pos=0, count=10), *(Item(g.user_id, FILLER, pos=p) for p in range(2, cap))
        )
        snap = _snap(g)
        snap.quests.append(Quest(g.user_id, 9, now))
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=9))
        got = await g.until(52)
        assert _quest(got, 9).isComplete
        assert rules.goods_count(snap, PILE_9) == 0
        rewards = sorted((i.template_id, i.count) for i in snap.items if i.template_id in (2060013, 208005))
        assert rewards == [(208005, 2), (2060013, 1)]


# --- aceite (TaskManage.isAvailableTask) -----------------------------------------------------------


async def test_aceite_confere_nivel_e_janela(tmp_path: Path) -> None:
    """183 pede nível 40 e vale até 2050; a 9 venceu em 2012 e não se aceita."""
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        snap.character.grades = 39
        assert not rules.can_accept(snap, templates, _row(g, 183), NOW, False)
        snap.character.grades = 40
        assert rules.can_accept(snap, templates, _row(g, 183), NOW, False)
        assert not rules.can_accept(snap, templates, _row(g, 183), datetime(2051, 1, 1, tzinfo=UTC), False)
        assert not rules.can_accept(snap, templates, _row(g, 9), NOW, False)


async def test_aceite_pre_requisitos_todos_juntos(tmp_path: Path) -> None:
    """100 pede 80, 81 e 90 (lista com vírgula é E, checkPreTask): uma que falte recusa."""
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        snap.character.grades = 30
        row = _row(g, 100)
        assert not rules.can_accept(snap, templates, row, NOW, False)
        snap.quests.extend(Quest(g.user_id, t, NOW, completed=True, completed_at=NOW) for t in (80, 81))
        assert not rules.can_accept(snap, templates, row, NOW, False)  # falta a 90
        snap.quests.append(Quest(g.user_id, 90, NOW, completed=True, completed_at=NOW))
        assert rules.can_accept(snap, templates, row, NOW, False)


async def test_aceite_de_missao_de_guilda(tmp_path: Path) -> None:
    """765 é IsLeague: sem guilda, o cliente não a mostra para aceitar."""
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        snap.character.grades = 30
        assert not rules.can_accept(snap, templates, _row(g, 765), NOW, False)
        assert rules.can_accept(snap, templates, _row(g, 765), NOW, True)


# --- repetição (dia do jogo vira às 5h) ------------------------------------------------------------


async def test_repetivel_reabre_so_com_o_dia_do_jogo_seguinte(tmp_path: Path) -> None:
    """183 (IsRepeat): concluída às 06:00 UTC (dia do jogo 17). Às 04:59 UTC do dia 18 ainda é o dia 17 (vira às
    5h), então não reabre; às 05:00 reabre, na mesma linha da tabela."""
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        snap.character.grades = 40
        q = Quest(g.user_id, 183, NOW, completed=True, completed_at=datetime(2026, 10, 17, 6, tzinfo=UTC))
        snap.quests.append(q)
        assert rules.accept_quest(snap, templates, 183, datetime(2026, 10, 17, 12, tzinfo=UTC), False) is None
        assert rules.accept_quest(snap, templates, 183, datetime(2026, 10, 18, 4, 59, tzinfo=UTC), False) is None
        reopened = rules.accept_quest(snap, templates, 183, datetime(2026, 10, 18, 5, tzinfo=UTC), False)
        assert reopened is q
        assert not q.completed
        assert [x.template_id for x in snap.quests].count(183) == 1


async def test_nao_repetivel_concluida_nao_reabre(tmp_path: Path) -> None:
    """922 não é repetível (IsRepeat falso): concluída, não volta a aceitar nem em outro dia."""
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        snap.character.grades = 50
        snap.quests.append(Quest(g.user_id, 922, NOW, completed=True, completed_at=NOW))
        assert rules.accept_quest(snap, templates, 922, datetime(2026, 10, 20, 12, tzinfo=UTC), False) is None


# --- recompensas (TaskRewardViewII._rewardList) ----------------------------------------------------


async def test_recompensas_estrategia_cristal_oferta_e_bonus_diario(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        c = snap.character
        strategy = c.strategy
        gp, guild = rules.pay_quest_rewards(snap, templates, _row(g, 90), [])
        assert (gp, guild) == (3000, 0)  # TemplateType 0: sem bônus diário
        assert c.strategy == strategy + 1000  # RewardStrategy (ruh)

        c.grades = 28
        crystals = c.crystals
        gp, _ = rules.pay_quest_rewards(snap, templates, _row(g, 241), [])
        assert gp == 12000 + (28 - 20) * 500  # TemplateType 1: 500 por nível acima do mínimo da missão (20)
        assert c.crystals == crystals + 1000  # RewardCrystal

        player_offer, total = c.consortia_offer, c.consortia_total_offer
        _, guild = rules.pay_quest_rewards(snap, templates, _row(g, 765), [])
        assert guild == 40  # RewardConsortiaOffer: quem chama credita na guilda
        assert (c.consortia_offer, c.consortia_total_offer) == (player_offer + 40, total + 40)  # RewardPlayerOffer


# --- passo do novice (5017) ------------------------------------------------------------------------


def test_passo_do_novice_so_para_a_frente_com_teto() -> None:
    """(cliente) sendSaveProcess manda múltiplos de 100 e sempre para a frente; o servidor aceita um salto de até 2000
    (de 0, até 11000 no primeiro 5017)."""
    assert rules.novice_step_ok(0, 11000)
    assert not rules.novice_step_ok(0, 19000)
    assert rules.novice_step_ok(11000, 11300)
    assert not rules.novice_step_ok(11000, 11250)
    assert not rules.novice_step_ok(11000, 11000)
    assert rules.novice_step_ok(24000, 25500)  # maior salto visto nas capturas
    assert not rules.novice_step_ok(11000, 30000)


async def test_5017_salto_acima_do_teto_nao_avanca(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000) as g:
        assert _snap(g).character.novice_process == 11000
        g.client.send(5017, pb.NoviceReqMsgMsg(noviceProcess=19000))
        await g.idle()
        assert _snap(g).character.novice_process == 11000
        g.client.send(5017, pb.NoviceReqMsgMsg(noviceProcess=11300))
        await g.idle()
        assert _snap(g).character.novice_process == 11300
