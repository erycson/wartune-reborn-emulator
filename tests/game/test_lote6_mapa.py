"""Lote 6 da auditoria: mapa e castelo. Trégua (2001/8562), redistribuir atributos (5170), formação da sala (8277),
exércitos alheios no mapa e o ataque a castelo/exército de jogador, ponto livre do castelo mudado, luta em grupo
com monstro dos Wilds e o PK no mapa de campanha (8525)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_outer_city import _set, _snap
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item
from wartune_server.game import arena as A
from wartune_server.game import battle as battle_mod
from wartune_server.game import buffs, monsters
from wartune_server.game import outer_city as oc
from wartune_server.game.campaign import CampaignMap
from wartune_server.protocol.messages import wartune_pb2 as pb

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")
TOKEN = 208006  # City Protection Token


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)


def _session(g: Game, uid: int | None = None):  # type: ignore[no-untyped-def]
    s = g.server.online.get(uid or g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _camp(map_id: int) -> CampaignMap:
    return CampaignMap(map_id, {}, (10, 10))


async def _on_map_1(g: Game, x: int, y: int) -> None:
    """Castelo no mapa compartilhado 1 (nível 11) em x, y."""
    snap = await _set(g, grades=15)
    assert snap.castle is not None
    snap.castle.map_id, snap.castle.pos_x, snap.castle.pos_y = 1, x, y
    snap.castle.grade = 15  # MapPhysicsCastle.attack: diferença de nível menor que 10 (command02)
    await g.server.services.characters.save(snap.castle)


async def test_tregua_usa_o_item_grava_o_fim_e_8562_cancela(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        row = g.server.services.templates.get("ItemTempInfos", TOKEN)
        assert row is not None and int(row["Property1"]) == buffs.PROTECTION
        item = Item(g.user_id, TOKEN, pos=0, count=1)
        _snap(g).items.append(item)
        await g.server.services.characters.save(item)
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        left = pb.BaseCastleMsg.FromString((await g.until(4452))[-1].body).defenceLefttime
        assert left == int(row["Property2"]) * 60 == buffs.protection_left(_snap(g), g.server.services.clock.now())
        stored = await g.server.services.characters.snapshot(g.user_id)
        assert buffs.protection_left(stored, g.server.services.clock.now()) > 0  # gravado

        g.client.send(8562)
        assert pb.BaseCastleMsg.FromString((await g.until(4452))[-1].body).defenceLefttime == 0
        assert buffs.protection_left(_snap(g), g.server.services.clock.now()) == 0


async def test_redistribuir_devolve_os_pontos_livres(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        hero = _snap(g).leader
        assert hero is not None
        hero.power_point, hero.captain_point, hero.remain_point = 3, 2, 1
        g.client.send(5170)
        await g.until(150)
        assert (hero.power_point, hero.captain_point, hero.remain_point) == (0, 0, 6)
        stored = (await g.server.services.characters.snapshot(g.user_id)).leader
        assert stored is not None and stored.remain_point == 6


async def test_formacao_da_sala_grava_todos_os_membros(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        other = await g.join("outro")
        rooms = _session(g).ctx.rooms
        room = rooms.create(g.user_id, 2, "")
        assert rooms.join(room, other.user_id)
        edit = pb.ArmyFightPosEditListMsg()
        edit.armyFightPos.add(userId=g.user_id, heroPos=2)
        edit.armyFightPos.add(userId=other.user_id, heroPos=8)
        g.client.send(8277, edit)
        mine = pb.ArmyFightPosEditListMsg.FromString((await g.until(4186))[-1].body)
        theirs = pb.ArmyFightPosEditListMsg.FromString((await other.until(4186))[-1].body)
        assert {p.userId: p.heroPos for p in mine.armyFightPos} == {g.user_id: 2, other.user_id: 8}
        assert theirs == mine
        assert room.positions == {g.user_id: 2, other.user_id: 8}


async def test_exercito_alheio_aparece_anda_e_some(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _on_map_1(g, 520, 520)
        other = await g.join("outro")
        await _on_map_1(other, 525, 525)
        grid = oc.grid_of(520, 520)
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid=grid))
        armies = pb.OutercityArmyUpdatedGridMsg.FromString((await g.until(169))[-1].body)
        assert {a.playerId for a in armies.updatedArmy} == {g.user_id, other.user_id}

        other.client.send(
            8254, pb.PosMoveMsg(mapId=1, armyId=other.user_id, routes=[pb.RouteMsg(x=530 * 20, y=525 * 20)])
        )
        route = pb.PosMoveMsg.FromString((await g.until(4167))[-1].body)
        assert route.armyId == other.user_id and route.routes[0].x == 530 * 20

        other.client.send(5161, pb.PayTypeMsg())
        assert pb.ArmyRemoveMsg.FromString((await g.until(4168))[-1].body).armyId == other.user_id


async def test_ataque_a_castelo_de_jogador_saqueia_e_respeita_a_tregua(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copy = A.copy_hero

    def weak(*args: object) -> dict[str, object]:  # o dono com 1 de vida: a vitória (e o saque) é certa
        return copy(*args) | {"hp": 1, "initHp": 1}  # type: ignore[arg-type]

    monkeypatch.setattr(A, "copy_hero", weak)
    async with logged_in(tmp_path, novice=19000) as g:
        await _on_map_1(g, 500, 500)
        other = await g.join("outro")
        await _on_map_1(other, 510, 510)
        them = _snap(other)
        them.character.gold = 10_000
        now = g.server.services.clock.now()
        truce = buffs.apply(them, buffs.PROTECTION, TOKEN, 1, 60, now)
        assert truce is not None

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=510, posY=510))
        codes = [p.code for p in await g.idle()]
        assert codes[-1] == 140 and 157 not in codes  # protegido: o exército só para
        buffs.stop(them, buffs.PROTECTION, now)

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=510, posY=510))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        assert prepare.battleType == oc.ROBOT_BATTLE_TYPE
        got = await g.fight(prepare)
        report = pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body)
        assert report.battleResult == 1
        assert them.character.gold == 9_000  # 10% do ouro do dono (TODO(inventado) player_castle.loot_pct)
        assert any(p.code == 148 for p in await other.idle(0.3))  # a carta da defesa
        stored = await g.server.services.characters.snapshot(other.user_id)
        assert stored.character.gold == them.character.gold


async def test_pvp_de_exercitos_no_mapa(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        await _on_map_1(g, 500, 500)
        other = await g.join("outro")
        await _on_map_1(other, 505, 505)
        g.client.send(8488, pb.PlayerChallengeMsg(tarUserId=other.user_id))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        got = await g.fight(prepare)
        assert any(p.code == 4103 for p in got)


async def test_castelo_mudado_cai_no_ponto_livre_mais_proximo(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        templates = g.server.services.templates
        other = await g.join("outro")
        cx, cy = oc.centre(templates, 1)
        await _on_map_1(other, cx, cy)  # o centro já tem dono
        snap = await _set(g, grades=11)
        assert snap.castle is not None
        snap.castle.energy = 500
        g.client.send(5176, pb.CastleReqMsg(magId=1, posX=0, posY=0, payType=1))
        moved = pb.CastleReqMsg.FromString((await g.until(105))[-1].body)
        assert (moved.posX, moved.posY) != (cx, cy)
        assert max(abs(moved.posX - cx), abs(moved.posY - cy)) == 1
        assert oc.nearest_free(templates, 1, (cx, cy), lambda x, y: (x, y) == (cx, cy)) == (moved.posX, moved.posY)
        # mapas com o ponto visto no inglês (105 de 24/10 #15693 e 27/10 #18053); o mapa 1 não tem: o centro
        settings = g.server.services.world.settings
        assert oc.landing(templates, settings, 2) == (2084, 1953)
        assert oc.landing(templates, settings, 3) == (1229, 1103)
        assert oc.landing(templates, settings, 1) == (cx, cy)


async def test_monstro_em_luta_aceita_reforco_do_time(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        other = await g.join("outro")
        s, o = _session(g), _session(other, other.user_id)
        found = monsters.on_map(s.ctx.world, s.ctx.templates, 1, s.ctx.clock.now())
        if not found:
            pytest.skip("sem monstros no mapa 1")
        m = found[0]
        await _on_map_1(g, m.x, m.y + 3)
        await _on_map_1(other, m.x, m.y + 4)
        assert s.ctx.teams.invite(g.user_id, other.user_id)
        assert s.ctx.teams.accept(other.user_id, g.user_id) is not None
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=m.x, posY=m.y))
        first = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        other.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=m.x, posY=m.y))
        await other.until(157)  # o estado da luta em curso (Battle.join)
        assert s.battle is not None and o in s.battle.joined
        field = monsters.KILL_FIELDS[m.boss_type]
        before = (getattr(_snap(g).character, field), getattr(o.snapshot.character, field))
        await g.fight(first)
        helper = await other.idle(0.5)
        assert [p.code for p in helper].count(4103) == 1  # o do dono vai só a ele
        after = (getattr(_snap(g).character, field), getattr(o.snapshot.character, field))
        assert after[1] - before[1] == after[0] - before[0]  # o abate conta igual para quem entrou
        other.client.send(8747, pb.SimplePropertyMsg())
        assert 4382 in [p.code for p in await other.idle()]


async def test_pk_na_ilha_dos_pets_luta_e_no_gancho_convida(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        other = await g.join("outro")
        s, o = _session(g), _session(other, other.user_id)
        s.campaign, o.campaign = _camp(20001), _camp(20001)
        g.client.send(8525, pb.HangupAttackMsg(defenceId=other.user_id))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        assert prepare.battleType == 19
        await g.fight(prepare)

        s.campaign, o.campaign = _camp(7001), _camp(7001)
        g.client.send(8525, pb.HangupAttackMsg(defenceId=other.user_id))  # sem op fora da ilha/mina: nada
        assert 157 not in [p.code for p in await g.idle()]
        other.client.send(8525, pb.HangupAttackMsg(op=2, attackId=g.user_id, defenceId=other.user_id))
        assert 157 not in [p.code for p in await g.idle()]  # aceite forjado, sem convite: recusado
        g.client.send(8525, pb.HangupAttackMsg(op=1, attackId=g.user_id, defenceId=other.user_id))
        invite = pb.HangupAttackMsg.FromString((await other.until(4421))[-1].body)
        assert (invite.op, invite.attackId) == (1, g.user_id)
        other.client.send(8525, pb.HangupAttackMsg(op=2, attackId=g.user_id, defenceId=other.user_id))
        assert pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body).battleType == 19
