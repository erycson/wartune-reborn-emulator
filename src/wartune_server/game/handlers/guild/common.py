"""Constantes e ajudantes da guilda, usados pelos outros módulos do pacote."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from ....domain import gameday
from ....domain.models import (
    Character,
    Consortia,
    ConsortiaMember,
)
from ....protocol.messages import wartune_pb2 as pb
from ....services import ledger
from ... import guild as gd
from ... import social
from ...builders import login as b
from ...session import GameSession
from ..login import army, player_info

S_PLAYER, S_CHAT, S_ALERT, S_ITEMS, S_ARMY = 3, 83, 111, 115, 150
S_JOINED, S_APPLY_DEL, S_INVITE_RESULT, S_PASS, S_INVITED, S_OFFER, S_BLESS = 35, 36, 37, 40, 41, 42, 45
S_RENAME, S_DUTY, S_STATE, S_INFO_PUSH = 49, 50, 117, 164
S_MEMBERS, S_OFFERS, S_INVITES, S_EVENTS, S_DUTIES, S_INFO = 4133, 4134, 4135, 4136, 4137, 4138
S_SEARCH, S_RECRUIT, S_ALTAR_INFO, S_ALTAR_ITEM, S_ADDFRESH, S_SITE = 4139, 4140, 4141, 4142, 4143, 4144
S_NEW_APPLY, S_LINK, S_VOTERS, S_VOTED, S_BOX_ALLOT, S_BOX = 4266, 4267, 4389, 4390, 4465, 4466
S_SHOP_BUY = 90
S_QUESTS = 112  # QuestUpdatedRspMsg

MIN_GRADE = 12  # CreatConsortiaFrame / ConsortiaSocektSendManager.checkApply
CREATE_GOLD = 200000  # CreatConsortiaFrame.command05
MAX_APPLICATIONS = 10
QUIT_COOLDOWN = timedelta(hours=24)
CD_CARD = 208013  # cartão que limpa a espera ao sair (ConsortiaStaffPage.exitCallback)
RENAME_POINTS = 1000  # ConsortiaRenameFrame.command01
# contribuição: 1000 ouro = 1, 5 Balens = 1 (ConsortiaContributeFrame inglês: ``/ 1000``, ``/ 5``, command05/06)
GOLD_PER_OFFER, POINTS_PER_OFFER = 1000, 5
QUICK_SECONDS = 600  # acelerar a melhoria: 1 diamante a cada 10 min (ConsortiaUpgradeFrame)
GUILD_SHOP = "2"  # ShopTempInfos.ShopType do mercado da guilda
# BuyInfo.result (ShopManager.shopingResult, como em handlers/shop.py)
R_OK, R_NO_PLAYER, R_NO_ITEM, R_NO_MONEY, R_LIMIT, R_GUILD, R_LEVEL, R_FAIL = 1, 2, 3, 4, 6, 9, 10, 11
TEXT_MAX = 200  # maxChars da placa, descrição e aviso (cliente inglês)
MEMBER_CHUNK = 100  # 4133 em pedaços (o cliente junta pelo uuid até somar totalRows)
_TAG = re.compile(r"<[^>]*>")


def _mine(s: GameSession) -> tuple[Consortia, ConsortiaMember] | None:
    return s.ctx.guilds.of(s.player_id)


def _now(s: GameSession) -> datetime:
    return s.ctx.clock.now()


def _day(now: datetime) -> str:
    return gameday.today(now)


def _char(s: GameSession) -> Character:
    assert s.snapshot is not None
    return s.snapshot.character


def _profile(s: GameSession, player_id: int) -> Character | None:
    other = s.ctx.online.get(player_id)
    if other is not None and other.snapshot is not None:
        return other.snapshot.character
    return s.ctx.guilds.profiles.get(player_id)


def _text(raw: str) -> str:
    return _TAG.sub("", raw).strip()[:TEXT_MAX]


def _player(o: GameSession) -> None:
    assert o.snapshot is not None
    o.send(S_PLAYER, b.complete(player_info(o, o.snapshot)))


def _alert(s: GameSession, text: str) -> None:
    s.send(S_ALERT, b.complete(pb.ChatChannelMsg(channel=7, encodeMsg=text)))


def _push_info(s: GameSession, guild: Consortia) -> None:
    """164 para os membros online (o cliente recarrega a lista quando ``currentCount`` muda)."""
    msg = gd.info_msg(s.ctx.guilds, guild, _now(s), s.ctx.templates)
    for o in gd.online_members(s.ctx, guild.id or 0):
        o.send(S_INFO_PUSH, msg)


def _refuse(s: GameSession, code: int, why: str, **extra: object) -> None:
    s.log.info("guilda: pedido recusado", code=code, motivo=why, **extra)


def _can(s: GameSession, right: int) -> tuple[Consortia, ConsortiaMember] | None:
    mine = _mine(s)
    return mine if mine is not None and gd.has_right(mine[1].duty_id, right) else None


def _join(
    s: GameSession, guild: Consortia, player_id: int, duty: int = gd.MEMBER
) -> tuple[ConsortiaMember, list[object]]:
    """Coloca o jogador na guilda (memória); devolve o membro e as candidaturas dele para apagar."""
    g = s.ctx.guilds
    member = ConsortiaMember(guild.id or 0, player_id, _now(s), duty_id=duty)
    g.members[player_id] = member
    gone: list[object] = list(g.invites_of(player_id))
    g.invites = [i for i in g.invites if i.user_id != player_id]
    if (c := _profile(s, player_id)) is not None:
        g.profiles[player_id] = c
    return member, gone


def _joined(s: GameSession, guild: Consortia, player_id: int, welcome: bool = True) -> None:
    """Avisa quem entrou e os membros. (visto) oficial_20261023-171155-1 #4561-#4567: a quem entrou 3, 150, 117,
    111 "Congratulations! You have joined Guild  [nome]." (dois espaços) e 4266 vazio; a todos os membros online o
    83 do canal 5 (type 5) "<link> has just become the guilds newest member!"; e o 164. O cliente pede 8211/8207/8212.
    ``welcome=False`` (quem criou a guilda): só 3, 150, 117 e 164 (dedução: sem captura da criação em inglês).
    """
    other = s.ctx.online.get(player_id)
    joiner = other.snapshot.character if other is not None and other.snapshot is not None else _profile(s, player_id)
    if other is not None and other.snapshot is not None:
        _player(other)
        other.send(S_ARMY, b.complete(army(other, other.snapshot)[0]))
        other.send(S_STATE, b.complete(pb.ConsortiaMsg(consortiaId=guild.id)))
        if welcome:
            _alert(other, f"Congratulations! You have joined Guild  [{guild.name}].")
            other.send(S_NEW_APPLY)
    if joiner is not None and welcome:
        text = f"{social.player_link(s.ctx, joiner)} has just become the guilds newest member!"
        msg = b.complete(pb.ChatChannelMsg(channel=5, type=5, encodeMsg=text, otherId=-1, userType=1))
        for o in gd.online_members(s.ctx, guild.id or 0):
            o.send(S_CHAT, msg)
    _push_info(s, guild)


def _left(s: GameSession, player_id: int, guild: Consortia | None) -> None:
    other = s.ctx.online.get(player_id)
    if other is not None and other.snapshot is not None:
        other.send(S_STATE, b.complete(pb.ConsortiaMsg(consortiaId=0)))
        _player(other)
    if guild is not None and guild.id in s.ctx.guilds.guilds:
        _push_info(s, guild)


def _event(s: GameSession, guild: Consortia, kind: int, *parts: str) -> object:
    return s.ctx.guilds.add_event(guild.id or 0, _now(s), kind, *parts)


def _in_cooldown(c: Character, now: datetime) -> bool:
    return c.is_auto and c.last_out_consortia is not None and now - c.last_out_consortia < QUIT_COOLDOWN


def _clear_cooldown(s: GameSession, is_pay: bool) -> list[object] | None:
    """Espera de 24 h depois de sair: com ``isPay`` paga ``Consortia_ClearCD_Point`` e entra já.

    None = ainda esperando; senão o que gravar junto (a linha do ledger, se pagou)."""
    c, now = _char(s), _now(s)
    if not _in_cooldown(c, now):
        return []
    cost = gd.config(s.ctx.templates, "Consortia_ClearCD_Point", 50)
    entry = ledger.pay(c, cost, bind=False, reason="guild_clear_cd", ref="join", now=now) if is_pay else None
    if entry is None:
        return None
    c.is_auto = False
    return [entry]
