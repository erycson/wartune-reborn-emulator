"""Cidade externa: grade de exércitos, andar, voltar ao castelo, ataque extra e mudar o castelo de
lugar (docs/cidade-externa.md). O mapa do castelo é uma instância do jogador; exército alheio não aparece,
e os pedidos que dependem dele são recusados sem resposta, como o cliente espera."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Pawn, PlayerSnapshot, Quest, WildLand
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
        tpl, guard = oc.draw(snap, oc.MINES[0])  # o sorteio do ciclo: nível e guarda
        per_hour = int(templates.get("MapPhysicsTempInfos", tpl)["Property4"])
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
            (10101, 1, 242), (10101, 1, 242), (guard, 2, 175)
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
        assert [(y.wildPox, y.wildYield) for y in politics.wildYield] == [("16,34", per_hour)]
        assert castle_mod.gold_yield(snap, templates) == before + per_hour
        assert (snap.character.gold, castle_mod.pending_gold(snap, templates, clock.now())[0]) == (gold, 0)

        # já é dele: atacar de novo só para o exército; e relogar mantém a mina ocupada
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=16, posY=34))
        assert [p.code for p in await g.until(140)] == [140]
        again = await g.connect()
        again.client.send(8201, pb.PhysicUpdateReqMsg(mapId=castle.map_id, reqGrid="0_0"))
        got = await again.until(4129)
        lands = pb.PhysicListUpdateMsg.FromString(got[-1].body).wildLand
        assert [(w.posX, w.occupyPlayerId) for w in lands] == [(16, g.user_id), (36, 0)]


async def test_refresh_de_12_horas_sorteia_nivel_e_guarda(tmp_path: Path) -> None:
    """RefreshTime 43200 s: o ciclo é do jogador e começa no login. O nível sai entre 8 e 10 e o guarda
    acompanha (replay: nível 8 com o guarda 6504; níveis 9 e 10 com 6505); o createDate vem no fuso do jogo."""
    clock = FakeClock(datetime(2026, 5, 21, 9, 19, 54, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None and castle.mines_at == clock.now()  # o login abriu o ciclo
        assert oc.game_date(castle.mines_at) == "2026-05-21 12:19:54"  # replay #706: 09:19:54 UTC
        start = castle.mines_at
        draws = []
        for k in range(40):
            castle.mines_at = start + k * oc.MINE_PERIOD
            draws += [oc.draw(snap, mine) for mine in oc.MINES]
        for template, guard in draws:
            level = template - 200400
            assert level in (8, 9, 10) and oc.MINE_TEMPLATE[level] == template
            assert guard == oc.MINE_GUARD[level]
        assert {t for t, _ in draws} == set(oc.MINE_TEMPLATE.values())  # o sorteio muda de um ciclo para o outro
        assert oc.draw(snap, oc.MINES[0]) == oc.draw(snap, oc.MINES[0])  # mesmo ciclo, mesmo sorteio


async def test_ocupacao_de_mina_vence_no_refresh(tmp_path: Path) -> None:
    """No refresh a mina do jogador volta livre: o ouro até o refresh sai na taxa antiga, o ciclo novo
    começa no pedido e a mina pode ser ocupada de novo na mesma linha (unique personagem+mina)."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None and castle.mines_at is not None
        templates = g.server.services.templates
        mine = oc.MINES[1]
        land = WildLand(g.user_id, mine.id, clock.now())
        snap.wild_lands.append(land)
        castle.produced_at = clock.now()
        await g.server.services.characters.save(land, castle, snap.character)

        boundary = castle.mines_at + oc.MINE_PERIOD
        expected, _ = castle_mod.pending_gold(snap, templates, boundary)  # na taxa com a mina, até o refresh
        assert expected > 0
        gold = snap.character.gold
        clock.advance((boundary - clock.now()).total_seconds() + 60)

        got = await _grid(g, oc.grid_of(mine.x, mine.y))
        page = pb.PhysicListUpdateMsg.FromString(next(p.body for p in got if p.code == 4129))
        shown = next(w for w in page.wildLand if w.id == mine.id)
        assert (shown.occupyPlayerId, shown.state) == (0, oc.MINE_FREE)
        assert castle.mines_at == clock.now() and shown.createDate == oc.game_date(clock.now())
        after = castle_mod.gold_yield(snap, templates) * 60 // 3600  # o minuto depois do refresh: só os prédios
        assert oc.occupied(snap, mine) is None and snap.character.gold == gold + expected + after
        assert oc.mine_gold(snap, templates) == 0

        assert oc.occupy(snap, mine, clock.now()) is land  # a linha do ciclo vencido volta a valer
        await g.server.services.characters.save(land)
        fresh = await g.server.services.characters.snapshot(g.user_id)
        assert oc.occupied(fresh, mine) is not None and len(fresh.wild_lands) == 1
        assert fresh.castle is not None and fresh.castle.mines_at == clock.now()


async def test_ouro_de_outro_handler_para_no_fim_do_ciclo(tmp_path: Path) -> None:
    """Todo settle de ouro (5015, 8202, 8327, fazenda, caixa) vira o ciclo: a mina só rende até o refresh."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None and castle.mines_at is not None
        templates = g.server.services.templates
        buildings = castle_mod.gold_yield(snap, templates)
        oc.occupy(snap, oc.MINES[0], clock.now())
        per_hour = castle_mod.gold_yield(snap, templates) - buildings
        assert per_hour > 0
        end = oc.cycle_end(snap)
        castle.produced_at, snap.character.gold = end - timedelta(hours=1), 0
        clock.advance((end - clock.now()).total_seconds() + 3600)  # uma hora antes e uma depois do refresh
        castle_mod.settle(snap, templates, clock.now())
        assert castle.mines_at == clock.now() and oc.mine_gold(snap, templates) == 0
        assert snap.character.gold == (buildings + per_hour) + buildings


async def test_mina_de_outro_jogador_nao_bloqueia_a_instancia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """O mapa do castelo é uma instância de cada conta (replay #706 e cevre #11: mesmas minas, instâncias,
    robôs e createDate diferentes). A mina que outro jogador ocupou aparece livre e abre a luta (missão 60),
    e o castelo dele não entra no 4129 da instância."""
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    async with logged_in(tmp_path, novice=22500) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        other = await g.join("outro")
        mine = oc.MINES[0]
        await g.server.services.characters.save(WildLand(other.user_id, mine.id, g.server.services.clock.now()))

        got = await _grid(g, oc.grid_of(mine.x, mine.y))
        page = pb.PhysicListUpdateMsg.FromString(next(p.body for p in got if p.code == 4129))
        assert [c.occupyPlayerId for c in page.baseCastle] == [g.user_id]
        assert next(w for w in page.wildLand if w.id == mine.id).occupyPlayerId == 0

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=mine.x, posY=mine.y))
        assert (await g.until(157))[-1].code == 157


async def test_castelo_de_outro_jogador_num_mapa_compartilhado(tmp_path: Path) -> None:
    """Nos mapas 1 a 5 o 4129 da grade traz os castelos dos outros jogadores com o nome deles."""
    async with logged_in(tmp_path, novice=22500) as g:
        other = await g.join("outro")
        for game, x in ((g, 2100), (other, 2110)):
            castle = _snap(game).castle
            assert castle is not None
            castle.map_id, castle.pos_x, castle.pos_y = 2, x, 1900
            await g.server.services.characters.save(castle)

        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=2, reqGrid=oc.grid_of(2100, 1900)))
        page = pb.PhysicListUpdateMsg.FromString((await g.until(4129))[-1].body)
        assert [(c.occupyPlayerId, c.occupyPlayerName, c.posX) for c in page.baseCastle][1:] == [
            (other.user_id, "Outro", 2110)
        ]
        assert list(page.wildLand) == []  # as minas do mapa 2 não existem no servidor


async def test_ocupacao_vence_ao_logar_depois_do_refresh(tmp_path: Path) -> None:
    """Quem volta ao jogo depois do refresh já entra com a mina livre: a linha sai no login, antes do 109 e do 152."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        assert snap.castle is not None
        snap.castle.mines_at = clock.now() - oc.MINE_PERIOD + timedelta(seconds=60)  # a 1 min do refresh
        await g.server.services.characters.save(snap.castle, WildLand(g.user_id, oc.MINES[0].id, clock.now()))
        gold_before = (await g.server.services.characters.snapshot(g.user_id)).character.gold
        clock.advance(120)  # passou o refresh; a chave do login (30 min) ainda vale
        await g.connect()
        fresh = await g.server.services.characters.snapshot(g.user_id)
        assert oc.occupied(fresh, oc.MINES[0]) is None
        assert fresh.castle is not None and fresh.castle.mines_at == clock.now()
        assert fresh.character.gold >= gold_before  # o settle do refresh nunca tira ouro
