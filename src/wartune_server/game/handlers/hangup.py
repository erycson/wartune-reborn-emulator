"""Rest House / Altar of Ennoblement (gancho): sala que devolve estamina (8258 7001-7009, 5125, 5033, 8292, 8293,
8295, 5025) e o PK por convite no mapa (8525). Regras e fontes em docs/salas-campanha.md#rest-house.

(cliente) ``HookMapMediator``/``HookTimeView``/``HookAlertFrame``/``CampaignMapController``: a sala é a campanha de
``Types`` 3; chegar na estátua (nó ``types`` 111) faz o servidor mandar o 29 ``CampaignConfirmMsg`` com ``type`` fora
dos conhecidos, que abre o ``HookAlertFrame`` ("Divine Statue"); "Begin" volta como 5033 ``paraBool1``. Meditando,
cada tique (120 s: o relógio da tela é ``leftWeay * 2 * 60``) manda 4235 ``addWeay`` 1 e o cliente soma a estamina e
escreve "Restored 1 Stamina through cultivation.". 8292 cancela, 8293 acelera: ``min(leftWeay, 200 - weary)`` ×
``HangupFastPoint`` (10) Balens, grátis com o contrato do rei 4 (Lord of Time).

O que resta para hoje (``leftWeay``) é um teto diário (``DataResetMsg.leftHangupWeary`` zera por dia), sem valor no
cliente: ``game_settings.rest_house``. A meditação vive na sessão: sair da sala ou desconectar acerta e para.

O convite de PK (8525 op 1) precisa da batalha no mapa (BattleType 19), que não existe. O cliente não espera
resposta, então só registramos. Não mandamos 4421 de volta: com a recusa automática ligada
(``SharedManager.refuseInvitation``) o cliente responde 8525 op 3 a qualquer 4421, e isso viraria laço.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from ...templates.repository import GameTemplates
from .. import events as ev
from .. import rules, space
from ..builders import login as b
from ..campaign import NORMAL, CampaignMap
from ..router import router
from ..session import GameContext, GameSession
from .player import _player

S_HANGUP_LEFT, S_HANGUP_STATE, S_HANGUP_ROOM, S_HANGUP_ARMIES, S_HANGUP_TICK = 4199, 4200, 4204, 4206, 4235
S_ROOM_ENTER, S_EXIT, S_CONFIRM, S_ROOM_CREATED, S_NODES, S_FOG = 21, 22, 29, 125, 127, 130
ROOM_ENTER = 1  # RoomCreatedMsg.createdType
HOOK_TYPE = 3  # Campaigns.Types das salas do gancho (7001-7009): o HookFrame desenha uma por campanha
MIN_GRADE = 21  # OpenGradesII.HOOK
HOOK_NODE = 111  # PosType.HOOK_NODE
CONFIRM_TYPE = 7  # 29.type fora de {0,2..6,10..14,17,21,22}: o CampaignMapController abre o HookAlertFrame
TICK = 120  # s por estamina (HookTimeView.updateTime)
LORD_OF_TIME = 4  # KingContracts 4: o HookTimeView manda o 8293 sem perguntar o preço
LEED = 22  # LeedTemp 22 "Enter the Altar of Ennoblement"
KEY = "hangup"  # EventState diário: value = estamina ganha hoje
# TODO(inventado): teto diário de estamina da sala (o cliente não traz o número; DataResetMsg.leftHangupWeary existe
# mas ninguém lê)
REST_HOUSE: dict[str, Any] = {"daily": 50}
TITLE = "Divine Statue"  # HookAlertFrame.title (o quadro usa o texto do cliente; o 29 só abre)
BODY = "Welcome to the land of ancient spirits! Here you can receive bonus Stamina, would you like to get started?"
START = (36, 22)  # (dedução) o bloco de tiles valor 4 do maps/7001/7001.titles (35-38, 21-22): o ponto de entrada
# (dedução) as quatro estátuas (mapmaterial/floor/guajifang/shenxiang01-04 no 7001.maps, base em 41,18 / 57,30 /
# 10,38 / 14,18) e os tiles valor 3 do .titles ao pé de cada uma; a 5ª marca (38,35) não tem estátua. O estado do
# 4206 é o índice da estátua: a CDN só tem images/hook/1.png a 4.png. O sonType 7001 é o build/7001.swf vazio
# (a estátua já está na arte do mapa).
STATUES = ((43, 17), (58, 29), (16, 37), (20, 17))
SON_TYPE = 7001


@dataclass
class Cultivation:
    statue: int  # 1..4, o estado do 4206
    started: datetime
    credited: int = 0  # tiques já vencidos desde ``started``
    gained: int = 0  # estamina desta meditação (o 4200 do fim leva no addWeay)
    timer: asyncio.TimerHandle | None = None


def config(settings: Mapping[str, Any]) -> dict[str, Any]:
    return REST_HOUSE | dict(settings.get("rest_house") or {})


def is_room(templates: GameTemplates, campaign_id: int) -> bool:
    row = templates.get("Campaigns", campaign_id, key="CampaignId") or {}
    return int(row.get("Types") or -1) == HOOK_TYPE


def statue_nodes(map_id: int) -> dict[int, dict[str, Any]]:
    out = {}
    for i, (x, y) in enumerate(STATUES, 1):
        camp = map_id * 100 + i
        out[camp] = {
            "nodeId": i, "campDataId": camp, "nodeName": TITLE, "masterType": HOOK_NODE, "sonType": SON_TYPE,
            "preNodeIds": "0", "nextNodeIds": "", "state": NORMAL, "refreshSpeed": 1, "posX": x, "posY": y,
            "curX": x, "curY": y, "level": 0, "styleType": 1, "attackTypes": 0, "nameColor": 5, "sizeType": 1,
            "toward": 0, "resource": 2, "resetX": 0, "resetY": 0, "fixX": 0, "fixY": 0, "heroTempId": 0,
            "handlerRange": 2, "fightCapaity": 0, "param1": i, "param2": 0, "param3": "", "param4": "", "param5": "",
        }  # fmt: skip
    return out


def left(s: GameSession, now: datetime) -> int:
    """Estamina que a sala ainda dá hoje."""
    assert s.snapshot is not None
    daily = int(config(s.ctx.world.settings)["daily"])
    return max(0, daily - ev.daily(s.snapshot, KEY, now).value)


def room_players(ctx: GameContext, map_id: int) -> list[GameSession]:
    return [o for o in ctx.online.sessions()
            if o.campaign is not None and o.campaign.hook and o.campaign.map_id == map_id
            and o.snapshot is not None]  # fmt: skip


def _state(s: GameSession) -> int:
    return s.hangup.statue if s.hangup is not None else 0


def _broadcast_state(s: GameSession) -> None:
    assert s.campaign is not None
    msg = pb.PlayerHangupStateListMsg()
    msg.hanupState.add(armyId=s.player_id, state=_state(s))
    for o in room_players(s.ctx, s.campaign.map_id):
        o.send(S_HANGUP_ARMIES, msg)


async def enter_room(s: GameSession, campaign_id: int) -> bool:
    """8258 ``param1`` 7001-7009. Falso se não for sala do gancho. Ordem: 4199 antes da view (o ``HookTimeView``
    lê ``hookleftWeay`` ao nascer), 125, 21 (todos da sala; os outros recebem o meu), 127, 130, 4206 e o leed 22."""
    ctx = s.ctx
    if not is_room(ctx.templates, campaign_id):
        return False
    snap = s.snapshot
    assert snap is not None
    if s.battle is not None or s.campaign is not None:
        return True
    if snap.character.grades < MIN_GRADE:
        s.log.info("8258 sala do gancho abaixo do nível", nivel=snap.character.grades)
        return True
    now = ctx.clock.now()
    space.leave(s)
    others = room_players(ctx, campaign_id)
    s.campaign = CampaignMap(campaign_id, statue_nodes(campaign_id), START, hook=True)
    s.send(S_HANGUP_LEFT, pb.HangupInfoMsg(leftWeay=left(s, now), isStartHangup=False, addWeay=0))
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER)
    room.room.campaignId = campaign_id
    s.send(S_ROOM_CREATED, room)
    me = space.room_player(snap, ctx.templates, s.campaign.pos, campaign_id, now)
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, campaign_id, now)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    for o in others:
        o.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    s.send(S_NODES, s.campaign.node_list())
    s.send(S_FOG, s.campaign.fog())
    states = pb.PlayerHangupStateListMsg()
    for o in (s, *others):
        states.hanupState.add(armyId=o.player_id, state=_state(o))
    s.send(S_HANGUP_ARMIES, states)
    s.log.info("entrou na sala do gancho", sala=campaign_id, resta=left(s, now))
    from . import events as hev  # handlers.events importa login, que importa a campanha

    await hev.leed_done(s, LEED)
    return True


def arrive(s: GameSession, node: Mapping[str, Any]) -> None:
    """5125 na estátua: o 29 que abre o HookAlertFrame (nada se já medita)."""
    c = s.campaign
    assert c is not None
    if node["masterType"] != HOOK_NODE or s.hangup is not None:
        return
    s.send(S_CONFIRM, pb.CampaignConfirmMsg(title=TITLE, body=BODY, mapId=c.map_id, nodeId=node["campDataId"],
                                            type=CONFIRM_TYPE))  # fmt: skip


async def confirm(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """5033 "Begin" (``paraInt2`` = nó, ``paraBool1``): começa a meditar. Sem estamina a ganhar hoje ou com a
    estamina cheia, o 4200 sem ``isStartHangup`` responde."""
    c, snap = s.campaign, s.snapshot
    assert c is not None and snap is not None
    node = c.node(msg.paraInt2)
    if not msg.paraBool1 or node is None or node["masterType"] != HOOK_NODE or s.hangup is not None:
        return
    now = s.ctx.clock.now()
    rest = left(s, now)
    if rest == 0 or snap.character.weary >= snap.character.weary_limit:
        s.log.info("meditação recusada", resta=rest, estamina=snap.character.weary)
        s.send(S_HANGUP_STATE, pb.HangupInfoMsg(leftWeay=rest, isStartHangup=False, addWeay=0))
        return
    s.hangup = Cultivation(int(node["param1"]), now)
    s.send(S_HANGUP_STATE, pb.HangupInfoMsg(leftWeay=rest, isStartHangup=True, addWeay=0))
    _broadcast_state(s)
    _schedule(s)
    s.log.info("meditação começou", estatua=s.hangup.statue, resta=rest)


def _schedule(s: GameSession) -> None:
    h = s.hangup
    assert h is not None
    elapsed = (s.ctx.clock.now() - h.started).total_seconds()
    wait = max(1.0, (h.credited + 1) * TICK - elapsed)
    h.timer = asyncio.get_running_loop().call_later(wait, lambda: asyncio.ensure_future(tick(s)))


def _full(s: GameSession, now: datetime) -> bool:
    c = s.snapshot.character  # type: ignore[union-attr]
    return left(s, now) == 0 or c.weary >= c.weary_limit


async def tick(s: GameSession) -> None:
    """Paga os tiques vencidos (um 4235 por estamina) e para quando acaba o de hoje ou a estamina enche."""
    h, snap = s.hangup, s.snapshot
    if h is None or snap is None:
        return
    now = s.ctx.clock.now()
    c = snap.character
    st = ev.daily(snap, KEY, now)
    due = int((now - h.started).total_seconds()) // TICK
    while h.credited < due and not _full(s, now):
        h.credited += 1
        h.gained += 1
        c.weary += 1
        st.value, st.updated_at = st.value + 1, now
        s.send(S_HANGUP_TICK, pb.HangupInfoMsg(leftWeay=left(s, now), isStartHangup=True, addWeay=1))
    await s.ctx.characters.save(c, st)
    if _full(s, now):
        await stop(s, "acabou")
    elif s.hangup is h:
        if h.timer is not None:
            h.timer.cancel()
        _schedule(s)


async def stop(s: GameSession, why: str) -> None:
    """Fim da meditação: 4200 sem ``isStartHangup`` com o total ganho e o 4206 estado 0 para a sala."""
    h = s.hangup
    if h is None:
        return
    if h.timer is not None:
        h.timer.cancel()
    s.hangup = None
    s.send(S_HANGUP_STATE, pb.HangupInfoMsg(leftWeay=left(s, s.ctx.clock.now()), isStartHangup=False,
                                            addWeay=h.gained))  # fmt: skip
    if s.campaign is not None and s.campaign.hook:
        _broadcast_state(s)
    s.log.info("meditação parou", motivo=why, ganhou=h.gained)


def _resync(s: GameSession) -> None:
    """8292/8293 sem meditação (o quadro do cliente ficou para trás): 4200 parado com o que resta hoje."""
    s.send(S_HANGUP_STATE, pb.HangupInfoMsg(leftWeay=left(s, s.ctx.clock.now()), isStartHangup=False, addWeay=0))


@router.on(8293)
async def quick_hangup(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Acelera: o que falta (até a estamina encher) de uma vez, ``HangupFastPoint`` Balens por estamina; grátis com
    o Lord of Time. Sem Balens nada muda (o cliente já mostrou o preço)."""
    snap = s.snapshot
    assert snap is not None
    if s.hangup is None:
        s.log.info("8293 sem meditação")
        _resync(s)
        return
    await tick(s)
    if s.hangup is None:
        return
    now = s.ctx.clock.now()
    c = snap.character
    n = min(left(s, now), c.weary_limit - c.weary)
    free = ev.has_contract(snap, LORD_OF_TIME, now)
    cost = 0 if free else n * int(rules.config(s.ctx.templates, "HangupFastPoint", "10"))
    paid = cash.pay(c, cost, msg.payType, "hangup", str(n), now) if cost else None
    if cost and paid is None:
        s.log.info("8293 sem Balens", custo=cost)
        return
    st = ev.daily(snap, KEY, now)
    c.weary += n
    st.value, st.updated_at = st.value + n, now
    s.hangup.gained += n
    await s.ctx.characters.save(c, st, *([paid] if paid is not None else []))
    _player(s)
    s.log.info("meditação acelerada", estamina=n, custo=cost)
    await stop(s, "acelerou")


@router.on(8292)
async def cancel_hangup(s: GameSession, _: object) -> None:
    """Cancela (``HookTimeView``, depois da confirmação): paga o que venceu e guarda o resto do dia."""
    if s.hangup is None:
        _resync(s)
        return
    await tick(s)
    await stop(s, "cancelou")


async def leave_room(s: GameSession, *, back: bool = True) -> bool:
    """5025 (ou desconexão, ``back`` falso) na sala do gancho: paga os tiques vencidos, para a meditação e sai como
    na pedreira (22 e a cidade do céu); os outros da sala recebem o 22 para tirar o exército."""
    c, snap = s.campaign, s.snapshot
    if c is None or not c.hook or snap is None:
        return False
    await tick(s)
    if s.hangup is not None:
        if s.hangup.timer is not None:
            s.hangup.timer.cancel()
        s.hangup = None
        _broadcast_state(s)
    s.campaign = None
    msg = pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id, serverName=snap.server.name)
    for o in room_players(s.ctx, c.map_id):
        o.send(S_EXIT, msg)
    if back:
        s.send(S_EXIT, msg)
        space.enter(s)
    s.log.info("saiu da sala do gancho", sala=c.map_id)
    return True


@router.on(8295)
async def hangup_room_state(s: GameSession, _: object) -> None:
    """Estado das salas do gancho: uma entrada por campanha, senão o ``HookItem`` lê ``roomState[id]`` indefinido e
    a janela quebra. ``curCount`` = quem está na sala agora; ``maxCount`` = ``Capacity`` da campanha (*dedução*): o
    ``HookContorler.getStateByCount`` mostra "cheia" com ``curCount >= maxCount / 2``."""
    rows = sorted(s.ctx.templates.find("Campaigns", Types=HOOK_TYPE), key=lambda r: int(r["CampaignId"]))
    out = pb.HangupStateListMsg(maxCount=max((int(r["Capacity"]) for r in rows), default=0))
    for r in rows:
        cid = int(r["CampaignId"])
        out.hangupState.add(campaignId=cid, curCount=len(room_players(s.ctx, cid)))
    s.send(S_HANGUP_ROOM, b.complete(out))


@router.on(8525)
async def map_pk(s: GameSession, msg: pb.HangupAttackMsg) -> None:
    """op 1 convite, 2 aceita, 3 recusa; sem op é o ataque no campo de animais (sem batalha aqui)."""
    s.log.info("8525 sem batalha de PK no mapa da campanha", op=msg.op, alvo=msg.defenceId)
