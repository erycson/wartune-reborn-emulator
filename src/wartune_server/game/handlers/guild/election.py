"""Guilda: eleição do chefe e recrutamento no chat."""

from __future__ import annotations

from ....domain import gameday
from ....protocol.messages import wartune_pb2 as pb
from ... import guild as gd
from ... import social
from ...builders import login as b
from ...router import router
from ...session import GameSession
from .. import chat
from .common import S_CHAT, S_VOTED, S_VOTERS, _can, _char, _mine, _profile, _push_info, _refuse, _text

VOTE_OFFER = 100  # chairmanElection.help: "Players with a contribution of at least 100"
VOTING = (3, 4)  # ConsortiaActivityPage: o "Impeach" só aparece com votingState 3 ou 4 (qual é "votando" é dedução)

# ---- eleição do chefe ------------------------------------------------------------------------


@router.on(8241)
async def voting_list(s: GameSession, _: object) -> None:
    """Candidatos (cargos 1-3) e votos da eleição atual. O cliente (``ElectionListView``) só lista quem tem
    ``isVotingman`` (= candidato) e tira o "já votou" da linha do próprio jogador (``votingTime > 0``), que vai
    mesmo quando ele não é candidato.

    Regra do oficial (cliente inglês ``chairmanElection.help``): chefe offline 10 dias abre a eleição;
    candidatos são os vice-chefes online nos últimos 3 dias (senão os outros cargos); um candidato só
    vira chefe direto; vota quem tem 100+ de contribuição, por 3 dias; o chefe voltando encerra.
    ponytail: só o voto está feito, ``voting_state`` ainda só muda pelo banco; abrir/fechar fica para depois.
    """
    mine = _mine(s)
    out = pb.ConsortiaVotingUsersMsg()
    if mine is not None:
        guild, me = mine
        members = s.ctx.guilds.members_of(guild.id or 0)
        voted = guild.voting_id > 0 and me.voted_id == guild.voting_id
        for m in members:
            candidate = m.duty_id <= gd.ELDER
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
    if not ok or mine is None or target is None or target.consortia_id != mine[0].id or target.duty_id > gd.ELDER:
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
