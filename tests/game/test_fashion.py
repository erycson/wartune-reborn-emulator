from pathlib import Path

from tests.game.harness import logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item
from wartune_server.protocol.messages import wartune_pb2 as pb

CLOTH = 1120101  # Lover's Gown: roupa de moda (SonType 112, espaço 10), qualquer classe


async def test_fashion_book_hide_and_first_wear(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        g.client.send(8625)
        book = pb.FashionMsg.FromString((await g.until(4542))[-1].body)
        rows = g.server.services.templates.rows("ItemTempInfos")
        modas = [r for r in rows if r.get("MasterType") == "1" and r.get("SonType") in ("109", "110", "111", "112")]
        assert not book.info and len(book.fashionIds) == len(modas)  # todas as modas do jogo, como o oficial

        cloth = Item(g.user_id, CLOTH, pos=0)
        snap.items.append(cloth)
        await g.server.services.characters.save(cloth)
        hero = snap.leader.id  # type: ignore[union-attr]
        g.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=4, endObjId=hero, endPos=10))
        got = await g.until(4542)
        assert codes(got) == [3, 150, 115, 115, 4542]
        assert pb.ArmyArmyMsg.FromString(got[1].body).simpleHeroInfo.fashionCloth == "/fashion_cloth_qixi01"
        assert [(i.tempId, i.isSwitch) for i in pb.FashionMsg.FromString(got[-1].body).info] == [(CLOTH, False)]

        g.client.send(5008, pb.HeroHideFashionReqMsg(hide=1))
        look = pb.HeroEquUpdatedMsg.FromString((await g.until(149))[-1].body)
        assert look.hide and look.fashionCloth == "/fashion_cloth_qixi01"
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.leader.hide_fashion and [f.template_id for f in saved.fashions] == [CLOTH]  # type: ignore[union-attr]

        g.client.send(8594, pb.StoreReqMsg(operate=False))  # composição: regra desconhecida, recusa
        assert not pb.StoreRspMsg.FromString((await g.until(4487))[-1].body).composeResult


ROBES, RESPLENDENT = 1120201, 1120202  # Magnificent Robes e Resplendent Robes: outras roupas (SonType 112)


def _book(got: list) -> list[tuple[int, bool]]:
    return sorted((i.tempId, i.isSwitch) for i in pb.FashionMsg.FromString(got[-1].body).info)


async def test_dressing_room_saves_an_activated_look_on_the_worn_piece(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        hero = snap.leader.id  # type: ignore[union-attr]
        cloth, robes = Item(g.user_id, CLOTH, pos=0), Item(g.user_id, ROBES, pos=1)
        loose = Item(g.user_id, RESPLENDENT, pos=2, is_binds=False)
        snap.items.extend([cloth, robes, loose])
        await g.server.services.characters.save(cloth, robes, loose)

        # "New bound clothing will automatically be activated when it is obtained": a livre não
        g.client.send(8625)
        assert _book(await g.until(4542)) == [(CLOTH, False), (ROBES, False)]
        g.client.send(8631, pb.FashionMsg(templateId=CLOTH))  # apaga o ícone de "novo"
        assert _book(await g.until(4542)) == [(CLOTH, True), (ROBES, False)]

        g.client.send(8595, pb.FashionMsg(templateId=ROBES))  # tipData01: nada vestido nesse espaço
        assert await g.idle() == []
        g.client.send(5005, pb.ItemReqMsg(beginBagType=1, beginPos=0, endBagType=4, endObjId=hero, endPos=10))
        await g.idle()
        g.client.send(8595, pb.FashionMsg(templateId=RESPLENDENT))  # tipData02: não ativada
        g.client.send(8595, pb.FashionMsg(templateId=CLOTH))  # tipData03: é a vestida
        assert await g.idle() == []

        g.client.send(8595, pb.FashionMsg(templateId=ROBES))  # sem custo
        got = await g.until(115)
        assert codes(got) == [3, 150, 115] and cloth.template_id == ROBES
        assert pb.ItemMovedListMsg.FromString(got[-1].body).moved[0].item.templateId == ROBES
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert [i.template_id for i in saved.items if i.id == cloth.id] == [ROBES]
        assert sorted((f.template_id, f.is_switch) for f in saved.fashions) == [(CLOTH, True), (ROBES, False)]
