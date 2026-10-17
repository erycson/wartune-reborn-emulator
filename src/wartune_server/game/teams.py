"""Time livre (``FreedomTeam``): até 4 jogadores, o capitão convida amigos e define as posições.

Em memória, no ``GameContext``, pelo mesmo motivo das salas (``rooms.py``): o capitão mexe em
membros que estão online em outras sessões. Só amigos entram: o cliente só oferece convite para
quem tem ``relation == 1`` (``FreedomTeamManager.inviteMember``), e o servidor confere de novo.
Pacotes em ``handlers/team.py``; regras em docs/salas-campanha.md.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

TEAM_MAX = 4  # FreedomTeamManager.as: convida só com menos de 4 membros


@dataclass
class Team:
    id: int
    captain: int
    members: list[int]
    fight_pos: dict[int, int] = field(default_factory=dict)  # userId -> posição no combate


class Teams:
    def __init__(self) -> None:
        self._teams: dict[int, Team] = {}
        self._of: dict[int, int] = {}  # userId -> teamId
        self._invites: dict[int, int] = {}  # convidado -> quem convidou (um convite por vez)
        self._ids = itertools.count(1)

    def of(self, player_id: int) -> Team | None:
        team_id = self._of.get(player_id)
        return self._teams.get(team_id) if team_id is not None else None

    def invite(self, inviter: int, invitee: int) -> bool:
        if invitee == inviter or invitee in self._of or invitee in self._invites:
            return False
        team = self.of(inviter)
        if team is not None and len(team.members) >= TEAM_MAX:
            return False
        self._invites[invitee] = inviter
        return True

    def accept(self, invitee: int, inviter: int) -> Team | None:
        """Aceita o convite pendente de ``inviter``. Cria o time se o convidador ainda não tem um."""
        if self._invites.get(invitee) != inviter:
            return None
        del self._invites[invitee]
        team = self.of(inviter)
        if team is None:
            team = Team(next(self._ids), inviter, [inviter])
            self._teams[team.id] = team
            self._of[inviter] = team.id
        elif len(team.members) >= TEAM_MAX:
            return None
        team.members.append(invitee)
        self._of[invitee] = team.id
        return team

    def decline(self, invitee: int, inviter: int) -> bool:
        if self._invites.get(invitee) != inviter:
            return False
        del self._invites[invitee]
        return True

    def has_invite(self, invitee: int, inviter: int) -> bool:
        return self._invites.get(invitee) == inviter

    def hand_captain(self, team: Team, player_id: int) -> bool:
        if player_id not in team.members or player_id == team.captain:
            return False
        team.captain = player_id
        return True

    def remove(self, team: Team, player_id: int) -> list[int]:
        """Tira ``player_id`` do time. Com um só membro sobrando o time acaba; devolve quem saiu."""
        team.members.remove(player_id)
        del self._of[player_id]
        if player_id == team.captain and team.members:
            team.captain = team.members[0]
        if len(team.members) >= 2:
            return [player_id]
        gone = [player_id, *team.members]
        for p in team.members:
            self._of.pop(p, None)
        del self._teams[team.id]
        return gone

    def leave(self, player_id: int) -> tuple[Team, list[int]] | None:
        """Saída pela desconexão: mesma regra de ``remove``. ``None`` se não está em time.

        Convites pendentes nos dois sentidos somem: os que ele recebeu e os que mandou.
        """
        self._invites = {k: v for k, v in self._invites.items() if k != player_id and v != player_id}
        team = self.of(player_id)
        if team is None:
            return None
        return team, self.remove(team, player_id)

    def set_positions(self, team: Team, positions: dict[int, int]) -> None:
        team.fight_pos = {p: pos for p, pos in positions.items() if p in team.members}
