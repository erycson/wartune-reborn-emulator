"""Compras gravadas em ``purchases``: o item levado e o preço do momento (loja comum e poção de HP).

As linhas de loja saem do template: o catálogo muda entre versões e o que importa é a gravação.
"""

from pathlib import Path

from tests.game.harness import Game, logged_in
from tests.game.test_mall import _purchases
from tests.game.test_shop import buy, me
from wartune_server.game.handlers import shop
from wartune_server.protocol.messages import wartune_pb2 as pb


def _gold_row(g: Game, shop_type: str | None) -> dict[str, str]:
    """Primeira linha paga em ouro que o personagem pode comprar (``shop.check`` sem recusa)."""
    session = g.server.online.get(g.user_id)
    assert session is not None
    for row in g.server.services.templates.rows("ShopTempInfos"):
        if (shop_type is None and row.get("ShopType") in (shop.MYSTERY, shop.BLOOD)) or (
            shop_type is not None and row.get("ShopType") != shop_type
        ):
            continue
        if shop.price(row) is not None and shop.price(row)[0] == "Gold" and shop.check(session, row, 1) == shop.OK:  # type: ignore[index]
            return dict(row)
    raise AssertionError("nenhuma linha de loja em ouro no template")


async def test_compra_na_loja_grava_o_item_e_o_preco(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        me(g).character.gold = 10_000_000
        row = _gold_row(g, None)
        g.client.send(5154, buy(int(row["Id"]), 2))
        assert pb.ShopMsg.FromString((await g.until(90))[-1].body).buyInfo.result == shop.OK
        unit = int(row["Gold"])
        assert _purchases(tmp_path) == [
            (me(g).character.id, "shop", int(row["Id"]), int(row["ItemId"]), 2, "Gold", 2 * unit)
        ]


async def test_pocao_de_hp_grava_a_compra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        me(g).character.gold = 10_000_000
        row = _gold_row(g, shop.BLOOD)
        msg = buy(int(row["Id"]), 1)
        g.client.send(5633, msg)
        assert pb.FastUseBloodMsg.FromString((await g.until(shop.S_BLOOD))[-1].body).result == shop.OK
        assert _purchases(tmp_path) == [
            (me(g).character.id, "blood", int(row["Id"]), int(row["ItemId"]), 1, "Gold", int(row["Gold"]))
        ]
