"""Lote 9: História (Time Story, 8629/8630 -> 4546) e caixa de ano novo (8994 -> 143/4811)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest
from sqlalchemy import Connection

from tests.game.harness import Game, logged_in
from tests.game.test_shop import me
from tests.game.test_space import _walk
from tests.test_end_to_end import TEMPLATES
from wartune_server.persistence.database import Database, _upgrade
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import FakeClock

pytestmark = pytest.mark.skipif(not TEMPLATES.exists(), reason="precisa de data/templates")


def _window(g: Game, begin: str, end: str) -> None:
    world = g.server.services.world
    box = {**world.settings["new_year_box"], "begin": begin, "end": end}
    object.__setattr__(world, "settings", MappingProxyType({**world.settings, "new_year_box": box}))


async def test_historia_ovo_a_cada_isaccess_com_limite_diario(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as g:
        c = g.client
        c.send(8630)  # fechar o quadro sem ovo: nada
        c.send(8629, pb.GameStoryMsg(index=2, isAccess=False))
        assert await g.idle() == []
        gold = me(g).character.gold
        for _ in range(5):
            c.send(8629, pb.GameStoryMsg(index=3, isAccess=True))
            c.send(8629, pb.GameStoryMsg(index=3, isAccess=True))  # ovo já à espera: não sai outro
            assert [p.code for p in await g.idle()] == [4546]
            c.send(8630)
            await g.idle()
        assert me(g).character.gold == gold + 5 * 50000
        c.send(8629, pb.GameStoryMsg(index=3, isAccess=True))  # 5 por dia
        assert await g.idle() == []


async def test_caixa_de_ano_novo_coleta_no_space(tmp_path: Path) -> None:
    clock = FakeClock(datetime.now(UTC))  # o ticket do login vale pela hora real
    async with logged_in(tmp_path, novice=33000, clock=clock) as g:
        _window(g, "2026-01-01 00:00:00", "2099-01-01 00:00:00")
        c = g.client
        me(g).character.grades = 40
        await g.idle()
        c.send(8994, pb.SimplePropertyMsg(param1=3))
        nodes = pb.QueryCollectCampaignNodeRspMsg.FromString((await g.until(4811))[-1].body).collectCampaignNode
        assert len(nodes) == 20 and nodes[0].campaignDataId == 30001 and nodes[0].mastType == 300
        c.send(8994, pb.SimplePropertyMsg(param1=1, param2=30001))  # longe do nó
        assert not any(p.code == 143 for p in await g.idle())
        c.send(8690, _walk(90, 107))
        c.send(8994, pb.SimplePropertyMsg(param1=1, param2=30001))
        assert any(p.code == 143 for p in await g.idle())
        clock.advance(2)
        gold = me(g).character.gold
        c.send(8994, pb.SimplePropertyMsg(param1=2, param2=30001))
        got = pb.QueryCollectCampaignNodeRspMsg.FromString((await g.until(4811))[-1].body)
        assert 30001 not in [n.campaignDataId for n in got.collectCampaignNode]
        assert me(g).character.gold == gold + 100000
        c.send(8994, pb.SimplePropertyMsg(param1=1, param2=30001))  # já coletada hoje
        assert not any(p.code == 143 for p in await g.idle())


async def test_caixa_de_ano_novo_fora_do_evento_sem_resposta(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=33000) as g:
        _window(g, "2000-01-01 00:00:00", "2000-01-08 00:00:00")
        await g.idle()
        g.client.send(8994, pb.SimplePropertyMsg(param1=3))
        assert await g.idle() == []


async def test_migracao_0123_num_banco_em_0122(tmp_path: Path) -> None:
    db = Database(f"sqlite+aiosqlite:///{tmp_path / 'velho.db'}")
    try:

        def old(conn: Connection) -> None:
            _upgrade(conn, "0122")

        async with db.engine.begin() as conn:
            await conn.run_sync(old)
        await db.engine.dispose()
        await db.migrate()
        async with db.engine.connect() as conn:
            keys = (
                await conn.exec_driver_sql(
                    "SELECT key FROM game_settings WHERE key IN ('new_year_box', 'time_story') ORDER BY key"
                )
            ).all()
        assert [k for (k,) in keys] == ["new_year_box", "time_story"]
    finally:
        await db.engine.dispose()
