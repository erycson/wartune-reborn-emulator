"""Servidor completo + personagem logado no socket, para testes de jogo com cliente falso."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_from_bytes

from aiohttp.test_utils import TestClient, TestServer

from tests.conftest import Portal
from tests.test_end_to_end import EVENTS, FakeFlashClient
from wartune_server.app import GameServerApp, build_services
from wartune_server.config import Settings
from wartune_server.net.servers import start_tcp
from wartune_server.persistence.repositories import SqlAlchemyUnitOfWork
from wartune_server.protocol import Packet
from wartune_server.protocol.messages import wartune_pb2 as pb
from wartune_server.services.clock import Clock


@dataclass
class Game:
    client: FakeFlashClient
    server: GameServerApp
    user_id: int
    join: Callable[[str], Awaitable[Game]]
    connect: Callable[[], Awaitable[Game]]  # mais um socket na mesma conta (relogin)
    http: TestClient  # type: ignore[type-arg]
    key: str  # chave da sessão HTTP (maillist etc.)

    async def until(self, code: int) -> list[Packet]:
        return await self.client.until(code)

    async def fight(self, prepare: pb.BattlePrepareMsg, skill: int = 30711) -> list[Packet]:
        """10007 e uma ordem por vez (como o cliente em modo manual) até o 4103."""
        me = next(h for h in prepare.heros if h.userId == self.user_id)
        self.client.send(10007, pb.LoadOverMsg(armyId=self.user_id, battleId=prepare.battleId))
        got: list[Packet] = []
        while not any(p.code == 4103 for p in got):
            self.client.send(10008, pb.UseSkillMsg(battleId=prepare.battleId, heroId=me.livingId, skillId=skill))
            got += await self.idle(0.05)
        return got

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
async def logged_in(
    tmp_path: Path, novice: int, job_icon: int = 6, clock: Clock | None = None, timezone: str = "UTC"
) -> AsyncIterator[Game]:
    """Servidor no ar e a conta "maga" logada. ``game.join("outro")`` loga mais um jogador."""
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'game.db'}",
        rsa_key_file=tmp_path / "rsa.pem",
        log_dir=tmp_path / "logs",
        skip_tutorial=False,
        game_timezone=timezone,
        events_file=EVENTS,
        _env_file=None,  # type: ignore[call-arg]
    )
    services = await build_services(settings, clock)
    portal = Portal(lambda: SqlAlchemyUnitOfWork(services.database.sessions))
    server = GameServerApp(settings, services)
    tcp = await start_tcp(server.acceptor, "127.0.0.1", 0)
    http = TestClient(TestServer(server.http_app))
    await http.start_server()
    clients: list[FakeFlashClient] = []

    async def join(username: str, icon: int = job_icon) -> Game:
        account = await portal.account(username)
        ticket = await portal.ticket(account.id)  # type: ignore[arg-type]
        temp = str(int.from_bytes(os.urandom(3)))  # chave da sessão HTTP: uma por login, como no cliente
        plain = f"{quote_from_bytes(username.encode(), safe='')}|{ticket}|{temp}|0".encode()
        form = {"p": services.keys.encrypt_b64(plain), "site": settings.site}
        login = await (await http.post("/login", data=form)).text()
        user_id = int(re.search(r'userId="(\d+)"', login).group(1))  # type: ignore[union-attr]
        key = hashlib.md5(temp.encode()).hexdigest()
        nick = username.capitalize()
        reg = {"userid": user_id, "username": username, "nickname": nick, "sex": 0, "camp": 1, "icon": icon}
        await http.post("/visualizeregister", data=reg | {"key": key})
        await services.characters.set_novice_process(user_id, novice)

        return await socket_login(user_id, key)

    async def socket_login(user_id: int, key: str) -> Game:
        client = FakeFlashClient(*await asyncio.open_connection("127.0.0.1", tcp.sockets[0].getsockname()[1]))
        clients.append(client)
        ekeys = os.urandom(8)
        client.send(20001, pb.LoginReqMsg(key=key, ekeys=list(ekeys)))
        client.rekey(ekeys)
        await client.until(150)
        client.send(8224, pb.PlayerDataMsg(user=True))
        # o 6, a cidade do céu (4595, depois do tutorial) e o 4151 (tutorial_en #93-#94, oficial_20261023-171155-1 #92-#94)
        await client.until(4151)
        return Game(client, server, user_id, join, lambda: socket_login(user_id, key), http, key)

    try:
        yield await join("maga")
    finally:
        for client in clients:
            client.writer.close()
        await http.close()
        tcp.close()
        server.acceptor.close_all()
        await services.database.dispose()
