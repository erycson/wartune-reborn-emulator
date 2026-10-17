"""Guilda (consortia): criar, entrar, sair, cargos, textos, listas, contribuição, melhorias,
habilidades, mercado, bênção do altar, baú e eleição. Estado em ``game/guild.py``; fluxo e fontes
em docs/guilda.md. As atividades (altar do demônio, terra secreta, guerra) ficam em
``guild_events.py``.
"""

from __future__ import annotations

import math
import random
import re
from datetime import datetime, timedelta

from ...domain.models import BagType, Character, Consortia, ConsortiaInvite, ConsortiaItem, ConsortiaMember, Item
from ...protocol.messages import wartune_pb2 as pb
from ...services.characters import normalize_nickname
from .. import guild as gd
from .. import rules
from ..bag import BAG_BASE as BAG_SIZE  # ponytail: só os 42 base; espaços comprados/alugados via bag.capacity(c, now)
from ..builders import login as b
from ..builders.player import item_moved
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .login import army, player_info

S_PLAYER, S_CHAT, S_ALERT, S_ITEMS, S_ARMY = 3, 83, 111, 115, 150
S_JOINED, S_APPLY_DEL, S_INVITE_RESULT, S_PASS, S_INVITED, S_OFFER, S_BLESS = 35, 36, 37, 40, 41, 42, 45
S_RENAME, S_DUTY, S_STATE, S_INFO_PUSH = 49, 50, 117, 164
S_MEMBERS, S_OFFERS, S_INVITES, S_EVENTS, S_DUTIES, S_INFO = 4133, 4134, 4135, 4136, 4137, 4138
S_SEARCH, S_RECRUIT, S_ALTAR_INFO, S_ALTAR_ITEM, S_ADDFRESH, S_SITE = 4139, 4140, 4141, 4142, 4143, 4144
S_NEW_APPLY, S_LINK, S_VOTERS, S_VOTED, S_BOX_ALLOT, S_BOX = 4266, 4267, 4389, 4390, 4465, 4466
S_SHOP_BUY = 90

MIN_GRADE = 12  # CreatConsortiaFrame / ConsortiaSocektSendManager.checkApply
CREATE_GOLD = 200000  # CreatConsortiaFrame.command05
MAX_APPLICATIONS = 10
QUIT_COOLDOWN = timedelta(hours=24)
CD_CARD = 208013  # cartão que limpa a espera ao sair (ConsortiaStaffPage.exitCallback)
RENAME_POINTS = 1000  # ConsortiaRenameFrame.command01
GOLD_PER_OFFER = 1000  # contribuição: 1000 ouro = 1, 1 diamante = 1 (ConsortiaContributeFrame)
QUICK_SECONDS = 600  # acelerar a melhoria: 1 diamante a cada 10 min (ConsortiaUpgradeFrame)
GUILD_SHOP = "2"  # ShopTempInfos.ShopType do mercado da guilda
# BuyInfo.result (ShopManager.shopingResult, como em handlers/shop.py)
R_OK, R_NO_PLAYER, R_NO_ITEM, R_NO_MONEY, R_GUILD, R_LEVEL, R_FAIL = 1, 2, 3, 4, 9, 10, 11
TEXT_MAX = 255
MEMBER_CHUNK = 100  # 4133 em pedaços (o cliente junta pelo uuid até somar totalRows)
_TAG = re.compile(r"<[^>]*>")


def _mine(s: GameSession) -> tuple[Consortia, ConsortiaMember] | None:
    return s.ctx.guilds.of(s.player_id)


def _now(s: GameSession) -> datetime:
    return s.ctx.clock.now()


def _day(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


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
    msg = gd.info_msg(s.ctx.guilds, guild, _now(s))
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


def _joined(s: GameSession, guild: Consortia, player_id: int) -> None:
    """Avisa quem entrou (117 + 3; o cliente pede 8211/8207/8212) e os membros (164)."""
    other = s.ctx.online.get(player_id)
    if other is not None and other.snapshot is not None:
        other.send(S_STATE, b.complete(pb.ConsortiaMsg(consortiaId=guild.id)))
        _player(other)
    _push_info(s, guild)


def _left(s: GameSession, player_id: int, guild: Consortia | None) -> None:
    other = s.ctx.online.get(player_id)
    if other is not None and other.snapshot is not None:
        other.send(S_STATE, b.complete(pb.ConsortiaMsg(consortiaId=0)))
        _player(other)
    if guild is not None and guild.id in s.ctx.guilds.guilds:
        _push_info(s, guild)


def _event(s: GameSession, guild: Consortia, remark: str) -> object:
    return s.ctx.guilds.add_event(guild.id or 0, _now(s), remark)


def _in_cooldown(c: Character, now: datetime) -> bool:
    return c.is_auto and c.last_out_consortia is not None and now - c.last_out_consortia < QUIT_COOLDOWN


def _clear_cooldown(s: GameSession, is_pay: bool) -> bool:
    """Espera de 24 h depois de sair: com ``isPay`` paga ``Consortia_ClearCD_Point`` e entra já."""
    c = _char(s)
    if not _in_cooldown(c, _now(s)):
        return True
    if not is_pay or not gd.pay_points(c, gd.config(s.ctx.templates, "Consortia_ClearCD_Point", 50), False):
        return False
    c.is_auto = False
    return True


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
    guild = Consortia(c.server_id, name, s.player_id, c.nickname or "", s.player_id, now)
    g.reserved.add(name.lower())
    try:
        await s.ctx.characters.save(c, guild)  # o id da guilda sai daqui
    finally:
        g.reserved.discard(name.lower())
    g.guilds[guild.id or 0] = guild
    # ponytail: duas transações (o membro precisa do id da guilda); se a segunda falhar fica uma
    # guilda sem membros e o ouro gasto. Uma só quando o mapeamento tiver relação guilda->membro.
    member, gone = _join(s, guild, s.player_id, gd.CHAIRMAN)
    event = _event(s, guild, f"{c.nickname} birliği kurdu.")
    await s.ctx.characters.save(member, event, delete=tuple(gone))
    castle_yield(s)
    _joined(s, guild, s.player_id)


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


# ---- candidaturas e convites -----------------------------------------------------------------


def _invite_msg(s: GameSession, i: ConsortiaInvite) -> pb.ConsortiaUserInviteInfoMsg:
    g = s.ctx.guilds
    guild = g.guilds.get(i.consortia_id)
    user, inviter = _profile(s, i.user_id), _profile(s, i.invite_id)
    chairman = _profile(s, guild.chairman_id) if guild else None
    return pb.ConsortiaUserInviteInfoMsg(
        id=i.id,
        consortiaId=i.consortia_id,
        consortiaName=guild.name if guild else "",
        createDate=b.fmt_time(guild.created_at) if guild else b.NEVER,
        userId=i.user_id,
        userNickname=(user.nickname or "") if user else "",
        inviteId=i.invite_id,
        inviteNickname=(inviter.nickname or "") if inviter else "",
        chairmanNickname=(chairman.nickname or "") if chairman else "",
        inviteDate=b.fmt_time(i.created_at),
        fromType=i.from_type,
        isexist=True,
    )


@router.on(8209)
async def invite_list(s: GameSession, _: object) -> None:
    """Candidaturas do jogador (``fromType`` falso) e convites recebidos (verdadeiro)."""
    out = pb.ConsortiaUserInviteInfoListRspMsg()
    for i in s.ctx.guilds.invites_of(s.player_id):
        out.inviteInfo.append(_invite_msg(s, i))
    s.send(S_INVITES, b.complete(out))


def _notify_recruiters(s: GameSession, guild: Consortia) -> None:
    for o in gd.online_members(s.ctx, guild.id or 0):
        mine = o.ctx.guilds.of(o.player_id)
        if mine is not None and gd.has_right(mine[1].duty_id, gd.R_RECRUIT):
            o.send(S_NEW_APPLY)  # o botão da guilda pisca


@router.on(5135)
async def apply(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    g = s.ctx.guilds
    c = _char(s)
    guild = g.guilds.get(msg.consortiaId)
    mine_apps = [i for i in g.invites_of(s.player_id) if not i.from_type]
    if guild is None or _mine(s) is not None or c.grades < MIN_GRADE or not guild.open_app:
        _refuse(s, 5135, "guilda fechada ou jogador sem requisitos", guilda=msg.consortiaId)
        return
    if len(mine_apps) >= MAX_APPLICATIONS or any(i.consortia_id == guild.id for i in mine_apps):
        _refuse(s, 5135, "candidaturas demais ou repetida")
        return
    if not _clear_cooldown(s, msg.isPay):
        _refuse(s, 5135, "espera de 24 h")
        return
    app = ConsortiaInvite(guild.id or 0, s.player_id, _now(s))
    g.invites.append(app)
    await s.ctx.characters.save(c, app)
    if msg.isPay:
        _player(s)
    s.send(S_JOINED, b.complete(pb.ConsortiaMsg(applyId=app.id)))
    _notify_recruiters(s, guild)


@router.on(5141)
async def apply_delete(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    g = s.ctx.guilds
    app = g.invite(msg.applyId)
    if app is None or app.user_id != s.player_id:
        _refuse(s, 5141, "candidatura de outro", candidatura=msg.applyId)
        return
    g.invites.remove(app)
    await s.ctx.characters.save(delete=(app,))
    s.send(S_APPLY_DEL)


@router.on(8214)
async def recruit_list(s: GameSession, msg: pb.SearchConditionMsg) -> None:
    """Candidatos à guilda; ``parameter1`` é o id da candidatura que o 5134 devolve."""
    mine = _mine(s)
    apps = s.ctx.guilds.applications(mine[0].id or 0) if mine else []
    page = max(msg.pageIndex, 1)
    out = pb.SimplePlayerListRspMsg(totalRows=len(apps), uuid=gd.new_uuid())
    for a in apps[(page - 1) * gd.PAGE : page * gd.PAGE]:
        c = _profile(s, a.user_id)
        if c is not None:
            row = gd.member_msg(s.ctx.guilds, c, None, s.ctx.online.get(a.user_id) is not None, None)
            row.parameter1 = a.id or 0
            out.playerInfo.append(row)
    s.send(S_RECRUIT, b.complete(out))


@router.on(5134)
async def apply_answer(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Aceitar (direito 9) ou recusar (33) uma candidatura."""
    g = s.ctx.guilds
    mine = _can(s, gd.R_RECRUIT if msg.result else gd.R_REJECT)
    app = g.invite(msg.applyId)
    if mine is None or app is None or app.from_type or app.consortia_id != mine[0].id:
        _refuse(s, 5134, "sem direito ou candidatura de outra guilda", candidatura=msg.applyId)
        return
    guild = mine[0]
    if not msg.result:
        g.invites.remove(app)
        await s.ctx.characters.save(delete=(app,))
        s.send(S_PASS)
        return
    if g.of(app.user_id) is not None or len(g.members_of(guild.id or 0)) >= gd.max_members(guild):
        _refuse(s, 5134, "candidato já tem guilda ou guilda cheia")
        return
    member, gone = _join(s, guild, app.user_id)
    who = _profile(s, app.user_id)
    event = _event(s, guild, f"{who.nickname if who else app.user_id} birliğe katıldı.")
    await s.ctx.characters.save(member, event, delete=tuple(gone))
    s.send(S_PASS)
    _joined(s, guild, app.user_id)


@router.on(5149)
async def open_app(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    mine = _can(s, gd.R_RECRUIT)
    if mine is None:
        _refuse(s, 5149, "sem direito")
        return
    mine[0].open_app = msg.result
    await s.ctx.characters.save(mine[0])
    _push_info(s, mine[0])


@router.on(5142)
async def invite(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Convida alguém sem guilda; se estiver online recebe o 41 e o cliente mostra o convite."""
    g = s.ctx.guilds
    mine = _can(s, gd.R_INVITE)
    target = _profile(s, msg.otherId) or next(iter(await s.ctx.characters.characters([msg.otherId])), None)
    if mine is None or target is None or not target.active or g.of(msg.otherId) is not None:
        _refuse(s, 5142, "sem direito ou alvo já em guilda", alvo=msg.otherId)
        return
    if any(i.consortia_id == mine[0].id and i.from_type for i in g.invites_of(msg.otherId)):
        return  # já convidado
    g.profiles.setdefault(msg.otherId, target)
    inv = ConsortiaInvite(mine[0].id or 0, msg.otherId, _now(s), invite_id=s.player_id, from_type=True)
    g.invites.append(inv)
    await s.ctx.characters.save(inv)
    other = s.ctx.online.get(msg.otherId)
    if other is not None:
        other.send(S_INVITED, b.complete(pb.ConsortiaMsg(applyId=inv.id)))


@router.on(8197)
async def robot_join(s: GameSession, _: object) -> None:
    """Nível 15 sem guilda: o cliente pede um convite automático.

    ponytail: o oficial tinha guildas-robô; aqui vem o convite da guilda aberta com mais membros
    que tenha vaga.
    """
    g = s.ctx.guilds
    if g.of(s.player_id) is not None or g.invites_of(s.player_id):
        return
    open_ = [x for x in g.guilds.values() if x.open_app and len(g.members_of(x.id or 0)) < gd.max_members(x)]
    if not open_:
        return
    guild = max(open_, key=lambda x: (len(g.members_of(x.id or 0)), -(x.id or 0)))
    inv = ConsortiaInvite(guild.id or 0, s.player_id, _now(s), invite_id=guild.chairman_id, from_type=True)
    g.invites.append(inv)
    await s.ctx.characters.save(inv)
    s.send(S_INVITED, b.complete(pb.ConsortiaMsg(applyId=inv.id)))


@router.on(5143)
async def invite_answer(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    g = s.ctx.guilds
    inv = g.invite(msg.applyId)
    guild = g.guilds.get(inv.consortia_id) if inv else None
    if inv is None or guild is None or inv.user_id != s.player_id or not inv.from_type:
        _refuse(s, 5143, "convite inexistente", convite=msg.applyId)
        return
    # o cliente mostra "entrou em X" procurando o convite na lista: o 37 vai antes de apagar
    s.send(S_INVITE_RESULT, b.complete(pb.ConsortiaMsg(result=msg.result, applyId=inv.id)))
    full = len(g.members_of(guild.id or 0)) >= gd.max_members(guild)
    if not msg.result or _mine(s) is not None or full or not _clear_cooldown(s, False):
        g.invites.remove(inv)
        await s.ctx.characters.save(delete=(inv,))
        return
    member, gone = _join(s, guild, s.player_id)
    event = _event(s, guild, f"{_char(s).nickname} birliğe katıldı.")
    await s.ctx.characters.save(member, event, delete=tuple(gone))
    _joined(s, guild, s.player_id)


# ---- sair / expulsar / cargos ----------------------------------------------------------------


@router.on(5146)
async def quit_(s: GameSession, msg: pb.ConsortiaQuitReqMsg) -> None:
    """Sair. O chefe só sai sozinho (a guilda acaba). ``clear_CDType`` 1 paga para não esperar
    24 h: cartão 208013 ou 50 diamantes."""
    g = s.ctx.guilds
    mine = _mine(s)
    if mine is None:
        return
    guild, member = mine
    alone = len(g.members_of(guild.id or 0)) == 1
    if member.duty_id == gd.CHAIRMAN and not alone:
        _refuse(s, 5146, "chefe com membros")
        return
    snap, c, now = s.snapshot, _char(s), _now(s)
    assert snap is not None
    gone: list[object] = []
    card = next((i for i in snap.items if i.template_id == CD_CARD and i.bag_type == BagType.BAG), None)
    paid = msg.clear_CDType == 1 and (card is not None or gd.pay_points(c, 50, False))
    if paid and card is not None:
        card.count -= 1
        if card.count <= 0:
            snap.items.remove(card)
            gone.append(card)
    c.is_auto, c.last_out_consortia = not paid, now
    if alone:
        gone += g.drop_guild(guild.id or 0)
        changed: list[object] = [c]
    else:
        del g.members[s.player_id]
        gone.append(member)
        changed = [c, _event(s, guild, f"{c.nickname} birlikten ayrıldı.")]
    if card is not None and card.count > 0:
        changed.append(card)
    await s.ctx.characters.save(*changed, delete=tuple(gone))
    if card is not None and paid:
        s.send(S_ITEMS, item_moved(card.bag_type, 0, card.pos, card if card.count > 0 else None, s.player_id))
    _left(s, s.player_id, None if alone else guild)


@router.on(5132)
async def kick(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    g = s.ctx.guilds
    mine = _can(s, gd.R_KICK)
    target = g.members.get(msg.otherId)
    if mine is None or target is None or target.consortia_id != mine[0].id or target.duty_id <= mine[1].duty_id:
        _refuse(s, 5132, "sem direito ou cargo maior", alvo=msg.otherId)
        return
    guild = mine[0]
    del g.members[msg.otherId]
    guild.kick_count += 1
    guild.kick_at = _now(s)
    who = _profile(s, msg.otherId)
    event = _event(s, guild, f"{who.nickname if who else msg.otherId} birlikten çıkarıldı.")
    await s.ctx.characters.save(guild, event, delete=(target,))
    _left(s, msg.otherId, guild)


@router.on(5131)
async def transfer(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Passa a chefia: o novo vira 1, o antigo vira 5 (como o ``refreshChairman`` do cliente)."""
    g = s.ctx.guilds
    mine = _mine(s)
    target = g.members.get(msg.otherId)
    if mine is None or mine[1].duty_id != gd.CHAIRMAN or target is None or target.consortia_id != mine[0].id:
        _refuse(s, 5131, "não é chefe ou alvo de fora", alvo=msg.otherId)
        return
    guild, me = mine
    if target is me:
        return
    target.duty_id, me.duty_id, guild.chairman_id = gd.CHAIRMAN, gd.MEMBER, msg.otherId
    who = _profile(s, msg.otherId)
    event = _event(s, guild, f"Birlik başkanlığı {who.nickname if who else msg.otherId} oyuncusuna devredildi.")
    await s.ctx.characters.save(guild, target, me, event)
    _push_info(s, guild)


@router.on(5137)
async def duty_update(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Promover/rebaixar: só abaixo do próprio cargo e nunca para chefe."""
    g = s.ctx.guilds
    mine = _can(s, gd.R_DUTY)
    target = g.members.get(msg.otherId)
    ok = mine is not None and target is not None and target.consortia_id == mine[0].id
    if not ok or not gd.VICE <= msg.positionId <= gd.MEMBER:
        _refuse(s, 5137, "sem direito ou cargo inválido", alvo=msg.otherId, cargo=msg.positionId)
        return
    assert mine is not None and target is not None
    if not mine[1].duty_id < target.duty_id or not mine[1].duty_id < msg.positionId:
        _refuse(s, 5137, "cargo maior que o próprio", alvo=msg.otherId)
        return
    target.duty_id = msg.positionId
    await s.ctx.characters.save(target)
    out = pb.ConsortiaMsg(otherId=msg.otherId, positionId=msg.positionId)
    for o in gd.online_members(s.ctx, mine[0].id or 0):
        o.send(S_DUTY, b.complete(out))


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


# ---- contribuição e melhorias ----------------------------------------------------------------


def _today(m: ConsortiaMember, now: datetime) -> int:
    return m.today_offer if m.offer_day == _day(now) else 0


@router.on(5144)
async def contribute(s: GameSession, msg: pb.ConsortiaUserOfferReqMsg) -> None:
    """Doação: 1000 ouro (arredondado para baixo) ou 1 diamante = 1 de contribuição, para a
    riqueza da guilda e para o jogador. Ordem do oficial: 109, 3, 111, 42, 164."""
    mine = _mine(s)
    c = _char(s)
    gold = max(msg.offerGold, 0) // GOLD_PER_OFFER * GOLD_PER_OFFER
    points = max(msg.offerPoint, 0)
    if mine is None or gold + points == 0 or c.gold < gold or c.point + c.gift_token < points:
        _refuse(s, 5144, "sem guilda ou sem recursos", ouro=msg.offerGold, diamantes=msg.offerPoint)
        return
    guild, member = mine
    now = _now(s)
    # ponytail: não se sabe se o oficial aceita diamante vinculado aqui; gasta primeiro o vinculado
    gd.pay_points(c, points, True)
    c.gold -= gold
    offer = gold // GOLD_PER_OFFER + points
    c.consortia_offer += offer
    c.consortia_total_offer += offer
    guild.offer += offer
    guild.total_offer += offer
    member.today_offer, member.offer_day = _today(member, now) + offer, _day(now)
    await s.ctx.characters.save(c, guild, member)
    if gold:
        castle_yield(s)
    _player(s)
    _alert(s, "Başarıyla katkı yapıldı!")
    s.send(S_OFFER, b.complete(pb.ConsortiaMsg(result=True)))
    _push_info(s, guild)


@router.on(8208)
async def offer_list(s: GameSession, msg: pb.ConsortiaOfferReqMsg) -> None:
    """Ranking de contribuição (de hoje, ou total com ``isHistory``), 8 por página."""
    mine = _mine(s)
    out = pb.ConsortiaContributeRspMsg(totalRows=0)
    now = _now(s)
    rows = []
    for m in s.ctx.guilds.members_of(mine[0].id or 0) if mine else []:
        c = _profile(s, m.character_id)
        if c is not None:
            rows.append((c.nickname or "", c.consortia_total_offer, _today(m, now), m.character_id))
    rows.sort(key=lambda r: (-(r[1] if msg.isHistory else r[2]), -r[1], r[3]))
    page = max(msg.pageIndex, 1)
    out.totalRows = len(rows)
    for nick, total, today, _ in rows[(page - 1) * gd.PAGE : page * gd.PAGE]:
        out.contributeInfo.add(nickName=nick, totalOffer=total, todayOffer=today)
    me = next((i for i, r in enumerate(rows) if r[3] == s.player_id), None)
    if me is not None:
        out.selfInfo.CopyFrom(
            pb.ConsortiaContributeMsg(nickName=rows[me][0], totalOffer=rows[me][1], todayOffer=rows[me][2])
        )
        out.selfOrder = me + 1
    s.send(S_OFFERS, b.complete(out))


def _cooldown_left(guild: Consortia, now: datetime) -> int:
    if guild.code_begin_at is None:
        return 0
    return max(0, guild.code_need - int((now - guild.code_begin_at).total_seconds()))


@router.on(5133)
async def upgrade(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Melhoria da guilda (tipos 1-5, direito 3) ou pesquisa de habilidade (6-12, direito 2),
    paga com a riqueza. O nível sobe já; ``CodeTime`` só trava a próxima melhoria de prédio."""
    kind = msg.upgradeType
    attr = gd.LEVEL_TYPES.get(kind)
    mine = _can(s, gd.R_UPGRADE if kind <= 5 else gd.R_RESEARCH)
    if attr is None or mine is None:
        _refuse(s, 5133, "tipo inválido ou sem direito", tipo=kind)
        return
    guild, now, templates = mine[0], _now(s), s.ctx.templates
    level = getattr(guild, attr) + 1
    row = gd.level_row(templates, kind, level)
    pre = templates.get("ConsortiaLevelInfos", int(row.get("PreTemplateId") or 0)) if row else None
    pre_ok = pre is None or getattr(guild, gd.LEVEL_TYPES[int(pre["Types"])]) >= int(pre["Levels"])
    need = int(row["NeedOffer"]) if row else 0
    busy = kind <= 5 and _cooldown_left(guild, now) > 0
    if row is None or level > gd.MAX_LEVEL or not pre_ok or guild.offer < need or busy:
        _refuse(s, 5133, "nível máximo, requisito, riqueza ou espera", tipo=kind, nivel=level)
        return
    setattr(guild, attr, level)
    guild.offer -= need
    if kind <= 5 and int(row.get("CodeTime") or 0) > 0:
        guild.code_type, guild.code_begin_at, guild.code_need = kind, now, int(row["CodeTime"])
    event = _event(s, guild, f"{row.get('LevelName', kind)} Lv.{level}")
    await s.ctx.characters.save(guild, event)
    _push_info(s, guild)


@router.on(8545)
async def quick(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Acaba a espera da melhoria: 1 diamante a cada 10 min que faltam (ConsortiaUpgradeFrame);
    ``payType`` 0 gasta os vinculados primeiro."""
    mine = _can(s, gd.R_UPGRADE)
    if mine is None:
        _refuse(s, 8545, "sem direito")
        return
    guild, c = mine[0], _char(s)
    left = _cooldown_left(guild, _now(s))
    if left <= 0 or not gd.pay_points(c, math.ceil(left / QUICK_SECONDS), msg.payType == 0):
        _refuse(s, 8545, "sem espera ou sem diamantes", falta=left)
        return
    guild.code_begin_at, guild.code_need = None, 0
    await s.ctx.characters.save(c, guild)
    _player(s)
    _push_info(s, guild)


@router.on(5147)
async def learn(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Aprende um nível de habilidade: gasta a contribuição pessoal (``NeedOffer`` do nível) e
    não passa da pesquisa da guilda daquele tipo."""
    attr = gd.SKILLS.get(msg.studySkill)
    mine = _mine(s)
    c = _char(s)
    if attr is None or mine is None:
        _refuse(s, 5147, "tipo inválido ou sem guilda", tipo=msg.studySkill)
        return
    level = getattr(c, attr) + 1
    row = gd.level_row(s.ctx.templates, msg.studySkill, level)
    researched = getattr(mine[0], gd.LEVEL_TYPES[msg.studySkill])
    if row is None or level > gd.MAX_LEVEL or researched < level or c.consortia_offer < int(row["NeedOffer"]):
        _refuse(s, 5147, "nível, pesquisa ou contribuição", tipo=msg.studySkill, nivel=level)
        return
    setattr(c, attr, level)
    c.consortia_offer -= int(row["NeedOffer"])
    await s.ctx.characters.save(c)
    _player(s)
    assert s.snapshot is not None
    s.send(S_ARMY, b.complete(army(s, s.snapshot)[0]))


def _buy_result(s: GameSession, buy: pb.BuyInfo, result: int) -> None:
    out = pb.BuyInfo(
        isDiscount=False, goodId=buy.goodId, count=buy.count, receiveId=s.player_id, result=result, type=buy.type
    )
    s.send(S_SHOP_BUY, b.complete(pb.ShopMsg(buyInfo=out)))


async def shop_buy(s: GameSession, buy: pb.BuyInfo) -> bool:
    """Compra no mercado da guilda (``ShopTempInfos.ShopType`` 2), paga com a contribuição pessoal.

    Não tem opcode próprio: o cliente usa a compra genérica 5154 (``ShopManager.sendShoping``), e o
    handler dele (``handlers/shop.py``) chama esta função primeiro. Devolve False se o ``goodId`` não
    é do mercado da guilda. Ordem do oficial: 3, 115, 111, 90, 83.
    """
    row = s.ctx.templates.get("ShopTempInfos", buy.goodId, key="Id")
    if row is None or row.get("ShopType") != GUILD_SHOP:
        return False
    snap, mine = s.snapshot, _mine(s)
    assert snap is not None
    c, count = snap.character, buy.count
    item_row = s.ctx.templates.get("ItemTempInfos", int(row["ItemId"]))
    price = int(row.get("ConsortiaOffer") or 0) * count
    stack = max(int(item_row.get("MaxCount") or 1), 1) if item_row else 1
    slots = math.ceil(count / stack) if count > 0 else 0
    used = sum(i.bag_type == BagType.BAG for i in snap.items)
    # o primeiro motivo que o cliente mostra (código 0 deixa a mensagem vazia)
    if mine is None or mine[0].shop_level < int(row.get("NeedConsortiaLevels") or 0):
        code = R_GUILD
    elif c.grades < int(row.get("NeedGrades") or 0):
        code = R_LEVEL
    elif buy.receiveId not in (0, s.player_id):  # presente exige gravar outro personagem
        code = R_NO_PLAYER
    elif item_row is None or not 0 < count <= 999:
        code = R_NO_ITEM
    elif c.consortia_offer < price:
        code = R_NO_MONEY
    elif used + slots > BAG_SIZE:
        code = R_FAIL
    else:
        code = R_OK
    if code != R_OK:
        _refuse(s, 5154, "mercado, nível, presente, quantidade, contribuição ou mochila", item=buy.goodId, codigo=code)
        _buy_result(s, buy, code)
        return True
    assert item_row is not None
    c.consortia_offer -= price
    new: list[Item] = []
    left = count
    while left > 0:
        item = Item(c.id or 0, int(row["ItemId"]), count=min(left, stack))
        item.pos = rules.free_bag_pos(snap)
        snap.items.append(item)
        new.append(item)
        left -= item.count
    await s.ctx.characters.save(c, *new)
    _player(s)
    moved = pb.ItemMovedListMsg()
    for item in new:
        moved.MergeFrom(item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
    s.send(S_ITEMS, moved)
    text = f"{item_row.get('TemplateName', row['ItemId'])} x{count} başarıyla alındı!"
    _alert(s, text)
    _buy_result(s, buy, 1)
    s.send(S_CHAT, b.complete(pb.ChatChannelMsg(channel=3, encodeMsg=text)))
    return True


# ---- bênção do altar -------------------------------------------------------------------------


def _bless_used(m: ConsortiaMember, now: datetime) -> int:
    return m.bless_count if m.bless_day == _day(now) else 0


def _sites(s: GameSession) -> list[int]:
    # DropViewInfos: as 10 casas da roleta (o cliente indexa os templates pelo Site)
    return [int(r["Site"]) for r in s.ctx.templates.rows("DropViewInfos")][:10]


@router.on(8215)
async def altar_info(s: GameSession, _: object) -> None:
    """4141 ``blessLeftTime`` = bênçãos já usadas hoje; 4142 o prêmio que falta pegar."""
    mine = _mine(s)
    s.send(S_ALTAR_INFO, b.complete(pb.ConsortiaMsg(blessLeftTime=_bless_used(mine[1], _now(s)) if mine else 0)))
    pending = s.ctx.guilds.blessed.get(s.player_id)
    if pending is not None:
        s.send(S_ALTAR_ITEM, b.complete(pb.ItemInfoMsg(templateId=pending[0], count=pending[1], userId=s.player_id)))


@router.on(8217)
async def altar_site(s: GameSession, _: object) -> None:
    s.send(S_SITE, b.complete(pb.ConsortiaInfoMsg(site=_sites(s))))


@router.on(5145)
async def bless(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Bênção: gasta ``Property1`` de contribuição, até ``Property2`` vezes por dia (nível do altar).
    ``blessSite`` é a posição na lista do 4144 (-1 = nada).

    ponytail: a tabela de prêmios do oficial não está nos templates; o prêmio é sempre um item
    do mercado da guilda liberado pelo nível do altar, na casa "Market Eşyası" (Site 1). A
    bênção rápida (``param1`` > 1, VIP 6) fica recusada: o custo e a quantidade do x10 estão só no m6.
    """
    g = s.ctx.guilds
    mine = _mine(s)
    c, now = _char(s), _now(s)
    used = _bless_used(mine[1], now) if mine else 0
    row = gd.level_row(s.ctx.templates, 3, mine[0].altar_level) if mine else None
    sites = _sites(s)
    pool = [
        r
        for r in s.ctx.templates.find("ShopTempInfos", ShopType=GUILD_SHOP)
        if mine is not None and int(r.get("NeedConsortiaLevels") or 0) <= mine[0].altar_level
    ]
    ok = mine is not None and row is not None and msg.param1 <= 1 and s.player_id not in g.blessed
    if (
        not ok
        or row is None
        or mine is None
        or used >= int(row["Property2"])
        or c.consortia_offer < int(row["Property1"])
    ):
        _refuse(s, 5145, "sem altar, limite do dia, contribuição, rápida ou prêmio por pegar", usadas=used)
        s.send(S_BLESS, b.complete(pb.ConsortiaMsg(blessSite=-1, blessLeftTime=used)))
        return
    if not pool or 1 not in sites:
        _refuse(s, 5145, "templates sem prêmio")
        s.send(S_BLESS, b.complete(pb.ConsortiaMsg(blessSite=-1, blessLeftTime=used)))
        return
    prize = int(random.choice(pool)["ItemId"])
    c.consortia_offer -= int(row["Property1"])
    mine[1].bless_count, mine[1].bless_day = used + 1, _day(now)
    g.blessed[s.player_id] = (prize, 1)  # ponytail: só na memória; reiniciar o servidor perde o prêmio
    await s.ctx.characters.save(c, mine[1])
    _player(s)
    s.send(
        S_BLESS,
        b.complete(pb.ConsortiaMsg(blessLeftTime=used + 1, blessSite=sites.index(1), blessTempId=prize, blessCount=1)),
    )


@router.on(8216)
async def altar_take(s: GameSession, _: object) -> None:
    """Pega o prêmio da bênção para a mochila (4143 ``result``)."""
    snap, g = s.snapshot, s.ctx.guilds
    assert snap is not None
    pending = g.blessed.get(s.player_id)
    if pending is None or sum(i.bag_type == BagType.BAG for i in snap.items) >= BAG_SIZE:
        s.send(S_ADDFRESH, b.complete(pb.ConsortiaMsg(result=False)))
        return
    del g.blessed[s.player_id]
    item = Item(snap.character.id or 0, pending[0], count=pending[1])
    item.pos = rules.free_bag_pos(snap)
    snap.items.append(item)
    await s.ctx.characters.save(item)
    s.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
    s.send(S_ADDFRESH, b.complete(pb.ConsortiaMsg(result=True)))


# ---- baú de prêmios --------------------------------------------------------------------------


def _box_msg(s: GameSession, guild_id: int) -> pb.ConsortiaStorageInfoMsg:
    out = pb.ConsortiaStorageInfoMsg()
    for i in s.ctx.guilds.box.get(guild_id, []):
        out.storageInfo.add(templateId=i.template_id, consortiaId=guild_id, count=i.count)
    return out


@router.on(8577)
async def box_check(s: GameSession, _: object) -> None:
    mine = _mine(s)
    s.send(S_BOX, b.complete(_box_msg(s, mine[0].id or 0) if mine else pb.ConsortiaStorageInfoMsg()))


@router.on(8579)
async def box_info(s: GameSession, msg: pb.ConsortiaTreasureBoxMsg) -> None:
    """Membros para distribuir um item do baú (4465)."""
    mine = _mine(s)
    if mine is None:
        _refuse(s, 8579, "sem guilda")
        return
    guild = mine[0]
    stored = next((i for i in s.ctx.guilds.box.get(guild.id or 0, []) if i.template_id == msg.templateId), None)
    out = pb.ConsortiaTreasureBoxMsg(
        consortiaId=guild.id,
        chairmanId=guild.chairman_id,
        templateId=msg.templateId,
        count=stored.count if stored else 0,
    )
    for m in s.ctx.guilds.members_of(guild.id or 0):
        c = _profile(s, m.character_id)
        if c is not None:
            out.playerInfo.add(
                job=c.job,
                nickName=c.nickname or "",
                level=c.grades,
                fightCapacity=c.fighting_capacity,
                userId=m.character_id,
                count=0,
                isReceived=False,
            )
    s.send(S_BOX_ALLOT, b.complete(out))


@router.on(8578)
async def box_send(s: GameSession, msg: pb.ConsortiaTreasureBoxMsg) -> None:
    """O chefe distribui: o item vai direto para a mochila de cada membro (online ou não)."""
    g = s.ctx.guilds
    mine = _mine(s)
    if mine is None or mine[1].duty_id != gd.CHAIRMAN:
        _refuse(s, 8578, "não é chefe")
        return
    guild = mine[0]
    box = g.box.get(guild.id or 0, [])
    stored = next((i for i in box if i.template_id == msg.templateId), None)
    wanted = [(p.userId, p.count) for p in msg.playerInfo if p.count > 0]
    members_ok = all((m := g.members.get(uid)) is not None and m.consortia_id == guild.id for uid, _ in wanted)
    total = sum(n for _, n in wanted)
    if stored is None or not wanted or not members_ok or total > stored.count:
        _refuse(s, 8578, "item, membro ou quantidade inválida", item=msg.templateId)
        return
    stored.count -= total
    if stored.count <= 0:
        box.remove(stored)
        await s.ctx.characters.save(delete=(stored,))
    else:
        await s.ctx.characters.save(stored)
    for uid, n in wanted:
        await _give(s, uid, msg.templateId, n)
    s.send(S_BOX, b.complete(_box_msg(s, guild.id or 0)))


async def _give(s: GameSession, player_id: int, template_id: int, count: int) -> None:
    """Item para outro jogador: pela sessão dele se estiver online (a sessão é dona do snapshot).

    ponytail: offline grava direto; se ele logar durante o await o item só aparece no próximo
    login (o 8224 recarrega o snapshot). Mochila cheia perde o item: falta correio.
    """
    other = s.ctx.online.get(player_id)
    snap = other.snapshot if other is not None else None
    if snap is None:
        snap = await s.ctx.characters.snapshot(player_id)
    if sum(i.bag_type == BagType.BAG for i in snap.items) >= BAG_SIZE:
        s.log.warning("baú: mochila cheia, item perdido", jogador=player_id, item=template_id)
        return
    item = Item(player_id, template_id, count=count)
    item.pos = rules.free_bag_pos(snap)
    snap.items.append(item)
    await s.ctx.characters.save(item)
    if other is not None and other.snapshot is snap:
        other.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, player_id))


def add_to_box(s: GameSession, guild_id: int, template_id: int, count: int) -> ConsortiaItem:
    """Prêmio para o baú da guilda (altar, guerra); quem chama grava o retorno."""
    box = s.ctx.guilds.box[guild_id]
    item = next((i for i in box if i.template_id == template_id), None)
    if item is None:
        item = ConsortiaItem(guild_id, template_id, count=0)
        box.append(item)
    item.count += count
    return item


# ---- eleição do chefe ------------------------------------------------------------------------


@router.on(8241)
async def voting_list(s: GameSession, _: object) -> None:
    """Candidatos (cargos 1-3) e votos da eleição atual.

    ponytail: o oficial abre a eleição quando o chefe some por muitos dias; a regra não está no
    cliente, então ``voting_state`` só muda pelo banco.
    """
    mine = _mine(s)
    out = pb.ConsortiaVotingUsersMsg()
    if mine is not None:
        guild, me = mine
        members = s.ctx.guilds.members_of(guild.id or 0)
        voted = guild.voting_id > 0 and me.voted_id == guild.voting_id
        for m in members:
            if m.duty_id > gd.ELDER:
                continue
            c = _profile(s, m.character_id)
            votes = sum(1 for x in members if x.voted_id == guild.voting_id and x.voted_for == m.character_id)
            out.info.add(
                userId=m.character_id,
                nickName=(c.nickname or "") if c else "",
                votingId=guild.voting_id,
                isVotingman=voted and me.voted_for == m.character_id,
                votingTime=0,
                votingData=votes if guild.voting_id > 0 else 0,
            )
    s.send(S_VOTERS, b.complete(out))


@router.on(8481)
async def vote(s: GameSession, msg: pb.ConsortiaVotingReqMsg) -> None:
    g = s.ctx.guilds
    mine = _mine(s)
    target = g.members.get(msg.votingUser)
    ok = mine is not None and mine[0].voting_state == 1 and mine[1].voted_id != mine[0].voting_id
    if not ok or mine is None or target is None or target.consortia_id != mine[0].id or target.duty_id > gd.ELDER:
        _refuse(s, 8481, "sem eleição, já votou ou candidato inválido", alvo=msg.votingUser)
        s.send(S_VOTED, b.complete(pb.ConsortiaVotingRspMsg(result=False)))
        return
    mine[1].voted_for, mine[1].voted_id = msg.votingUser, mine[0].voting_id
    await s.ctx.characters.save(mine[1])
    s.send(S_VOTED, b.complete(pb.ConsortiaVotingRspMsg(result=True)))


# ---- recrutamento ----------------------------------------------------------------------------


@router.on(8335)
async def speak(s: GameSession, msg: pb.ConditionSpeakMsg) -> None:
    """Anúncio de recrutamento: o cliente só deixa com ``speakTimes > 0``, e aqui é sempre 0."""
    _refuse(s, 8335, "sem anúncios de recrutamento", texto=msg.speak[:40])
