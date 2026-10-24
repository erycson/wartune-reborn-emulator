"""Painel de atividades: o catálogo oficial do data/events.json, a troca (tipo 10), as que ainda vão começar e o gasto
de Balens (tipo 1)."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.game.harness import Game, logged_in
from tests.game.test_atividades_contadas import _session
from tests.game.test_shop import LUCK_GIFT, LUCK_POINT, buy
from wartune_server.domain.models import Item
from wartune_server.game import events as ev
from wartune_server.game.handlers import events as hev
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

CAPTURE = Path(__file__).parents[2] / "captures" / "tutorial_en.json"
START = datetime(2026, 10, 18, 12, tzinfo=UTC)
CAN, TAKEN, NOT_YET = 1, 2, 3
HORN = 208002  # Bullhorn (Large), empilhável
END = START + timedelta(days=7)


def _active(
    active_id: str, active_type: int, getway: int, packages: tuple[ev.Package, ...], begin: datetime = START
) -> ev.Active:
    return ev.Active(active_id, active_type, "t", "d", "c", getway, 1, begin, END, packages)


CATALOG = ev.EventCatalog(
    9,
    (
        # 2 Bullhorns por 1000 de ouro, duas vezes no máximo (o 2º item é o custo mostrado, templateType 4)
        _active("TROCA", 10, 2, (ev.Package("T1", 1, (11, 2, HORN), ((-100, 1000, 1), (HORN, 2, 4)), limit=2),)),
        _active("GASTO", 1, 1, (ev.Package("G1", 1, (9, 70), ((-100, 500, 1),)),)),
        _active("DEPOIS", 13, 3, (ev.Package("D1", 1, (14, 1), ((-100, 1, 1),)),), begin=START + timedelta(days=1)),
    ),
)


async def _data(g: Game) -> dict[str, tuple[int, list[tuple[int, int]]]]:
    """activeId -> (value, [(status, getCount)]) do 4476."""
    g.client.send(8586, pb.SumActiveGetPackageMsg(type=1))
    msg = pb.SumActiveDataMsg.FromString((await g.until(4476))[-1].body)
    return {d.activeId: (d.value, [(p.status, p.getCount) for p in d.packdata]) for d in msg.datas}


def test_catalogo_do_operador_traz_as_41_do_oficial_como_a_captura() -> None:
    catalog = ev.EventCatalog.load(Path(__file__).parents[2] / "data" / "events.json")
    packets = json.loads(CAPTURE.read_text(encoding="utf-8"))
    official = [
        a
        for p in packets
        if not p["isClient"] and p["code"] == 4475
        for a in pb.SumActivesMsg.FromString(bytes.fromhex(p["bodyHex"])).actives
    ]
    assert len(official) == 41
    for want in official:
        a = catalog.active(want.activeId)
        assert a is not None and hev.active_info(a) == want, want.title
    [data] = [pb.SumActiveDataMsg.FromString(bytes.fromhex(p["bodyHex"])) for p in packets if p["index"] == 68]
    limits = {p.packId: p.getCount for d in data.datas if d.type == hev.EXCHANGE for p in d.packdata}
    mine = {p.package_id: p.limit for a in catalog.actives if a.active_type == hev.EXCHANGE for p in a.packages}
    assert mine == limits  # o personagem novo ainda não trocou: o getCount do #68 é o limite
    charges = {d.activeId: d.activeCharge for d in data.datas if catalog.active(d.activeId) is not None}
    assert {a.active_id: a.charge for a in catalog.actives if a.active_id in charges} == charges
    assert catalog.data_stamp > 3  # o cliente só troca o cache quando sobe


async def test_troca_gasta_o_item_respeita_o_limite_e_a_que_vai_comecar_so_aparece(tmp_path: Path) -> None:
    clock = FakeClock(START)
    async with logged_in(tmp_path, novice=19000, clock=clock) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        s.ctx = replace(s.ctx, events=CATALOG)

        hev._send_actives(s)  # o login: a que começa amanhã já vai no 4475
        got = await g.idle()
        listed = [a.activeId for p in got if p.code == 4475 for a in pb.SumActivesMsg.FromString(p.body).actives]
        assert listed == ["TROCA", "GASTO", "DEPOIS"]
        data = await _data(g)
        assert data["TROCA"][1] == [(NOT_YET, 2)] and data["DEPOIS"][1] == [(NOT_YET, 0)]
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId="DEPOIS", packageId="D1", count=1))
        assert await g.idle() == []  # ainda não começou

        horn = Item(g.user_id, HORN, pos=5, count=5)
        snap.items.append(horn)
        await s.ctx.characters.save(horn)
        assert (await _data(g))["TROCA"][1] == [(CAN, 2)]
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId="TROCA", packageId="T1", count=3))
        assert await g.idle() == []  # 3 vezes passa do limite de 2

        gold = snap.character.gold
        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId="TROCA", packageId="T1", count=2))
        got = await g.until(83)
        assert [p.code for p in got] == [115, 3, 109, 4476, 111, 4476, 83]
        assert horn.count == 1 and snap.character.gold == gold + 2000
        assert (await _data(g))["TROCA"][1] == [(TAKEN, 0)]
        saved = await s.ctx.characters.snapshot(g.user_id)
        assert [i.count for i in saved.items if i.template_id == HORN] == [1]

        g.client.send(8586, pb.SumActiveGetPackageMsg(type=2, activeId="TROCA", packageId="T1", count=1))
        assert await g.idle() == []  # limite usado


async def test_gasto_de_balens_conta_na_atividade_do_tipo_1(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, clock=FakeClock(START)) as g:
        s = _session(g)
        snap = s.snapshot
        assert snap is not None
        s.ctx = replace(s.ctx, events=CATALOG)
        snap.character.point, snap.character.gift_token = 1000, 1000
        await s.ctx.characters.save(snap.character)

        g.client.send(5154, buy(LUCK_POINT, 1, pay_type=1))  # 35 Balens
        await g.until(90)
        assert (await _data(g))["GASTO"] == (35, [(NOT_YET, 0)])
        g.client.send(5154, buy(LUCK_GIFT, 1))  # Balens vinculados: não conta
        await g.until(90)
        assert snap.character.gift_token < 1000 and (await _data(g))["GASTO"][0] == 35
        g.client.send(5154, buy(LUCK_POINT, 1, pay_type=1))
        await g.until(90)
        assert (await _data(g))["GASTO"] == (70, [(CAN, 0)])
        saved = await s.ctx.characters.snapshot(g.user_id)
        assert next(e.value for e in saved.events if e.key == "sum:GASTO") == 70
