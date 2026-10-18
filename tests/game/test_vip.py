from pathlib import Path

from sqlalchemy import select

from tests.game.harness import Game, logged_in
from wartune_server.domain.models import CashLedger, PlayerSnapshot
from wartune_server.protocol.messages import wartune_pb2 as pb


def _snap(g: Game) -> PlayerSnapshot:
    session = g.server.online.get(g.user_id)
    assert session is not None and session.snapshot is not None
    return session.snapshot


async def _ledger(g: Game) -> list[tuple[int, int, str]]:
    async with g.server.services.database.sessions() as db:
        rows = (await db.execute(select(CashLedger).order_by(CashLedger.id))).scalars()  # type: ignore[arg-type]
        return [(r.delta_point, r.delta_gift_token, r.reason) for r in rows]


async def test_alchemy_and_soul_spend_diamonds(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        snap = _snap(g)
        c = snap.character
        g.client.send(8321, pb.PlayerLuckyMsg())  # sem diamante: só devolve o estado
        lucky = pb.PlayerLuckyMsg.FromString((await g.until(4224))[-1].body)
        assert (lucky.luckyCount, lucky.remainCount, lucky.point) == (0, 20, 2) and lucky.gold > 0
        assert await _ledger(g) == []

        c.point, c.gift_token, gold = 5, 100, c.gold
        g.client.send(8321, pb.PlayerLuckyMsg())
        got = await g.until(4224)
        after = pb.PlayerLuckyMsg.FromString(got[-1].body)
        assert (after.luckyCount, after.point) == (1, 4)
        assert (c.point, c.gift_token, c.gold) == (3, 100, gold + lucky.gold)  # vinculado não paga alquimia
        assert await _ledger(g) == [(-2, 0, "alchemy")]

        g.client.send(8467, pb.PlayerRefiningSoulMsg())  # nível < RefiningSoul_Grades (24)
        assert pb.PlayerRefiningSoulMsg.FromString((await g.until(4372))[-1].body).count == 0
        c.grades, strategy = 30, c.strategy
        g.client.send(8467, pb.PlayerRefiningSoulMsg())
        soul = pb.PlayerRefiningSoulMsg.FromString((await g.until(4372))[-1].body)
        assert soul.count == 1 and c.point == 1 and c.strategy == strategy + soul.soul

        saved = await g.server.services.characters.snapshot(g.user_id)
        assert saved.character.point == 1


async def test_vip_open_gift_and_king_contract(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        c = _snap(g).character
        g.client.send(8513, pb.VipOpenInfoMsg(days=31))  # 298 diamantes que não tem
        assert await g.idle() == []

        c.point = 400
        g.client.send(8513, pb.VipOpenInfoMsg(days=31))
        got = await g.until(4416)
        vip = pb.VipInfoMsg.FromString(next(p for p in got if p.code == 4410).body)
        assert (vip.isVip, vip.isExpirt, vip.isTakeGift, vip.vipGp, vip.vipGrade) == (True, False, True, 310, 3)
        assert c.point == 102

        g.client.send(8505)  # presente semanal: VipDrop site 3
        got = await g.until(83)
        assert any(p.code == 115 for p in got)
        assert pb.VipInfoMsg.FromString(next(p for p in got if p.code == 4410).body).isTakeGift is False
        g.client.send(8505)  # mesma semana
        assert await g.idle() == []

        need = {int(r["Id"]): int(r["NeedPoint"]) for r in g.server.services.templates.rows("KingContracts")}
        c.point = need[2] + 12  # sobram 12 depois do contrato 2; o 3 custa mais que isso
        assert need[3] > c.point
        g.client.send(8540, pb.KingContractBuyMsg(ids=[3], friendId=g.user_id))  # recusado: sem diamante
        g.client.send(8540, pb.KingContractBuyMsg(ids=[2], friendId=g.user_id))
        king = pb.KingContractMsg.FromString((await g.until(4434))[-1].body)
        assert len(king.kingContractInfos) == 7 and c.point == 12
        assert await _ledger(g) == [(-298, 0, "vip"), (-need[2], 0, "king_contract")]

        g.client.send(8519, pb.VipRouletteMsg())  # sem tabela: 4414 vazio (o cliente só tira a máscara)
        assert [p.code for p in await g.idle()] == [4414]
