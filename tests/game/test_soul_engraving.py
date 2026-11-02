"""Soul Engraving (8484): nível por custo de cada nível, ordem da resposta e a condição 58 (missão 858).
(visto) 20261101-220132-1 #1962-#2003."""

from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import logged_in
from tests.game.test_shop import me
from wartune_server.domain.models import Item, Quest
from wartune_server.game import rules
from wartune_server.game.handlers.items import STORE_GRADE, store_level
from wartune_server.protocol.messages import wartune_pb2 as pb

ORDER = {115, 4484, 3, 150, 111, 112, 4385, 83}


async def test_store_level_is_cost_per_level(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        levels = list(g.server.services.templates.find("UpGradeTempInfos", Types=STORE_GRADE))
    assert store_level(levels, 0, 566) == (7, 1)  # 10+30+52+76+102+131+164 = 565
    assert store_level(levels, 7, 1 + 100) == (7, 101)


def test_jewel_effect_and_engraved_gem() -> None:
    assert [rules.jewel_effect(g) for g in (0, 7, 50, 60, 80, 81)] == [0, 14, 100, 130, 200, 0]
    assert rules.engraved({"Attack": "100", "Power": "10"}, 7) == {"Attack": "114", "Power": "10"}


async def test_use_store_order_and_condition_58(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = me(g)
        c = snap.character
        crystal = Item(g.user_id, 208014, pos=5, count=666)
        quest = Quest(g.user_id, 858, datetime.now(UTC))
        snap.items.append(crystal)
        snap.quests.append(quest)
        await g.server.services.characters.save(crystal, quest)
        gp = c.gp

        g.client.send(8484, pb.ItemUseStoreReqMsg(count=566))
        got = await g.until(83)
        assert [p.code for p in got if p.code in ORDER] == [115, 4484, 3, 3, 150, 111, 112, 4385, 83]
        assert (c.store_grade, c.store_gp, c.gp) == (7, 1, gp)
        assert quest.progress == 1
        alert = next(p for p in got if p.code == 111)
        assert pb.ChatChannelMsg.FromString(alert.body).encodeMsg == "Received:EXP x566"

        g.client.send(8484, pb.ItemUseStoreReqMsg(count=100))
        got = await g.until(83)
        assert [p.code for p in got if p.code in ORDER] == [115, 3, 111, 112, 4385, 83]  # 858 ainda aberta: +1
        assert (c.store_grade, c.store_gp) == (7, 101)
