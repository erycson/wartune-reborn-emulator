"""Amigos, lista negra, grupos, perfil SNS, busca e dados de outros jogadores; troca de nome.

Formatos e textos conferidos no cliente (``FriendManager``, ``FriendSocketOutManager``,
``SNSManager``, ``RenameView``) e (só turco) em ``arkadas_istegi_gonderme.json``; ver docs/social.md.
"""

from __future__ import annotations

import re

from sqlalchemy.exc import IntegrityError

from ...domain.errors import NotFoundError, ValidationError
from ...domain.models import Character, FriendGroup, Quest, Relation, RelationType, SnsProfile
from ...protocol.messages import wartune_pb2 as pb
from ...services.characters import character_name
from .. import items, rules, social
from ..builders import login as b
from ..builders.player import quest_update
from ..router import router
from ..session import GameSession
from . import vip
from .login import army, player_info

S_ADD, S_REMOVE, S_REQUEST, S_RECOMMEND, S_UPDATE = 78, 79, 84, 85, 165
S_CHAT, S_ALERT, S_PLAYER, S_ARMY, S_ITEMS, S_QUESTS = 83, 111, 3, 150, 115, 112
S_GROUP_ADD, S_GROUP_DEL, S_GROUP_RENAME, S_MOVE = 4227, 4228, 4229, 4230
S_CHAT_STATE, S_RECENT_STATE, S_SEARCH, S_SNS_UPDATED = 4232, 4272, 4273, 4239
S_INFO, S_SEARCH_NICK, S_CHECK_NICK, S_REFUSE, S_RENAME, S_HERO_INFO = 4128, 4170, 4148, 4193, 4271, 4464
MIN_GRADE = 6  # FriendManager.sendAddFriendRequest
MAX_FRIENDS, MAX_BLACKLIST = 200, 50  # FriendManager.maxFriendCount (200 + vip.friend_bonus) e FullBlackList
# FridendsListView: groupDic com até 4 (o 2 e mais 3 do jogador, command01 "Max Group number has been reached."),
# nome até 12 (checkStringLength) e sem , | % (InputAgain)
MAX_GROUPS, GROUP_NAME_MAX, GROUP_NAME_BAD = 3, 12, frozenset(",|%")
FIRST_GROUP = 4  # 1 recentes, 2 amigos, 3 lista negra, -1 estranhos, -2 cônjuge: ids do cliente
SEARCH_PAGE = 10  # __findFriendHandler: ceil(totalRows / 10)
RECOMMEND_MAX = 10
RENAME_CARD = "289"  # SonType da carta de renomear (208018)
RENAME_ITEM, RENAME_FREE = 1, 2  # PlayerRenameReqMsg.type (RenameView)
SIGN_MAX = 60
SNS_FIELDS = {  # SNSInfoMsg -> SnsProfile (15033 manda só os campos alterados)
    "signDesc": "sign_desc",
    "sex": "sex",
    "birthdayType": "birthday_type",
    "birthYear": "birth_year",
    "birthMonth": "birth_month",
    "birthDay": "birth_day",
    "starId": "star_id",
    "bloodType": "blood_type",
    "country": "country",
    "province": "province",
    "city": "city",
    "headId": "head_id",
}
SEARCH_FIELDS = {  # FriendSearchConditionReqMsg -> SnsProfile (0 = qualquer)
    "sex": "sex",
    "birthMonth": "birth_month",
    "birthDay": "birth_day",
    "starId": "star_id",
    "bloodType": "blood_type",
    "country": "country",
    "province": "province",
    "city": "city",
}
_TAG = re.compile(r"<[^>]*>")
# textos do language.txt inglês (o cliente já barra antes de mandar: FriendManager.sendAddFriendRequest)
NOT_FOUND = "Player not found!"  # ConsortiaTransferFrame.command06
REFUSES = "Player is not accepting friend requests"  # texto deduzido (sem fonte no cliente/captura)
ALREADY = "Already in your Friend List."  # FriendManager.command05
FULL = {
    RelationType.FRIEND: "Friend number limit has been reached.",  # FriendManager.command02
    RelationType.BLACKLIST: "Your Blacklist number has reached 50, delete some of them before adding more.",  # content
}
# oficial_encantar #1778 (111 no canal 111), #1779 e #1793 (83 no canal 3)
WAITING = "Added successfully, awaiting the other player's response."
ADDED, ADDED_YOU = "You added a new friend: {}.", "{} has added you to his/her friends list."
WAITING_CHANNEL = 111


def _fail(s: GameSession, text: str) -> None:
    # 78 com result false: o cliente mostra addMsg (FriendManager.__addFriend)
    s.send(S_ADD, b.complete(pb.FriendInfoMsg(result=False, addMsg=text)))


async def _add(s: GameSession, nickname: str, relation: int) -> None:
    snap = s.snapshot
    assert snap is not None
    me = snap.character
    target = await social.by_nickname(s.ctx, me.server_id, nickname)
    if relation not in (RelationType.FRIEND, RelationType.BLACKLIST) or me.grades < MIN_GRADE:
        s.log.info("15003 recusado", relacao=relation)
        return
    if target is None or target.id == me.id or target.id is None:
        _fail(s, NOT_FOUND)
        return
    mine = social.relation_to(s, target.id)
    count = sum(r.relation == relation or (relation == 1 and r.relation == 3) for r in snap.relations)
    if mine is not None and (mine.relation == relation or (relation == 1 and mine.relation == RelationType.PENDING)):
        _fail(s, ALREADY)
        return
    if count >= (MAX_BLACKLIST if relation == RelationType.BLACKLIST else MAX_FRIENDS + vip.friend_bonus(s, snap)):
        _fail(s, FULL[RelationType(relation)])
        return
    theirs = await social.row_of(s.ctx, target.id, me.id or 0)
    if relation == RelationType.FRIEND and target.refuse_friend and theirs is None:
        _fail(s, REFUSES)
        return
    if mine is None:
        mine = Relation(me.id or 0, target.id, relation)
        snap.relations.append(mine)
    changed = [mine]
    if relation == RelationType.BLACKLIST:
        mine.relation, mine.group_id = relation, social.BLACK_GROUP
        if theirs is not None and theirs.relation == RelationType.FRIEND:  # a amizade acaba do meu lado
            theirs.relation = RelationType.PENDING
            changed.append(theirs)
    elif theirs is not None and theirs.relation in (RelationType.FRIEND, RelationType.PENDING):
        # o outro já me tinha adicionado: aceitar o pedido = amizade dos dois lados
        mine.relation, mine.group_id = RelationType.FRIEND, social.DEFAULT_GROUP
        theirs.relation = RelationType.FRIEND
        theirs.group_id = theirs.group_id if theirs.group_id > 0 else social.DEFAULT_GROUP
        changed.append(theirs)
    else:
        mine.relation, mine.group_id = RelationType.PENDING, social.NO_GROUP
    # pedido pendente ou aceito conta: (cliente) FriendManager.as __addFriend dispara ADD_FRIEND;
    # (visto, só turco: arkadas_istegi_gonderme #1) 78 com relation 3, pendente
    quests: list[Quest] = []
    if relation == RelationType.FRIEND:
        quests = rules.quest_event(snap, s.ctx.templates, rules.FRIEND_CONDITION, 0, len(snap.relations))
    await s.ctx.characters.save(*changed, *quests)

    sns = await s.ctx.characters.read(lambda uow: uow.sns.by_character(target.id or 0))
    s.send(S_ADD, social.friend_info(s.ctx, target, mine, sns))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    other = s.ctx.online.get(target.id)
    if theirs in changed and other is not None and theirs is not None:
        other.send(S_UPDATE, social.friend_update(s.ctx, me.id or 0, theirs))
        if theirs.relation == RelationType.FRIEND:  # aceitou: 165 e o aviso, como em #1792-#1793
            text = ADDED_YOU.format(social.player_link(s.ctx, me))
            other.send(S_CHAT, b.complete(pb.ChatChannelMsg(channel=3, encodeMsg=text)))
    if mine.relation == RelationType.BLACKLIST:
        return
    if mine.relation == RelationType.PENDING:
        s.send(S_ALERT, pb.ChatChannelMsg(channel=WAITING_CHANNEL, encodeMsg=WAITING))
        if other is not None and not social.blocks(other, me.id or 0):
            other.send(S_REQUEST, b.complete(pb.FriendRelationMsg(otherId=me.id, nickName=me.nickname or "")))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=ADDED.format(social.player_link(s.ctx, target))))


@router.on(15003)
async def add_relation(s: GameSession, msg: pb.FriendRelationMsg) -> None:
    """Pedir amizade (1) ou pôr na lista negra (2). Aceitar um pedido é mandar 1 de volta."""
    await _add(s, msg.nickName, msg.relation)


@router.on(15012)
async def confirm_friend(s: GameSession, msg: pb.FriendRelationMsg) -> None:
    """Sem chamador no cliente; tratado como aceitar (= 15003 com relation 1)."""
    await _add(s, msg.nickName, RelationType.FRIEND)


@router.on(15004)
async def remove_relation(s: GameSession, msg: pb.FriendRelationMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    mine = social.relation_to(s, msg.otherId)
    if mine is None:
        s.send(S_REMOVE, b.complete(pb.FriendRelationMsg(otherId=msg.otherId, result=False)))
        return
    snap.relations.remove(mine)
    theirs = await social.row_of(s.ctx, msg.otherId, s.player_id)
    demoted = theirs is not None and theirs.relation == RelationType.FRIEND
    if demoted:
        assert theirs is not None
        theirs.relation = RelationType.PENDING
    await s.ctx.characters.save(*([theirs] if demoted else []), delete=(mine,))
    s.send(S_REMOVE, b.complete(pb.FriendRelationMsg(otherId=msg.otherId, result=True)))
    other = s.ctx.online.get(msg.otherId)
    if demoted and other is not None and theirs is not None:
        other.send(S_UPDATE, social.friend_update(s.ctx, s.player_id, theirs))


@router.on(8285)
async def refuse_friend(s: GameSession, _: object) -> None:
    """Liga/desliga "recusar pedidos de amizade" (SettingFrame manda sem corpo)."""
    c = s.snapshot.character if s.snapshot else None
    assert c is not None
    c.refuse_friend = not c.refuse_friend
    await s.ctx.characters.save(c)
    s.send(S_REFUSE, pb.RefuseFriendRspMsg(result=c.refuse_friend))


@router.on(15013)
async def recommend(s: GameSession, _: object) -> None:
    """85: jogadores online que ainda não estão na lista (o cliente pede no login). (visto) oficial_20261023-171155-1
    #71, #4219, #5864: o oficial manda vazio; ``game_settings.friend_recommend`` (migração 0070) liga a lista."""
    snap = s.snapshot
    assert snap is not None
    known = {r.other_id for r in snap.relations} | {s.player_id}
    msg = pb.RecommendListMsg()
    if not s.ctx.world.settings.get("friend_recommend", False):
        s.send(S_RECOMMEND, msg)
        return
    for other in s.ctx.online.sessions():
        c = other.snapshot.character if other.snapshot else None
        if c is None or c.id in known or c.grades < MIN_GRADE:
            continue
        if len(msg.girlList) + len(msg.boyList) >= RECOMMEND_MAX:
            break
        target = msg.boyList if c.sex else msg.girlList
        target.add(
            playerId=c.id, nickName=c.nickname or "", level=c.grades, sex=c.sex, job=c.job
        ).attack = c.fighting_capacity
    for player in (*msg.girlList, *msg.boyList):
        b.complete(player)
    s.send(S_RECOMMEND, msg)


def _group(s: GameSession, group_id: int) -> FriendGroup | None:
    assert s.snapshot is not None
    return next((g for g in s.snapshot.groups if g.group_id == group_id), None)


def _group_name(raw: str) -> str | None:
    name = _TAG.sub("", raw).strip()
    return name if 0 < len(name) <= GROUP_NAME_MAX and not GROUP_NAME_BAD & set(name) else None


@router.on(15025)
async def add_group(s: GameSession, msg: pb.FriendGroupMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    name = _group_name(msg.groupName)
    if name is None or len(snap.groups) >= MAX_GROUPS:
        s.log.info("15025 recusado", nome=msg.groupName)
        return
    group = FriendGroup(s.player_id, max([FIRST_GROUP - 1, *(g.group_id for g in snap.groups)]) + 1, name)
    snap.groups.append(group)
    await s.ctx.characters.save(group)
    s.send(S_GROUP_ADD, pb.FriendGroupMsg(groupId=group.group_id, groupName=name, result=1))


@router.on(15026)
async def del_group(s: GameSession, msg: pb.FriendGroupMsg) -> None:
    """Os amigos do grupo voltam para o grupo 2, como o cliente faz (``changeListGroup``)."""
    snap = s.snapshot
    assert snap is not None
    group = _group(s, msg.groupId)
    if group is None:
        return
    snap.groups.remove(group)
    moved = [r for r in snap.relations if r.group_id == group.group_id]
    for r in moved:
        r.group_id = social.DEFAULT_GROUP
    await s.ctx.characters.save(*moved, delete=(group,))
    s.send(S_GROUP_DEL, b.complete(pb.FriendGroupMsg(groupId=group.group_id, result=1)))


@router.on(15027)
async def rename_group(s: GameSession, msg: pb.FriendGroupMsg) -> None:
    group, name = _group(s, msg.groupId), _group_name(msg.groupName)
    if group is None or name is None:
        return
    group.name = name
    await s.ctx.characters.save(group)
    s.send(S_GROUP_RENAME, pb.FriendGroupMsg(groupId=group.group_id, groupName=name, result=1))


@router.on(15028)
async def move_friend(s: GameSession, msg: pb.MoveFriendReqMsg) -> None:
    r = social.relation_to(s, msg.firendId)
    ok = r is not None and r.relation == RelationType.FRIEND
    ok = ok and (msg.groupId == social.DEFAULT_GROUP or _group(s, msg.groupId) is not None)
    if ok:
        assert r is not None
        r.group_id = msg.groupId
        await s.ctx.characters.save(r)
    s.send(S_MOVE, pb.MoveFriendReqMsg(firendId=msg.firendId, groupId=msg.groupId, result=1 if ok else 0))


@router.on(15029)
async def chat_state(s: GameSession, msg: pb.ChatStateMsg) -> None:
    """Estado do IM (online, ocupado, ausente...): eco para mim e aviso para quem me tem na lista."""
    s.chat_state = msg.chatState if 0 < msg.chatState <= social.ONLINE else social.ONLINE
    reply = _TAG.sub("", msg.replayStr)[:SIGN_MAX]
    out = pb.ChatStateMsg(userId=s.player_id, chatState=s.chat_state, result=1, replayStr=reply)
    s.send(S_CHAT_STATE, out)
    social.notify_watchers(s, S_CHAT_STATE, out)


@router.on(15043)
async def recent_state(s: GameSession, msg: pb.RecentContractsStateReqMsg) -> None:
    out = pb.ChatStateListRspMsg()
    for uid in list(msg.userId)[:50]:
        out.chatState.add(userId=uid, chatState=social.state_of(s.ctx, uid), result=1, replayStr="")
    s.send(S_RECENT_STATE, out)


def _sns_reply(s: GameSession, p: SnsProfile) -> None:
    assert s.snapshot is not None
    s.send(S_SNS_UPDATED, pb.SNSUpdatedMsg(result=1, snsInfo=social.sns_info(s.snapshot.character, p)))


@router.on(15033)
async def sns_update(s: GameSession, msg: pb.SNSInfoMsg) -> None:
    """Só os campos presentes mudam (a assinatura e o avatar vêm sozinhos)."""
    snap = s.snapshot
    assert snap is not None
    p = snap.sns or SnsProfile(s.player_id)
    for name, attr in SNS_FIELDS.items():
        if msg.HasField(name):
            value = getattr(msg, name)
            setattr(p, attr, _TAG.sub("", value)[:SIGN_MAX] if isinstance(value, str) else max(0, value))
    object.__setattr__(snap, "sns", p)  # snapshot é frozen; o perfil nasce no primeiro 15033
    await s.ctx.characters.save(p)
    _sns_reply(s, p)


@router.on(15036)
async def sns_reset(s: GameSession, _: object) -> None:
    snap = s.snapshot
    assert snap is not None
    p = snap.sns or SnsProfile(s.player_id)
    for attr in SNS_FIELDS.values():
        setattr(p, attr, "" if attr == "sign_desc" else 0)
    object.__setattr__(snap, "sns", p)
    await s.ctx.characters.save(p)
    _sns_reply(s, p)


@router.on(15042)
async def friend_search(s: GameSession, msg: pb.FriendSearchConditionReqMsg) -> None:
    """Busca por perfil SNS, 10 por página; ``pageIndex`` começa em 1 (FindResultFrame: ``curPage = 1``)."""
    filters = {attr: getattr(msg, name) for name, attr in SEARCH_FIELDS.items()}
    offset = (max(msg.pageIndex, 1) - 1) * SEARCH_PAGE
    total, found = await s.ctx.characters.read(lambda uow: uow.sns.search(filters, offset, SEARCH_PAGE))
    people = await social.characters(s.ctx, [p.character_id for p in found])
    out = pb.FriendSearchRspMsg(totalRows=total)
    for p in found:
        if (c := people.get(p.character_id)) is not None:
            out.snsInfo.append(social.sns_info(c, p))
    s.send(S_SEARCH, out)


async def _character(s: GameSession, player_id: int) -> Character | None:
    return (await social.characters(s.ctx, [player_id])).get(player_id)


@router.on(8200)
async def simple_info(s: GameSession, msg: pb.InfoReqMsg) -> None:
    """4128 ``InfoRspMsg`` (PlayerManager.__getSimpleInfoHandler); ``from`` volta igual."""
    c = await _character(s, msg.otherId)
    if c is None:
        s.log.info("8200 sem jogador", outro=msg.otherId)
        return
    out = pb.InfoRspMsg(info=social.simple_player(s.ctx, c))
    setattr(out, "from", getattr(msg, "from"))  # "from" é palavra reservada
    s.send(S_INFO, out)


@router.on(8257)
async def player_search(s: GameSession, msg: pb.SimplePlayerSearchReqMsg) -> None:
    """4170: sem ``info`` quando não existe (o correio e a guilda checam ``hasInfo``)."""
    assert s.snapshot is not None
    c = await social.by_nickname(s.ctx, s.snapshot.character.server_id, msg.otherNickname.strip())
    out = pb.SimplePlayerSearchRspMsg()
    if c is not None:
        out.info.CopyFrom(social.simple_player(s.ctx, c))
    s.send(S_SEARCH_NICK, out)


@router.on(8223)
async def check_nick(s: GameSession, msg: pb.CheckNickMsg) -> None:
    """Apelido -> id para presente da loja (ShopManager.__checkNicknameBack); -1 = não existe."""
    assert s.snapshot is not None
    c = await social.by_nickname(s.ctx, s.snapshot.character.server_id, msg.nickName.strip())
    s.send(S_CHECK_NICK, pb.CheckNickMsg(playerId=c.id if c is not None else -1, nickName=msg.nickName))


@router.on(25097)
async def cross_user_info(s: GameSession, msg: pb.DetailReqMsg) -> None:
    """Dados do herói de quem falou no chat de batalha (4464); sem entre-servidores = este servidor."""
    other = s.ctx.online.get(msg.otherId)
    try:
        snap = other.snapshot if other is not None else await s.ctx.characters.snapshot(msg.otherId)
    except NotFoundError:
        snap = None
    if snap is None or snap.leader is None or snap.castle is None:
        s.log.info("25097 sem jogador", outro=msg.otherId)
        return
    stats = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now())
    hero = b.hero_info(snap.leader, snap.character.id or 0, stats)
    s.send(S_HERO_INFO, b.complete(hero))


@router.on(8345)
async def rename(s: GameSession, msg: pb.PlayerRenameReqMsg) -> None:
    """Troca de nome: carta (SonType 289) na posição ``pos`` ou grátis se o nome tem "!" (fusão)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    c = snap.character
    card = items.bag_item(snap, pos=msg.pos) if msg.type == RENAME_ITEM else None
    row = s.ctx.templates.get("ItemTempInfos", card.template_id) if card is not None else None
    paid = row is not None and row.get("SonType") == RENAME_CARD
    try:
        nick = character_name(msg.nickName)
    except ValidationError:
        nick = ""
    ok = bool(nick) and (paid or (msg.type == RENAME_FREE and "!" in (c.nickname or "")))
    if ok and await social.by_nickname(s.ctx, c.server_id, nick) is not None:
        ok = False
    if not ok:
        s.log.info("8345 recusado", tipo=msg.type, nome=msg.nickName)
        s.send(S_RENAME, pb.PlayerRenameRspMsg(result=False))
        return
    old = c.nickname
    gone = items.take_one(snap, card) if paid and card is not None else None
    named: list[object] = [c, snap.leader, *([snap.castle] if snap.castle else [])]
    for entity in named:
        setattr(entity, "name" if entity is snap.castle else "nickname", nick)
    kept = [card] if card is not None and gone is None else []
    try:
        await s.ctx.characters.save(*named, *kept, delete=(gone,) if gone else ())
    except IntegrityError:  # outro pegou o nome entre a checagem e o save: nada foi gravado
        for entity in named:
            setattr(entity, "name" if entity is snap.castle else "nickname", old)
        if card is not None:
            card.count += 1
            if gone is not None:
                snap.items.append(card)
        s.send(S_RENAME, pb.PlayerRenameRspMsg(result=False))
        return
    if card is not None:
        s.send(S_ITEMS, items.item_update(card, s.player_id))
    s.send(S_RENAME, pb.PlayerRenameRspMsg(result=True))
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    s.send(S_ARMY, b.complete(army(s, snap)[0]))
