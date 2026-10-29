"""Lote 5 da auditoria: chat do time e da cena, corneta entre servidores, nó compartilhado (um teste por item)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import BagType, Item
from wartune_server.game.campaign import CampaignMap
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def _s(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    s.snapshot.character.grades = max(s.snapshot.character.grades, 30)  # chat pede nível 6+
    return s


def _chats(got: list, channel: int) -> list[str]:  # type: ignore[type-arg]
    return [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83 and
            pb.ChatChannelMsg.FromString(p.body).channel == channel]  # fmt: skip


async def test_1_chat_do_time_vai_so_aos_membros(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        c = await a.join("corvo")
        _s(b), _s(c)
        teams = _s(a).ctx.teams
        assert teams.invite(a.user_id, b.user_id) and teams.accept(b.user_id, a.user_id)
        await b.idle()
        await c.idle()
        a.client.send(15005, pb.ChatChannelMsg(channel=6, encodeMsg="vamos"))
        assert _chats(await a.idle(), 6) == ["vamos"]
        assert _chats(await b.idle(), 6) == ["vamos"]
        assert _chats(await c.idle(), 6) == []


async def test_2_chat_da_cena_so_no_mesmo_mapa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        c = await a.join("corvo")
        _s(c)
        for g in (a, b):
            _s(g).space_pos = (1, 1)  # cidade do céu
        await b.idle()
        await c.idle()
        a.client.send(15005, pb.ChatChannelMsg(channel=8, encodeMsg="oi"))
        assert _chats(await b.idle(), 8) == ["oi"]
        assert _chats(await c.idle(), 8) == []  # está na cidade


async def test_3_corneta_entre_servidores_vai_a_todos_online(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        await b.idle()
        item = Item(a.user_id, 208025, count=1, bag_type=BagType.BAG, pos=30)
        await _s(a).ctx.characters.save(item)
        _s(a).snapshot.items.append(item)  # type: ignore[union-attr]
        a.client.send(8623, pb.CrossBigBugleMsg(content="alô"))
        assert [pb.CrossBigBugleMsg.FromString(p.body).content for p in await b.idle() if p.code == 4541] == ["alô"]


async def test_4_saida_do_no_vai_a_quem_esta_na_mesma_sala(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await a.join("bruxa")
        c = await a.join("corvo")
        sa, sb, sc = _s(a), _s(b), _s(c)
        room = sa.ctx.rooms.create(a.user_id, 4, "")
        assert sa.ctx.rooms.join(room, b.user_id)
        for s in (sa, sb, sc):
            s.campaign = CampaignMap(map_id=1001, nodes={1: {"campDataId": 1, "nodeId": 1}}, pos=(0, 0))
        await b.idle()
        await c.idle()
        a.client.send(8301, pb.PlayerNodeStateMsg(mapId=1001, nodeId=1))
        assert any(p.code == 4208 for p in await b.idle())
        assert not any(p.code == 4208 for p in await c.idle())  # mesmo mapa, sem a sala
