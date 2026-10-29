"""Mensagens que o oficial manda e o servidor não mandava: 3842, 4610, 4270, 4470, 4388, 4269 e 4549."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.game.harness import logged_in
from wartune_server.domain.models import Item
from wartune_server.game import arena, rules
from wartune_server.game import battlefield as bf
from wartune_server.game import events as ev
from wartune_server.game.builders import login as b
from wartune_server.game.handlers import login, stars, warfield
from wartune_server.game.rooms import PVE
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

TRIAL_CARD = 2031201
IN_4005 = datetime(2026, 10, 27, 15, 10, tzinfo=UTC)
IN_4007 = datetime(2026, 10, 27, 17, 10, tzinfo=UTC)
IN_MINE = datetime(2026, 10, 27, 19, 45, tzinfo=UTC)  # carrinho: 19:30 a 20:00


def _session(g):  # type: ignore[no-untyped-def]
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


async def test_3842_relogin_avisa_a_sessao_antiga(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        await g.idle()
        await g.connect()
        old = g.client
        while data := await old.reader.read(65536):  # a antiga recebe o 3842 e é fechada
            old.decoder.feed(data)
        got = []
        while (p := old.decoder.next_packet()) is not None:
            got.append(p)
        assert got[-1].code == 3842
        assert pb.GatewayMsg.FromString(got[-1].body).notifyMsg == login.LOGIN_OTHER_TEXT


async def test_4610_montaria_vip_no_cartao_e_no_vencimento(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        s = _session(g)
        snap = s.snapshot
        rules.systems(snap).mount_template = 1000  # com montaria (o tutorial, sem ela, não recebe)
        card = Item(g.user_id, TRIAL_CARD, pos=0)
        snap.items.append(card)
        await g.server.services.characters.save(card)
        await g.idle()
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        got = await g.idle()
        codes = [p.code for p in got]
        assert codes.index(4610) < codes.index(111) < codes.index(4410)  # 191924 #7255-#7258
        msg = pb.SimplePropertyMsg.FromString(next(p.body for p in got if p.code == 4610))
        assert (msg.param1, msg.param7) == (1116, True)

        g.client.send(8530)  # ainda VIP: nada
        assert 4610 not in [p.code for p in await g.idle()]
        ev.peek(snap, "vip").text = b.fmt_time(s.ctx.clock.now() - timedelta(days=1))  # type: ignore[union-attr]
        g.client.send(8530)
        got = await g.idle()
        assert [p.code for p in got][:3] == [4427, 4610, 4426]  # 232017 #18-#20
        assert pb.SimplePropertyMsg.FromString(got[1].body).param7 is False
        g.client.send(8530)  # só uma vez
        assert 4610 not in [p.code for p in await g.idle()]


async def test_4270_entrada_recusada_manda_a_sala(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        other = await g.join("outro")
        other.client.send(5023, pb.RoomReqMsg(roomType=PVE, password="abc"))
        room = pb.RoomMsg.FromString((await other.until(12))[-1].body)
        await g.idle()
        g.client.send(5024, pb.RoomReqMsg(roomId=room.roomId, roomType=PVE, password="errada"))
        got = await g.idle()
        assert [p.code for p in got] == [4270]
        assert pb.RoomMsg.FromString(got[0].body).roomId == room.roomId


async def test_4470_lista_vazia_depois_da_loja_misteriosa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001) as g:
        _session(g).snapshot.character.grades = 30
        await g.idle()
        g.client.send(8483, pb.ShopFreshReqMsg(isButton=False))
        got = await g.idle()
        assert [p.code for p in got] == [4384, 4470] and got[1].body == b""  # 232017 #3056-#3057


async def test_4388_estrela_de_qualidade_4(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async with logged_in(tmp_path, novice=30001) as g:
        s = _session(g)
        s.snapshot.character.gold = 10**6
        row = s.ctx.templates.get("starTempInfos", 404)
        assert row is not None
        monkeypatch.setattr(stars, "roll", lambda *a, **k: row)
        await g.idle()
        g.client.send(8269, pb.StarRandReqMsg(site=0))
        got = await g.idle()
        codes = [p.code for p in got]
        assert codes.index(4388) < codes.index(4180)
        sns = pb.SnsRspMsg.FromString(next(p.body for p in got if p.code == 4388))
        assert (sns.type, sns.data, len(sns.md5)) == (2, "4", 32)


async def test_4269_entrega_no_campo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4007)) as g:
        s = _session(g)
        s.snapshot.character.grades = 35
        g.client.send(8332, pb.WorldBossMsg(param1=4007))
        await g.idle()
        g.client.send(5125, pb.CampaignReqMsg(paraInt1=4007006, paraBool1=True))
        await g.idle()
        g.client.send(5032, pb.CallBackReqMsg(mapId=4007, nodeId=4007006, cmd=2))
        await g.idle()
        s.ctx.warfields.fields[4007].mark(g.user_id).carry = "superior"  # a qualidade é sorteada na coleta
        g.client.send(5033, pb.CampaignReqMsg(paraInt1=4007, paraInt2=4007012, paraBool1=True))
        got = await g.idle()
        assert got[-1].code == 4269
        movie = pb.WarMovieMsg.FromString(got[-1].body)
        assert (movie.score, movie.geste, movie.isAdd, movie.userId) == (30, 3, True, g.user_id)


async def test_8334_pvp_no_campo_com_4494_e_4269(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    copy = arena.copy_hero  # cópia do alvo com 1 de vida: a luta acaba no primeiro golpe
    monkeypatch.setattr(arena, "copy_hero", lambda *a: copy(*a) | {"maxHp": 1, "initHp": 1, "hp": 1})
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_4005)) as g:
        games = [g]
        for i in range(2):
            if i:  # o segundo entra depois (como no teste do 4185)
                games.append(await g.join("outro"))
            game = games[-1]
            _session(game).snapshot.character.grades = 35
            await game.idle()
            game.client.send(8332, pb.WorldBossMsg(param1=4005))
            await game.idle()
        other = games[1]
        await g.idle()
        s = _session(g)
        field = s.ctx.warfields.fields[4005]
        field.mark(other.user_id).score = 100
        g.client.send(8334, pb.WarFieldAttackMsg(userId=other.user_id, defenceServerName="x"))
        got = await g.idle()
        assert got and got[-1].code == 157, [p.code for p in got]
        start = pb.CrossArmyListMsg.FromString(next(p.body for p in got if p.code == 4494))
        assert {a.state for a in start.armyList} == {2} and len(start.armyList) == 2
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert prepare.battleType == 32
        s.battle.set_auto(True)  # o herói age sozinho
        g.client.send(10007, pb.LoadOverMsg(armyId=g.user_id, battleId=prepare.battleId))
        mine = await g.until(4103) + await g.idle()
        theirs = await other.idle()
        end = [pb.CrossArmyListMsg.FromString(p.body) for p in theirs if p.code == 4494][-1]
        assert {a.state for a in end.armyList} == {0}
        m1 = pb.WarMovieMsg.FromString(next(p.body for p in mine if p.code == 4269))
        m2 = pb.WarMovieMsg.FromString(next(p.body for p in theirs if p.code == 4269))
        assert m1.isAdd != m2.isAdd
        loser = other if m1.isAdd else g
        assert _session(loser).campaign.pos == bf.CAMP[field.mark(loser.user_id).team]
        if m1.isAdd:  # venceu: o outro perde 15 dos 100 e ele ganha 20 + 100 // 20
            assert m1.score == 25 and field.mark(other.user_id).score == 85
            assert pb.SnsRspMsg.FromString(next(p.body for p in mine if p.code == 4388)).type == 4


async def test_4549_mina_abre_e_fecha(tmp_path: Path) -> None:
    clock = FakeClock(IN_MINE)
    async with logged_in(tmp_path, novice=30001, clock=clock) as g:
        s = _session(g)
        assert s.mine_open is True  # o login dentro da janela já mandou o true
        await g.idle()
        warfield.push_states(s)
        assert await g.idle() == []  # sem mudança
        clock.advance(20 * 60)  # 20:05
        warfield.push_states(s)
        got = [p for p in await g.idle() if p.code == 4549]
        assert len(got) == 1 and pb.GuildMsg.FromString(got[0].body).param5 is False
