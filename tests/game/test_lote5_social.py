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
from wartune_server.game.handlers import altar, marriage, offer
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


async def test_7_altar_do_demonio_entra_e_a_onda_vem_depois_do_preparo(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        await _create(a)
        s, guild = _s(a), _guild(a)
        guild.altar_state, guild.altar_at = gd.ALTAR_OPEN, clock.now()
        a.client.send(8542)
        got = await a.idle()
        [room] = [pb.RoomCreatedMsg.FromString(p.body) for p in got if p.code == 125]
        assert room.room.campaignId == altar.ALTAR_MAP and s.campaign is not None and s.campaign.altar
        [rep] = [pb.AltarCampaignReportMsg.FromString(p.body) for p in got if p.code == 4437]
        assert (rep.waveNum, rep.altarDurability, rep.leftStartTime) == (0, 100, 60000)  # 1 min de preparo
        clock.advance(61)
        await altar.clock(s)
        [rep] = [pb.AltarCampaignReportMsg.FromString(p.body) for p in await a.idle() if p.code == 4437]
        assert (rep.waveNum, rep.monsterCount) == (1, 1)
        run = s.ctx.guilds.altars[guild.id]
        hero = s.ctx.templates.get("GameHeroTemp", 1042)
        assert run.pool.hp == int(hero["Live"]) * 50  # vida do template
        clock.advance(5 * 60)  # a onda escapa: o altar perde vida e vem a próxima
        await altar.clock(s)
        assert (run.wave, run.durability) == (2, 80)
        guild.offer = 20000
        a.client.send(8593, pb.ConsortiaAltarOpenReqMsg(altarType=altar.LIVE))
        got = await a.idle()
        assert run.durability == 100 and guild.offer == 10000
        assert [pb.AltarCampaignSkillMsg.FromString(p.body).templateId for p in got if p.code == 4485] == [1]


async def test_8_reviver_no_altar_paga_contribuicao(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:
        await _create(a)
        s, guild = _s(a), _guild(a)
        guild.altar_state, guild.altar_at = gd.ALTAR_OPEN, clock.now()
        a.client.send(8542)
        await a.idle()
        run = s.ctx.guilds.altars[guild.id]
        run.pool.dead[a.user_id] = clock.now() + timedelta(seconds=30)
        s.snapshot.character.consortia_offer = 120  # type: ignore[union-attr]
        balens = s.snapshot.character.point  # type: ignore[union-attr]
        a.client.send(8264, pb.PayTypeMsg(payType=0))
        got = await a.idle()
        assert s.snapshot.character.consortia_offer == 70 and s.snapshot.character.point == balens  # type: ignore[union-attr]
        assert not run.pool.is_dead(a.user_id, clock.now())
        assert any(p.code == 4175 for p in got)


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


async def _married(a: Game) -> Game:
    from tests.game.test_marriage import _engage

    b = await a.join("bruxo", 3)  # type: ignore[call-arg]
    await _engage(a, b)
    b.client.send(15049, pb.MarriageOpMsg(opType=4, property1=3, payType=1))
    await a.until(4658)
    a.client.send(8759, pb.MarriageOpMsg(opType=5, property5=True))
    a.client.send(8759, pb.MarriageOpMsg(opType=5, property5=False))
    await a.until(4657)
    await a.idle()
    await b.idle()
    return b


async def test_5_jogo_do_coracao_missao_e_loja_do_casal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=19000) as a:
        b = await _married(a)
        monkeypatch.setattr(marriage, "_heart_cfg", lambda s: {"questions": 2, "seconds": 30, "points": 20})
        a.client.send(8802, pb.MarriageOpMsg(opType=marriage.HEART_START))
        await b.until(marriage.S_HEART_ASK)
        b.client.send(8802, pb.MarriageOpMsg(opType=marriage.HEART_ACCEPT))
        first = pb.MarriageHeartMsg.FromString((await a.until(marriage.S_HEART))[-1].body)
        assert first.maxOrder == 2 and first.curQuestion.order == 1
        assert list(first.curQuestion.options)[0] == 0  # índices 0-based (Option(options[i]+1))
        saved = marriage.dump_pending()  # o jogo vai para server_states e volta igual
        marriage._hearts.clear()
        marriage.load_pending(saved)
        assert marriage.dump_pending() == saved and a.user_id in marriage._hearts
        for order, (x, y) in enumerate([(0, 0), (0, 1)], 1):  # 0 = "A" (selectIndex)
            a.client.send(8802, pb.MarriageOpMsg(opType=marriage.HEART_ANSWER, property1=order, property2=x))
            await a.idle()
            b.client.send(8802, pb.MarriageOpMsg(opType=marriage.HEART_ANSWER, property1=order, property2=y))
            await b.idle()
        await a.idle()
        roses = sum(i.count for i in _s(a).snapshot.items if i.template_id == marriage.ROSE)  # type: ignore[union-attr]
        assert roses == 50 // 5  # syncRate 50: Rose Hazel x syncRate/5 (MarryHeartFrame)
        assert marriage.couple(_s(a).snapshot.marriage)["happy"] == 20  # type: ignore[union-attr]  # 1 acerto
        assert marriage.couple(_s(b).snapshot.marriage)["happy"] == 20  # type: ignore[union-attr]

        talk = next(r["TemplateId"] for r in _s(a).ctx.templates.find("RewardCondictionInfos", CondictionType="16")
                    if int(r["TemplateId"]) // 1000 == 4)  # fmt: skip
        monkeypatch.setattr(marriage.random, "choice", lambda pool: int(talk))
        a.client.send(8774, pb.MarriageOpMsg(opType=marriage.TASK_ACCEPT))
        got = pb.RewardUpdatedRspMsg.FromString((await a.until(marriage.S_TASKS))[-1].body)
        assert got.reward[0].templateId == int(talk) and not got.reward[0].isComplete
        a.client.send(8774, pb.MarriageOpMsg(opType=marriage.TASK_TALK))
        done = pb.RewardUpdatedRspMsg.FromString((await a.until(marriage.S_TASKS))[-1].body)
        assert done.reward[0].isComplete
        happy = marriage.couple(_s(a).snapshot.marriage)["happy"]  # type: ignore[union-attr]
        assert happy >= 20 + 50  # mar_task_add_happy

        a.client.send(9611, pb.AltarShopListMsg(op=marriage.SHOP_BUY, templateId=41001000))
        shop = pb.AltarShopListMsg.FromString((await a.until(marriage.S_MATE_SHOP))[-1].body)
        assert shop.altarScore == happy - 30
        assert next(i for i in shop.info if i.templateId == 41001000).leftCount == 0
