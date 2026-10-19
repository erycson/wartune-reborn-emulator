"""Guilda: criar, buscar, informações, listas e textos (placa, descrição, nome)."""

from __future__ import annotations

from ....domain.models import (
    Consortia,
    ConsortiaEvent,
    ConsortiaMember,
)
from ....domain.repositories import UnitOfWork
from ....protocol.messages import wartune_pb2 as pb
from ....services.characters import normalize_nickname
from ... import guild as gd
from ... import rules
from ...builders import login as b
from ...builders.player import quest_update
from ...castle import castle_yield
from ...router import router
from ...session import GameSession
from .common import (
    CREATE_GOLD,
    MEMBER_CHUNK,
    MIN_GRADE,
    RENAME_POINTS,
    S_DUTIES,
    S_EVENTS,
    S_INFO,
    S_LINK,
    S_MEMBERS,
    S_QUESTS,
    S_RENAME,
    S_SEARCH,
    _can,
    _char,
    _clear_cooldown,
    _joined,
    _mine,
    _now,
    _player,
    _profile,
    _push_info,
    _refuse,
    _text,
)

# ---- criar / buscar / informações ------------------------------------------------------------


@router.on(5130)
async def create(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    c = _char(s)
    g = s.ctx.guilds
    try:
        name = normalize_nickname(msg.consortiaName)
    except Exception:
        _refuse(s, 5130, "nome inválido", nome=msg.consortiaName)
        return
    if _mine(s) is not None or c.grades < MIN_GRADE or c.gold < CREATE_GOLD or g.name_taken(name):
        _refuse(s, 5130, "sem requisitos ou nome em uso", nome=name)
        return
    if not _clear_cooldown(s, msg.isPay):
        _refuse(s, 5130, "espera de 24 h")
        return
    now = _now(s)
    c.gold -= CREATE_GOLD
    snap = s.snapshot
    assert snap is not None
    quests = rules.quest_event(snap, s.ctx.templates, rules.GUILD_JOIN_CONDITION, 0, 1)  # missão 22: criar
    guild = Consortia(c.server_id, name, s.player_id, c.nickname or "", s.player_id, now)
    member = ConsortiaMember(0, s.player_id, now, duty_id=gd.CHAIRMAN)
    # texto deduzido (sem fonte no cliente/captura)
    event = ConsortiaEvent(0, now, f"{c.nickname} founded the guild."[:255])
    gone = g.invites_of(s.player_id)
    # tira as candidaturas da memória antes do await: outra guilda não aceita (5134) no meio da criação
    g.invites = [i for i in g.invites if i.user_id != s.player_id]

    async def change(uow: UnitOfWork) -> None:
        # uma transação: guilda, membro, evento e as candidaturas dele (o membro precisa do id da guilda)
        await uow.save(c)
        await uow.save(guild)
        await uow.flush()
        member.consortia_id = event.consortia_id = guild.id or 0
        await uow.save(member)
        await uow.save(event)
        for q in quests:
            await uow.save(q)
        for invite in gone:
            await uow.delete(invite)

    g.reserved.add(name.lower())
    try:
        await s.ctx.characters.write(change)
    finally:
        g.reserved.discard(name.lower())
    gid = guild.id or 0
    g.guilds[gid] = guild
    g.members[s.player_id] = member
    g.events[gid].append(event)
    g.profiles[s.player_id] = c
    castle_yield(s)
    _joined(s, guild, s.player_id)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(8213)
async def search(s: GameSession, msg: pb.SearchConditionMsg) -> None:
    """Busca por nome (ou todas) em páginas de 8; página além do fim volta à 1 com ``isReset``."""
    g = s.ctx.guilds
    key = _text(msg.consortiaName).lower()
    found = sorted(
        (x for x in g.guilds.values() if key in x.name.lower()),
        key=lambda x: (-x.levels, -len(g.members_of(x.id or 0)), x.id or 0),
    )
    page = max(msg.pageIndex, 1)
    reset = (page - 1) * gd.PAGE >= len(found) and page > 1
    if reset:
        page = 1
    now = _now(s)
    out = pb.ConsortiaSearchRspMsg(totalRows=len(found), isReset=reset)
    for x in found[(page - 1) * gd.PAGE : page * gd.PAGE]:
        out.consortiaInfo.append(gd.info_msg(g, x, now))
    s.send(S_SEARCH, b.complete(out))


@router.on(8212)
async def info(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    mine = _mine(s)
    guild = s.ctx.guilds.guilds.get(msg.consortiaId) or (mine[0] if mine else None)
    if guild is None:
        _refuse(s, 8212, "guilda não existe", guilda=msg.consortiaId)
        return
    s.send(S_INFO, b.complete(gd.info_msg(s.ctx.guilds, guild, _now(s))))


@router.on(8343)
async def link(s: GameSession, msg: pb.ConsortiaLinkReqMsg) -> None:
    """Link de guilda no chat: o cliente abre a janela de informações com o 4267."""
    g = s.ctx.guilds
    guild = g.guilds.get(msg.consortiaId)
    if guild is None:
        _refuse(s, 8343, "guilda não existe", guilda=msg.consortiaId)
        return
    out = pb.ConsortiaLinkRspMsg(
        consortiaId=guild.id,
        consortiaName=guild.name,
        creatorName=guild.creator_name,
        levels=guild.levels,
        offer=guild.offer,
        currentCount=len(g.members_of(guild.id or 0)),
        honor=0,
        description=guild.description,
    )
    s.send(S_LINK, b.complete(out))


@router.on(8211)
async def duty_list(s: GameSession, _: object) -> None:
    out = pb.ConsortiaDutyListRspMsg()
    for duty in sorted(gd.RIGHTS, reverse=True):  # o oficial manda do 5 ao 1
        out.dutyInfo.add(levels=duty, dutyName="", rights=gd.RIGHTS[duty].ljust(gd.RIGHTS_LEN, b"\0"))
    s.send(S_DUTIES, b.complete(out))


@router.on(8207)
async def member_list(s: GameSession, _: object) -> None:
    mine = _mine(s)
    if mine is None:
        s.send(S_MEMBERS, b.complete(pb.SimplePlayerListRspMsg(totalRows=0, uuid=gd.new_uuid())))
        return
    guild = mine[0]
    rows = []
    for m in s.ctx.guilds.members_of(guild.id or 0):
        c = _profile(s, m.character_id)
        if c is None or not c.nickname:
            continue  # o cliente descarta quem vem sem apelido
        other = s.ctx.online.get(m.character_id)
        if other is not None and other.snapshot is not None and other.snapshot.leader is not None:
            c.fighting_capacity = rules.leader_stats(other.snapshot, s.ctx.templates).fighting_capacity
        rows.append(gd.member_msg(s.ctx.guilds, c, m, other is not None, guild))
    key = gd.new_uuid()
    for i in range(0, max(len(rows), 1), MEMBER_CHUNK):
        part = pb.SimplePlayerListRspMsg(totalRows=len(rows), uuid=key)
        part.playerInfo.extend(rows[i : i + MEMBER_CHUNK])
        s.send(S_MEMBERS, b.complete(part))


@router.on(8210)
async def event_list(s: GameSession, _: object) -> None:
    out = pb.ConsortiaEventListRspMsg()
    mine = _mine(s)
    for e in s.ctx.guilds.events.get(mine[0].id or 0, []) if mine else []:
        out.eventInfo.add(
            id=e.id or 0, consortiaId=e.consortia_id, remark=e.remark, createDate=b.fmt_time(e.created_at), type=e.type
        ).isExist = True
    s.send(S_EVENTS, b.complete(out))


# ---- textos ----------------------------------------------------------------------------------


async def _set_text(s: GameSession, code: int, right: int, attr: str, raw: str) -> None:
    mine = _can(s, right)
    if mine is None:
        _refuse(s, code, "sem direito")
        return
    setattr(mine[0], attr, _text(raw))
    await s.ctx.characters.save(mine[0])
    _push_info(s, mine[0])


@router.on(5139)
async def placard(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    await _set_text(s, 5139, gd.R_PLACARD, "placard", msg.placard)


@router.on(5140)
async def description(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    await _set_text(s, 5140, gd.R_DESCRIPTION, "description", msg.description)


@router.on(8544)
async def group_placard(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    await _set_text(s, 8544, gd.R_PLACARD, "group_placard", msg.groupPlacard)


@router.on(5148)
async def rename(s: GameSession, msg: pb.ConsortiaRenameReqMsg) -> None:
    """Renomear (direito 18): 1000 diamantes; ``payType`` 0 aceita os vinculados primeiro.

    ponytail: o ``same`` (renomear grátis depois de juntar servidores) é cobrado igual.
    """
    g = s.ctx.guilds
    mine = _can(s, gd.R_RENAME)
    try:
        name = normalize_nickname(msg.newName)
    except Exception:
        name = ""
    c = _char(s)
    ok = mine is not None and name and not g.name_taken(name) and gd.pay_points(c, RENAME_POINTS, msg.payType == 0)
    if not ok or mine is None:
        _refuse(s, 5148, "sem direito, nome inválido/em uso ou sem diamantes", nome=msg.newName)
        s.send(S_RENAME, b.complete(pb.ConsortiaRenameRspMsg(result=False)))
        return
    mine[0].name = name
    await s.ctx.characters.save(c, mine[0])
    s.send(S_RENAME, b.complete(pb.ConsortiaRenameRspMsg(result=True)))
    _player(s)
    _push_info(s, mine[0])
    for o in gd.online_members(s.ctx, mine[0].id or 0):
        if o is not s:
            _player(o)  # o nome da guilda vai no PlayerMsg
