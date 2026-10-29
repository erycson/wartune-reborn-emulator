"""Tipos de condição de missão por grupo (guilda, arena e batalhas, equipamento, demais): ver docs/missoes.md e
as constantes em ``game/rules.py``. Cada teste confere o ``condition_1`` que o 112 levaria."""

from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import PlayerSnapshot, Quest
from wartune_server.game import rules
from wartune_server.game.handlers import vehicle
from wartune_server.game.session import GameSession
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb

S_QUESTS = 112


def _session(g: Game) -> GameSession:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s


def _snap(g: Game) -> PlayerSnapshot:
    snap = _session(g).snapshot
    assert snap is not None
    return snap


def _open(g: Game, *template_ids: int) -> None:
    now = datetime.now(UTC)
    _snap(g).quests.extend(Quest(g.user_id, t, now) for t in template_ids)


def _progress(g: Game, template_id: int) -> int:
    return next(rules.progress_of(q, 0) for q in _snap(g).quests if q.template_id == template_id)


def _quests(got: list[Packet]) -> dict[int, int]:
    out: dict[int, int] = {}
    for p in got:
        if p.code == S_QUESTS:
            for q in pb.QuestUpdatedRspMsg.FromString(p.body).quest:
                out[q.templateId] = q.condition_1
    return out


async def test_guilda_contribuicao_29_sobe_pelo_estado(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _open(g, 221)  # tipo 29, Para2 10
        _snap(g).character.consortia_total_offer = 12
        rules.social_state_quests(_snap(g), _session(g).ctx.templates, None)
        assert _progress(g, 221) == 12


async def test_tanques_79_e_80_contam_com_para1_0_e_3001(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _open(g, 912, 914, 913, 915)
        await vehicle._count(_session(g), rules.TANK_JOIN_CONDITION)
        await vehicle._count(_session(g), rules.TANK_WIN_CONDITION)
        got = _quests(await g.idle())
        assert got == {912: 1, 914: 1, 913: 1, 915: 1}


async def test_equipamento_reforco_17_e_pedras_77(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _open(g, 121, 908)  # 121: reforçar ao 3 (Para1 2, grau > Para1); 908: gastar pedras (Para1 0)
        snap, templates = _snap(g), _session(g).ctx.templates
        assert not rules.quest_event(snap, templates, 17, 2, 1)  # grau 2 ainda não passa
        assert rules.quest_event(snap, templates, 17, 3, 1)
        rules.quest_event(snap, templates, rules.RUNE_COMBINE, 3020010, 4)
        assert (_progress(g, 121), _progress(g, 908)) == (1, 4)


async def test_alquimia_64_conta_no_8321(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _snap(g).character.grades = 20
        _open(g, 184)
        await g.idle()
        g.client.send(8321, pb.PlayerLuckyMsg())
        got = _quests(await g.until(S_QUESTS) + await g.idle())
        assert got[184] == 1
