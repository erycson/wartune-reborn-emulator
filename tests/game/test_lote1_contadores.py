"""Lote 1 da auditoria: rankings e contadores (um teste por item)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import EventState, Item, PlayerSnapshot, PlayerSystems, Quest
from wartune_server.game import battlefield as bf
from wartune_server.game import events as ev
from wartune_server.game import fishing as fs
from wartune_server.game import maze as mz
from wartune_server.game import recover, rules, titles
from wartune_server.game.handlers import events as hev
from wartune_server.game.handlers import guildwar, offer, space, systems, tower, warfield
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def _s(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _snap(s: GameSession) -> PlayerSnapshot:
    assert s.snapshot is not None
    return s.snapshot


def _got(msg: pb.AppellsMsg) -> set[int]:
    return {a.appellId for a in msg.appells if a.isGet}


async def test_1_titulos_leem_contadores_e_rankings(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        snap = _snap(s)
        rows = list(s.ctx.templates.rows("AppellInfos"))
        wins = min((r for r in rows if r["CondtionType"] == titles.ARENA_WINS), key=lambda r: int(r["Para"]))
        top = next(r for r in rows if r["CondtionType"] == "15" and r["Para"] == "1")  # 1º no poder
        wid, tid = int(wins["TemplateId"]), int(top["TemplateId"])
        await hev.title_ranks(s)
        assert wid not in _got(hev.titles_msg(s))
        assert tid in _got(hev.titles_msg(s))  # sozinho no servidor: 1º no ranking de poder
        titles.count(snap, titles.ARENA_WINS, NOW, int(wins["Para"]))
        assert wid in _got(hev.titles_msg(s))


async def test_2_order_do_labirinto_no_4373_do_login(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        snap = _snap(s)
        st = mz.store(snap, mz.Tower(record=5, record_at=NOW.isoformat()), NOW)
        await s.ctx.characters.save(st)
        s.maze_order.clear()
        listed = await tower.login_list(s)
        assert [t.order for t in listed.towerInfo] == [1]


def test_3_ranking_semanal_da_pesca_lista_quem_tem_zero_no_fim() -> None:
    week = fs.parse("", NOW).week

    def row(cid: int, score: int) -> EventState:
        return EventState(cid, fs.KEY, NOW, text=json.dumps(asdict(fs.Fisher(score=score, week=week))))

    states = [row(1, 0), row(2, 7), row(3, 0)]
    assert [c for c, _ in fs.weeks(states, NOW)] == [2]
    assert [c for c, _ in fs.weeks(states, NOW, zeros=True)] == [2, 1, 3]


async def test_4_guerra_de_guildas_soma_vitorias_e_derrotas(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        snap = _snap(s)
        await guildwar._prize(s, True)
        await guildwar._prize(s, False)
        await guildwar._prize(s, True)
        assert ev.peek(snap, titles.GUILD_WAR_WINS).value == 2  # type: ignore[union-attr]
        assert ev.peek(snap, titles.GUILD_WAR_LOSSES).value == 1  # type: ignore[union-attr]
        assert titles.counters(snap)[titles.GUILD_WAR_FIRST] == 2  # o mesmo contador do "Guild Guardian"


async def test_5_painel_conta_a_mina_e_a_recompensa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        _snap(s).character.grades = 40
        g.client.send(8633)
        got = await g.idle()
        [info] = pb.ClickDatasRspMsg.FromString(next(p.body for p in got if p.code == 4413)).info
        assert (info.keys, info.keyData) == ("minefield", 1)
        await hev.count_click(s, "reward")
        g.client.send(8518)
        got = await g.until(4412)
        keys = {i.keys: i.keyData for i in pb.ClickDatasRspMsg.FromString(got[-1].body).info}
        assert keys == {"minefield": 1, "reward": 1}


async def test_6_anel_entrega_com_as_condicoes_contadas(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        snap = _snap(s)
        snap.character.grades = 40
        counted = {offer.ENCHANT, offer.SOCKET, offer.ASTRAL, offer.GUILD_OFFER, offer.SYNTH, offer.BALEN_BUY}
        tid, conds = next(
            (int(r["TemplateId"]), c)
            for r in s.ctx.templates.find("RewardTemps", Type=offer.RING)
            if (c := offer._conditions(s, int(r["TemplateId"]))) and all(int(x["CondictionType"]) in counted for x in c)
        )
        ring = ev.daily(snap, "ring", NOW)
        ring.text = json.dumps({"t": tid})
        g.client.send(8729)  # nada contado: só o estado
        assert 4614 in [p.code for p in await g.idle()] and json.loads(ring.text)["t"] == tid
        for c in conds:
            await offer.progress(s, int(c["CondictionType"]), int(c["Para2"]))
        await g.idle()
        g.client.send(8729)
        got = await g.until(4614)
        assert pb.RewardUpdatedRspMsg.FromString(got[-1].body).reward[0].isComplete
        assert ring.value == 1 and not ring.text


async def test_7_devocao_27_ao_entrar_no_campo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(datetime(2026, 10, 27, 15, 10, tzinfo=UTC))) as g:
        s = _s(g)
        _snap(s).character.grades = 35
        g.client.send(8332, pb.WorldBossMsg(param1=4005))
        got = await g.idle()
        leed = pb.LeedUpdatedRspMsg.FromString(next(p.body for p in got if p.code == 4152))
        assert [(x.templateId, x.isComplete) for x in leed.leed] == [(warfield.FIELD_LEED, True)]


async def test_8_recuperar_exp_le_a_participacao_de_ontem(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        snap = _snap(s)
        snap.character.grades = 40
        snap.character.reset_day = "2026-10-26"
        yesterday = NOW - timedelta(days=1)
        for key, value in (("offer:count", 20), ("hangup", 60), ("leed:18", 1), ("leed:23", 1), ("spire", 1)):
            st = ev.state(snap, key, yesterday)
            st.value, st.updated_at = value, yesterday
        left = recover.pending(snap, NOW) if False else json.loads(recover.build(snap, s.ctx.templates, NOW).text)
        for son in (recover.OFFER, recover.ALTAR, recover.BOSS, recover.CATACOMBS, recover.SPIRE):
            assert str(son) not in left, son  # fez tudo ontem: nada a recuperar
        assert str(recover.ARENA) in left  # o coliseu ficou sem fazer


def test_9_bau_da_guilda_enche_pela_participacao_na_guerra() -> None:
    from collections import defaultdict

    sides = {1: SimpleNamespace(guild_id=10), 2: SimpleNamespace(guild_id=20)}
    war = SimpleNamespace(winner=1, side=lambda n: sides[n])
    ctx = SimpleNamespace(guilds=SimpleNamespace(guilds={10: object(), 20: object()}, box=defaultdict(list)))
    got = guildwar._treasures(ctx, war, {1: 3, 2: 3})  # type: ignore[arg-type]
    assert sorted((i.consortia_id, i.template_id, i.count) for i in got) == [
        (10, guildwar.TREASURE, 3),
        (20, guildwar.TREASURE, 1),
    ]


async def test_10_repetivel_concluida_vai_no_112_do_login(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        tid = next(
            int(r["TemplateId"])
            for r in s.ctx.templates.rows("QuestTemps")
            if rules.is_repeat(s.ctx.templates, int(r["TemplateId"]))
        )
        await s.ctx.characters.save(Quest(g.user_id, tid, NOW, completed=True, completed_at=NOW))
        sent: list[object] = []
        real = GameSession.send

        def spy(self: GameSession, code: int, msg: object | None = None, *a: object, **k: object) -> None:
            if code == 112:
                sent.append(msg)
            real(self, code, msg, *a, **k)  # type: ignore[arg-type]

        monkeypatch.setattr(GameSession, "send", spy)
        await g.connect()
        listed = {i.templateId for m in sent for i in m.quest}  # type: ignore[attr-defined]
        assert tid in listed


def test_11_patrulha_conta_a_conversa_sem_posicao() -> None:
    node = {"MasterType": space.PATROL, "PosX": "999", "PosY": "999", "HandlerRange": "0"}
    far = SimpleNamespace(space_pos=(1, 1))
    assert space._near(far, node)  # type: ignore[arg-type]
    assert not space._near(far, node | {"MasterType": "2"})  # type: ignore[arg-type]


async def test_12_mina_alcancavel_fora_da_janela_conta_a_503(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        snap = _snap(s)
        snap.character.grades = 40
        rush = Quest(g.user_id, 503, NOW)  # Amethyst Rush (condição 86)
        snap.quests.append(rush)
        await space._transfer(s, {"MoveToMapId": str(bf.MINE), "Param3": "0"})
        assert s.campaign is not None and s.campaign.warfield == bf.MINE
        await warfield.confirm(s, pb.CampaignReqMsg(paraBool1=True, paraInt2=bf.MINE * 100 + bf.CART_NODE))
        assert s.ctx.warfields.carts[g.user_id].quality == bf.CART_NORMAL  # 12:00: o carrinho comum
        await warfield.callback(s, pb.CallBackReqMsg(cmd=2, nodeId=bf.MINE * 100 + bf.PICK_NODE))
        assert s.ctx.warfields.carts[g.user_id].picks == 1
        assert rush.progress == 1


def test_13_campo_vence_o_lado_com_mais_pontos() -> None:
    field = bf.Field(4005, NOW)
    a, b = field.mark(1), field.mark(2)
    assert (a.team, b.team) == (bf.TEAM, bf.ENEMY)  # quem chega entra no lado com menos gente
    assert field.winner() is None  # 0 a 0
    b.score = 30
    a.score = 10
    assert field.winner() == bf.ENEMY and field.count(bf.TEAM) == 1


def test_14_cartas_ganhas_entram_na_colecao() -> None:
    import asyncio

    from wartune_server.templates.repository import GameTemplates

    templates = asyncio.run(GameTemplates.load(Path("data/templates/tempinfos.xml")))
    sy = PlayerSystems(1)
    first, again, junk = Item(1, 6000001, count=1), Item(1, 6000001, count=3), Item(1, 208001, count=5)
    assert systems.gain_cards(sy, templates, [first, junk]) == [first]
    assert systems.cards(sy)[10001] == [1, 0, 0]  # a primeira cópia abre a carta
    assert systems.gain_cards(sy, templates, [again]) == []  # repetida fica na mochila para o op 3
    assert systems.cards(sy)[10001] == [1, 0, 0]


async def test_15_titulos_de_ranking_proprio_chefe_e_lider(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        snap = _snap(s)
        rows = {(r["CondtionType"], r["Para"]): int(r["TemplateId"]) for r in s.ctx.templates.rows("AppellInfos")}
        honor, charm, blow, master = (
            rows[("13", "1")],
            rows[("20", "1")],
            rows[("11", "5001,5002,5003")],
            rows[("12", "1")],
        )
        await hev.title_ranks(s)
        assert {honor, charm, blow, master} & _got(hev.titles_msg(s)) == set()  # 0 pontos não entra no ranking
        snap.character.geste = 10
        titles.count(snap, titles.BOSS_BLOW, NOW)
        await hev.title_ranks(s)
        guild = SimpleNamespace(chairman_id=g.user_id, server_id=snap.character.server_id)
        ctx = SimpleNamespace(
            guilds=SimpleNamespace(guilds={7: guild}),
            online=s.ctx.online,
            clock=s.ctx.clock,
            characters=s.ctx.characters,
        )
        [st] = await guildwar._champion(ctx, 7)  # type: ignore[arg-type]
        assert st.value == 1
        got = _got(hev.titles_msg(s))
        assert {honor, blow, master} <= got and charm not in got
        assert ev.peek(snap, titles.RANK_KEYS[titles.HONOR_RANK]).value == 10  # type: ignore[union-attr]


async def test_16_apprehend_abre_a_luta_com_o_npc(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        g.client.send(8298, pb.RewardArrestMsg(condictionType=offer.CAPTURE, param1=1))  # herói fora das condições
        await g.idle()
        assert s.battle is None
        g.client.send(8298, pb.RewardArrestMsg(condictionType=offer.CAPTURE, param1=20000))  # Claren the Swordsman
        got = await g.until(157)
        assert s.battle is not None and got[-1].code == 157
