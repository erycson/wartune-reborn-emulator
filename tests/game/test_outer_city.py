"""Cidade externa: grade de exércitos, andar, voltar ao castelo, ataque extra e mudar o castelo de
lugar (docs/cidade-externa.md). O mapa do castelo é uma instância do jogador; exército alheio não aparece,
e os pedidos que dependem dele são recusados sem resposta, como o cliente espera."""

import functools
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Item, Pawn, PlayerSnapshot, Quest, WildLand, WildMonsterKill
from wartune_server.game import arena as A
from wartune_server.game import battle as battle_mod
from wartune_server.game import castle as castle_mod
from wartune_server.game import mines, monsters, robots
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
        price = A.config(g.server.services.templates, "AddAttck_Point", oc.ATTACK_PRICE)  # 395 nos templates EN
        snap = await _set(g, point=price + 50, gift_token=0)
        assert snap.arena is not None and snap.arena.attack_left == 5
        # o dia já é o de hoje (senão a virada zera o contador antes da compra)
        snap.arena.day, snap.arena.attack_left = A.today(g.server.services.clock.now()), 3
        await g.server.services.characters.save(snap.arena)

        g.client.send(9506, pb.OutercityReqMsg(mapId=0, attackCount=1, type=1))
        got = await g.until(3)
        assert pb.PlayerMsg.FromString(got[-1].body).attackLeftCount == 4
        assert snap.character.point == 50
        assert [p.code for p in await g.until(83)] == [4152, 83]  # leed 15 (gasto de diamante)

        g.client.send(9506, pb.OutercityReqMsg(mapId=0, attackCount=1, type=1))  # sem diamante suficiente
        assert [p.code for p in await g.idle()] == [111]  # aviso: o cliente só confere 100

        snap.character.gift_token = price  # tipo 2: o vinculado paga primeiro
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
        other = 1  # mapa 1: nível 11 (WorldMapHelper)
        centre = oc.centre(g.server.services.templates, other)
        world = g.server.services.world
        mine = world.mines[0]
        land = mines.occupy(
            snap, mine, mines.draw(snap, world, g.server.services.templates, mine)[0], datetime.now(UTC)
        )
        await g.server.services.characters.save(land)

        g.client.send(5176, pb.CastleReqMsg(magId=other, posX=0, posY=0, payType=1))
        got = await g.until(105)
        # (visto) oficial_20261023-153200-1 #185-#187: a mina se solta e o 152 vem sem wildYield
        assert [p.code for p in got] == [140, 152, 105]
        assert not pb.CastleYieldMsg.FromString(got[1].body).wildYield and snap.wild_lands == []
        assert (await g.server.services.characters.snapshot(g.user_id)).wild_lands == []
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
    """Missão 60 (inglesa #718-#821): as minas vêm no 4129, o 5160 numa livre abre a luta com o guarda
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
        world = g.server.services.world
        tpl, guard = mines.draw(snap, world, templates, world.mines[0])  # o sorteio do ciclo: nível e guarda
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
        assert pb.MapUpdatedMsg.FromString(got[2].body).wildLand.state == mines.MINE_FIGHTING
        # inglesa #721: exército compacto com heroTempId e job (o cliente grava heroTempId no herói; com 0 a luta
        # trava em ResourceModel.loadBattleJobUI e o boneco perde o corpo)
        army_msg = pb.MapUpdatedMsg.FromString(got[0].body).army
        assert snap.leader is not None
        assert (army_msg.heroTempId, army_msg.job, army_msg.state) == (snap.leader.template_id, 3, 2)  # maga
        assert not army_msg.HasField("simpleHeroInfo") and not army_msg.armyPawn
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert prepare.battleType == 1 and [(x.tempId, x.side, x.hp) for x in prepare.soldiers] == [
            (10101, 1, 242), (10101, 1, 242), (guard, 2, 175)
        ]  # fmt: skip
        assert (
            list(prepare.soldiers[0].skillId) == [10, 11] * 5 and prepare.heros[0].pawnTempId == 10101
        )  # inglesa #727

        strategy = snap.character.strategy
        got = await g.fight(prepare)
        got += await g.idle()
        report = pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body)
        assert (report.battleResult, report.battleScene) == (1, 4)
        after = [p.code for p in got if p.code not in (153, 75, 154, 156, 4600)]
        # o 83 da devoção (leed 9) logo depois do 4152; o oficial manda depois do 140 (tutorial_en #748-#753).
        # Com soldados perdidos, 109 e 3 antes do 4103 e o Daru = os perdidos (oficial_20261023-153200-1 #1620-#1623)
        assert after == [150, 109, 3, 4103, 150, 100, 140, 140, 112, 4152, 83, 109, 152, 140, 169]
        assert report.strategyBonus > 0 and snap.character.strategy == strategy + report.strategyBonus
        g.client.send(5035, pb.LoginStateMsg(state=3))  # de volta ao mapa: o 4382 mostra o Daru (#1636)
        movie = pb.FightOverMoiveMsg.FromString((await g.until(4382))[-1].body)
        assert movie.strategy == report.strategyBonus
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
    acompanha (níveis 9 e 10 com 6505: inglesa #718; nível 8 com 6504: só turco, replay); o createDate vem no fuso do jogo."""
    clock = FakeClock(datetime(2026, 5, 21, 12, 19, 54, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None and castle.mines_at == clock.now()  # o login abriu o ciclo
        assert (
            mines.game_date(castle.mines_at) == "2026-05-21 12:19:54"
        )  # só turco: replay #706 (12:19:54 em UTC+3; aqui o fuso é UTC)
        world, templates = g.server.services.world, g.server.services.templates
        start = castle.mines_at
        draws = []
        for k in range(40):
            castle.mines_at = start + k * mines.MINE_PERIOD
            draws += [mines.draw(snap, world, templates, mine) for mine in world.mines_on(oc.BASE_MAP)]
        for template, guard in draws:
            level = template - 200400
            assert level in (8, 9, 10) and mines.level_template(templates, level) == template
            assert guard == {8: 6504, 9: 6505, 10: 6505}[level]
        assert {t for t, _ in draws} == {200408, 200409, 200410}  # o sorteio muda de um ciclo para o outro
        first = world.mines_on(oc.BASE_MAP)[0]
        assert mines.draw(snap, world, templates, first) == mines.draw(snap, world, templates, first)  # mesmo ciclo


async def test_ocupacao_de_mina_vence_no_refresh(tmp_path: Path) -> None:
    """No refresh a mina do jogador volta livre: o ouro até o refresh sai na taxa antiga, o ciclo novo
    começa no pedido e a mina pode ser ocupada de novo na mesma linha (unique personagem+mina)."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None and castle.mines_at is not None
        templates = g.server.services.templates
        mine = g.server.services.world.mines[1]
        land = mines.occupy(snap, mine, mines.level_template(templates, 8), clock.now())
        castle.produced_at = clock.now()
        await g.server.services.characters.save(land, castle, snap.character)

        boundary = castle.mines_at + mines.MINE_PERIOD
        expected, _ = castle_mod.pending_gold(snap, templates, boundary)  # na taxa com a mina, até o refresh
        assert expected > 0
        gold = snap.character.gold
        clock.advance((boundary - clock.now()).total_seconds() + 60)

        got = await _grid(g, oc.grid_of(mine.x, mine.y))
        page = pb.PhysicListUpdateMsg.FromString(next(p.body for p in got if p.code == 4129))
        shown = next(w for w in page.wildLand if w.id == mine.id)
        assert (shown.occupyPlayerId, shown.state) == (0, mines.MINE_FREE)
        assert castle.mines_at == clock.now() and shown.createDate == mines.game_date(clock.now())
        after = castle_mod.gold_yield(snap, templates) * 60 // 3600  # o minuto depois do refresh: só os prédios
        assert mines.occupied(snap, mine) is None and snap.character.gold == gold + expected + after
        assert mines.mine_gold(snap, templates) == 0

        assert mines.occupy(snap, mine, land.template_id, clock.now()) is land  # a linha do ciclo vencido volta
        await g.server.services.characters.save(land)
        fresh = await g.server.services.characters.snapshot(g.user_id)
        assert mines.occupied(fresh, mine) is not None and len(fresh.wild_lands) == 1
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
        mines.occupy(snap, g.server.services.world.mines[0], mines.level_template(templates, 8), clock.now())
        per_hour = castle_mod.gold_yield(snap, templates) - buildings
        assert per_hour > 0
        end = mines.cycle_end(snap)
        castle.produced_at, snap.character.gold = end - timedelta(hours=1), 0
        clock.advance((end - clock.now()).total_seconds() + 3600)  # uma hora antes e uma depois do refresh
        castle_mod.settle(snap, templates, clock.now())
        assert castle.mines_at == clock.now() and mines.mine_gold(snap, templates) == 0
        assert snap.character.gold == (buildings + per_hour) + buildings


async def test_mina_de_outro_jogador_nao_bloqueia_a_instancia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """O mapa do castelo é uma instância de cada conta (só turco: replay #706 e cevre #11, mesmas minas, instâncias,
    robôs e createDate diferentes). A mina que outro jogador ocupou aparece livre e abre a luta (missão 60),
    e o castelo dele não entra no 4129 da instância."""
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    async with logged_in(tmp_path, novice=22500) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        other = await g.join("outro")
        mine = g.server.services.world.mines[0]
        await g.server.services.characters.save(WildLand(other.user_id, mine.id, g.server.services.clock.now()))

        got = await _grid(g, oc.grid_of(mine.x, mine.y))
        page = pb.PhysicListUpdateMsg.FromString(next(p.body for p in got if p.code == 4129))
        assert [c.occupyPlayerId for c in page.baseCastle] == [g.user_id, robots.ROBOT_USER_BASE]  # robô em (44,22)
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
        assert {w.type for w in page.wildLand} <= {20}  # só minas do mundo (geradas: o mapa 2 não tem captura)


async def test_castelos_robo_na_grade_da_instancia(tmp_path: Path) -> None:
    """Missão 100 (captura inglesa #532): o robô de (44,22) vem no 4129 da grade 0_0 com o próprio castelo,
    o de (59,56) na grade 1_1, com grau 8 e o nome da conta. Em outro mapa, nenhum."""
    async with logged_in(tmp_path, novice=19000) as g:
        castle = _snap(g).castle
        assert castle is not None
        got = await _grid(g, "0_0")
        page = pb.PhysicListUpdateMsg.FromString(next(p.body for p in got if p.code == 4129))
        [robo] = [c for c in page.baseCastle if c.id == 765958]
        assert (robo.mapId, robo.posX, robo.posY, robo.type, robo.state, robo.grade) == (castle.map_id, 44, 22, 1, 1, 8)
        assert robo.occupyPlayerId == robots.ROBOT_USER_BASE and robo.castleName == robo.occupyPlayerName
        assert robo.occupyPlayerName in {"Aillendre", "Addyn"}
        again = await _grid(g, "0_0")  # o nome sai da conta: o mesmo pedido devolve o mesmo nome
        twice = pb.PhysicListUpdateMsg.FromString(next(p.body for p in again if p.code == 4129))
        assert [c.occupyPlayerName for c in twice.baseCastle if c.id == 765958] == [robo.occupyPlayerName]

        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=castle.map_id, reqGrid="1_1"))
        page = pb.PhysicListUpdateMsg.FromString((await g.until(4129))[-1].body)
        assert [c.id for c in page.baseCastle] == [castle.id, 765957]
        assert (
            page.baseCastle[1].occupyPlayerName != robo.occupyPlayerName
        )  # os dois robôs da conta têm nomes distintos

        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=1, reqGrid="0_0"))  # mapa 1: não é a instância do jogador
        page = pb.PhysicListUpdateMsg.FromString((await g.until(4129))[-1].body)
        assert 765958 not in [c.id for c in page.baseCastle]


async def test_ataque_ao_castelo_robo_conta_a_missao_8_e_gasta_o_ataque(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missão 100 (m8 alvo 80_3, tile (44,22)): o 5160 no robô abre a luta inglesa (#1656-#1657: 140 do robô em
    luta, battleType 4, mapa 993, herói 11008 com o nome do robô e 2 pilhas 10102); o fim conta o tipo 8, manda o
    112 e o 4382 e gasta um ataque do dia (o PlayerMsg mostra o contador)."""

    async def lose(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:  # a captura é uma derrota com o exército todo morto (#1760); daqui venceria
            if unit.side == 1:
                unit.hp = 0
        return False

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", lose)
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None and snap.arena is not None
        snap.character.grades = 10  # |10 - 8| < 10: o cliente deixa atacar
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        snap.quests.append(Quest(g.user_id, 100, datetime.now(UTC)))
        snap.arena.day, snap.arena.attack_left = A.today(clock.now()), 5
        await g.server.services.characters.save(snap.arena)

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=44, posY=22))
        got = await g.until(157)
        # devoção do leed 10 "Plunder another player" no ataque, antes da luta (tutorial_en #1648-#1657; lá o 83 vem
        # depois dos 140): exército ×2, o próprio castelo, 4452, 3 com o ataque gasto, o robô em luta
        assert [p.code for p in got] == [4152, 83, 140, 140, 140, 4452, 3, 140, 157]
        own = pb.MapUpdatedMsg.FromString(got[4].body)
        assert (own.updatedType, own.baseCastle.occupyPlayerId) == (2, g.user_id)
        assert pb.PlayerMsg.FromString(got[6].body).attackLeftCount == 4
        leed = pb.LeedUpdatedRspMsg.FromString(got[0].body)
        assert ([x.templateId for x in leed.leed], leed.totalNum) == ([10], 10)
        robot = pb.MapUpdatedMsg.FromString(got[7].body)
        assert (robot.updatedType, robot.baseCastle.id, robot.baseCastle.state) == (2, 765958, 4)
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert (prepare.battleType, prepare.mapTempId) == (4, 993)
        assert [(x.tempId, x.side, x.pos, x.hp) for x in prepare.soldiers if x.side == 2] == [
            (10102, 2, 1, 282),
            (10102, 2, 7, 282),
        ]
        [enemy] = [h for h in prepare.heros if h.side == 2]
        assert (enemy.tempId, enemy.type, enemy.pos, enemy.grade, enemy.hp) == (11008, 2, 6, 8, 240)
        assert list(enemy.skillId) == [10711, 10811]
        assert enemy.nickName == robot.baseCastle.occupyPlayerName
        assert snap.arena.attack_left == 4  # gasta ao começar a luta

        strategy = snap.character.strategy
        got = await g.fight(prepare)
        got += await g.idle()
        report = pb.BattleReportMsg.FromString(next(p.body for p in got if p.code == 4103))
        assert report.battleScene == 6
        after = [p.code for p in got if p.code not in (153, 75, 154, 156, 4600)]
        assert after == [150, 109, 3, 4103, 150, 100, 112, 148, 140, 140, 140, 4382]  # #1758-#1770 sem o 150 cheio
        back = pb.MapUpdatedMsg.FromString([p.body for p in got if p.code == 140][-1])
        assert (back.baseCastle.id, back.baseCastle.state) == (765958, 1)
        # a missão 100 conta vencendo ou perdendo (#1765: derrota com condition_1 1)
        quest = pb.QuestUpdatedRspMsg.FromString(next(p.body for p in got if p.code == 112)).quest[0]
        assert (quest.templateId, quest.condition_1) == (100, 1)
        assert pb.PlayerMsg.FromString(next(p.body for p in got if p.code == 3)).attackLeftCount == 4
        movie = pb.FightOverMoiveMsg.FromString(next(p.body for p in got if p.code == 4382))
        # derrota, como na captura: o Daru é o exército inteiro (#1762: 172 = as 172 tropas)
        assert report.battleResult == 2 and movie.strategy == report.strategyBonus == 150
        assert snap.character.strategy == strategy + movie.strategy


async def test_castelo_robo_recusa_sem_ataque_ou_com_diferenca_de_nivel(tmp_path: Path) -> None:
    """O cliente só ataca com ataque no dia e com menos de 10 níveis de diferença do castelo (grau 8). Recusa
    é 140 parado: sem luta, sem gasto."""
    async with logged_in(tmp_path, novice=22500) as g:
        snap = _snap(g)
        castle = snap.castle
        assert castle is not None and snap.arena is not None
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        snap.arena.day = A.today(g.server.services.clock.now())

        snap.character.grades, snap.arena.attack_left = 10, 0
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=44, posY=22))  # sem ataque no dia
        assert [p.code for p in await g.until(140)] == [140]

        snap.character.grades, snap.arena.attack_left = 18, 5
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=44, posY=22))  # 18 - 8 = 10
        assert [p.code for p in await g.until(140)] == [140]
        assert await g.idle() == []  # nem batalha nem gasto
        assert snap.arena.attack_left == 5


async def test_castelo_robo_so_existe_na_instancia_do_castelo(tmp_path: Path) -> None:
    """O robô segue a regra da mina: só na instância do castelo. Com o castelo no mapa 1 (compartilhado), o 4129
    desse mapa não traz o robô de (44,22), e o 5160 no tile dele só para o exército, sem luta nem ataque gasto."""
    async with logged_in(tmp_path, novice=22500) as g:
        snap = await _set(g, grades=11)  # o mapa 1 pede nível 11
        castle = snap.castle
        assert castle is not None and snap.arena is not None
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        castle.energy = 500
        g.client.send(5176, pb.CastleReqMsg(magId=1, posX=0, posY=0, payType=1))
        assert [p.code for p in await g.until(105)] == [
            140,
            152,
            105,
        ]  # mudou de mapa: o 152 (oficial_20261023-153200-1 #186)
        assert castle.map_id == 1

        got = await _grid(g, "0_0")
        page = pb.PhysicListUpdateMsg.FromString(next(p.body for p in got if p.code == 4129))
        assert 765958 not in [c.id for c in page.baseCastle]

        attacks = snap.arena.attack_left
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=1, posX=44, posY=22))
        assert [p.code for p in await g.until(140)] == [140]  # sem luta: o tile do robô é da instância
        assert await g.idle() == []
        assert snap.arena.attack_left == attacks


async def test_dois_ataques_seguidos_ao_robo_geram_uma_luta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dois 5160 seguidos no robô: o primeiro abre a luta e gasta um ataque; o segundo, com a luta em curso,
    só para o exército (140)."""
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = await _set(g, grades=10)
        castle = snap.castle
        assert castle is not None and snap.arena is not None
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        snap.arena.day, snap.arena.attack_left = A.today(clock.now()), 5
        await g.server.services.characters.save(snap.arena)

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=44, posY=22))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=castle.map_id, posX=44, posY=22))  # a luta segue em curso
        second = [p.code for p in await g.until(140)]
        assert second[-1] == 140 and 157 not in second
        assert snap.arena.attack_left == 4  # um só gasto
        # o 1º 5160 já terminou (um pacote por vez): o gasto está no banco antes do fim da luta
        stored = await g.server.services.characters.snapshot(g.user_id)
        assert stored.arena is not None and stored.arena.attack_left == 4

        await g.fight(prepare)
        await g.idle()


async def test_ocupacao_vence_ao_logar_depois_do_refresh(tmp_path: Path) -> None:
    """Quem volta ao jogo depois do refresh já entra com a mina livre: a linha sai no login, antes do 109 e do 152."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        assert snap.castle is not None
        snap.castle.mines_at = clock.now() - mines.MINE_PERIOD + timedelta(seconds=60)  # a 1 min do refresh
        first = g.server.services.world.mines[0]
        await g.server.services.characters.save(snap.castle, WildLand(g.user_id, first.id, clock.now()))
        gold_before = (await g.server.services.characters.snapshot(g.user_id)).character.gold
        clock.advance(120)  # passou o refresh; a chave do login (30 min) ainda vale
        await g.connect()
        fresh = await g.server.services.characters.snapshot(g.user_id)
        assert mines.occupied(fresh, first) is None
        assert fresh.castle is not None and fresh.castle.mines_at == clock.now()
        assert fresh.character.gold >= gold_before  # o settle do refresh nunca tira ouro


async def test_catalogo_do_mundo_vem_do_banco(tmp_path: Path) -> None:
    """Minas, guardas, robôs e monstros saem das tabelas das migrações 0027, 0028 e 0040, na ordem da captura."""
    async with logged_in(tmp_path, novice=22500) as g:
        world = g.server.services.world
        assert [(m.id, m.x, m.y, m.levels) for m in world.mines_on(oc.BASE_MAP)] == [
            (853876, 16, 34, range(8, 11)), (853877, 36, 34, range(8, 11)),
            (853874, 71, 54, range(8, 11)), (853875, 54, 64, range(8, 11)),
        ]  # fmt: skip
        assert {lv: world.mine_guards[lv] for lv in (8, 9, 10)} == {8: 6504, 9: 6505, 10: 6505}
        assert len(world.mines_on(1)) == 60 and len(world.mine_guards) == 53  # 0064: mapa 1 e níveis 11 a 60
        assert [(r.id, r.x, r.y, r.grade) for r in world.robots] == [(765958, 44, 22, 8), (765957, 59, 56, 8)]
        assert [str(n) for n in world.robot_names] == ["Aillendre", "Addyn"]
        assert dict(world.monster_counts[2]) == {1: 40, 2: 20, 3: 5} and 100 not in world.monster_counts
        assert world.monsters[210127].fight_capacity == 746796 and world.monsters[210101].fight_capacity == 1033


async def test_unidade_de_cada_monstro_bate_com_o_tempinfos(tmp_path: Path) -> None:
    """world_monsters (0029): todo monstro (MasterType 21) tem uma unidade com o mesmo nome e nível; o normal
    é pawn, a elite e o chefe são herói (com AddName de elite ou BOSS)."""
    async with logged_in(tmp_path, novice=22500) as g:
        templates, world = g.server.services.templates, g.server.services.world
        rows = list(templates.find("MapPhysicsTempInfos", MasterType="21"))
        assert len(rows) == 30 == len(world.monsters)
        for row in rows:
            unit = world.monsters[int(row["TemplateId"])]
            if row["Property1"] == "1":
                pawn = templates.get("PawnTempInfos", unit.pawn_id)
                assert unit.hero_id == 0 and (pawn["PawnName"], pawn["Level"]) == (
                    row["MapPhysicsTempName"],
                    row["Grades"],
                )
            else:
                hero = templates.get("GameHeroTemp", unit.hero_id)
                assert unit.pawn_id == 0 and (hero["TemplateName"], hero["Grades"]) == (
                    row["MapPhysicsTempName"],
                    row["Grades"],
                )
                assert hero["AddName"] == "Elite" or hero["AddName"].startswith("BOSS")


async def test_ocupacao_sem_nivel_gravado_e_completada_no_login(tmp_path: Path) -> None:
    """Ocupação de antes da 0027 (sem ``template_id``) no ciclo atual: o login grava o nível sorteado e a mina
    volta a render, em vez de ficar 0 até o refresh."""
    clock = FakeClock()
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        mine = g.server.services.world.mines[0]
        await g.server.services.characters.save(WildLand(g.user_id, mine.id, clock.now()))
        await g.connect()
        fresh = await g.server.services.characters.snapshot(g.user_id)
        land = mines.occupied(fresh, mine)
        assert land is not None and (land.pos_x, land.pos_y) == (16, 34)
        templates = g.server.services.templates
        assert land.template_id == mines.draw(fresh, g.server.services.world, templates, mine)[0]
        assert mines.mine_gold(fresh, templates) > 0


async def test_chefes_do_mapa_e_relogio_de_2_horas(tmp_path: Path) -> None:
    """9525 -> 4938 com os 5 chefes (bossType 3) do sorteio do mapa 2, iguais em todo pedido do ciclo, e o
    relógio que as duas capturas mostram: 2026-05-21 22:00 (local; testes em UTC) menos 4828 s (transfer) e 5775 s (cevre) (só turco)."""
    clock = FakeClock(datetime(2026, 5, 21, 20, 39, 31, 290000, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        g.client.send(9525, pb.MapBossQuestMsg(mapId=2))
        msg = pb.MapBossMsg.FromString((await g.until(4938))[-1].body)
        templates, world = g.server.services.templates, g.server.services.world
        chiefs = [m for m in monsters.on_map(world, templates, 2, clock.now()) if m.boss_type == monsters.CHIEF]
        rows = [templates.get("MapPhysicsTempInfos", m.template_id) for m in chiefs]
        assert [(b.bossName, b.grade, b.type, b.x, b.y) for b in msg.bosslist] == [
            (r["MapPhysicsTempName"], int(r["Grades"]), 1, m.x, m.y) for r, m in zip(rows, chiefs, strict=True)
        ]
        assert len(chiefs) == 5 and all(r["Property1"] == "3" for r in rows)
        assert (msg.leftBossTime, msg.count1, msg.leftFogTime) == (4828, 0, 0)
        g.client.send(9525, pb.MapBossQuestMsg(mapId=2))
        assert pb.MapBossMsg.FromString((await g.until(4938))[-1].body).bosslist == msg.bosslist

        g.client.send(
            9525, pb.MapBossQuestMsg(mapId=100)
        )  # instância do castelo: sem chefes (inglesa #526: 4938 sem bosslist)
        msg = pb.MapBossMsg.FromString((await g.until(4938))[-1].body)
        assert (len(msg.bosslist), msg.leftBossTime) == (0, 4828)

        left = functools.partial(monsters.refresh_left, templates)
        assert left(datetime(2026, 5, 21, 20, 23, 44, 227000, tzinfo=UTC)) == 5775  # só turco: cevre #3
        assert left(datetime(2026, 5, 21, 22, tzinfo=UTC)) == 7200  # 22:00: o próximo é 00:00
        assert left(datetime(2026, 5, 21, 21, 59, 59, 900000, tzinfo=UTC)) == 1  # nunca 0
        assert left(datetime(2026, 5, 22, 3, tzinfo=UTC)) == 5 * 3600  # 03:00: sem refresh até as 08:00
        start = monsters.cycle_start(templates, datetime(2026, 5, 22, 3, tzinfo=UTC))
        assert start == datetime(2026, 5, 22, tzinfo=UTC)  # o ciclo das 00:00 locais


async def test_monstros_dos_wilds_no_4129_como_na_captura(tmp_path: Path) -> None:
    """8201 numa grade do mapa 2 com monstro: type 21 como no oficial (oficial_20261023-171155-1 #6919: um armyPawn
    por pilha do normal, nenhum na elite e no chefe, refreshTime 0, size = Property2, createDate = começo do ciclo).
    O ciclo novo sorteia outros pontos."""
    clock = FakeClock(datetime(2026, 5, 21, 20, 39, 31, tzinfo=UTC))  # 20:39: ciclo das 20:00
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        templates, world = g.server.services.templates, g.server.services.world
        found = monsters.on_map(world, templates, 2, clock.now())
        assert [sum(m.boss_type == t for m in found) for t in (1, 2, 3)] == [40, 20, 5]
        assert len({m.id for m in found}) == 65 and monsters.on_map(world, templates, 100, clock.now()) == []
        m = found[0]
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=2, reqGrid=oc.grid_of(m.x, m.y)))
        page = pb.PhysicListUpdateMsg.FromString((await g.until(4129))[-1].body)
        land = next(w for w in page.wildLand if w.id == m.id)
        row = templates.get("MapPhysicsTempInfos", m.template_id)
        assert (land.type, land.templateId, land.posX, land.posY, land.state) == (21, m.template_id, m.x, m.y, 1)
        assert (land.level, land.bossType, land.size) == (int(row["Grades"]), m.boss_type, int(row["Property2"]))
        assert (land.refreshTime, land.createDate) == (0, "2026-05-21 20:00:00")
        assert len(land.armyPawn) == monsters.stacks(templates, m)
        later = monsters.on_map(world, templates, 2, clock.now() + timedelta(hours=2))
        assert [(n.x, n.y) for n in later] != [(n.x, n.y) for n in found]

        clock.advance(2 * 3600)  # virada com o jogador parado: o 20008 tira o velho (state 0) da grade vista
        g.client.send(20008)
        gone = pb.MapUpdatedMsg.FromString((await g.until(140))[-1].body).wildLand
        assert (gone.id, gone.posX, gone.posY, gone.state) == (m.id, m.x, m.y, 0)


async def test_divine_light_tira_a_nevoa_por_20_segundos(tmp_path: Path) -> None:
    """5006 da Divine Light (2131055, SonType 316): gasta um, 4939 com leftFogTime 20, e o 4938 do mapa do
    castelo leva o que sobra até zerar."""
    clock = FakeClock(datetime(2026, 5, 21, 17, 39, 31, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        assert snap.castle is not None
        light = Item(g.user_id, 2131055, pos=0, count=2)
        snap.items.append(light)
        await g.server.services.characters.save(light)
        g.client.send(5006, pb.ItemUseMsg(pos=0, count=2, bagType=1))
        assert pb.MapBossMsg.FromString((await g.until(4939))[-1].body).leftFogTime == 20
        assert light.count == 1
        clock.advance(5)
        g.client.send(9525, pb.MapBossQuestMsg(mapId=snap.castle.map_id))
        assert pb.MapBossMsg.FromString((await g.until(4938))[-1].body).leftFogTime == 15
        g.client.send(9525, pb.MapBossQuestMsg(mapId=2))  # outro mapa: com névoa
        assert pb.MapBossMsg.FromString((await g.until(4938))[-1].body).leftFogTime == 0
        clock.advance(20)
        g.client.send(9525, pb.MapBossQuestMsg(mapId=snap.castle.map_id))
        assert pb.MapBossMsg.FromString((await g.until(4938))[-1].body).leftFogTime == 0


async def test_luta_com_monstro_normal_abate_e_conta_no_dia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """5160 num monstro normal do mapa 2 (visto: oficial_20261023-171155-1 #6916-#6988): 140 em luta (state 4, com o
    curArmyId), 157 battleType 3841 com 2 pilhas de 350 nas pos 2 e 8 e só o herói do jogador (livingId 3); a vitória
    não tira tropa nem dá Daru, grava o abate do ciclo, tira o monstro (140 state 0), conta no dia (4938 count1); o
    baú vem no 8201 seguinte (4940) e abre com "Wilds Slayer Rewards..."; o próximo 5160 recusa."""

    async def win(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 2:
                unit.hp = 0
        return True

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", win)
    clock = FakeClock(datetime(2026, 5, 21, 17, 39, 31, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        snap.pawns.append(Pawn(g.user_id, 10101, army_count=150))
        templates, world = g.server.services.templates, g.server.services.world
        found = monsters.on_map(world, templates, 2, clock.now())
        m = min((x for x in found if x.boss_type == 1), key=lambda x: monsters.level(templates, x))
        assert monsters.level(templates, m) == 10
        snap.character.grades = 20  # 10 abaixo: ainda conta (help: 15 abaixo não conta)
        assert snap.leader is not None
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=2, reqGrid=oc.grid_of(m.x, m.y)))
        await g.until(169)

        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=2, posX=m.x, posY=m.y))
        got = await g.until(157)
        assert [p.code for p in got] == [140, 140, 140, 157]
        fighting = pb.MapUpdatedMsg.FromString(got[2].body).wildLand
        assert (fighting.state, list(fighting.curArmyId)) == (monsters.MONSTER_FIGHTING, [g.user_id])
        prepare = pb.BattlePrepareMsg.FromString(got[-1].body)
        assert prepare.battleType == 3841
        assert [(x.livingId, x.tempId, x.side, x.pos, x.hp) for x in prepare.soldiers] == [
            (1, 6992, 2, 2, 350), (2, 6992, 2, 8, 350)
        ]  # fmt: skip
        assert [(h.livingId, h.side) for h in prepare.heros] == [(3, 1)]
        strategy = snap.character.strategy

        got = await g.fight(prepare)
        got += await g.idle()
        report = pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body)
        assert (report.battleResult, report.battleScene, report.strategyBonus) == (1, 5, 0)
        assert snap.character.strategy == strategy and snap.pawns[-1].army_count == 150
        assert 4940 not in [p.code for p in got]
        gone = [pb.MapUpdatedMsg.FromString(p.body).wildLand for p in got if p.code == 140]
        assert (gone[-1].id, gone[-1].state) == (m.id, monsters.MONSTER_GONE)
        info = pb.MapBossMsg.FromString(next(p for p in got if p.code == 4938).body)
        assert (info.count1, info.count2, info.count3) == (1, 0, 0)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.kills_normal == 1
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=2, reqGrid=oc.grid_of(m.x, m.y)))
        got = await g.until(169)
        assert [p.code for p in got][-3:] == [4129, 4940, 169]
        box = pb.MapBoxMsg.FromString(got[-2].body).boxlist  # baú no tile, gravado
        assert [(x.mapId, x.x, x.y, x.type, x.grade, x.userId) for x in box] == [(2, m.x, m.y, 1, 10, g.user_id)]
        assert [b.id for b in saved.wild_boxes] == [int(box[0].boxId)]

        monkeypatch.setattr(monsters, "loot", lambda *_: [(-100, 500), (-300, 700), (2131057, 2)])
        gold = snap.character.gold
        g.client.send(9526, box[0])
        got = await g.idle()
        assert 4940 not in [p.code for p in got]
        text = "Wilds Slayer RewardsMystery Stone x2, 700 Daru, 500 Gold"
        assert [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code in (111, 83)] == [text, text]
        assert snap.character.gold == gold + 500 and any(i.template_id == 2131057 for i in snap.items)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.wild_boxes == [] and saved.character.gold == gold + 500
        g.client.send(9526, box[0])  # de novo: o baú já não existe
        assert all(p.code != 4940 for p in await g.idle())

        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=2, reqGrid=oc.grid_of(m.x, m.y)))
        page = pb.PhysicListUpdateMsg.FromString((await g.until(4129))[-1].body)
        assert m.id not in [w.id for w in page.wildLand]
        await g.until(169)
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=2, posX=m.x, posY=m.y))
        assert [p.code for p in await g.idle()] == [140]  # abatido no ciclo: só para

        clock.advance(2 * 3600)  # ciclo novo: o mesmo id é outro monstro, vivo
        again = next(x for x in monsters.on_map(world, templates, 2, clock.now()) if x.id == m.id)
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=2, reqGrid=oc.grid_of(again.x, again.y)))
        page = pb.PhysicListUpdateMsg.FromString((await g.until(4129))[-1].body)
        assert m.id in [w.id for w in page.wildLand if w.type == 21]


async def test_chefe_abatido_fica_no_painel_como_morto(tmp_path: Path) -> None:
    """bosslist: o chefe abatido no ciclo vem com type 0 ("(Killed)", language bossStatus0)."""
    clock = FakeClock(datetime(2026, 5, 21, 17, 39, 31, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        templates, world = g.server.services.templates, g.server.services.world
        chief = next(x for x in monsters.on_map(world, templates, 2, clock.now()) if x.boss_type == monsters.CHIEF)
        kill = WildMonsterKill(2, chief.id, chief.born, g.user_id, clock.now())
        await g.server.services.characters.write(lambda uow: uow.wild_kills.add(kill))
        g.client.send(9525, pb.MapBossQuestMsg(mapId=2))
        msg = pb.MapBossMsg.FromString((await g.until(4938))[-1].body)
        assert [b.type for b in msg.bosslist] == [0, 1, 1, 1, 1]


async def test_bau_com_mochila_cheia_vai_pelo_correio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """9526 sem espaço: o baú some e o conteúdo chega como anexo no correio do jogo (148), 5 por carta."""
    from wartune_server.domain.models import WildBox
    from wartune_server.game import bag

    clock = FakeClock(datetime(2026, 5, 21, 17, 39, 31, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        snap = _snap(g)
        box = WildBox(g.user_id, 2, 50, 60, 2, 30, clock.now())
        snap.wild_boxes.append(box)
        await g.server.services.characters.save(box)
        drops = [(2131057, n) for n in range(1, 7)]  # 6 anexos: 2 cartas
        monkeypatch.setattr(monsters, "loot", lambda *_: drops)
        monkeypatch.setattr(bag, "BAG_BASE", 0)  # mochila cheia
        g.client.send(9526, pb.ArmyBoxMsg(boxId=str(box.id)))
        got = await g.idle()
        assert [p.code for p in got].count(148) == 2 and 4940 in [p.code for p in got]
        chars = g.server.services.characters
        mails = await chars.read(lambda uow: uow.mails.by_receiver(g.user_id))
        annexes = await chars.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
        assert len(mails) == 2 and mails[0].title == "Wilds Chest"
        assert sorted((a.template_id, a.count) for a in annexes) == drops
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.wild_boxes == [] and not any(i.template_id == 2131057 for i in saved.items)


async def test_tabela_de_queda_semeada_e_valida(tmp_path: Path) -> None:
    """A semente da 0030: todo item existe (ou é moeda), chance entre 0 e 1, e cada tipo em todo nível de 10 a
    80 tem ouro; o BOSS de 40+ sempre dá a Legendary Stone do nível."""
    from wartune_server.game import rewards

    async with logged_in(tmp_path, novice=22500) as g:
        templates, world = g.server.services.templates, g.server.services.world
        drops = world.monster_drops
        assert drops and all(0 < d.chance <= 1 and 0 < d.min_count <= d.max_count for d in drops)
        assert all(d.template_id in rewards.CURRENCIES or templates.get("ItemTempInfos", d.template_id) for d in drops)
        for t in (1, 2, 3):
            for lvl in range(10, 81):
                assert any(d.boss_type == t and d.template_id == -100 and d.chance == 1 and
                           d.min_level <= lvl <= d.max_level for d in drops), (t, lvl)  # fmt: skip
        import random

        got = monsters.loot(world, 3, 72, random.Random(0))
        count = {t: sum(n for i, n in got if i == t) for t, _ in got}
        assert count[2129700] == 2 and count[2131057] >= 8 and count[-100] >= 180_000  # 0032: os vídeos do Lv70
        low = monsters.loot(world, 3, 45, random.Random(0))
        assert dict(low)[2131057] >= 10  # abaixo de 60 vale a 0030


def test_tabela_de_queda_por_tipo_e_nivel() -> None:
    """loot: só as linhas do tipo e da faixa de nível; cada uma sorteada sozinha pela chance."""
    import random

    from wartune_server.domain.world import MonsterDrop, World

    world = World(monster_drops=(MonsterDrop(1, 1, 49, -100, 1.0, 10, 10), MonsterDrop(1, 50, 80, -100, 1.0, 99, 99),
                                 MonsterDrop(2, 1, 80, -300, 1.0, 5, 5), MonsterDrop(1, 1, 80, 2131057, 0.0, 1, 1)))  # fmt: skip
    rng = random.Random(1)
    assert monsters.loot(world, 1, 20, rng) == [(-100, 10)]
    assert monsters.loot(world, 1, 60, rng) == [(-100, 99)]
    assert monsters.loot(world, 2, 60, rng) == [(-300, 5)]
    half = World(monster_drops=(MonsterDrop(3, 1, 80, 2131056, 0.5, 1, 3),))
    got = [monsters.loot(half, 3, 70, rng) for _ in range(2000)]
    assert 800 < sum(bool(x) for x in got) < 1200 and {n for x in got for _, n in x} == {1, 2, 3}


def test_quinze_niveis_abaixo_nao_conta_e_o_limite_do_dia() -> None:
    """count_kill: 15 níveis abaixo não conta; o limite vem do WorldMapKill (5,3,1)."""
    from wartune_server.domain.models import Character
    from wartune_server.templates.repository import GameTemplates

    templates = GameTemplates({"MapPhysicsTempInfos": [{"TemplateId": "210103", "Grades": "10"}],
                               "ConfigInfos": []})  # fmt: skip
    chief = monsters.Monster(1, 2, 210103, 3, 50, 50, datetime(2026, 5, 21, tzinfo=UTC))
    c = Character(account_id=1, server_id=1, created_at=datetime(2026, 5, 21, tzinfo=UTC))
    c.grades = 25
    assert not monsters.count_kill(c, templates, chief) and c.kills_boss == 0
    c.grades = 24
    assert monsters.count_kill(c, templates, chief) and c.kills_boss == 1
    assert not monsters.count_kill(c, templates, chief) and c.kills_boss == 1  # limite 1 por dia


async def test_luta_de_sessao_que_caiu_nao_prende_o_monstro(tmp_path: Path) -> None:
    """Luta cancelada (a sessão caiu: on_end não roda): o monstro volta a state 1 sem limpeza explícita."""
    clock = FakeClock(datetime(2026, 5, 21, 17, 39, 31, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        templates, world = g.server.services.templates, g.server.services.world
        m = next(x for x in monsters.on_map(world, templates, 2, clock.now()) if x.boss_type == 1)
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=2, posX=m.x, posY=m.y))
        await g.until(157)
        session = g.server.online.get(g.user_id)
        assert session is not None and session.battle is not None
        wilds = session.ctx.wilds
        assert wilds.state(m, set()) == monsters.MONSTER_FIGHTING
        session.battle.cancel()
        await g.idle()
        assert wilds.state(m, set()) == monsters.MONSTER_ALIVE


async def test_derrota_para_monstro_nao_abate_nem_conta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A luta com monstro pode ser perdida (visto: oficial_20261023-171155-1 #7227-#7238): 4103 com derrota, o
    monstro volta a state 1, o exército volta para casa (140 no castelo), sem abate nem contador e sem 4938."""
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    clock = FakeClock(datetime(2026, 5, 21, 17, 39, 31, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        templates, world = g.server.services.templates, g.server.services.world
        found = monsters.on_map(world, templates, 2, clock.now())
        m = max((x for x in found if x.boss_type == 2), key=lambda x: monsters.level(templates, x))
        g.client.send(8201, pb.PhysicUpdateReqMsg(mapId=2, reqGrid=oc.grid_of(m.x, m.y)))
        await g.until(169)
        g.client.send(5160, pb.MapPhysicAttackMsg(mapId=2, posX=m.x, posY=m.y))
        prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
        assert [h.tempId for h in prepare.heros if h.side == 2] == [world.monsters[m.template_id].hero_id]
        got = await g.fight(prepare)
        got += await g.idle()
        assert pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body).battleResult == 2
        back = [pb.MapUpdatedMsg.FromString(p.body) for p in got if p.code == 140]
        assert (back[-2].wildLand.id, back[-2].wildLand.state) == (m.id, monsters.MONSTER_ALIVE)
        snap = _snap(g)
        assert snap.castle is not None
        home = (snap.castle.pos_x - oc.HOME_OFFSET, snap.castle.pos_y - oc.HOME_OFFSET)
        assert (back[-1].army.curPosX, back[-1].army.curPosY, back[-1].army.state) == (*home, 0)
        assert 4938 not in [p.code for p in got]
        cycle = monsters.cycle_start(templates, clock.now())
        assert await g.server.services.characters.read(lambda uow: uow.wild_kills.in_cycle(2, cycle)) == set()


async def test_voltar_ao_castelo_so_manda_o_4382_com_luta_pendente(tmp_path: Path) -> None:
    """tutorial_en #576: 4382 depois da luta; #826 e #1128: sem luta, nada (o OuterCityManager quebraria)."""
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8747, pb.SimplePropertyMsg(param7=True))
        assert 4382 not in [p.code for p in await g.idle()]
        g.server.online.get(g.user_id).outer_fight_over = True  # type: ignore[union-attr]
        g.client.send(8747, pb.SimplePropertyMsg(param7=True))
        assert [p.code for p in await g.idle()].count(4382) == 1


def test_formacao_muda_as_posicoes_na_luta() -> None:
    """8276: herói e tropa na fileira 1 ou 3. (visto) tutorial_en #727 (herói 1, tropa 3): herói 4, tropas 3 e 9;
    oficial_20261023-171155-1 (herói 3, tropa 1, as 25 lutas): herói 6, tropas 1 e 7."""
    from types import SimpleNamespace

    from wartune_server.templates.repository import GameTemplates

    templates = GameTemplates.parse(Path("data/templates/tempinfos.xml").read_bytes())
    assert (oc.hero_pos(1), oc.hero_pos(3), oc.hero_pos(0)) == (4, 6, 4)
    for fight_pos, want in ((3, [3, 9]), (1, [1, 7]), (0, [3, 9])):
        snap = SimpleNamespace(pawns=[Pawn(1, 10101, army_count=150, fight_pos=fight_pos)], buildings=[])
        soldiers, _ = oc.army_soldiers(snap, templates)  # type: ignore[arg-type]
        assert [s["pos"] for s in soldiers] == want


async def test_teleporte_do_exercito_como_no_oficial(tmp_path: Path) -> None:
    """(visto) oficial_20261023-171155-1 #7307-#7310: 8326 para um tile além de 1000 (696, 3793): 140 do exército
    parado, 4237 sem mapId com a energia que sobrou (100 por teleporte) e 111 "Teleportation Complete"; o exército
    fica lá. Fora do mapa: 4263."""
    async with logged_in(tmp_path, novice=22500) as g:
        snap = _snap(g)
        assert snap.castle is not None
        snap.castle.energy = 200
        size = oc.map_size(g.server.services.templates, snap.castle.map_id)
        assert size is not None
        x, y = size[0] - 5, size[1] - 5
        g.client.send(8326, pb.ArmyPositionMsg(posX=x, posY=y, payType=2))
        got = await g.until(111)
        assert [p.code for p in got] == [140, 4237, 111]
        moved = pb.ArmyPositionMsg.FromString(got[1].body)
        assert (moved.posX, moved.posY, moved.mapId, moved.leftEnergy) == (x, y, 0, 100)
        assert pb.ChatChannelMsg.FromString(got[2].body).encodeMsg == "Teleportation Complete"
        assert g.server.online.get(g.user_id).outer_army == (snap.castle.map_id, x, y)  # type: ignore[union-attr]
        g.client.send(8326, pb.ArmyPositionMsg(posX=size[0], posY=1, payType=2))
        assert [p.code for p in await g.idle()] == [4263]


async def test_chefe_morto_e_anunciado_para_o_servidor(tmp_path: Path) -> None:
    """(só turco: teknoloji_upgrade #1) 83 canal 2 para todos, com o link 111 do painel dos chefes."""
    from wartune_server.game.handlers import outer_city as hoc

    clock = FakeClock(datetime(2026, 5, 21, 17, 39, 31, tzinfo=UTC))
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        other = await g.join("outro")
        await g.idle()
        await other.idle()
        templates, world = g.server.services.templates, g.server.services.world
        chief = next(x for x in monsters.on_map(world, templates, 2, clock.now()) if x.boss_type == monsters.CHIEF)
        s = g.server.online.get(g.user_id)
        assert s is not None
        hoc._boss_killed(s, chief)
        mine, theirs = [pb.ChatChannelMsg.FromString((await c.until(83))[-1].body) for c in (g, other)]
        name = templates.get("MapPhysicsTempInfos", chief.template_id)["MapPhysicsTempName"]
        assert mine == theirs and mine.channel == 2
        assert f"has killed the Wilds BOSS {name} and won a reward" in mine.encodeMsg
        assert mine.encodeMsg.endswith('<a t="111" name="Find the Wilds BOSS"/>')
