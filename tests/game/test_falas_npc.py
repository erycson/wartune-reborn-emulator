"""Falas dos NPCs (4163, ``game_settings.npc_chat`` da 0076): repertório por sonType das capturas inglesas."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_masmorra_1001 import codes, enter
from tests.test_end_to_end import TEMPLATES
from wartune_server.game.handlers import campaign as hc
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


class _Always(random.Random):
    def random(self) -> float:
        return 0.0


async def test_tique_faz_os_npcs_vivos_falarem(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1006)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None
        hc.talk_tick(s, _Always(1))
        got = [pb.NPCChatMsg.FromString(p.body) for p in await g.idle() if p.code == hc.S_NPC_CHAT]
        lines = s.ctx.world.settings["npc_chat"]["lines"]
        by_id = {n["nodeId"]: n for n in s.campaign.nodes.values()}
        assert got  # (visto) 231733: Tauren Gladiator, Berserker e Kronos falam na 1151
        for m in got:
            node = by_id[m.id]
            assert node["state"] == 1 and m.content in lines[str(node["sonType"])]["idle"]


async def test_chase_fala_so_na_primeira_vez(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hc.random, "random", lambda: 0.0)
    async with logged_in(tmp_path, novice=19000) as g:
        await enter(g, 1006)
        s = g.server.online.get(g.user_id)
        assert s is not None and s.campaign is not None
        berserker = s.campaign.node(115105)  # sonType 2107, agressivo
        assert berserker is not None and berserker["attackTypes"] == 1
        g.client.send(8196, pb.NodeLockReqMsg(nodeId=115105, lock=True))
        got = await g.idle()
        assert codes(got) == [4105, 4163]  # (visto) 231733 #764-#765
        assert pb.NPCChatMsg.FromString(got[1].body).content == "More humans? Get them!"
        g.client.send(8196, pb.NodeLockReqMsg(nodeId=115105, lock=True))
        assert codes(await g.idle()) == [4105]
