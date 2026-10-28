"""Guerra de guildas (mapa 4501): o estado puro de ``game/guildwar.py`` (par, fator, placar, defesa, buffs)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_guild import _create, _session
from tests.game.test_masmorra_1001 import back_to_map, codes
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Consortia
from wartune_server.game import arena
from wartune_server.game import guildwar as gw
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 26, 20, 0)


@pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
async def test_entrar_no_mapa_4501_recebe_placar_e_nos(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 10, 26, 20, 1, tzinfo=UTC))
    async with logged_in(tmp_path, novice=33000, clock=clock) as g:
        await _create(g)
        guilds = _session(g).ctx.guilds
        for i in range(4):  # a 5ª guilda (sem poder) é a adversária da 1ª
            guilds.guilds[900 + i] = Consortia(id=900 + i, server_id=1, name=f"G{i}", creator_id=0, creator_name="",
                                               chairman_id=0, created_at=clock.now())  # fmt: skip
        g.client.send(8471)
        got = await g.idle()
        assert codes(got) == [125, 140, 21, 127, 4439, 4440]
        assert pb.RoomCreatedMsg.FromString(got[0].body).room.campaignId == gw.WAR_MAP
        score = pb.GuildWarInfoListMsg.FromString(got[4].body)
        assert [x.consortiaId for x in score.guildWarInfos][1] == 903
        got = await back_to_map(g)
        assert {4450, 4462} <= set(codes(got))
        hp = pb.NodeHpListMsg.FromString(next(p.body for p in got if p.code == 4450))
        assert [n.currentHp for n in hp.nodeHp] == [gw.TOWER_HP, gw.TOWER_HP]
        guilds.wars[903].ticker.cancel()


@pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
async def test_8548_luta_real_contra_jogador_inimigo(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    copy = arena.copy_hero  # o inimigo com 1 de vida: quem ataca vence no primeiro golpe
    monkeypatch.setattr(arena, "copy_hero", lambda *a: copy(*a) | {"maxHp": 1, "initHp": 1, "hp": 1})
    clock = FakeClock(datetime(2026, 10, 26, 20, 1, tzinfo=UTC))
    async with logged_in(tmp_path, novice=33000, clock=clock) as g:
        await _create(g, "Lobos")
        other = await g.join("outro")
        await _create(other, "Ursos")
        s = _session(g)
        ids = [s.ctx.guilds.of(x.user_id)[0].id for x in (g, other)]  # type: ignore[index]
        war = gw.War(gw.Side(ids[0], "Lobos", gw.RED), gw.Side(ids[1], "Ursos", gw.BLUE), gw.window(clock.now())[0])
        s.ctx.guilds.wars[ids[0]] = s.ctx.guilds.wars[ids[1]] = war  # as duas se enfrentam hoje
        for game in (g, other):
            game.client.send(8471)
            await game.idle()
        assert other.server.online.get(other.user_id).campaign.gvg  # type: ignore[union-attr]
        war.gates_open = True
        g.client.send(8548, pb.GuildMsg(param1=other.user_id))
        got = await g.until(157)
        assert pb.BattlePrepareMsg.FromString(got[-1].body).battleType == 24
        s.battle.set_auto(True)  # type: ignore[union-attr]
        g.client.send(10007, pb.LoadOverMsg(armyId=g.user_id, battleId=s.battle.id))  # type: ignore[union-attr]
        mine = await g.until(4103) + await g.idle()
        assert pb.BattleReportMsg.FromString(next(p.body for p in mine if p.code == 4103)).battleResult == 1
        theirs = await other.idle()
        dead = [pb.PlayerStateListMsg.FromString(p.body) for p in theirs if p.code == 4175]
        assert any(x.armyId == other.user_id and x.state == gw.DEAD for m in dead for x in m.playerState)
        assert other.user_id in war.dead and {4104, 131} <= set(codes(theirs))


def _war() -> gw.War:
    return gw.War(gw.Side(1, "A", gw.RED), gw.Side(2, "B", gw.BLUE), NOW)


def test_pares_e_grupos() -> None:
    top = [10, 20, 30, 40, 50, 60, 70, 80]
    p = gw.pairs(top)
    assert p[10] == (50, gw.RED, 1) and p[50] == (10, gw.BLUE, 1)
    assert p[40] == (80, gw.RED, 4)
    assert gw.group_of(top, 60) == 2 and gw.group_of(top, 99) == 0
    assert gw.pairs([1, 2, 3]) == {}  # sem par ninguém luta


def test_janela() -> None:
    opened, ends = gw.window(NOW + timedelta(minutes=7))
    assert (opened.hour, ends.hour) == (20, 21)


def test_fator_das_torres_e_placar() -> None:
    w = _war()
    assert w.hit(w.red, 7, "x", 1, 100_000) == 50_000  # sem torre: x0,5
    w.owner = {1: gw.RED, 2: gw.RED, 3: gw.RED, 4: gw.RED}
    assert w.hit(w.red, 7, "x", 1, 100_000) == 200_000  # 4 torres: x2
    w.dead.add(9)
    assert w.tick(NOW) == [9] and not w.dead
    assert w.red.score == 25 and w.blue.hp == gw.TOWER_HP - 250_000
    assert w.wounds[7].wound == 250_000


def test_vitoria_por_vantagem_e_torre_caida() -> None:
    w = _war()
    w.red.dealt = gw.WIN_LEAD * gw.POINT_DAMAGE
    w.tick(NOW)
    assert w.winner == gw.RED
    w = _war()
    w.owner = {i: gw.BLUE for i in range(4)}
    w.hit(w.blue, 8, "y", 1, gw.TOWER_HP)
    assert w.red.hp == 0 and w.winner == gw.BLUE
    w = _war()
    w.time_over()
    assert w.winner == gw.RED  # empate fica com a vermelha


def test_defesa() -> None:
    w = _war()
    assert w.defend(5, 1, w.red, set(), cap=1) == "taken" and w.owner[5] == gw.RED
    assert w.defend(5, 2, w.blue, {1}, cap=1) == "full"
    assert w.defend(5, 3, w.red, set(), cap=2) == "ok"
    w.owner[5] = gw.BLUE
    assert w.defend(5, 2, w.red, {1, 3}, cap=5) == "contested"
    w.wound_of(1, "a", 1)
    w.tick(NOW)
    assert w.wounds[1].wound == gw.DEFEND_WOUND
    assert w.stop_defending(1) == 5 and w.defending(1) == 0


def test_buffs() -> None:
    w = _war()
    assert w.can_buff(w.red, gw.INSPIRATION, 1, 60, NOW)
    w.use_buff(w.red, gw.INSPIRATION, NOW)
    assert not w.can_buff(w.red, gw.INSPIRATION, 1, 60, NOW)
    assert w.rage(w.red, 7) and not w.rage(w.red, 7)
    w.red.hp = 1
    w.use_buff(w.red, gw.BLESSING, NOW)
    assert w.red.hp == 1 + int(gw.TOWER_HP * gw.BLESSING_HEAL)
    assert not w.can_buff(w.red, gw.BLESSING, 2, 60, NOW + timedelta(seconds=30))
    assert w.can_buff(w.red, gw.BLESSING, 2, 60, NOW + timedelta(seconds=60))
