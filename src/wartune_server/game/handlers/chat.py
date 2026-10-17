"""Chat entre jogadores: mundo (8198), cena (15005), privado (15023) e quem mandou (15038).

Remetente e nome saem sempre do snapshot do servidor; o texto perde as tags HTML para ninguém
forjar link de jogador ou item. Regras do cliente em docs/chat.md.
"""

from __future__ import annotations

import re
from datetime import timedelta

from ...domain.errors import NotFoundError
from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession

S_CHAT, S_PRIVATE, S_PRIVATE_REPLY, S_USER_INFO = 83, 4231, 4236, 4256
CURRENT, WORLD = 8, 10
MIN_GRADE, MAX_LEN = 6, 76  # ChatHelper / ChatInputViewII
COOLDOWN = {CURRENT: timedelta(seconds=10), WORLD: timedelta(seconds=2)}
PRIVATE_COOLDOWN = timedelta(seconds=1)  # ponytail: o cliente não limita o privado; 1 s contra spam
OFFLINE = -1  # 4236.result: "o jogador não está online"
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


async def _say(s: GameSession, msg: pb.ChatChannelMsg, channel: int) -> None:
    snap = s.snapshot
    assert snap is not None
    text = _text(s, msg.encodeMsg, channel, COOLDOWN[channel])
    if text is None:
        s.log.info("chat recusado", canal=channel, tamanho=len(msg.encodeMsg))
        return
    c = snap.character
    out = pb.ChatChannelMsg(channel=channel, encodeMsg=text, otherId=c.id, name=c.nickname or "")
    # o cliente não mostra a própria mensagem ao enviar: quem falou também recebe o 83
    s.ctx.online.broadcast(S_CHAT, b.complete(out))


@router.on(8198)
async def world_chat(s: GameSession, msg: pb.ChatChannelMsg) -> None:
    """Canal mundo (corneta pequena). ponytail: grátis; item 208003, cota grátis e 4500 depois."""
    await _say(s, msg, WORLD)


@router.on(15005)
async def channel_chat(s: GameSession, msg: pb.ChatChannelMsg) -> None:
    """Canal da cena (8). Guilda (5) e time (6) ficam recusados até existirem.

    ponytail: "cena" = todos online até existir o registro de cenas (cidade do céu).
    """
    if msg.channel != CURRENT:
        s.log.info("canal de chat não suportado", canal=msg.channel)
        return
    await _say(s, msg, CURRENT)


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
    if target is None:
        out.result = OFFLINE
    else:
        target.send(S_PRIVATE, out)
    s.send(S_PRIVATE_REPLY, out)


@router.on(15038)
async def user_info(s: GameSession, msg: pb.InfoReqMsg) -> None:
    """Dados de outro jogador: o cliente pede ao receber privado de quem não é amigo e só mostra
    a mensagem depois deste 4256."""
    other = s.ctx.online.get(msg.otherId)
    try:
        snap = other.snapshot if other is not None else await s.ctx.characters.snapshot(msg.otherId)
    except NotFoundError:
        snap = None
    if snap is None or not snap.character.active:
        s.log.info("15038 sem jogador", outro=msg.otherId)
        return
    c = snap.character
    out = pb.RelationPlayerMsg()
    setattr(out, "from", getattr(msg, "from"))  # "from" é palavra reservada
    out.player.CopyFrom(
        pb.SimplePlayerInfoMsg(
            userId=c.id,
            nickName=c.nickname or "",
            isExist=1,
            sexs=c.sex,
            pics=c.icon,
            camp=c.camp,
            grades=c.grades,
            gp=c.gp,
            repute=c.repute,
            job=c.job,
            fightingCapacity=c.fighting_capacity,
            state=1 if other is not None else 0,
        )
    )
    out.snsInfo.SetInParent()  # o cliente lê snsInfo sem checar nulo
    s.send(S_USER_INFO, b.complete(out))
