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
from typing import TYPE_CHECKING, Any

from ..domain import gameday
from ..domain.models import Character, Consortia, ConsortiaEvent, ConsortiaInvite, ConsortiaItem, ConsortiaMember
from ..protocol.messages import wartune_pb2 as pb
from ..services.characters import CharacterService
from ..templates.repository import GameTemplates, Row
from . import rules
from .builders import login as b

if TYPE_CHECKING:
    from .session import GameContext, GameSession

CHAIRMAN, VICE, ELDER, MEMBER = 1, 2, 3, 5
# direitos por cargo (visto: 4137 de 171155 #4571, 215937 #112 e 231733 #113, iguais ao turco login.json #116);
# bit i-1 = getRightsByIndex(i)
RIGHTS = {
    1: bytes.fromhex("ffff7fe87f"),
    2: bytes.fromhex("baff744855"),
    3: bytes.fromhex("b0bf704804"),
    4: bytes.fromhex("20fe700004"),
    5: bytes.fromhex("20fe700004"),
}
RIGHTS_LEN = 55
# índices de getRightsByIndex que o cliente usa (m6 ConsortiaStaffPage, ConsortiaPlayerMenu...)
R_CHAIRMAN, R_RESEARCH, R_UPGRADE, R_PLACARD, R_KICK = 1, 2, 3, 4, 5
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
SKILLS = rules.GUILD_SKILL_FIELDS
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


def speak_left(templates: GameTemplates, guild: Consortia, now: datetime) -> int:
    """Anúncios de recrutamento que restam hoje (``speakTimes``). (visto) oficial_20261023-171155-1 #4944: 5 por dia;
    o cliente inglês: "You have {0} more notices available today. (Resets daily at 5A.M.)"."""
    used = guild.speak_count if guild.speak_day == gameday.today(now) else 0
    return max(config(templates, "Consortia_SpeakTimes", SPEAK_PER_DAY) - used, 0)


SPEAK_PER_DAY = 5


def altar_state(guild: Consortia, now: datetime) -> int:
    """Calculado na hora: aberto por 21 min (ou até o altar cair, ``ALTAR_ENDED`` gravado), encerrado até o fim do
    dia, fechado no dia seguinte."""
    at = guild.altar_at
    if at is None or guild.altar_state == ALTAR_CLOSED or not gameday.same_day(at, now):
        return ALTAR_CLOSED
    if guild.altar_state == ALTAR_ENDED:
        return ALTAR_ENDED
    return ALTAR_OPEN if (now - at).total_seconds() < ALTAR_SECONDS else ALTAR_ENDED


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
    invasions: dict[int, Any] = field(default_factory=dict)  # guilda -> ``fam.Invasion`` (Invasores do 7501)
    # guilda -> ``fam.Lords`` (Master Treasure Thief chamado). shortcut: só na memória, um reinício encerra a chamada
    lords: dict[int, Any] = field(default_factory=dict)
    wars: dict[int, Any] = field(default_factory=dict)  # guilda -> ``guildwar.War`` de hoje (as duas do par)
    election_at: datetime | None = None  # última conferência das eleições (``handlers.guild.election.clock``)
    altars: dict[int, Any] = field(default_factory=dict)  # guilda -> ``handlers.altar.Run`` do altar aberto

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

    def add_event(self, guild_id: int, now: datetime, kind: int, *parts: str) -> ConsortiaEvent:
        e = ConsortiaEvent(guild_id, now, remark(*parts), type=kind)
        self.events[guild_id].append(e)
        del self.events[guild_id][:-50]  # ponytail: só os 50 últimos na memória; o banco guarda todos
        return e

    def grade_order(self, guild: Consortia) -> int:
        """Posição da guilda no servidor (``orderInfo.gradeOrder``, aba principal e ranking do m11). *Dedução*: nível,
        depois a riqueza total; o critério do oficial não está no cliente nem nos templates."""
        key = (guild.levels, guild.total_offer)
        return 1 + sum(1 for x in self.guilds.values() if (x.levels, x.total_offer) > key)

    def fight_power(self, guild_id: int) -> int:
        """``fightPower``: soma do poder dos membros (dedução: 884460 para 99 membros no oficial #4944)."""
        found = (self.profiles.get(m.character_id) for m in self.members_of(guild_id))
        return sum(c.fighting_capacity for c in found if c is not None)

    def fight_order(self, guild: Consortia) -> int:
        """``orderInfo.fightPowerOrder``: posição pelo ``fightPower`` (a 1ª do oficial tinha 1 nos dois)."""
        mine = self.fight_power(guild.id or 0)
        return 1 + sum(1 for x in self.guilds.values() if self.fight_power(x.id or 0) > mine)

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


def info_msg(g: Guilds, guild: Consortia, now: datetime, templates: GameTemplates) -> pb.ConsortiaInfoMsg:
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
        fightPower=g.fight_power(guild.id or 0),
        speakTimes=speak_left(templates, guild, now),
    )
    msg.orderInfo.consortiaId, msg.orderInfo.gradeOrder = guild.id or 0, g.grade_order(guild)
    msg.orderInfo.fightPowerOrder = g.fight_order(guild)
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


# ConsortiaEventItem.decode: o remark é partido por "|" e montado pelo tipo (o texto de cada parte é dedução)
EV_KICK = 1  # "Member Changes", 4 partes: nome, texto, nome, texto
EV_MEMBER = 3  # "Member Changes", 2 partes: nome, texto
EV_TRANSFER = 7  # "Transfer Ownership", 3 partes: texto, nome, texto
EV_EVENT = 9  # "Guild Event", 3 partes: texto, nome, texto
EV_UPGRADE = 11  # "Upgrade Guild", 1 parte


def remark(*parts: str) -> str:
    """Um "|" num apelido quebraria as partes do ``ConsortiaEventItem``."""
    return "|".join(p.replace("|", "") for p in parts)[:255]


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
                o.send(162, b.complete(pb.ConsortiaMsg(otherId=s.player_id)))


def on_logout(s: GameSession, fighting_capacity: int) -> None:
    assert s.snapshot is not None
    g = s.ctx.guilds
    s.snapshot.character.fighting_capacity = fighting_capacity  # só para as listas de quem está offline
    g.logout_at[s.player_id] = s.ctx.clock.now()
    from .handlers.guildwar import leave_war  # handlers importa este módulo

    leave_war(s)
    mine = g.of(s.player_id)
    if mine is not None:
        for o in online_members(s.ctx, mine[0].id or 0):
            if o is not s:
                o.send(163, b.complete(pb.ConsortiaMsg(otherId=s.player_id)))
