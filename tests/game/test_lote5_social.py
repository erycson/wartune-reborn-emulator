"""Lote 5 da auditoria: chat do time e da cena, corneta entre servidores, nó compartilhado (um teste por item)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_guild import _create, _guild, _member
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import BagType, Item
from wartune_server.game import guild as gd
from wartune_server.game.campaign import CampaignMap
from wartune_server.game.handlers import offer
from wartune_server.game.handlers.guild import election
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


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


async def test_9_vagas_extras_do_painel_ficam_zero_sem_pacote_de_compra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        await a.idle()
        offer.login_push(_s(a))
        [count] = [pb.RewardCountUpdateRspMsg.FromString(p.body) for p in await a.idle() if p.code == 4360]
        assert count.rewardCount == 0  # o cliente mostra 20 + rewardCount (OfferRewardManager)


async def test_6_eleicao_abre_com_o_chefe_sumido_conta_os_votos_e_fecha(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        await _create(a)
        b = await _member(a, "bruxa")
        c = await _member(a, "corvo")
        sb = _s(b)
        guild, g = _guild(a), sb.ctx.guilds
        a.client.writer.close()
        for _ in range(40):
            if sb.ctx.online.get(a.user_id) is None:
                break
            await b.idle(0.05)
        old = clock.now() - timedelta(days=11)
        g.logout_at[a.user_id] = old
        profile = g.profiles[a.user_id]
        profile.offline_at = profile.last_login_at = old
        await election.clock(sb)
        assert guild.voting_state == election.OPEN_VOTE and guild.voting_id == 1
        sb.snapshot.character.consortia_offer = 100  # type: ignore[union-attr]
        b.client.send(8481, pb.ConsortiaVotingReqMsg(votingUser=c.user_id))
        assert pb.ConsortiaVotingRspMsg.FromString([p for p in await b.idle() if p.code == 4390][0].body).result
        clock.advance(2 * 86400)
        await election.clock(sb)
        assert guild.voting_state == election.OPEN_VOTE  # ainda nos 3 dias
        clock.advance(86400 + 60)
        await election.clock(sb)
        assert guild.voting_state == election.NO_VOTE and guild.chairman_id == c.user_id
        assert g.members[c.user_id].duty_id == gd.CHAIRMAN and g.members[a.user_id].duty_id == gd.MEMBER
