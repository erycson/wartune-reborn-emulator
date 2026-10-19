"""Loja do labirinto (ShopType 4): a compra com Crypt Tokens (208009, a coluna ``MazeCoin``) contra a captura
``yeralti_labirent_marketi_alisveris`` (só turco) (5154 goodId 105 e 110), e o andar que o cliente esconde (GoodsItem.as:380)."""

from pathlib import Path

from tests.game.harness import Game, logged_in
from tests.game.test_shop import buy, codes, me
from wartune_server.domain.models import Item
from wartune_server.protocol.messages import wartune_pb2 as pb

MAZE_COIN = 208009  # Crypt Tokens (SonType 296), MazeCoin na loja
GOLD_BOX_GOOD, RING_GOOD = 105, 110  # ShopTempInfos 105: Gold Chest (1 moeda, andar 5); 110: Kronos (25, andar 15)
FLOOR_80_GOOD = 571  # ShopType 4 com MazeLayers 80: acima do maxIndex da torre (60), o cliente não mostra
SECOND_MAZE_GOOD = 630  # ShopType 4 com MazeLayers2 5: o segundo labirinto não tem info aqui (towerInfo2 = 0)


def result(got: list) -> int:  # type: ignore[type-arg]
    return pb.ShopMsg.FromString(got[-1].body).buyInfo.result


def template_name(g: Game, template: int) -> str:
    return next(g.server.services.templates.find("ItemTempInfos", TemplateId=template))["TemplateName"]


async def test_maze_shop_sells_for_maze_coin_like_the_capture(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        coins = Item(g.user_id, MAZE_COIN, pos=36, count=118)  # a captura: 118 -> 117 (Gold Chest) -> 92 (Kronos)
        me(g).items.append(coins)
        await g.server.services.characters.save(coins)

        g.client.send(5154, buy(GOLD_BOX_GOOD, 1, pay_type=1))  # o pedido da captura vem com payType 1
        got = await g.until(90)
        assert codes(got) == [115, 115, 111, 83, 90]  # a moeda, o item, o aviso e o chat, como o oficial
        assert (result(got), coins.count) == (1, 117)
        box = pb.ItemMovedListMsg.FromString(got[1].body).moved[0].item
        assert (box.templateId, box.count) == (2030101, 1)
        box_name = template_name(g, 2030101)
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == f"{box_name} x1 purchased successfully!"

        g.client.send(5154, buy(RING_GOOD, 1, pay_type=1))
        got = await g.until(90)
        assert codes(got) == [115, 115, 111, 83, 90]
        assert (result(got), coins.count) == (1, 92)
        ring = pb.ItemMovedListMsg.FromString(got[1].body).moved[0].item
        assert (ring.templateId, ring.count) == (1991017, 1)
        ring_name = template_name(g, 1991017)
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == f"{ring_name} x1 purchased successfully!"

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert [(i.template_id, i.count) for i in saved.items if i.template_id == MAZE_COIN] == [(MAZE_COIN, 92)]
        assert {2030101, 1991017} <= {i.template_id for i in saved.items}


async def test_maze_shop_refuses_without_coins_and_above_the_floor(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        coins = Item(g.user_id, MAZE_COIN, pos=36, count=92)
        me(g).items.append(coins)
        await g.server.services.characters.save(coins)

        g.client.send(5154, buy(RING_GOOD, 4, pay_type=1))  # 100 moedas, tem 92: nada muda
        got = await g.until(90)
        assert codes(got) == [90] and result(got) == 4
        assert coins.count == 92

        coins.count = 1000  # sobra dinheiro, mas o andar não chega: o cliente nem mostra o botão
        await g.server.services.characters.save(coins)
        for good in (FLOOR_80_GOOD, SECOND_MAZE_GOOD):
            g.client.send(5154, buy(good, 1, pay_type=1))
            got = await g.until(90)
            assert codes(got) == [90] and result(got) == 11
        assert coins.count == 1000
