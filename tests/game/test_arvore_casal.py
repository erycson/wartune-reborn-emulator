"""Árvore do casal (8773 -> 4678, ``marriageTree`` no 4386): regar, cultivar, limpar, colher e trocar o item."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_marriage import _engage, _session
from wartune_server.domain.models import BagType, Item, MarriageState
from wartune_server.game import farm
from wartune_server.game import marriage_tree as tree
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock


async def _marry(a: Game, b: Game) -> None:
    await _engage(a, b)
    b.client.send(15049, pb.MarriageOpMsg(opType=4, property1=3, payType=1))
    await a.until(4658)
    a.client.send(8759, pb.MarriageOpMsg(opType=5, property5=True))
    await b.until(148)
    await a.idle()
    await b.idle()


async def _op(g: Game, op: int) -> pb.MarriageTreeMsg:
    g.client.send(8773, pb.MarriageOpMsg(opType=op))
    return pb.MarriageTreeMsg.FromString((await g.until(4678))[-1].body)


async def test_marriage_tree_cycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()
    monkeypatch.setattr(tree, "pests", lambda: "1,2,0,0,0")
    async with logged_in(tmp_path, novice=19000, clock=clock) as a:  # maga
        b = await a.join("bruxo", 3)  # type: ignore[call-arg]  # mago: o lado A
        await _marry(a, b)
        sa, sb = _session(a), _session(b)
        assert sa.snapshot is not None and sb.snapshot is not None
        ma, mb = sa.snapshot.marriage, sb.snapshot.marriage
        assert ma is not None and mb is not None and ma.state == MarriageState.MARRIED
        assert ma.tree and ma.tree == mb.tree  # a mesma árvore nas duas linhas

        info = farm.farm_info(sa.snapshot, clock.now(), sa.ctx.templates, own=True)
        assert (info.marriageTree.userIdA, info.marriageTree.userIdB) == (b.user_id, a.user_id)
        assert info.marriageTree.startTime == "" and info.marriageTree.treeState == tree.NO_PESTS

        c = sa.snapshot.character
        c.gold = 200_000
        before = json.loads(ma.tree)["trainBType"]
        assert (await _op(a, 1005)).trainBType != before  # troca o item em dobro do lado B
        assert c.gold <= 100_000 + 1_000  # 100.000 de ouro (mais a produção acumulada)
        await b.until(4678)  # o cônjuge também recebe

        watered = await _op(a, 1001)
        assert watered.startTime and watered.endTime and watered.feedUser == a.user_id
        assert watered.feedCount == 1 and watered.treeState == "1,2,0,0,0"
        assert pb.MarriageTreeMsg.FromString((await b.until(4678))[-1].body).startTime == watered.startTime
        assert json.loads(ma.tree)["feedUser"] == 0  # o efeito da rega não repete

        kind = watered.trainBType
        feed = int(sa.ctx.templates.get("ItemTempInfos", kind)["Feed"])
        item = Item(a.user_id, kind, count=2, bag_type=BagType.STORE, pos=0)
        sa.snapshot.items.append(item)
        await sa.ctx.characters.save(item)
        grown = await _op(a, 1002)
        assert grown.stateValue == feed * 2 * 2 and grown.trainBCount == 1  # em dobro: é o item do lado
        assert item not in sa.snapshot.items

        cleared = await _op(a, 1003)  # só a 1ª hora chegou
        assert cleared.treeState == "0,2,0,0,0"

        clock.advance(5 * 3600 + 1)
        a.client.send(8773, pb.MarriageOpMsg(opType=1004))
        await a.until(115)
        assert json.loads(ma.tree)["isGetB"] is True
        await b.idle()  # descarta os 4678 das operações da esposa
        b.client.send(8773, pb.MarriageOpMsg(opType=1004))
        reset = pb.MarriageTreeMsg.FromString((await b.until(4678))[-1].body)
        assert reset.startTime == "" and not reset.isGetA and not reset.isGetB  # os dois colheram: pede rega
        assert any(i.template_id == 208034 for i in sb.snapshot.items)


def test_chest_by_value() -> None:
    from wartune_server.game.handlers.marriage import _chest

    assert [_chest(v) for v in (0, 199, 200, 799, 800)] == [2060475, 2060475, 2060476, 2060476, 2060477]
