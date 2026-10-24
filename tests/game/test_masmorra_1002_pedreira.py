"""Masmorra Baylon Plains (1002: 1131 -> 1132, 1141 -> 1142), pedreira 6001 e o relatório 137, pela captura inglesa."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_masmorra_1001 import Sure, back_to_map, codes, content, enter, fast_battles, leave, won
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import campaign as cm
from wartune_server.game import rules
from wartune_server.game.campaign import DONE, NORMAL, SHOW, CampaignMap, StageRun, grades, report, total_gp
from wartune_server.game.campaign import unlock_actions as actions
from wartune_server.game.handlers import campaign as hc
from wartune_server.game.handlers.campaign import _map_finished
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
__all__ = ["fast_battles"]  # fixture autouse importada: sem sorte nos drops e lutas rápidas

WOOD = 2100022  # Wood, item da missão 102 (tipo 32)


def test_exp_do_fim_e_em_float_como_o_oficial() -> None:
    assert (total_gp(600), total_gp(800)) == (630, 839)  # (visto) inglesa #1100 e #2707: 800 * 1,05 dá 839


def test_notas_das_seis_amostras_dao_1_5_5_e_4() -> None:
    row_1001 = {"StandardDamage": 2560, "StandardHurt": 4200, "BaseGp": 600}
    row_1002 = {"StandardDamage": 5920, "StandardHurt": 9400, "BaseGp": 800}
    start = datetime(2026, 10, 18, tzinfo=UTC)
    samples = [(row_1001, 424, 0), (row_1001, 1253, 727), (row_1002, 1751, 32), (row_1002, 2162, 99)]
    for row, wound, hurt in samples:  # inglesa #1098, #1521, #2705, #3157
        run = StageRun(1001, 0, (1011,), start, wound=wound, hurt=hurt)
        assert grades(run, row) == (1, 5, 5, 4)
    run = StageRun(1002, 0, (1131, 1132), start, wound=6000, hurt=9400, lost=2, batter=7)
    assert grades(run, row_1002) == (5, 1, 3, 3)  # S no dano, todo o padrão sofrido = D, 2 derrotas = C
    msg = report(run, row_1002, start + timedelta(seconds=189.9))
    assert (msg.time, msg.batter, msg.failedCount, msg.totalGp) == (189, 7, 2, 839)


async def test_caixa_do_cacador_114203_sorteia_daru_ou_luck_stone(tmp_path: Path) -> None:
    """0052: o 114203 dá Daru (inglesa #3057) ou Lvl. 3 Luck Stone (oficial_encantar #1436); o aviso do item não
    leva ``x1`` (#1457)."""
    async with logged_in(tmp_path, novice=25500) as g:
        world, templates = g.server.services.world, g.server.services.templates
    assert world.campaigns[1002]["wins"]["114203"]["pick"] == [[[-300, 10000]], [[2040103, 1]]]
    assert hc._win_text(templates, [(2040103, 1)]) == "Received: Lvl. 3 Luck Stone"
    assert hc._win_text(templates, [(-300, 10000)]) == "Received: 10,000 Daru"
    assert hc._win_text(templates, [(2040103, 2)]) == "Received: Lvl. 3 Luck Stone x2"


def test_param4_com_e_sem_acao() -> None:
    assert actions({"masterType": 42, "param4": "102110,0|102109,1"}) == [(102110, 0), (102109, 1)]
    assert actions({"masterType": 42, "param4": "113106"}) == [(113106, SHOW)]  # 1002: só aparece
    assert actions({"masterType": 61, "param4": "113203|113207|113208"}) == []  # caixa: são os nós que fecham


def test_portal_do_1131_aparece_com_o_grupo_e_a_caixa_nao_fecha_o_mapa() -> None:
    camp = CampaignMap.enter_dungeon(content(1002), 1131)
    assert camp.locked(113106)
    camp.nodes[113102]["state"] = DONE
    assert not _map_finished(camp, 113104)  # o grupo caiu, mas o param4 libera o portal
    camp.nodes[113104]["state"] = DONE
    assert not camp.locked(113106)
    camp = CampaignMap.enter_dungeon(content(1002), 1132)
    assert not _map_finished(camp, 113203)  # caixa do caçador (61)
    assert _map_finished(camp, 113205)  # Karlan (41)


async def arrive(g: Game, camp: int) -> list[Packet]:
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
    return await g.idle()


async def confirm(g: Game, camp: int) -> list[Packet]:
    asked = await arrive(g, camp)
    assert codes(asked) == [29, 4126]  # inglesa #2397-#2398
    mapid = pb.CampaignConfirmMsg.FromString(asked[0].body).mapId
    g.client.send(5033, pb.CampaignReqMsg(paraInt1=mapid, paraInt2=camp, paraBool1=True))
    return await g.idle()


def text(packet: Packet) -> str:
    if packet.code == 126:
        return pb.CampaignNotifyMsg.FromString(packet.body).body
    return pb.ChatChannelMsg.FromString(packet.body).encodeMsg


async def test_1002_do_1131_ao_karlan_e_a_segunda_etapa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        got = await enter(g, 1002)
        assert codes(got) == [125, 140, 21, 127, 130, 143, 138, 3, 83]  # inglesa #2311-#2320
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1131
        assert text(got[-1]) == "Entered [Baylon Plains] and deducted 20 stamina."

        g.client.send(5038, pb.CampaignReqMsg(paraInt1=1131))
        assert list(pb.SystemArmyMsg.FromString((await g.until(20))[-1].body).soldierTemplated) == [2022]

        with monkeypatch.context() as m:
            m.setattr(Sure, "outcome", cm.OUT_FIGHT)
            tomb = await confirm(g, 113105)  # tumba: o sentinela acorda (#2400-#2404)
        assert codes(tomb)[:2] == [126, 128] and text(tomb[0]) == "You've startled a sentinel... begin battle!"
        assert list(pb.CampaignNodeUpdateMsg.FromString(tomb[1].body).visitUserIds) == [g.user_id]
        await g.fight(pb.BattlePrepareMsg.FromString(next(p.body for p in tomb if p.code == 157)))
        await g.idle()
        await back_to_map(g)

        for camp in (113102, 113104):
            g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
            last = await won(g)
        portal = [pb.CampaignNodeUpdateMsg.FromString(p.body) for p in last if p.code == 128][-1]
        assert (portal.nodeId, portal.nodeState) == (14083, NORMAL)  # 113106, sem FLICKER (#2471)
        assert 143 not in codes(last)

        got = await arrive(g, 113106)
        assert codes(got) == [4208, 125, 127, 130, 21, 131]  # inglesa #2503-#2508
        room = pb.RoomCreatedMsg.FromString(got[1].body)
        assert (room.createdType, room.room.campaignId) == (3, 1132)

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=113202, paraBool1=True))
        await won(g)

        characters = g.server.services.characters
        daru = (await characters.snapshot(g.user_id)).character.strategy
        cache = await confirm(g, 113203)
        assert codes(cache)[-1] == 157  # caixa do caçador: luta direto (#2599-#2602)
        after = await g.fight(pb.BattlePrepareMsg.FromString(cache[-1].body)) + await g.idle()
        tail = codes(after)[codes(after).index(126) - 1 :]
        # inglesa #2630-#2644, sem os 140/131 repetidos; o 83 da EXP depois dos 128 (oficial_20261023-171155-1 #5543)
        assert tail == [3, 126, 128, 128, 128, 83, 83]
        assert text(after[codes(after).index(126)]) == "Received: 10,000 Daru"
        done = [pb.CampaignNodeUpdateMsg.FromString(p.body) for p in after if p.code == 128][-3:]
        assert {(n.nodeId, n.nodeState) for n in done} == {(14086, DONE), (14088, DONE), (14089, DONE)}
        assert (await characters.snapshot(g.user_id)).character.strategy == daru + 10000  # gravado
        await back_to_map(g)

        assert codes(await arrive(g, 113205)) == [138]  # Karlan fala antes (#2666)
        g.client.send(5032, pb.CallBackReqMsg(mapId=1827, nodeId=113205, cmd=2))
        g.client.send(8282, pb.BatterLastInfoMsg(count=7))
        end = await won(g)
        # inglesa #2703-#2714; o 4152 e o 83 a mais são a devoção do leed 4, que a inglesa já tinha do tutorial (#521)
        assert codes(end)[-12:] == [4382, 3, 137, 4151, 83, 135, 4165, 150, 150, 140, 4152, 83]
        msg = pb.CampaignReportMsg.FromString(next(p.body for p in end if p.code == 137))
        assert (msg.totalGp, msg.batter, msg.failedCount) == (839, 7, 0)
        assert [text(p) for p in end if p.code == 83][-2:] == [
            "Received 839 EXP ",
            "Your devotion level has increased to 10.",
        ]
        rank = pb.RankListRspMsg.FromString(next(p.body for p in end if p.code == 4151))
        assert [r.campaignId for r in rank.rankInfo] == [1002]

        await leave(g)
        got = await enter(g, 1002)  # (visto) #2788: o mesmo 5039 leva à 2ª etapa
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 1141

        before = (await characters.snapshot(g.user_id)).character.strategy
        coins = await confirm(g, 114105)  # tumba com Daru (#2874-#2877)
        assert codes(coins) == [3, 126, 128, 83] and text(coins[1]) == "Received: 5,000 Daru"
        assert (await characters.snapshot(g.user_id)).character.strategy == before + 5000
        assert await arrive(g, 114105) == []  # já aberta

        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None and session.snapshot.leader is not None
        session.snapshot.leader.grades = 40  # a Karda vem com três heróis: o mago de teste precisa aguentar
        for camp in (114102, 114104):
            g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp, paraBool1=True))
            await won(g)
        got = await arrive(g, 114106)
        assert codes(got) == [4208, 125, 127, 130, 21, 131]  # inglesa #2956-#2962
        assert pb.RoomCreatedMsg.FromString(got[1].body).room.campaignId == 1142

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=114202, paraBool1=True))
        await won(g)
        daru = (await characters.snapshot(g.user_id)).character.strategy
        cache = await confirm(g, 114203)
        after = await g.fight(pb.BattlePrepareMsg.FromString(cache[-1].body)) + await g.idle()  # Sure: o 1º do pick
        assert text(after[codes(after).index(126)]) == "Received: 10,000 Daru"
        assert (
            await characters.snapshot(g.user_id)
        ).character.strategy == daru + 10000  # Daru da luta = tropas perdidas
        movie = await back_to_map(g)
        assert pb.FightOverMoiveMsg.FromString(movie[0].body).strategy == 0  # inglesa #3076: 15 mortos; aqui sem tropa

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=114206, paraBool1=True))  # Karda: luta na chegada
        end = await won(g)
        assert 138 not in codes(end)
        # inglesa #3155-#3166 (lá sem subida de nível; aqui o mago de teste sobe e vêm 139/100 do push_level)
        tail = [c for c in codes(end) if c not in (139, 100)][-10:]
        assert tail == [4382, 3, 137, 4151, 83, 135, 4165, 150, 150, 140]
        rank = pb.RankListRspMsg.FromString(next(p.body for p in end if p.code == 4151))
        assert [r.campaignId for r in rank.rankInfo] == [1002]
        snap = await characters.snapshot(g.user_id)
        assert {e.key: e.value for e in snap.events}["campaign_stage:1002"] == 0  # volta ao 1131


async def test_pedreira_entra_colhe_luta_e_sai(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        g.client.send(8258, pb.WorldBossMsg(param1=6001))
        got = await g.idle()
        assert codes(got) == [125, 140, 140, 21, 127]  # inglesa #1805-#1809
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 6001

        got = await arrive(g, 600108)
        movie = pb.PlayerMovieMsg.FromString(got[0].body)
        assert codes(got) == [143] and (movie.movieType, movie.targetId) == ("COLLECTION", 7)  # #1843

        characters = g.server.services.characters
        for _ in range(2):  # (visto) #1847 e #1861: a mesma pilha duas vezes
            g.client.send(5032, pb.CallBackReqMsg(mapId=6001, nodeId=600108, cmd=2))
            got = await g.idle()
            assert codes(got) == [115, 4476, 111, 83] and text(got[3]) == "Received: Wood x2"  # #1848-#1860
        snap = await characters.snapshot(g.user_id)
        assert rules.goods_count(snap, WOOD) == 4  # a missão 102 (tipo 32) lê a bolsa

        g.client.send(8699)
        got = await g.until(157)
        assert codes(got) == [140, 157]  # inglesa #1929-#1930
        got = await g.fight(pb.BattlePrepareMsg.FromString(got[-1].body)) + await g.idle()
        assert codes(got)[-9:] == [115, 4476, 111, 140, 4103, 150, 100, 83, 4382]  # inglesa #2050-#2070
        assert text(got[-2]) == "Received: Wood x18"
        assert rules.goods_count(await characters.snapshot(g.user_id), WOOD) == 22

        g.client.send(5025, pb.RoomExitMsg())
        got = await g.until(4595)
        assert codes(got) == [4165, 150, 150, 140, 22, 4595]  # inglesa #2118-#2123
        session = g.server.online.get(g.user_id)
        assert session is not None and session.campaign is None
