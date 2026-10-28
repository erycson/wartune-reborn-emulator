"""Guerra de guildas no mapa 4501: entrar (8471), a lista de participantes (8473), os buffs (8547), as torres, o
placar, os mortos, o fim e o prêmio. As regras puras estão em ``game/guildwar.py``.

(visto) sessão 20261026-225632-1, lado vermelho (Stormborn x Guild):

- 8471 -> 125 {createdType 1, 4501}, 140, 21, 127, 4439, 4440 (#2466-#2472); o 5035 state 4 -> 21 com todos,
  4450, 4457 (segundos até a barreira cair) e 4462 (#2474-#2477); os outros recebem o 21 de quem entrou e o 4462.
- A barreira (masterType 53) some na abertura: 143 ``DISAPPEARD`` e 128 state 8 com uuId (#2586-#2589).
- Mystery Tower: 5125 -> 29 "Are you sure you want to defend?" e 4126 (#2772-#2775); 5033 -> 111 "You are now
  defending!..." e 4175 state 4; a torre tomada: 111 a todos, 128 state 16/17 com o lado e 4439 (#2705-#2760).
  Andar para longe: 111 "too far away" e 4175 state 0 (#2854-#2855).
- Ward Tower inimiga: 5125 -> 140, 157 battleType 20 (#2942-#2945); o fim: 140, 4175 state 1, 4103 (scene 12,
  strategy 435), 100 e o 4382 na volta (#2986-#3012); morto até o tique seguinte (4175 state 0 com o 4439).
- No acampamento morto: 111 "You cannot leave camp when dead!" e 4126 (#3030-#3032).
- O fim (#6249-#6302): 111 a todos, 4439, a saída (22, 4165, 140, 4595) e o prêmio (4471, 3, 115, 111).
"""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Mapping
from typing import Any

import structlog

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from .. import boss_fight, outer_city, rewards, space
from .. import guildwar as gw
from ..battle import Battle, SharedHp
from ..builders import login as b
from ..builders.army import castle_pawns
from ..campaign import CampaignMap
from ..router import router
from ..session import GameContext, GameSession
from .campaign import (
    ARMY_FIGHTING,
    ARMY_IDLE,
    ENTER,
    S_ARMY_PAWN,
    S_BATTLE_REPORT,
    S_CONFIRM,
    S_EXIT,
    S_FULL_ARMY,
    S_MAP_SYNC,
    S_MOVIE,
    S_NODE,
    S_NODES,
    S_ROOM_CREATED,
    S_ROOM_ENTER,
    S_STANDPOS,
    _push_player,
    _uuid,
    boosted,
    exit_to_city,
    map_sync,
    player_hero,
)
from .guild.common import _alert, _mine, _push_info, _refuse
from .guild.info import member_list
from .login import army
from .player import hero_after_fight, hp_pack

S_SCORE, S_BUFFERS, S_HP, S_WOUND, S_COUNT, S_LEFT = 4439, 4440, 4450, 4460, 4462, 4457
S_STATE, S_MOVE, S_HONOR_DAY, S_ITEMS, S_PLAYER = 4175, 4185, 4471, 115, 3
S_ARMY_MOVED, S_ARMY_UPDATE = 4104, 131  # (visto #3335-#3336) o morto no acampamento
TOWER_BATTLE = "450104"  # a luta da captura (#2945) serve às duas Ward Towers
CONFIRM_MAP = 3644  # (visto #2774) CampaignConfirmMsg.mapId
GONE = 8  # nodeState da barreira caída (#2589)
DEFEND_ASK = "Are you sure you want to defend?"  # (visto #2774)
DEFENDING = "You are now defending! Move away from the Mystery Tower if you do not wish to defend it any longer."
TOO_FAR = "You are too far away from the Mystery Tower and are no longer defending it!"  # (visto #2854)
FULL = "Maximum defense member reached!"  # (visto #3142)
DEAD_CAMP = "You cannot leave camp when dead!"  # (visto #3031)
LATE_TEXT = (  # (visto #4884)
    "The Guild Battle has lasted for 20 mins. The winner's rewards will now be reduced, while the loser's rewards "
    "will be increased."
)
WIN_TEXT = "Guild [{win}] has claimed victory, having earned {lead:,} more points than guild [{lose}]!"  # #6249
STRATEGY = 435  # (visto #2990, #3443 ... #5541) strategyBonus de cada luta na torre
SCENE = 12  # (visto #2990) battleScene
RANGE = 2  # TODO(inventado): distância (tiles) da Mystery Tower em que a defesa vale (handlerRange 1 no nó)
WOUND_EVERY = 8  # (dedução) o 4460/4450 sai a cada poucos segundos (219 em ~27 min); como o 4174 do chefe
INSIGNIA, WHIP = 208001, 208017  # ItemTempInfos "Insignia" e "Mount Training Whip" (#6276, #6289)
# (visto #6273-#6302) a guilda vencedora depois dos 20 min: "Received 850 Honor, Insignia x950, Mount Training Whip
# x40, and 850 Contribution."; TODO(inventado): o mesmo antes dos 20 min e a metade para a perdedora
PRIZE_HONOR, PRIZE_OFFER, PRIZE_ITEMS = 850, 850, ((INSIGNIA, 950), (WHIP, 40))
log = structlog.get_logger(__name__)


# ---- estado e mensagens ---------------------------------------------------------------------------


def _top(ctx: GameContext) -> list[int]:
    """As 8 guildas de maior poder (a mesma ordem do 4441)."""
    g = ctx.guilds
    return [x.id or 0 for x in sorted(g.guilds.values(), key=lambda x: -g.fight_power(x.id or 0))][: 2 * gw.GROUPS]


def war_of(s: GameSession) -> tuple[gw.War, gw.Side] | None:
    mine = _mine(s)
    war = s.ctx.guilds.wars.get(mine[0].id or 0) if mine else None
    me = war.of(mine[0].id or 0) if war is not None and mine is not None else None
    return (war, me) if war is not None and me is not None else None


def players_on(ctx: GameContext, war: gw.War) -> list[GameSession]:
    ids = {war.red.guild_id, war.blue.guild_id}
    return [o for o in ctx.online.sessions()
            if o.campaign is not None and o.campaign.gvg and o.snapshot is not None
            and (m := ctx.guilds.of(o.player_id)) is not None and m[0].id in ids]  # fmt: skip


def _side_of(ctx: GameContext, war: gw.War, player_id: int) -> int:
    m = ctx.guilds.of(player_id)
    me = war.of(m[0].id or 0) if m else None
    return me.side if me else 0


def _to_all(ctx: GameContext, war: gw.War, code: int, msg: Any, but: GameSession | None = None) -> None:
    for o in players_on(ctx, war):
        if o is not but:
            o.send(code, msg)


def _score(war: gw.War) -> pb.GuildWarInfoListMsg:
    """4439 (visto #2471): as duas guildas, vermelha primeiro; ``noviceCount`` = Mystery Towers da guilda."""
    msg = pb.GuildWarInfoListMsg()
    for x in war.sides():
        msg.guildWarInfos.add(consortiaId=x.guild_id, consrotiaName=x.name, noviceCount=war.towers(x.side),
                              score=x.score)  # fmt: skip
    return msg


def _buffers(war: gw.War, me: gw.Side, content: Mapping[str, Any]) -> pb.GuildBufferListMsg:
    """4440 (visto #2472): os 4 buffs com os usos que restam e o início da espera (``param1``)."""
    msg = pb.GuildBufferListMsg(consortiaId=me.guild_id)
    for row in content.get("buffers", []):
        used, at = me.buffs.get(row["templateId"], (0, None))
        msg.buffers.add(templateId=row["templateId"], consortiaId=me.guild_id, bufferName=row["bufferName"],
                        curreCount=row["curreCount"] - used, maxCdTimer=row["maxCdTimer"],
                        objectData=row["objectData"], needPay=row["needPay"], descr=row["descr"],
                        param1=b.fmt_time(at) if at else gw.NO_DATE)  # fmt: skip
    return msg


def _hp(war: gw.War, c: CampaignMap) -> pb.NodeHpListMsg:
    """4450 (visto #2475): as duas Ward Towers pelo campDataId. ``campaignId`` (101932 no oficial, o número da sala)
    o cliente não lê."""
    msg = pb.NodeHpListMsg()
    for camp, node in c.nodes.items():
        if node["masterType"] == gw.WARD:
            msg.nodeHp.add(nodeId=camp, currentHp=war.side(int(node["param1"])).hp, totalHp=gw.TOWER_HP)
    return msg


def _wounds(war: gw.War) -> pb.WorldBossInfoMsg:
    """4460 (visto #2597): todos os que entraram, em ``woundInfo`` e ``castleWound`` (o cliente lê o 2º)."""
    msg = pb.WorldBossInfoMsg()
    for pid, w in war.wounds.items():
        row = dict(userId=pid, nickName=w.nickname, wound=w.wound, job=w.job)
        msg.woundInfo.add(**row)
        msg.castleWound.add(**row)
    return msg


def _count(ctx: GameContext, war: gw.War) -> pb.GuildJoinPlayerInfoMsg:
    """4462 (visto #2477): quantos de cada guilda estão no mapa."""
    on = players_on(ctx, war)
    n = {x.side: sum(1 for o in on if _side_of(ctx, war, o.player_id) == x.side) for x in war.sides()}
    return pb.GuildJoinPlayerInfoMsg(redConsortiaId=war.red.guild_id, redCount=n[gw.RED],
                                     blueConsortiaId=war.blue.guild_id, blueCount=n[gw.BLUE])  # fmt: skip


def _state(player_id: int, state: int) -> pb.PlayerStateListMsg:
    msg = pb.PlayerStateListMsg()
    msg.playerState.add(armyId=player_id, state=state)
    return msg


def _tower_update(camp: int, node: dict[str, Any], side: int) -> pb.CampaignNodeUpdateMsg:
    """128 da Mystery Tower tomada (visto #2706 e #4067): state 16 ou 17 e ``param1`` = lado, sem uuId."""
    node["state"] = gw.OWNED[side]
    return pb.CampaignNodeUpdateMsg(nodeId=node["nodeId"], nodeState=node["state"], param1=side)


def _nodes(content: Mapping[str, Any], war: gw.War) -> dict[int, dict[str, Any]]:
    """Os nós do 127 com a barreira e as Mystery Towers de agora."""
    nodes = {n["campDataId"]: copy.deepcopy(n) for n in content["maps"][str(gw.WAR_MAP)]["nodes"]}
    for camp, node in nodes.items():
        if node["masterType"] == gw.GATE and war.gates_open:
            node["state"] = GONE
        elif node["masterType"] == gw.MYSTERY and (side := war.owner.get(camp, 0)):
            _tower_update(camp, node, side)
    return nodes


def _wound(s: GameSession, war: gw.War) -> gw.Wound:
    ch = s.snapshot.character  # type: ignore[union-attr]
    return war.wound_of(s.player_id, ch.nickname or "", boss_fight.CLASS_JOB[boss_fight.job_class(ch.job)])


# ---- entrar, lista de participantes, buffs --------------------------------------------------------


def _start(ctx: GameContext, guild_id: int) -> gw.War | None:
    """A guerra de hoje da guilda: a que já existe ou uma nova com a adversária do 4441, se a janela está aberta."""
    now = ctx.clock.now()
    opened, ends = gw.window(now)
    war = ctx.guilds.wars.get(guild_id)
    if isinstance(war, gw.War) and war.opened == opened:
        return war
    if not opened <= now < ends:
        return None
    pair = gw.pairs(_top(ctx)).get(guild_id)
    if pair is None:
        return None
    other, side, _ = pair
    red, blue = (guild_id, other) if side == gw.RED else (other, guild_id)
    g = ctx.guilds.guilds
    war = gw.War(gw.Side(red, g[red].name, gw.RED), gw.Side(blue, g[blue].name, gw.BLUE), opened)
    ctx.guilds.wars[red] = ctx.guilds.wars[blue] = war
    war.ticker = asyncio.get_running_loop().create_task(_clock(ctx, war))
    return war


@router.on(8471)
async def enter(s: GameSession, _: object) -> None:
    """Entrar: membro na lista (``gvg_out`` falso ou o líder, ``gvg.NotinWarList``), fora de luta e de outro mapa,
    na janela da guerra e com adversária. Sem guerra o oficial não foi visto recusando: só o log."""
    mine, snap, content = _mine(s), s.snapshot, s.ctx.world.campaigns.get(gw.WAR_MAP)
    if mine is None or snap is None or content is None or s.battle is not None or s.campaign is not None:
        _refuse(s, 8471, "sem guilda, sem conteúdo ou já num mapa", conteudo=content is not None)
        return
    guild, member = mine
    if member.gvg_out and guild.chairman_id != s.player_id:
        _refuse(s, 8471, "fora da lista de participantes")
        return
    war = _start(s.ctx, guild.id or 0)
    me = war.of(guild.id or 0) if war is not None else None
    if war is None or me is None or war.settled:
        _refuse(s, 8471, "sem guerra agora ou sem adversária")
        return
    x, y = content["starts"][str(me.side)]
    space.leave(s)
    s.campaign = CampaignMap(gw.WAR_MAP, _nodes(content, war), (int(x), int(y)), content=content, gvg=True)
    _wound(s, war)
    room = pb.RoomCreatedMsg(createdType=ENTER)
    room.room.campaignId = gw.WAR_MAP
    s.send(S_ROOM_CREATED, room)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    s.send(S_ROOM_ENTER, _room_player(s))
    s.send(S_NODES, s.campaign.node_list())
    s.send(S_SCORE, _score(war))
    s.send(S_BUFFERS, _buffers(war, me, content))
    s.log.info("entrou na guerra de guildas", lado=me.side, adversaria=war.enemy(me).guild_id)


def _room_player(s: GameSession, *others: GameSession) -> pb.RoomEnterMsg:
    now = s.ctx.clock.now()
    return pb.RoomEnterMsg(result=1, player=[
        space.room_player(o.snapshot, s.ctx.templates, o.campaign.pos, gw.WAR_MAP, now)  # type: ignore[arg-type,union-attr]
        for o in (s, *others)
    ])  # fmt: skip


def show_map(s: GameSession) -> None:
    """1º 5035 state 4 (visto #2474-#2477): 21 com todos, 4450, 4457 e 4462; os outros veem quem chegou."""
    c, found = s.campaign, war_of(s)
    assert c is not None
    c.ready = True
    if found is None:
        return
    war, _ = found
    others = [o for o in players_on(s.ctx, war) if o is not s]
    s.send(S_ROOM_ENTER, _room_player(s, *others))
    s.send(S_HP, _hp(war, c))
    left = int((war.gates_at - s.ctx.clock.now()).total_seconds())
    if left > 0:
        s.send(S_LEFT, pb.GuildMsg(param1=left))
    for o in others:
        o.send(S_ROOM_ENTER, _room_player(s))
    _to_all(s.ctx, war, S_COUNT, _count(s.ctx, war))
    if s.player_id in war.dead:
        s.send(S_STATE, _state(s.player_id, gw.DEAD))


def leave_war(s: GameSession) -> bool:
    """5025 ou desconexão: a luta acaba, a defesa também, 22 a todos e o 4462 novo (visto #4541-#4542)."""
    c, snap, found = s.campaign, s.snapshot, war_of(s)
    if c is None or not c.gvg or snap is None:
        return False
    if s.battle is not None:
        s.battle.cancel()
        s.battle = None
    if found is not None:
        found[0].stop_defending(s.player_id)
    exit_to_city(s)
    if found is not None:
        war = found[0]
        _to_all(s.ctx, war, S_EXIT, pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id))
        _to_all(s.ctx, war, S_COUNT, _count(s.ctx, war))
    return True


def _manager(guild_chair: int, member: Any, player_id: int) -> bool:
    """(cliente) ``GvgModel.isFightManager``: o líder, o vice na lista ou quem tem o papel (op 2)."""
    return (
        player_id == guild_chair
        or member.duty_id == 1
        or (member.duty_id == 2 and not member.gvg_out)
        or (member.gvg_role == 1)
    )


@router.on(8473)
async def team_edit(s: GameSession, msg: pb.TeamEditMsg) -> None:
    """Lista de participantes (cliente ``GvgEnterWar*``): op 0 põe, 1 tira (o líder nunca), 2 dá ou tira o papel de
    gerente (``param1``). Só o gerente da luta; a resposta é a lista de membros nova (4133)."""
    mine = _mine(s)
    target = s.ctx.guilds.members.get(msg.userId)
    if mine is None or target is None or target.consortia_id != mine[0].id:
        _refuse(s, 8473, "sem guilda ou de outra guilda", alvo=msg.userId)
        return
    guild, member = mine
    if not _manager(guild.chairman_id, member, s.player_id) or (msg.op == 1 and msg.userId == guild.chairman_id):
        _refuse(s, 8473, "sem direito", alvo=msg.userId, op=msg.op)
        return
    if msg.op in (0, 1):
        target.gvg_out = msg.op == 1
    elif msg.op == 2:
        target.gvg_role = 1 if msg.param1 else 0
    else:
        _refuse(s, 8473, "op desconhecido", op=msg.op)
        return
    await s.ctx.characters.save(target)
    await member_list(s, None)


@router.on(8547)
async def buy_buff(s: GameSession, msg: pb.GuildMsg) -> None:
    """Buff da guerra (``param1`` = templateId), (cliente) ``GvgBufferIcon``: só líder ou vice (``dutyId`` 1/2),
    paga ``needPay`` da riqueza da guilda, respeita os usos e a espera. Efeitos: Inspiration (1) dá a fúria na
    próxima luta de cada membro, Goddess Blessing (4) cura 30% da própria Ward Tower; TODO(inventado): Call to Arms
    (2, a carruagem) e Invincible (3) só gastam: sem captura do efeito."""
    found, mine, c = war_of(s), _mine(s), s.campaign
    if found is None or mine is None or c is None or not c.gvg or c.content is None or found[0].settled:
        _refuse(s, 8547, "fora da guerra", buff=msg.param1)
        return
    war, me = found
    guild, member = mine
    row = next((r for r in c.content.get("buffers", []) if r["templateId"] == msg.param1), None)
    now = s.ctx.clock.now()
    if row is None or member.duty_id not in (1, 2) or guild.offer < row["needPay"]:
        _refuse(s, 8547, "buff, direito ou riqueza", buff=msg.param1, riqueza=guild.offer)
        return
    if not war.can_buff(me, row["templateId"], row["curreCount"], row["maxCdTimer"], now):
        _refuse(s, 8547, "sem usos ou esperando", buff=msg.param1)
        return
    guild.offer -= row["needPay"]
    war.use_buff(me, row["templateId"], now)
    await s.ctx.characters.save(guild)
    _push_info(s, guild)
    for o in players_on(s.ctx, war):
        if _side_of(s.ctx, war, o.player_id) == me.side:
            o.send(S_BUFFERS, _buffers(war, me, c.content))
    if row["templateId"] == gw.BLESSING:
        _to_all(s.ctx, war, S_HP, _hp(war, c))
    s.log.info("guerra de guildas: buff", buff=row["templateId"], riqueza=guild.offer)


# ---- no mapa --------------------------------------------------------------------------------------


async def arrive(s: GameSession, camp: int, node: dict[str, Any]) -> None:
    """5125: acampamento, Mystery Tower, Ward Tower inimiga ou a barreira."""
    c, found = s.campaign, war_of(s)
    if c is None or found is None or s.battle is not None or c.fighting:
        return
    war, me = found
    kind, back = node["masterType"], (int(node["resetX"]), int(node["resetY"]))
    if kind == gw.CAMP and s.player_id in war.dead:
        _alert(s, DEAD_CAMP)
        _stand(s, back)
    elif s.player_id in war.dead or war.settled:
        return
    elif kind == gw.GATE and not war.gates_open:
        _stand(s, back)  # (dedução, como a barreira do chefe) antes da abertura não se passa
    elif kind == gw.MYSTERY and war.gates_open:
        s.send(S_CONFIRM, pb.CampaignConfirmMsg(title="Note", body=DEFEND_ASK, mapId=CONFIRM_MAP, nodeId=camp))
        _stand(s, back)
    elif kind == gw.WARD and int(node["param1"]) != me.side and war.gates_open:
        _attack(s, war, me, camp)


def _stand(s: GameSession, pos: tuple[int, int]) -> None:
    assert s.campaign is not None
    s.campaign.pos = pos
    s.send(S_STANDPOS, pb.StandPosMsg(id=s.player_id, posX=pos[0], posY=pos[1]))


async def confirm(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """5033 no 29 da Mystery Tower: entra na defesa (até ``param2`` do nó, dedução) e toma a torre."""
    c, found = s.campaign, war_of(s)
    node = c.node(msg.paraInt2) if c is not None else None
    if not msg.paraBool1 or found is None or node is None or node["masterType"] != gw.MYSTERY:
        return
    war, me = found
    if s.player_id in war.dead or war.settled or not war.gates_open:
        return
    enemies = {o.player_id for o in players_on(s.ctx, war) if _side_of(s.ctx, war, o.player_id) != me.side}
    got = war.defend(msg.paraInt2, s.player_id, me, enemies, int(node["param2"]) or 1)
    if got == "full":
        _alert(s, FULL)
        return
    _alert(s, DEFENDING)
    _to_all(s.ctx, war, S_STATE, _state(s.player_id, gw.DEFENDING))
    if got == "taken":
        n = war.towers(me.side)
        text = (f"Guild [{me.name}] occupied {n} Mystery Tower{'s' if n > 1 else ''}, damage received by opponent "
                f"Ward Tower {gw.EFFECT[n]}")  # fmt: skip
        for o in players_on(s.ctx, war):
            _alert(o, text)
            if (mine := o.campaign.node(msg.paraInt2)) is not None:  # type: ignore[union-attr]
                o.send(S_NODE, _tower_update(msg.paraInt2, mine, me.side))
        _to_all(s.ctx, war, S_SCORE, _score(war))


def moved(s: GameSession, msg: pb.PosMoveMsg) -> None:
    """5124: o caminho aos outros do mapa (4185, como no campo) e a defesa que acaba longe da torre."""
    c, found = s.campaign, war_of(s)
    if c is None or found is None:
        return
    war, _ = found
    _to_all(s.ctx, war, S_MOVE, pb.PosMoveMsg(mapId=gw.WAR_MAP, armyId=s.player_id, routes=msg.routes), but=s)
    camp = war.defending(s.player_id)
    node = c.node(camp) if camp else None
    if node is not None and max(abs(c.pos[0] - node["resetX"]), abs(c.pos[1] - node["resetY"])) > RANGE:
        war.stop_defending(s.player_id)
        _alert(s, TOO_FAR)
        _to_all(s.ctx, war, S_STATE, _state(s.player_id, gw.ALIVE))


def player_fight(s: GameSession, target: int) -> None:
    """8548 (cliente ``checkGvgArmy``: exército perto no mapa; ``param1`` = userId). (visto 26/10 #2924-#3348): 14
    pedidos contra a própria guilda (a adversária não entrou) e nenhuma resposta, então mesmo lado é ignorado.
    TODO(inventado): contra o inimigo não há luta na captura; vence o de maior ``fightingCapacity`` (empate: quem
    ataca) e o perdedor morre como na torre: 4175 state 1, 4104 e 131 no acampamento (a sequência de #3334-#3336)."""
    found, other = war_of(s), s.ctx.online.get(target)
    if found is None or other is None or other.campaign is None or not other.campaign.gvg:
        return
    war, me = found
    if _side_of(s.ctx, war, target) in (0, me.side) or war.settled or not war.gates_open:
        return
    if {s.player_id, target} & war.dead or s.battle is not None or other.battle is not None:
        return
    power = {o: o.snapshot.character.fighting_capacity if o.snapshot else 0 for o in (s, other)}
    loser = other if power[s] >= power[other] else s
    _kill(loser, war)


def _kill(o: GameSession, war: gw.War) -> None:
    c = o.campaign
    assert c is not None and c.content is not None
    side = _side_of(o.ctx, war, o.player_id)
    war.stop_defending(o.player_id)
    war.dead.add(o.player_id)
    x, y = c.content["starts"][str(side)]
    c.pos = (int(x), int(y))
    _to_all(o.ctx, war, S_STATE, _state(o.player_id, gw.DEAD))
    _to_all(o.ctx, war, S_ARMY_MOVED, pb.ArmyPosUpdatedMsg(armyId=o.player_id, curPosX=c.pos[0], curPosY=c.pos[1]))
    _to_all(o.ctx, war, S_ARMY_UPDATE, pb.ArmyArmyMsg(armyId=o.player_id, playerId=o.player_id, curPosX=c.pos[0],
                                                      curPosY=c.pos[1], state=0))  # fmt: skip


def _attack(s: GameSession, war: gw.War, me: gw.Side, camp: int) -> None:
    """A luta na Ward Tower inimiga: a vida dela é a da guerra (``SharedHp``), cada golpe passa pelo fator das
    Mystery Towers e vira ferida e placar."""
    c, snap = s.campaign, s.snapshot
    assert c is not None and c.content is not None and snap is not None
    spec = copy.deepcopy(c.content["battles"][TOWER_BATTLE])
    enemy = war.enemy(me)
    tower = spec["heroes"][0]
    tower["hp"] = tower["initHp"] = enemy.hp
    w = _wound(s, war)
    pid = s.player_id
    link = SharedHp(tower["livingId"], lambda: enemy.hp, lambda v: war.hit(me, pid, w.nickname, w.job, v))
    war.stop_defending(pid)
    if war.rage(me, pid):  # Inspiration (4440 objectData 80)
        rage = next((r["objectData"] for r in c.content["buffers"] if r["templateId"] == gw.INSPIRATION), 0)
        s.hero_sp = max(s.hero_sp, int(rage))
    c.fighting = camp
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))

    async def finished(battle: Battle, won: bool) -> None:
        await _over(s, battle, won)

    s.battle = Battle(spec, player_hero(s, spec, boosted(s)), s.ctx.templates, s.ctx.clock, s.send, finished,
                      shared=link, settings=s.ctx.world.settings)  # fmt: skip
    s.log.info("guerra de guildas: luta na torre", vida=enemy.hp, battle=s.battle.id)
    s.battle.start()


async def _over(s: GameSession, battle: Battle, won: bool) -> None:
    """Fim da luta na torre: tropa perdida como nas outras lutas, 435 de Daru, morto até o tique (perdeu) e o
    4382 na volta ao mapa."""
    snap, c, found = s.snapshot, s.campaign, war_of(s)
    assert snap is not None and snap.leader is not None
    s.battle, s.hero_sp = None, battle.player_sp
    rows: list[object] = [snap.leader, snap.character]
    if (hit := outer_city.lose_troops(snap, s.ctx.templates, battle.troops())) is not None:
        outer_city.refill(*hit)
        rows += snap.pawns
    healed = hero_after_fight(s, battle.player.hp if battle.player is not None else None)
    snap.character.strategy += STRATEGY
    await s.ctx.characters.save(*rows)
    if c is None or not c.gvg or found is None:
        return  # saiu no meio da luta
    war, me = found
    c.fighting, c.over = 0, (0, STRATEGY)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    if not won:
        war.dead.add(s.player_id)
        _to_all(s.ctx, war, S_STATE, _state(s.player_id, gw.DEAD))
        x, y = c.content["starts"][str(me.side)]  # type: ignore[index]
        c.pos = (int(x), int(y))  # (dedução) o morto volta ao acampamento (#3030 já está lá)
    report = pb.BattleReportMsg(battleResult=1 if won else 2, strategyBonus=STRATEGY, gpBonus=0, battleScene=SCENE)
    report.failCount, report.goldBonus, report.petGpBonus = 0, 0, 0
    s.send(S_BATTLE_REPORT, report)
    await _push_player(s)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    s.send(S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    hp_pack(s, healed)
    _to_all(s.ctx, war, S_HP, _hp(war, c))
    if war.winner and not war.settled:
        await settle(s.ctx, war)


# ---- relógio, fim e prêmio ------------------------------------------------------------------------


async def _clock(ctx: GameContext, war: gw.War) -> None:
    while not war.settled:
        await asyncio.sleep(1)
        try:
            await step(ctx, war)
        except Exception:  # o relógio não pode morrer no meio da guerra
            log.exception("guerra de guildas: falha no relógio")


async def step(ctx: GameContext, war: gw.War) -> None:
    """Um passo do relógio: a barreira, o 4457 dos 10 s, o tique de 33 s (placar, mortos que voltam), o 4460/4450,
    o aviso dos 20 min e o fim (vantagem, torre caída ou 21:00)."""
    now = ctx.clock.now()
    on = players_on(ctx, war)
    left = (war.gates_at - now).total_seconds()
    if not war.warned and 0 < left <= gw.WARN_LEFT:
        war.warned = True
        _to_all(ctx, war, S_LEFT, pb.GuildMsg(param1=int(left)))
    if not war.gates_open and left <= 0:
        war.gates_open, war.last_tick = True, now
        for o in on:
            for node in o.campaign.nodes.values():  # type: ignore[union-attr]
                if node["masterType"] == gw.GATE:
                    node["state"] = GONE
                    o.send(S_MOVIE, pb.PlayerMovieMsg(movieTargetType=0, targetId=node["nodeId"],
                                                      movieType="DISAPPEARD"))  # fmt: skip
                    o.send(S_NODE, pb.CampaignNodeUpdateMsg(nodeId=node["nodeId"], nodeState=GONE, uuId=_uuid(),
                                                            param1=int(node["param1"]),
                                                            sonType=node["sonType"]))  # fmt: skip
    if war.gates_open and war.last_tick is not None and (now - war.last_tick).total_seconds() >= gw.TICK:
        for pid in war.tick(now):
            _to_all(ctx, war, S_STATE, _state(pid, gw.ALIVE))
        _to_all(ctx, war, S_SCORE, _score(war))
    if not war.late and now - war.opened >= gw.LATE:
        war.late = True
        for o in on:
            _alert(o, LATE_TEXT)
    if on and (war.wounds_at is None or (now - war.wounds_at).total_seconds() >= WOUND_EVERY):
        sent = (tuple((p, w.wound) for p, w in war.wounds.items()), war.red.hp, war.blue.hp)
        if sent != war.wounds_sent:
            war.wounds_sent, war.wounds_at = sent, now
            for o in on:
                o.send(S_WOUND, _wounds(war))
                o.send(S_HP, _hp(war, o.campaign))  # type: ignore[arg-type]
    if now >= war.ends_at:
        war.time_over()
    if war.winner and not war.settled:
        await settle(ctx, war)


async def settle(ctx: GameContext, war: gw.War) -> None:
    """O fim (visto #6249-#6302): 111 a todos, 4439, a saída do mapa e o prêmio; o 4441 passa a mostrar o
    ``result1``. Quem está numa luta sai com ela cancelada (como a saída do mapa)."""
    war.settled = True
    win, lose = war.side(war.winner), war.enemy(war.side(war.winner))
    lead = gw.WIN_LEAD if win.score - lose.score >= gw.WIN_LEAD else win.score - lose.score
    text = WIN_TEXT.format(win=win.name, lead=lead, lose=lose.name)
    for o in players_on(ctx, war):
        _alert(o, text)
        o.send(S_SCORE, _score(war))
        side = _side_of(ctx, war, o.player_id)
        leave_war(o)
        await _prize(o, side == war.winner)
    log.info("guerra de guildas: fim", vencedora=win.guild_id, placar=(win.score, lose.score))


async def _prize(o: GameSession, won: bool) -> None:
    """(visto #6273-#6302) 4471 (a honra do dia), 3, 115 e o 111 "Received ..." a quem está no mapa no fim."""
    snap = o.snapshot
    assert snap is not None
    cut = 1 if won else 2  # TODO(inventado): a perdedora leva a metade
    honor, offer = PRIZE_HONOR // cut, PRIZE_OFFER // cut
    drops = [(t, n // cut) for t, n in PRIZE_ITEMS]
    ch = snap.character
    ch.geste += honor
    ch.consortia_offer += offer
    ch.consortia_total_offer += offer
    new: list[Item] = []
    if rewards.can_grant(snap, o.ctx.templates, drops, o.ctx.clock.now()):
        new, _ = rewards.grant(snap, o.ctx.templates, drops)
    await o.ctx.characters.save(ch, *new)
    o.send(S_HONOR_DAY, pb.SimplePropertyMsg(param1=honor, param2=int(o.ctx.world.settings.get("honor_day_max", 0))))
    await _push_player(o)
    if new:
        o.send(S_ITEMS, rewards.items_msg(new, o.player_id))
    names = ", ".join(f"{_name(o, t)} x{n}" for t, n in drops)
    _alert(o, f"Received {honor} Honor, {names}, and {offer} Contribution.")


def _name(o: GameSession, template_id: int) -> str:
    row = o.ctx.templates.get("ItemTempInfos", template_id) or {}
    return str(row.get("TemplateName", template_id))


def result(ctx: GameContext, guild_id: int) -> int:
    """``result1`` do 4441 (visto #6451): 1 para a vencedora da guerra de hoje já acabada."""
    war = ctx.guilds.wars.get(guild_id)
    me = war.of(guild_id) if war is not None and war.settled else None
    return 1 if me is not None and war.winner == me.side else 0  # type: ignore[union-attr]
