"""Guilda: eleição do chefe e recrutamento no chat."""

from __future__ import annotations

from ....protocol.messages import wartune_pb2 as pb
from ... import guild as gd
from ...builders import login as b
from ...router import router
from ...session import GameSession
from .common import S_VOTED, S_VOTERS, _mine, _profile, _refuse

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
