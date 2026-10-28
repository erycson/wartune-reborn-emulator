import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from wartune_server.domain.models import Quest, WorldBossFight
from wartune_server.domain.world import WorldBoss
from wartune_server.game import boss_fight, worldboss
from wartune_server.game.handlers import worldboss as wb
from wartune_server.game.router import router
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock
from wartune_server.templates.repository import GameTemplates

WORLD_BOSS_OPCODES = (8258, 8259, 8264, 8271, 8470)
ALERT = 111
BEFORE_OPEN = datetime(2026, 5, 21, 12, 20, tzinfo=UTC)  # 12:20 (testes em UTC): 5001 aberto (11:35-12:35), 5003 não
OPEN_5001 = datetime(2026, 5, 21, 11, 40, tzinfo=UTC)  # 11:40: 5001 aberto (abre 11:35 no inglês)


@pytest.fixture(autouse=True)
def _no_info_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    """O 4174 de 8 s (relógio de verdade) não entra nas listas exatas de pacotes."""
    monkeypatch.setattr(wb, "INFO_EVERY", 3600)


def _states(msg: pb.WorldBossStateMsg) -> list[tuple[int, int]]:
    return [(i.campaignId, i.state) for i in msg.worldBossInfo]


def test_window_uses_the_game_timezone_and_edges() -> None:
    templates = GameTemplates(
        {
            "Campaigns": [
                {"CampaignId": "5001", "Types": "1", "OpenTime": "11:00", "StopTime": "12:00", "MinLevel": "20"},
                {"CampaignId": "5003", "Types": "1", "OpenTime": "21:35", "StopTime": "22:35", "MinLevel": "20"},
                {"CampaignId": "4602", "Types": "16", "OpenTime": "21:35", "StopTime": "22:35", "MinLevel": "20"},
            ]
        }
    )
    # só turco (replay idx 78 -> 102): 5001=2 e 5003=1; a inglesa #103 também
    assert _states(worldboss.states_msg(templates, BEFORE_OPEN)) == [(5001, 2), (5003, 1)]
    # só turco: login.json #120, 20:06 (era UTC+3): o mesmo 5001=2 e 5003=1
    assert _states(worldboss.states_msg(templates, datetime(2026, 5, 21, 20, 6, tzinfo=UTC))) == [(5001, 2), (5003, 1)]
    row = worldboss.boss(templates, 5001)
    assert row is not None
    # visto 27/10 e 26/10: o mapa abre 4 min antes de nascer, e nasce 1 min depois do OpenTime
    assert worldboss.state(row, datetime(2026, 5, 21, 10, 57, tzinfo=UTC)) == worldboss.OPEN
    assert worldboss.state(row, datetime(2026, 5, 21, 10, 56, 59, tzinfo=UTC)) == worldboss.BEFORE
    assert not worldboss.spawned(row, datetime(2026, 5, 21, 11, 0, 59, tzinfo=UTC))
    assert worldboss.spawned(row, datetime(2026, 5, 21, 11, 1, tzinfo=UTC))
    since, now = datetime(2026, 5, 21, 10, 40, tzinfo=UTC), datetime(2026, 5, 21, 11, 1, tzinfo=UTC)
    assert worldboss.events(row, since, now) == [("notice", 15), ("notice", 10), ("notice", 5), ("countdown", 3),
                                                 ("countdown", 2), ("countdown", 1), ("spawn", 0)]  # fmt: skip
    assert worldboss.events(row, now, now) == []
    assert worldboss.state(row, datetime(2026, 5, 21, 11, 59, tzinfo=UTC)) == worldboss.OPEN  # 11:59
    assert worldboss.state(row, datetime(2026, 5, 21, 12, tzinfo=UTC)) == worldboss.CLOSED  # 12:00
    assert worldboss.boss(templates, 4602) is None  # Types 16 não é chefe do mundo


async def test_agenda_e_recusas_com_o_relogio_da_captura(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(BEFORE_OPEN)) as g:
        c = g.client
        c.send(8271)
        [state] = [pb.WorldBossStateMsg.FromString(p.body) for p in await g.idle() if p.code == 4182]
        assert _states(state) == [(5001, 0), (5003, 1)]  # 5001 já abriu às 11:35 no inglês (fecha 12:35)

        c.send(8258, pb.WorldBossMsg(param1=5003))  # fora da janela: o oficial não responde (#1386)
        c.send(8258, pb.WorldBossMsg(param1=4602))  # não é chefe do mundo
        assert [p.code for p in await g.idle()] == [ALERT]

        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        ch = session.snapshot.character
        ch.point, ch.gift_token = 50, 50
        c.send(8264, pb.PayTypeMsg(payType=0))  # reviver: sem morte no chefe, nada cobrado
        c.send(8470, pb.WorldBossBufferMsg(op=2, type=2))  # buff: sem mapa do chefe, nada cobrado
        assert [p.code for p in await g.idle()] == [ALERT, ALERT]
        assert (ch.point, ch.gift_token) == (50, 50)


async def test_entrar_e_sair_do_chefe_com_dois_jogadores(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        g.client.send(8258, pb.WorldBossMsg(param1=5001))  # nível 1 < 20
        assert [p.code for p in await g.idle()] == [ALERT]

        b = await g.join("outro")
        for game in (g, b):
            session = g.server.online.get(game.user_id)
            assert session is not None and session.snapshot is not None
            session.snapshot.character.grades = 20
        await g.idle()  # a cidade do céu mostra o outro chegando
        g.client.send(8258, pb.WorldBossMsg(param1=5001))
        got = await g.idle()
        assert [p.code for p in got] == [125, 140, 21, 127, 4165, 150]  # visto #1396-#1404
        [nodes] = [pb.CampaignNodeListMsg.FromString(p.body) for p in got if p.code == 127]
        # entrada, o Bloodfang, o portal e a barreira (já nasceu às 11:36: some)
        assert sorted((n.campDataId, n.masterType, n.heroTempId, n.state) for n in nodes.node) == [
            (500101, 40, -1, 2), (500102, 42, 2002, 1), (500103, 61, -1, 1), (500104, 53, -1, 8)]  # fmt: skip
        [boss] = [n for n in nodes.node if n.masterType == 42]
        assert boss.nodeName == "Bloodfang" and (boss.posX, boss.fixX) == (51, 1029)
        g.client.send(5035, pb.LoginStateMsg(state=4))
        got = await g.idle()
        assert [p.code for p in got] == [4371, 4413]
        [click] = pb.ClickDatasRspMsg.FromString(got[1].body).info  # #1407: o contador do dia do chefe
        assert (click.keys, click.keyData) == ("5001", 1)
        g.client.send(5035, pb.LoginStateMsg(state=4))  # a volta de cada luta não responde (#1731)
        assert [p.code for p in await g.idle()] == []
        g.client.send(5038, pb.CampaignReqMsg(paraInt1=5001))
        [army] = [pb.SystemArmyMsg.FromString(p.body) for p in await g.idle() if p.code == 20]
        assert list(army.heroTemplated) == [2002]
        ctx = g.server.online.get(g.user_id).ctx  # type: ignore[union-attr]
        info = ctx.bosses.pools[5001].info(g.user_id, 1, OPEN_5001)
        assert (info.curHp, info.totalHp, info.totalNum, info.grades) == (2_000_000, 2_000_000, 1, 0)  # Live do herói

        await b.idle()
        b.client.send(8258, pb.WorldBossMsg(param1=5001))
        [enter] = [pb.RoomEnterMsg.FromString(p.body) for p in await b.idle() if p.code == 21]
        assert sorted(p.playerId for p in enter.player) == sorted([g.user_id, b.user_id])
        [joined] = [pb.RoomEnterMsg.FromString(p.body) for p in await g.idle() if p.code == 21]
        assert [p.playerId for p in joined.player] == [b.user_id]

        b.client.send(5025, pb.RoomExitMsg())
        [mine] = [pb.CampaignExitMsg.FromString(p.body) for p in await b.idle() if p.code == 22]
        [theirs] = [pb.CampaignExitMsg.FromString(p.body) for p in await g.idle() if p.code == 22]
        assert mine.playerId == theirs.playerId == b.user_id and mine.result == 1
        bs = g.server.online.get(b.user_id)
        assert bs is not None and bs.campaign is None


async def test_dois_jogadores_batem_no_mesmo_chefe_e_um_so_da_o_ultimo_golpe(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        b = await g.join("outro")
        sessions = [g.server.online.get(x.user_id) for x in (g, b)]
        for session in sessions:
            assert session is not None and session.snapshot is not None
            session.snapshot.character.grades = 20
        for game in (g, b):
            await game.idle()
            game.client.send(8258, pb.WorldBossMsg(param1=5001))
            await game.idle()
        ctx = sessions[0].ctx  # type: ignore[union-attr]
        pool = ctx.bosses.pools[5001]
        pool.fight.total_hp = 150  # morre em poucos golpes

        async def fight(game: object) -> list[object]:
            game.client.send(5125, pb.CampaignReqMsg(paraInt1=500102))  # type: ignore[attr-defined]
            got = await game.until(157)  # type: ignore[attr-defined]
            prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
            assert prepare.battleType == 17
            return await game.fight(prepare)  # type: ignore[attr-defined,no-any-return]

        reports = await asyncio.gather(fight(g), fight(b))
        assert pool.hp == 0 and pool.fight.killer_id in (g.user_id, b.user_id)
        assert sum(w.wound for w in pool.wounds.values()) == 150
        for got in reports:
            [report] = [pb.BattleReportMsg.FromString(p.body) for p in got if p.code == 4103]  # type: ignore[attr-defined]
            assert report.battleResult == 1

        async def stored(uow: object) -> tuple[object, list[object]]:
            fight = await uow.world_boss.fight(5001, pool.fight.opened_at)  # type: ignore[attr-defined]
            return fight, await uow.world_boss.wounds(fight.id)  # type: ignore[attr-defined]

        fight_row, wounds = await ctx.characters.read(stored)
        assert fight_row.killer_id == pool.fight.killer_id  # type: ignore[attr-defined]
        assert sum(w.wound for w in wounds) == 150  # type: ignore[attr-defined]
        assert fight_row.settled and fight_row.next_hp == 225  # type: ignore[attr-defined]  # morreu: +50%

        for game, got in zip((g, b), reports, strict=True):
            got = [*got, *await game.idle()]  # type: ignore[attr-defined]
            codes = [p.code for p in got]  # type: ignore[attr-defined]
            assert codes.count(4203) == 1 and codes[-1] == 4203 and codes[-3:-1] == [22, 4165], codes  # #3241-#3251
            texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 83]  # type: ignore[attr-defined]
            assert any("struck the final blow to defeat the World Boss Bloodfang" in t and "800,000 Gold!" in t
                       for t in texts)  # fmt: skip
            assert any(t.startswith("The top 3 players in terms of total damage dealt to Boss Bloodfang are:")
                       for t in texts)  # fmt: skip

        killer = pool.fight.killer_id

        async def killer_mails(uow: object) -> tuple[list[str], int]:
            mails = await uow.mails.by_receiver(killer)  # type: ignore[attr-defined]
            annexes = await uow.mails.annexes([m.id for m in mails])  # type: ignore[attr-defined]
            return [m.title for m in mails], sum(a.count for a in annexes if a.template_id == -100)

        titles, _ = await ctx.characters.read(killer_mails)
        # um correio por prêmio (#3260); o último golpe (800 mil no 5001, #3234) vai direto, sem correio
        assert "World Boss Award: Apollo Prize" in titles and "World Boss Award: Lucky Prize" not in titles
        killer_session = next(x for x in sessions if x is not None and x.player_id == killer)
        assert killer_session.snapshot is not None and killer_session.snapshot.character.gold >= 800_000

        g.client.send(8258, pb.WorldBossMsg(param1=5001))  # morto: não entra mais hoje
        assert [p.code for p in await g.idle()] == [ALERT]
        g.client.send(8271)
        [state] = [pb.WorldBossStateMsg.FromString(p.body) for p in await g.idle() if p.code == 4182]
        assert _states(state) == [(5001, 2), (5003, 1)]


async def test_janela_fecha_no_relogio_e_tira_todos(tmp_path: Path) -> None:
    clock = FakeClock(OPEN_5001)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.grades = 20
        await g.idle()
        g.client.send(8258, pb.WorldBossMsg(param1=5001))
        await g.idle()
        clock.advance(60 * 60)  # 12:40: passou do StopTime 12:35
        g.client.send(20008)
        codes = [p.code for p in await g.idle()]
        assert 4203 in codes and 22 in codes and session.campaign is None
        pool = session.ctx.bosses.pools[5001]
        assert pool.fight.settled and pool.fight.next_hp == 2_000_000  # não morreu: -10%, mas não abaixo do Live


async def test_morre_no_sexto_golpe_e_revive_pagando(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        ch = session.snapshot.character
        ch.grades, ch.point, ch.gift_token = 20, 20, 0
        # 759 "Participate in a World BOSS Battle" (tipo 40) e 183 "Instant Battle" (tipo 66, o 8264 pago)
        join, instant = Quest(g.user_id, 759, datetime.now(UTC)), Quest(g.user_id, 183, datetime.now(UTC))
        damage = Quest(g.user_id, 762, datetime.now(UTC))  # tipo 41 "Total Damage Dealt"
        session.snapshot.quests.extend([join, instant, damage])
        await g.server.services.characters.save(join, instant, damage)
        await g.idle()
        g.client.send(8258, pb.WorldBossMsg(param1=5001))
        await g.idle()
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=500102))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        got = await g.fight(prepare)
        got += await g.idle()
        [report] = [pb.BattleReportMsg.FromString(p.body) for p in got if p.code == 4103]
        assert report.battleResult == 2 and report.goldBonus == report.strategyBonus > 0  # o dano paga
        [dead] = [pb.PlayerStateListMsg.FromString(p.body) for p in got if p.code == 4175]
        assert (dead.playerState[0].state, dead.playerState[0].leftTime) == (1, 30_000)
        assert 112 in [p.code for p in got] and (join.progress, instant.progress) == (1, 0)  # a luta conta o tipo 40
        assert damage.progress > 0  # o dano da luta conta o tipo 41

        g.client.send(5125, pb.CampaignReqMsg(paraInt1=500102))  # morto: sem luta
        assert [p.code for p in await g.idle()] == [4175]

        g.client.send(8264, pb.PayTypeMsg(payType=1))
        got = await g.idle()
        [alive] = [pb.PlayerStateListMsg.FromString(p.body) for p in got if p.code == 4175]
        assert alive.playerState[0].state == 0 and ch.point == 5
        assert 112 in [p.code for p in got] and instant.progress == 1  # o reviver pago conta o tipo 66
        codes = [p.code for p in got]
        assert codes.index(4434) < codes.index(4175) < codes.index(157)  # #8629-#8638: a luta começa na hora
        g.client.send(8264, pb.PayTypeMsg(payType=1))  # vivo: aviso, nada cobrado
        assert [p.code for p in await g.idle()] == [ALERT] and ch.point == 5 and instant.progress == 1


async def test_campanha_que_nao_e_chefe_nem_pedreira_diz_indisponivel(tmp_path: Path) -> None:
    """8258 com uma campanha que existe mas não é chefe nem pedreira (a 6001 entra: test_pedreira_6001.py): aviso de
    indisponível, sem cobrar nada, não o "inválido" de id que não existe."""
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        g.client.send(8258, pb.WorldBossMsg(param1=1001))
        [alert] = await g.idle()
        assert alert.code == ALERT
        assert pb.ChatChannelMsg.FromString(alert.body).encodeMsg == "This action is not available now."


async def test_corpo_vazio_nao_derruba_a_sessao(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(BEFORE_OPEN)) as g:
        c = g.client
        for code in (8258, 8259, 8264, 8470):
            c.send(code)  # corpo vazio: 8258 recusa (id 0), 8259 não tem resposta
        c.send(8271)
        assert [p.code for p in await g.idle()] == [ALERT, ALERT, ALERT, 4182, 4451, 4637, 462, 4741, 4683, 4685]


async def test_relogio_manda_4182_quando_o_chefe_abre(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 5, 21, 11, 30, tzinfo=UTC))  # 11:30: 5001 abre às 11:35
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        c = g.client
        c.send(8271)
        [state] = [pb.WorldBossStateMsg.FromString(p.body) for p in await g.idle() if p.code == 4182]
        assert _states(state) == [(5001, 1), (5003, 1)]
        c.send(20008)
        assert 4182 not in [p.code for p in await g.idle()]  # nada mudou
        clock.advance(6 * 60)
        c.send(20008)
        [state] = [pb.WorldBossStateMsg.FromString(p.body) for p in await g.idle() if p.code == 4182]
        assert _states(state) == [(5001, 0), (5003, 1)]


async def test_janela_do_chefe_vida_compartilhada_e_premios(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(OPEN_5001)) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None
        ctx, now = session.ctx, OPEN_5001
        pool = await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, 5001, now)
        assert pool is not None and pool.fight.id is not None
        assert pool is await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, 5001, now)  # a mesma janela
        assert await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, 5003, now) is None  # fechado
        assert pool.hp == pool.fight.total_hp == 2_000_000  # o Live do herói 2002

        assert pool.hit(1, "A", 6, 1_500_000, now) == 1_500_000
        assert pool.inspire() == 3
        assert pool.hit(2, "B", 7, 900_000, now) == 500_000  # só o que resta
        assert pool.hit(1, "A", 6, 10, now) == 0  # morto
        assert (pool.hp, pool.fight.killer_id) == (0, 2)
        assert boss_fight.next_hp(pool.boss, pool.fight) == 3_000_000  # morreu: +50%
        # visto: 5 abates = 2M x 1,5^5 = 15.187.500 (5001, 27/10); 7 = 34.171.875 (5003, 26/10)
        hp, five = 2_000_000, False
        for _ in range(7):
            pool.fight.total_hp = hp
            hp = boss_fight.next_hp(pool.boss, pool.fight)
            if hp == 15_187_500:
                five = True
        assert five and hp == 34_171_875

        got = boss_fight.end_rewards(ctx.world, pool)
        # classes diferentes (6 % 3, 7 % 3): os dois são o 1º da classe; 75% e 25% passam do maior degrau
        assert got[1] == (300_000 + 180_000, 300_000 + 180_000)
        assert got[2] == (300_000 + 180_000 + 800_000, 300_000 + 180_000)
        kinds = [(p.character_id, p.kind) for p in boss_fight.end_prizes(ctx.world, pool)]
        assert kinds == [(1, "apollo"), (2, "apollo"), (1, "warrior"), (2, "warrior"), (2, "lucky")]
        pool.fight.killer_id = 0
        assert boss_fight.end_rewards(ctx.world, pool) == {}  # "Defeating the World Boss earns": vivo, nada


async def test_barreira_antes_de_nascer_e_o_nascimento_no_relogio(tmp_path: Path) -> None:
    """Visto #1411-#1414 e #1669-#1670: antes de nascer, a barreira responde 111 e empurra (4126); no nascimento, a
    barreira some (128) e o 83 vai a todos."""
    clock = FakeClock(datetime(2026, 5, 21, 11, 33, tzinfo=UTC))  # o mapa abriu 11:32, nasce 11:36
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        session.snapshot.character.grades = 20
        await g.idle()
        g.client.send(8258, pb.WorldBossMsg(param1=5001))
        [nodes] = [pb.CampaignNodeListMsg.FromString(p.body) for p in await g.idle() if p.code == 127]
        assert [n.state for n in nodes.node if n.campDataId == 500104] == [1]  # a barreira ainda está lá
        for camp in (500104, 500102):
            g.client.send(5125, pb.CampaignReqMsg(paraInt1=camp))
            got = await g.idle()
            assert [p.code for p in got] == [ALERT, 4126]
            assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "The current battle hasn't started yet."
            stand = pb.StandPosMsg.FromString(got[1].body)
            assert (stand.posX, stand.posY) == (45, 46)

        clock.advance(3 * 60 + 30)  # 11:36:30
        g.client.send(20008)
        got = await g.idle()
        chat = [pb.ChatChannelMsg.FromString(p.body) for p in got if p.code == 83]
        assert "World Boss Bloodfang will appear in 1 minutes! Get ready for the battle of a lifetime!" in [
            m.encodeMsg for m in chat]  # fmt: skip
        [spawn] = [m for m in chat if m.encodeMsg == "World Boss Bloodfang has spawned!"]
        assert spawn.channel == 12 and spawn.isCenterTip and spawn.isBigTip
        [gate] = [pb.CampaignNodeUpdateMsg.FromString(p.body) for p in got if p.code == 128]
        assert (gate.nodeId, gate.nodeState) == (4, 8)
        assert session.campaign is not None and session.campaign.nodes[500104]["state"] == 8
        g.client.send(20008)  # o mesmo marco não sai duas vezes
        assert 128 not in [p.code for p in await g.idle()]


def test_vida_cai_se_o_chefe_nao_morre() -> None:
    boss = WorldBoss(5001, 2001, 2145, 40, 30, 40, 70, 2_000_000, 1_000_000, 600, 20, 10, 6, 30, 5, 10_000_000,
                     1_500_000, 0)  # fmt: skip
    fight = WorldBossFight(5001, OPEN_5001, 1_050_000)
    assert boss_fight.next_hp(boss, fight) == 1_000_000  # -10%, sem passar do mínimo


def test_todo_opcode_da_lista_tem_handler() -> None:
    for code in WORLD_BOSS_OPCODES:
        assert router.get(code) is not None, code
