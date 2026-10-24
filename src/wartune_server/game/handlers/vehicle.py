"""Veículos (Tank Trials): garagem, janela (4512), fila (8608/8609 e a sala de veículo no 5039) e a batalha da
campanha 3001 (cena VEHICLE do m17: 8610 e 8615 a 8617).

Regras da partida em ``game/vehicles.py``; fontes e o que é dedução em ``docs/diversos.md``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog
from google.protobuf.message import Message

from ...domain.models import Character, Mail, MailType
from ...domain.repositories import UnitOfWork
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import mail as mailbox
from .. import space
from .. import vehicles as vh
from ..builders import login as b
from ..router import router
from ..session import GameContext, GameSession

S_PLAYER, S_STATE, S_PROFILE, S_LIST, S_TECH = 3, 4512, 4515, 4516, 4501
S_DIE_STATE, S_ATTACK = 4175, 4520
S_ROOM_CREATED, S_SEARCHING, S_ROOM_STATE = 125, 4525, 25
ROOM_ENTER = 1  # RoomCreatedMsg.createdType: com a tela de carregamento (3 = sem)
SEARCHING = 1  # SimplePropertyMsg.param1 do 4525: o DaimonTrialBottomView liga o relógio "procurando"
ROOM_MATCHING, ROOM_PLAYING = 2, 3  # RoomStateRspMsg.roomState (VehicleRoomFrame: 2 conta o tempo, 3 jogando)
GARAGE = "1"  # VehicleObjectTempInfo.Type dos veículos da garagem (DaimonModel)
EXIT_NODE = 0  # WorldBossPlayerStateMsg.state fora de 6/7/8 = desceu do veículo/torre (CampaignArmy.exitNode)
# 4501 param1 = PlayerModel.vehicleTech, comparado com NeedGrades (DaimonRightView inglês, "Requires {0} Tank Tech
# Level."). A tecnologia de tanque não tem tela nem regra de evolução no cliente; (visto) 218 no inglês fora do login
# (oficial_encantar #2605, 171155 #6386) e (só turco: login.json #112) 18218 no login, sem relação com força ou
# perfil. ``game_settings.vehicle_tech``; sem ele, o 218 do inglês (abaixo dos 365 do Nightwolf e dos 915 do 4)
TECH_SETTING = "vehicle_tech"
NOT_OPEN = "Tanks are not open yet!"  # language EN vehicle.noOpen
LOW_LEVEL = f"Requires level {vh.MIN_LEVEL}."
BUSY = "Finish your current battle or map first."
MAIL_TITLE = "Tank Trials"
MAIL_TEXT = "Tank Trials rewards."  # (dedução) o cliente não tem o texto do correio
TICK = 1.0  # segundos entre os tiques das partidas

log = structlog.get_logger(__name__)


def _alert(s: GameSession, text: str) -> None:
    from .player import alert  # player importa login, que importa este módulo

    alert(s, text)


def tech(s: GameSession) -> int:
    return int(s.ctx.world.settings.get(TECH_SETTING) or 218)


def owned(c: Character) -> list[int]:
    return [int(v) for v in c.vehicles.split(",") if v]


def _rewarded(s: GameSession) -> bool:
    """Já recebeu o prêmio da janela aberta."""
    win = vh.window(s.ctx.templates, s.ctx.clock.now())
    return win is not None and s.player_id in s.ctx.vehicles.rewarded.get(win[0], set())


def _profile(s: GameSession, c: Character) -> pb.PlayerVehicleProfileMsg:
    # isFirst = ainda tem o prêmio desta janela: false faz o DaimonTrialBottomView avisar "Tank Trails attempts have
    # run out. You will gain no rewards if you enter." (room.view.pve.RoomRightView.tip) antes de entrar
    return pb.PlayerVehicleProfileMsg(
        exp=c.vehicle_exp, score=c.vehicle_score, defaultVehicle=c.vehicle_default, isFirst=not _rewarded(s)
    )


def _garage(c: Character) -> pb.PlayerVehicleListMsg:
    # ponytail: id = templateId (o oficial manda um id de banco; o cliente só usa templateId)
    return pb.PlayerVehicleListMsg(vehicles=[pb.PlayerVehicleMsg(id=t, templateId=t) for t in owned(c)])


def _open(s: GameSession) -> bool:
    return vh.window(s.ctx.templates, s.ctx.clock.now()) is not None


def login(s: GameSession) -> None:
    """Estado de veículos no login (só turco: login.json #83, #110-#112; o tutorial_en, nível 1-15, não manda
    nenhum dos quatro). O 4512 diz se a janela está aberta (``BaseManager.__vehicleStartHandler``)."""
    assert s.snapshot is not None
    c = s.snapshot.character
    s.vehicle_open = _open(s)
    s.send(S_STATE, pb.MatchStateMsg(matchState=s.vehicle_open))
    s.send(S_PROFILE, _profile(s, c))
    s.send(S_LIST, _garage(c))
    s.send(S_TECH, pb.SimplePropertyMsg(param1=tech(s)))


def push_state(s: GameSession) -> None:
    """No relógio (20008): 4512 de novo quando a janela abre ou fecha (o botão e a fila dependem dele)."""
    if s.vehicle_open is None or s.snapshot is None:
        return
    if (now_open := _open(s)) != s.vehicle_open:
        s.vehicle_open = now_open
        s.send(S_STATE, pb.MatchStateMsg(matchState=now_open))
        if not now_open:
            _drop_queue(s.ctx)


def _drop_queue(ctx: GameContext) -> None:
    """Janela fechada com gente esperando: a fila acaba; a sala de veículo volta a esperar (25 ``roomState`` 1)."""
    from ..rooms import IN_USE

    for group in ctx.vehicles.queue:
        room = ctx.rooms.of(group[0])
        if room is not None:
            room.state = IN_USE
            _room_state(ctx, room.members, IN_USE)
    ctx.vehicles.queue.clear()


def _deliver(ctx: GameContext) -> vh.Deliver:
    def send(player_id: int, code: int, msg: Message) -> None:
        if (o := ctx.online.get(player_id)) is not None:
            o.send(code, msg)

    return send


def _refusal(s: GameSession) -> str | None:
    """Travas da entrada: janela aberta e com 5 min ou mais pela frente (``VehicleRoomFrame.checkCanEnter``),
    nível 35 (``CampaignInfo`` 3001), fora de outra luta, mapa, fila ou partida."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    win = vh.window(s.ctx.templates, now)
    if win is None:
        return NOT_OPEN
    if (win[1] - now).total_seconds() < vh.LAST_ENTRY:
        return vh.CLOSING
    if snap.character.grades < vh.MIN_LEVEL:
        return LOW_LEVEL
    arena = s.ctx.vehicles
    if _busy(s) or arena.queued(s.player_id) or arena.match_of(s.player_id):
        return BUSY
    return None


def _busy(s: GameSession) -> bool:
    """Numa luta ou num mapa não terminado (a mesma regra da entrada das masmorras, 5039)."""
    return s.battle is not None or (s.campaign is not None and not s.campaign.finished)


@router.on(8608)
async def quick_play(s: GameSession, _: object) -> None:
    """Entrada solo (``RoomListSocketOutManager.quickStart``): 4525 ``param1`` 1 (relógio "procurando") e a fila."""
    why = _refusal(s) or (BUSY if s.ctx.rooms.of(s.player_id) is not None else None)
    if why is not None:
        _alert(s, why)
        return
    s.ctx.vehicles.enqueue([s.player_id])
    s.send(S_SEARCHING, pb.SimplePropertyMsg(param1=SEARCHING))
    await match_up(s.ctx)


@router.on(8609)
async def quick_play_cancel(s: GameSession, _: object) -> None:
    """Cancelar a fila solo: o cliente arruma a tela sozinho e não espera resposta."""
    if s.ctx.vehicles.queued(s.player_id) == [s.player_id]:
        s.ctx.vehicles.dequeue(s.player_id)


async def room_start(s: GameSession) -> bool:
    """5039 do dono de uma sala de veículo (``VehicleRoomFrame.__startClickHandler``, todos prontos): a sala vai para
    a fila junta, no mesmo time, e todos recebem o 25 com ``roomState`` 2 (o relógio da sala). ``False`` = não é
    sala de veículo (o 5039 segue para as masmorras)."""
    from ..rooms import VEHICLE

    room = s.ctx.rooms.of(s.player_id)
    if room is None or room.type != VEHICLE:
        return False
    if room.master != s.player_id or any(p not in room.ready for p in room.members if p != room.master):
        s.log.info("5039 de veículo recusado: só o dono, com todos prontos")
        return True
    for pid in room.members:
        other = s.ctx.online.get(pid)
        why = _refusal(other) if other is not None and other.snapshot is not None else NOT_OPEN
        if why is not None:
            _alert(s, why)
            return True
    s.ctx.vehicles.enqueue(list(room.members))
    room.state = ROOM_MATCHING
    _room_state(s.ctx, room.members, ROOM_MATCHING)
    await match_up(s.ctx)
    return True


def room_cancel(s: GameSession) -> None:
    """O dono cancela a procura (5037 ``state`` 1) ou alguém sai da sala: a sala sai da fila."""
    s.ctx.vehicles.dequeue(s.player_id)


def _room_state(ctx: GameContext, members: list[int], state: int) -> None:
    for pid in members:
        if (o := ctx.online.get(pid)) is not None:
            o.send(S_ROOM_STATE, pb.RoomStateRspMsg(roomState=state))


async def match_up(ctx: GameContext) -> None:
    """Põe a fila nas partidas e cada tanque na cena. Sala: 25 ``roomState`` 3 e a sala fecha (o cliente descarta o
    ``RoomManager`` no 125). Depois o 125 com a campanha 3001 e a entrada da partida (``Match.join``)."""
    now = ctx.clock.now()
    win = vh.window(ctx.templates, now)
    arena = ctx.vehicles
    if win is None:
        _drop_queue(ctx)
        return
    for match, group, team in arena.place(ctx.templates, win, now, _deliver(ctx), tiles=vh.tank_map()):
        room = ctx.rooms.of(group[0])
        if room is not None:  # a fila só tem grupo de sala vindo da sala de veículo (5039)
            _room_state(ctx, group, ROOM_PLAYING)
            ctx.rooms.close(room)
        for pid in group:
            o = ctx.online.get(pid)
            tank = _tank(o, team) if o is not None and not _busy(o) else None
            if o is None or tank is None:
                match.seats.pop(pid, None)
                continue
            space.leave(o)
            created = pb.RoomCreatedMsg(createdType=ROOM_ENTER)
            created.room.campaignId = vh.CAMPAIGN
            o.send(S_ROOM_CREATED, created)
            match.join(tank, now)
            o.log.info("entrou na batalha de veículos", time=team, tanque=tank.template)
    if arena.matches and arena.task is None:
        arena.task = asyncio.create_task(_run(ctx), name="vehicles")


def _tank(s: GameSession, team: int) -> vh.Tank | None:
    from .vip import is_vip  # vip importa player, que importa este pacote

    snap = s.snapshot
    if snap is None:
        return None
    c = snap.character
    mine = owned(c)
    template = c.vehicle_default if c.vehicle_default in mine else (mine[0] if mine else 1)
    guild = s.ctx.guilds.of(s.player_id)
    return vh.new_tank(s.ctx.templates, s.player_id, c.nickname or "", template, c.vehicle_exp, team,
                       guild=guild[0].name if guild else "", vip=int(is_vip(snap, s.ctx.clock.now())))  # fmt: skip


async def _run(ctx: GameContext) -> None:
    """Relógio das partidas: um tique por segundo enquanto houver partida."""
    try:
        while ctx.vehicles.matches:
            await asyncio.sleep(TICK)
            await tick_all(ctx)
    finally:
        ctx.vehicles.task = None


async def tick_all(ctx: GameContext) -> None:
    now = ctx.clock.now()
    for match in list(ctx.vehicles.matches):
        try:
            if match.tick(now):
                await settle(ctx, match, now)
        except Exception:  # sem isto o relógio de todas morre e os tanques ficam presos (BUSY)
            log.exception("erro na partida de veículos; encerrada")
            if match in ctx.vehicles.matches:
                ctx.vehicles.matches.remove(match)
    if ctx.vehicles.queue:
        await match_up(ctx)


async def settle(ctx: GameContext, match: vh.Match, now: datetime) -> None:
    """Fim da partida: 4514 (``Match.finish``), a EXP e os pontos do tanque no personagem, os baús pelo correio e o
    4515 novo (``isFirst`` false). Uma vez por janela por jogador."""
    arena = ctx.vehicles
    if match in arena.matches:
        arena.matches.remove(match)
    win = vh.window(ctx.templates, match.start)
    rewards = match.finish(arena.rewarded.setdefault(win[0] if win is not None else match.start, set()))
    for reward in rewards:
        o = ctx.online.get(reward.player_id)
        if o is None or o.snapshot is None:
            continue
        c = o.snapshot.character
        c.vehicle_exp += reward.exp
        c.vehicle_score += reward.score
        mail = Mail(c.id or 0, now, MAIL_TITLE, MAIL_TEXT, mail_type=MailType.SYSTEM, send_type=mailbox.SYSTEM_SENDER)
        goods = list(reward.items)

        async def change(
            uow: UnitOfWork, c: Character = c, mail: Mail = mail, goods: list[tuple[int, int]] = goods
        ) -> None:
            await uow.save(c)
            await mailbox.stage(uow, mail, goods)

        await ctx.characters.write(change)
        mailbox.notify(ctx.online, mail)
        o.send(S_PROFILE, _profile(o, c))
        o.log.info("fim da batalha de veículos", pontos=reward.score, exp=reward.exp, premios=goods)


async def leave_vehicle(s: GameSession) -> None:
    """8610 ou desconexão: sai da fila e da partida (4523); se um lado esvaziou, a partida acaba."""
    arena = s.ctx.vehicles
    arena.dequeue(s.player_id)
    match = arena.match_of(s.player_id)
    if match is not None:
        now = s.ctx.clock.now()
        match.leave(s.player_id, now)
        if not match.over and match.ended(now):
            await settle(s.ctx, match, now)


def _match(s: GameSession) -> vh.Match | None:
    m = s.ctx.vehicles.match_of(s.player_id) if s.snapshot is not None else None
    return m if m is not None and s.player_id in m.tanks else None


@router.on(8610)
async def vehicle_exit(s: GameSession, _: object) -> None:
    """Voltar (``VehicleSocketOutManager.sendReturnCampaignRoom``): o cliente sai sozinho em 0,5 s."""
    if _match(s) is None:
        s.log.info("8610 fora da batalha de veículos")
        return
    await leave_vehicle(s)
    await match_up(s.ctx)  # o lugar que abriu


@router.on(8615)
async def vehicle_move(s: GameSession, msg: pb.VehicleMoveMsg) -> None:
    m = _match(s)
    if m is None or not m.move(s.player_id, [(p.x, p.y) for p in msg.path], s.ctx.clock.now()):
        s.log.info("8615 recusado", caminho=[(p.x, p.y) for p in msg.path][:3])


@router.on(8616)
async def vehicle_cast(s: GameSession, msg: pb.VehicleAttackReqMsg) -> None:
    m = _match(s)
    now = s.ctx.clock.now()
    if m is None or not m.cast(s.player_id, msg, now):
        s.log.info("8616 recusado", skill=msg.skillId, alvos=list(msg.suffererId))
        return
    if m.ended(now):
        await settle(s.ctx, m, now)


@router.on(8617)
async def vehicle_pickup(s: GameSession, msg: pb.VehiclePickPropMsg) -> None:
    m = _match(s)
    if m is None or not m.pickup(s.player_id, msg.propNodeId, s.ctx.clock.now()):
        s.log.info("8617 recusado", no=msg.propNodeId)


@router.on(8611)
async def choose_vehicle(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    c = s.snapshot.character if s.snapshot else None
    if c is None or msg.paraInt1 not in owned(c):
        s.log.info("8611 recusado", veiculo=msg.paraInt1)
        return
    c.vehicle_default = msg.paraInt1
    await s.ctx.characters.save(c)
    s.send(S_PROFILE, _profile(s, c))


@router.on(8619)
async def activate_vehicle(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Compra/ativa um veículo da garagem com ``NeedDiamond`` Balens (DaimonRightView inglês, alerta USEBINDPOINT).

    ``NeedGrades`` é a tecnologia de tanque (4501); ``param2`` 0 = pode usar vinculados
    (VehicleDaimonController.sendOpenVehicle).
    """
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    row = s.ctx.templates.get("VehicleObjectTempInfos", msg.param1)
    price, need = (int(row.get("NeedDiamond", 0)), int(row.get("NeedGrades", 0))) if row else (0, 0)
    bad = row is None or row.get("Type") != GARAGE or msg.param1 in owned(c) or need > tech(s)
    entry = None
    if not bad and price:
        now = s.ctx.clock.now()
        entry = ledger.pay(c, price, bind=msg.param2 == 0, reason="vehicle", ref=str(msg.param1), now=now)
    if bad or (price and entry is None):
        s.log.info("8619 recusado", veiculo=msg.param1, diamante=c.point)
        return
    c.vehicles = ",".join(str(t) for t in [*owned(c), msg.param1])
    await s.ctx.characters.save(c, *([entry] if entry else []))
    s.send(S_LIST, _garage(c))
    s.send(S_PROFILE, _profile(s, c))
    if price:
        from .login import player_info  # login importa este módulo

        s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(25111)
async def exit_vehicle_node(s: GameSession, msg: pb.WarFieldAttackMsg) -> None:
    """Sair do veículo/torre num mapa de guerra: 4175 com estado fora de 6/7/8 solta o jogador do nó."""
    state = pb.WorldBossPlayerStateMsg(armyId=s.player_id, state=EXIT_NODE, serverName=msg.defenceServerName)
    s.send(S_DIE_STATE, b.complete(pb.PlayerStateListMsg(playerState=[state])))


@router.on(25112)
async def vehicle_attack(s: GameSession, msg: pb.VehicleAttackReqMsg) -> None:
    """Skill de veículo em mapa de guerra (GvG): devolve a animação sem dano.

    ponytail: os mapas de guerra com veículos (CampaignInfo Types 9 / GvG) não existem; dano e alvos
    quando existirem (``VehicleSkillTempInfos``).
    """
    reply = pb.VehicleAttackRspMsg(
        skillId=msg.skillId,
        effectX=msg.effectX,
        effectY=msg.effectY,
        attackerId=s.player_id,
        serverName=msg.attackServerName,
        attackTyep=1,  # 1 = useSkill (CampaignSocketManger.__playerAttackHandler)
    )
    s.send(S_ATTACK, reply)
