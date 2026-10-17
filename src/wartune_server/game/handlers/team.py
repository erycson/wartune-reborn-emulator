"""Times livres (FreedomTeam): aceitar convite, convidar amigo, capitão, posições de combate e expulsar.

Estado em ``GameContext.teams`` (``game/teams.py``). Só amigos são convidados e só quem está online.
Sair por pedido não tem opcode nesta lista (8740/8741 ficam de fora): o time só é deixado na desconexão.
"""

from __future__ import annotations

from google.protobuf.message import Message

from ...domain.models import RelationType
from ...protocol.messages import wartune_pb2 as pb
from .. import rules, social
from ..builders import login as b
from ..router import router
from ..session import GameSession
from ..teams import TEAM_MAX, Team

S_INVITE, S_INFO, S_DISMISS, S_CREATE, S_ADD = 4620, 4624, 4625, 4622, 4626
S_CAPTAIN, S_FIGHT_POS, S_LEFT, S_KICK = 4627, 4628, 4629, 4630


def _info(s: GameSession, team: Team) -> pb.TeamInfoMsg:
    out = pb.TeamInfoMsg(teamId=team.id, memberId=team.members, captainId=team.captain)
    for pid in team.members:
        other = s.ctx.online.get(pid)
        if other is None or other.snapshot is None or other.snapshot.leader is None:
            continue
        snap = other.snapshot
        leader = snap.leader
        assert leader is not None
        detail = b.complete(
            pb.TeamPlayerInfoMsg(
                playerId=pid,
                nickName=snap.character.nickname or "",
                grades=snap.character.grades,
                heroId=leader.id,
                templateId=leader.template_id,
                armyId=pid,
                fightingCapacity=rules.leader_stats(snap, s.ctx.templates).fighting_capacity,
                onlineState=True,
            )
        )
        out.memberDetail.extend([detail])
    return out


def _send_team(s: GameSession, team: Team, code: int, msg: Message | None) -> None:
    for pid in team.members:
        other = s.ctx.online.get(pid)
        if other is not None:
            other.send(code, msg)


@router.on(8734)
async def answer_invite(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Resposta ao convite: ``param1`` quem convidou, ``param7`` aceitou. Aceitar cria o time se preciso."""
    inviter = msg.param1
    if not msg.param7:
        s.ctx.teams.decline(s.player_id, inviter)
        return
    existed = s.ctx.teams.of(inviter) is not None
    team = s.ctx.teams.accept(s.player_id, inviter)
    if team is None:
        s.log.info("8734 recusado", convidador=inviter)
        return
    _send_team(s, team, S_ADD if existed else S_CREATE, _info(s, team))


@router.on(8738)
async def invite(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Convida um amigo online (``param1``). Quem não é amigo ou está offline não recebe convite."""
    target = msg.param1
    rel = social.relation_to(s, target)
    other = s.ctx.online.get(target)
    if rel is None or rel.relation != RelationType.FRIEND or other is None:
        s.log.info("8738 recusado", alvo=target)
        return
    if not s.ctx.teams.invite(s.player_id, target):
        s.log.info("8738 recusado (time cheio ou convite pendente)", alvo=target)
        return
    team = s.ctx.teams.of(s.player_id)
    assert s.snapshot is not None
    other.send(
        S_INVITE,
        pb.InviteTeamMsg(
            teamId=team.id if team else 0,
            inviterId=s.player_id,
            inviterName=s.snapshot.character.nickname or "",
        ),
    )


@router.on(8736)
async def change_captain(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    team = s.ctx.teams.of(s.player_id)
    if team is None or team.captain != s.player_id or not s.ctx.teams.hand_captain(team, msg.param1):
        s.log.info("8736 recusado", novo=msg.param1)
        return
    _send_team(s, team, S_CAPTAIN, pb.SimplePropertyMsg(param1=team.captain))


@router.on(8737)
async def fight_positions(s: GameSession, msg: pb.MemberFightPosListMsg) -> None:
    """Posições de combate de quem está no time (qualquer membro pode mudar: dedução, sem captura)."""
    team = s.ctx.teams.of(s.player_id)
    if team is None:
        return
    positions = {m.memberId: m.pos for m in msg.memberPos if 0 <= m.pos < TEAM_MAX}
    s.ctx.teams.set_positions(team, positions)
    out = pb.MemberFightPosListMsg(isGet=False)
    out.memberPos.extend([pb.MemberFightPos(memberId=p, pos=pos) for p, pos in team.fight_pos.items()])
    _send_team(s, team, S_FIGHT_POS, out)


@router.on(8739)
async def kick_member(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    team = s.ctx.teams.of(s.player_id)
    target = msg.param1
    if team is None or team.captain != s.player_id or target == s.player_id or target not in team.members:
        s.log.info("8739 recusado", alvo=target)
        return
    _send_team(s, team, S_KICK, pb.SimplePropertyMsg(param1=target))  # o expulso também recebe
    if s.ctx.teams.remove(team, target):
        _send_team(s, team, S_DISMISS, None)
    else:
        _send_team(s, team, S_INFO, _info(s, team))


def leave_team(s: GameSession) -> None:
    """Desconexão: sai do time (e limpa convites). Com dois membros o time acaba (4625); senão os demais
    veem a saída (4629) e, se era o capitão, o novo (4627)."""
    before = s.ctx.teams.of(s.player_id)
    was_captain = before is not None and before.captain == s.player_id
    left = s.ctx.teams.leave(s.player_id)
    if left is None:
        return
    team, dissolved = left
    if dissolved:
        _send_team(s, team, S_DISMISS, None)
        return
    _send_team(s, team, S_LEFT, pb.SimplePropertyMsg(param1=s.player_id))
    if was_captain:
        _send_team(s, team, S_CAPTAIN, pb.SimplePropertyMsg(param1=team.captain))
