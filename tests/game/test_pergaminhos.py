"""Pergaminhos de efeito (SonType 201, ``game/buffs.py``): 115, 110 e 4188 como na captura turca
``exp_kitabi_kullanim...`` (2013002; só turco: a inglesa não usa o pergaminho); EXP Boost dobra a EXP da batalha de campanha só dentro do prazo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.game.harness import Game, logged_in
from tests.game.test_shop import codes, me
from tests.test_end_to_end import TEMPLATES
from wartune_server.domain.models import Item
from wartune_server.game import battle as battle_mod
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")

EXP_LV1, EXP_LV2, EXP_LV3, GOLD_SCROLL = 2013001, 2013002, 2013003, 2010501
START = datetime(2026, 1, 1, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fast_battles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)


async def _give(g: Game, template_id: int, pos: int = 0, count: int = 1) -> Item:
    item = Item(g.user_id, template_id, pos=pos, count=count)
    me(g).items.append(item)
    await g.server.services.characters.save(item)
    return item


async def _use(g: Game, pos: int = 0, last: int = 3) -> list:  # type: ignore[type-arg]
    g.client.send(5006, pb.ItemUseMsg(pos=pos, count=1, bagType=1))
    return await g.until(last)


def _buffer(got: list) -> pb.BufferDataMsg:  # type: ignore[type-arg]
    return pb.ItemBufferRspMsg.FromString(next(p for p in got if p.code == 4188).body).bufferData[0]


async def _first_battle_gp(g: Game) -> int:
    """Primeira batalha do tutorial (gpBonus 5 no template), como em test_tutorial."""
    c = g.client
    c.send(5127, pb.NoviceReqMsgMsg(type=1))
    await g.until(143)
    c.send(5017, pb.NoviceReqMsgMsg(noviceProcess=11300))
    await g.until(1)
    c.send(8196, pb.NodeLockReqMsg(nodeId=1000103, lock=True))
    await g.until(4105)
    c.send(5124, pb.PosMoveMsg(mapId=10001, armyId=g.user_id, routes=[pb.RouteMsg(x=800, y=1180)]))
    c.send(5125, pb.CampaignReqMsg(paraInt1=1000103, paraBool1=True))
    prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
    got = await g.fight(prepare)
    return pb.BattleReportMsg.FromString(next(p for p in got if p.code == 4103).body).gpBonus


async def test_exp_scroll_packets_double_the_battle_exp_and_survive_restart(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000, clock=FakeClock(START)) as g:
        await _give(g, EXP_LV2)
        got = await _use(g)
        assert codes(got) == [115, 150, 4434, 110, 4188, 150, 3]  # (visto) 191924 #2241, sem texto
        effect = pb.PropertyUpdatedMsg.FromString(got[3].body)
        assert (effect.propertyType, effect.value) == (30, 100)
        data = _buffer(got)
        assert (data.templateId, data.validityDate, data.grade, data.type, data.typeTemplateid) == (
            2030,
            60,
            100,
            2,
            EXP_LV2,
        )
        assert not [i for i in me(g).items if i.template_id == EXP_LV2]

        assert await _first_battle_gp(g) == 10  # 5 da batalha x (100 + 100)%

        saved = await g.server.services.characters.snapshot(g.user_id)
        st = next(e for e in saved.events if e.key == "buff:2030")
        assert (st.value, st.text, st.updated_at) == (100, str(EXP_LV2), START + timedelta(minutes=60))


async def test_exp_is_normal_after_the_scroll_ends(tmp_path: Path) -> None:
    clock = FakeClock(START)
    async with logged_in(tmp_path, novice=11000, clock=clock) as g:
        await _give(g, EXP_LV2)
        await _use(g)
        clock.advance(3601)
        assert await _first_battle_gp(g) == 5


async def test_same_grade_adds_time_weaker_is_refused_and_stop_clears(tmp_path: Path) -> None:
    clock = FakeClock(START)
    async with logged_in(tmp_path, novice=11000, clock=clock) as g:
        await _give(g, EXP_LV2, pos=0, count=2)
        weak = await _give(g, EXP_LV1, pos=1)
        await _give(g, EXP_LV3, pos=2)
        await _use(g)
        assert _buffer(await _use(g)).validityDate == 120  # mesmo grau: soma (dedução)

        g.client.send(5006, pb.ItemUseMsg(pos=1, count=1, bagType=1))  # 50% sobre 100%: recusa, sem resposta
        got = await _use(g, pos=2)
        assert codes(got) == [115, 150, 4434, 110, 4188, 150, 3] and weak.count == 1
        assert (_buffer(got).grade, _buffer(got).validityDate) == (200, 60)  # maior substitui grau e tempo

        g.client.send(8283, pb.EffectRemoveReqMsg(templateId=2030))
        got = await g.until(4434)  # (visto) 20261030-151436 #2299-#2304: 110 {30, 0}, 4188 isCancel, 150, 4434
        assert codes(got)[-4:] == [110, 4188, 150, 4434] and _buffer(got).validityDate == 0 and _buffer(got).isCancel
        assert pb.PropertyUpdatedMsg.FromString(next(p.body for p in got if p.code == 110)).value == 0


async def test_power_potion_raises_total_power_until_it_ends(tmp_path: Path) -> None:
    """Lvl. 2 Power Potion (2013502, efeito 2135 "Strength +{Grades}", grau 40): 150 com totalPower +40 (o basePower
    não muda) e o PhyAttack derivado junto; o 8283 devolve os totais sem a poção."""
    async with logged_in(tmp_path, novice=11000, clock=FakeClock(START)) as g:
        me(g).character.grades = 20  # NeedGrades 10
        await _give(g, 2013502)
        got = await _use(g)
        assert codes(got) == [115, 150, 4434, 110, 150, 4188, 150, 3]  # (visto) 191924 #1737: atributo, 150 a mais
        on = pb.ArmyArmyMsg.FromString(got[4].body).simpleHeroInfo
        assert on.totalPower == on.basePower + 40

        g.client.send(8283, pb.EffectRemoveReqMsg(templateId=2135))
        got = await g.until(4434)  # (visto) 20261030-151436 #2910-#2917: 110 {3, -40}, 150, 4188, 150, 4434
        assert codes(got)[-5:] == [110, 150, 4188, 150, 4434]
        assert pb.PropertyUpdatedMsg.FromString(next(p.body for p in got if p.code == 110)).value == -40
        off = pb.ArmyArmyMsg.FromString(next(p.body for p in got if p.code == 150)).simpleHeroInfo
        assert off.totalPower == off.basePower
        assert on.totalPhyAttack - off.totalPhyAttack == 4 * 40  # PhyAttack = 4 x Power


async def test_gold_scroll_raises_the_warehouse_cap(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=11000, clock=FakeClock(START)) as g:
        await _give(g, GOLD_SCROLL)
        got = await _use(g)
        assert codes(got) == [115, 150, 4434, 110, 4188, 109, 150, 3]
        assert pb.CastleYieldMsg.FromString(got[5].body).goldMax == 12500  # 10000 sem armazém (nasce no 9) + 25%


async def test_crit_scroll_sends_the_extra_army(tmp_path: Path) -> None:
    """(visto) oficial_20261024-191924-1 #1737 (Crit Scroll, efeito 2047): 115, 150, 4434, 110, 150, 4188, 150, 3."""
    async with logged_in(tmp_path, novice=11000, clock=FakeClock(START)) as g:
        await _give(g, 2014701)
        assert codes(await _use(g)) == [115, 150, 4434, 110, 150, 4188, 150, 3]
