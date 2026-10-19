from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.domain.models import Item
from wartune_server.protocol.messages import wartune_pb2 as pb

NEWBIE_BOX = 2060101  # Lvl. 5 Starter Pack (guerreiro), GradeDrop 90105: 10 de Bound Balens


async def test_opening_the_newbie_box_swaps_it_for_its_drop(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, job_icon=1) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        snap.character.grades, gold = 5, snap.character.gold
        box = Item(g.user_id, NEWBIE_BOX, pos=0)
        snap.items.append(box)
        await g.server.services.characters.save(snap.character, box)

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        got = await g.until(3)
        assert [p.code for p in got] == [115, 150, 109, 115, 111, 83, 3]
        assert pb.ItemMovedListMsg.FromString(got[0].body).moved[0].HasField("item") is False
        added = pb.ItemMovedListMsg.FromString(got[3].body).moved
        assert [(m.item.templateId, m.changePos) for m in added] == [(2060102, 0), (1080002, 1), (1070002, 2)]
        text = pb.ChatChannelMsg.FromString(got[4].body).encodeMsg
        assert (
            text
            == "Received:  10 Bound Balens, 3,000 Gold, Amethyst Ring x1, Coruscan Crest x1, Lvl. 10 Starter Pack x1"
        )
        assert pb.PlayerMsg.FromString(got[6].body).giftToken == 10

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert sorted(i.template_id for i in saved.items if i.bag_type == 1) == [1070002, 1080002, 2060102]
        assert (saved.character.gold, saved.character.gift_token) == (gold + 3000, 10)

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))  # agora é a Lv.10: nível 5 não abre
        assert await g.idle() == []
