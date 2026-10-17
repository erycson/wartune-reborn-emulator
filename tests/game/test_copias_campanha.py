"""Campanha em grupo (4240): o Büyük Sefer soma uma entrada no dia (captura
``buyuk_sefer_kullanimi_grup_sahne_yarari_1``), e no dia seguinte o login volta ao ``MultiCampaign_MaxCount``."""

from pathlib import Path

from tests.game.harness import logged_in
from tests.game.test_shop import codes, me
from wartune_server.domain.models import Item
from wartune_server.game.handlers.login import player_info
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

BUYUK_SEFER = 2032101  # ItemTempInfos: SonType 203, Property1 15, Property2 1 ("valid for the day used")


async def test_buyuk_sefer_adds_one_entry_per_use_and_is_saved(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        item = Item(g.user_id, BUYUK_SEFER, pos=0, count=2)
        me(g).items.append(item)
        await g.server.services.characters.save(item)

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        got = await g.until(3)
        assert codes(got) == [115, 4240, 111, 3]  # visto: 115, 4240, 111 e 3 (o 109 do castelo não é do item)
        copies = pb.MultiCampaignEnterCountMsg.FromString(got[1].body)
        assert (copies.campaignCount, copies.campaignMaxcount) == (2, 2)  # 1/1 do login + 1 uso
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Grup Ek Sahne yararı 1 kez arttı"
        assert pb.PlayerMsg.FromString(got[3].body).campaignCount == 2
        assert item.count == 1

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        copies = pb.MultiCampaignEnterCountMsg.FromString((await g.until(4240))[-1].body)
        assert (copies.campaignCount, copies.campaignMaxcount) == (3, 3)
        await g.until(3)

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert (saved.character.multi_copy_count, saved.character.multi_copy_max) == (3, 3)
        assert saved.character.multi_copy_day == "2026-01-01"
        assert not [i for i in saved.items if i.template_id == BUYUK_SEFER]  # as duas unidades foram usadas


async def test_copies_go_back_to_the_base_on_the_next_day(tmp_path: Path) -> None:
    clock = FakeClock()
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        item = Item(g.user_id, BUYUK_SEFER, pos=0, count=1)
        me(g).items.append(item)
        await g.server.services.characters.save(item)
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        await g.until(3)

        session = g.server.online.get(g.user_id)
        assert session is not None
        today = player_info(session, me(g))  # o que o login manda (o 3 também usa essa função)
        assert (today.campaignCount, today.campaignMaxcount) == (2, 2)

        clock.advance(24 * 3600)  # o dia seguinte: o item valia só no dia do uso
        tomorrow = player_info(session, me(g))
        assert (tomorrow.campaignCount, tomorrow.campaignMaxcount) == (1, 1)
