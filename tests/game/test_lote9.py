"""Lote 9 da auditoria: campo minado (atividade 111), privilégios VIP conferidos um a um e os soldados especiais
9001-9008 da carta 203 tipo 9 no castelo. Os outros itens do lote estão em test_lote9_trilhas.py (Gods Descent e
Sky Trails), test_lote9_mundo.py (buff/dublê do chefe, Master Treasure Thief, coleta no espaço) e
test_lote9_cruzado.py (assistir batalha, entre servidores local); o PK de animais (8525) em
test_lote6_mapa.py::218."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import logged_in
from tests.game.test_heroi_exercito import snap_of
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import EventState, Pawn
from wartune_server.game import events as ev
from wartune_server.game import fam, outer_city, rankings, server_state
from wartune_server.game.handlers import vip
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
IN_MINE = datetime(2026, 10, 27, 19, 45, tzinfo=UTC)


async def test_campo_minado_conta_a_atividade_111(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []
    monkeypatch.setattr(ev, "count", lambda snap, cat, kind, now, n=1: seen.append(kind) or [])
    async with logged_in(tmp_path, novice=30001, clock=FakeClock(IN_MINE)) as g:
        snap_of(g).character.grades = 30
        g.client.send(8633)
        assert 4548 in [p.code for p in await g.idle()]
        assert seen == [ev.MINEFIELD] and ev.COUNTED[ev.MINEFIELD] is False  # "During the event": o período


async def test_cada_privilegio_vip_tem_onde_vale(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        kinds = {int(r["type"]) for r in s.ctx.templates.rows("VipPrerogativeTempInfos")}
        assert kinds == set(vip.PRIVILEGES)


async def test_soldados_9001_9008_no_exercito_e_na_luta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = snap_of(g)
        a, b = Pawn(snap.character.id or 0, 9001), Pawn(snap.character.id or 0, 9003)
        a.castle_count = b.castle_count = 50
        snap.pawns.extend([a, b])
        await g.server.services.characters.save(a, b)
        g.client.send(5156, pb.ArmyPawnInfoMsg(tempateId=9003, ownPawns=10))  # o segundo, não o primeiro do "// 100"
        await g.idle()
        assert (a.army_count, b.army_count, b.castle_count) == (0, 10, 40)
        g.client.send(5158, pb.ArmyPawnInfoMsg(tempateId=9003))  # sem NextLevelTemplateId: não evolui
        await g.idle()
        assert b.template_id == 9003
        s = g.server.online.get(g.user_id)
        assert s is not None
        soldiers, pawn_tpl = outer_city.army_soldiers(snap, s.ctx.templates)
        assert pawn_tpl == 9003 and soldiers


def test_ranking_do_sky_trails_soma_e_ordena() -> None:
    now = datetime(2026, 10, 29, tzinfo=UTC)

    def st(cid: int, top: int, ranks: dict[str, int]) -> EventState:
        return EventState(cid, "singlepass", now, text=json.dumps({"max": top, "ranks": ranks}))

    rows = [st(1, 5, {"1": 2}), st(2, 7, {"1": 1}), st(3, 5, {"1": 5, "2": 1}), st(4, 0, {})]
    rows.append(EventState(9, "singlepass_bugle", now, text="{}"))  # outra chave do mesmo prefixo
    assert rankings.singlepass_ranked(rows) == [(2, 7, 1), (3, 5, 6), (1, 5, 2)]


async def test_master_treasure_thief_volta_depois_do_reinicio(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        at = s.ctx.clock.now()
        s.ctx.guilds.lords[7] = fam.Lords(at, {750133}, wave=1, told=0)
        await server_state.save(s.ctx, server_state.LORDS)
        s.ctx.guilds.lords.clear()
        loaded = await server_state.ServerStates.load(g.server.services.characters, s.ctx.states.server_id)
        server_state.restore(s.ctx, loaded)
        lords = s.ctx.guilds.lords[7]
        assert (lords.called_at, lords.dead, lords.wave, lords.told) == (at, {750133}, 1, 0)


def test_levas_do_master_treasure_thief() -> None:
    """(visto) 183522: 20 dos 30 por leva, levas a 0/180/360 s, a 3ª fica e já não está "aberta"; leva nova zera
    os vencidos."""
    at = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
    lords = fam.Lords(at)
    camps = list(range(750133, 750163))
    assert len(lords.shown(camps, 0)) == 20 and lords.shown(camps, 0) == fam.Lords(at).shown(camps, 0)
    assert [lords.batch(at + timedelta(seconds=t)) for t in (0, 179, 180, 360, 539, 540)] == [0, 0, 1, 2, 2, None]
    assert lords.open(at + timedelta(seconds=359)) and not lords.open(at + timedelta(seconds=360))
    assert lords.left_ms(at + timedelta(seconds=40)) == 140000
    store = {7: lords}
    lords.dead.add(750133)
    assert fam.lords_of(store, 7, at + timedelta(seconds=200)) is lords and not lords.dead
    assert fam.lords_of(store, 7, at + timedelta(days=1)) is None and 7 not in store
