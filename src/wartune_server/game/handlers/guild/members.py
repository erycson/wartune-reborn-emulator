"""Guilda: candidaturas, convites, sair, expulsar, passar a chefia e cargos."""

from __future__ import annotations

from ....domain import gameday
from ....domain.models import (
    BagType,
    Consortia,
    ConsortiaInvite,
)
from ....protocol.messages import wartune_pb2 as pb
from ....services import ledger
from ... import guild as gd
from ... import rules
from ...builders import login as b
from ...builders.player import item_moved, quest_update
from ...router import router
from ...session import GameSession
from .common import (
    CD_CARD,
    MAX_APPLICATIONS,
    MIN_GRADE,
    S_APPLY_DEL,
    S_DUTY,
    S_INVITE_RESULT,
    S_INVITED,
    S_INVITES,
    S_ITEMS,
    S_JOINED,
    S_NEW_APPLY,
    S_PASS,
    S_QUESTS,
    S_RECRUIT,
    _can,
    _char,
    _clear_cooldown,
    _event,
    _join,
    _joined,
    _left,
    _mine,
    _now,
    _player,
    _profile,
    _push_info,
    _refuse,
)

# ---- candidaturas e convites -----------------------------------------------------------------


def _invite_msg(s: GameSession, i: ConsortiaInvite) -> pb.ConsortiaUserInviteInfoMsg:
    """(visto) oficial_20261023-171155-1 #4253 e #4259: ``createDate`` e ``inviteDate`` são o dia da candidatura à
    meia-noite ("2026-10-23 00:00:00", também na guilda criada antes), ``isexist`` verdadeiro."""
    g = s.ctx.guilds
    day = f"{gameday.local(i.created_at):%Y-%m-%d} 00:00:00"
    guild = g.guilds.get(i.consortia_id)
    user, inviter = _profile(s, i.user_id), _profile(s, i.invite_id)
    chairman = _profile(s, guild.chairman_id) if guild else None
    return pb.ConsortiaUserInviteInfoMsg(
        id=i.id,
        consortiaId=i.consortia_id,
        consortiaName=guild.name if guild else "",
        createDate=day if guild else b.NEVER,
        userId=i.user_id,
        userNickname=(user.nickname or "") if user else "",
        inviteId=i.invite_id,
        inviteNickname=(inviter.nickname or "") if inviter else "",
        chairmanNickname=(chairman.nickname or "") if chairman else "",
        inviteDate=day,
        fromType=i.from_type,
        isexist=True,
    )


@router.on(8209)
async def invite_list(s: GameSession, _: object) -> None:
    """Candidaturas do jogador (``fromType`` falso) e convites recebidos (verdadeiro), a mais nova primeiro
    ((visto) #4259: 302 antes de 301)."""
    out = pb.ConsortiaUserInviteInfoListRspMsg()
    for i in sorted(s.ctx.guilds.invites_of(s.player_id), key=lambda i: i.id or 0, reverse=True):
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
    paid = _clear_cooldown(s, msg.isPay)
    if paid is None:
        _refuse(s, 5135, "espera de 24 h")
        return
    app = ConsortiaInvite(guild.id or 0, s.player_id, _now(s))
    g.invites.append(app)
    await s.ctx.characters.save(c, app, *paid)
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
    if mine is not None and app is None:
        # a candidatura sumiu (o candidato entrou noutra guilda ou criou a dele): o ApplyPlayerList já tirou a linha
        # e espera um 40 por pedido antes de pedir a lista de novo (*dedução*: o 40 de uma recusa)
        s.send(S_PASS)
        return
    if mine is None or app is None or app.from_type or app.consortia_id != mine[0].id:
        _refuse(s, 5134, "sem direito ou candidatura de outra guilda", candidatura=msg.applyId)
        return
    guild = mine[0]
    if not msg.result or g.of(app.user_id) is not None:
        g.invites.remove(app)
        await s.ctx.characters.save(delete=(app,))
        s.send(S_PASS)
        return
    if len(g.members_of(guild.id or 0)) >= gd.max_members(guild):
        _refuse(s, 5134, "guilda cheia")
        return
    member, gone = _join(s, guild, app.user_id)
    who = _profile(s, app.user_id)
    # texto deduzido (sem fonte no cliente/captura)
    event = _event(s, guild, gd.EV_MEMBER, (who.nickname if who else None) or str(app.user_id), "joined the guild.")
    # offline: a missão 22 dele avança no 5014 (rules.social_state_quests)
    other = s.ctx.online.get(app.user_id)
    snap = other.snapshot if other is not None else None
    quests = rules.quest_event(snap, s.ctx.templates, rules.GUILD_JOIN_CONDITION, 0, 1) if snap is not None else []
    await s.ctx.characters.save(member, event, *quests, delete=tuple(gone))
    s.send(S_PASS)
    _joined(s, guild, app.user_id)
    if other is not None and snap is not None and quests:
        other.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


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
    """Convida alguém sem guilda e de nível 12+; se estiver online recebe o 41 e o cliente mostra o convite.

    Direito 9, o mesmo do recrutamento: todo botão de convite do cliente inglês usa ``getRightsByIndex(9)``
    (ConsortiaRecruitFrame também filtra ``grades >= 12`` e sem guilda)."""
    g = s.ctx.guilds
    mine = _can(s, gd.R_RECRUIT)
    target = _profile(s, msg.otherId) or next(iter(await s.ctx.characters.characters([msg.otherId])), None)
    bad = target is None or not target.active or target.grades < MIN_GRADE or g.of(msg.otherId) is not None
    if mine is None or target is None or bad:
        _refuse(s, 5142, "sem direito, alvo abaixo do 12 ou já em guilda", alvo=msg.otherId)
        return
    # 8286 (C_ROOM_REFUSE, SettingFrame "refuseInvite") vale para convites de pesca/estrada/caça-níquel;
    # na guilda é dedução: quem recusa não recebe o 41
    if target.refuse_invite:
        _refuse(s, 5142, "alvo recusa convites", alvo=msg.otherId)
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
    if not msg.result or _mine(s) is not None or full or _clear_cooldown(s, False) is None:
        g.invites.remove(inv)
        await s.ctx.characters.save(delete=(inv,))
        return
    member, gone = _join(s, guild, s.player_id)
    # texto deduzido (sem fonte no cliente/captura)
    event = _event(s, guild, gd.EV_MEMBER, _char(s).nickname or "", "joined the guild.")
    snap = s.snapshot
    assert snap is not None
    quests = rules.quest_event(snap, s.ctx.templates, rules.GUILD_JOIN_CONDITION, 0, 1)  # missão 22
    await s.ctx.characters.save(member, event, *quests, delete=tuple(gone))
    _joined(s, guild, s.player_id)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


# ---- sair / expulsar / cargos ----------------------------------------------------------------


@router.on(5146)
async def quit_(s: GameSession, msg: pb.ConsortiaQuitReqMsg) -> None:
    """Sair. O chefe só sai sozinho (a guilda acaba). ``clear_CDType`` 1 paga para não esperar
    24 h: cartão 208013 ou ``Consortia_ClearCD_Point`` diamantes (395; ``ConsortiaFrame.checkTxt``)."""
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
    entry = None
    if msg.clear_CDType == 1 and card is None:
        cost = gd.config(s.ctx.templates, "Consortia_ClearCD_Point", 50)
        entry = ledger.pay(c, cost, bind=False, reason="guild_clear_cd", ref="quit", now=now)
    paid = msg.clear_CDType == 1 and (card is not None or entry is not None)
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
        # texto deduzido (sem fonte no cliente/captura)
        changed = [c, _event(s, guild, gd.EV_MEMBER, c.nickname or "", "left the guild.")]
    if card is not None and card.count > 0:
        changed.append(card)
    if entry is not None:
        changed.append(entry)
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
    # texto deduzido (sem fonte no cliente/captura)
    name = (who.nickname if who else None) or str(msg.otherId)
    event = _event(s, guild, gd.EV_KICK, _char(s).nickname or "", "expelled", name, "from the guild.")
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
    # texto deduzido (sem fonte no cliente/captura)
    name = (who.nickname if who else None) or str(msg.otherId)
    event = _event(s, guild, gd.EV_TRANSFER, "Guild Master title transferred to", name, "")
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
