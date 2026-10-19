"""Todo opcode de mochila/loja/forja/moda tem handler e não derruba a sessão, com corpo vazio ou mínimo."""

from pathlib import Path

from google.protobuf.message import Message

from tests.game.harness import logged_in
from tests.game.test_shop import me
from wartune_server.domain.models import Item
from wartune_server.game.router import router
from wartune_server.protocol.messages import wartune_pb2 as pb

CODES = (
    [5005, 5006, 5007, 5008, 5010, 5129, 5150, 5151, 5152, 5153, 5154, 5633, 8199, 8218, 8220, 8336, 8339, 8340]
    + [8346, 8464, 8482, 8483, 8484, 8538, 8592, 8594, 8595, 8597, 8624, 8625, 8631, 8632, 8644, 8645, 8693]
    + [8781, 8809, 8819]
)
HOLY_SWORD = 1011004  # Sword of the Righteous: Profile 4, refino 2127001, 5 atributos


def test_every_code_has_a_handler() -> None:
    from wartune_server.game import handlers  # noqa: F401  (registra)

    assert [c for c in CODES if router.get(c) is None] == []


async def test_handlers_survive_empty_and_minimal_bodies(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        c = snap.character
        c.point, c.gift_token, c.gold = 5000, 0, 10**6
        sword = Item(g.user_id, HOLY_SWORD, bag_type=0, pos=0, join_1=0, join_2=0, join_3=0)
        stuff = [sword, Item(g.user_id, 208014, pos=5, count=3), Item(g.user_id, 208004, pos=6, count=2)]
        snap.items.extend(stuff)
        await g.server.services.characters.save(c, *stuff)

        minimal: dict[int, Message] = {
            8199: pb.DetailReqMsg(otherId=g.user_id),
            8819: pb.RentalBagOpReqMsg(opType=1, param1=1, param2="30"),
            8484: pb.ItemUseStoreReqMsg(count=2),
            8464: pb.RefreshPropertyReqMsg(itemId=sword.id or 0),
            8597: pb.AppellExchangeMsg(look=True),
            5152: pb.StoreReqMsg(holePos=4, operate=True),  # 4º furo: só em item Profile 5
            5008: pb.HeroHideFashionReqMsg(hide=2),
            5010: pb.PayTypeMsg(payType=1, property1=1),
            8625: pb.FashionMsg(),
        }
        for code in CODES:
            for msg in [None, minimal[code]] if code in minimal else [None]:
                g.client.send(code, msg)
                g.client.send(20008)  # o relógio volta = a sessão seguiu viva
                await g.until(4234)

        assert c.store_gp == 2 and c.bag_count == 7 and c.rental_bag_until is not None
        assert sword.join_4 == -1  # Sword of the Righteous é Profile 4: o 4º furo é só do Profile 5
