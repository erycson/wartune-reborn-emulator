"""Cidade externa (mapa do castelo): grade de exércitos, andar, voltar ao castelo, ataques extras,
mudar o castelo de lugar e a volta para a cidade no fim do tutorial.

Regras e fontes em ``game/outer_city.py``, ``mines.py``, ``robots.py``, ``bosses.py`` e
``docs/cidade-externa.md``. O mapa do castelo é uma instância do jogador (o castelo e as 4 minas do
mapa 100); nos mapas compartilhados (1 a 5) aparecem os castelos dos outros jogadores. Quando o cliente
pede algo que depende de exército alheio ou de terra selvagem, o pedido é recusado com log e o que o
cliente precisa para não travar é mandado.
"""

from __future__ import annotations

import asyncio
import math

from ...domain.models import Castle
from ...domain.world import Mine, RobotCastle
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import pay
from .. import arena as A
from .. import bosses, mines, robots, rules
from .. import castle as cs
from .. import outer_city as oc
from ..battle import Battle
from ..builders import login as b
from ..builders.army import castle_pawns
from ..builders.player import quest_update
from ..castle import castle_yield, politics_msg
from ..router import router
from ..session import GameSession
from . import events
from .campaign import player_hero
from .login import army, player_info

S_PLAYER, S_RESET, S_MAP_SYNC, S_TRANSFER, S_RETURN = 3, 4202, 140, 105, 98
S_MAP_BOSS, S_PHYSICS, S_GRID_ARMY, S_FIGHT_MOVIE = 4938, 4129, 169, 4382
S_FULL_ARMY, S_REPORT, S_ARMY_PAWN, S_QUESTS, S_POLITICS = 150, 4103, 100, 112, 152
ARMY_IDLE, ARMY_MOVING, ARMY_FIGHTING = 0, 1, 2  # MapUpdatedMsg/ArmyArmyMsg.state
# replay #761-#767: 18 tiles em 2,43 s. ponytail: velocidade fixa, sem montaria nem efeitos
WALK_SECONDS_PER_TILE = 0.134
MAP_ARMY, MAP_WILD = 3, 1  # MapUpdatedMsg.updatedType
OCCUPY = 7  # QuestCondictionInfos.CondictionType: ocupar terra (Para1 = SonType, missão 60)
LEED_MINE = 9  # LeedTemp: ocupar mina (replay #741)
ATTACK_CASTLE = 8  # QuestCondictionInfos.CondictionType: atacar cidade (100, 411 e 765; Para1 1 = vitória)


def _army_now(s: GameSession, state: int = ARMY_IDLE) -> pb.ArmyArmyMsg:
    """O próprio exército onde ele está agora (no castelo ou no último ponto andado)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    msg = army(s, snap)[0]
    msg.mapId, msg.curPosX, msg.curPosY = oc.position(snap.castle, s.outer_army)
    msg.state = state
    return msg


def _army_brief(s: GameSession, state: int = ARMY_IDLE) -> pb.ArmyArmyMsg:
    """O exército como o oficial manda no 140 e no 169 (compacto, com ``heroTempId`` e ``job``)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    return b.brief_army(_army_now(s), rules.job_type(snap.character.job), snap.leader.template_id, state)


def _grid_msg(s: GameSession, grids: set[str], map_id: int) -> pb.OutercityArmyUpdatedGridMsg:
    """169: o exército próprio se cair numa das grades pedidas no mesmo mapa; senão lista vazia."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    msg = pb.OutercityArmyUpdatedGridMsg()
    map_now, x, y = oc.position(snap.castle, s.outer_army)
    if map_id == map_now and oc.grid_of(x, y) in grids:
        msg.updatedArmy.add().CopyFrom(_army_brief(s))
    return msg


def _send_player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _castle_state(s: GameSession) -> None:
    """105 com o castelo como está: resposta de recusa (o cliente só troca de lugar se a posição mudar)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    castle = snap.castle
    s.send(
        S_TRANSFER,
        pb.CastleReqMsg(magId=castle.map_id, posX=castle.pos_x, posY=castle.pos_y, leftEnergy=castle.energy),
    )


async def refresh(s: GameSession) -> None:
    """Refresh de 12 h das minas (``castle.settle`` vira o ciclo). Sem tarefa periódica: roda ao logar,
    nos pedidos de mina (8201, 5160 e o fim da luta) e em todo ``settle`` de ouro, então quem fica online
    cruzando o refresh vê a mina cair no próximo pedido."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    now = s.ctx.clock.now()
    if filled := mines.backfill(snap, s.ctx.world, s.ctx.templates):
        await s.ctx.characters.save(*filled)
    if snap.castle.mines_at is not None and now < mines.cycle_end(snap):
        return
    cs.settle(snap, s.ctx.templates, now)
    await s.ctx.characters.save(snap.character, snap.castle)


@router.on(9525)
async def map_boss(s: GameSession, msg: pb.MapBossQuestMsg) -> None:
    s.send(S_MAP_BOSS, bosses.boss_msg(s.ctx.world, s.ctx.templates, msg.mapId, s.ctx.clock.now()))


@router.on(5004)
async def user_display(s: GameSession, msg: pb.OutercityReqMsg) -> None:
    """Pede os jogadores da tela. O cliente não lê resposta (``client_listens false``): os exércitos
    chegam no 5181 e nas atualizações ao vivo, então só registramos."""
    s.log.info("5004 tela", mapa=msg.mapId)


@router.on(5181)
async def army_grid(s: GameSession, msg: pb.OutercityReqMsg) -> None:
    """Grade de exércitos (``files`` = "x_y,..."). Sem resposta própria: nas capturas (transfer #12-15,
    cevre #11-12) o 5181 não tem S>C; a grade vem no 169 que o 8201 manda logo depois (ver 8201)."""
    s.log.info("5181 grade", mapa=msg.mapId, grades=len(msg.files.split(",")))


async def _rivals(s: GameSession, grids: set[str], map_id: int) -> list[tuple[Castle, str]]:
    """Castelos de outros jogadores nas grades pedidas de um mapa compartilhado (1 a 5). A instância
    100000xxx é do jogador: no oficial ela só tem o castelo dele e 2 robôs (replay #706, cevre #11)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    if map_id != snap.castle.map_id or oc.template_of(map_id) == oc.BASE_MAP:
        return []
    own = snap.character.id or 0
    castles = await s.ctx.characters.read(lambda uow: uow.castles.on_map(map_id))
    near = [c for c in castles if c.character_id != own and oc.grid_of(c.pos_x, c.pos_y) in grids]
    if not near:
        return []
    chars = await s.ctx.characters.read(lambda uow: uow.characters.by_ids([c.character_id for c in near]))
    names = {c.id: c.nickname or "" for c in chars}
    return [(c, names.get(c.character_id, "")) for c in near]


@router.on(8201)
async def physics_by_grid(s: GameSession, msg: pb.PhysicUpdateReqMsg) -> None:
    """4129 com as minas da grade (ciclo atual do jogador), o próprio castelo e, num mapa compartilhado, os
    castelos de outros jogadores; depois 169 com o exército próprio se cair numa grade pedida do mesmo mapa.

    ponytail: os exércitos alheios não aparecem (o 169 é só o próprio): a posição de outro jogador só existe
    na sessão dele, e não há presença entre sessões.
    """
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    await refresh(s)
    grids = {g for g in msg.reqGrid.split(",") if g}
    reply = pb.PhysicListUpdateMsg(reqGrid=msg.reqGrid)
    if oc.template_of(msg.mapId) == oc.BASE_MAP:  # replay #706: as minas vêm antes do castelo
        for mine in mines.mines_in(s.ctx.world, grids):
            land = mines.mine_msg(snap, s.ctx.world, s.ctx.templates, mine, mines.MINE_FREE, _capacity(s))
            reply.wildLand.append(land)
    reply.baseCastle.add().CopyFrom(b.complete(b.castle_msg(snap, snap.castle)))
    # (visto) cevre #11: os robôs vêm junto com o castelo
    for robot in robots.robots_in(snap, s.ctx.world, msg.mapId, grids):
        reply.baseCastle.add().CopyFrom(b.complete(robots.robot_castle_msg(snap, s.ctx.world, robot)))
    for castle, name in await _rivals(s, grids, msg.mapId):
        reply.baseCastle.add().CopyFrom(b.complete(oc.rival_castle_msg(castle, name)))
    s.send(S_PHYSICS, reply)
    s.send(S_GRID_ARMY, _grid_msg(s, grids, msg.mapId))


@router.on(8254)
async def army_move(s: GameSession, msg: pb.PosMoveMsg) -> None:
    """O exército andou: guarda o último ponto (pixels // 20). Como no replay (#761-#767): 140 ×2
    andando no ponto de saída e, na chegada, 140 ×2 parado no destino. Sem outro jogador no mapa não
    há o que avisar (4167). Outro exército, mapa diferente, rota vazia ou fora do mapa: ignorado."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    castle = snap.castle
    if msg.armyId != snap.character.id or not msg.routes or msg.mapId != castle.map_id:
        s.log.info("8254 ignorado", exercito=msg.armyId, mapa=msg.mapId)
        return
    x, y = msg.routes[-1].x // oc.TILE, msg.routes[-1].y // oc.TILE
    if not oc.inside(s.ctx.templates, castle.map_id, x, y):
        s.log.info("8254 fora do mapa", x=x, y=y)
        return
    _stop_walk(s)
    _map, x0, y0 = oc.position(castle, s.outer_army)
    _army_sync(s, ARMY_MOVING)
    s.outer_army = (castle.map_id, x, y)
    s.outer_walk = asyncio.create_task(_arrive(s, WALK_SECONDS_PER_TILE * math.dist((x0, y0), (x, y))))


async def _arrive(s: GameSession, seconds: float) -> None:
    await asyncio.sleep(seconds)
    s.outer_walk = None
    if s.battle is None and s.campaign is None:  # numa campanha o 140 é do mapa dela
        _army_sync(s, ARMY_IDLE)


def _stop_walk(s: GameSession) -> None:
    if s.outer_walk is not None:
        s.outer_walk.cancel()
        s.outer_walk = None


@router.on(5161)
async def return_home(s: GameSession, _: pb.PayTypeMsg) -> None:
    """Volta o exército para o castelo (de graça: o botão do exército não checa nada). 98 com a posição."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    _stop_walk(s)
    s.outer_army = None
    _map, x, y = oc.home(snap.castle)
    s.send(S_RETURN, pb.OutercityRspMsg(result=snap.character.id, curPosX=x, curPosY=y))


def _capacity(s: GameSession) -> int:
    assert s.snapshot is not None
    return rules.leader_stats(s.snapshot, s.ctx.templates).fighting_capacity


def _mine_sync(s: GameSession, mine: Mine, state: int) -> None:
    """140 da mina com o dono que ela tem agora (o próprio jogador, se ocupou)."""
    snap = s.snapshot
    assert snap is not None
    land = mines.mine_msg(snap, s.ctx.world, s.ctx.templates, mine, state, _capacity(s))
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_WILD, wildLand=land))


def _army_sync(s: GameSession, state: int) -> None:
    for _ in range(2):  # o oficial manda o 140 do exército sempre duas vezes
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s, state)))


@router.on(5160)
async def attack(s: GameSession, msg: pb.MapPhysicAttackMsg) -> None:
    """Atacar uma posição do mapa. Mina de ouro livre: luta com o guarda (replay #713-#795): 140 do
    exército lutando, 140 da mina em luta (state 4) e a 157. Castelo-robô: luta (ver ``_attack_robot``).
    Mina já ocupada, castelo de outro jogador, terra ou tesouro: o exército só para (140 parado)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    await refresh(s)
    _stop_walk(s)
    robot = robots.robot_at(snap, s.ctx.world, msg.mapId, msg.posX, msg.posY)
    if robot is not None:
        _attack_robot(s, robot)
        return
    mine = mines.mine_at(s.ctx.world, msg.mapId, msg.posX, msg.posY)
    if mine is None or mines.occupied(snap, mine) is not None or s.battle is not None:
        s.log.info("5160 sem alvo", mapa=msg.mapId, x=msg.posX, y=msg.posY)
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))
        return
    _, guard = mines.draw(snap, s.ctx.world, s.ctx.templates, mine)
    _army_sync(s, ARMY_FIGHTING)
    _mine_sync(s, mine, mines.MINE_FIGHTING)
    spec = oc.guard_battle(snap, s.ctx.templates, guard)

    async def finished(battle: Battle, won: bool) -> None:
        await _mine_over(s, battle, mine, won)

    s.battle = Battle(spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished)
    s.log.info("batalha da mina", mina=mine.id, battle=s.battle.id)
    s.battle.start()


async def _mine_over(s: GameSession, battle: Battle, mine: Mine, won: bool) -> None:
    """Fim da luta da mina, na ordem do replay (#734-#744): 150, 4103, 150, 100, 140 ×2; vencendo,
    a mina fica do jogador: 112 da missão 60, 4152, 109, 152 com o rendimento e 140 da mina ocupada."""
    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
    report = pb.BattleReportMsg(battleResult=1 if won else 2, strategyBonus=0, gpBonus=0, battleScene=4)
    report.failCount, report.goldBonus, report.petGpBonus = 0, 0, 0
    s.send(S_FULL_ARMY, b.complete(_army_now(s, ARMY_FIGHTING)))
    s.send(S_REPORT, report)
    s.send(S_FULL_ARMY, b.complete(_army_now(s, ARMY_FIGHTING)))
    s.send(S_ARMY_PAWN, castle_pawns(snap, templates))
    _army_sync(s, ARMY_IDLE)
    await refresh(s)  # a luta pode ter cruzado o refresh: a ocupação é do ciclo novo
    now = s.ctx.clock.now()
    if not won or mines.occupied(snap, mine) is not None:
        _mine_sync(s, mine, mines.MINE_FREE)
        return
    assert snap.castle is not None
    cs.settle(snap, templates, now)  # o ouro até agora sai na taxa antiga; a mina conta daqui em diante
    land = mines.occupy(snap, mine, mines.draw(snap, s.ctx.world, templates, mine)[0], now)
    quests = rules.quest_event(snap, templates, OCCUPY, mines.MINE_SON_TYPE, 1)
    await s.ctx.characters.save(snap.character, snap.castle, land, *quests)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    await events.leed_done(s, LEED_MINE)
    castle_yield(s)
    s.send(S_POLITICS, politics_msg(snap, templates))
    _mine_sync(s, mine, mines.MINE_FREE)
    map_id, x, y = oc.position(snap.castle, s.outer_army)
    s.send(S_GRID_ARMY, _grid_msg(s, {oc.grid_of(x, y)}, map_id))  # replay #749


def _attack_robot(s: GameSession, robot: RobotCastle) -> None:
    """Ataque a um castelo-robô (cliente: MapPhysicsCastle.attack e CityInfoFrame). Recusa com 140 parado,
    sem luta, se já há luta, se não há ataque no dia (``attackCount`` do cliente) ou se a diferença de nível
    para o castelo for 10 ou mais (MapPhysicsCastle.attack). Senão gasta um ataque e luta com o guarda de grau 8.
    (dedução) o ataque sai do contador do dia (o mesmo do 9506). A gravação vem no fim da luta."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None and snap.arena is not None
    c, arena, now = snap.character, snap.arena, s.ctx.clock.now()
    if A.roll_day(arena, now):
        s.send(S_RESET, A.data_reset(snap, now))
    if s.battle is not None or arena.attack_left <= 0 or abs(c.grades - robot.grade) >= 10:
        s.log.info("5160 castelo-robô recusado", castelo=robot.id, ataques=arena.attack_left, nivel=c.grades)
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s)))
        return
    arena.attack_left -= 1  # sem await até criar a luta: dois 5160 seguidos não gastam o mesmo ataque
    _army_sync(s, ARMY_FIGHTING)
    spec = oc.guard_battle(snap, s.ctx.templates, s.ctx.world.mine_guards.get(robot.grade, 0))

    async def finished(battle: Battle, won: bool) -> None:
        await _castle_over(s, battle, won)

    s.battle = Battle(spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished)
    s.log.info("batalha com castelo-robô", castelo=robot.id, battle=s.battle.id)
    s.battle.start()


async def _castle_over(s: GameSession, battle: Battle, won: bool) -> None:
    """Fim da luta com o castelo-robô, na ordem da luta da mina: 150, 4103, 150, 100 e 140 do exército.
    Vencendo, conta o tipo 8 (Para1 1 = vitória: 100 e 411 aceitam qualquer Para1, 765 pede a vitória) e
    manda o 112. Ouro saqueado: sem captura, sai 0 (ponytail). Grava o contador de ataques em uma save."""
    snap = s.snapshot
    assert snap is not None and snap.arena is not None
    templates = s.ctx.templates
    s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
    report = pb.BattleReportMsg(battleResult=1 if won else 2, strategyBonus=0, gpBonus=0, battleScene=4)
    report.failCount, report.goldBonus, report.petGpBonus = 0, 0, 0
    s.send(S_FULL_ARMY, b.complete(_army_now(s, ARMY_FIGHTING)))
    s.send(S_REPORT, report)
    s.send(S_FULL_ARMY, b.complete(_army_now(s, ARMY_FIGHTING)))
    s.send(S_ARMY_PAWN, castle_pawns(snap, templates))
    _army_sync(s, ARMY_IDLE)
    quests = rules.quest_event(snap, templates, ATTACK_CASTLE, 1, 1) if won else []
    await s.ctx.characters.save(snap.character, snap.arena, *quests)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    _send_player(s)  # attackLeftCount novo


@router.on(8488)
async def pvp_army(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """PvP contra o exército de outro jogador no mapa. Os exércitos alheios não aparecem na cidade externa
    (ver 8201), então não há alvo: nada muda e o cliente não espera resposta para isso (ele só espera a 157)."""
    s.log.info("8488 sem alvo no mapa", alvo=msg.tarUserId)


@router.on(8699)
async def collection_battle(s: GameSession, _: object) -> None:
    """Só o guia do tutorial manda (ação a46 do m8). Nenhuma captura tem o passo nem o nó de coleta
    que ele abre: sem o que iniciar, só registramos (docs/cidade-externa.md)."""
    s.log.info("8699 do guia do tutorial sem coleta para iniciar")


@router.on(9506)
async def add_attack(s: GameSession, msg: pb.OutercityReqMsg) -> None:
    """Ataque extra da cidade externa (AttackAlertFrame): 100 diamantes, ``type 2`` usa o vinculado
    primeiro; até 5 no dia (o cliente mostra "x/5"). Responde o PlayerMsg com o contador novo."""
    snap = s.snapshot
    assert snap is not None and snap.arena is not None
    c, arena, now = snap.character, snap.arena, s.ctx.clock.now()
    if A.roll_day(arena, now):
        s.send(S_RESET, A.data_reset(snap, now))
    if arena.attack_left >= A.ATTACK_FREE:
        s.log.info("9506 recusado", motivo="cheio")
        return
    entry = pay(c, oc.ATTACK_PRICE, bind=msg.type == 2, reason="attack_count", ref="outer_city", now=now)
    if entry is None:
        s.log.info("9506 recusado", motivo="sem diamantes")
        return
    arena.attack_left += 1
    await s.ctx.characters.save(c, arena, entry)
    _send_player(s)


@router.on(5176)
async def move_castle(s: GameSession, msg: pb.CastleReqMsg) -> None:
    """Muda o castelo de lugar.

    Outro mapa (``magId`` diferente): o servidor escolhe o ponto (centro do mapa) e gasta 200 de
    energia de teleporte; sem energia, completa até o teto com diamante (``payType 2`` = vinculado).
    Mesmo mapa com ``posX``/``posY``: 100 de energia, no ponto pedido se estiver no mapa.
    Resposta: 140 com o exército no lugar novo e 105 com o castelo (mapa, posição, energia). Recusa:
    105 com o castelo como está.
    """
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, castle, now = snap.character, snap.castle, s.ctx.clock.now()
    templates = s.ctx.templates
    if msg.magId in (0, castle.map_id):
        if not (msg.posX and msg.posY) or not oc.inside(templates, castle.map_id, msg.posX, msg.posY):
            s.log.info("5176 recusado", motivo="ponto fora do mapa")
            _castle_state(s)
            return
        target, spot, need = castle.map_id, (msg.posX, msg.posY), oc.ENERGY_SAME_MAP
    else:
        if not oc.map_allowed(msg.magId, c.grades) or oc.map_size(templates, msg.magId) is None:
            s.log.info("5176 recusado", motivo="mapa fechado", mapa=msg.magId)
            _castle_state(s)
            return
        target, spot, need = msg.magId, oc.centre(templates, msg.magId), oc.ENERGY_OTHER_MAP
    top = cs.energy_max(templates)
    diamonds = oc.energy_diamonds(castle, top, need)
    entry = None
    if diamonds:
        entry = pay(c, diamonds, bind=msg.payType == 2, reason="transfer_energy", ref="castle", now=now)
        if entry is None:
            s.log.info("5176 recusado", motivo="sem diamantes para a energia")
            _castle_state(s)
            return
        castle.energy = top
    castle.energy -= need
    castle.map_id, castle.pos_x, castle.pos_y = target, spot[0], spot[1]
    quests = rules.update_state_quests(snap, templates, snap.quests)  # 37: missões do mapa (checkMapId)
    _stop_walk(s)
    s.outer_army = None
    await s.ctx.characters.save(c, castle, *([entry] if entry else []), *quests)
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=3, army=_army_brief(s)))
    s.send(S_TRANSFER, pb.CastleReqMsg(magId=target, posX=spot[0], posY=spot[1], leftEnergy=castle.energy))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    if entry is not None:
        _send_player(s)


@router.on(8747)
async def enter_castle(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    s.send(S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=0))
    s.battle_gp, s.outer_fight_over = 0, False
