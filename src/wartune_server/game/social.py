"""Amigos, lista negra e perfil: estado compartilhado entre sessões e mensagens comuns.

As linhas de ``relations`` de quem está online vivem no snapshot dele; quem altera a linha de
outro jogador mexe no objeto da sessão dele (``row_of``) para o ``save`` dela não desfazer.
Regras e formatos em docs/social.md.
"""

from __future__ import annotations

from datetime import datetime

from google.protobuf.message import Message

from ..domain.models import Character, Marriage, Relation, RelationType, SnsProfile
from ..protocol.messages import wartune_pb2 as pb
from .builders import login as b
from .session import GameContext, GameSession

ONLINE, OFFLINE = 7, 0  # SimplePlayerInfoMsg.state / chatState: 7 = online no IM, 0 = offline
# FriendManager.initGroupList cria o 2; FridendsListView: -1 = estranhos (pendentes), 3 = cabeçalho da lista negra
DEFAULT_GROUP, NO_GROUP, BLACK_GROUP = 2, -1, 3
S_FRIEND_LOGIN, S_FRIEND_LOGOUT = 160, 161
S_MARRIAGE = 4657


async def characters(ctx: GameContext, ids: list[int]) -> dict[int, Character]:
    """Personagens por id: da sessão quando online (estado mais novo), senão do banco."""
    found = {i: s.snapshot.character for i in ids if (s := ctx.online.get(i)) is not None and s.snapshot}
    missing = [i for i in ids if i not in found]
    if missing:
        for c in await ctx.characters.read(lambda uow: uow.characters.by_ids(missing)):
            if c.active and c.id is not None:
                found[c.id] = c
    return found


async def by_nickname(ctx: GameContext, server_id: int, nickname: str) -> Character | None:
    c = await ctx.characters.read(lambda uow: uow.characters.by_nickname(server_id, nickname))
    if c is None or not c.active or c.id is None:
        return None
    online = ctx.online.get(c.id)
    return online.snapshot.character if online is not None and online.snapshot else c


async def row_of(ctx: GameContext, owner_id: int, other_id: int) -> Relation | None:
    """Linha de ``owner_id`` para ``other_id`` (objeto da sessão se o dono estiver online)."""
    owner = ctx.online.get(owner_id)
    if owner is not None and owner.snapshot is not None:
        return next((r for r in owner.snapshot.relations if r.other_id == other_id), None)
    return await ctx.characters.read(lambda uow: uow.relations.get(owner_id, other_id))


def relation_to(s: GameSession, other_id: int) -> Relation | None:
    assert s.snapshot is not None
    return next((r for r in s.snapshot.relations if r.other_id == other_id), None)


def blocks(receiver: GameSession, sender_id: int) -> bool:
    """``receiver`` pôs ``sender_id`` na lista negra: não recebe chat nem privado dele."""
    r = relation_to(receiver, sender_id) if receiver.snapshot is not None else None
    return r is not None and r.relation == RelationType.BLACKLIST


def watchers(s: GameSession) -> list[GameSession]:
    """Sessões online que têm este jogador na lista (amigo, pendente ou lista negra)."""
    me = s.player_id
    return [o for o in s.ctx.online.sessions() if o.snapshot is not None and relation_to(o, me) is not None]


def notify_watchers(s: GameSession, code: int, msg: Message) -> None:
    for other in watchers(s):
        if other is not s:
            other.send(code, msg)


def announce(s: GameSession, online: bool) -> None:
    """160/161: o cliente procura ``otherId`` na lista de quem recebe."""
    notify_watchers(s, S_FRIEND_LOGIN if online else S_FRIEND_LOGOUT, pb.FriendRelationMsg(otherId=s.player_id))


def state_of(ctx: GameContext, player_id: int) -> int:
    session = ctx.online.get(player_id)
    return session.chat_state if session is not None else OFFLINE


def last_seen(c: Character) -> datetime | None:
    """Última vez no jogo: a saída gravada (``offline_at``) ou, se caiu sem gravar a saída, o último login."""
    return max((t for t in (c.offline_at, c.last_login_at) if t is not None), default=None)


def simple_player(ctx: GameContext, c: Character) -> pb.SimplePlayerInfoMsg:
    return b.complete(
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
            state=state_of(ctx, c.id or 0),
            logOutTime=b.fmt_time(seen) if (seen := last_seen(c)) else b.NEVER,
            right=1,
        )
    )


def sns_info(c: Character, p: SnsProfile | None) -> pb.SNSInfoMsg:
    p = p or SnsProfile(c.id or 0)
    return b.complete(
        pb.SNSInfoMsg(
            id=p.id or 0,
            userId=c.id,
            nickname=c.nickname or "",
            signDesc=p.sign_desc,
            sex=p.sex,
            birthdayType=p.birthday_type,
            birthYear=p.birth_year,
            birthMonth=p.birth_month,
            birthDay=p.birth_day,
            starId=p.star_id,
            bloodType=p.blood_type,
            country=p.country,
            province=p.province,
            city=p.city,
            headId=p.head_id,
            job=c.job,
        )
    )


GRADE_STEP = 10  # padrão de game_settings friend_grade_step (0037)


def friend_grade(ctx: GameContext, r: Relation) -> int:
    """Grau de amizade (``relationGrade``/``friendGrade``). (dedução) 1 + pontos // passo:
    (só turco) ciftlik #85 tem grau 4 com 34 pontos; a tabela real não está no cliente nem nos templates.
    Só amigo tem grau."""
    if r.relation != RelationType.FRIEND:
        return 0
    return 1 + r.friend_gp // max(1, int(ctx.world.settings.get("friend_grade_step", GRADE_STEP)))


def friend_info(ctx: GameContext, c: Character, r: Relation, p: SnsProfile | None = None) -> pb.FriendInfoMsg:
    """78 / 165 (``FriendManager.readFriendInfo``)."""
    state = state_of(ctx, c.id or 0)
    guild = ctx.guilds.of(c.id or 0)
    return b.complete(
        pb.FriendInfoMsg(
            userId=c.id,
            relation=r.relation,
            relationGrade=friend_grade(ctx, r),
            relationGp=r.friend_gp,
            sex=c.sex,
            pic=c.icon,
            grades=c.grades,
            nickName=c.nickname or "",
            onlineState=state,
            result=True,
            addMsg="success",
            fightCapacity=c.fighting_capacity,
            job=c.job,
            groupId=r.group_id,
            consortiaId=guild[0].id if guild else 0,  # oficial_encantar #1777: a guilda do outro
            consortiaName=guild[0].name if guild else "",
            snsInfo=sns_info(c, p),
            chatState=state,
        )
    )


async def friend_list(s: GameSession) -> pb.FriendRelationList:
    """4156 do login numa página só (``maxPage=1``; 0 sem ninguém, captura inglesa #61): o cliente espera
    ``maxPage`` pacotes.

    ponytail: página única; paginar se a lista passar do tamanho de um pacote (200 amigos cabem).
    """
    snap = s.snapshot
    assert snap is not None
    found = await characters(s.ctx, [r.other_id for r in snap.relations])
    msg = pb.FriendRelationList(maxPage=1 if snap.relations or snap.groups else 0, curPage=0)
    for r in snap.relations:
        if (c := found.get(r.other_id)) is not None:
            entry = msg.relationList.add(relation=r.relation, friendRp=r.friend_gp, friendGrade=friend_grade(s.ctx, r),
                                         groupId=r.group_id, isVip=0)  # fmt: skip
            entry.player.CopyFrom(simple_player(s.ctx, c))
    for g in snap.groups:
        msg.group.add(groupId=g.group_id, groupName=g.name, result=1)
    return msg


async def marriage_msg(ctx: GameContext, m: Marriage) -> pb.MarriageMsg:
    """4657 ``MarriageMsg`` (MarryManager.__marryInfoHandler): cônjuge e situação."""
    mate = (await characters(ctx, [m.mate_id])).get(m.mate_id)
    seen = last_seen(mate) if mate else None
    days = (ctx.clock.now() - seen).days if seen else 0
    online = ctx.online.get(m.mate_id) is not None
    return b.complete(
        pb.MarriageMsg(
            userId=m.mate_id,
            nickName=mate.nickname or "" if mate else "",
            state=m.state,
            templateId=m.spec_id,
            # speTemplateId != 0 = cerimônia reservada e alianças por trocar (MarryUIMediator); aqui casar já troca
            speTemplateId=0,
            engageTime=b.fmt_time(m.since),
            # MarryInfo.marriageTime lê "YYYY-MM-DD hh:mm:ss" (desconto e botão de cerimônia nas 72 h); noivo: vazio
            marTime=b.fmt_time(m.married_at) if m.married_at else "",
            logoutDays=0 if online else days,  # divórcio grátis (op 15) com 5+ dias offline
        )
    )


def player_link(ctx: GameContext, c: Character) -> str:
    """Link de jogador no chat (``<a t="1" .../>``), como no 83 oficial do pedido de amizade (oficial_encantar #1779:
    ``consortiaId`` é a guilda do jogador; ``grades`` vai 0)."""
    guild = ctx.guilds.of(c.id or 0)
    gid = guild[0].id if guild else 0
    return f'<a t="1" id="{c.id}" name="{c.nickname}" consortiaId="{gid}" serverName="" grades="0" />'
