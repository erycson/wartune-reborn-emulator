"""Castelos NPC dos mapas do mundo (game/npc_castles.py, docs/cidade-externa.md#castelos-npc-do-mundo)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import MailType, Pawn, PlayerSnapshot
from wartune_server.game import arena as A
from wartune_server.game import battle as battle_mod
from wartune_server.game import caches, mines, monsters, npc_castles
from wartune_server.game import outer_city as oc
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

NOISE = (153, 75, 154, 156, 4600)
ALADYR = (729056, 2486, 2671)  # grade 49_53, grau 12, dono 1300000011


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _to_map_1(g: Game) -> PlayerSnapshot:
    snap = _snap(g)
    snap.character.grades = 12
    assert snap.castle is not None and snap.arena is not None
    snap.castle.energy = 500
    snap.pawns.append(Pawn(g.user_id, 10101, army_count=150, fight_pos=1))
    snap.arena.day, snap.arena.attack_left = A.today(g.server.services.clock.now()), 5
    g.client.send(5176, pb.CastleReqMsg(magId=1, posX=0, posY=0, payType=1))
    await g.until(105)
    assert snap.castle.map_id == 1
    return snap


async def test_vistos_gerados_e_tiles_livres(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=22500) as g:
        world, templates = g.server.services.world, g.server.services.templates
        [aladyr] = npc_castles.castles_in(world, templates, 1, {"49_53"})
        assert (aladyr.id, aladyr.x, aladyr.y, aladyr.grade, aladyr.user_id, aladyr.name) == (
            *ALADYR, 12, 1300000011, "Aladyr"
        )  # fmt: skip
        assert npc_castles.castles_in(world, templates, 1, {"47_53"}) == []  # grade vista sem castelo
        grids = {f"{x}_{y}" for x in range(10, 40) for y in range(10, 40)}
        made = npc_castles.castles_in(world, templates, 1, grids)
        assert made == npc_castles.castles_in(world, templates, 1, grids)  # semente: igual para todos
        assert made and all(11 <= c.grade <= 20 and c.id >= npc_castles.ID_BASE and c.name for c in made)
        assert len({c.user_id for c in made}) == len(made)
        assert all(mines.world_mine_at(world, templates, 1, c.x, c.y) is None for c in made)
        assert npc_castles.castles_in(world, templates, 100000001, {"0_0"}) == []  # instância do castelo
        assert [(r.id, r.grade) for r in world.robots] == [(765958, 8), (765957, 8)]  # robôs da instância intactos
        now = g.server.services.clock.now()
        spots = [
            (c.x, c.y) for c in caches.on_map(world, templates, 1, now) + monsters.on_map(world, templates, 1, now)
        ]
        assert not any(npc_castles.castle_at(world, templates, 1, x, y) for x, y in spots)
        assert npc_castles.pawn_hp(world, templates, 12) == 443
        assert npc_castles.pawn_hp(world, templates, 14) == round(440 * 1.05)


async def test_ataque_ao_castelo_npc_e_relatorio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """(visto) oficial_20261023-171155-1 #740-#749 e #819-#833: 4129 com Aladyr; o ataque é o do castelo-robô (leed,
    140 ×2, 140 do próprio castelo, 4452, 3, 140 do Aladyr em luta, 157 battleType 4 no 993 com 2 pilhas de 10112 de
    443 e o herói 11012); a derrota manda o relatório (148, ``MailType`` 3)."""

    async def lose(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 1:
                unit.hp = 0
        return False

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", lose)
    async with logged_in(tmp_path, novice=22500, clock=FakeClock()) as g:
        snap = await _to_map_1(g)
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid="49_53"))
        page = pb.PhysicListUpdateMsg.FromString((await g.until(169))[-2].body)
        npc = next(c for c in page.baseCastle if c.id == ALADYR[0])
        assert (npc.occupyPlayerId, npc.castleName, npc.grade, npc.state) == (1300000011, "Aladyr", 12, 1)

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=ALADYR[1], posY=ALADYR[2]))
        got = await g.until(157)
        assert [p.code for p in got if p.code not in (4152, 83)] == [140, 140, 140, 4452, 3, 140, 157]
        fighting = pb.MapUpdatedMsg.FromString([p.body for p in got if p.code == 140][-1])
        assert (fighting.baseCastle.id, fighting.baseCastle.state) == (ALADYR[0], 4)
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert (prepare.battleType, prepare.mapTempId) == (4, 993)
        assert [(x.tempId, x.pos, x.hp) for x in prepare.soldiers if x.side == 2] == [(10112, 1, 443), (10112, 7, 443)]
        [enemy] = [h for h in prepare.heros if h.side == 2]
        assert (enemy.tempId, enemy.nickName, enemy.grade, enemy.hp) == (11012, "Aladyr", 12, 501)
        assert list(enemy.skillId) == [10711, 10811, 11011]
        assert snap.arena is not None and snap.arena.attack_left == 4

        got = await g.fight(prepare) + await g.idle()
        after = [p.code for p in got if p.code not in NOISE]
        assert after[after.index(4103) :][-5:] == [148, 140, 140, 140, 4382]
        back = pb.MapUpdatedMsg.FromString([p.body for p in got if p.code == 140][-1])
        assert (back.baseCastle.id, back.baseCastle.state) == (ALADYR[0], 1)
        chars = g.server.services.characters
        [mail] = [m for m in await chars.read(lambda uow: uow.mails.by_receiver(g.user_id)) if m.mail_type == 3]
        assert mail.mail_type == MailType.BATTLE_REPORT
        report = ET.fromstring(mail.contents)
        info, me, he = report.find("info"), report.find("me"), report.find("he")
        assert info is not None and me is not None and he is not None
        assert (info.get("playerName"), info.get("result"), info.get("pos"), info.get("mapId")) == (
            "Aladyr", "2", "2486,2671", "1"
        )  # fmt: skip
        assert (me.get("site1Name"), he.get("heroId"), he.get("grade")) == ("Lancer", "11012", "12")
        assert int(me.get("site1Count") or 0) == 150


async def test_castelo_nao_muda_para_tile_ocupado(tmp_path: Path) -> None:
    """O 5176 no mesmo mapa recusa o tile de uma mina ou de um castelo NPC (105 com o castelo como está)."""
    async with logged_in(tmp_path, novice=22500) as g:
        snap = await _to_map_1(g)
        assert snap.castle is not None
        here = (snap.castle.pos_x, snap.castle.pos_y)
        world, templates = g.server.services.world, g.server.services.templates
        assert not npc_castles.tile_taken(world, templates, 1, *here)
        for x, y in ((2487, 2632), ALADYR[1:]):
            g.client.send(5176, pb.CastleReqMsg(magId=1, posX=x, posY=y, payType=1))
            moved = pb.CastleReqMsg.FromString((await g.until(105))[-1].body)
            assert (moved.posX, moved.posY) == here == (snap.castle.pos_x, snap.castle.pos_y)
        assert oc.inside(templates, 1, 2487, 2632)
