"""Campo de batalha (Ancient Battleground, 4005 e 4007) e Amethyst Mine (30000).

Entrada (8332) pela janela do template (``OpenTime``/``StopTime``) e nível, 4248 com o estado de cada campo, nós de
entrega e coleta (5125/5032/5033), lista de pedidos (8337), restaurar vida (8338), o fim com o prêmio (no relógio
20008, ``clock``) e a mina com o carrinho (8633). Regras e números em ``game/battlefield.py``.

Pendente: PvP dentro do campo (8334 -> 157 battleType 32). O alvo fica em outro servidor e aqui não há como montar a
luta, então o 8334 só registra. As missões tipo 45 (abates) e 50 (vitórias) dependem desse PvP.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import battlefield as bf
from .. import rewards, rules, space, worldboss
from ..builders import login as b
from ..builders.player import quest_update
from ..campaign import CampaignMap
from ..router import router
from ..session import GameContext, GameSession
from .campaign import ARMY_IDLE, map_sync
from .login import army

S_WARFIELD_STATE, S_WAR_ORDER, S_WAR_INFO, S_WAR_REPORT = 4248, 4255, 4252, 4254
S_PLAYER_STATE, S_MINE, S_ROOM_CREATED, S_ROOM_ENTER, S_NODES = 4175, 4548, 125, 21, 127
S_MAP, S_FULL_ARMY, S_MOVE, S_EXIT, S_QUESTS, S_ITEMS = 140, 150, 4185, 22, 112, 115
S_CONFIRM, S_MOVIE, S_CHAT, S_ALERT, S_COUNT = 29, 143, 83, 111, 4493
S_WAR_MOVIE = 4269  # WarMovieMsg (U_C_WARMOVIE)
S_MINE_ACTIVE = 4549  # GuildMsg.param5 (U_C_MINE_ACTIVE_STATE): BaseManager.__mineralHandler -> mineralIsOpen
ROOM_ENTER = 1  # RoomCreatedMsg.createdType
ENTER_QUEST = 44  # "Participate in a Battleground" (QuestCondictionInfos tipo 44, visto nos templates)
END_TEXT = "The battle has ended! You will be teleported out momentarily."
ENTERED_TEXT = "Entered resource transport state. Movement speed is now decreased by 50%."
DELIVER_BODY = "Turn in resources to obtain points and honor. Continue?"
FULL_HP = "You already have full HP, no need to recharge!"
CART_BODY = (
    "Get Minecart| If you want to collect Amethyst, you'll need to bring a minecart! "
    "A higher level minecart will yield "
    "higher level rewards. (Adv. Minecarts are available daily from 19:30-20:00)"
)  # (visto #1962)
CART_GOT, CART_HAS = "You received a Adv. Minecart.", "You already have a cart!"  # (visto #1955, #1966)
SHARD_TEXT = "Battleground Treasure Shard"


def _chat(text: str, channel: int = 12, *, tip: bool = False) -> pb.ChatChannelMsg:
    return pb.ChatChannelMsg(channel=channel, encodeMsg=text, otherId=-1, userType=1, isCenterTip=tip, isBigTip=tip)


def _open(ctx: GameContext, campaign_id: int, now: datetime) -> tuple[bf.Field, datetime] | None:
    """A partida de hoje do campo, se a janela está aberta (a partida nasce no primeiro a entrar)."""
    row = bf.field_row(ctx.templates, campaign_id)
    if row is None or not bf.is_open(row, now):
        return None
    opened, stop = bf.row_window(row, now)
    return bf.current_field(ctx.warfields, campaign_id, opened), stop


def _states_tuple(templates: GameTemplates, now: datetime) -> tuple[tuple[int, int], ...]:
    """Os 4001-4011 do 4248. Os campos implementados (4005/4007) seguem a janela; os demais, como antes (sem mapa)."""
    out = []
    for campaign in range(4001, 4012):
        if campaign in bf.FIELDS:
            row = bf.field_row(templates, campaign)
            out.append((campaign, bf.state(row, now) if row is not None else 2))
            continue
        row = templates.get("Campaigns", campaign, key="CampaignId")
        value = worldboss.state(row, now) if row is not None else worldboss.CLOSED
        out.append((campaign, 3 if value == worldboss.OPEN else value))  # na janela sem mapa: 3, não 0
    return tuple(out)


def states(templates: GameTemplates, now: datetime) -> pb.WorldBossStateMsg:
    """Estado de cada campo (``WarFieldInfo``): 0 aberto (o único que mostra o botão), 1 não abriu, 2 encerrado."""
    msg = pb.WorldBossStateMsg()
    for campaign, value in _states_tuple(templates, now):
        msg.worldBossInfo.add(campaignId=campaign, state=value)
    return msg


def login(s: GameSession) -> None:
    now = s.ctx.clock.now()
    s.war_states = _states_tuple(s.ctx.templates, now)
    s.send(S_WARFIELD_STATE, states(s.ctx.templates, now))
    s.mine_open = bf.mine_open(now)
    if s.mine_open:  # TODO(inventado): login dentro da janela; as capturas só têm a abertura e o fecho
        s.send(S_MINE_ACTIVE, pb.GuildMsg(param5=True))


def push_states(s: GameSession) -> None:
    """No relógio (20008): manda o 4248 de novo quando um campo abre ou fecha, e o 4549 quando a mina abre ou fecha
    ((visto) 231733 #1232 e #4154: true às 19:30, false às 20:00, a todos os online)."""
    if s.war_states is None:
        return  # o cliente ainda não recebeu o login
    now = s.ctx.clock.now()
    if (mine := bf.mine_open(now)) != s.mine_open:
        s.mine_open = mine
        s.send(S_MINE_ACTIVE, pb.GuildMsg(param5=mine))
    if (cur := _states_tuple(s.ctx.templates, now)) != s.war_states:
        s.war_states = cur
        s.send(S_WARFIELD_STATE, states(s.ctx.templates, now))


def players_on(ctx: GameContext, campaign_id: int) -> list[GameSession]:
    return [o for o in ctx.online.sessions()
            if o.campaign is not None and o.campaign.warfield == campaign_id and o.snapshot is not None]  # fmt: skip


def on_map(s: GameSession, campaign_id: int) -> list[GameSession]:
    return [o for o in players_on(s.ctx, campaign_id) if o is not s]


def _field(s: GameSession) -> tuple[bf.Field, datetime] | None:
    """A partida do campo onde o jogador está, se a janela ainda é a dela."""
    c = s.campaign
    if c is None or c.warfield not in bf.FIELDS:
        return None
    return _open(s.ctx, c.warfield, s.ctx.clock.now())


def _info(s: GameSession, field: bf.Field, stop: datetime) -> pb.WarFightInfoMsg:
    """4252: o placar do jogador e do time (visto #14238). O time 1 não tem jogadores aqui (0)."""
    mine = field.mark(s.player_id)
    left = max(0, int((stop - s.ctx.clock.now()).total_seconds() * 1000))
    return pb.WarFightInfoMsg(teamId=bf.TEAM, score=mine.score, order=1, geste=mine.honor, hitCount=0, leftTime=left,
                              oneCount=len(field.marks), twoCount=0, oneScore=field.our_score(),
                              twoScore=0)  # fmt: skip


def _state_msg(player_id: int, state: int) -> pb.PlayerStateListMsg:
    msg = pb.PlayerStateListMsg()
    msg.playerState.add(armyId=player_id, state=state, leftTime=0)
    return msg


def _ranking(field: bf.Field, serverName: str, name_of: str, player_id: int) -> list[pb.WarReportMsg]:
    """As linhas de placar do campo (4255/4254): uma por jogador, do maior ponto para o menor."""
    rows = []
    for order, (pid, mark) in enumerate(sorted(field.marks.items(), key=lambda kv: -kv[1].score), 1):
        name = name_of if pid == player_id else ""
        rows.append(pb.WarReportMsg(order=order, nickName=name, userId=pid, score=mark.score, hitCount=0,
                                    teamId=bf.TEAM, geste=mark.honor, serverName=serverName, itemCount=0,
                                    winGesteCount=0))  # fmt: skip
    return rows


@router.on(8332)
async def enter_field(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Entrar no campo (``param1`` = campanha, visto #14230): 125 (isCross), 140, 21, 127 e 4252; missão 44."""
    ctx, snap = s.ctx, s.snapshot
    assert snap is not None
    now = ctx.clock.now()
    if msg.param1 not in bf.FIELDS or s.battle is not None or s.campaign is not None:
        s.log.info("8332 recusado", campanha=msg.param1)
        return
    found = _open(ctx, msg.param1, now)
    row = bf.field_row(ctx.templates, msg.param1)
    if found is None or row is None:
        s.log.info("8332 com o campo fechado", campanha=msg.param1)
        return
    if not int(row["MinLevel"]) <= snap.character.grades <= int(row["MaxLevel"]):
        s.log.info("8332 fora do nível do campo", nivel=snap.character.grades)
        return
    field, stop = found
    cid = msg.param1
    field.mark(s.player_id)
    space.leave(s)
    s.campaign = CampaignMap(cid, bf.field_nodes(cid), bf.START, warfield=cid)
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER, isCross=True)
    room.room.campaignId = cid
    s.send(S_MAP, map_sync(s, ARMY_IDLE))  # (visto #14232 e #9475): 140 vem antes do 125 no campo
    s.send(S_ROOM_CREATED, room)
    me = space.room_player(snap, ctx.templates, s.campaign.pos, cid, now)
    others = on_map(s, cid)
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, cid, now)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    for other in others:
        other.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    s.send(S_NODES, s.campaign.node_list())
    s.send(S_WAR_INFO, _info(s, field, stop))
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    quests = rules.quest_event(snap, ctx.templates, ENTER_QUEST, 0, 1)
    if quests:
        await ctx.characters.save(*quests)
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(8337)
async def war_order(s: GameSession, _: object) -> None:
    """Classificação do campo de hoje (4255): quem está no campo, com o placar e a honra de cada um."""
    msg = pb.WarReportListMsg()
    snap = s.snapshot
    if snap is not None:
        for cid in bf.FIELDS:
            found = _open(s.ctx, cid, s.ctx.clock.now())
            if found is not None and found[0].marks:
                msg.info.extend(_ranking(found[0], snap.server.name, snap.character.nickname or "", s.player_id))
                break
    s.send(S_WAR_ORDER, msg)


@router.on(8334)
async def war_attack(s: GameSession, msg: pb.WarFieldAttackMsg) -> None:
    """Atacar outro jogador no campo: o alvo vem de outro servidor (``defenceServerName``), sem luta aqui."""
    s.log.info("8334 sem luta: o alvo está em outro servidor", pedido=str(msg))


@router.on(8338)
async def restore_hp(s: GameSession, _: object) -> None:
    """Restaurar vida no campo: a vida do exército não se gasta no campo, então sempre "cheia" (visto #15796).

    TODO(inventado): a vida do campo não é guardada; só a mensagem de vida cheia é respondida.
    """
    if s.campaign is not None and s.campaign.is_warfield:
        s.send(S_ALERT, _chat(FULL_HP, channel=7))


@router.on(8599)
async def entries_left(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Entradas do campo (4493): com o campo aberto, sem entradas (visto #22505 ``paraBool1`` false)."""
    if msg.paraInt1 not in bf.FIELDS or _open(s.ctx, msg.paraInt1, s.ctx.clock.now()) is None:
        return
    s.send(S_COUNT, pb.CampaignReqMsg(paraInt1=msg.paraInt1, paraBool1=False))


@router.on(8633)
async def enter_mine(s: GameSession, _: object) -> None:
    """Entrar na mina (30000): 125, 140, 21, 127 e 4548 com o carrinho (visto #1917-#1923)."""
    ctx, snap = s.ctx, s.snapshot
    assert snap is not None
    if s.battle is not None or s.campaign is not None:
        return
    row = next(ctx.templates.find("Campaigns", CampaignId=bf.MINE), None)
    if row is None or not int(row["MinLevel"]) <= snap.character.grades <= int(row["MaxLevel"]):
        s.log.info("8633 fora do nível da mina", nivel=snap.character.grades)
        return
    now = ctx.clock.now()
    space.leave(s)
    s.campaign = CampaignMap(bf.MINE, bf.mine_nodes(), bf.START, warfield=bf.MINE)  # TODO(inventado): entrada da mina
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER)
    room.room.campaignId = bf.MINE
    s.send(S_ROOM_CREATED, room)
    s.send(S_MAP, map_sync(s, ARMY_IDLE))
    me = space.room_player(snap, ctx.templates, s.campaign.pos, bf.MINE, now)
    others = on_map(s, bf.MINE)
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, bf.MINE, now)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    s.send(S_NODES, s.campaign.node_list())
    s.send(S_MINE, _mine_msg(s))
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))


def _mine_msg(s: GameSession) -> pb.TramcarInfoMsg:
    """4548: o carrinho do jogador (``carInfo``); sem carrinho, tudo zero."""
    cart = s.ctx.warfields.carts.get(s.player_id)
    car = pb.CarInfo(userId=s.player_id, armyId=s.player_id, minerals=0, quality=0, tramcarCount=0, handCount=0,
                     isOwn=0, pickCount=0)  # fmt: skip
    if cart is not None:
        car.quality, car.tramcarCount, car.isOwn, car.pickCount = cart.quality, 1, 1, cart.picks
        car.minerals = cart.picks * 20  # (visto #2136): 20 por coleta
    msg = pb.TramcarInfoMsg(activeTime=0, count=0, multiple=2)
    msg.carInfo.add().CopyFrom(car)
    return msg  # TODO(inventado): activeTime e count


async def arrive(s: GameSession, camp: int, node: dict[str, Any]) -> None:
    """5125 num nó do campo ou da mina: a entrega abre o 29 e a coleta manda o filme (o 5032 faz a coleta)."""
    c = s.campaign
    assert c is not None
    if c.warfield == bf.MINE:
        n = camp - bf.MINE * 100
        if n == bf.CART_NODE and bf.mine_open(s.ctx.clock.now()):
            s.send(S_CONFIRM, pb.CampaignConfirmMsg(title="", body=CART_BODY, mapId=bf.MINE, nodeId=camp, type=2))
        elif n == bf.PICK_NODE and s.player_id in s.ctx.warfields.carts:
            s.send(S_MOVIE, pb.PlayerMovieMsg(movieTargetType=0, targetId=int(node["nodeId"]),
                                              movieType="COLLECTION", delay=0))  # fmt: skip
        return
    found = _field(s)
    if found is None:
        return
    field = found[0]
    n = camp - c.warfield * 1000
    mark = field.mark(s.player_id)
    if n == bf.DELIVER and mark.carry is not None:
        s.send(S_CONFIRM, pb.CampaignConfirmMsg(title="", body=DELIVER_BODY, mapId=c.warfield, nodeId=camp, type=2))
    elif n in bf.COLLECT and mark.carry is None:
        s.send(S_MOVIE, pb.PlayerMovieMsg(movieTargetType=0, targetId=int(node["nodeId"]), movieType="COLLECTION",
                                          delay=0))  # fmt: skip


async def callback(s: GameSession, msg: pb.CallBackReqMsg) -> None:
    """5032 (``cmd`` 2 = coleta) num nó do campo ou da mina: o minério vai para o jogador ou para o carrinho."""
    c = s.campaign
    assert c is not None
    if msg.cmd != 2:
        return
    camp = msg.nodeId
    if c.warfield == bf.MINE:
        n = camp - bf.MINE * 100
        cart = s.ctx.warfields.carts.get(s.player_id)
        if n != bf.PICK_NODE or cart is None:
            return
        cart.picks += 1
        s.send(S_MINE, _mine_msg(s))
        left = bf.PICKS_PER_CART - cart.picks
        if left > 0:
            s.send(S_ALERT, _chat(f"Collection complete. ({left} / {bf.PICKS_PER_CART}) collections remaining.", 7))
        else:  # carrinho cheio: descarrega; o Amethyst não é creditado (não há moeda para ele; TODO)
            # TODO(visto): o texto veio com 200 (#2079, #2304) e com 100 (#2234); aqui vai sempre 200
            s.ctx.warfields.carts.pop(s.player_id, None)
            s.send(S_CHAT, _chat("Minecart dumped; you gained 200 Amethyst.", 3))
            s.send(S_MINE, _mine_msg(s))
        return
    found = _field(s)
    if found is None:
        return
    mark = found[0].mark(s.player_id)
    n = camp - c.warfield * 1000
    if n not in bf.COLLECT or mark.carry is not None:
        return
    mark.carry = bf.COLLECT[n]
    s.send(S_PLAYER_STATE, _state_msg(s.player_id, 2))
    s.send(S_ALERT, _chat(ENTERED_TEXT, 7))


async def confirm(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """5033 com ``paraBool1`` (sim): entrega no campo (pontos, honra e shards) ou o carrinho da mina."""
    c, snap = s.campaign, s.snapshot
    assert c is not None and snap is not None
    if not msg.paraBool1:
        return
    camp = msg.paraInt2
    if c.warfield == bf.MINE:
        if camp - bf.MINE * 100 == bf.CART_NODE and bf.mine_open(s.ctx.clock.now()):
            if s.player_id in s.ctx.warfields.carts:
                s.send(S_ALERT, _chat(CART_HAS, 7))
                return
            s.ctx.warfields.carts[s.player_id] = bf.Cart()
            s.send(S_ALERT, _chat(CART_GOT, 7))
            s.send(S_MINE, _mine_msg(s))
        return
    found = _field(s)
    if found is None or camp - c.warfield * 1000 != bf.DELIVER:
        return
    field, stop = found
    mark = field.mark(s.player_id)
    if mark.carry is None:
        return
    quality = mark.carry
    pts, honor, shards = bf.TURN_IN[quality]
    mark.score, mark.honor, mark.carry = mark.score + pts, mark.honor + honor, None
    drops = [(bf.SHARD, shards)]
    new: list[Item] = []
    if rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        new, _ = rewards.grant(snap, s.ctx.templates, drops)
    # ordem da captura (visto #14391-#14418): 4175, 4252, 115, 111, 83
    s.send(S_PLAYER_STATE, _state_msg(s.player_id, 0))
    s.send(S_WAR_INFO, _info(s, field, stop))
    await s.ctx.characters.save(snap.character, *new)
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    text = bf.turn_in_text(quality, pts, honor, shards)
    s.send(S_ALERT, _chat(text, 7))
    s.send(S_CHAT, _chat(text, 3))
    # (visto) 152321 #14713-#14717: 111, 83, 4252 e o 4269 (ScoreOrGesteAction: o número subindo no mapa)
    s.send(S_WAR_MOVIE, pb.WarMovieMsg(score=pts, geste=honor, isAdd=True, userId=s.player_id,
                                       serverName=snap.server.name))  # fmt: skip


def leave_field(s: GameSession) -> bool:
    """Sai do campo ou da mina (5025 ou desconexão): 22 para os outros no mapa e para o próprio."""
    c, snap = s.campaign, s.snapshot
    if c is None or not c.is_warfield or snap is None:
        return False
    if s.battle is not None:
        s.battle.cancel()
        s.battle = None
    msg = pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id, serverName=snap.server.name)
    for other in on_map(s, c.warfield):
        other.send(S_EXIT, msg)
    s.campaign = None
    s.send(S_EXIT, msg)
    return True


def broadcast_move(s: GameSession, msg: pb.PosMoveMsg) -> None:
    """4185 a quem está no mesmo mapa: o caminho do jogador, com o nome do nosso servidor (``serverName``)."""
    c, snap = s.campaign, s.snapshot
    assert c is not None and snap is not None
    move = pb.PosMoveMsg(mapId=c.warfield, armyId=s.player_id, routes=msg.routes, serverName=snap.server.name)
    for other in on_map(s, c.warfield):
        other.send(S_MOVE, move)


async def clock(s: GameSession) -> None:
    """No relógio (20008): fecha as partidas cujo ``StopTime`` já passou (uma vez por partida)."""
    ctx, now = s.ctx, s.ctx.clock.now()
    for cid in bf.FIELDS:
        row = bf.field_row(ctx.templates, cid)
        if row is None:
            continue
        opened, stop = bf.row_window(row, now)
        field = ctx.warfields.fields.get(cid)
        if field is not None and field.opened == opened and now >= stop and not field.settled:
            await settle(ctx, field)


async def settle(ctx: GameContext, field: bf.Field) -> None:
    """Fim da partida: o texto, o prêmio (Insignia x80) a quem estava no campo, o placar e a saída (22)."""
    field.settled = True
    now = ctx.clock.now()
    for o in players_on(ctx, field.campaign_id):
        snap = o.snapshot
        assert snap is not None
        o.send(S_CHAT, _chat(END_TEXT, tip=True))  # ordem da captura (visto #16358-#16364): texto, 4254, 22
        report = pb.WarReportListMsg(oneTeamId=bf.TEAM, twoTeamId=bf.ENEMY, oneScore=field.our_score(), twoScore=0)
        report.info.extend(_ranking(field, snap.server.name, snap.character.nickname or "", o.player_id))
        o.send(S_WAR_REPORT, report)
        o.campaign = None
        o.send(S_EXIT, pb.CampaignExitMsg(result=1, playerId=o.player_id, armyId=o.player_id,
                                          serverName=snap.server.name))  # fmt: skip
        # TODO(inventado): a regra de vencedor; sem outro time aqui, a nossa equipe vence (visto a vitória #16396)
        drops = [(bf.INSIGNIA, bf.WIN_INSIGNIA)]
        new: list[Item] = []
        if rewards.can_grant(snap, ctx.templates, drops, now):
            new, _ = rewards.grant(snap, ctx.templates, drops)
        await ctx.characters.save(snap.character, *new)
        if new:
            o.send(S_ITEMS, rewards.items_msg(new, o.player_id))
        o.send(S_CHAT, _chat(bf.win_text()))  # o prêmio chega depois da saída (visto #16396)
    for o in ctx.online.sessions():
        push_states(o)
