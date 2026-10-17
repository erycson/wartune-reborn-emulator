"""Cidade externa: grade de exércitos, andar, voltar ao castelo, ataque extra e mudar o castelo de
lugar (docs/cidade-externa.md). Sem outros jogadores no mapa: os pedidos que dependem deles são
recusados sem resposta, como o cliente espera."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Pawn, PlayerSnapshot, Quest
from wartune_server.game import arena as A
from wartune_server.game import battle as battle_mod
from wartune_server.game import castle as castle_mod
from wartune_server.game import outer_city as oc
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _set(g: Game, **fields: int) -> PlayerSnapshot:
    snap = _snap(g)
    for name, value in fields.items():
        setattr(snap.character, name, value)
    await g.server.services.characters.save(snap.character)
    return snap


def _walked(g: Game) -> tuple[int, int, int] | None:
    session = g.server.online.get(g.user_id)
    assert session is not None
    return session.outer_army


def _armies(got: list) -> list[pb.ArmyArmyMsg]:  # type: ignore[type-arg]
    return [a for p in got if p.code == 169 for a in pb.OutercityArmyUpdatedGridMsg.FromString(p.body).updatedArmy]


async def _grid(g: Game, grid: str) -> list:  # type: ignore[type-arg]
    # o cliente pede a grade no 8201 (reqGrid): 4129 e depois o 169 com os exércitos da grade
    g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=_snap(g).castle.map_id, reqGrid=grid))  # type: ignore[union-attr]
    return await g.until(169)


async def test_grid_walk_and_return_home(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        castle = _snap(g).castle
        assert castle is not None
        home_x, home_y = castle.pos_x - 2, castle.pos_y - 2

        got = await _grid(g, oc.grid_of(home_x, home_y))
        assert [(a.armyId, a.curPosX, a.curPosY) for a in _armies(got)] == [(g.user_id, home_x, home_y)]
        assert _armies(await _grid(g, "99_99")) == []  # grade sem o exército
        g.client.send(5004, pb.OutercityReqMsg(mapId=castle.map_id, position="0_0"))  # cliente não lê resposta
        assert await g.idle() == []

        # andar: só o último ponto (pixels // 20) vale; outro exército e rota vazia são ignorados
        g.client.send(8254, pb.PosMoveMsg(mapId=castle.map_id, armyId=g.user_id + 1, routes=[pb.RouteMsg(x=0, y=0)]))
        g.client.send(8254, pb.PosMoveMsg(mapId=castle.map_id, armyId=g.user_id, routes=[]))
        g.client.send(8254, pb.PosMoveMsg(mapId=castle.map_id, armyId=g.user_id, routes=[pb.RouteMsg(x=67, y=80)]))
        await g.idle()
        assert _walked(g) == (castle.map_id, 3, 4)

        got = await _grid(g, oc.grid_of(3, 4))
        assert [(a.curPosX, a.curPosY) for a in _armies(got)] == [(3, 4)]

        g.client.send(5161, pb.PayTypeMsg(payType=1))  # voltar: de graça, 98 com a posição do castelo
        back = pb.OutercityRspMsg.FromString((await g.until(98))[-1].body)
        assert (back.result, back.curPosX, back.curPosY) == (g.user_id, home_x, home_y)
        assert _walked(g) is None


async def test_attack_extra_costs_diamonds_and_is_capped_at_five(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = await _set(g, point=150, gift_token=0)
        assert snap.arena is not None and snap.arena.attack_left == 5
        # o dia já é o de hoje (senão a virada zera o contador antes da compra)
        snap.arena.day, snap.arena.attack_left = A.today(g.server.services.clock.now()), 3
        await g.server.services.characters.save(snap.arena)

        g.client.send(9506, pb.OutercityReqMsg(mapId=0, attackCount=1, type=1))
        got = await g.until(3)
        assert pb.PlayerMsg.FromString(got[-1].body).attackLeftCount == 4
        assert snap.character.point == 50

        g.client.send(9506, pb.OutercityReqMsg(mapId=0, attackCount=1, type=1))  # sem diamante suficiente
        assert await g.idle() == []

        snap.character.gift_token = 100  # tipo 2: o vinculado paga primeiro
        g.client.send(9506, pb.OutercityReqMsg(type=2))
        got = await g.until(3)
        assert pb.PlayerMsg.FromString(got[-1].body).attackLeftCount == 5
        assert (snap.character.point, snap.character.gift_token) == (50, 0)

        g.client.send(9506, pb.OutercityReqMsg(type=1))  # já são 5: nada
        assert await g.idle() == []
        g.client.send(9506)  # corpo vazio não derruba a sessão
        g.client.send(20008)
        await g.until(4234)


async def test_move_castle_to_another_map_spends_energy_and_answers_105(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = await _set(g, grades=11, point=0, gift_token=0)
        castle = snap.castle
        assert castle is not None
        castle.energy = 500
        other = 1  # Özgürlük Otlağı: nível 11 (WorldMapHelper)
        centre = oc.centre(g.server.services.templates, other)

        g.client.send(5176, pb.CastleReqMsg(magId=other, posX=0, posY=0, payType=1))
        got = await g.until(105)
        assert [p.code for p in got] == [140, 105]
        moved = pb.CastleReqMsg.FromString(got[-1].body)
        assert (moved.magId, moved.posX, moved.posY, moved.leftEnergy) == (other, centre[0], centre[1], 300)
        assert (castle.map_id, castle.pos_x, castle.pos_y, castle.energy) == (other, centre[0], centre[1], 300)

        g.client.send(5176, pb.CastleReqMsg(magId=2, posX=0, posY=0, payType=1))  # mapa 2 pede nível 21
        refused = pb.CastleReqMsg.FromString((await g.until(105))[-1].body)
        assert (refused.magId, refused.leftEnergy) == (other, 300)

        castle.energy = 100  # faltam 400 para o teto: (500 - 100) / 5 = 80 diamantes
        g.client.send(5176, pb.CastleReqMsg(magId=100, posX=0, posY=0, payType=1))  # sem diamante
        assert pb.CastleReqMsg.FromString((await g.until(105))[-1].body).leftEnergy == 100
        snap.character.point = 80
        g.client.send(5176, pb.CastleReqMsg(magId=100, posX=0, posY=0, payType=1))
        assert pb.CastleReqMsg.FromString((await g.until(105))[-1].body).leftEnergy == 300
        assert (snap.character.point, castle.map_id) == (0, 100)


async def test_move_castle_inside_the_map_checks_the_point(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None
        castle.energy = 500
        here = castle.map_id

        g.client.send(5176, pb.CastleReqMsg(magId=here, posX=10, posY=12, payType=1))
        got = await g.until(105)
        assert [p.code for p in got] == [140, 105]
        assert (castle.pos_x, castle.pos_y, castle.energy) == (10, 12, 400)
        assert [(a.curPosX, a.curPosY) for a in _armies(await _grid(g, oc.grid_of(8, 10)))] == [(8, 10)]

        g.client.send(5176, pb.CastleReqMsg(magId=here, posX=99999, posY=1, payType=1))  # fora do mapa
        assert pb.CastleReqMsg.FromString((await g.until(105))[-1].body).posX == 10
        assert castle.energy == 400


async def test_pedidos_que_dependem_de_outro_jogador(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        castle = _snap(g).castle
        assert castle is not None
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=5, posY=5))  # sem alvo: para o exército
        got = await g.until(140)
        assert pb.MapUpdatedMsg.FromString(got[-1].body).army.state == 0
        g.client.send(8488, pb.PlayerChallengeMsg(tarUserId=99))  # PvP sem exército alheio: nada a responder
        g.client.send(8699)  # guia do tutorial: nada a coletar
        g.client.send(5160)  # corpo vazio: também para o exército, sem derrubar a sessão
        await g.until(140)
        assert await g.idle() == []


async def test_castelo_novo_no_ponto_do_guia(tmp_path: Path) -> None:
    """O guia do tutorial procura o castelo no pixel (520,920) = tile (26,46), como o oficial."""
    async with logged_in(tmp_path, novice=19000) as g:
        castle = _snap(g).castle
        assert castle is not None and (castle.pos_x, castle.pos_y) == (26, 46)


async def test_mina_de_ouro_luta_e_ocupa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missão 60 (replay #706-#795): as minas vêm no 4129, o 5160 numa livre abre a luta com o guarda
    e a vitória deixa a mina do jogador, conta na missão e soma o ouro dela no castelo."""
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        snap.quests.append(Quest(g.user_id, 60, datetime.now(UTC)))
        templates = g.server.services.templates
        before = castle_mod.gold_yield(snap, templates)
        castle.produced_at = clock.now() - timedelta(hours=1)  # uma hora sem recolher: taxa antiga
        gold = snap.character.gold + castle_mod.pending_gold(snap, templates, clock.now())[0]

        got = await _grid(g, "-1_0,-1_1,0_0,0_1,1_0,1_1")
        lands = pb.PhysicListUpdateMsg.FromString(got[0].body).wildLand
        assert [(w.posX, w.posY, w.state, w.occupyPlayerId) for w in lands] == [
            (16, 34, 1, 0), (36, 34, 1, 0), (71, 54, 1, 0), (54, 64, 1, 0)
        ]  # fmt: skip
        assert not lands[0].HasField("occupyPlayerName")  # livre: como o oficial

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=16, posY=34))
        got = await g.until(157)
        assert [p.code for p in got] == [140, 140, 140, 157]
        assert pb.MapUpdatedMsg.FromString(got[2].body).wildLand.state == oc.MINE_FIGHTING
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert prepare.battleType == 1 and [(x.tempId, x.side, x.hp) for x in prepare.soldiers] == [
            (10101, 1, 242), (10101, 1, 242), (6505, 2, 175)
        ]  # fmt: skip

        got = await g.fight(prepare)
        got += await g.idle()
        report = pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body)
        assert (report.battleResult, report.battleScene) == (1, 4)
        after = [p.code for p in got if p.code not in (153, 75, 154, 156, 4600)]
        assert after == [150, 4103, 150, 100, 140, 140, 112, 4152, 109, 152, 140, 169]
        quest = pb.QuestUpdatedRspMsg.FromString(next(p for p in got if p.code == 112).body).quest[0]
        assert (quest.templateId, quest.condition_1) == (60, 1)
        land = pb.MapUpdatedMsg.FromString([p for p in got if p.code == 140][-1].body).wildLand
        assert (land.occupyPlayerId, land.state) == (g.user_id, 1)
        politics = pb.CastleYieldMsg.FromString(next(p for p in got if p.code == 152).body)
        assert [(y.wildPox, y.wildYield) for y in politics.wildYield] == [("16,34", 680)]
        assert castle_mod.gold_yield(snap, templates) == before + 680
        assert (snap.character.gold, castle_mod.pending_gold(snap, templates, clock.now())[0]) == (gold, 0)

        # já é dele: atacar de novo só para o exército; e relogar mantém a mina ocupada
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=16, posY=34))
        assert [p.code for p in await g.until(140)] == [140]
        again = await g.connect()
        again.client.send(8201, pb.PhysicUpdateReqMsg(mapId=castle.map_id, reqGrid="0_0"))
        got = await again.until(4129)
        lands = pb.PhysicListUpdateMsg.FromString(got[-1].body).wildLand
        assert [(w.posX, w.occupyPlayerId) for w in lands] == [(16, g.user_id), (36, 0)]
