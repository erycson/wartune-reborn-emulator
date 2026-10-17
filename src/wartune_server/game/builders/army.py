"""Mensagens de tropas (``ArmyPawnInfoMsg``), no formato das capturas (relay #647, #668-670)."""

from __future__ import annotations

from ...domain.models import Pawn, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates, Row
from .. import rules
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
    """100: tropas no castelo (``armyId`` 0); sem ``pawns``, todas mais os tipos que o quartel já
    libera, com 0 (replay #578: 10101 ownPawns 0). Só esse 100 põe ``canRecruit`` no cliente
    (``ArmyManager.getCasernPawn``); sem ele a célula mostra "Gereken Kışla1" e some o "Asker Al"."""
    msg = pb.ArmyPawnUpdatedMsg()
    if pawns is None:
        pawns = [*snap.pawns, *unlocked_pawns(snap, templates)]
    for pawn in pawns:
        if (tpl := templates.get("PawnTempInfos", pawn.template_id)) is not None:
            msg.armyPawn.append(pawn_msg(pawn, tpl, 0, pawn.castle_count))
    return msg


def unlocked_pawns(snap: PlayerSnapshot, templates: GameTemplates) -> list[Pawn]:
    """Nível 1 dos tipos (SonType 101-109, a lista do quartel) que o quartel libera e o jogador não tem."""
    barracks = rules.building_row(snap, templates, rules.BARRACKS)
    if barracks is None:
        return []
    owned = {p.template_id // 100 for p in snap.pawns}
    return [
        Pawn(snap.character.id or 0, son * 100 + 1)
        for son in range(101, 110)
        if son not in owned
        and (tpl := templates.get("PawnTempInfos", son * 100 + 1)) is not None
        and int(barracks["TemplateId"]) >= int(tpl["NeedBuilding"] or 0)
    ]


def army_pawn_msg(snap: PlayerSnapshot, templates: GameTemplates, army_id: int) -> pb.ArmyPawnInfoMsg | None:
    pawn = next((p for p in snap.pawns if p.army_count > 0), None)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    return pawn_msg(pawn, tpl, army_id, pawn.army_count) if pawn and tpl else None
