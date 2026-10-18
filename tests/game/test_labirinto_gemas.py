"""Labirinto de gemas (9508..9517): a regra da troca e da cascata contra a captura oficial, e os pedidos.

Os dados de ``CAPTURED_*`` vêm de ``captures/av_askeri_ve_odul_toplama.json`` (4922 e 4923/4924, 7 trocas,
10 passos). Cada passo é (marcas que saem, gemas novas, pontos, EXP, prêmio) como o servidor oficial mandou.
"""

import random
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any

from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import BagType, CashLedger, Item, PlayerSnapshot
from wartune_server.game import events as ev
from wartune_server.game import gemmaze as gm
from wartune_server.game.handlers import gemmaze as handler
from wartune_server.game.handlers.gemmaze import _maze_fits
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.templates.repository import GameTemplates

NOW = datetime(2026, 1, 1, tzinfo=UTC)

CAPTURED_BOARD = [1, 3, 2, 2, 1, 4, 3, 4, 4, 3, 1, 4, 3, 1, 3, 1, 3, 5, 5, 1, 4, 1, 3, 5, 5]
CAPTURED_FINAL = [5, 5, 4, 1, 4, 1, 3, 1, 5, 1, 2, 1, 4, 1, 4, 1, 5, 3, 4, 3, 4, 3, 2, 5, 5]
CAPTURED_MOVES: list[tuple[tuple[int, int], list[tuple[list[int], list[tuple[int, int]], int, int, int]]]] = [
    (
        (11, 12),
        [
            ([1, 6, 11, 16], [(1, 3), (6, 1), (11, 5), (16, 5)], 20, 2, 2060008),
            ([16, 17, 18], [(1, 5), (2, 3), (3, 3)], 10, 1, 208027),
        ],
    ),
    ((20, 21), [([10, 15, 20], [(0, 5), (5, 1), (10, 2)], 10, 1, 208027)]),
    ((21, 22), [([12, 17, 22], [(2, 2), (7, 4), (12, 1)], 10, 1, 208027)]),
    ((12, 17), [([17, 18, 19], [(2, 4), (3, 4), (4, 1)], 10, 1, 208014)]),
    (
        (8, 9),
        [
            ([9, 14, 19], [(4, 4), (9, 1), (14, 2)], 10, 1, 2060008),
            ([2, 3, 4], [(2, 1), (3, 2), (4, 1)], 10, 1, 2060008),
        ],
    ),
    (
        (7, 12),
        [
            ([12, 13, 14], [(2, 4), (3, 1), (4, 2)], 10, 1, 2060008),
            ([9, 14, 19], [(4, 3), (9, 5), (14, 2)], 10, 1, 208014),
        ],
    ),
    ((8, 9), [([9, 14, 19], [(4, 4), (9, 1), (14, 4)], 10, 1, 2060008)]),
]


def _body(got: list[Packet], code: int) -> bytes:
    return next(p.body for p in reversed(got) if p.code == code)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _ledger(g: Game) -> list[tuple[int, int, str]]:
    async with g.server.services.database.sessions() as db:
        rows = (await db.execute(select(CashLedger).order_by(CashLedger.id))).scalars()  # type: ignore[arg-type]
        return [(r.delta_point, r.delta_gift_token, r.reason) for r in rows]


def _set_board(g: Game, game: gm.Game) -> None:
    """Põe o tabuleiro no estado da sessão (a linha de ``EventState`` do labirinto), já renovado hoje."""
    session = g.server.online.get(g.user_id)
    assert session is not None
    game.day = game.day or session.ctx.clock.now().date().isoformat()
    ev.state(_snap(g), handler.KEY, NOW).text = game.dump()


def _has_swap_with_match(board: list[int]) -> bool:
    for a in range(gm.CELLS):
        for b in (a + 1, a + gm.SIZE):
            if b < gm.CELLS and gm.neighbors(a, b):
                swapped = list(board)
                swapped[a], swapped[b] = swapped[b], swapped[a]
                if gm.runs(swapped):
                    return True
    return False


# --- regra pura -------------------------------------------------------------------------------


def test_captured_moves_replay_on_the_official_board() -> None:
    board = list(CAPTURED_BOARD)
    for (begin, end), steps in CAPTURED_MOVES:
        board[begin], board[end] = board[end], board[begin]
        for dels, adds, points, exp, reward in steps:
            found = gm.runs(board)
            assert sorted({m for run in found for m in run}) == dels
            assert sum(len(run) - 2 for run in found) == exp and 10 * exp == points
            assert reward in {tid for tid, _ in gm.REWARDS}
            board = gm.fall(board, dels)
            for mark, color in adds:
                board[mark] = color
    assert board == CAPTURED_FINAL


def test_play_resolves_the_captured_first_move() -> None:
    result = gm.play(gm.Game(board=list(CAPTURED_BOARD), exp=61), 11, 12, random.Random(7))
    assert result is not None and result.times == 19
    first = result.steps[0]
    assert (first.dels, first.points, first.exp) == ((1, 6, 11, 16), 20, 2)
    assert (first.reward, first.count) in gm.REWARDS
    assert all(1 <= color <= gm.COLORS for _, color in first.adds)


def test_play_rejects_bad_swaps_and_a_board_without_moves() -> None:
    game = gm.Game(board=list(CAPTURED_BOARD))
    rng = random.Random(1)
    assert gm.play(game, 4, 5, rng) is None  # fim e início de linhas diferentes não são vizinhos
    assert gm.play(game, 0, 0, rng) is None  # a gema não troca com ela mesma
    assert gm.play(game, 0, 25, rng) is None  # fora do tabuleiro
    assert gm.play(gm.Game(board=list(CAPTURED_BOARD), times=0), 11, 12, rng) is None


def test_swap_without_match_spends_a_move_and_keeps_the_swapped_board() -> None:
    result = gm.play(gm.Game(board=list(CAPTURED_BOARD)), 0, 1, random.Random(1))
    assert result is not None
    assert result.steps == () and result.times == 19
    assert (result.board[0], result.board[1]) == (3, 1)


def test_fall_drops_the_survivors_of_a_column_and_leaves_the_top_empty() -> None:
    out = gm.fall(list(range(1, 26)), [6])  # tira a marca 6: a coluna 1 desce uma casa
    assert [out[m] for m in (1, 6, 11, 16, 21)] == [0, 2, 12, 17, 22]
    assert out[0] == 1 and out[2] == 3


def test_new_board_has_no_ready_match_and_at_least_one_move() -> None:
    for seed in range(20):
        game = gm.new_game(random.Random(seed))
        assert len(game.board) == gm.CELLS and set(game.board) <= set(range(1, gm.COLORS + 1))
        assert gm.runs(game.board) == []
        assert _has_swap_with_match(game.board)


def test_game_state_survives_the_json_row() -> None:
    game = gm.Game(list(CAPTURED_BOARD), 13, 4, 2, 7, 44, score=300, week=120, box=5, day="2026-01-01")
    assert gm.Game.load(game.dump()) == game


def test_maze_bag_stacks_up_to_its_48_spaces() -> None:
    templates = GameTemplates({"ItemTempInfos": [MappingProxyType({"TemplateId": "2060008", "MaxCount": "2"})]})
    held = []
    for pos in range(47):
        item = Item(1, 2060008, bag_type=BagType.MAZE, count=1)
        item.pos = pos
        held.append(item)
    snap: Any = SimpleNamespace(items=held)  # só ``items`` é lido
    assert _maze_fits(snap, templates, [(2060008, 1)] * 49)  # 47 pilhas de 1 + 1 espaço novo com 2
    assert not _maze_fits(snap, templates, [(2060008, 1)] * 50)
    assert _maze_fits(snap, templates, [(2060008, 49)]) and not _maze_fits(snap, templates, [(2060008, 50)])


# --- pedidos no servidor ----------------------------------------------------------------------


async def test_open_sends_the_board_and_keeps_it_for_the_next_open(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(9508)
        first = pb.GemMazeInfoMsg.FromString(_body(await g.idle(), 4922))
        assert len(first.allGems) == 25
        assert (first.timesLeft, first.helpTimesLeft, first.maxExp, first.gemLevel) == (20, 5, 30, 0)
        assert list(first.boxesId) == list(handler.BOX_IDS)
        g.client.send(9508)
        again = pb.GemMazeInfoMsg.FromString(_body(await g.idle(), 4922))
        assert [x.color for x in again.allGems] == [x.color for x in first.allGems]
        saved = await g.server.services.characters.snapshot(g.user_id)
        row = ev.peek(saved, handler.KEY)
        assert row is not None and gm.Game.load(row.text).board == [x.color for x in first.allGems]


async def test_login_pushes_the_board_only_when_the_account_has_one(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(8224, pb.PlayerDataMsg(user=True))  # login sem tabuleiro gravado: sem 4922
        assert all(p.code != 4922 for p in await g.idle())
        g.client.send(9508)
        board = pb.GemMazeInfoMsg.FromString(_body(await g.idle(), 4922)).allGems
        again = await g.connect()  # relogin: a conta agora tem tabuleiro, então o 4922 volta no login
        again.client.send(8224, pb.PlayerDataMsg(user=True))
        pushed = pb.GemMazeInfoMsg.FromString(_body(await again.idle(), 4922))
        assert [x.color for x in pushed.allGems] == [x.color for x in board]


async def test_move_plays_the_cascade_pays_the_maze_bag_and_unlocks_the_client(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _set_board(g, gm.Game(board=list(CAPTURED_BOARD), exp=61))
        g.client.send(9509, pb.GemMoveMsg(beginMark=11, endMark=12))
        got = await g.idle()
        updates = [pb.GemInfoUpdateMsg.FromString(p.body) for p in got if p.code == 4923]
        assert sorted(m.mark for m in updates[0].gemDel) == [1, 6, 11, 16]
        assert list(updates[0].score) == [20] and updates[0].curExp == 63
        assert all(len(u.rewardInfo) == 1 for u in updates)
        assert [p.code for p in got][-1] == 4924
        assert any(p.code == 83 and b"Puan 20" in p.body for p in got)
        snap = _snap(g)
        maze = [i for i in snap.items if i.bag_type == BagType.MAZE]
        paid = sum(dict(gm.REWARDS)[u.rewardInfo[0].rewardId] for u in updates)  # 208014 vem 2 por passo
        assert sum(i.count for i in maze) == paid
        saved = await g.server.services.characters.snapshot(g.user_id)
        state = gm.Game.load(ev.peek(saved, handler.KEY).text)
        assert state.times == 19 and state.exp >= 63 and state.score >= 20
        assert sum(i.count for i in saved.items if i.bag_type == BagType.MAZE) == paid


async def test_refused_moves_only_unlock_the_client(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _set_board(g, gm.Game(board=list(CAPTURED_BOARD)))
        g.client.send(9509, pb.GemMoveMsg(beginMark=0, endMark=7))  # não são vizinhos
        assert [p.code for p in await g.idle()] == [4924]
        assert gm.Game.load(ev.peek(_snap(g), handler.KEY).text).times == 20


async def test_buy_times_costs_diamonds_and_stops_at_the_cap(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _, cost, _ = handler._buy_info(g.server.services.templates)  # diamantes por compra do template
        c = _snap(g).character
        c.point = 100
        _set_board(g, gm.Game(board=list(CAPTURED_BOARD), times=20))
        g.client.send(9516, pb.GemMazeBuyTimesMsg(buyTypes=1))
        got = await g.idle()
        assert pb.GemMazeBuyTimesRspMsg.FromString(_body(got, 4927)).moveTimesLeft == 30
        assert c.point == 100 - cost and await _ledger(g) == [(-cost, 0, "gemmaze_buy")]

        _set_board(g, gm.Game(board=list(CAPTURED_BOARD), times=90))  # 90 + 10 passa do teto de 99
        g.client.send(9516, pb.GemMazeBuyTimesMsg(buyTypes=1))
        assert [p.code for p in await g.idle() if p.code == 4927] == []
        assert c.point == 100 - cost


async def test_receive_all_moves_the_maze_bag_into_the_main_bag(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _set_board(g, gm.Game(board=list(CAPTURED_BOARD)))
        g.client.send(9509, pb.GemMoveMsg(beginMark=11, endMark=12))
        await g.idle()
        g.client.send(9517)
        got = await g.idle()
        assert any(p.code == 111 and b"Ba\xc5\x9far" in p.body for p in got)  # "Başarıyla alındı!"
        snap = _snap(g)
        assert not [i for i in snap.items if i.bag_type == BagType.MAZE]
        rewards = {2060008, 208027, 208014}
        assert sum(i.count for i in snap.items if i.bag_type == BagType.BAG and i.template_id in rewards) >= 1


async def test_friend_help_is_refused_without_leaving_the_client_stuck(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        g.client.send(9510, pb.GemMoveInviteMsg(playerIdInvited=1))
        assert [p.code for p in await g.idle()] == [4924]


async def test_box_needs_its_score_and_pays_the_box_item_once(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        _set_board(g, gm.Game(board=list(CAPTURED_BOARD), score=1200))
        g.client.send(9513, pb.GetRewardBoxMsg(boxId=4))  # caixa 3: 1600 pontos, ainda não
        box = pb.GetRewardBoxRspMsg.FromString(_body(await g.idle(), 4928))
        assert box.boxGetMark == 0 and list(box.rewardInfo) == []
        g.client.send(9513, pb.GetRewardBoxMsg(boxId=2))  # caixa 2: 700 pontos
        got = await g.idle()
        box = pb.GetRewardBoxRspMsg.FromString(_body(got, 4928))
        assert box.boxGetMark == 2 and [r.rewardId for r in box.rewardInfo] == [handler.BOX_IDS[1]]
        assert any(p.code == 115 for p in got)
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert [(i.template_id, i.count) for i in saved.items if i.bag_type == BagType.MAZE] == [(2131036, 1)]
        row = ev.peek(saved, handler.KEY)
        assert row is not None and gm.Game.load(row.text).box == 2
        g.client.send(9513, pb.GetRewardBoxMsg(boxId=2))  # de novo: recusa, sem segunda caixa
        assert list(pb.GetRewardBoxRspMsg.FromString(_body(await g.idle(), 4928)).rewardInfo) == []
        assert sum(i.count for i in _snap(g).items if i.bag_type == BagType.MAZE) == 1
        g.client.send(9513, pb.GetRewardBoxMsg(boxId=3))  # não é um bit de caixa
        assert pb.GetRewardBoxRspMsg.FromString(_body(await g.idle(), 4928)).boxGetMark == 2


def test_refresh_renews_moves_score_and_boxes_on_a_new_day_and_keeps_the_level() -> None:
    game = gm.Game(list(CAPTURED_BOARD), times=3, help=0, level=5, exp=61, score=700, week=900, box=1)
    game.day = "2026-01-07"  # quarta
    gm.refresh(game, datetime(2026, 1, 7, 23, tzinfo=UTC))  # mesmo dia: nada muda
    assert (game.times, game.score, game.box) == (3, 700, 1)
    gm.refresh(game, datetime(2026, 1, 8, 12, tzinfo=UTC))  # dia seguinte, mesma semana
    assert (game.times, game.help, game.score, game.box, game.week) == (20, 5, 0, 0, 900)
    assert (game.level, game.exp, game.board) == (5, 61, CAPTURED_BOARD)
    game.times = 45  # movimentos comprados não somem
    gm.refresh(game, datetime(2026, 1, 12, 12, tzinfo=UTC))  # segunda: semana nova
    assert (game.times, game.week) == (45, 0)


def test_reward_counts_follow_the_capture() -> None:
    assert dict(gm.REWARDS) == {2060008: 1, 208027: 1, 208014: 2}
