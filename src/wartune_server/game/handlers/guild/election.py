"""Guilda: eleição do chefe e recrutamento no chat."""

from __future__ import annotations

from datetime import datetime, timedelta

from ....domain import gameday
from ....domain.models import Consortia, ConsortiaMember
from ....protocol.messages import wartune_pb2 as pb
from ... import guild as gd
from ... import social
from ...builders import login as b
from ...router import router
from ...session import GameSession
from .. import chat
from .common import S_CHAT, S_VOTED, S_VOTERS, _can, _char, _event, _mine, _now, _profile, _push_info, _refuse, _text

VOTE_OFFER = 100  # chairmanElection.help: "Players with a contribution of at least 100"
VOTING = (3, 4)  # ConsortiaActivityPage: o "Impeach" só aparece com votingState 3 ou 4 (qual é "votando" é dedução)
OPEN_VOTE, NO_VOTE = 3, 0
# chairmanElection.help (cliente, igual no turco): chefe 10 dias offline abre; candidato offline há no máximo 3 dias;
# a votação dura 3 dias
CHAIRMAN_AWAY, CANDIDATE_SEEN, VOTE_DAYS = timedelta(days=10), timedelta(days=3), timedelta(days=3)
CHECK_EVERY = timedelta(seconds=60)

# ---- eleição do chefe ------------------------------------------------------------------------


def _last_seen(s: GameSession, player_id: int) -> datetime | None:
    """Agora para quem está online; senão a última saída ou entrada conhecida (sessão ou banco)."""
    if s.ctx.online.get(player_id) is not None:
        return _now(s)
    c = s.ctx.guilds.profiles.get(player_id)
    seen = [s.ctx.guilds.logout_at.get(player_id), *((c.offline_at, c.last_login_at) if c else ())]
    return max((t for t in seen if t is not None), default=None)


def candidates(s: GameSession, guild: Consortia, at: datetime) -> list[ConsortiaMember]:
    """Os vice-chefes vistos nos últimos 3 dias; sem nenhum, o cargo abaixo, e assim por diante.
    (dedução) a regra dos 3 dias vale também para os cargos de baixo (o texto só fala do vice)."""
    others = [m for m in s.ctx.guilds.members_of(guild.id or 0) if m.duty_id != gd.CHAIRMAN]
    for duty in sorted({m.duty_id for m in others}):
        found = [
            m for m in others
            if m.duty_id == duty and (seen := _last_seen(s, m.character_id)) is not None and at - seen <= CANDIDATE_SEEN
        ]  # fmt: skip
        if found:
            return found
    return []


async def _crown(s: GameSession, guild: Consortia, new: ConsortiaMember) -> None:
    """O eleito vira chefe; o antigo vira membro (como o 5131). Fecha a votação."""
    old = s.ctx.guilds.members.get(guild.chairman_id)
    new.duty_id, guild.chairman_id = gd.CHAIRMAN, new.character_id
    if old is not None:
        old.duty_id = gd.MEMBER
    guild.voting_state = NO_VOTE
    who = _profile(s, new.character_id)
    # TODO(inventado): o texto do evento (sem fonte no cliente/captura)
    event = _event(s, guild, gd.EV_TRANSFER, "Guild Master elected:", (who.nickname if who else None) or "", "")
    await s.ctx.characters.save(guild, new, *([old] if old else []), event)
    _push_info(s, guild)


async def clock(s: GameSession) -> None:
    """No relógio (20008), no máximo uma vez por minuto no servidor: abre, conta e fecha as eleições.

    Chefe offline há 10 dias: com um candidato só, ele vira chefe; com mais, abre a votação (``votingState`` 3, um
    ``votingId`` novo). Votação aberta: o chefe voltando cancela; depois de 3 dias, o mais votado vira chefe (empate:
    o primeiro da lista de candidatos, TODO(inventado)); sem candidato, a votação só fecha."""
    g, now = s.ctx.guilds, _now(s)
    if g.election_at is not None and now - g.election_at < CHECK_EVERY:
        return
    g.election_at = now
    for guild in list(g.guilds.values()):
        if guild.voting_state in VOTING:
            at = guild.voting_at or now
            if s.ctx.online.get(guild.chairman_id) is not None:
                guild.voting_state = NO_VOTE
                await s.ctx.characters.save(guild)
                _push_info(s, guild)
            elif now - at >= VOTE_DAYS:
                cands = candidates(s, guild, at)
                ballots = [x.voted_for for x in g.members_of(guild.id or 0) if x.voted_id == guild.voting_id]
                if cands:
                    await _crown(s, guild, max(cands, key=lambda m: ballots.count(m.character_id)))
                else:
                    guild.voting_state = NO_VOTE
                    await s.ctx.characters.save(guild)
            continue
        seen = _last_seen(s, guild.chairman_id)
        if seen is None or now - seen < CHAIRMAN_AWAY:
            continue
        cands = candidates(s, guild, now)
        if len(cands) == 1:
            await _crown(s, guild, cands[0])
        elif cands:
            guild.voting_state, guild.voting_id, guild.voting_at = OPEN_VOTE, guild.voting_id + 1, now
            await s.ctx.characters.save(guild)
            _push_info(s, guild)


@router.on(8241)
async def voting_list(s: GameSession, _: object) -> None:
    """Candidatos (cargos 1-3) e votos da eleição atual. O cliente (``ElectionListView``) só lista quem tem
    ``isVotingman`` (= candidato) e tira o "já votou" da linha do próprio jogador (``votingTime > 0``), que vai
    mesmo quando ele não é candidato.

    Regra do oficial (cliente inglês ``chairmanElection.help``): chefe offline 10 dias abre a eleição;
    candidatos são os vice-chefes online nos últimos 3 dias (senão os outros cargos); um candidato só
    vira chefe direto; vota quem tem 100+ de contribuição, por 3 dias; o chefe voltando encerra (``clock``).
    """
    mine = _mine(s)
    out = pb.ConsortiaVotingUsersMsg()
    if mine is not None:
        guild, me = mine
        members = s.ctx.guilds.members_of(guild.id or 0)
        voted = guild.voting_id > 0 and me.voted_id == guild.voting_id
        cands = candidates(s, guild, guild.voting_at or _now(s)) if guild.voting_state in VOTING else []
        for m in members:
            candidate = m in cands
            if not candidate and m is not me:
                continue
            c = _profile(s, m.character_id)
            votes = sum(1 for x in members if x.voted_id == guild.voting_id and x.voted_for == m.character_id)
            out.info.add(
                userId=m.character_id,
                nickName=(c.nickname or "") if c else "",
                votingId=guild.voting_id,
                isVotingman=candidate,
                votingTime=int(voted and m is me),
                votingData=votes if guild.voting_id > 0 else 0,
            )
    s.send(S_VOTERS, b.complete(out))


@router.on(8481)
async def vote(s: GameSession, msg: pb.ConsortiaVotingReqMsg) -> None:
    g = s.ctx.guilds
    mine = _mine(s)
    target = g.members.get(msg.votingUser)
    ok = mine is not None and mine[0].voting_state in VOTING and mine[1].voted_id != mine[0].voting_id
    c = _char(s)
    ok = ok and max(c.consortia_total_offer, c.consortia_offer) >= VOTE_OFFER  # ConsortiaModel.hasVotePermission
    ok = ok and mine is not None and target in candidates(s, mine[0], mine[0].voting_at or _now(s))
    if not ok or mine is None or target is None:
        _refuse(s, 8481, "sem eleição, já votou, contribuição < 100 ou candidato inválido", alvo=msg.votingUser)
        s.send(S_VOTED, b.complete(pb.ConsortiaVotingRspMsg(result=False)))
        return
    mine[1].voted_for, mine[1].voted_id = msg.votingUser, mine[0].voting_id
    await s.ctx.characters.save(mine[1])
    s.send(S_VOTED, b.complete(pb.ConsortiaVotingRspMsg(result=True)))


# ---- recrutamento ----------------------------------------------------------------------------


SPEAK_MAX = 54  # RecruitMemberFrame corta em 54 caracteres


@router.on(8335)
async def speak(s: GameSession, msg: pb.ConditionSpeakMsg) -> None:
    """Anúncio de recrutamento ("Recruit Link", ``RecruitMemberFrame``): quem pode recrutar (direito 9, o mesmo do
    botão no chat), ``speakTimes`` por dia da guilda. Sai no canal mundo como o 83 de ``type`` 2 com
    ``consortiaId``/``consortiaName``: o cliente desenha "[guilda]，Recruit Members" clicável (``ChatFormat
    .createConsortiaCellData``, o clique pede para entrar) e depois o texto. Depois, o 164 com o ``speakTimes`` novo.
    TODO(inventado): o canal (mundo) e quem fala (o próprio jogador); sem captura do oficial."""
    mine = _can(s, gd.R_RECRUIT)
    now = s.ctx.clock.now()
    if mine is None or gd.speak_left(s.ctx.templates, mine[0], now) <= 0:
        _refuse(s, 8335, "sem direito ou sem anúncios hoje", texto=msg.speak[:40])
        return
    guild = mine[0]
    day = gameday.today(now)
    guild.speak_count = (guild.speak_count if guild.speak_day == day else 0) + 1
    guild.speak_day = day
    await s.ctx.characters.save(guild)
    c = _char(s)
    out = pb.ChatChannelMsg(channel=chat.WORLD, type=RECRUIT_LINK, encodeMsg=_text(msg.speak)[:SPEAK_MAX])
    out.otherId, out.name, out.consortiaId, out.consortiaName = c.id or 0, c.nickname or "", guild.id or 0, guild.name
    done = b.complete(out)
    for other in s.ctx.online.sessions():
        if not social.blocks(other, s.player_id):
            other.send(S_CHAT, done)
    _push_info(s, guild)


RECRUIT_LINK = 2  # ChatData.type do link da guilda (ChatFormat.getContentCellData)
