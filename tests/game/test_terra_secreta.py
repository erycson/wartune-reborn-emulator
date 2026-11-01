"""Terra secreta da guilda (7501, ``handlers/fam.py``) pela oficial_20261023-171155-1 #5056-#5172."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_guild import _create, _session
from tests.game.test_masmorra_1001 import _undying, back_to_map, codes
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Consortia
from wartune_server.game import battle as battle_mod
from wartune_server.game import fam
from wartune_server.game.campaign import DONE, NORMAL
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

INVADER = 750109  # o Invasor da captura (nó 595)


async def _enter(g: Game) -> list[Packet]:
    await _create(g)
    g.client.send(8537)
    return await g.idle()


async def _fight(g: Game) -> list[Packet]:
    g.client.send(5125, pb.CampaignReqMsg(paraInt1=INVADER, paraBool1=True))
    got = await g.until(157)
    assert codes(got) == [140, 131, 128, 157]  # #5082-#5085
    prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
    assert (prepare.battleType, prepare.mapTempId) == (23, 7501)
    return await g.fight(prepare) + await g.idle()


def _node(got: list[Packet]) -> pb.CampaignNodeUpdateMsg:
    return pb.CampaignNodeUpdateMsg.FromString(next(p.body for p in reversed(got) if p.code == 128))


async def test_entrar_perder_para_o_invasor_e_sair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    async with logged_in(tmp_path, novice=33000, clock=FakeClock(DAY)) as g:
        got = await _enter(g)
        assert codes(got) == [125, 140, 21]  # #5057-#5059
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == 7501

        got = await back_to_map(g)
        assert codes(got) == [127, 21, 21, 4432, 4632, 4453]  # #5061-#5066
        tree = pb.FamInfoMsg.FromString(got[3].body)
        # a captura (#5064) tinha 3: a invocação das 11:53 já tinha saído; guilda nova pode invocar (2)
        assert (tree.treeState, tree.treeGrades, tree.personNum) == (2, 1, 1)
        lords = pb.FamLordsInfoMsg.FromString(got[4].body)
        assert (lords.currentTurns, lords.leftTime) == (1, 180000)
        assert codes(await back_to_map(g)) == []  # a sala sai uma vez só

        g.client.send(5038, pb.CampaignReqMsg(paraInt1=7501))
        got = await g.idle()
        assert list(pb.SystemArmyMsg.FromString(got[0].body).soldierTemplated) == [3001]  # #5070

        got = await _fight(g)  # nível baixo contra 4 soldados de 7.936 de vida: perde
        report = pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103))
        assert (report.battleResult, report.battleScene) == (2, 3)
        tail = [c for c in codes(got) if c not in (113, 83)]
        assert tail[tail.index(4103) :] == [4103, 3, 150, 100, 4122, 140, 4104, 131, 128]  # #5105-#5113
        node = _node(got)
        assert node.nodeState == NORMAL and node.uuId and node.sonType == 2105
        assert codes(await back_to_map(g)) == [4382]  # #5117

        g.client.send(5025, pb.RoomExitMsg())
        got = await g.until(83)
        assert codes(got) == [4165, 150, 150, 140, 22, 4595, 83]  # #5164-#5169; 121659 #656
        assert pb.ChatChannelMsg.FromString(got[-1].body).encodeMsg == "Left Guild Chamber"
        assert _session(g).campaign is None


async def test_vencer_o_invasor_da_contribuicao(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_floor_hp", _undying)
    async with logged_in(tmp_path, novice=33000, clock=FakeClock(DAY)) as g:
        await _enter(g)
        await back_to_map(g)
        before = _session(g).snapshot.character.consortia_offer  # type: ignore[union-attr]
        wealth = _session(g).ctx.guilds.of(_session(g).player_id)[0].offer  # type: ignore[index]
        got = await _fight(g)
        assert pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleResult == 1
        assert _node(got).nodeState == DONE and 4122 not in codes(got)
        texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83]
        assert "Received: 10 Contribution" in texts  # TODO(inventado) o texto de quem venceu
        assert _session(g).snapshot.character.consortia_offer == before + 10  # type: ignore[union-attr]
        # (visto) 231733 #4104-#4105: o aviso a toda a guilda e o 164 com a riqueza +10
        assert any(t.endswith("has defeated an invader and earned 10 guild contribution!") for t in texts)
        info = pb.ConsortiaInfoMsg.FromString(next(p.body for p in got if p.code == 164))
        assert info.offer == wealth + 10

        # o vencido some para todos (a onda é da guilda; quem está na sala recebe o 128 state 8)
        (inv,) = _session(g).ctx.guilds.invasions.values()
        assert INVADER in inv.dead and not inv.fighting


async def test_um_por_vez_no_invasor(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000, clock=FakeClock(DAY)) as g:
        await _enter(g)
        await back_to_map(g)
        s = _session(g)
        mine = s.ctx.guilds.of(s.player_id)
        assert mine is not None
        inv, _ = fam.invasion(s.ctx.guilds.invasions, mine[0].id or 0, s.ctx.clock.now())
        inv.fighting[INVADER] = 999  # outro membro lutando com ele
        s.ctx.online._by_id[999] = SimpleNamespace(battle=object())  # type: ignore[assignment]
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=INVADER, paraBool1=True))
        got = await g.idle()
        assert codes(got) == [111, 128] and s.battle is None
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "Target is in battle, please wait…"
        del s.ctx.online._by_id[999]


def test_ondas_de_invasores_a_toda_hora() -> None:
    """(visto) 183522: os avisos a toda hora cheia e os Invasores somem às :30; o 1º olhar depois de subir o
    servidor não avisa."""
    store: dict[int, fam.Invasion] = {}
    inv, new = fam.invasion(store, 1, DAY + timedelta(minutes=30))
    assert not new and inv.wave == DAY
    inv.dead.add(INVADER)
    assert fam.invasion(store, 1, DAY + timedelta(minutes=59)) == (inv, False)
    inv2, new = fam.invasion(store, 1, DAY + timedelta(hours=1))
    assert new and inv2.wave == DAY + timedelta(hours=1) and not inv2.dead
    assert fam.invaders_up(DAY + timedelta(minutes=29)) and not fam.invaders_up(DAY + timedelta(minutes=30))


async def test_sem_guilda_nao_entra(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as g:
        g.client.send(8537)
        assert codes(await g.idle()) == []
        assert _session(g).campaign is None


TREE = 750102  # "Guild Tree of Ancients" (masterType 61)
DAY = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)


def _guild() -> Consortia:
    return Consortia(server_id=1, name="g", creator_id=1, creator_name="", chairman_id=1, created_at=DAY)


def test_arvore_sobe_com_o_data_do_nivel_seguinte_e_zera() -> None:
    """(dedução) 36 invocações levam ao nível 6 com 7 de EXP, como a guilda de 36 dias da captura (#5064)."""
    templates = asyncio.run(GameTemplates.load(TEMPLATES))
    guild = _guild()
    for day in range(36):
        assert fam.state(guild, DAY + timedelta(days=day)) == fam.CALLABLE
        fam.summon(guild, templates, DAY + timedelta(days=day))
        assert fam.state(guild, DAY + timedelta(days=day, minutes=14)) == fam.CALLED
        assert fam.state(guild, DAY + timedelta(days=day, minutes=16)) == fam.NO_OPER
    assert (guild.tree_grade, guild.tree_gp) == (6, 7)


def test_tiques_de_15_segundos_so_dentro_da_invocacao() -> None:
    guild = _guild()
    guild.tree_called_at = DAY
    assert fam.ticks(guild, DAY, DAY + timedelta(seconds=44)) == (2, DAY + timedelta(seconds=44))
    n, since = fam.ticks(guild, DAY + timedelta(seconds=44), DAY + timedelta(hours=1))
    assert (n, since) == (58, DAY + timedelta(seconds=900))  # 60 tiques no total
    assert fam.ticks(guild, since, DAY + timedelta(hours=2))[0] == 0


async def test_lider_invoca_energiza_compra_o_buff_e_ganha_exp(tmp_path: Path) -> None:
    clock = FakeClock(DAY)
    async with logged_in(tmp_path, novice=33000, clock=clock) as g:
        await _enter(g)
        got = await back_to_map(g)
        tree = pb.FamInfoMsg.FromString(next(p.body for p in got if p.code == 4432))
        assert (tree.treeState, tree.pickTime) == (2, "2000-01-01 00:00:00")  # o líder pode invocar

        g.client.send(8565)
        got = await g.idle()
        tree = pb.FamInfoMsg.FromString(next(p.body for p in got if p.code == 4432))
        assert (tree.treeState, tree.opreate, tree.treeGrades, tree.treeGp) == (1, 2, 2, 0)  # nível 2 pede 1
        shown = {pb.CampaignNodeUpdateMsg.FromString(p.body).nodeId for p in got if p.code == 128}
        assert len(shown) == 11  # a árvore e 10 das 21 coletas (visto 183522 #11313-#11322)
        s = _session(g)
        assert s.campaign is not None
        collect = next(c for c, n in s.campaign.nodes.items() if n["masterType"] == 91 and n["state"] == NORMAL)
        g.client.send(8565)
        assert codes(await g.idle()) == []  # uma vez por dia

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=TREE, paraBool1=True))
        got = await g.idle()
        assert pb.FamInfoMsg.FromString(next(p.body for p in got if p.code == 4432)).treeWaterCount == 1
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=TREE, paraBool1=True))
        assert codes(await g.idle()) == []  # uma energia por invocação

        char = _session(g).snapshot.character  # type: ignore[union-attr]
        char.consortia_offer = 500
        g.client.send(8566)
        got = await g.idle()
        assert pb.FamInfoMsg.FromString(next(p.body for p in got if p.code == 4453)).rate == pytest.approx(1.2)
        assert char.consortia_offer == 300  # Fam_Buffer_Price 200

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=collect, paraBool1=True))
        got = await g.idle()
        assert codes(got) == [143, 4609]  # (visto) 20261026-225632-1 #6488-#6489
        assert pb.NodeLockReqMsg.FromString(got[1].body) == pb.NodeLockReqMsg(nodeId=collect, lock=True)
        assert char.consortia_offer == 300
        g.client.send(5032, pb.CallBackReqMsg(mapId=7501, nodeId=collect, cmd=2))
        got = await g.idle()
        assert codes(got) == [3, 111, 83, 128, 164]  # #6491-#6495; o 83 da guilda (183522 #11131-#11132)
        assert pb.ChatChannelMsg.FromString(got[1].body).encodeMsg == "Successfully collected!"
        assert "guild contribution!" in pb.ChatChannelMsg.FromString(got[2].body).encodeMsg
        assert char.consortia_offer in (301, 305, 310)  # (visto) 1, 5 ou 10 (fam_tree.collect_offers, 0146)

        before, grade = char.total_gp, char.grades
        clock.advance(30)
        g.client.send(20008)
        await g.idle()
        assert char.total_gp == before + 2 * round(grade * 2 * 17 * 1.2)  # 2 tiques, árvore nível 2 (0146)
