"""Recuperar EXP (9503/4912): lista do que sobrou ontem, resgate com ouro ou item, some ao resgatar, zera por dia."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tests.game.harness import Game, logged_in
from wartune_server.domain import gameday
from wartune_server.domain.models import PlayerSnapshot
from wartune_server.game import daily
from wartune_server.game import events as ev
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

DAY = 86400


def _snap(g: Game) -> PlayerSnapshot:
    s = g.server.online.get(g.user_id)
    assert s is not None and s.snapshot is not None
    return s.snapshot


async def _list(g: Game, kind: int = 0, count: int = 0, way: int = 0) -> tuple[list[int], dict[int, pb.RecoverInfo]]:
    g.client.send(9503, pb.RecoverReqMsg(type=kind, count=count, way=way))
    got = await g.idle()
    rows = pb.RecoverInfosMsg.FromString(next(p.body for p in reversed(got) if p.code == 4912)).recoverInfos
    return [p.code for p in got], {r.sonType: r for r in rows}


async def test_lista_de_ontem_resgate_e_virada(tmp_path: Path) -> None:
    clock = FakeClock(datetime(2026, 10, 23, 10, tzinfo=UTC))
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = g.server.online.get(g.user_id)
        assert s is not None
        snap, templates = _snap(g), s.ctx.templates
        assert (await _list(g))[1] == {}  # personagem novo: nada de ontem
        c = snap.character
        c.grades, c.gold, c.point, c.gift_token = 29, 1_000_000, 40, 0
        today = gameday.today(clock.now())
        assert snap.arena is not None
        snap.arena.day, snap.arena.challenge_count = today, 5  # 5 das 15 lutas do coliseu
        done = ev.daily(snap, "offer:count", clock.now())
        done.value = 10  # 10 das 20 tarefas do painel

        clock.advance(DAY)
        daily.roll(snap, templates, clock.now())
        codes, rows = await _list(g)
        assert codes == [4912, 109]
        # (visto) d27 #63, nível 29: as linhas 1 e 4 iguais às do oficial
        assert (rows[1].num, rows[1].itemCost, rows[1].itemReward, rows[1].goldCost, rows[1].goldReward) == (
            1, 3, 160320, 100000, 80160)
        assert (rows[4].num, rows[4].itemCost, rows[4].itemReward, rows[4].goldCost, rows[4].goldReward) == (
            10, 10, 334080, 200000, 111360)
        assert (rows[8].num, rows[8].itemReward, rows[8].goldCost) == (10, 100, 0)

        g.client.send(9503, pb.RecoverReqMsg(type=1, count=2, way=2))  # grupo, tudo, com ouro
        got = await g.idle()
        texts = [pb.ChatChannelMsg.FromString(p.body).encodeMsg for p in got if p.code == 111]
        assert texts == ["80,160 EXP gained through Recovery."] and c.gold == 900_000
        assert [p.code for p in got][:2] == [109, 3] and got[-1].code == 4912
        c.grades = 29  # o personagem de teste não tem a EXP do nível 29: a EXP recalcula o nível
        rows = (await _list(g))[1]
        assert 1 not in rows and 4 in rows

        _, rows = await _list(g, 8, 1, 1)  # item sem ter o item: recusado
        assert rows[8].num == 10
        _, rows = await _list(g, 8, 1, 3)  # item que falta pago com RECOVER_POINT (35) diamantes
        assert rows[8].num == 9 and c.point == 5
        assert sum(i.count for i in snap.items if i.template_id == 208001) == 10
        _, rows = await _list(g, 8, 2, 3)  # 9 itens = 315 diamantes: sem saldo
        assert rows[8].num == 9
        _, rows = await _list(g, 8, 2, 2)  # coliseu não tem ouro
        assert rows[8].num == 9

        clock.advance(DAY)  # outro dia: a lista é a de ontem (nada feito: cada atividade cheia)
        daily.roll(snap, templates, clock.now())
        rows = (await _list(g))[1]
        assert (rows[1].num, rows[4].num, rows[8].num) == (1, 20, 15)
