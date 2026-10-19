"""Subida de nível na entrega de missão: o exército é completado com o castelo até a liderança nova e saem 139 (se
faltou soldado), 100, 150 e o 4640 ao chegar no nível do fundo novato (tutorial_en #636-#639 e #1132-#1133, replay
#625-#628 e #938-#939). Ver docs/cidade-externa.md."""

from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Pawn, Quest
from wartune_server.game import rules
from wartune_server.game.session import GameSession
from wartune_server.protocol.messages import wartune_pb2 as pb

QUEST = 51  # 3,000 EXP (tutorial_en #635): do nível 5 para o 6 na captura
LANCER = 10101


def _session(g: Game) -> GameSession:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session


def _almost_six(s: GameSession) -> None:
    """Nível 5 a 1000 EXP do 6, com a missão 51 pronta para entregar."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    six = next(total for grade, total in rules.grade_steps(s.ctx.templates) if grade == 6)
    snap.character.total_gp = six - 1000
    snap.character.grades = snap.leader.grades = 5
    assert snap.castle is not None
    snap.castle.produced_at = datetime(2026, 10, 18, tzinfo=UTC)  # castelo aberto (8281)
    snap.quests.append(Quest(snap.character.id or 0, QUEST, datetime(2026, 10, 18, tzinfo=UTC), progress=2))


def _level_codes(codes: list[int]) -> list[int]:
    return [c for c in codes if c in (139, 100, 150, 4640)]


async def test_castelo_vazio_manda_139_100_150_e_4640(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = _session(g)
        _almost_six(s)
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=QUEST))
        got = await g.until(52)
        assert _level_codes([p.code for p in got]) == [139, 100, 150, 4640]  # EN #636-#639
        pawns = pb.ArmyPawnUpdatedMsg.FromString(next(p.body for p in got if p.code == 100))
        assert [(a.tempateId, a.ownPawns) for a in pawns.armyPawn] == [(LANCER, 0)]  # EN #637


async def test_castelo_completa_o_exercito_ate_a_lideranca(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        _almost_six(s)
        pawn = Pawn(snap.character.id or 0, LANCER, castle_count=748)
        snap.pawns.append(pawn)
        pawn.army_count = rules.leader_stats(snap, s.ctx.templates).total["ConatArmy"]  # cheio no nível 5
        five = pawn.army_count
        g.client.send(5014, pb.QuestFinishedReqMsg(templateId=QUEST))
        got = await g.until(52)
        assert _level_codes([p.code for p in got]) == [100, 150, 4640]  # sem 139: o castelo tinha tropa
        six = rules.leader_stats(snap, s.ctx.templates).total["ConatArmy"]
        assert six - five == 10  # EN #624/#638: liderança 142 -> 152
        assert (pawn.army_count, pawn.castle_count) == (six, 748 - (six - five))
        castle = pb.ArmyPawnUpdatedMsg.FromString(next(p.body for p in got if p.code == 100))
        assert [(a.tempateId, a.ownPawns) for a in castle.armyPawn] == [(LANCER, 748 - (six - five))]
        army = pb.ArmyArmyMsg.FromString(next(p.body for p in got if p.code == 150))
        assert [a.ownPawns for a in army.armyPawn] == [six]
        saved = await g.server.services.characters.snapshot(g.user_id)  # gravado com a entrega
        assert [(p.castle_count, p.army_count) for p in saved.pawns] == [(pawn.castle_count, six)]
