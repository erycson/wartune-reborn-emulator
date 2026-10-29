"""Lote 2 da auditoria: limites, tetos e horários (um teste por item)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

from tests.game.harness import Game, logged_in
from tests.game.test_mall import _put, _sell
from tests.game.test_masmorra_1001 import codes, enter
from tests.game.test_masmorra_1002_pedreira import arrive, text
from wartune_server.domain import gameday
from wartune_server.domain.models import Item, PlayerSnapshot
from wartune_server.domain.world import ExpRate
from wartune_server.game import events as ev
from wartune_server.game import mall as market
from wartune_server.game import titles, worldboss
from wartune_server.game.builders import login as b
from wartune_server.game.handlers import guildwar, vip
from wartune_server.game.handlers.items import ITEM_EXP_FULL
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

NOW = datetime(2026, 10, 27, 20, 0, tzinfo=UTC)
EXP_BOOK = 2030701  # Lvl. 1 EXP Book: EXP+500
HORN = 208002  # Bullhorn (Large), o item que o test_mall anuncia


def _s(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _snap(g: Game) -> PlayerSnapshot:
    snap = _s(g).snapshot
    assert snap is not None
    return snap


def _setting(g: Game, key: str, value: object) -> None:
    world = g.server.services.world
    object.__setattr__(world, "settings", MappingProxyType({**world.settings, key: value}))


async def test_1_teto_diario_de_exp_de_itens(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(NOW)) as g:
        _setting(g, "item_exp_daily", 700)
        snap = _snap(g)
        book = Item(g.user_id, EXP_BOOK, pos=0, count=3)
        snap.items.append(book)
        await g.server.services.characters.save(book)
        gp = snap.character.total_gp
        for _ in range(2):
            g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
            await g.idle()
        assert snap.character.total_gp == gp + 700  # 500 e depois só os 200 que faltam
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        got = await g.idle()
        assert [text(p) for p in got if p.code == 111] == [ITEM_EXP_FULL] and book.count == 1


async def test_2_colheita_espera_a_animacao(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=25500, clock=clock) as g:
        g.client.send(8258, pb.WorldBossMsg(param1=6001))
        await g.idle()
        await arrive(g, 600108)
        g.client.send(5032, pb.CallBackReqMsg(mapId=6001, nodeId=600108, cmd=2))
        assert await g.idle() == []  # colado no 143: pedido forjado
        clock.advance(5)
        g.client.send(5032, pb.CallBackReqMsg(mapId=6001, nodeId=600108, cmd=2))
        assert 111 in codes(await g.idle())
        g.client.send(5032, pb.CallBackReqMsg(mapId=6001, nodeId=600108, cmd=2))
        assert await g.idle() == []  # a próxima também espera


async def test_3_sem_estamina_avisa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=25500) as g:
        _snap(g).character.weary = 19
        got = await enter(g)
        assert codes(got) == [111] and text(got[0]) == "Insufficient Stamina"


def test_4_chefe_com_janela_que_cruza_a_meia_noite() -> None:
    row = {"OpenTime": "23:30", "StopTime": "00:30"}

    def at(day: int, hour: int, minute: int) -> datetime:
        return datetime(2026, 10, day, hour, minute, tzinfo=gameday.GAME_TZ).astimezone(UTC)

    assert worldboss.state(row, at(27, 23, 0)) == worldboss.BEFORE
    assert worldboss.state(row, at(27, 23, 40)) == worldboss.OPEN
    assert worldboss.state(row, at(28, 0, 10)) == worldboss.OPEN  # depois da meia-noite, ainda a de ontem
    assert worldboss.state(row, at(28, 0, 40)) == worldboss.BEFORE  # fechou; a de hoje abre às 23:25
    assert worldboss.spawned(row, at(28, 0, 10))
    assert worldboss.window(row, at(27, 23, 40))[1] == at(28, 0, 30)


def test_5_evento_de_exp_so_na_hora_do_dia() -> None:
    rate = ExpRate(2, "2026-10-27 00:00:00", "2026-10-29 00:00:00", 20 * 3600, 22 * 3600, 1)
    world = SimpleNamespace(exp_rates=(rate,))

    def at(day: int, hour: int) -> datetime:
        return datetime(2026, 10, day, hour, 0, tzinfo=gameday.GAME_TZ).astimezone(UTC)

    assert ev.running_rates(world, at(28, 21)) == [rate]  # type: ignore[arg-type]
    assert ev.running_rates(world, at(28, 12)) == []  # type: ignore[arg-type]  # dentro das datas, fora da hora


async def test_6_vip_vencido_avisa(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        st = ev.state(_snap(g), "vip", NOW)
        st.text = b.fmt_time(NOW + timedelta(minutes=1))
        clock.advance(120)
        vip.notify_expired(g.server.online, NOW + timedelta(minutes=2), NOW + timedelta(minutes=3))
        assert await g.idle() == []  # venceu antes da rodada anterior
        vip.notify_expired(g.server.online, NOW, NOW + timedelta(minutes=2))
        info = pb.VipInfoMsg.FromString(next(p.body for p in await g.idle() if p.code == 4410))
        assert not info.isVip


async def test_7_vipgp_por_dia(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s, snap = _s(g), _snap(g)
        snap.character.point = 400
        g.client.send(8513, pb.VipOpenInfoMsg(days=31))
        await g.until(4416)
        gp = ev.peek(snap, "vip")
        assert gp is not None and gp.value == 10  # só o dia da compra
        clock.advance(3 * 86400)
        await vip.login_push(s)
        assert gp.value == 40
        clock.advance(60 * 86400)
        await vip.login_push(s)
        assert gp.value == 310  # 31 dias, nem um a mais


async def test_8_leilao_dorme_ate_o_fim(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        services, server = g.server.services, _snap(g).character.server_id
        assert await market.next_wait(services.characters, server, clock.now(), 60) == 60  # nada à venda
        sold = await _put(g, HORN, 1)
        g.client.send(8448, _sell(sold, hour=8))
        await g.until(4352)
        clock.advance(8 * 3600 - 7)
        assert await market.next_wait(services.characters, server, clock.now(), 60) == 7


async def test_9_titulo_de_lider_sai_do_anterior(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(NOW)) as g:
        s = _s(g)
        other = await g.join("rival")
        server = _snap(g).character.server_id
        guilds = {1: SimpleNamespace(chairman_id=g.user_id, server_id=server)}
        guilds[2] = SimpleNamespace(chairman_id=other.user_id, server_id=server)
        ctx = SimpleNamespace(
            guilds=SimpleNamespace(guilds=guilds), online=s.ctx.online, clock=s.ctx.clock, characters=s.ctx.characters
        )
        key = titles.KEYS[titles.GUILD_MASTER]
        await s.ctx.characters.save(*await guildwar._champion(ctx, 1))  # type: ignore[arg-type]
        assert ev.peek(_snap(g), key).value == 1  # type: ignore[union-attr]
        changed = await guildwar._champion(ctx, 2)  # type: ignore[arg-type]
        assert {(e.character_id, e.value) for e in changed} == {(g.user_id, 0), (other.user_id, 1)}
        assert ev.peek(_snap(g), key).value == 0  # type: ignore[union-attr]  # online: a linha da memória
