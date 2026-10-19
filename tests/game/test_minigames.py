from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, PlayerSnapshot
from wartune_server.game import events as ev
from wartune_server.game.handlers import minigames
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

# fundo normal da 0041 (hora do jogo; o harness roda em UTC+3): compra até 18 23:59:59, resgate de 19 a 23
BUYING = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
HARVEST = datetime(2026, 10, 18, 21, 0, 1, tzinfo=UTC)  # 19 00:00:01 no jogo
AFTER_FUND = datetime(2026, 11, 1, tzinfo=UTC)  # só depois do login: o ticket vence pelo relógio real
BEFORE_FUND = datetime(2026, 10, 1, tzinfo=UTC)

MINIGAME_CODES = [
    8534,
    8574,
    8604,
    8629,
    8630,
    8634,
    8638,
    8639,
    8640,
    8703,
    8722,
    8723,
    8748,
    8750,
    8751,
    8866,
    8994,
    9500,
    9501,
    9502,
    9503,
    9507,
    9508,
    9509,
    9510,
    9513,
    9515,
    9516,
    9517,
    9520,
    9521,
    9522,
    9523,
    9550,
    9602,
    9610,
    9638,
    9645,
]  # os 38 C>S da lista de minigames (docs/eventos.md)


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _ledger(g: Game) -> list[tuple[int, int, str]]:
    async with g.server.services.database.sessions() as db:
        rows = (await db.execute(select(CashLedger).order_by(CashLedger.id))).scalars()  # type: ignore[arg-type]
        return [(r.delta_point, r.delta_gift_token, r.reason) for r in rows]


def _body(got: list[Packet], code: int) -> bytes:
    return next(p.body for p in reversed(got) if p.code == code)


async def test_every_minigame_opcode_answers_empty_body_without_dropping_the_session(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        for code in MINIGAME_CODES:
            g.client.send(code)  # corpo vazio: o cliente manda assim nos pedidos sem campos
            await g.idle(0.05)
        g.client.send(8750)  # resposta garantida: se a sessão caiu, o idle levanta
        assert any(p.code == 4637 for p in await g.idle())


async def test_closed_minigames_answer_the_closed_state(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(BEFORE_FUND)) as g:
        g.client.send(9500)
        slot = pb.SlotActiveMsg.FromString(_body(await g.idle(), 4901))
        assert slot.open is False

        g.client.send(9502)
        seek = pb.PlayerSeekInfoMsg.FromString(_body(await g.idle(), 4914))
        assert (seek.op, seek.seekCount, seek.state) == (1, 0, 0) and seek.HasField("seekNodeList")

        g.client.send(9638)
        got = await g.idle()
        assert pb.SimplePropertyMsg.FromString(_body(got, 414)).param7 is False
        assert pb.ChairsListMsg.FromString(_body(got, 415)).luckyNickName == []

        g.client.send(9645)
        got = await g.idle()
        assert pb.SimplePropertyMsg.FromString(_body(got, 190)).param7 is False
        assert pb.SimplePropertyMsg.FromString(_body(got, 4590)).param1 == 2059

        g.client.send(9610)
        got = await g.idle()
        assert [p.code for p in got if p.code in (363, 364)] == [364, 363]  # 364 antes do 363

        g.client.send(8703)
        assert pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612)).activeType == 0

        g.client.send(8534)
        assert [p.code for p in await g.idle()] == [4428]

        g.client.send(9520)
        assert [p.code for p in await g.idle()] == [300]  # só o quadro da estrada dourada fecha

        g.client.send(8750)
        assert pb.LotteryMsg.FromString(_body(await g.idle(), 4637)).isOpen is False


async def test_recover_list_is_empty_and_refuses_any_recover(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        for kind in (0, 1):  # 0 pede a lista; 1 tenta resgatar: a lista continua vazia
            g.client.send(9503, pb.RecoverReqMsg(type=kind, count=1, way=1))
            got = await g.idle()
            assert [p.code for p in got] == [4912]
            assert list(pb.RecoverInfosMsg.FromString(got[-1].body).recoverInfos) == []


async def test_novice_fund_buys_one_level_and_harvests_each_tier_once(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = _snap(g).character
        c.grades, c.point = 10, 500

        g.client.send(8751, pb.DepositActiveMsg(opType=1, opParam=1))  # nível 11 é o mínimo
        fund = pb.DepositActiveMsg.FromString(_body(await g.idle(), 4640))
        assert (fund.depositLevel, c.point) == (0, 500) and await _ledger(g) == []

        c.grades, c.point = 11, 100  # 500 diamantes para o nível 1 (tutorial_en #2784)
        g.client.send(8751, pb.DepositActiveMsg(opType=1, opParam=1))
        assert pb.DepositActiveMsg.FromString(_body(await g.idle(), 4640)).depositLevel == 0
        assert (c.point, await _ledger(g)) == (100, [])

        c.point = 600
        g.client.send(8751, pb.DepositActiveMsg(opType=1, opParam=1))
        fund = pb.DepositActiveMsg.FromString(_body(await g.idle(), 4640))
        assert (fund.depositLevel, c.point) == (1, 100)
        assert await _ledger(g) == [(-500, 0, "fund_novice")]

        g.client.send(8751, pb.DepositActiveMsg(opType=1, opParam=2))  # já comprou: recusa
        assert await g.idle() != [] and c.point == 100

        c.grades = 9  # tier 1 pede nível 10
        g.client.send(8751, pb.DepositActiveMsg(opType=2, opParam=1))
        assert pb.DepositActiveMsg.FromString(_body(await g.idle(), 4640)).logs == []

        c.grades, gift = 10, c.gift_token
        g.client.send(8751, pb.DepositActiveMsg(opType=2, opParam=1))
        fund = pb.DepositActiveMsg.FromString(_body(await g.idle(), 4640))
        assert [log.type for log in fund.logs] == [1]
        assert {(i.templateId, i.count) for i in fund.harvestedInfos} == {(-400, 250), (-500, 25)}
        assert (c.point, c.gift_token) == (350, gift + 25)
        assert await _ledger(g) == [(-500, 0, "fund_novice"), (250, 25, "fund_novice")]

        g.client.send(8751, pb.DepositActiveMsg(opType=2, opParam=1))  # de novo: nada
        assert c.point == 350

        g.client.send(8751, pb.DepositActiveMsg(opType=2, opParam=2))  # tier 2 pede nível 20
        assert c.point == 350

        c.grades = 20
        g.client.send(8751, pb.DepositActiveMsg(opType=2, opParam=2))
        await g.idle()
        assert c.point == 600

        saved = await g.server.services.characters.snapshot(g.user_id)
        state = ev.peek(saved, "fund:novice")
        assert state is not None and state.value == 1
        assert ev.peek(saved, "fund:novice:get:1") is not None and ev.peek(saved, "fund:novice:get:2") is not None
        assert saved.character.point == 600


async def test_normal_fund_buys_in_the_buy_window_and_harvests_one_tier_per_day(tmp_path: Path) -> None:
    clock = FakeClock(BUYING)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        c = _snap(g).character
        c.grades, c.point = 11, 1500
        g.client.send(8703, pb.DepositActiveMsg())
        fund = pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612))
        assert (fund.activeType, fund.setEndDate, len(fund.activeParams)) == (1, "2026-10-18 23:59:59", 3)
        assert [(i.templateId, i.count) for i in fund.activeParams[0].itemInfos][0] == (2126025, 25)  # #86

        g.client.send(8703, pb.DepositActiveMsg(opType=1, opParam=1))  # 1000 diamantes
        fund = pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612))
        assert (fund.depositLevel, c.point) == (1, 500) and await _ledger(g) == [(-1000, 0, "fund_normal")]

        g.client.send(8703, pb.DepositActiveMsg(opType=2, opParam=1))  # ainda na compra: sem resgate
        assert pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612)).logs == []

        clock._now = HARVEST
        g.client.send(8703, pb.DepositActiveMsg(opType=2, opParam=1))
        fund = pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612))
        assert fund.activeType == 2 and [log.type for log in fund.logs] == [1]
        g.client.send(8703, pb.DepositActiveMsg(opType=2, opParam=2))  # o 2º tier só 1440 min depois
        assert [log.type for log in pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612)).logs] == [1]
        clock.advance(timedelta(minutes=1440).total_seconds())
        g.client.send(8703, pb.DepositActiveMsg(opType=2, opParam=2))
        assert [log.type for log in pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612)).logs] == [1, 2]

        c.point = 5000
        g.client.send(8703, pb.DepositActiveMsg(opType=1, opParam=2))  # fora da compra: recusa
        await g.idle()
        assert c.point == 5000
        saved = await g.server.services.characters.snapshot(g.user_id)
        assert ev.peek(saved, "fund:normal:AEECCD60-F30C-8381-38D0-CD64DD26B34F:get:2") is not None

        clock._now = AFTER_FUND
        g.client.send(8703, pb.DepositActiveMsg())
        assert pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612)).activeType == 0


async def test_novice_fund_login_push_only_from_level_6(tmp_path: Path) -> None:
    """tutorial_en: o login no nível 1 não manda 4640; o primeiro sai no nível 6 (#639)."""
    async with logged_in(tmp_path, novice=19000) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None
        await g.idle()
        _snap(g).character.grades = 5
        minigames.login_push(session)
        assert 4640 not in [p.code for p in await g.idle()]
        _snap(g).character.grades = 6
        minigames.login_push(session)
        assert 4640 in [p.code for p in await g.idle()]
