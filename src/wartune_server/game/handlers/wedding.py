"""Sala do casamento (salões 4301-4303): criar (8759 op 6), lista (op 10, 4662), entrar (op 13), o passeio de carro
(op 7, 4672), o padre e o criado (8760) e o fim pelo tempo (``mar_time``).

Fluxo do cliente: a cerimônia escolhida (15049 -> op 5) fica reservada (``speTemplateId``, ``marriage.reserve``); o
casal cria a sala, entra (como na sala do RoomManager: 125, 140, 21 com os jogadores, 127, 150) e o padre (nó de
``param1`` 3, MarryWeddingDialogFrame) faz o voto (101) só para o casal com ``speTemplateId != 0`` e o cônjuge na sala:
aí casa, os presentes da cerimônia vão pelo correio e a festa começa (``property2`` 3 no 4674, MarryModel ``can*``).
O criado (``param1`` 8) tem bolo 102, champanhe 108, flores 103 e doces 107 (do casal, uma vez cada), presentes de ouro
104 (``marriage_gift`` pela cerimônia, convidado) e pontos 112 (convidado, 3/2/1 vezes pela cerimônia,
``isCandandPoint``) e fogos 109 (``marriage_fireworks``). O carro (op 7) passa na cidade pelo ``Path`` da cerimônia
(``MarryCarAi`` anda pelo ``property4``). Convites: 110/111 mandam o 16 ``RoomInviteMsg`` (``roomType`` 4,
``userKey`` "a_b", InviteFrame -> op 13) e o 8353 tipo 1 o link ``<a t="6" roomType="4">`` (ChatFormat).

TODO(inventado) (``wedding_room``, 0112): as falas do voto (4660), pontos do casal por ação do criado, o preço dos
fogos sem o ConfigInfo e a moeda (ouro); (dedução) ``property2`` 1 antes do voto, quem recebe os presentes e os pontos
(metade a cada um) e o link do chat entrar sem senha (o cliente manda ``property5`` sem a senha).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ...protocol.messages import wartune_pb2 as pb
from .. import social, space
from ..builders import login as b
from ..campaign import CampaignMap
from ..mail import send_system_mail
from ..router import router
from ..session import GameContext, GameSession
from . import marriage as mr
from . import worldboss as wb
from .campaign import ARMY_IDLE, map_sync
from .login import army, player_info
from .player import alert

S_ROOMS, S_GUESTS, S_INFO, S_CAR, S_OATH, S_INVITE, S_CONFIRM, S_MOVE = 4662, 4673, 4674, 4672, 4660, 16, 29, 4185
OATH, CAKE, FLOWER, GIFT, PASSWORD, KICK, SWEET, BUBBLY, FIREWORK, INVITE, INVITE_ALL, POINT = (
    101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112,
)  # fmt: skip
PRIEST, STEWARD = 3, 8  # CampaignNode.param1 (MarryWeddingDialogFrame.initOptionsWedding)
DIALOG = 11  # CampaignConfirmMsg.type 11/12: abre o MarryWeddingDialogFrame (CampaignMapController)
WAITING, PARTY = 1, 3  # 4674 property2: 3 libera as ações do criado (MarryModel.can*)
ROOM_TYPE = 4  # RoomInviteMsg.roomType / link do chat (ChatFormat: MarryCampaignInfo)
MIN_GRADE = 30  # MarryModel.canEnterWedding: grades > 30
NO_ENTRY = "You cannot enter this wedding."
DEFAULTS: dict[str, Any] = {"action_happy": 10, "fireworks": 2000, "oath": ["I now pronounce you married!"]}


@dataclass
class Wedding:
    a: int
    b: int
    nick_a: str
    nick_b: str
    spec: int
    number: int
    started: datetime
    password: str = ""
    state: int = WAITING
    cake: bool = False
    bubbly: bool = False
    flower_a: bool = False
    flower_b: bool = False
    sweet: bool = False
    rode: bool = False
    gifted: list[int] = field(default_factory=list)
    points: dict[int, int] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.a}_{self.b}"  # MarryRoomItem: ``userIdA + "_" + userIdB``

    def master(self, pid: int) -> bool:
        return pid in (self.a, self.b)


_weddings: dict[str, Wedding] = {}


def cfg(ctx: GameContext) -> dict[str, Any]:
    return DEFAULTS | dict(ctx.world.settings.get("wedding_room") or {})


def of_couple(pid: int) -> Wedding | None:
    return next((w for w in _weddings.values() if w.master(pid)), None)


def _spec(ctx: GameContext, w: Wedding) -> dict[str, Any]:
    return dict(ctx.templates.get("MarrySpecTempInfos", w.spec) or {})


def map_of(ctx: GameContext, w: Wedding) -> int:
    return int(_spec(ctx, w).get("CampaignId") or 4303)


def here(ctx: GameContext, w: Wedding) -> list[GameSession]:
    return [o for o in ctx.online.sessions() if o.campaign is not None and o.campaign.wedding == w.key]


def _current(s: GameSession) -> Wedding | None:
    return _weddings.get(s.campaign.wedding) if s.campaign is not None and s.campaign.wedding else None


def room_msg(w: Wedding) -> pb.MarriageProMsg:
    """4662 (MarryRoomItem): ``property1`` trancada, 2 o tipo (moldura), 3 o número, 4 o início (o relógio de
    ``mar_time`` do MarryUIMediator), 7 a cerimônia (MarryModel.canRideCar)."""
    return b.complete(pb.MarriageProMsg(
        userIdA=w.a, nickNameA=w.nick_a, userIdB=w.b, nickNameB=w.nick_b, property1=bool(w.password),
        property2=w.spec, property3=w.number, property4=b.fmt_time(w.started), property7=w.spec,
    ))  # fmt: skip


def info_msg(w: Wedding, viewer: int) -> pb.MarriageProMsg:
    """4674 (MarryWeddingInfo) para ``viewer``: 1 doces, 2 a fase, 3 champanhe, 4 "0" = ainda pode dar presente, 6 bolo,
    7/8 flores de A/B, 9 a cerimônia, 10 pontos já dados por ele."""
    return b.complete(pb.MarriageProMsg(
        userIdA=w.a, nickNameA=w.nick_a, userIdB=w.b, nickNameB=w.nick_b, property1=w.sweet, property2=w.state,
        property3=int(w.bubbly), property4="1" if viewer in w.gifted else "0", property6=int(w.cake),
        property7=int(w.flower_a), property8=int(w.flower_b), property9=w.spec, property10=w.points.get(viewer, 0),
    ))  # fmt: skip


def tell(ctx: GameContext, w: Wedding) -> None:
    for o in here(ctx, w):
        o.send(S_INFO, info_msg(w, o.player_id))


def _guests(w: Wedding, sessions: list[GameSession], present: bool) -> pb.EngageMsg:
    """4673 (MarryManager.__guestInfoHandler): ``property1`` falso tira da lista; ``property2`` 1 = deu presente."""
    out = pb.EngageMsg()
    for o in sessions:
        if o.snapshot is not None and not w.master(o.player_id):
            c = o.snapshot.character
            out.engageInfos.append(b.complete(pb.MarriageProMsg(userIdA=o.player_id, nickNameA=c.nickname or "",
                                                                jobA=c.job, property1=present,
                                                                property2=int(o.player_id in w.gifted))))  # fmt: skip
    return out


async def create(s: GameSession) -> None:
    """Op 6: o casal (noivo ou casado) com cerimônia (reservada ou a do casamento) e sem sala abre uma."""
    snap = s.snapshot
    assert snap is not None
    m = snap.marriage
    reserved = int(mr.couple(m).get("reserved") or 0)
    spec = reserved or (m.spec_id if m is not None and m.state == mr.MARRIED else 0)
    if m is None or m.state not in mr._CEREMONY or not spec or of_couple(s.player_id) is not None:
        s.log.info("sala de casamento recusada", spec=spec)
        return
    mate = (await social.characters(s.ctx, [m.mate_id])).get(m.mate_id)
    number = max((w.number for w in _weddings.values()), default=0) + 1
    w = Wedding(s.player_id, m.mate_id, snap.character.nickname or "", mate.nickname or "" if mate else "", spec,
                number, s.ctx.clock.now())  # fmt: skip
    _weddings[w.key] = w
    for cid in (w.a, w.b):
        if (o := s.ctx.online.get(cid)) is not None:
            o.send(S_ROOMS, pb.EngageMsg(engageInfos=[room_msg(w)]))


def room_list(s: GameSession) -> None:
    s.send(S_ROOMS, pb.EngageMsg(engageInfos=[room_msg(w) for w in _weddings.values()]))


async def enter(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Op 13 (``property3`` "a_b", ``property4`` a senha, ``property5`` veio do link do chat)."""
    snap, w = s.snapshot, _weddings.get(msg.property3)
    assert snap is not None
    ok = (
        w is not None
        and s.battle is None
        and s.campaign is None
        and (
            w.master(s.player_id)
            or (snap.character.grades > MIN_GRADE and (not w.password or msg.property4 == w.password or msg.property5))
        )
    )
    content = s.ctx.world.campaigns.get(map_of(s.ctx, w)) if w is not None else None
    if not ok or w is None or content is None:
        s.log.info("entrada no casamento recusada", sala=msg.property3, conteudo=content is not None)
        alert(s, NO_ENTRY)
        return
    ctx, now, map_id = s.ctx, s.ctx.clock.now(), map_of(s.ctx, w)
    data = content["maps"][str(map_id)]
    nodes = {int(n["campDataId"]): dict(n) for n in data["nodes"]}
    x, y = data["start"]
    s.campaign = CampaignMap(map_id, nodes, (int(x), int(y)), content=content, wedding=w.key)
    space.leave(s)
    room = pb.RoomCreatedMsg(createdType=wb.ROOM_ENTER)
    room.room.campaignId = map_id
    s.send(wb.S_ROOM_CREATED, room)
    s.send(wb.S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    me = space.room_player(snap, ctx.templates, s.campaign.pos, map_id, now)
    others = [o for o in here(ctx, w) if o is not s]
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, map_id, now)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(wb.S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    for o in others:
        o.send(wb.S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
        o.send(S_GUESTS, _guests(w, [s], True))
    s.send(wb.S_NODES, s.campaign.node_list())
    s.send(wb.S_FULL_ARMY, b.complete(army(s, snap)[0]))
    s.send(S_INFO, info_msg(w, s.player_id))
    s.send(S_GUESTS, _guests(w, here(ctx, w), True))


def leave(s: GameSession) -> bool:
    """Sai do salão (5025, expulso, fim do tempo ou desconexão): 22 para todos no salão, o próprio também."""
    c, snap, w = s.campaign, s.snapshot, _current(s)
    if c is None or not c.wedding or snap is None:
        return False
    msg = pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id, serverName=snap.server.name)
    others = [o for o in here(s.ctx, w) if o is not s] if w is not None else []
    for o in others:
        o.send(wb.S_EXIT, msg)
        if w is not None:
            o.send(S_GUESTS, _guests(w, [s], False))
    s.campaign = None
    s.send(wb.S_EXIT, msg)
    return True


def arrive(s: GameSession, node: dict[str, Any]) -> None:
    """5125 num NPC do salão: o 29 tipo 11 abre o MarryWeddingDialogFrame (as opções saem do 4674)."""
    if int(node.get("param1") or 0) in (PRIEST, STEWARD) and s.campaign is not None:
        s.send(S_CONFIRM, pb.CampaignConfirmMsg(mapId=s.campaign.map_id, nodeId=int(node["nodeId"]), type=DIALOG))


def moved(s: GameSession, msg: pb.PosMoveMsg) -> None:
    w = _current(s)
    for o in here(s.ctx, w) if w is not None else []:
        if o is not s and s.campaign is not None:
            o.send(S_MOVE, pb.PosMoveMsg(mapId=s.campaign.map_id, armyId=s.player_id, routes=msg.routes))


async def ride(s: GameSession) -> None:
    """Op 7: o carro do casal (4672 a todos online; ``property4`` o ``Path`` da cerimônia, que o MarryCarAi anda)."""
    w = of_couple(s.player_id)
    path = str(_spec(s.ctx, w).get("Path") or "") if w is not None else ""
    if w is None or w.state != PARTY or w.rode or not path:
        s.log.info("passeio de carro recusado", sala=w and w.key)
        return
    w.rode = True
    jobs = await social.characters(s.ctx, [w.a, w.b])
    car = b.complete(pb.MarriageProMsg(userIdA=w.a, nickNameA=w.nick_a, userIdB=w.b, nickNameB=w.nick_b,
                                       property4=path, property6=jobs[w.a].job if w.a in jobs else 0,
                                       property7=jobs[w.b].job if w.b in jobs else 0))  # fmt: skip
    for o in s.ctx.online.sessions():
        o.send(S_CAR, car)


async def _oath(s: GameSession, w: Wedding) -> bool:
    """101: casa (noivo) ou renova a cerimônia (casado), os presentes da cerimônia pelo correio e as falas (4660)."""
    snap = s.snapshot
    assert snap is not None and snap.marriage is not None
    mate = s.ctx.online.get(snap.marriage.mate_id)
    reserved = int(mr.couple(snap.marriage).get("reserved") or 0)
    if not reserved or w.state != WAITING or mate is None or mate not in here(s.ctx, w):
        return False
    m = snap.marriage
    other = await mr._row(s.ctx, m.mate_id)
    data = mr.couple(m)
    data.pop("reserved", None)
    for row in (m, *([other] if other is not None else [])):
        row.couple = json.dumps(data)
    await mr._couple(s, mr.MARRIED, reserved)
    await mr.ensure_tree(s.ctx, snap)
    w.state, w.spec = PARTY, reserved
    spec = _spec(s.ctx, w)
    goods = [(int(t), int(n)) for t, n in (p.split(",") for p in str(spec.get("Rewards") or "").split("|") if p)]
    for cid in (w.a, w.b):  # presentes da cerimônia pelo correio (até 5 por correio)
        for i in range(0, len(goods), 5):
            await send_system_mail(s.ctx, cid, spec["TemplateName"], spec["TemplateName"], goods[i : i + 5])
    names = {"a": w.nick_a, "b": w.nick_b}
    speakers = [(0, 0, "Priest"), (w.a, 1, w.nick_a), (w.b, 2, w.nick_b)]
    for i, line in enumerate(cfg(s.ctx)["oath"]):
        uid, role, name = speakers[0] if i % 2 == 0 or i == len(cfg(s.ctx)["oath"]) - 1 else speakers[1 + (i // 2) % 2]
        out = pb.MarriageProMsg(property2=uid, property3=role, property4=line.format(**names), property5=name)
        for o in here(s.ctx, w):
            o.send(S_OATH, b.complete(out))
    return True


async def _pay_gold(s: GameSession, amount: int) -> bool:
    snap = s.snapshot
    assert snap is not None
    if amount <= 0 or snap.character.gold < amount:
        return False
    snap.character.gold -= amount
    s.send(wb.S_PLAYER, b.complete(player_info(s, snap)))
    return True


async def _to_couple(ctx: GameContext, w: Wedding, gold: int = 0, bound: int = 0) -> None:
    """(dedução) metade para cada um do casal; online pela sessão, offline pelo banco."""
    found = await social.characters(ctx, [w.a, w.b])
    for c in found.values():
        c.gold += gold // 2
        c.gift_token += bound // 2
        await ctx.characters.save(c)
        if (o := ctx.online.get(c.id or 0)) is not None and o.snapshot is not None:
            o.send(wb.S_PLAYER, b.complete(player_info(o, o.snapshot)))


@router.on(8760)
async def wedding_dialog(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """O padre e o criado (MarryWeddingDialogFrame), senha (105), expulsar (106) e convites (110/111)."""
    w, op, snap = _current(s) or of_couple(s.player_id), msg.opType, s.snapshot
    assert snap is not None
    if w is None:
        s.log.info("8760 fora do casamento", op=op)
        return
    master, ctx = w.master(s.player_id), s.ctx
    happy = int(cfg(ctx)["action_happy"])
    done = False
    if op == OATH and master:
        done = await _oath(s, w)
    elif op in (CAKE, BUBBLY, FLOWER, SWEET) and master and w.state == PARTY:
        flag = {
            CAKE: "cake",
            BUBBLY: "bubbly",
            SWEET: "sweet",
            FLOWER: "flower_a" if s.player_id == w.a else "flower_b",
        }
        if not getattr(w, flag[op]):
            setattr(w, flag[op], True)
            await mr.add_happy(s, happy)
            done = True
    elif op == GIFT and not master and w.state == PARTY and s.player_id not in w.gifted:
        row = next(ctx.templates.find("ConfigInfos", ConfigName="marriage_gift"), None)
        tiers = [int(x) for x in row["ConfigValue"].split(",")] if row else []
        amount = tiers[3 - w.spec] if 1 <= w.spec <= 3 and len(tiers) == 3 else 100000  # o cliente: 3 - spec
        if msg.property1 == amount and await _pay_gold(s, amount):
            w.gifted.append(s.player_id)
            await ctx.characters.save(snap.character)
            await _to_couple(ctx, w, gold=amount)
            for o in here(ctx, w):
                o.send(S_GUESTS, _guests(w, [s], True))
            done = True
    elif op == POINT and not master and w.state == PARTY and w.points.get(s.player_id, 0) < 4 - w.spec:
        entry = mr._pay(s, snap.character, msg.property1, mr.POINT, "wedding_point") if msg.property1 > 0 else None
        if entry is not None:
            w.points[s.player_id] = w.points.get(s.player_id, 0) + 1
            await ctx.characters.save(snap.character, entry)
            s.send(wb.S_PLAYER, b.complete(player_info(s, snap)))
            await _to_couple(ctx, w, bound=msg.property1)
            done = True
    elif op == FIREWORK and w.state == PARTY:
        row = next(ctx.templates.find("ConfigInfos", ConfigName="marriage_fireworks"), None)
        done = await _pay_gold(s, int(row["ConfigValue"]) if row else int(cfg(ctx)["fireworks"]))
        if done:
            await ctx.characters.save(snap.character)
    elif op == PASSWORD and master:
        w.password, done = msg.property3[:6], True
        for o in here(ctx, w):
            o.send(S_ROOMS, pb.EngageMsg(engageInfos=[room_msg(w)]))
    elif (
        op == KICK and master and (target := ctx.online.get(msg.property1)) is not None and not w.master(msg.property1)
    ):
        done = target in here(ctx, w) and leave(target)
    elif op in (INVITE, INVITE_ALL) and master:
        for uid in [msg.property1] if op == INVITE else list(msg.userIds):
            guest = ctx.online.get(uid)
            if guest is not None and guest is not s and guest.campaign is None:
                guest.send(S_ROOMS, pb.EngageMsg(engageInfos=[room_msg(w)]))  # o link precisa da sala no roomDic
                guest.send(S_INVITE, pb.RoomInviteMsg(playerId=s.player_id, nickName=snap.character.nickname or "",
                                                  name=str(_spec(ctx, w).get("TemplateName") or ""),
                                                  signStr=w.password, roomType=ROOM_TYPE, userKey=w.key))  # fmt: skip
        done = True
    if not done:
        s.log.info("8760 recusado", op=op, fase=w.state)
        return
    tell(ctx, w)
    await mr.save_pending(ctx)


async def clock(s: GameSession) -> None:
    """Fim pelo tempo (ConfigInfo ``mar_time`` em minutos, 120 sem ele; MarryUIMediator): todos saem e a sala some."""
    ctx, now = s.ctx, s.ctx.clock.now()
    minutes = mr._config(ctx, "mar_time", 120)
    over = [w for w in _weddings.values() if now - w.started >= timedelta(minutes=minutes)]
    for w in over:
        for o in here(ctx, w):
            leave(o)
        del _weddings[w.key]
    if over:
        await mr.save_pending(ctx)


def link(w: Wedding, ctx: GameContext) -> dict[str, object]:
    """Atributos do link do 8353 tipo 1 (ChatFormat roomType 4: ``id`` a chave, ``position`` a senha)."""
    return {"campaignId": map_of(ctx, w), "position": w.password, "roomType": ROOM_TYPE}


def dump() -> list[dict[str, Any]]:
    return [asdict(w) | {"started": w.started.isoformat()} for w in _weddings.values()]


def load(rows: list[dict[str, Any]]) -> None:
    for r in rows:
        w = Wedding(**(r | {"started": datetime.fromisoformat(r["started"]),
                            "points": {int(k): v for k, v in r.get("points", {}).items()}}))  # fmt: skip
        _weddings[w.key] = w
