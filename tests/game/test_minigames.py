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

# fundo normal da 0038 (hora do jogo; o harness roda em UTC): compra até 18 23:59:59, resgate de 19 a 23
BUYING = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
HARVEST = datetime(2026, 10, 19, 0, 0, 1, tzinfo=UTC)  # 19 00:00:01 no jogo
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

        g.client.send(9638)
        got = await g.idle()
        assert pb.SimplePropertyMsg.FromString(_body(got, 414)).param7 is False
        assert pb.ChairsListMsg.FromString(_body(got, 415)).luckyNickName == []

        g.client.send(9645, extend1=minigames.ORE_OP)
        got = await g.idle()
        assert [p.code for p in got] == [190] and pb.SimplePropertyMsg.FromString(got[0].body).param7 is False

        g.client.send(9610, pb.LuckExchangeOpMsg(exchangeId="x", exchangeCount=1))  # sem edição: recusa
        got = await g.idle()  # (visto) #11765-#11767: 111 "Insufficient exchange items." e o 4247 zerado
        assert [p.code for p in got] == [111, 4247]
        assert pb.ChatChannelMsg.FromString(got[0].body).encodeMsg == "Insufficient exchange items."
        assert [r.rate for r in pb.RateUpdateReqMsg.FromString(got[1].body).rateInfo] == [0]  # linha zerada, sem evento

        g.client.send(8703)
        assert pb.DepositActiveMsg.FromString(_body(await g.idle(), 4612)).activeType == 0

        g.client.send(8534)
        assert [p.code for p in await g.idle()] == [4428]

        g.client.send(9520)
        # (visto) 1026-225632-1 #2453: 4933 com o tabuleiro de 36 casas, sem 300 (ver minigames.golden_road)
        got = await g.idle()
        assert [p.code for p in got] == [4933]
        assert len(pb.GoldenRoadMsg.FromString(got[0].body).cellInfo) == 36

        g.client.send(8750)
        assert pb.LotteryMsg.FromString(_body(await g.idle(), 4637)).isOpen is False


def _signin(g: Game, op: int, day: int = 0) -> None:
    g.client.send(9645, pb.SuperSigninCardReqMsg(opType=op, date=day), extend1=minigames.SIGNIN_OP)


def _states(got: list[Packet]) -> list[int]:
    return [d.state for d in pb.SuperSigninCardRespMsg.FromString(_body(got, 513)).details]


async def test_super_signin_card_buys_receives_and_signs_a_missed_day(tmp_path: Path) -> None:
    """0054 (oficial_encantar #118-#119): cartão de 500 Balens; o dia 1 sai na compra, o dia perdido assina por 10."""
    clock = FakeClock(datetime(2026, 10, 23, 10, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        minigames.signin_login(s)
        got = await g.idle()
        assert [p.code for p in got] == [4590, 514]  # sem cartão: nem 513, como o oficial
        top = pb.SimplePropertyMsg.FromString(got[0].body)
        assert (top.param1, top.param4, top.param5, top.param7) == (
            2059,
            "2026-10-23 00:00:00",
            "2026-10-30 00:00:00",
            True,
        )
        temp = pb.SuperSigninRewardMsg.FromString(got[1].body)
        assert (temp.cardPrice, temp.reSigninPrice, temp.temp[0].itemMsg) == (500, 10, "3040001,5|21261044,1")

        c = _snap(g).character
        c.point, c.gift_token = 600, 1000
        _signin(g, minigames.SIGNIN_BUY)  # nível 1: o ícone só abre no 6
        assert _states(await g.idle()) == []
        c.grades = 10
        _signin(g, minigames.SIGNIN_BUY)
        assert _states(await g.idle()) == [1, 0, 0, 0, 0, 0, 0]
        assert (c.point, c.gift_token) == (100, 1000)  # só Balens livres

        _signin(g, minigames.SIGNIN_RECEIVE, 1)
        assert _states(await g.idle()) == [2, 0, 0, 0, 0, 0, 0]
        assert sorted((i.template_id, i.count) for i in _snap(g).items if i.template_id in (3040001, 21261044)) == [
            (3040001, 5),
            (21261044, 1),
        ]
        _signin(g, minigames.SIGNIN_RECEIVE, 2)  # ainda não abriu: recusa, estado igual
        assert _states(await g.idle()) == [2, 0, 0, 0, 0, 0, 0]

        clock.advance(2 * 86400)  # dia 3 do cartão; no dia 2 ninguém entrou
        g.client.send(8750)  # qualquer pedido: quem está no jogo assina o dia
        assert _states(await g.idle()) == [2, 3, 1, 0, 0, 0, 0]
        _signin(g, minigames.SIGNIN_RESIGN, 2)
        assert _states(await g.idle()) == [2, 1, 1, 0, 0, 0, 0]
        assert c.point == 90
        _signin(g, minigames.SIGNIN_BUY)  # um cartão por edição
        assert _states(await g.idle()) == [2, 1, 1, 0, 0, 0, 0] and c.point == 90
        assert [r for r in await _ledger(g) if r[2] == "super_signin"] == [
            (-500, 0, "super_signin"),
            (-10, 0, "super_signin"),
        ]


REBATE_ID = "05E8C640-2BDA-E798-EFE5-CD8663F29F62"  # 0055 (oficial_encantar #61)
PACK_500, PACK_1000 = "A7C07FB5-4874-7375-1344-CD8663F2FE8C", "BFA9BF57-58FF-E0F1-2A9E-CD8663F2FCB7"


async def test_recharge_gift_pack_counts_the_recharges_of_the_window(tmp_path: Path) -> None:
    """Recharge Gift Pack: o pacote sai quando a recarga da janela (cash_ledger ``recharge``) chega ao ``point``."""
    clock = FakeClock(datetime(2026, 10, 23, 10, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        minigames.send_rebate(s)
        info = pb.RebateInfoMsg.FromString(_body(await g.idle(), 4461))
        assert (info.id, len(info.packages)) == (REBATE_ID, 7)
        first = next(p for p in info.packages if p.order == 1)
        assert (first.point, first.itemid1, first.count1, first.itemid8) == (500, 208017, 4, 0)

        c = _snap(g).character
        old = CashLedger(c.id or 0, 900, 0, 900, 0, "recharge", "portal", datetime(2026, 10, 22, tzinfo=UTC))
        new = CashLedger(c.id or 0, 600, 0, 1500, 0, "recharge", "portal", datetime(2026, 10, 23, 9, tzinfo=UTC))
        async with g.server.services.database.sessions() as db:  # como o portal: direto no banco
            db.add_all([old, new])  # só a de dentro da janela conta
            await db.commit()
        g.client.send(8574, pb.RebateOpMsg(id=REBATE_ID, op=1))
        user = pb.UserRebateMsg.FromString(_body(await g.idle(), 4463))
        assert (user.point, user.userid, any(x.isget for x in user.packagestates)) == (600, g.user_id, False)

        for pack in (PACK_500, PACK_500, PACK_1000):  # o segundo 500 já foi; 1000 passa da recarga
            g.client.send(8574, pb.RebateOpMsg(id=REBATE_ID, packageid=pack, op=2))
            user = pb.UserRebateMsg.FromString(_body(await g.idle(), 4463))
        assert [x.id for x in user.packagestates if x.isget] == [PACK_500]
        got = sorted((i.template_id, i.count) for i in _snap(g).items if i.template_id in (208017, 2060487, 2126025))
        assert got == [(208017, 4), (2060487, 5), (2126025, 2)]

        clock.advance(6 * 86400)  # dia 29: acabou, o botão some
        g.client.send(8574, pb.RebateOpMsg(id=REBATE_ID, op=1))
        assert pb.RebateInfoMsg.FromString(_body(await g.idle(), 4461)).id == ""


async def test_recover_list_is_empty_and_refuses_any_recover(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        for kind in (0, 1):  # 0 pede a lista; 1 tenta resgatar: a lista continua vazia
            g.client.send(9503, pb.RecoverReqMsg(type=kind, count=1, way=1))
            got = await g.idle()
            # (visto) 191924-1 #9044 e 1027 #745: 109 depois do 4912 só na lista (type 0)
            assert [p.code for p in got] == ([4912, 109] if kind == 0 else [4912])
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
