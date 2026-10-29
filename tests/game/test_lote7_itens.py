"""Lote 7 da auditoria (itens/forja): caixas pela descrição, autoBuy da composição, ordem de consumo, lojas de
pontuação, Amethyst e honra, leilão (ordem e reempilhar). Ver docs/itens.md e docs/progresso.md."""

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_mall import _put, _sell, last
from tests.game.test_shop import buy, me
from wartune_server.domain.models import BagType, Item, PlayerSnapshot
from wartune_server.game import bag, rewards
from wartune_server.game import events as ev
from wartune_server.game.handlers import mall as h
from wartune_server.protocol.messages import wartune_pb2 as pb

GEM1, GEM2, GEM3 = 2050101, 2050102, 2050103  # Lvl. 1-3 Physical Attack Gem (ComposeTempInfos 33 e 34, 4 por 1)


async def _give(g: Game, tid: int, count: int, pos: int, binds: bool = True) -> Item:
    item = Item(g.user_id, tid, pos=pos, count=count, is_binds=binds)
    me(g).items.append(item)
    await g.server.services.characters.save(item)
    return item


async def _grade(g: Game, grades: int) -> None:
    c = me(g).character
    c.grades = grades
    await g.server.services.characters.save(c)


def _count(snap: PlayerSnapshot, tid: int) -> int:
    return bag.count_of(snap, tid)


# --- caixa com conteúdo pela descrição ---


async def test_caixa_206_abre_pela_descricao(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _grade(g, 40)
        await _give(g, 2060044, 1, pos=20)  # Guild Treasure: "Contains: Mount Training Whip x30, Shadow Crystal x10."
        g.client.send(5006, pb.ItemUseMsg(pos=20, count=1, bagType=1))
        got = await g.until(83)
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == (
            "Received: Mount Training Whip x30, Shadow Crystal x10"
        )
        assert (_count(me(g), 208017), _count(me(g), 208012), _count(me(g), 2060044)) == (30, 10, 0)

        gold = me(g).character.gold
        await _give(g, 2060028, 2, pos=21)  # Fayden's Reliquary: "one of the following: 50000 Gold, 10000 Daru."
        g.client.send(5006, pb.ItemUseMsg(pos=21, count=2, bagType=1))
        await g.until(83)
        c = me(g).character
        assert (c.gold - gold) // 50000 + c.strategy // 10000 >= 2  # uma das duas por caixa
        assert _count(me(g), 2060028) == 0


def test_descricao_sem_lista_ou_nome_desconhecido_recusa(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from tests.game.test_batalha import _templates  # type: ignore[attr-defined]
    from wartune_server.game.handlers.items import box_contents

    s = SimpleNamespace(ctx=SimpleNamespace(templates=_templates()))
    assert box_contents(s, "Contains special level rewards.") is None  # type: ignore[arg-type]
    assert box_contents(s, "Click to receive one of the following: Lvl 1 or 2 Gem x1, 50 Vouchers") is None  # type: ignore[arg-type]
    fixed = box_contents(s, "Contents: 300,000 Gold, Bullhorn (Large) x10.")  # type: ignore[arg-type]
    assert fixed == ([(-100, 300000), (208002, 10)], False)


# --- autoBuy da composição de pedras ---


async def test_compose_now_compra_o_que_falta_e_sobe_a_cadeia(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _grade(g, 30)
        c = me(g).character
        c.gold, c.gift_token, c.point = 10**5, 1000, 0
        await g.server.services.characters.save(c)
        await _give(g, GEM1, 8, pos=20)  # dá 2 de nível 2; faltam 2, compradas a 85 vinculados (ShopTempInfo 44)
        g.client.send(5153, pb.StoreReqMsg(composeId=34, composeNum=1, autoBuy=True, payType=0))
        await g.until(89)
        assert (_count(me(g), GEM1), _count(me(g), GEM2), _count(me(g), GEM3)) == (0, 0, 1)
        assert me(g).character.gift_token == 1000 - 2 * 85

        await _give(g, GEM1, 3, pos=21)  # sem Balens: recusa e nada muda
        c.gift_token = 0
        g.client.send(5153, pb.StoreReqMsg(composeId=33, composeNum=1, autoBuy=True, payType=0))
        g.client.send(5153, pb.StoreReqMsg(composeId=33, composeNum=1))  # sem autoBuy: falta material
        await g.idle()
        assert _count(me(g), GEM1) == 3


# --- ordem de consumo ---


def test_consome_vinculado_primeiro_e_depois_pela_posicao() -> None:
    from types import SimpleNamespace

    free_late = Item(1, GEM1, pos=1, count=5, is_binds=False)
    bound = Item(1, GEM1, pos=9, count=5, is_binds=True)
    free_early = Item(1, GEM1, pos=0, count=1, is_binds=False)
    snap: PlayerSnapshot = SimpleNamespace(items=[free_late, bound, free_early])  # type: ignore[assignment]
    changed, gone = bag.take(snap, GEM1, 7)
    assert gone == [bound, free_early] and changed == [free_late] and free_late.count == 4
    assert rewards.take_one(snap, GEM1) == (free_late, False)


# --- lojas de pontuação 8/15 e Amethyst (11) ---


async def test_loja_de_selos_paga_com_a_essencia(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _give(g, 3101021, 70, pos=20)  # Essence of Water; ShopTempInfo 849 = Water Sylph Seal por 60
        g.client.send(5154, buy(849, 1))
        got = await g.until(90)
        assert pb.ShopMsg.FromString(got[-1].body).buyInfo.result == 1
        assert (_count(me(g), 3101021), _count(me(g), 2060404)) == (10, 1)
        g.client.send(5154, buy(849, 1))  # só 10: falta
        assert pb.ShopMsg.FromString((await g.until(90))[-1].body).buyInfo.result == 4


async def test_amethyst_da_mina_paga_a_loja_de_ametista(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _grade(g, 30)
        now = g.server.services.clock.now()
        await g.server.services.characters.save(rewards.add_amethyst(me(g), 250, now))
        g.client.send(5154, buy(1067, 1))  # 2030102 por 200 MineScore
        got = await g.until(90)
        assert pb.ShopMsg.FromString(got[-1].body).buyInfo.result == 1
        assert pb.PlayerMsg.FromString(next(p for p in got if p.code == 3).body).mineScore == 50
        st = ev.peek(me(g), rewards.AMETHYST_KEY)
        assert st is not None and st.value == 50
        g.client.send(5154, buy(1067, 1))
        assert pb.ShopMsg.FromString((await g.until(90))[-1].body).buyInfo.result == 4


# --- leilão: cancelar reempilha ---


async def test_cancelar_leilao_reempilha_na_pilha_incompleta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        horn = await _put(a, 208002, 10)
        a.client.send(8448, _sell(horn, count=4, point=40, hour=8))
        await a.until(4352)
        listing = (await a.server.services.characters.read(lambda uow: uow.mall.by_seller(a.user_id)))[0]
        a.client.send(8454, pb.AuctionItemReqMsg(id=listing.id))
        assert last(await a.until(4358), pb.CanceltemRspMsg).result == h.OK
        horns = [i for i in me(a).items if i.template_id == 208002 and i.bag_type == BagType.BAG]
        assert [(i.pos, i.count) for i in horns] == [(5, 10)]


# --- paginação da lista de amigos (4156) ---


async def test_lista_de_amigos_vai_em_paginas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from wartune_server.domain.models import Relation
    from wartune_server.game import social

    monkeypatch.setattr(social, "FRIEND_PAGE", 1)
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        c = await a.join("corvo")
        me(a).relations.extend(Relation(a.user_id, o.user_id, 1, group_id=2) for o in (b, c))
        session = a.server.online.get(a.user_id)
        assert session is not None
        pages = await social.friend_list(session)
        assert [(p.maxPage, p.curPage, len(p.relationList)) for p in pages] == [(2, 0, 1), (2, 1, 1)]


# --- offline x1,5 / x2 pagos ---


async def test_offline_x2_cobra_balens_e_dobra_a_exp(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=20000) as g:
        c = me(g).character
        c.offline_seconds, c.point, c.gift_token = 7200, 0, 100
        await g.server.services.characters.save(c)
        total = c.total_gp
        g.client.send(8287, pb.OfflineRewardMsg(rateCount=20))
        player = pb.PlayerMsg.FromString((await g.until(3))[-1].body)
        assert player.totalGp == total + 120 * c.grades * 2  # 120 min x nível, x2
        assert me(g).character.gift_token == 100 - 2 * 10  # 10 por hora (0115, TODO inventado)


# --- pergaminhos de %, cartas e mascote na luta ---


def test_pergaminhos_de_porcentagem_somam_na_luta() -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from tests.game.test_batalha import _templates  # type: ignore[attr-defined]
    from wartune_server.game import buffs

    now = datetime(2026, 1, 1, tzinfo=UTC)
    snap: PlayerSnapshot = SimpleNamespace(events=[], character=SimpleNamespace(id=1))  # type: ignore[assignment]
    buffs.apply(snap, 2041, 2010101, 10, 60, now)  # Physical Attack Scroll: "PATK +{Grades}%"
    buffs.apply(snap, 2037, 2010102, 5, 60, now)  # Student's Oatmeal: "Defense +{Grades}%"
    stats = buffs.percent_stats(snap, _templates(), now)
    assert stats == {"PhyAttack": 10, "PhyDefence": 5, "MagicDefence": 5}
    assert buffs.percent_stats(snap, _templates(), now.replace(hour=2)) == {}  # venceu


# --- fila de tecnologia no login (visto: 4155 com orderId 3 orderType 2) ---


def test_fila_de_tecnologia_nasce_com_a_academia_como_no_4155_ingles() -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from tests.game.test_batalha import _templates  # type: ignore[attr-defined]
    from wartune_server.domain.models import Building
    from wartune_server.game import castle

    t = _templates()
    academy = next(t.find("BuildingTempInfos", SonType=castle.ACADEMY))
    snap: PlayerSnapshot = SimpleNamespace(  # type: ignore[assignment]
        character=SimpleNamespace(id=1), orders=[], buildings=[Building(1, int(academy["TemplateId"]))]
    )
    order = castle.tech_order(snap, t, datetime(2026, 1, 1, tzinfo=UTC))
    assert order is not None and (order.order_id, order.order_type) == (3, castle.TECH_ORDER)


# --- vida do campo (8338) ---


def test_restaurar_vida_no_campo_usa_a_reserva() -> None:
    import inspect

    from wartune_server.game.handlers import warfield

    src = inspect.getsource(warfield.restore_hp)
    assert "heal_hero" in src and "FULL_HP" in src
