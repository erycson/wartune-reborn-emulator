"""Mensagens de tropas (``ArmyPawnInfoMsg``), no formato das capturas (relay #647, #668-670)."""

from __future__ import annotations

from ...domain.models import Pawn, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates, Row
from .login import complete

# ordem de pawnLive no cliente (o oficial manda as 7; o cliente lê pelo menos 0..5)
PAWN_LIVE = ("Attack", "Defence", "MagicAttack", "MagicDefence", "Live", "ForceHit", "Parry")


def pawn_msg(pawn: Pawn, tpl: Row, army_id: int, count: int) -> pb.ArmyPawnInfoMsg:
    msg = pb.ArmyPawnInfoMsg(
        armyId=army_id,
        sites=0,
        sonType=int(tpl["SonType"]),
        tempateId=pawn.template_id,
        ownPawns=count,
        fightPos=pawn.fight_pos,
        specialTempIds=pawn.specials,
        blessNum=pawn.bless,
    )
    if pawn.comprehend:
        msg.comprehednTempIds = pawn.comprehend
    for column in PAWN_LIVE:
        complete(msg.pawnLive.add(tempData=int(tpl.get(column, 0))))
    return msg


def castle_pawns(
    snap: PlayerSnapshot, templates: GameTemplates, pawns: list[Pawn] | None = None
) -> pb.ArmyPawnUpdatedMsg:
    """100: tropas no castelo (``armyId`` 0); sem ``pawns``, todas."""
    msg = pb.ArmyPawnUpdatedMsg()
    for pawn in snap.pawns if pawns is None else pawns:
        if (tpl := templates.get("PawnTempInfos", pawn.template_id)) is not None:
            msg.armyPawn.append(pawn_msg(pawn, tpl, 0, pawn.castle_count))
    return msg


def army_pawn_msg(snap: PlayerSnapshot, templates: GameTemplates, army_id: int) -> pb.ArmyPawnInfoMsg | None:
    pawn = next((p for p in snap.pawns if p.army_count > 0), None)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    return pawn_msg(pawn, tpl, army_id, pawn.army_count) if pawn and tpl else None
