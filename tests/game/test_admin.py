import os
from pathlib import Path
from urllib.parse import quote_from_bytes

import pytest
from aiohttp.test_utils import TestClient, TestServer
from sqlalchemy import select

from tests.conftest import Portal
from tests.game.harness import Game, logged_in
from wartune_server.domain.models import Account, CashLedger, Character, Item, ItemLog, LoginHistory
from wartune_server.http.app import HttpDeps, build_http_app
from wartune_server.persistence.repositories import SqlAlchemyUnitOfWork
from wartune_server.protocol.messages import wartune_pb2 as pb

NEWBIE_BOX = 2060101  # dá 2 gift_token, 3000 de ouro e 3 itens


async def _rows(g: Game, entity: type) -> list:  # type: ignore[type-arg]
    async with g.server.services.database.sessions() as db:
        return list(await db.scalars(select(entity).order_by(entity.id)))  # type: ignore[attr-defined]


async def _http_login(g: Game, http: TestClient, username: str) -> str:
    s = g.server
    async with SqlAlchemyUnitOfWork(s.services.database.sessions) as uow:
        account = await uow.accounts.by_username(username)
    assert account is not None and account.id is not None
    ticket = await Portal(lambda: SqlAlchemyUnitOfWork(s.services.database.sessions)).ticket(account.id)
    plain = f"{quote_from_bytes(username.encode(), safe='')}|{ticket}|{int.from_bytes(os.urandom(3))}|0".encode()
    form = {"p": s.services.keys.encrypt_b64(plain), "site": s.settings.site}
    return await (await http.post("/login", data=form)).text()


async def test_gm_ban_kicks_and_refuses_http_and_socket_login(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        s = g.server
        settings = s.settings.model_copy(update={"gm_secret": "segredo"})
        http = TestClient(
            TestServer(build_http_app(HttpDeps(settings, s.services.login, s.services.characters, s.online)))
        )
        await http.start_server()
        try:
            (account,) = [a for a in await _rows(g, Account) if a.username == "maga"]
            form = {"account_id": account.id, "banned": 1}
            assert (await http.post("/gm/ban", data=form, headers={"X-GM-Secret": "x"})).status == 403
            assert (
                await http.post("/gm/ban", data=form | {"banned": 2}, headers={"X-GM-Secret": "segredo"})
            ).status == 400

            ok = await http.post("/gm/ban", data=form, headers={"X-GM-Secret": "segredo"})
            assert ok.status == 200 and s.online.get(g.user_id) is None
            assert [a.banned for a in await _rows(g, Account) if a.id == account.id] == [True]
            with pytest.raises(AssertionError, match="conexão fechada"):  # a chave HTTP já não vale
                await g.connect()
            assert 'value="false"' in await _http_login(g, http, "maga")

            await http.post("/gm/ban", data=form | {"banned": 0}, headers={"X-GM-Secret": "segredo"})
            assert 'value="true"' in await _http_login(g, http, "maga")
        finally:
            await http.close()


async def test_socket_login_refused_when_banned_after_http_login(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        async with SqlAlchemyUnitOfWork(g.server.services.database.sessions) as uow:
            account = await uow.accounts.by_username("maga")
            assert account is not None
            account.banned = True  # o portal marcou com o servidor fora: sessão HTTP ainda existe
            await uow.commit()
        with pytest.raises(AssertionError, match="conexão fechada"):
            await g.connect()


async def test_login_history_records_http_and_socket(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000) as g:
        rows = await _rows(g, LoginHistory)
        assert [(r.source, r.character_id) for r in rows] == [("game", g.user_id)] * 2  # /login e 20001
        assert all(r.ip == "127.0.0.1" and r.created_at for r in rows)


async def test_opening_a_box_writes_cash_ledger_and_item_log(tmp_path: Path) -> None:
    async with logged_in(tmp_path, novice=19000, job_icon=1) as g:
        session = g.server.online.get(g.user_id)
        assert session is not None and session.snapshot is not None
        snap = session.snapshot
        snap.character.grades = 5
        box = Item(g.user_id, NEWBIE_BOX, pos=0)
        snap.items.append(box)
        await g.server.services.characters.save(snap.character, box)

        g.client.send(5006, pb.ItemUseMsg(pos=0, count=1, bagType=1))
        await g.until(3)

        (cash,) = await _rows(g, CashLedger)
        assert (cash.character_id, cash.delta_point, cash.delta_gift_token) == (g.user_id, 0, 2)
        assert (cash.balance_gift_token, cash.reason, cash.ref, cash.gm) == (2, "item", f"5006:{NEWBIE_BOX}", None)
        logs = [(r.template_id, r.count, r.action) for r in await _rows(g, ItemLog)]
        assert logs[0] == (NEWBIE_BOX, -1, "use") and len(logs) == 4 and {a for *_, a in logs[1:]} == {"drop"}
        (char,) = await _rows(g, Character)
        assert char.gift_token == 2
