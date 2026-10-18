"""Entrega de missões (5014) e as regras que ela usa: condição de bolsa (27, 28, 32, 49), recompensas (RewardStrategy,
RewardCrystal, ofertas e bônus diário), aceite (nível, janela, pré-requisito em E, guilda), repetição pelo dia do jogo
(vira às 5h) e passo do novice (5017). Ver docs/missoes.md."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_missoes_social import _create_guild, _guild
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


async def test_recompensa_completa_a_pilha_que_ja_existe(tmp_path: Path) -> None:
    """A 9 dá 208005 x2 (bag.add, como a mochila empilha): com uma pilha dele (1) já na mochila, fica uma pilha só de 3."""
    async with logged_in(tmp_path, novice=19000) as g:
        now = datetime.now(UTC)
        await _put(g, Item(g.user_id, PILE_9, pos=0, count=10), Item(g.user_id, 208005, pos=1, count=1))
        snap = _snap(g)
        snap.quests.append(Quest(g.user_id, 9, now))
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=9))
        assert _quest(await g.until(52), 9).isComplete
        assert [(i.pos, i.count) for i in snap.items if i.template_id == 208005] == [(1, 3)]


async def test_entrega_cabe_quando_a_recompensa_entra_numa_pilha(tmp_path: Path) -> None:
    """Mochila sem casa livre: a 9 libera a pilha de 10 (uma casa). O 2060013 x1 ocupa essa casa e o 208005 x2 completa a
    pilha que já está na mochila. Contar só casas livres recusava a entrega."""
    async with logged_in(tmp_path, novice=19000) as g:
        now = datetime.now(UTC)
        cap = bag.capacity(_snap(g).character, now)
        await _put(
            g,
            Item(g.user_id, PILE_9, pos=0, count=10),
            Item(g.user_id, 208005, pos=1, count=1),
            *(Item(g.user_id, FILLER, pos=p) for p in range(2, cap)),
        )
        snap = _snap(g)
        snap.quests.append(Quest(g.user_id, 9, now))
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=9))
        assert _quest(await g.until(52), 9).isComplete
        assert [i.count for i in snap.items if i.template_id == 208005] == [3]
        assert [i.pos for i in snap.items if i.template_id == 2060013] == [0]


async def test_entrega_gasta_so_a_quantidade_pedida_fora_do_item_de_missao(tmp_path: Path) -> None:
    """(visto) 2100001 (SonType 210, item de missão) sai inteiro na 90. Item comum (2125010, SonType 201, da 9): só o
    pedido, 10 de 12. Sem fonte para os demais itens comprados, então esta regra é dedução."""
    async with logged_in(tmp_path, novice=19000) as g:
        templates = g.server.services.templates
        await _put(g, Item(g.user_id, PILE_9, pos=0, count=12))
        assert rules.goods_to_take(_snap(g), templates, 9) == [(PILE_9, 10)]
        await _put(g, Item(g.user_id, PILE_90, pos=1, count=12))
        assert rules.goods_to_take(_snap(g), templates, 90) == [(PILE_90, 12)]


async def test_entrega_de_item_comum_deixa_o_resto_na_bolsa(tmp_path: Path) -> None:
    """Item comum (2125010, SonType 201, da 9): a entrega gasta só as 10 pedidas e deixa 2 na bolsa. A captura só mostra o
    item de missão (2100001) saindo inteiro, então esta parte é dedução."""
    async with logged_in(tmp_path, novice=19000) as g:
        now = datetime.now(UTC)
        await _put(g, Item(g.user_id, PILE_9, pos=0, count=12))
        snap = _snap(g)
        snap.quests.append(Quest(g.user_id, 9, now))
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=9))
        assert _quest(await g.until(52), 9).isComplete
        assert rules.goods_count(snap, PILE_9) == 2


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
        assert reopened is not None and reopened[0] is q
        assert not q.completed
        assert [x.template_id for x in snap.quests].count(183) == 1


async def test_nao_repetivel_concluida_nao_reabre(tmp_path: Path) -> None:
    """922 não é repetível (IsRepeat falso): concluída, não volta a aceitar nem em outro dia."""
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        snap.character.grades = 50
        snap.quests.append(Quest(g.user_id, 922, NOW, completed=True, completed_at=NOW))
        assert rules.accept_quest(snap, templates, 922, datetime(2026, 10, 20, 12, tzinfo=UTC), False) is None


async def test_bitmap_mantem_o_bit_da_repetivel_reaberta(tmp_path: Path) -> None:
    """(citado em rules.ever_completed, login.json #89): a repetível reaberta mantém o bit do states ligado, e a
    pré-missão do cliente (IsTaskFinish) continua a ler esse bit. Missão nunca concluída segue com o bit apagado."""
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        snap.quests.append(Quest(g.user_id, 183, NOW, completed=False, completed_at=NOW))
        bits = rules.quest_bitmap(snap)
        assert bits[182 // 8] & (1 << (182 % 8))  # id 183 -> bit 182
        assert not bits[183 // 8] & (1 << (183 % 8))  # id 184 nunca concluída


async def test_aceite_devolve_as_outras_missoes_que_ele_mudou(tmp_path: Path) -> None:
    """A 10 (tutorial, condição tipo 23) cumpre a condição quando o novice avança. Aceitar outra missão atualiza a 10 e
    a devolve junto: quem chama grava e manda o 112 das duas (antes a 10 ficava só na memória)."""
    async with logged_in(tmp_path, novice=0) as g:
        templates, snap = g.server.services.templates, _snap(g)
        snap.character.grades = 40
        q10 = Quest(g.user_id, 10, NOW)
        snap.quests.append(q10)
        snap.character.novice_process = 19000
        accepted = rules.accept_quest(snap, templates, 183, NOW, False)
        assert accepted is not None
        assert any(x is q10 for x in accepted[1])


async def test_5012_manda_112_com_as_outras_missoes_que_mudaram(tmp_path: Path) -> None:
    """Handler: aceitar a 183 muda a 10 (tutorial). O 112 do 5012 traz as duas, então o cliente vê a 10 mudada."""
    async with logged_in(tmp_path, novice=0) as g:
        snap = _snap(g)
        snap.character.grades = 40
        snap.quests.append(Quest(g.user_id, 10, NOW))
        snap.character.novice_process = 19000
        g.client.send(5012, pb.QuestAddedMsg(questId=[183]))
        got = await g.until(112)
        assert _quest(got, 183).templateId == 183
        assert _quest(got, 10).templateId == 10


# --- recompensas (TaskRewardViewII._rewardList) ----------------------------------------------------


async def test_recompensas_estrategia_cristal_oferta_e_bonus_diario(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        templates, snap = g.server.services.templates, _snap(g)
        c = snap.character
        strategy = c.strategy
        gp, guild = rules.pay_quest_rewards(snap, templates, _row(g, 90))
        assert (gp, guild) == (3000, 0)  # TemplateType 0: sem bônus diário
        assert c.strategy == strategy + 1000  # RewardStrategy (ruh)

        c.grades = 28
        crystals = c.crystals
        gp, _ = rules.pay_quest_rewards(snap, templates, _row(g, 241))
        assert gp == 12000 + (28 - 20) * 500  # TemplateType 1: 500 por nível acima do mínimo da missão (20)
        assert c.crystals == crystals + 1000  # RewardCrystal

        player_offer, total = c.consortia_offer, c.consortia_total_offer
        _, guild = rules.pay_quest_rewards(snap, templates, _row(g, 765))
        assert guild == 40  # RewardConsortiaOffer: quem chama credita na guilda
        assert (c.consortia_offer, c.consortia_total_offer) == (player_offer + 40, total + 40)  # RewardPlayerOffer


async def test_missao_de_guilda_entrega_a_bolsa_e_credita_as_ofertas(tmp_path: Path) -> None:
    """847 (IsLeague, nível 31-35, CT49 208012 x8; RewardConsortiaOffer 20 e RewardPlayerOffer 20): com guilda e a bolsa
    com 208012, aceita já com 8; a entrega consome as unidades e credita a oferta do jogador e a da guilda."""
    async with logged_in(tmp_path, novice=19000) as g:
        await _create_guild(g)  # IsLeague: o cliente só mostra a 847 para quem tem guilda
        snap = _snap(g)
        snap.character.grades = 31
        await _put(g, Item(g.user_id, 208012, pos=0, count=8))
        g.client.send(5012, pb.QuestAddedMsg(questId=[847]))
        assert _quest(await g.until(112), 847).condition_1 == 8  # a bolsa conta já no aceite
        player_offer, guild_offer = snap.character.consortia_offer, _guild(g).offer
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=847))
        assert _quest(await g.until(52), 847).isComplete
        assert rules.goods_count(snap, 208012) == 0
        assert snap.character.consortia_offer == player_offer + 20  # RewardPlayerOffer
        assert _guild(g).offer == guild_offer + 20  # RewardConsortiaOffer, na guilda


# --- passo do novice (5017) ------------------------------------------------------------------------


def test_passo_do_novice_so_para_a_frente_com_teto() -> None:
    """(cliente) sendSaveProcess manda só múltiplo de 100 positivo; a ordem crescente vem do guia (newbie.xml).
    O servidor aceita um passo de até 3500, o maior do guia, e de 0 até 11000 no primeiro 5017."""
    assert rules.novice_step_ok(0, 11000)
    assert not rules.novice_step_ok(0, 19000)
    assert rules.novice_step_ok(11000, 11300)
    assert not rules.novice_step_ok(11000, 11250)
    assert not rules.novice_step_ok(11000, 11000)
    assert rules.novice_step_ok(24000, 25500)
    assert rules.novice_step_ok(28500, 32000)  # maior salto do newbie.xml (saveId)
    assert not rules.novice_step_ok(28500, 32100)
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
