"""Campo de batalha (Ancient Battleground, 4005 e 4007) e Amethyst Mine (30000).

Entrada (8332) pela janela do template (``OpenTime``/``StopTime``) e nível, 4248 com o estado de cada campo, nós de
entrega e coleta (5125/5032/5033), lista de pedidos (8337), restaurar vida (8338), o fim com o prêmio (no relógio
20008, ``clock``), a mina com o carrinho (8633) e o PvP entre jogadores do campo (8334, 157 battleType 32; todos
estão neste servidor, então ``defenceServerName`` é o nosso). Regras e números em ``game/battlefield.py``.

Missões: 44 na entrada, 45 (abates) a cada vitória no PvP e 50 (vitória no campo) no fim da partida.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

from ...domain import gameday
from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import arena_grupo, buffs, rewards, rules, space, taxas, titles, worldboss
from .. import battlefield as bf
from .. import events as ev
from ..battle import Battle
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
S_WAR_MOVIE, S_HONOR = 4269, 4471  # WarMovieMsg (U_C_WARMOVIE), SimplePropertyMsg (U_C_DAYGESTE_SEND)
S_CROSS, S_ARMY_POS, S_SNS, S_REPORT = 4494, 4104, 4388, 4103  # CrossArmyListMsg, ArmyPosUpdatedMsg, SnsRspMsg
PVP_TYPE, PVP_SCENE, SNS_PVP = 32, 11, 4  # 157 do 8334 (visto #9662, #11103); 4388 type 4 na vitória (#11111)
KILL_QUEST, WIN_QUEST = 45, 50  # "Battleground Kills" (missão 767 sobe no #11106) e "Obtain Victory in War Camp"
# o perdedor volta ao acampamento do lado (``bf.CAMP``) e espera a onda de renascer (``bf.respawn_ms``: vistos 0, 5,
# 10, 20, 25 e 30 s, #10534, #9655, #9969, 121453 #9015, #9797, #9775); morto carregando minério é o state 3 e o
# minério fica (visto #10273 state 3, #10384 state 2, entrega #10406)
DEAD, DEAD_CARRYING = 1, 3
CROSS_POINTS = 10  # (visto #11130) ", Cross-server PvP points +10" (pvpHeroHelperFrame: abates no campo dão pontos)
WIN_TEXT = "You received: {} Points and {} Honor., Cross-server PvP points +{}"
LOSE_TEXT = "You lost: {} Points."
ATTACKED_TEXT = "{} is attacking you!"  # (visto #10207 no 111 e #10209 no 83 com o link do atacante)
DEAD_GATE = "You cannot leave camp when dead!"  # (visto #9840)
ENEMY_BASE = "Unable to enter the enemy faction's base."  # (visto 20261101 #6130)
IN_BATTLE = "Player is now in battle!"  # (visto #10962)
DOUBLE_TIME = "It’s Amethyst Double Time! All Amethyst collected is doubled."  # (visto 191924 #14218, #760, #23583)
HONOR_DAY = "honor_day"  # event_state diário: a honra do dia do 4471 (visto #10104 3, #10410 6 ... #11674 123)
DUMP_AMETHYST = 200  # (visto #2079, #2304) "Minecart dumped; you gained 200 Amethyst."
S_MINE_ACTIVE = 4549  # GuildMsg.param5 (U_C_MINE_ACTIVE_STATE): BaseManager.__mineralHandler -> mineralIsOpen
ROOM_ENTER = 1  # RoomCreatedMsg.createdType
ENTER_QUEST = 44  # "Participate in a Battleground" (QuestCondictionInfos tipo 44, visto nos templates)
FIELD_LEED = 27  # LeedTemp 27 "Enter Battleground" (PassCount 1), pelo título
END_TEXT = "The battle has ended! You will be teleported out momentarily."
ENTERED_TEXT = "Entered resource transport state. Movement speed is now decreased by 50%."
DELIVER_BODY = "Turn in resources to obtain points and honor. Continue?"
FULL_HP = "You already have full HP, no need to recharge!"
RESET_STARS, NO_STARS = 200, "Inadequate Star Points"  # idioma PvpMapRightView.reset / StarIconView.command01
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


def honor_day(snap: Any, now: datetime) -> int:
    """A honra ganha hoje (o ``param1`` do 4471)."""
    st = ev.peek(snap, HONOR_DAY)
    return st.value if st is not None and gameday.same_day(st.updated_at, now) else 0


def honor_day_msg(s: GameSession) -> pb.SimplePropertyMsg:
    assert s.snapshot is not None
    top = int(s.ctx.world.settings.get("honor_day_max", 0))
    return pb.SimplePropertyMsg(param1=honor_day(s.snapshot, s.ctx.clock.now()), param2=top)


def add_honor(s: GameSession, honor: int) -> list[Any]:
    """Honra na hora (o geste do personagem e a do dia): 4471 e 3, como na entrega e no abate (visto #10104-#10105,
    #11104-#11105). Devolve o que gravar."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    snap.character.geste += honor
    day = ev.daily(snap, HONOR_DAY, now)
    day.value, day.updated_at = day.value + honor, now
    s.send(S_HONOR, honor_day_msg(s))
    _player(s)
    return [snap.character, day]


def push_states(s: GameSession) -> None:
    """No relógio (20008): manda o 4248 de novo quando um campo abre ou fecha, e o 4549 quando a mina abre ou fecha
    ((visto) 231733 #1232 e #4154: true às 19:30, false às 20:00, a todos os online; na abertura, o aviso da hora
    dobrada, 191924 #14217-#14218)."""
    if s.war_states is None:
        return  # o cliente ainda não recebeu o login
    now = s.ctx.clock.now()
    if (mine := bf.mine_open(now)) != s.mine_open:
        s.mine_open = mine
        s.send(S_MINE_ACTIVE, pb.GuildMsg(param5=mine))
        if mine:
            s.send(S_CHAT, _chat(DOUBLE_TIME, tip=True))
    if (cur := _states_tuple(s.ctx.templates, now)) != s.war_states:
        s.war_states = cur
        s.send(S_WARFIELD_STATE, states(s.ctx.templates, now))


def players_on(ctx: GameContext, campaign_id: int) -> list[GameSession]:
    return [o for o in ctx.online.sessions()
            if o.campaign is not None and o.campaign.warfield == campaign_id and o.snapshot is not None]  # fmt: skip


def on_map(s: GameSession, campaign_id: int) -> list[GameSession]:
    return [o for o in players_on(s.ctx, campaign_id) if o is not s]


def _room_player(o: GameSession, cid: int) -> pb.RoomPlayerMsg:
    """O 21 de um jogador no campo: a guilda e o lado (``teamId``, visto #9477 consortiaId 1 e teamId 2)."""
    assert o.snapshot is not None and o.campaign is not None
    guild = o.ctx.guilds.of(o.player_id)
    msg = space.room_player(o.snapshot, o.ctx.templates, o.campaign.pos, cid, o.ctx.clock.now(),
                            guild=guild[0] if guild else None)  # fmt: skip
    found = o.ctx.warfields.fields.get(cid)
    if found is not None and o.player_id in found.marks:
        msg.teamId = found.marks[o.player_id].team
    return msg


def _link(o: GameSession) -> str:
    """O nome com link do chat (visto #10209): ``<a t="1" id=... name=... consortiaId=... serverName=... />``."""
    assert o.snapshot is not None
    guild = o.ctx.guilds.of(o.player_id)
    c = o.snapshot.character
    return (f'<a t="1" id="{c.id}" name="{c.nickname or ""}" consortiaId="{guild[0].id if guild else 0}" '
            f'serverName="{o.snapshot.server.name}" grades="0" />')  # fmt: skip


def _field(s: GameSession) -> tuple[bf.Field, datetime] | None:
    """A partida do campo onde o jogador está, se a janela ainda é a dela."""
    c = s.campaign
    if c is None or c.warfield not in bf.FIELDS:
        return None
    return _open(s.ctx, c.warfield, s.ctx.clock.now())


def _info(s: GameSession, field: bf.Field) -> pb.WarFightInfoMsg:
    """4252 (visto #9482 em diante): os pontos, os abates e a honra total do jogador (o geste do personagem, 850->853
    na entrega #10137), ``order`` 0 e os dois lados fixos (one = time 1, two = time 2); sem ``leftTime``."""
    assert s.snapshot is not None
    mine = field.mark(s.player_id)
    return pb.WarFightInfoMsg(teamId=mine.team, score=mine.score, order=0, geste=s.snapshot.character.geste,
                              hitCount=mine.wins, oneCount=field.count(1), twoCount=field.count(2),
                              oneScore=field.score(1), twoScore=field.score(2))  # fmt: skip


def _push_info(ctx: GameContext, field: bf.Field) -> None:
    """O 4252 vai a todos no campo a cada mudança de placar (visto: um a cada entrega ou abate de qualquer um)."""
    for o in players_on(ctx, field.campaign_id):
        o.send(S_WAR_INFO, _info(o, field))


def _state_msg(player_id: int, state: int, server: str = "", left: int = 0) -> pb.PlayerStateListMsg:
    msg = pb.PlayerStateListMsg()
    msg.playerState.add(armyId=player_id, state=state, leftTime=left, serverName=server)
    return msg


def _ranking(field: bf.Field, prize: dict[int, tuple[int, int]] | None = None) -> list[pb.WarReportMsg]:
    """As linhas do placar (4255/4254, visto #9632 e #11669): todos que entraram, na ordem de chegada, ``order`` 0,
    nome, abates e a honra do campo; no fim, o prêmio de cada um (``itemCount`` Insignia, ``winGesteCount`` honra;
    0 para quem já tinha saído, visto yasuo2/yasuo3)."""
    rows = []
    for pid, mark in field.marks.items():
        item, honor = (prize or {}).get(pid, (0, 0))
        rows.append(pb.WarReportMsg(order=0, nickName=mark.name, userId=pid, score=mark.score, hitCount=mark.wins,
                                    teamId=mark.team, geste=mark.honor, serverName=mark.server, itemCount=item,
                                    winGesteCount=honor))  # fmt: skip
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
    field = found[0]
    cid = msg.param1
    mark = field.mark(s.player_id)
    mark.name, mark.server = snap.character.nickname or "", snap.server.name
    space.leave(s)
    s.campaign = CampaignMap(cid, bf.field_nodes(cid), bf.CAMP[mark.team], warfield=cid)  # (visto #9477: 17,76)
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER, isCross=True)
    room.room.campaignId = cid
    s.send(S_MAP, map_sync(s, ARMY_IDLE))  # (visto #14232 e #9475): 140 vem antes do 125 no campo
    s.send(S_ROOM_CREATED, room)
    me = _room_player(s, cid)
    others = on_map(s, cid)
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *(_room_player(o, cid) for o in others)]))
    for other in others:
        other.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    s.send(S_NODES, s.campaign.node_list())
    _push_info(ctx, field)  # o lado de quem entrou cresce para todos (visto #9533)
    states_now = pb.PlayerStateListMsg()  # (visto #9483): o estado de cada um no campo logo depois do 4252
    for o in [s, *others]:
        m = field.mark(o.player_id)
        states_now.playerState.add(armyId=o.player_id, state=2 if m.carry else 0, leftTime=0, serverName=m.server)
    s.send(S_PLAYER_STATE, states_now)
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
    found = _field(s)
    if found is None:  # fora do campo: a partida aberta em que o jogador entrou
        found = next((f for cid in bf.FIELDS if (f := _open(s.ctx, cid, s.ctx.clock.now())) is not None
                      and s.player_id in f[0].marks), None)  # fmt: skip
    if found is not None:
        msg.info.extend(_ranking(found[0]))
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
    if me.dead or them.dead or me.team == them.team:  # TODO(inventado): o recuso de morto ou do mesmo lado (o
        s.log.info("8334 contra morto ou aliado")  # cliente só oferece o ataque a inimigos vivos)
        return
    if bf.in_base(them.team, target.campaign.pos):  # TODO(inventado): a base protege (o texto é o da entrada)
        s.send(S_ALERT, _chat(ENEMY_BASE, 7))
        return
    me.fighting = them.fighting = True
    cid = c.warfield
    # o alvo é avisado (visto #10207-#10209: 111 com o nome, 4494 e 83 com o link)
    target.send(S_ALERT, _chat(ATTACKED_TEXT.format(snap.character.nickname or ""), 7))
    _to_map(s.ctx, cid, S_CROSS, _cross((s, c.pos, 2), (target, target.campaign.pos, 2)))
    target.send(S_CHAT, _chat(ATTACKED_TEXT.format(_link(s)), 3))

    async def finished(won: bool) -> None:
        await pvp_over(s, target, field, won)

    pvp_fight(s, target.snapshot, PVP_TYPE, PVP_SCENE, finished)


async def pvp_over(s: GameSession, target: GameSession, field: bf.Field, won: bool) -> None:
    """Fim da luta do campo (``bf.pvp_loss``/``bf.pvp_gain``): o perdedor perde 15% dos pontos e renasce no
    acampamento do lado (4104 e 4175 state 1, ou 3 carregando, por 25 s); o vencedor ganha 20 + 1 a cada 20 pontos
    do outro, 10 de honra e 10 pontos de PvP entre servidores, e o lado dele soma o ganho (a perda não desconta).
    Ordem (visto) 152321 #11098-#11131: 4104, 4175, 4252, 4494, 4103, 4471, 3, 112 (767), 4388 tipo 4, 4252, 4269,
    111 e 83; o perdedor: 4104, 4175, 4252, 4494, 4103, 4269 (isAdd false), 111 e 83 (#9795-#9830).
    TODO(inventado): o 4388 ``data`` = abates no campo (visto "1" duas vezes, #11111 e #11260)."""
    winner, loser = (s, target) if won else (target, s)
    wm, lm = field.mark(winner.player_id), field.mark(loser.player_id)
    wm.fighting = lm.fighting = False
    if field.settled:  # a partida acabou durante a luta: só o fim da luta
        s.send(S_REPORT, pb.BattleReportMsg(battleResult=1 if won else 2, battleScene=PVP_SCENE))
        return
    ctx, cid, now = s.ctx, field.campaign_id, s.ctx.clock.now()
    lost, gained = bf.pvp_loss(lm.score), bf.pvp_gain(lm.score)
    lm.score -= lost
    wm.score, wm.honor, wm.wins = wm.score + gained, wm.honor + bf.KILL_HONOR, wm.wins + 1
    field.gain(wm.team, gained)
    wm.streak += 1
    texts = _streak_texts(ctx, field, winner, loser, wm, lm)
    lm.streak = 0
    here = [o for o in (winner, loser) if o.campaign is not None and o.campaign.warfield == cid]
    if loser in here:
        camp = bf.CAMP[lm.team]
        loser.campaign.pos = camp  # type: ignore[union-attr]
        _to_map(ctx, cid, S_ARMY_POS, pb.ArmyPosUpdatedMsg(armyId=loser.player_id, curPosX=camp[0], curPosY=camp[1],
                                                           serverName=lm.server))  # fmt: skip
    for text in texts:  # (visto #10963-#10970): 111 logo depois do 4104, 83 depois do 4494; os dois com link
        _to_map(ctx, cid, S_ALERT, _chat(text, 7))
    if loser in here:
        _die(ctx, field, loser.player_id)
    _push_info(ctx, field)
    rows = [(o, o.campaign.pos, 0) for o in here]  # type: ignore[union-attr]
    _to_map(ctx, cid, S_CROSS, _cross(*rows))
    for text in texts:
        _to_map(ctx, cid, S_CHAT, _chat(text, 3))
    s.send(S_REPORT, pb.BattleReportMsg(battleResult=1 if won else 2, battleScene=PVP_SCENE))  # (visto) #11103
    saves = add_honor(winner, bf.KILL_HONOR) if winner.snapshot is not None else []
    await _quest(winner, KILL_QUEST)  # (visto #11106): 112 da 767 depois do 4471/3
    if (wsnap := winner.snapshot) is not None:  # títulos "Executioner"/"Grim Reaper" (Accumulated N kills)
        saves.append(titles.count(wsnap, titles.FIELD_KILLS, now))
        cfg = ctx.world.settings.get("arena_party") or {}
        cross = ev.state(wsnap, arena_grupo.KEY, now)
        cross.value = arena_grupo.points(cross, now, cfg) + CROSS_POINTS
        cross.text, cross.updated_at = arena_grupo.period(now, cfg), now
        saves.append(cross)
        await ctx.characters.save(*saves)
    winner.send(S_SNS, sns_msg(winner.player_id, SNS_PVP, str(wm.wins)))
    if winner in here:
        winner.send(S_WAR_INFO, _info(winner, field))  # a honra nova (visto #11126 geste 872)
    for o, add, pts, honor, text in (
        (winner, True, gained, bf.KILL_HONOR, WIN_TEXT.format(gained, bf.KILL_HONOR, CROSS_POINTS)),
        (loser, False, lost, 0, LOSE_TEXT.format(lost)),
    ):
        name = o.snapshot.server.name if o.snapshot else ""
        o.send(S_WAR_MOVIE, pb.WarMovieMsg(score=pts, geste=honor, isAdd=add, userId=o.player_id, serverName=name))
        o.send(S_ALERT, _chat(text, 7))
        o.send(S_CHAT, _chat(text, 3))


def _streak_texts(
    ctx: GameContext, field: bf.Field, winner: GameSession, loser: GameSession, wm: bf.Mark, lm: bf.Mark
) -> list[str]:
    """As frases do abate (``wm.streak`` já com este): primeiro sangue da partida, a da sequência
    (``taxas.field_streaks``) e o "pôs fim" a quem estava em sequência de ``taxas.field_streak_stop``."""
    out = []
    win, lose = _link(winner), _link(loser)
    if not field.first_blood:
        field.first_blood = True
        out.append(bf.FIRST_BLOOD.format(win))
    if (line := bf.streak_text(wm.streak, taxas.get(ctx.world.settings, "field_streaks"))) is not None:
        out.append(line.format(win))
    if lm.streak >= int(taxas.get(ctx.world.settings, "field_streak_stop")):
        out.append(bf.STOP_TEXT.format(win, lose))
    return out


def _die(ctx: GameContext, field: bf.Field, player_id: int) -> None:
    """Morto até a próxima onda (``bf.respawn_ms``, ``taxas.field_respawn_period``): 4175 state 1, ou 3 carregando."""
    mark = field.marks[player_id]
    mark.dead, mark.streak = True, 0
    now = ctx.clock.now()
    left = bf.respawn_ms(field.opened, now, int(taxas.get(ctx.world.settings, "field_respawn_period")))
    dead = DEAD_CARRYING if mark.carry else DEAD
    _to_map(ctx, field.campaign_id, S_PLAYER_STATE, _state_msg(player_id, dead, mark.server, left))
    asyncio.get_running_loop().call_later(left / 1000, _revive, ctx, field, player_id)


def _revive(ctx: GameContext, field: bf.Field, player_id: int) -> None:
    """Fim dos 25 s: o 4175 do renascido a todos no campo, state 2 se ainda carrega, 0 se não (visto #9905, #10384)."""
    mark = field.marks.get(player_id)
    if mark is None or not mark.dead or field.settled:
        return
    mark.dead = False
    _to_map(ctx, field.campaign_id, S_PLAYER_STATE, _state_msg(player_id, 2 if mark.carry else 0, mark.server))


@router.on(8338)
async def restore_hp(s: GameSession, _: object) -> None:
    """Restaurar vida no campo (``PvpMapRightView`` "reset", ``warMaxhp``): o herói ferido (a luta do campo gasta a
    vida como as outras, ``pvp_fight``) volta cheio por 200 Star Points (idioma
    ``PvpMapRightView.reset``: "Spend 200 Star points to restore your health."), 150 e 3; cheio, o aviso (visto
    #15796); sem pontos, ``StarIconView.command01``."""
    snap = s.snapshot
    if s.campaign is None or not s.campaign.is_warfield or snap is None or snap.leader is None:
        return
    live = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now()).live
    if b.hero_hp(snap.leader, live) >= live:
        s.send(S_ALERT, _chat(FULL_HP, channel=7))
        return
    sy = rules.systems(snap)
    if sy.star_point < RESET_STARS:
        s.send(S_ALERT, _chat(NO_STARS, channel=7))
        return
    sy.star_point -= RESET_STARS
    snap.leader.hp = live
    await s.ctx.characters.save(snap.leader, sy)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    _player(s)


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
    s.campaign = CampaignMap(bf.MINE, bf.mine_nodes(), bf.START, warfield=bf.MINE)
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
    # atividade "Amethyst Mine" (tipo 111): cada entrada é uma participação (dedução pelo texto)
    if counted := ev.count(snap, ctx.events, ev.MINEFIELD, now):
        await ctx.characters.save(*counted)


def _mine_msg(s: GameSession) -> pb.TramcarInfoMsg:
    """4548: o carrinho do jogador (``carInfo``); sem carrinho, tudo zero."""
    cart = s.ctx.warfields.carts.get(s.player_id)
    car = pb.CarInfo(userId=s.player_id, armyId=s.player_id, minerals=0, quality=0, tramcarCount=0, handCount=0,
                     isOwn=0, pickCount=0)  # fmt: skip
    if cart is not None:
        car.quality, car.tramcarCount, car.isOwn, car.pickCount = cart.quality, 1, 1, cart.picks
        car.minerals = cart.picks * 20  # (visto #2136): 20 por coleta
    # (visto) 183522 #6036, 232017, 225632: ``count`` sempre 2, ``activeTime`` o que falta da janela
    msg = pb.TramcarInfoMsg(activeTime=bf.mine_left(s.ctx.clock.now()), count=2, multiple=2)
    msg.carInfo.add().CopyFrom(car)
    return msg


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
    if mark.dead:
        if n in bf.EXIT_GATES:
            s.send(S_ALERT, _chat(DEAD_GATE, 7))
        return
    if n in bf.ENEMY_ENTRY and node["param1"] != mark.team:
        s.send(S_ALERT, _chat(ENEMY_BASE, 7))
    elif n == bf.DELIVER[3 - mark.team] and not mark.fighting and s.battle is None and camp not in field.busy:
        # o oficial inimigo luta (20261101 #4031-#4133: 5125 no 012 do time 1, sem 4105; 128 nodeState 4, 157
        # tipo 32 e, na derrota, a perda do guardião, 150)
        _guardian_fight(s, field, camp, node, chase=False)
    elif n == bf.DELIVER[mark.team] and mark.carry is not None:
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
    if n not in bf.COLLECT or mark.carry is not None or mark.dead:
        return
    mark.carry = bf.ore(taxas.get(s.ctx.world.settings, "field_ore_weights"))
    _to_map(s.ctx, c.warfield, S_PLAYER_STATE, _state_msg(s.player_id, 2, mark.server))  # (visto #9957, a todos)
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
    if found is None:
        return
    field = found[0]
    mark = field.mark(s.player_id)
    if camp - c.warfield * 1000 != bf.DELIVER[mark.team] or mark.carry is None or mark.dead:
        return
    quality = mark.carry
    pts, honor, shards = bf.TURN_IN[quality]
    mark.score, mark.honor, mark.carry = mark.score + pts, mark.honor + honor, None
    field.gain(mark.team, pts)
    drops = [(bf.SHARD, shards)]
    new: list[Item] = []
    if rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        new, _ = rewards.grant(snap, s.ctx.templates, drops)
    # ordem (visto 152321 #10102-#10138): 4175, 4252 (a honra velha), 4471, 3, 115, 111, 83, 4252 e 4269
    _to_map(s.ctx, c.warfield, S_PLAYER_STATE, _state_msg(s.player_id, 0, mark.server))
    _push_info(s.ctx, field)
    saves = add_honor(s, honor)
    await s.ctx.characters.save(*saves, *new)
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    text = bf.turn_in_text(quality, pts, honor, shards)
    s.send(S_ALERT, _chat(text, 7))
    s.send(S_CHAT, _chat(text, 3))
    s.send(S_WAR_INFO, _info(s, field))
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
    found = _field(s)
    if found is not None and (dead := found[0].mark(s.player_id)).dead:
        # morto fica na base até a onda (decisão do usuário): o caminho para no último passo dentro dela
        routes = list(msg.routes)
        keep = next((i for i, r in enumerate(routes) if not bf.in_base(dead.team, (r.x // bf.TILE, r.y // bf.TILE))),
                    len(routes))  # fmt: skip
        if keep < len(routes):
            del msg.routes[keep:]
            end = (msg.routes[-1].x // bf.TILE, msg.routes[-1].y // bf.TILE) if msg.routes else bf.CAMP[dead.team]
            c.pos = end
            s.send(S_ARMY_POS, pb.ArmyPosUpdatedMsg(armyId=s.player_id, curPosX=end[0], curPosY=end[1],
                                                    serverName=dead.server))  # fmt: skip
            if not msg.routes:
                return
    move = pb.PosMoveMsg(mapId=c.warfield, armyId=s.player_id, routes=msg.routes, serverName=snap.server.name)
    for other in on_map(s, c.warfield):
        other.send(S_MOVE, move)
    if found is None:
        return
    mark = found[0].mark(s.player_id)
    mark.path = tuple((r.x // bf.TILE, r.y // bf.TILE) for r in msg.routes)
    mark.path_at = time.monotonic()
    _watch_path(s, found[0], mark.path_at)


def _watch_path(s: GameSession, field: bf.Field, started: float) -> None:
    """Segue o trecho andado (``taxas.field_move_speed`` casas/s) e chama ``guardian_chase`` na casa em que o jogador
    entra no alcance; um 5124 novo troca o trecho e este para."""
    mark = field.mark(s.player_id)
    if mark.path_at != started or s.campaign is None or not s.campaign.is_warfield:
        return
    speed = float(taxas.get(s.ctx.world.settings, "field_move_speed"))
    if mark.carry:  # ENTERED_TEXT (visto #9958): "Movement speed is now decreased by 50%."
        speed *= float(taxas.get(s.ctx.world.settings, "field_carry_speed"))
    elapsed = time.monotonic() - started
    pos = bf.position_at(mark.path, elapsed, speed)
    if pos is None:
        return
    s.campaign.pos = pos
    if guardian_chase(s) or pos == mark.path[-1]:
        return
    asyncio.get_running_loop().call_later(1 / speed, _watch_path, s, field, started)


S_CHASE, S_NODE, S_NPC_MOVE = 4105, 128, 4122  # NPCChaseMsg, CampaignNodeUpdateMsg, NPCMoveMsg
FIGHTING_NODE, ALIVE_NODE, DOWN_NODE = 4, 1, 8  # 128 nodeState na luta e de volta (visto #10210, #10341)


def guardian_chase(s: GameSession) -> bool:
    """Um guardião vivo do outro lado (``bf.ALIVE_GUARDIANS``) a até ``taxas.field_guardian_range`` casas persegue e
    puxa luta. Ordem (visto 121453 #10205-#10211): 4105 (nó, exército e a posição do jogador), 4494 (state 2),
    128 nodeState 4 (userId, param1 = lado do guardião) e o 157."""
    c, snap = s.campaign, s.snapshot
    found = _field(s)
    if c is None or snap is None or found is None or s.battle is not None:
        return False
    field = found[0]
    mark = field.mark(s.player_id)
    if mark.dead or mark.fighting:
        return False
    reach = int(taxas.get(s.ctx.world.settings, "field_guardian_range"))
    x, y = c.pos
    for camp, node in c.nodes.items():
        n = camp - c.warfield * 1000
        if (n in bf.ALIVE_GUARDIANS.get(c.warfield, ()) and camp not in field.busy and node["param1"] != mark.team
                and max(abs(node["posX"] - x), abs(node["posY"] - y)) <= reach):  # fmt: skip
            _guardian_fight(s, field, camp, node)
            return True
    return False


def _guardian_fight(s: GameSession, field: bf.Field, camp: int, node: dict[str, Any], chase: bool = True) -> None:
    from .campaign import player_hero  # campaign importa este módulo
    from .singlepass import boss_spec

    c, mark = s.campaign, field.mark(s.player_id)
    assert c is not None
    field.busy.add(camp)
    mark.fighting = True
    side = int(node["param1"])
    if chase:
        _to_map(s.ctx, c.warfield, S_CHASE, pb.NPCChaseMsg(nodeId=camp, armyId=s.player_id, curPosX=c.pos[0],
                                                           curPosY=c.pos[1], serverName=mark.server))  # fmt: skip
    _to_map(s.ctx, c.warfield, S_CROSS, _cross((s, c.pos, 2)))
    _to_map(s.ctx, c.warfield, S_NODE, pb.CampaignNodeUpdateMsg(nodeId=camp, nodeState=FIGHTING_NODE,
                                                                userId=s.player_id, param1=side))  # fmt: skip
    hero = s.ctx.templates.get("GameHeroTemp", int(node["heroTempId"])) or {}
    spec = boss_spec(s, hero, max(1, int(hero.get("Live") or 1)), bf.GUARDIAN_BATTLE)
    spec["battleScene"] = PVP_SCENE

    async def finished(battle: Battle, won: bool) -> None:
        s.battle, s.hero_sp = None, battle.player_sp
        await _guardian_over(s, field, camp, node, won)

    s.battle = Battle(spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished,
                      settings=s.ctx.world.settings)  # fmt: skip
    s.battle.start()


async def _guardian_over(s: GameSession, field: bf.Field, camp: int, node: dict[str, Any], won: bool) -> None:
    """Fim da luta com o guardião. Derrota (visto 121453 #10335-#10364): 4104 para o acampamento, 4103, 4122 do
    guardião de volta ao ponto, 4175 morto, 128 nodeState 1, 4494 state 0, 4269 e "You lost: N Points."
    (``taxas.field_guardian_loss``). TODO(inventado): a vitória (não vista) derruba o guardião (128 nodeState 8) e
    não dá pontos."""
    mark = field.mark(s.player_id)
    mark.fighting = False
    field.busy.discard(camp)
    cid, ctx, c = field.campaign_id, s.ctx, s.campaign
    here = c is not None and c.warfield == cid and not field.settled
    if won:
        s.send(S_REPORT, pb.BattleReportMsg(battleResult=1, battleScene=PVP_SCENE))
        # TODO(inventado): o oficial vencido (não visto) fica de pé, senão o lado perde a entrega
        if c is not None and here and camp - cid * 1000 not in bf.DELIVER.values():
            c.nodes.pop(camp, None)
            _to_map(ctx, cid, S_NODE, pb.CampaignNodeUpdateMsg(nodeId=camp, nodeState=DOWN_NODE,
                                                               param1=int(node["param1"])))  # fmt: skip
            _to_map(ctx, cid, S_CROSS, _cross((s, c.pos, 0)))
        return
    home = bf.CAMP[mark.team]
    if c is not None and here:
        c.pos = home
        _to_map(ctx, cid, S_ARMY_POS, pb.ArmyPosUpdatedMsg(armyId=s.player_id, curPosX=home[0], curPosY=home[1],
                                                           serverName=mark.server))  # fmt: skip
    s.send(S_REPORT, pb.BattleReportMsg(battleResult=2, battleScene=PVP_SCENE))
    if not here:
        return
    _to_map(ctx, cid, S_NPC_MOVE, pb.NPCMoveMsg(id=camp, curPosX=int(node["posX"]), curPosY=int(node["posY"])))
    _die(ctx, field, s.player_id)
    _to_map(ctx, cid, S_NODE, pb.CampaignNodeUpdateMsg(nodeId=camp, nodeState=ALIVE_NODE, param1=int(node["param1"])))
    _to_map(ctx, cid, S_CROSS, _cross((s, home, 0)))
    lost = min(mark.score, int(taxas.get(ctx.world.settings, "field_guardian_loss")))
    mark.score -= lost
    _push_info(ctx, field)
    s.send(S_WAR_MOVIE, pb.WarMovieMsg(score=lost, geste=0, isAdd=False, userId=s.player_id, serverName=mark.server))
    s.send(S_ALERT, _chat(LOSE_TEXT.format(lost), 7))
    s.send(S_CHAT, _chat(LOSE_TEXT.format(lost), 3))


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
    """Fim da partida: vence o lado com mais pontos (``Field.winner``); quem está no campo leva 80 Insignia e 90 de
    honra (vencedor) ou 30 e 30 (perdedor, visto #11669 prince/VRIES) e a missão 50 se venceu. ``oneTeamId`` é o
    vencedor (cliente ``PvpSortListView.isVictory``: ``teamId == oneTeamId``; visto #11669 2455 x 2448).
    Ordem (visto 152321 #11662-#11704): 4248 state 2, 83, 4254, 4248, 22, 4471, 3, 115, 112 (818) e o 83 do prêmio."""
    field.settled = True
    now = ctx.clock.now()
    winner = field.winner()
    here = players_on(ctx, field.campaign_id)
    prize = {o.player_id: (bf.WIN_INSIGNIA, bf.WIN_HONOR) if field.mark(o.player_id).team == winner
             else (bf.LOSE_INSIGNIA, bf.LOSE_HONOR) for o in here}  # fmt: skip
    first = winner or 1  # empate (``bf.Field.winner``): ninguém vence, o time 1 vai em one
    second = 2 if first == 1 else 1
    report = pb.WarReportListMsg(oneTeamId=first if winner else 0, twoTeamId=second, oneScore=field.score(first),
                                 twoScore=field.score(second))  # fmt: skip
    report.info.extend(_ranking(field, prize))
    for o in here:
        snap = o.snapshot
        assert snap is not None
        push_states(o)  # 4248 com o campo encerrado
        o.send(S_CHAT, _chat(END_TEXT, tip=True))
        o.send(S_WAR_REPORT, report)
        o.send(S_WARFIELD_STATE, states(ctx.templates, now))
        o.campaign = None
        o.send(S_EXIT, pb.CampaignExitMsg(result=1, playerId=o.player_id, armyId=o.player_id,
                                          serverName=snap.server.name))  # fmt: skip
        insignia, honor = prize[o.player_id]
        drops = [(bf.INSIGNIA, insignia)]
        new: list[Item] = []
        if rewards.can_grant(snap, ctx.templates, drops, now):
            new, _ = rewards.grant(snap, ctx.templates, drops)
        # Double Honor Scroll: "Honor Received +{Grades}%"
        saves = add_honor(o, honor * (100 + buffs.percent(snap, ctx.templates, buffs.HONOR_BOOST, now)) // 100)
        await ctx.characters.save(*saves, *new)
        if new:
            o.send(S_ITEMS, rewards.items_msg(new, o.player_id))
        if winner is not None and field.mark(o.player_id).team == winner:  # "Obtain Victory in War Camp" (818)
            await _quest(o, WIN_QUEST)
        o.send(S_CHAT, _chat(bf.win_text(insignia, honor)))
    for o in ctx.online.sessions():
        push_states(o)
