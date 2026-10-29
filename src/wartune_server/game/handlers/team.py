"""Times livres (FreedomTeam): aceitar convite, convidar amigo, capitão, posições de combate e expulsar.

Estado em ``GameContext.teams`` (``game/teams.py``). Só amigos são convidados e só quem está online.
Sair por pedido: 8741 (sai de vez) e 8740 (sai por ora: continua no time, marcado como ausente). A recusa de
convite de time é 8746 (o mesmo código de ``C_TREASUREMAP_REQUEST``, que não tem remetente). Ver docs/salas-campanha.md.
"""

from __future__ import annotations

from google.protobuf.message import Message

from ...domain.models import RelationType
from ...protocol.messages import wartune_pb2 as pb
from .. import rules, server_state, social
from ..builders import login as b
from ..router import router
from ..session import GameSession
from ..teams import TEAM_MAX, Team

S_INVITE, S_INFO, S_DISMISS, S_CREATE, S_ADD = 4620, 4624, 4625, 4622, 4626
S_CAPTAIN, S_FIGHT_POS, S_LEFT, S_KICK = 4627, 4628, 4629, 4630
S_AWAY, S_REFUSE_TEAM = 4621, 4635  # 4621 é só um aviso (o cliente só recarrega); 4635 é RefuseFriendRspMsg


def _info(s: GameSession, team: Team, gone: int = 0) -> pb.TeamInfoMsg:
    """``gone``: quem está saindo do jogo agora (ainda na lista de online), sem detalhe como os offline."""
    out = pb.TeamInfoMsg(teamId=team.id, memberId=team.members, captainId=team.captain)
    for pid in team.members:
        other = s.ctx.online.get(pid)
        if pid == gone or other is None or other.snapshot is None or other.snapshot.leader is None:
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
                fightingCapacity=rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now()).fighting_capacity,
                onlineState=True,
                hasLeftForNow=pid in team.away,
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
    await _save(s)
    _send_team(s, team, S_ADD if existed else S_CREATE, _info(s, team))


@router.on(8738)
async def invite(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Convida um amigo online (``param1``). Quem não é amigo ou está offline não recebe convite."""
    target = msg.param1
    rel = social.relation_to(s, target)
    other = s.ctx.online.get(target)
    if rel is None or rel.relation != RelationType.FRIEND or other is None or other.snapshot is None:
        s.log.info("8738 recusado", alvo=target)
        return
    if other.snapshot.character.refuse_team_invite:  # 8746: quem recusa convite de time não recebe o 4620
        s.log.info("8738 recusado (alvo recusa convites de time)", alvo=target)
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
    await _save(s)
    _send_team(s, team, S_CAPTAIN, pb.SimplePropertyMsg(param1=team.captain))


@router.on(8737)
async def fight_positions(s: GameSession, msg: pb.MemberFightPosListMsg) -> None:
    """Posições de combate de quem está no time (qualquer membro pode mudar: dedução, sem captura)."""
    team = s.ctx.teams.of(s.player_id)
    if team is None:
        return
    positions = {m.memberId: m.pos for m in msg.memberPos if 0 <= m.pos < TEAM_MAX}
    s.ctx.teams.set_positions(team, positions)
    await _save(s)
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
    dissolved = s.ctx.teams.remove(team, target)
    await _save(s)
    if dissolved:
        _send_team(s, team, S_DISMISS, None)
    else:
        _send_team(s, team, S_INFO, _info(s, team))


def _quit(s: GameSession, notify_self: bool) -> None:
    """Sai do time e avisa. Com dois membros o time acaba (4625 aos que sobraram); senão os demais veem a saída
    (4629) e, se era o capitão, o novo (4627). ``notify_self``: o próprio jogador também recebe o que tira o time
    da tela dele (o 4629 com o próprio id ou o 4625). Na desconexão não há tela para avisar."""
    before = s.ctx.teams.of(s.player_id)
    was_captain = before is not None and before.captain == s.player_id
    left = s.ctx.teams.leave(s.player_id)
    if left is None:
        return
    team, dissolved = left
    if dissolved:
        _send_team(s, team, S_DISMISS, None)
        if notify_self:
            s.send(S_DISMISS)
        return
    if notify_self:
        s.send(S_LEFT, pb.SimplePropertyMsg(param1=s.player_id))
    _send_team(s, team, S_LEFT, pb.SimplePropertyMsg(param1=s.player_id))
    if was_captain:
        _send_team(s, team, S_CAPTAIN, pb.SimplePropertyMsg(param1=team.captain))


def leave_team(s: GameSession) -> None:
    """Desconexão: os convites somem, mas o jogador fica no time (``server_states``); os demais recebem o 4624 sem
    o detalhe dele (offline). (dedução) sem captura de relogar em time (docs/salas-campanha.md)."""
    s.ctx.teams.drop_invites(s.player_id)
    team = s.ctx.teams.of(s.player_id)
    if team is not None:
        _send_team(s, team, S_INFO, _info(s, team, gone=s.player_id))


def login(s: GameSession) -> None:
    """Login de quem está num time (gravado): o 4624 para ele e para os demais (o detalhe dele volta)."""
    team = s.ctx.teams.of(s.player_id)
    if team is None:
        return
    info = _info(s, team)
    s.send(S_INFO, info)
    for pid in team.members:
        other = s.ctx.online.get(pid)
        if other is not None and other is not s:
            other.send(S_INFO, info)


async def _save(s: GameSession) -> None:
    await server_state.save(s.ctx, server_state.TEAMS)


@router.on(8741)
async def quit_team(s: GameSession, _: object) -> None:
    """Sai de vez (``FreedomTeamManageFrame.__requestQuitBtnHandler``, depois da confirmação)."""
    _quit(s, notify_self=True)
    await _save(s)


@router.on(8740)
async def leave_for_now(s: GameSession, _: object) -> None:
    """Sai por ora: continua no time marcado como ausente (``hasLeftForNow``), e alterna. O cliente não chama
    ``sendAFK`` em lugar nenhum, então o efeito vem do campo do protocolo (dedução)."""
    team = s.ctx.teams.of(s.player_id)
    if team is None:
        s.log.info("8740 recusado: sem time")
        return
    s.ctx.teams.toggle_away(team, s.player_id)
    await _save(s)
    _send_team(s, team, S_AWAY, pb.SimplePropertyMsg(param1=s.player_id))
    _send_team(s, team, S_INFO, _info(s, team))


@router.on(8746)
async def refuse_team_invite(s: GameSession, _: object) -> None:
    """Alterna a recusa de convites de time (``PlayerMsg.refuseTeamInvite``). O cliente manda a cada troca."""
    assert s.snapshot is not None
    c = s.snapshot.character
    c.refuse_team_invite = not c.refuse_team_invite
    await s.ctx.characters.save(c)
    s.send(S_REFUSE_TEAM, pb.RefuseFriendRspMsg(result=c.refuse_team_invite))
