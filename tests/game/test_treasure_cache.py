"""Treasure Cache do mapa do mundo (game/caches.py, docs/cidade-externa.md#treasure-cache)."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Pawn, PlayerSnapshot
from wartune_server.game import battle as battle_mod
from wartune_server.game import caches as tc
from wartune_server.game import outer_city as oc
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

NOISE = (153, 75, 154, 156, 4600)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _to_map_1(g: Game) -> PlayerSnapshot:
    snap = _snap(g)
    snap.character.grades = 12
    assert snap.castle is not None
    snap.castle.energy = 500
    snap.pawns.append(Pawn(g.user_id, 10101, army_count=150, fight_pos=1))  # a formação da captura
    assert snap.leader is not None
    snap.leader.fight_pos = 3
    g.client.send(5176, pb.CastleReqMsg(magId=1, posX=0, posY=0, payType=1))
    await g.until(105)
    assert snap.castle.map_id == 1
    return snap


def _lands(got: list) -> list[pb.WildLandMsg]:  # type: ignore[type-arg]
    return [w for p in got if p.code == 4129 for w in pb.PhysicListUpdateMsg.FromString(p.body).wildLand]


def _synced(got: list) -> list[pb.WildLandMsg]:  # type: ignore[type-arg]
    out = [pb.MapUpdatedMsg.FromString(p.body) for p in got if p.code == 140]
    return [m.wildLand for m in out if m.updatedType == 1]


def test_regras_vistas_no_template() -> None:
    from wartune_server.templates.repository import GameTemplates

    templates = GameTemplates.parse(TEMPLATES.read_bytes())
    assert tc.template_of(templates, 15) == (220115, 18000)  # (visto) #1938: 18000000 ms no recém-nascido
    assert [tc.guard(templates, lv) for lv in (13, 14, 15)] == [6011, 6013, 6014]  # #573, #1532, #328
    born = datetime(2026, 1, 1, tzinfo=UTC)
    c = tc.Cache(tc.ID_BASE + 1, 1, 220113, 13, 50, 60, born, born + timedelta(seconds=18000))
    msg = tc.cache_msg(templates, c, born + timedelta(seconds=1))
    assert (msg.type, msg.level, msg.refreshTime, len(msg.armyPawn)) == (22, 13, 17_999_000, 3)


async def test_baus_do_mapa_1_sao_os_mesmos_para_todos(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=22500) as g:
        world, templates = g.server.services.world, g.server.services.templates
        now = g.server.services.clock.now()
        first = tc.on_map(world, templates, 1, now)
        assert first == tc.on_map(world, templates, 1, now)
        assert len(first) == 1000 and {c.level for c in first} <= set(range(11, 21))
        assert all(c.born <= now < c.ends for c in first)
        assert tc.on_map(world, templates, 100, now) == []  # instância do castelo: sem baú


async def test_luta_com_o_bau_da_o_item_e_o_bau_some(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(visto) oficial_20261023-171155-1 #570-#670: 140 lutando, 140 do baú em luta, 157 battleType 3 com 3 guardas
    de vida Live/100; vencendo, o item antes do 4103, o baú em state 0, "Received: ... x1" e o 4382 em seguida."""

    async def win(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 2:
                unit.hp = 0
        return True

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", win)
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = await _to_map_1(g)
        world, templates = g.server.services.world, g.server.services.templates
        c = tc.on_map(world, templates, 1, clock.now())[0]
        grid = oc.grid_of(c.x, c.y)
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid=grid))
        seen = [w for w in _lands(await g.until(169)) if w.type == 22]
        assert c.id in [w.id for w in seen]

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=c.x, posY=c.y))
        got = await g.until(157)
        assert [p.code for p in got] == [140, 140, 140, 157]
        assert [(w.id, w.state) for w in _synced(got)] == [(c.id, 4)]
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert (prepare.battleType, prepare.mapTempId) == (3, 1)
        pawn = tc.guard(templates, c.level)
        hp = int((templates.get("PawnTempInfos", pawn) or {})["Live"]) // 100
        assert [(x.tempId, x.pos, x.hp) for x in prepare.soldiers if x.side == 2] == [
            (pawn, 4, hp), (pawn, 2, hp), (pawn, 8, hp),
        ]  # fmt: skip
        mine = [(x.pos) for x in prepare.soldiers if x.side == 1] + [h.pos for h in prepare.heros if h.side == 1]
        assert mine == [1, 7, 6]  # #574: tropas na frente, herói atrás

        bag = len(snap.items)
        got = await g.fight(prepare) + await g.idle()
        codes = [p.code for p in got if p.code not in NOISE]
        assert codes.index(115) < codes.index(111) < codes.index(4103)
        assert codes[-3:] == [83, 169, 4382]
        assert [(w.id, w.state) for w in _synced(got)] == [(c.id, 0)]
        text = pb.ChatChannelMsg.FromString(next(p.body for p in got if p.code == 111)).encodeMsg
        assert text.startswith("Received: ") and text.endswith(" x1")
        assert len(snap.items) == bag + 1
        assert pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleScene == 0

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=c.x, posY=c.y))  # já aberto: só para o exército
        assert [p.code for p in await g.until(140)] == [140]
        assert await g.idle() == []
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid=grid))
        assert c.id not in [w.id for w in _lands(await g.until(169))]

        clock.advance((c.ends - clock.now()).total_seconds() + 1)  # a vida seguinte nasce em outro tile
        assert (c.id, c.born) not in {(n.id, n.born) for n in tc.on_map(world, templates, 1, clock.now())}


async def test_derrota_devolve_o_bau(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(visto) #370-#381: 4103 result 2 e o baú volta a state 1."""

    async def lose(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 1:
                unit.hp = 0
        return False

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", lose)
    async with logged_in(tmp_path, novice=22500) as g:
        await _to_map_1(g)
        world, templates = g.server.services.world, g.server.services.templates
        c = tc.on_map(world, templates, 1, g.server.services.clock.now())[0]
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid=oc.grid_of(c.x, c.y)))
        await g.until(169)
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=c.x, posY=c.y))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        got = await g.fight(prepare) + await g.idle()
        assert pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103)).battleResult == 2
        assert [(w.id, w.state) for w in _synced(got)] == [(c.id, 1)]
        assert 115 not in [p.code for p in got]


def test_premio_pedra_do_nivel_ou_equipamento_da_classe() -> None:
    from wartune_server.domain.world import World
    from wartune_server.templates.repository import GameTemplates

    templates = GameTemplates.parse(TEMPLATES.read_bytes())
    snap = SimpleNamespace(character=SimpleNamespace(job=3))  # o prêmio só olha a classe
    born = datetime(2026, 1, 1, tzinfo=UTC)
    c = tc.Cache(1, 1, 220113, 13, 0, 0, born, born + timedelta(days=1))
    rolls = [tc.loot(World(), templates, snap, c, random.Random(i)) for i in range(40)]  # type: ignore[arg-type]
    got = {r[0] for r in rolls}
    assert (2040103, 1) in got  # Lvl. 3 Luck Stone (#661)
    assert (1043102, 1) in got  # Elders Robe (#1792)
    gear = {t for t, _ in got if t != 2040103}
    assert all((templates.get("ItemTempInfos", t) or {}).get("Job") == "3" for t in gear)
