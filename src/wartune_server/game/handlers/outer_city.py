"""Cidade externa (mapa do castelo): grade de exércitos, andar, voltar ao castelo, ataques extras,
mudar o castelo de lugar e a volta para a cidade no fim do tutorial.

Regras e fontes em ``game/outer_city.py`` e ``docs/cidade-externa.md``. O mundo do servidor tem só o
castelo do próprio jogador: quando o cliente pede algo que depende de outro jogador, terra selvagem
ou castelo alheio, o pedido é recusado com log e o que o cliente precisa para não travar é mandado.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import pay
from .. import arena as A
from .. import castle as cs
from .. import outer_city as oc
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .login import army, player_info

S_PLAYER, S_RESET, S_MAP_SYNC, S_TRANSFER, S_RETURN = 3, 4202, 140, 105, 98
S_MAP_BOSS, S_PHYSICS, S_GRID_ARMY, S_FIGHT_MOVIE = 4938, 4129, 169, 4382
ARMY_IDLE = 0  # MapUpdatedMsg/ArmyArmyMsg.state: parado


def _army_now(s: GameSession, state: int = ARMY_IDLE) -> pb.ArmyArmyMsg:
    """O próprio exército onde ele está agora (no castelo ou no último ponto andado)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    msg = army(s, snap)[0]
    msg.mapId, msg.curPosX, msg.curPosY = oc.position(snap.castle, s.outer_army)
    msg.state = state
    return msg


def _grid_msg(s: GameSession, grids: set[str], map_id: int) -> pb.OutercityArmyUpdatedGridMsg:
    """169: o exército próprio se cair numa das grades pedidas no mesmo mapa; senão lista vazia."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    msg = pb.OutercityArmyUpdatedGridMsg()
    map_now, x, y = oc.position(snap.castle, s.outer_army)
    if map_id == map_now and oc.grid_of(x, y) in grids:
        msg.updatedArmy.add().CopyFrom(_army_now(s))
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


@router.on(9525)
async def map_boss(s: GameSession, _: pb.MapBossQuestMsg) -> None:
    s.send(S_MAP_BOSS, pb.MapBossMsg(count1=0, count2=0, count3=0, leftBossTime=0, leftFogTime=0))


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


@router.on(8201)
async def physics_by_grid(s: GameSession, msg: pb.PhysicUpdateReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    # ponytail: só o próprio castelo; terras selvagens e castelos vizinhos quando houver mapa compartilhado
    reply = pb.PhysicListUpdateMsg(reqGrid=msg.reqGrid)
    reply.baseCastle.add().CopyFrom(b.complete(b.castle_msg(snap, snap.castle)))
    s.send(S_PHYSICS, reply)
    grids = {g for g in msg.reqGrid.split(",") if g}
    s.send(S_GRID_ARMY, _grid_msg(s, grids, msg.mapId))


@router.on(8254)
async def army_move(s: GameSession, msg: pb.PosMoveMsg) -> None:
    """O exército andou: guarda o último ponto (pixels // 20). Sem outro jogador no mapa não há o que
    avisar (4167). Outro exército, mapa diferente, rota vazia ou fora do mapa: ignorado."""
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
    s.outer_army = (castle.map_id, x, y)


@router.on(5161)
async def return_home(s: GameSession, _: pb.PayTypeMsg) -> None:
    """Volta o exército para o castelo (de graça: o botão do exército não checa nada). 98 com a posição."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    s.outer_army = None
    _map, x, y = oc.home(snap.castle)
    s.send(S_RETURN, pb.OutercityRspMsg(result=snap.character.id, curPosX=x, curPosY=y))


@router.on(5160)
async def attack(s: GameSession, msg: pb.MapPhysicAttackMsg) -> None:
    """Atacar uma posição do mapa (castelo, terra, mina ou tesouro). O servidor não tem nenhum desses
    alvos fora do castelo do próprio jogador, então não há batalha: o exército só para (140 parado)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    s.log.info("5160 sem alvo", mapa=msg.mapId, x=msg.posX, y=msg.posY)
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=3, army=_army_now(s)))


@router.on(8488)
async def pvp_army(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """PvP contra o exército de outro jogador no mapa. Não há outros exércitos no mapa do servidor:
    sem alvo, nada muda e o cliente não espera resposta para isso (ele só espera a 157)."""
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
    s.outer_army = None
    await s.ctx.characters.save(c, castle, *([entry] if entry else []))
    s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=3, army=_army_now(s)))
    s.send(S_TRANSFER, pb.CastleReqMsg(magId=target, posX=spot[0], posY=spot[1], leftEnergy=castle.energy))
    if entry is not None:
        _send_player(s)


@router.on(8747)
async def enter_castle(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    s.send(S_FIGHT_MOVIE, pb.FightOverMoiveMsg(gp=s.battle_gp, gold=0, strategy=0))
    s.battle_gp = 0
