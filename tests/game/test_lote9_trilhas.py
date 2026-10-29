"""Lote 9: Gods Descent (8752-8755 type 1, 5021 type 2) e Sky Trails (8753/8755 type 0, 8636-8638)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Connection

from tests.game.harness import Game, logged_in
from tests.game.test_shop import me
from tests.test_end_to_end import TEMPLATES
from wartune_server.game import battle as battle_mod
from wartune_server.game import events as ev
from wartune_server.game.handlers import minijogo as mj
from wartune_server.persistence.database import Database, _upgrade
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock
from wartune_server.templates.repository import GameTemplates

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def _result(monkeypatch: pytest.MonkeyPatch, won: bool) -> None:
    """Luta sem turnos: vencendo, o chefe morre; perdendo, fica com metade da vida."""

    async def fight(battle: battle_mod.Battle) -> bool:
        for unit in battle.units:
            if unit.side == 2:
                unit.hp = 0 if won else unit.max_hp // 2
        return won

    monkeypatch.setattr(battle_mod, "FRAME_SECONDS", 0.001)
    monkeypatch.setattr(battle_mod.Battle, "_fight", fight)


def _one(got: list, code: int, kind: type) -> object:  # type: ignore[type-arg]
    return kind.FromString(next(p for p in reversed(got) if p.code == code).body)


async def _attack(g: Game, kind: int, target: int) -> list:  # type: ignore[type-arg]
    g.client.send(8755, pb.PlayerChallengeMsg(type=kind, tarUserId=target, payType=0))
    prepare = pb.BattlePrepareMsg.FromString((await g.until(157))[-1].body)
    return await g.fight(prepare) + await g.idle()


def _count(g: Game, template: int) -> int:
    return sum(i.count for i in me(g).items if i.template_id == template)


def test_templates_leem_o_nivel_aninhado_do_tollgate_reward() -> None:
    t = GameTemplates.parse(TEMPLATES.read_bytes())
    assert len(t.rows("ScoreRewards")) == 28 and len(t.rows("BossRewards")) == 370
    assert [r["Area"] for r in t.rows("AreaRewards")][:1] == ["1"] and t.rows("LuckyRewards")


async def test_sky_trails_luta_avaliacao_premios_area_e_cornetas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with logged_in(tmp_path, novice=22500) as g:
        me(g).character.grades = 60
        g.client.send(8753, pb.PlayerChallengeMsg(type=0))
        info = _one(await g.idle(), 4552, pb.SinglePassMsg)
        assert (info.area, info.maxIndex, info.count) == (1, 0, 0)  # type: ignore[attr-defined]

        g.client.send(8755, pb.PlayerChallengeMsg(type=0, tarUserId=2))  # TipsTxt02: a 1 primeiro
        got = await g.idle()
        assert not any(p.code == 157 for p in got) and _one(got, 4552, pb.SinglePassMsg).maxIndex == 0  # type: ignore[attr-defined]

        _result(monkeypatch, won=True)
        got = await _attack(g, 0, 1)
        report = _one(got, 4103, pb.BattleReportMsg)
        assert report.battleScene == 5  # type: ignore[attr-defined]  # herói intacto: S
        items = {(i.templateId, i.count) for i in report.baseItem}  # type: ignore[attr-defined]
        assert (2125057, 5) in items and (2125052, 1) in items  # BossReward Type 0 e Type 2 da fase 1
        info = _one(got, 4552, pb.SinglePassMsg)
        assert (info.maxIndex, info.count) == (1, 1)  # type: ignore[attr-defined]
        assert [(r.index, r.rank) for r in info.rankInfo] == [(1, 5)]  # type: ignore[attr-defined]
        assert _count(g, 2125057) == 15 and _count(g, 2125052) == 1

        g.client.send(8755, pb.PlayerChallengeMsg(type=0, tarUserId=1))  # TipsTxt03: já tem S
        assert not any(p.code == 157 for p in await g.idle())

        snap, now = me(g), datetime.now(UTC)
        d = mj.load(snap, "singlepass")
        d["max"] = 10
        await g.server.services.characters.save(mj.store(snap, "singlepass", d, now))
        g.client.send(8637, pb.PlayerChallengeMsg())
        info = _one(await g.idle(), 4552, pb.SinglePassMsg)
        assert (info.area, info.areaReward) == (2, "1")  # type: ignore[attr-defined]
        assert _count(g, 2125057) == 35  # AreaReward da área 1: x20

        g.client.send(8638, pb.PlayerChallengeMsg())
        info = _one(await g.idle(), 4552, pb.SinglePassMsg)
        assert info.itemCount == 4 and _count(g, 3150001) == 4  # type: ignore[attr-defined]  # 10 / 5 * 2


async def test_sky_trails_conta_a_atividade_113(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with logged_in(tmp_path, novice=22500) as g:
        monkeypatch.setattr(ev, "count", lambda snap, cat, kind, now, n=1: seen.append(kind) or [])
        seen: list[int] = []
        _result(monkeypatch, won=False)
        got = await _attack(g, 0, 1)
        assert seen == [ev.SKY_TRAILS] and _one(got, 4552, pb.SinglePassMsg).maxIndex == 0  # type: ignore[attr-defined]


async def test_gods_descent_vida_persiste_contagem_primeiro_e_premio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = FakeClock(datetime(2026, 10, 27, 12, tzinfo=UTC))  # edição de 26/10, lutas até 31/10 00:00
    async with logged_in(tmp_path, novice=22500, clock=clock) as g:
        c = me(g).character
        c.grades, c.point = 60, 1000
        g.client.send(8753, pb.PlayerChallengeMsg(type=1))
        got = await g.idle()
        assert _one(got, 4645, pb.TollgateMsg).isOpen  # type: ignore[attr-defined]
        info = _one(got, 4643, pb.TollgateMsg)
        assert (info.curTollgateId, info.remainCount, len(info.challengeInfo)) == (1, 5, 30)  # type: ignore[attr-defined]
        live = info.challengeInfo[0].lastHp  # type: ignore[attr-defined]
        assert live == 2120000  # GameHeroTemp 6001

        _result(monkeypatch, won=False)
        got = await _attack(g, 1, 1)
        info = _one(got, 4643, pb.TollgateMsg)
        gate = info.challengeInfo[0]  # type: ignore[attr-defined]
        assert (info.remainCount, gate.lastHp, gate.remainTime) == (4, live // 2, 30 * 60)  # type: ignore[attr-defined]
        assert info.addTimeCount == 1  # type: ignore[attr-defined]

        g.client.send(5021, pb.PlayerChallengeMsg(type=2, payType=1))
        info = _one(await g.idle(), 4643, pb.TollgateMsg)
        assert info.challengeInfo[0].remainTime == 35 * 60 and c.point == 990  # type: ignore[attr-defined]

        _result(monkeypatch, won=True)
        got = await _attack(g, 1, 1)
        assert any((i.templateId, i.count) == (2100035, 10) for i in _one(got, 4103, pb.BattleReportMsg).baseItem)  # type: ignore[attr-defined]  # primeiro a matar: Type 3
        info = _one(got, 4643, pb.TollgateMsg)
        assert (info.curTollgateId, info.score) == (2, 10)  # type: ignore[attr-defined]
        assert info.challengeInfo[0].attackName == c.nickname and info.challengeInfo[0].lastHp == 0  # type: ignore[attr-defined]

        g.client.send(8754, pb.PlayerChallengeMsg())
        rank = _one(await g.idle(), 4646, pb.TollgateMsg)
        assert [(r.userId, r.score, r.order) for r in rank.scoreInfo] == [(g.user_id, 10, 1)]  # type: ignore[attr-defined]

        g.client.send(8752, pb.PlayerChallengeMsg())  # ainda nas lutas: nada
        assert not any(p.code == 4647 for p in await g.idle())
        clock.advance(timedelta(days=4).total_seconds())
        g.client.send(8753, pb.PlayerChallengeMsg(type=1))
        got = await g.idle()
        assert not _one(got, 4645, pb.TollgateMsg).isOpen and any(p.code == 4644 for p in got)  # type: ignore[attr-defined]
        before = _count(g, 208030)
        g.client.send(8752, pb.PlayerChallengeMsg())
        reward = _one(await g.idle(), 4647, pb.TollgateRewardMsg)
        assert (reward.order, reward.score) == (1, 10) and "208030|400" in reward.scoreItems  # type: ignore[attr-defined]
        assert _count(g, 208030) == before + 400
        g.client.send(8752, pb.PlayerChallengeMsg())  # uma vez só
        assert not any(p.code == 4647 for p in await g.idle())


async def test_migracao_0119_num_banco_em_0118(tmp_path: Path) -> None:
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'velho.db'}")
    try:

        def old(conn: Connection) -> None:
            _upgrade(conn, "0118")

        async with db.engine.begin() as conn:
            await conn.run_sync(old)
        await db.engine.dispose()
        await db.migrate()
        async with db.engine.connect() as conn:
            keys = (
                await conn.exec_driver_sql(
                    "SELECT key FROM game_settings WHERE key IN ('gods_descent', 'sky_trails') ORDER BY key"
                )
            ).all()
        assert [k for (k,) in keys] == ["gods_descent", "sky_trails"]
    finally:
        await db.engine.dispose()
