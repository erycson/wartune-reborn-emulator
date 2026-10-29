"""Campo de batalha (Ancient Battleground, 4005 e 4007) e Amethyst Mine (30000).

Entrada (8332) pela janela do template (``OpenTime``/``StopTime``) e nível, 4248 com o estado de cada campo, nós de
entrega e coleta (5125/5032/5033), lista de pedidos (8337), restaurar vida (8338), o fim com o prêmio (no relógio
20008, ``clock``), a mina com o carrinho (8633) e o PvP entre jogadores do campo (8334, 157 battleType 32; todos
estão neste servidor, então ``defenceServerName`` é o nosso). Regras e números em ``game/battlefield.py``.

Missões: 44 na entrada, 45 (abates) a cada vitória no PvP e 50 (vitória no campo) no fim da partida.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import battlefield as bf
from .. import buffs, rewards, rules, space, titles, worldboss
from ..builders import login as b
from ..campaign import CampaignMap
from ..router import router
from ..session import GameContext, GameSession
from .army import count_quest
from .campaign import ARMY_IDLE, map_sync, pvp_fight
from .login import army
from .player import _player
from .stars import sns_msg

S_WARFIELD_STATE, S_WAR_ORDER, S_WAR_INFO, S_WAR_REPORT = 4248, 4255, 4252, 4254
S_PLAYER_STATE, S_MINE, S_ROOM_CREATED, S_ROOM_ENTER, S_NODES = 4175, 4548, 125, 21, 127
S_MAP, S_FULL_ARMY, S_MOVE, S_EXIT, S_QUESTS, S_ITEMS = 140, 150, 4185, 22, 112, 115
S_CONFIRM, S_MOVIE, S_CHAT, S_ALERT, S_COUNT = 29, 143, 83, 111, 4493
S_WAR_MOVIE = 4269  # WarMovieMsg (U_C_WARMOVIE)
S_CROSS, S_ARMY_POS, S_SNS, S_REPORT = 4494, 4104, 4388, 4103  # CrossArmyListMsg, ArmyPosUpdatedMsg, SnsRspMsg
PVP_TYPE, PVP_SCENE, SNS_PVP = 32, 11, 4  # 157 do 8334 (visto #9662, #11103); 4388 type 4 na vitória (#11111)
KILL_QUEST, WIN_QUEST = 45, 50  # "Battleground Kills" (missão 767 sobe no #11106) e "Obtain Victory in War Camp"
RESPAWN, RESPAWN_MS = (179, 75), 25000  # (visto #11098, #11101): o perdedor volta para lá, 25 s morto
LOSS_PCT, WIN_HONOR = 15, 10  # (visto #9828 "You lost: 15 Points." com 100; #11130 "... and 10 Honor.")
WIN_TEXT, LOSE_TEXT = "You received: {} Points and {} Honor.", "You lost: {} Points."
IN_BATTLE = "Player is now in battle!"  # (visto #10962)
DUMP_AMETHYST = 200  # (visto #2079, #2304) "Minecart dumped; you gained 200 Amethyst."
S_MINE_ACTIVE = 4549  # GuildMsg.param5 (U_C_MINE_ACTIVE_STATE): BaseManager.__mineralHandler -> mineralIsOpen
ROOM_ENTER = 1  # RoomCreatedMsg.createdType
ENTER_QUEST = 44  # "Participate in a Battleground" (QuestCondictionInfos tipo 44, visto nos templates)
FIELD_LEED = 27  # LeedTemp 27 "Enter Battleground" (PassCount 1), pelo título
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
CART_GOT_NORMAL = "You received a Minecart."
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
    """4252: o placar do jogador e dos dois lados (visto #14238, um lado só: o do jogador em ``one``)."""
    mine = field.mark(s.player_id)
    other = bf.ENEMY if mine.team == bf.TEAM else bf.TEAM
    left = max(0, int((stop - s.ctx.clock.now()).total_seconds() * 1000))
    return pb.WarFightInfoMsg(teamId=mine.team, score=mine.score, order=1, geste=mine.honor, hitCount=mine.wins,
                              leftTime=left, oneCount=field.count(mine.team), twoCount=field.count(other),
                              oneScore=field.score(mine.team), twoScore=field.score(other))  # fmt: skip


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
                                    teamId=mark.team, geste=mark.honor, serverName=serverName, itemCount=0,
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
    await _quest(s, ENTER_QUEST)
    from .events import leed_done  # events importa login, que importa este pacote

    await leed_done(s, FIELD_LEED)


async def _quest(s: GameSession, kind: int) -> None:
    """+1 nas missões de condição ``kind`` (``Para1`` 0) e o 112 se alguma subiu."""
    await count_quest(s, kind)


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


def _cross(*rows: tuple[GameSession, tuple[int, int], int]) -> pb.CrossArmyListMsg:
    """4494: posição (grade) e estado de cada exército (2 = lutando, 0 = livre)."""
    msg = pb.CrossArmyListMsg()
    for o, (x, y), state in rows:
        name = o.snapshot.server.name if o.snapshot else ""
        msg.armyList.add(armyId=o.player_id, playerId=o.player_id, curPosX=x, curPosY=y, state=state, serverName=name)
    return msg


def _to_map(ctx: GameContext, campaign_id: int, code: int, msg: Any) -> None:
    for o in players_on(ctx, campaign_id):
        o.send(code, msg)


@router.on(8334)
async def war_attack(s: GameSession, msg: pb.WarFieldAttackMsg) -> None:
    """Atacar outro jogador no campo (``userId``; ``defenceServerName`` é sempre o nosso): luta PvP (157
    battleType 32) contra a cópia do alvo, como o coliseu. (visto) 152321 #9660-#9662 e #10957-#10962: 4494 com os
    dois em state 2 e o 157; alvo já lutando: 111 "Player is now in battle!"."""
    c, snap = s.campaign, s.snapshot
    found = _field(s)
    target = s.ctx.online.get(msg.userId)
    if (found is None or c is None or snap is None or s.battle is not None or target is None or target is s
            or target.campaign is None or target.campaign.warfield != c.warfield
            or target.snapshot is None):  # fmt: skip
        s.log.info("8334 recusado", pedido=str(msg))
        return
    field = found[0]
    me, them = field.mark(s.player_id), field.mark(target.player_id)
    if me.fighting or them.fighting or target.battle is not None:
        s.send(S_ALERT, _chat(IN_BATTLE, 7))
        return
    me.fighting = them.fighting = True
    cid = c.warfield
    _to_map(s.ctx, cid, S_CROSS, _cross((s, c.pos, 2), (target, target.campaign.pos, 2)))

    async def finished(won: bool) -> None:
        await pvp_over(s, target, field, won)

    pvp_fight(s, target.snapshot, PVP_TYPE, PVP_SCENE, finished)


async def pvp_over(s: GameSession, target: GameSession, field: bf.Field, won: bool) -> None:
    """Fim da luta do campo: o perdedor perde 15% dos pontos e renasce em 179,75 (4104 e 4175 state 1 por 25 s);
    o vencedor ganha os mesmos pontos e 10 de honra. Ordem (visto) 152321 #11098-#11131: 4104, 4175, 4252, 4494,
    4388 tipo 4, 4269, 111 e 83; o perdedor: 4269 (isAdd false), 111 e 83 (#9828-#9830).
    TODO(inventado): 15% arredondado para cima (visto 100 -> 15, 115 -> 18); o ganho igual à perda (visto 21 e 23
    sem a pontuação do outro) e o 4388 ``data`` = vitórias no campo (visto "1" na primeira)."""
    winner, loser = (s, target) if won else (target, s)
    wm, lm = field.mark(winner.player_id), field.mark(loser.player_id)
    wm.fighting = lm.fighting = False
    if field.settled:  # a partida acabou durante a luta: só o fim da luta
        s.send(S_REPORT, pb.BattleReportMsg(battleResult=1 if won else 2, battleScene=PVP_SCENE))
        return
    cid = field.campaign_id
    lost = -(-lm.score * LOSS_PCT // 100)
    lm.score -= lost
    wm.score, wm.honor, wm.wins = wm.score + lost, wm.honor + WIN_HONOR, wm.wins + 1
    here = [o for o in (winner, loser) if o.campaign is not None and o.campaign.warfield == cid]
    if loser in here:
        loser.campaign.pos = RESPAWN  # type: ignore[union-attr]
        name = loser.snapshot.server.name if loser.snapshot else ""
        _to_map(s.ctx, cid, S_ARMY_POS, pb.ArmyPosUpdatedMsg(armyId=loser.player_id, curPosX=RESPAWN[0],
                                                             curPosY=RESPAWN[1], serverName=name))  # fmt: skip
        state = pb.PlayerStateListMsg()
        state.playerState.add(armyId=loser.player_id, state=1, leftTime=RESPAWN_MS, serverName=name)
        _to_map(s.ctx, cid, S_PLAYER_STATE, state)
    stop = bf.row_window(bf.field_row(s.ctx.templates, cid), s.ctx.clock.now())[1]  # type: ignore[arg-type]
    for o in here:
        o.send(S_WAR_INFO, _info(o, field, stop))
    rows = [(o, o.campaign.pos, 0) for o in here]  # type: ignore[union-attr]
    _to_map(s.ctx, cid, S_CROSS, _cross(*rows))
    s.send(S_REPORT, pb.BattleReportMsg(battleResult=1 if won else 2, battleScene=PVP_SCENE))  # (visto) #11103
    await _quest(winner, KILL_QUEST)  # (visto #11106): 112 da 767 depois do 4103
    if winner.snapshot is not None:  # títulos "Executioner"/"Grim Reaper" (Accumulated N Battleground kills)
        await s.ctx.characters.save(titles.count(winner.snapshot, titles.FIELD_KILLS, s.ctx.clock.now()))
    winner.send(S_SNS, sns_msg(winner.player_id, SNS_PVP, str(wm.wins)))
    for o, add, honor, text in ((winner, True, WIN_HONOR, WIN_TEXT.format(lost, WIN_HONOR)),
                                (loser, False, 0, LOSE_TEXT.format(lost))):  # fmt: skip
        name = o.snapshot.server.name if o.snapshot else ""
        o.send(S_WAR_MOVIE, pb.WarMovieMsg(score=lost, geste=honor, isAdd=add, userId=o.player_id, serverName=name))
        o.send(S_ALERT, _chat(text, 7))
        o.send(S_CHAT, _chat(text, 3))


@router.on(8338)
async def restore_hp(s: GameSession, _: object) -> None:
    """Restaurar vida no campo (``PvpMapRightView`` "reset", ``warMaxhp``): o herói ferido (a luta do campo gasta a
    vida como as outras, ``pvp_fight``) volta cheio pela reserva das poções (``rules.heal_hero``), 113 e 150; cheio,
    o aviso (visto #15796). TODO(inventado): a cura pela reserva (só o aviso de vida cheia foi visto)."""
    snap = s.snapshot
    if s.campaign is None or not s.campaign.is_warfield or snap is None or snap.leader is None:
        return
    now = s.ctx.clock.now()
    live = rules.leader_stats(snap, s.ctx.templates, now).live
    healed = rules.heal_hero(snap, s.ctx.templates, now) if b.hero_hp(snap.leader, live) < live else 0
    if not healed:
        s.send(S_ALERT, _chat(FULL_HP, channel=7))
        return
    await s.ctx.characters.save(snap.leader)
    from .shop import send_blood  # shop importa campaign, que importa este módulo

    send_blood(s)
    army(s, snap)


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
    from .events import count_click  # events importa login, que importa este pacote

    await count_click(s, "minefield")  # DayGuideManager "minefield" -> atividade 13 (MaxCount 2)


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
        if n == bf.CART_NODE:  # o texto: fora das 19:30-20:00 o carrinho é o comum (``bf.CART_NORMAL``)
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
        await _quest(s, rules.AMETHYST_CONDITION)  # 503 "Mine Amethyst"; TODO(inventado): a posição do 112
        left = bf.PICKS_PER_CART - cart.picks
        if left > 0:
            s.send(S_ALERT, _chat(f"Collection complete. ({left} / {bf.PICKS_PER_CART}) collections remaining.", 7))
        else:  # carrinho cheio: descarrega e o Amethyst entra no ``playerInfo.mineral`` (rewards.AMETHYST)
            # TODO(visto): o texto veio com 200 (#2079, #2304) e com 100 (#2234); aqui vai sempre 200
            s.ctx.warfields.carts.pop(s.player_id, None)
            snap = s.snapshot
            assert snap is not None
            await s.ctx.characters.save(rewards.add_amethyst(snap, DUMP_AMETHYST, s.ctx.clock.now()))
            _player(s)
            s.send(S_CHAT, _chat(f"Minecart dumped; you gained {DUMP_AMETHYST} Amethyst.", 3))
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
        if camp - bf.MINE * 100 == bf.CART_NODE:
            if s.player_id in s.ctx.warfields.carts:
                s.send(S_ALERT, _chat(CART_HAS, 7))
                return
            adv = bf.mine_open(s.ctx.clock.now())
            s.ctx.warfields.carts[s.player_id] = bf.Cart(quality=bf.CARTS_ADV if adv else bf.CART_NORMAL)
            # TODO(inventado): o texto do carrinho comum (só o avançado foi visto, #1955)
            s.send(S_ALERT, _chat(CART_GOT if adv else CART_GOT_NORMAL, 7))
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
    """Fim da partida: o texto, o prêmio a quem estava no campo, o placar e a saída (22). Vence o lado com mais
    pontos (``Field.winner``): Insignia x80 e a missão 50 (visto #16396); o outro lado leva a metade."""
    field.settled = True
    now = ctx.clock.now()
    winner = field.winner()
    for o in players_on(ctx, field.campaign_id):
        snap = o.snapshot
        assert snap is not None
        o.send(S_CHAT, _chat(END_TEXT, tip=True))  # ordem da captura (visto #16358-#16364): texto, 4254, 22
        team = field.mark(o.player_id).team
        other = bf.ENEMY if team == bf.TEAM else bf.TEAM
        report = pb.WarReportListMsg(oneTeamId=team, twoTeamId=other, oneScore=field.score(team),
                                     twoScore=field.score(other))  # fmt: skip
        report.info.extend(_ranking(field, snap.server.name, snap.character.nickname or "", o.player_id))
        o.send(S_WAR_REPORT, report)
        o.campaign = None
        o.send(S_EXIT, pb.CampaignExitMsg(result=1, playerId=o.player_id, armyId=o.player_id,
                                          serverName=snap.server.name))  # fmt: skip
        won = team == winner
        # TODO(inventado): o lado perdedor (e o empate) leva a metade; só a vitória foi vista (#16396)
        insignia = bf.WIN_INSIGNIA if won else bf.WIN_INSIGNIA // 2
        drops = [(bf.INSIGNIA, insignia)]
        new: list[Item] = []
        if rewards.can_grant(snap, ctx.templates, drops, now):
            new, _ = rewards.grant(snap, ctx.templates, drops)
        # a honra do texto vai para o geste (a honra do jogador: Honor Certificate, NeedGeste da loja de honra)
        honor = bf.WIN_HONOR * insignia // bf.WIN_INSIGNIA  # Double Honor Scroll: "Honor Received +{Grades}%"
        snap.character.geste += honor * (100 + buffs.percent(snap, ctx.templates, buffs.HONOR_BOOST, now)) // 100
        await ctx.characters.save(snap.character, *new)
        if new:
            o.send(S_ITEMS, rewards.items_msg(new, o.player_id))
        _player(o)
        o.send(S_CHAT, _chat(bf.win_text(insignia)))  # o prêmio chega depois da saída (visto #16396)
        if won:  # "Obtain Victory in War Camp" (missão 818); TODO(inventado): a posição do 112
            await _quest(o, WIN_QUEST)
    for o in ctx.online.sessions():
        push_states(o)
