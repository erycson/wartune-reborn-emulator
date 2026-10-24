"""Chat entre jogadores: mundo (8198), cena (15005/25024/25096), cornetas (5011, 8623), convite rápido da sala
(8353), privado (15023) e quem mandou (15038).

Remetente e nome saem sempre do snapshot do servidor; o texto perde as tags HTML para ninguém
forjar link de jogador ou item. Quem pôs o remetente na lista negra não recebe. Regras do
cliente em docs/chat.md.
"""

from __future__ import annotations

import re
from datetime import timedelta
from xml.sax.saxutils import quoteattr

from ...domain import gameday
from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from .. import events as ev
from .. import guild, items, rooms, social
from ..builders import login as b
from ..router import router
from ..session import GameSession

S_CHAT, S_PRIVATE, S_PRIVATE_REPLY, S_USER_INFO = 83, 4231, 4236, 4256
S_ITEMS, S_FREE_BUGLES, S_CROSS_BUGLE = 115, 4500, 4541
BIG_BUGLE, GUILD, CURRENT, WORLD, CROSS = 1, 5, 8, 10, 13
MIN_GRADE, MAX_LEN = 6, 100  # ChatHelper / ChatInputViewII (cliente inglês: maxChars 100, checkLength)
BUGLE = timedelta(seconds=2)
# ponytail: o cliente não limita a guilda (ChatHelper); 1 s contra spam
COOLDOWN = {GUILD: timedelta(seconds=1), CURRENT: timedelta(seconds=10), WORLD: BUGLE, BIG_BUGLE: BUGLE, CROSS: BUGLE}
PRIVATE_COOLDOWN = timedelta(seconds=1)  # IMFrame: 1 s entre mensagens (friends.im.IMFrame.command03)
OFFLINE = -1  # 4236.result: "o jogador não está online"
SMALL_BUGLE, BIG_BUGLE_ITEM, CROSS_BUGLE_ITEM = 208003, 208002, 208025  # ShopGoodsInfo.*_BUGLE_TEMP_ID
ROOM_LINK = 4  # ChatChannelMsg.type: ChatFormat.createRoomCellData lê cada <tag> da mensagem como link de sala
INVITE_ROOM = 0  # CaptainSpeakMsg.type: 0 sala, 1 casamento (QuickInviteFrame.getSendType)
S_ALERT = 111
_TAG = re.compile(r"<[^>]*>")


def _text(s: GameSession, raw: str, key: int, cooldown: timedelta) -> str | None:
    """Texto limpo se o jogador pode falar agora (``key`` = canal ou -destinatário); marca o envio."""
    assert s.snapshot is not None
    text = _TAG.sub("", raw).strip()
    now = s.ctx.clock.now()
    last = s.chat_at.get(key)
    if not text or len(text) > MAX_LEN or s.snapshot.character.grades < MIN_GRADE:
        return None
    if last is not None and now - last < cooldown:
        return None
    s.chat_at[key] = now
    return text


def _broadcast(s: GameSession, code: int, msg: pb.ChatChannelMsg | pb.CrossBigBugleMsg) -> None:
    # o cliente não mostra a própria mensagem ao enviar: quem falou também recebe
    for other in s.ctx.online.sessions():
        if not social.blocks(other, s.player_id):
            other.send(code, msg)


def _channel_msg(s: GameSession, channel: int, text: str) -> pb.ChatChannelMsg:
    assert s.snapshot is not None
    c = s.snapshot.character
    out = pb.ChatChannelMsg(channel=channel, encodeMsg=text, otherId=c.id, name=c.nickname or "")
    mine = s.ctx.guilds.of(s.player_id)
    if mine is not None:
        out.consortiaId, out.consortiaName = mine[0].id or 0, mine[0].name
    return b.complete(out)


async def _say(s: GameSession, msg: pb.ChatChannelMsg, channel: int) -> None:
    text = _text(s, msg.encodeMsg, channel, COOLDOWN[channel])
    if text is None:
        s.log.info("chat recusado", canal=channel, tamanho=len(msg.encodeMsg))
        return
    out = _channel_msg(s, channel, text)
    if channel == GUILD:  # só os membros online da guilda (quem falou também)
        mine = s.ctx.guilds.of(s.player_id)
        for o in guild.online_members(s.ctx, mine[0].id or 0) if mine is not None else []:
            if not social.blocks(o, s.player_id):
                o.send(S_CHAT, out)
        return
    _broadcast(s, S_CHAT, out)


def free_bugles(s: GameSession) -> int:
    """Cornetas pequenas grátis que restam hoje (o contador zera na virada do dia do servidor).

    Cota do ConfigInfo ``SMALL_BUGLE_FREE_COUNT`` (10, #2780) + ``vip_bugle_bonus[nível VIP]`` (``game_settings``,
    migração 0036): nem o cliente nem a captura dizem se o VIP ganha mais, então o padrão é 0 (sem efeito).
    """
    from .vip import is_vip, vip_grade  # vip importa player, que importa este pacote

    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    today = gameday.today(now)
    if c.bugle_free_day != today:
        c.bugle_free_day, c.bugle_free_used = today, 0
    quota = int(ev.config(s.ctx.templates, "SMALL_BUGLE_FREE_COUNT", "0"))
    bonus = list(s.ctx.world.settings.get("vip_bugle_bonus") or [])
    if is_vip(snap, now) and 0 <= (grade := vip_grade(s, snap)) < len(bonus):
        quota += int(bonus[grade])
    return max(0, quota - c.bugle_free_used)


async def _pay_bugle(s: GameSession, template_id: int, *, free: bool = False) -> bool:
    """Gasta uma corneta (grátis primeiro, se ``free``) antes de qualquer await; grava e avisa."""
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    if free and free_bugles(s) > 0:
        c.bugle_free_used += 1
        await s.ctx.characters.save(c)
        s.send(S_FREE_BUGLES, pb.CampaignReqMsg(paraInt1=free_bugles(s)))
        return True
    item: Item | None = items.bag_item(snap, template_id=template_id)
    if item is None:
        return False
    gone = items.take_one(snap, item)
    await s.ctx.characters.save(*([] if gone else [item]), delete=(gone,) if gone else ())
    s.send(S_ITEMS, items.item_update(item, s.player_id))
    return True


@router.on(8198)
async def world_chat(s: GameSession, msg: pb.ChatChannelMsg) -> None:
    """Canal mundo (corneta pequena): nível mínimo ``world_chat_min_grade`` (banco), cota grátis do dia e depois o
    item 208003. Abaixo do nível: 111 "Requires character Level of 20" (tutorial_en #2781-#2782, nível 14)."""
    assert s.snapshot is not None
    need = int(s.ctx.world.settings.get("world_chat_min_grade", MIN_GRADE))
    if s.snapshot.character.grades < need:  # antes de marcar o intervalo e de gastar corneta
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Requires character Level of {need}"))
        return
    text = _text(s, msg.encodeMsg, WORLD, COOLDOWN[WORLD])
    if text is None or not await _pay_bugle(s, SMALL_BUGLE, free=True):
        s.log.info("corneta pequena recusada", tamanho=len(msg.encodeMsg))
        return
    _broadcast(s, S_CHAT, _channel_msg(s, WORLD, text))
    from . import events  # events importa login, que importa este pacote

    await events.leed_done(s, events.WORLD_CHAT_LEED)


@router.on(8705)
async def free_bugle_count(s: GameSession, _: object) -> None:
    s.send(S_FREE_BUGLES, pb.CampaignReqMsg(paraInt1=free_bugles(s)))


@router.on(5011)
async def big_bugle(s: GameSession, msg: pb.ChatChannelMsg) -> None:
    """Corneta grande (item 208002), canal 1: vai para a faixa de cornetas de todos."""
    text = _text(s, msg.encodeMsg, BIG_BUGLE, COOLDOWN[BIG_BUGLE])
    if text is None or not await _pay_bugle(s, BIG_BUGLE_ITEM):
        s.log.info("corneta grande recusada", tamanho=len(msg.encodeMsg))
        return
    _broadcast(s, S_CHAT, _channel_msg(s, BIG_BUGLE, text))


@router.on(8623)
async def cross_bugle(s: GameSession, msg: pb.CrossBigBugleMsg) -> None:
    """Corneta entre servidores (item 208025) -> 4541. Sem entre-servidores: só este servidor."""
    snap = s.snapshot
    assert snap is not None
    text = _text(s, msg.content, CROSS, COOLDOWN[CROSS])
    if text is None or not await _pay_bugle(s, CROSS_BUGLE_ITEM):
        s.log.info("corneta entre servidores recusada", tamanho=len(msg.content))
        return
    c = snap.character
    out = pb.CrossBigBugleMsg(
        serverId=snap.server.id, serverName=snap.server.name, userId=c.id, nickName=c.nickname or "", content=text
    )
    out.isLookInfo = True
    _broadcast(s, S_CROSS_BUGLE, b.complete(out))


@router.on(15005)
async def channel_chat(s: GameSession, msg: pb.ChatChannelMsg) -> None:
    """Canal da cena (8) e da guilda (5, só membros online). Time (6) fica recusado até existir.

    ponytail: "cena" = todos online até existir o registro de cenas (cidade do céu).
    """
    if msg.channel not in (CURRENT, GUILD):
        s.log.info("canal de chat não suportado", canal=msg.channel)
        return
    await _say(s, msg, msg.channel)


@router.on(25024)
async def battle_cross_chat(s: GameSession, msg: pb.ChatChannelMsg) -> None:
    """Canal 8 em batalha entre servidores (battleType 10/33/34): sem cross = canal local."""
    await channel_chat(s, msg)


@router.on(25096)
async def warfield_chat(s: GameSession, msg: pb.ChatChannelMsg) -> None:
    """Canais 6/8 na campanha entre servidores: tratado como o 15005 deste servidor."""
    await channel_chat(s, msg)


@router.on(15023)
async def private_chat(s: GameSession, msg: pb.ChatFriendMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    text = _text(s, msg.encodeMsg, -msg.toId, PRIVATE_COOLDOWN)
    if text is None or msg.toId == s.player_id:
        s.log.info("privado recusado", para=msg.toId)
        return
    out = pb.ChatFriendMsg(
        fromId=s.player_id,
        fromNick=snap.character.nickname or "",
        toId=msg.toId,
        encodeMsg=text,
        sendDate=b.fmt_time(s.ctx.clock.now()),
    )
    target = s.ctx.online.get(msg.toId)
    if target is None or social.blocks(target, s.player_id):
        out.result = OFFLINE  # lista negra parece offline para quem foi bloqueado
    else:
        target.send(S_PRIVATE, out)
    s.send(S_PRIVATE_REPLY, out)


@router.on(15038)
async def user_info(s: GameSession, msg: pb.InfoReqMsg) -> None:
    """Dados de outro jogador: o cliente pede ao receber privado de quem não é amigo e só mostra
    a mensagem depois deste 4256."""
    c = (await social.characters(s.ctx, [msg.otherId])).get(msg.otherId)
    if c is None:
        s.log.info("15038 sem jogador", outro=msg.otherId)
        return
    other = s.ctx.online.get(msg.otherId)
    if other is not None and other.snapshot is not None:
        sns = other.snapshot.sns
    else:
        sns = await s.ctx.characters.read(lambda uow: uow.sns.by_character(msg.otherId))
    out = pb.RelationPlayerMsg()
    setattr(out, "from", getattr(msg, "from"))  # "from" é palavra reservada
    # (visto) oficial_20261023-171155-1 #70, #7753, #7758: a amizade de quem pergunta (relation 1, friendRp,
    # friendGrade, groupId 2). (dedução) sem relação os campos ficam 0: nenhuma captura pergunta por um estranho
    mine = s.snapshot.relations if s.snapshot is not None else []
    if (rel := next((r for r in mine if r.other_id == msg.otherId), None)) is not None:
        out.relation, out.friendRp, out.groupId = rel.relation, rel.friend_gp, rel.group_id
        out.friendGrade = social.friend_grade(s.ctx, rel)
    out.player.CopyFrom(social.simple_player(s.ctx, c))
    out.snsInfo.CopyFrom(social.sns_info(c, sns))  # o cliente lê snsInfo sem checar nulo
    b.complete(out)
    social.no_job(out.snsInfo)
    s.send(S_USER_INFO, out)


@router.on(8353)
async def quick_invite(s: GameSession, msg: pb.CaptainSpeakMsg) -> None:
    """ "Fast Invite" (``QuickInviteFrame``): o texto vai quebrado em linhas (``inviteContent``) e custa 1 Bullhorn
    (Small), com a cota grátis antes ("First 10 Attempts are Free", a mesma do 8198). Sai no canal mundo como link de
    sala (``ChatChannelMsg.type`` 4): o texto inteiro é o ``name`` da tag, e o clique manda o 9504 com o ``id``.
    ``position`` 0 é sala trancada (``RoomInfo.isLock``). ponytail: formato montado do cliente (sem captura do
    oficial); o tipo 1 (casamento) fica de fora porque a sala de casamento não existe (``marriage.py``)."""
    room = s.ctx.rooms.of(s.player_id)  # qualquer membro, com lugar livre (RoomRightView._inviteClick)
    if msg.type != INVITE_ROOM or room is None or rooms.OPEN not in room.seats:
        s.log.info("8353 sem sala", tipo=msg.type, sala=room.id if room else None)
        return
    text = _text(s, "".join(msg.inviteContent), WORLD, COOLDOWN[WORLD])
    if text is None or not await _pay_bugle(s, SMALL_BUGLE, free=True):
        s.log.info("8353 recusado", tamanho=sum(map(len, msg.inviteContent)))
        return
    attrs = {"id": room.id, "campaignId": room.campaign, "roomType": rooms.PVE, "position": int(not room.password)}
    link = "<room " + " ".join(f"{k}={quoteattr(str(v))}" for k, v in attrs.items()) + f" name={quoteattr(text)}/>"
    out = _channel_msg(s, WORLD, link)
    out.type = ROOM_LINK
    _broadcast(s, S_CHAT, out)
