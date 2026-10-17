"""Cidade do céu (space, mapa 10000): onde um jogador vê os outros andando.

Todo jogador que já passou do tutorial está "no space" enquanto online, como no oficial (os
4597/4594 continuam chegando com ele no castelo; o cliente guarda a lista e só desenha na cena
SPACE). Detalhes e capturas em docs/mundo-compartilhado.md.
"""

from __future__ import annotations

from ..domain.models import PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import rules
from .builders import login as b
from .session import GameSession

SPACE = 10000
S_CREATE, S_RETURN, S_PRESENT, S_MOVE, S_REMOVE, S_LOOK = 4595, 4606, 4597, 4594, 4607, 149
POST_TUTORIAL = 19000  # noviceProcess da cena do castelo; antes disso o 4595 atrapalharia o tutorial


def room_player(
    snap: PlayerSnapshot, templates: GameTemplates, pos: tuple[int, int], campaign_id: int, *, cloth: str = ""
) -> pb.RoomPlayerMsg:
    """Como o cliente desenha um jogador numa cena (``SpaceManager.readMember``)."""
    c, leader = snap.character, snap.leader
    assert leader is not None
    return b.complete(
        pb.RoomPlayerMsg(
            heroId=leader.id,
            playerId=c.id,
            grades=c.grades,
            nickName=c.nickname or "",
            templateId=leader.template_id,
            arm=rules.arm_avatar(snap, templates),
            cloth=cloth,
            armyId=c.id,
            fightingCapacity=rules.leader_stats(snap, templates).fighting_capacity,
            curPosX=pos[0],
            curPosY=pos[1],
            campaignId=campaign_id,
            onlineState=True,
        )
    )


def member(s: GameSession) -> pb.RoomPlayerMsg:
    assert s.snapshot is not None and s.space_pos is not None
    snap, templates = s.snapshot, s.ctx.templates
    return room_player(snap, templates, s.space_pos, SPACE, cloth=rules.cloth_avatar(snap, templates))


def _positions(sessions: list[GameSession]) -> pb.SpacePlayerMoveMsg:
    msg = pb.SpacePlayerMoveMsg()
    for o in sessions:
        assert o.space_pos is not None
        msg.players.add(playerId=o.player_id).path.add(x=o.space_pos[0], y=o.space_pos[1])
    return msg


def others(s: GameSession) -> list[GameSession]:
    return [o for o in s.ctx.online.sessions() if o is not s and o.space_pos is not None]


def enter(s: GameSession, code: int = S_CREATE) -> None:
    """Login: cria a cena (4595), apresenta quem já está lá e avisa os outros.

    O 4594 só desenha quem o cliente já conhece por um 4597, por isso vai sempre depois dele.
    """
    assert s.snapshot is not None
    if s.snapshot.character.novice_process < POST_TUTORIAL:
        return
    c = s.snapshot.character
    s.space_pos = s.space_pos or (c.space_x, c.space_y)  # onde saiu da última vez
    me = member(s)
    s.send(code, pb.RoomEnterMsg(result=1, player=[me]))  # 4595 no login, 4606 voltando de um mapa
    present = others(s)
    if present:
        s.send(S_PRESENT, pb.RoomEnterMsg(result=1, player=[member(o) for o in present]))
        s.send(S_MOVE, _positions(present))
    for o in present:
        o.send(S_PRESENT, pb.RoomEnterMsg(result=1, player=[me]))
        o.send(S_MOVE, _positions([s]))


def back(s: GameSession) -> None:
    """8688: o jogador pediu para ir à cidade do céu; o 4606 troca a cena."""
    if s.space_pos is None:
        enter(s, S_RETURN)
    else:
        s.send(S_RETURN, pb.RoomEnterMsg(result=1, player=[member(s)]))


def move(s: GameSession, path: list[tuple[int, int]]) -> None:
    """8690: guarda o último ponto e repassa o caminho aos outros (o próprio não recebe eco)."""
    if s.space_pos is None or not path:
        return
    s.space_pos = path[-1]
    assert s.snapshot is not None
    s.snapshot.character.space_x, s.snapshot.character.space_y = s.space_pos  # gravado ao sair
    msg = pb.SpacePlayerMoveMsg()
    player = msg.players.add(playerId=s.player_id)
    for x, y in path:
        player.path.add(x=x, y=y)
    for o in others(s):
        o.send(S_MOVE, msg)


def refresh_look(s: GameSession) -> None:
    """149: o jogador trocou equipamento; os outros redesenham arma e armadura dele."""
    if s.space_pos is None:
        return
    assert s.snapshot is not None
    snap, templates = s.snapshot, s.ctx.templates
    msg = b.complete(
        pb.HeroEquUpdatedMsg(
            playerId=s.player_id,
            armStr=rules.arm_avatar(snap, templates),
            clothStr=rules.cloth_avatar(snap, templates),
            hide=False,
            appellId=0,
        )
    )
    for o in others(s):
        o.send(S_LOOK, msg)


def leave(s: GameSession) -> None:
    """Saiu do jogo: some da tela dos outros (4607)."""
    if s.space_pos is None:
        return
    gone = pb.SpacePlayerMoveMsg()
    gone.players.add(playerId=s.player_id)
    for o in others(s):
        o.send(S_REMOVE, gone)
    s.space_pos = None
