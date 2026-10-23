"""Minas de ouro dos mapas do mundo (game/mines.py, docs/cidade-externa.md#minas-do-mundo)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Pawn, PlayerSnapshot
from wartune_server.game import battle as battle_mod
from wartune_server.game import mines
from wartune_server.game import outer_city as oc
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

NOISE = (153, 75, 154, 156, 4600)
GRID = "49_52"  # grade vista: 806735 (2487,2611) e 806736 (2487,2632), entre outras
FIRST, SECOND, THIRD = (806736, 2487, 2632), (806735, 2487, 2611), (806961, 2480, 2701)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _to_map_1(g: Game) -> PlayerSnapshot:
    snap = _snap(g)
    snap.character.grades = 12
    assert snap.castle is not None
    snap.castle.energy = 500
    snap.pawns.append(Pawn(g.user_id, 10101, army_count=150, fight_pos=1))
    g.client.send(5176, pb.CastleReqMsg(magId=1, posX=0, posY=0, payType=1))
    await g.until(105)
    assert snap.castle.map_id == 1
    return snap


def _lands(got: list) -> list[pb.WildLandMsg]:  # type: ignore[type-arg]
    return [w for p in got if p.code == 4129 for w in pb.PhysicListUpdateMsg.FromString(p.body).wildLand]


def _synced(got: list) -> list[pb.WildLandMsg]:  # type: ignore[type-arg]
    out = [pb.MapUpdatedMsg.FromString(p.body) for p in got if p.code == 140]
    return [m.wildLand for m in out if m.updatedType == 1]


def _win(monkeypatch: pytest.MonkeyPatch) -> None:
    async def win(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 2:
                unit.hp = 0
        return True

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", win)


async def _occupy(g: Game, mine: tuple[int, int, int]) -> list:  # type: ignore[type-arg]
    g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=mine[1], posY=mine[2]))
    prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
    return await g.fight(prepare) + await g.idle()


async def test_ciclo_grades_e_guardas(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=22500) as g:
        world, templates = g.server.services.world, g.server.services.templates
        at = datetime(2026, 10, 23, 11, 50, tzinfo=UTC)
        assert mines.world_cycle_start(world, at) == datetime(2026, 10, 23, 1, 15, 41, tzinfo=UTC)
        assert mines.world_cycle_start(world, at.replace(hour=14)) == datetime(2026, 10, 23, 13, 15, 41, tzinfo=UTC)
        seen = mines.world_mines_in(world, templates, 1, {GRID})
        assert {FIRST[0], SECOND[0]} <= {m.id for m in seen}
        assert all(m.id < mines.WORLD_ID_BASE for m in seen)  # grade vista: só as do catálogo
        made = mines.world_mines_in(world, templates, 1, {"10_10", "70_20"})
        assert made == mines.world_mines_in(world, templates, 1, {"10_10", "70_20"})
        assert all((m.min_level, m.max_level) == (11, 20) and oc.grid_of(m.x, m.y) in {"10_10", "70_20"} for m in made)
        for m in made:
            assert mines.world_mine(world, templates, 1, m.id) == m
        assert mines.world_mines_in(world, templates, 100000001, {GRID}) == []  # instância do castelo
        assert [mines.guard_capacity(templates, p) for p in (6506, 6520)] == [866, 1436]
        assert mines.guard_capacity(templates, 6510) == mines._formula_capacity(templates, 6510) > 0
        assert world.mine_guards[18] == 6520 and world.mine_guards[60] == 6595


async def test_ocupa_e_desiste_da_mina_do_mundo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(visto) oficial_20261023-171155-1 #3037-#3082: 157 battleType 1 no mapa 1; vencendo, 152 "Autaric
    Plains(x,y)", 140 da mina com o dono, 169 e o 4382 logo em seguida. Terceira mina: recusada (cliente: 2)."""
    _win(monkeypatch)
    async with logged_in(tmp_path, novice=22500, clock=FakeClock()) as g:
        snap = await _to_map_1(g)
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid=GRID))
        free = next(w for w in _lands(await g.until(169)) if w.id == FIRST[0])
        assert (free.type, free.mapId, free.occupyPlayerId, free.state) == (20, 1, 0, 1)
        assert 0 < free.refreshTime <= 43_200_000 and free.fightCapaity > 0

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=FIRST[1], posY=FIRST[2]))
        got = await g.until(157)
        assert [p.code for p in got] == [140, 140, 140, 157]
        assert [(w.id, w.state) for w in _synced(got)] == [(FIRST[0], 4)]
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert (prepare.battleType, prepare.mapTempId) == (1, 1)
        got = await g.fight(prepare) + await g.idle()
        codes = [p.code for p in got if p.code not in NOISE]
        assert codes[-2:] == [169, 4382]
        politics = pb.CastleYieldMsg.FromString(next(p.body for p in got if p.code == 152))
        assert [(y.wildPoxName, y.mapId) for y in politics.wildYield] == [("Autaric Plains(2487,2632)", 1)]
        assert [(w.id, w.occupyPlayerId) for w in _synced(got)][-1] == (FIRST[0], g.user_id)
        land = next(w for w in snap.wild_lands if w.wild_id == FIRST[0])
        assert land.map_id == 1 and land.cycle_at is not None

        await _occupy(g, SECOND)
        assert len(mines.held(snap)) == 2
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=THIRD[1], posY=THIRD[2]))
        assert [p.code for p in await g.until(140)] == [140]  # recusa: só o exército parado
        assert await g.idle() == []

        g.client.send(5179, pb.BuildingReqMsg(position="2487,2632"))
        got = await g.until(152)
        assert pb.GiveupWildLandMsg.FromString(next(p.body for p in got if p.code == 108)).wildLandPos == "2487,2632"
        assert [w.wild_id for w in mines.held(snap)] == [SECOND[0]]


async def test_mina_de_outro_jogador_aparece_e_pode_ser_tomada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(visto) #1503: a mina de Alt29 aparece com o nome e o poder dele. TODO(inventado): a luta pela mina de outro
    jogador (contra o herói dele) e a carta para quem perde."""
    _win(monkeypatch)
    async with logged_in(tmp_path, novice=22500, clock=FakeClock()) as g:
        maga = await _to_map_1(g)
        await _occupy(g, FIRST)
        other = await g.join("outro")
        rival = await _to_map_1(other)
        other.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid=GRID))
        held = next(w for w in _lands(await other.until(169)) if w.id == FIRST[0])
        assert (held.occupyPlayerId, held.occupyPlayerName) == (g.user_id, "Maga")
        assert held.fightCapaity == next(w for w in maga.wild_lands if w.wild_id == FIRST[0]).capacity

        other.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=FIRST[1], posY=FIRST[2]))
        prepare = pb.BattlePrepareMsg.FromString((await other.until(157))[-1].body)
        assert [(h.side, h.pos) for h in prepare.heros if h.side == 2] == [(2, 5)]
        await other.fight(prepare)
        await other.idle()
        assert [w.wild_id for w in mines.held(rival)] == [FIRST[0]]
        assert mines.held(maga) == []
        assert 148 in [p.code for p in await g.idle()]  # carta para quem perdeu


async def test_virada_do_ciclo_com_o_jogador_online(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(visto) #170-#175: na virada cada mina sai com 109, 152 (com as que faltam) e 148 (carta)."""
    _win(monkeypatch)
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = await _to_map_1(g)
        await _occupy(g, FIRST)
        await _occupy(g, SECOND)
        assert snap.castle is not None
        clock.advance((mines.cycle_end(snap) - clock.now()).total_seconds() + 1)
        g.client.send(20008, pb.SynchronizedTimeMsg())
        got = [p for p in await g.idle(0.3) if p.code in (109, 152, 148)]
        assert [p.code for p in got] == [109, 152, 148, 109, 152, 148]
        rows = [len(pb.CastleYieldMsg.FromString(p.body).wildYield) for p in got if p.code == 152]
        assert rows == [1, 0]
        assert mines.held(snap) == []
        assert snap.castle.mines_at == mines.world_cycle_start(g.server.services.world, clock.now())
