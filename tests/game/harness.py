"""Servidor completo + personagem logado no socket, para testes de jogo com cliente falso."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_from_bytes

from aiohttp.test_utils import TestClient, TestServer

from tests.conftest import Portal
from tests.test_end_to_end import FakeFlashClient
from wartune_server.app import GameServerApp, build_services
from wartune_server.config import Settings
from wartune_server.net.servers import start_tcp
from wartune_server.persistence.repositories import SqlAlchemyUnitOfWork
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb


@dataclass
class Game:
    client: FakeFlashClient
    server: GameServerApp
    user_id: int

    async def until(self, code: int) -> list[Packet]:
        return await self.client.until(code)

    async def idle(self, seconds: float = 0.15) -> list[Packet]:
        """Tudo que chegar até o servidor ficar ``seconds`` sem mandar nada."""
        got: list[Packet] = []
        c = self.client
        while True:
            while (p := c.decoder.next_packet()) is not None:
                got.append(p)
            try:
                data = await asyncio.wait_for(c.reader.read(65536), seconds)
            except TimeoutError:
                return got
            assert data, "conexão fechada"
            c.decoder.feed(data)


@asynccontextmanager
async def logged_in(tmp_path: Path, novice: int, job_icon: int = 6) -> AsyncIterator[Game]:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'game.db'}",
        rsa_key_file=tmp_path / "rsa.pem",
        log_dir=tmp_path / "logs",
        skip_tutorial=False,
        _env_file=None,  # type: ignore[call-arg]
    )
    services = await build_services(settings)
    portal = Portal(lambda: SqlAlchemyUnitOfWork(services.database.sessions))
    server = GameServerApp(settings, services)
    tcp = await start_tcp(server.acceptor, "127.0.0.1", 0)
    http = TestClient(TestServer(server.http_app))
    await http.start_server()
    try:
        account = await portal.account("maga")
        ticket = await portal.ticket(account.id)
        temp = "7654321"
        plain = f"{quote_from_bytes(b'maga', safe='')}|{ticket}|{temp}|0".encode()
        form = {"p": services.keys.encrypt_b64(plain), "site": settings.site}
        login = await (await http.post("/login", data=form)).text()
        user_id = int(re.search(r'userId="(\d+)"', login).group(1))  # type: ignore[union-attr]
        key = hashlib.md5(temp.encode()).hexdigest()
        reg = {"userid": user_id, "username": "maga", "nickname": "Maga", "sex": 0, "camp": 1, "icon": job_icon}
        await http.post("/visualizeregister", data=reg | {"key": key})
        await services.characters.set_novice_process(user_id, novice)

        client = FakeFlashClient(*await asyncio.open_connection("127.0.0.1", tcp.sockets[0].getsockname()[1]))
        ekeys = os.urandom(8)
        client.send(20001, pb.LoginReqMsg(key=key, ekeys=list(ekeys)))
        client.rekey(ekeys)
        await client.until(150)
        client.send(8224, pb.PlayerDataMsg(user=True))
        await client.until(6)
        yield Game(client, server, user_id)
        client.writer.close()
    finally:
        await http.close()
        tcp.close()
        server.acceptor.close_all()
        await services.database.dispose()
