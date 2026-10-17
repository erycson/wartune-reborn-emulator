"""Guildas (consortia) em memória: guilda, membros, candidaturas, eventos e baú.

Tudo da guilda fica aqui e não no ``Character`` de cada sessão: o chefe expulsa ou aceita alguém
que está online, e o próximo ``save`` da sessão do outro gravaria o ``Character`` antigo por cima.
O handler altera o registro antes de qualquer ``await`` e grava junto com o personagem, na mesma
``characters.save``. Regras do cliente em docs/guilda.md.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from ..domain.models import Character, Consortia, ConsortiaEvent, ConsortiaInvite, ConsortiaItem, ConsortiaMember
from ..protocol.messages import wartune_pb2 as pb
from ..services.characters import CharacterService
from ..templates.repository import GameTemplates, Row
from .builders import login as b

if TYPE_CHECKING:
    from .session import GameContext, GameSession

CHAIRMAN, VICE, ELDER, MEMBER = 1, 2, 3, 5
# direitos por cargo, copiados do oficial (login.json #116); bit i-1 = getRightsByIndex(i)
RIGHTS = {
    1: bytes.fromhex("ffff7fe87f"),
    2: bytes.fromhex("baff744855"),
    3: bytes.fromhex("b0bf704804"),
    4: bytes.fromhex("20fe700004"),
    5: bytes.fromhex("20fe700004"),
}
RIGHTS_LEN = 55
# índices de getRightsByIndex que o cliente usa (m6 ConsortiaStaffPage, ConsortiaPlayerMenu...)
R_CHAIRMAN, R_RESEARCH, R_UPGRADE, R_PLACARD, R_KICK, R_INVITE = 1, 2, 3, 4, 5, 6
R_RECRUIT, R_RENAME, R_DUTY, R_DESCRIPTION, R_REJECT = 9, 18, 19, 30, 33
LEVEL_TYPES = {
    1: "levels",
    2: "shop_level",
    3: "altar_level",
    4: "school_level",
    5: "store_level",
    6: "attack_level",
    7: "defence_level",
    8: "agility_level",
    9: "ability_level",
    10: "captain_level",
    11: "gold_level",
    12: "physique_level",
}
# tipo -> coluna do personagem (ConsortiaSkillHelper.getLevelByType; o 7 não tem habilidade)
SKILLS = {6: "skill_attack", 8: "skill_agility", 9: "skill_ability", 10: "skill_captain", 11: "skill_gold"}
SKILLS[12] = "skill_physique"
MAX_LEVEL = 10
PAGE = 8  # linhas por página em 4134, 4139 e 4140
ONLINE = 7  # SimplePlayerInfoMsg.state


def has_right(duty: int, index: int) -> bool:
    bits = RIGHTS.get(duty, b"")
    i = index - 1
    return i >> 3 < len(bits) and bool(bits[i >> 3] >> (i & 7) & 1)


def max_members(guild: Consortia) -> int:
    return guild.levels * 20 + 10  # ConsortiaItem.as: currentCount / (levels * 20 + 10)


def level_row(templates: GameTemplates, kind: int, level: int) -> Row | None:
    return next(templates.find("ConsortiaLevelInfos", Types=kind, Levels=level), None)


def config(templates: GameTemplates, name: str, default: int) -> int:
    row = next(templates.find("ConfigInfos", ConfigName=name), None)
    try:
        return int(row["ConfigValue"]) if row else default
    except ValueError:
        return default


ALTAR_CLOSED, ALTAR_OPEN, ALTAR_ENDED = 0, 1, 2
ALTAR_SECONDS = 1260  # duração do altar do demônio (21 min)


def altar_state(guild: Consortia, now: datetime) -> int:
    """Calculado na hora: aberto por 21 min, encerrado até o fim do dia, fechado no dia seguinte."""
    at = guild.altar_at
    if at is None or guild.altar_state == ALTAR_CLOSED or at.date() != now.date():
        return ALTAR_CLOSED
    return ALTAR_OPEN if (now - at).total_seconds() < ALTAR_SECONDS else ALTAR_ENDED


def pay_points(c: Character, amount: int, bind_first: bool) -> bool:
    """Diamantes: ``bind_first`` (payType 0) gasta primeiro os vinculados (giftToken)."""
    bind = min(c.gift_token, amount) if bind_first else 0
    if c.point < amount - bind:
        return False
    c.gift_token -= bind
    c.point -= amount - bind
    return True


@dataclass
class Guilds:
    """Estado de todas as guildas do servidor (um processo = um servidor)."""

    guilds: dict[int, Consortia] = field(default_factory=dict)
    members: dict[int, ConsortiaMember] = field(default_factory=dict)  # character_id ->
    invites: list[ConsortiaInvite] = field(default_factory=list)
    events: dict[int, list[ConsortiaEvent]] = field(default_factory=lambda: defaultdict(list))
    box: dict[int, list[ConsortiaItem]] = field(default_factory=lambda: defaultdict(list))
    # dados de quem está offline para as listas (atualizado no login/logout; online vale a sessão)
    profiles: dict[int, Character] = field(default_factory=dict)
    logout_at: dict[int, datetime] = field(default_factory=dict)
    reserved: set[str] = field(default_factory=set)  # nomes sendo criados (entre a checagem e o save)
    blessed: dict[int, tuple[int, int]] = field(default_factory=dict)  # prêmio da bênção por pegar

    @classmethod
    async def load(cls, characters: CharacterService, server_id: int) -> Guilds:
        guilds, members, invites, events, items = await characters.guild_state(server_id)
        g = cls()
        g.guilds = {x.id: x for x in guilds if x.id is not None}
        g.members = {m.character_id: m for m in members}
        g.invites = invites
        for e in events:
            g.events[e.consortia_id].append(e)
        for i in items:
            g.box[i.consortia_id].append(i)
        ids = sorted({m.character_id for m in members} | {i.user_id for i in invites} | {i.invite_id for i in invites})
        g.profiles = {c.id: c for c in await characters.characters(ids) if c.id is not None}
        return g

    def of(self, player_id: int) -> tuple[Consortia, ConsortiaMember] | None:
        m = self.members.get(player_id)
        guild = self.guilds.get(m.consortia_id) if m else None
        return (guild, m) if guild is not None and m is not None else None

    def members_of(self, guild_id: int) -> list[ConsortiaMember]:
        return [m for m in self.members.values() if m.consortia_id == guild_id]

    def by_name(self, name: str) -> Consortia | None:
        low = name.lower()
        return next((x for x in self.guilds.values() if x.name.lower() == low), None)

    def name_taken(self, name: str) -> bool:
        return self.by_name(name) is not None or name.lower() in self.reserved

    def invite(self, invite_id: int) -> ConsortiaInvite | None:
        return next((i for i in self.invites if i.id == invite_id), None)

    def invites_of(self, user_id: int) -> list[ConsortiaInvite]:
        return [i for i in self.invites if i.user_id == user_id]

    def applications(self, guild_id: int) -> list[ConsortiaInvite]:
        return [i for i in self.invites if i.consortia_id == guild_id and not i.from_type]

    def add_event(self, guild_id: int, now: datetime, remark: str, kind: int = 1) -> ConsortiaEvent:
        e = ConsortiaEvent(guild_id, now, remark[:255], type=kind)
        self.events[guild_id].append(e)
        del self.events[guild_id][:-50]  # ponytail: só os 50 últimos na memória; o banco guarda todos
        return e

    def drop_guild(self, guild_id: int) -> list[object]:
        """Tira a guilda e tudo dela da memória; devolve as entidades para apagar."""
        gone: list[object] = [self.guilds.pop(guild_id)]
        for m in self.members_of(guild_id):
            del self.members[m.character_id]
            gone.append(m)
        gone += [i for i in self.invites if i.consortia_id == guild_id]
        self.invites = [i for i in self.invites if i.consortia_id != guild_id]
        gone += self.events.pop(guild_id, [])
        gone += self.box.pop(guild_id, [])
        return gone


# ---- mensagens -------------------------------------------------------------------------------


def _date(value: datetime | None) -> str:
    return b.fmt_time(value) if value is not None else b.NEVER


def info_msg(g: Guilds, guild: Consortia, now: datetime) -> pb.ConsortiaInfoMsg:
    chairman = g.profiles.get(guild.chairman_id)
    msg = pb.ConsortiaInfoMsg(
        consortiaId=guild.id,
        creatorId=guild.creator_id,
        chairmanId=guild.chairman_id,
        levels=guild.levels,
        currentCount=len(g.members_of(guild.id or 0)),
        kickCount=guild.kick_count,
        shopLevel=guild.shop_level,
        storeLevel=guild.store_level,
        altarLevel=guild.altar_level,
        schoolLevel=guild.school_level,
        attackLevel=guild.attack_level,
        defenceLevel=guild.defence_level,
        agilityLevel=guild.agility_level,
        abilityLevel=guild.ability_level,
        captainLevel=guild.captain_level,
        goldLevel=guild.gold_level,
        physiqueLevel=guild.physique_level,
        offer=guild.offer,
        totalOffer=guild.total_offer,
        codeType=guild.code_type,
        codeNeedDate=guild.code_need,
        placard=guild.placard,
        description=guild.description,
        groupPlacard=guild.group_placard,
        consortiaName=guild.name,
        creatorName=guild.creator_name,
        chairmanName=(chairman.nickname or "") if chairman else "",
        openApp=guild.open_app,
        isExist=True,
        createDate=_date(guild.created_at),
        kickDate=_date(guild.kick_at),
        # o cliente avisa "guilda inativa" se warnDate tiver 8 dias ou mais (outOfDate)
        deductDate=_date(now),
        warnDate=_date(now),
        quitDate=b.NEVER,
        codeBeginDate=_date(guild.code_begin_at),
        currentDate=_date(now),  # base da contagem da espera da melhoria
        votingDate=_date(guild.voting_at),
        votingStatic=guild.voting_state,
        votingId=guild.voting_id,
        altarDate=_date(guild.altar_at),
        altarState=altar_state(guild, now),
        maxMave=guild.max_wave,
    )
    msg.orderInfo.consortiaId = guild.id or 0
    return b.complete(msg)


def member_msg(
    g: Guilds, c: Character, m: ConsortiaMember | None, online: bool, guild: Consortia | None
) -> pb.SimplePlayerInfoMsg:
    msg = pb.SimplePlayerInfoMsg(
        userId=c.id,
        nickName=c.nickname or "",
        isExist=1,
        sexs=c.sex,
        pics=c.icon,
        camp=c.camp,
        state=ONLINE if online else 0,
        consortiaID=guild.id if guild else 0,
        consortiaName=guild.name if guild else "",
        consortiaOffer=c.consortia_offer,
        consortiaTotalOffer=c.consortia_total_offer,
        grades=c.grades,
        gp=c.gp,
        repute=c.repute,
        logOutTime=_date(g.logout_at.get(c.id or 0) or c.last_login_at),
        dutyId=m.duty_id if m else 0,
        fightingCapacity=c.fighting_capacity,
        right=1,
        job=c.job,
    )
    return b.complete(msg)


def new_uuid() -> str:
    return uuid.uuid4().hex


# ---- sessões ---------------------------------------------------------------------------------


def online_members(ctx: GameContext, guild_id: int) -> list[GameSession]:
    found = (ctx.online.get(m.character_id) for m in ctx.guilds.members_of(guild_id))
    return [o for o in found if o is not None and o.snapshot is not None]


def on_login(s: GameSession) -> None:
    """Login: o perfil passa a ser o da sessão; os outros membros veem o jogador online (162)."""
    assert s.snapshot is not None
    g = s.ctx.guilds
    g.profiles[s.player_id] = s.snapshot.character
    mine = g.of(s.player_id)
    if mine is not None:
        for o in online_members(s.ctx, mine[0].id or 0):
            if o is not s:
                o.send(162, pb.ConsortiaMsg(otherId=s.player_id))


def on_logout(s: GameSession, fighting_capacity: int) -> None:
    assert s.snapshot is not None
    g = s.ctx.guilds
    s.snapshot.character.fighting_capacity = fighting_capacity  # só para as listas de quem está offline
    g.logout_at[s.player_id] = s.ctx.clock.now()
    mine = g.of(s.player_id)
    if mine is not None:
        for o in online_members(s.ctx, mine[0].id or 0):
            if o is not s:
                o.send(163, pb.ConsortiaMsg(otherId=s.player_id))
