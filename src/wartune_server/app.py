"""Raiz de composição: monta as dependências e sobe HTTP, socket TCP, policy e WebSocket."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass

import structlog
from aiohttp import web

from .config import Settings
from .domain.models import GameServer
from .game import handlers as _handlers  # noqa: F401  (registra os handlers)
from .game.router import router
from .game.session import GameContext, GameSession, OnlinePlayers
from .http.app import HttpDeps, build_http_app
from .http.config_xml import load_template, render_client_config
from .net.servers import ConnectionAcceptor, start_policy, start_tcp, websocket_app
from .persistence.database import Database
from .persistence.repositories import SqlAlchemyUnitOfWork
from .protocol.registry import MessageRegistry
from .security.rsa_keys import LoginKeyPair
from .services.accounts import AccountService
from .services.characters import CharacterService, GridCastlePlacement
from .services.clock import Clock, SystemClock
from .services.login import LoginService
from .services.sessions import InMemoryLoginSessionStore
from .templates.repository import GameTemplates

log = structlog.get_logger(__name__)


@dataclass
class Services:
    database: Database
    accounts: AccountService
    login: LoginService
    characters: CharacterService
    templates: GameTemplates
    keys: LoginKeyPair
    clock: Clock


async def build_services(settings: Settings, clock: Clock | None = None) -> Services:
    clock = clock or SystemClock()
    database = Database(settings.database_url, echo=settings.database_echo)
    await database.create_schema()
    await _register_server(database, settings, clock)

    def uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(database.sessions)

    templates, keys = await asyncio.gather(
        GameTemplates.load(settings.templates_file),
        asyncio.to_thread(LoginKeyPair.load_or_create, settings.rsa_key_file),
    )
    sessions = InMemoryLoginSessionStore(clock, settings.socket_session_ttl_seconds)
    return Services(
        database=database,
        accounts=AccountService(uow, clock, settings.login_ticket_ttl_seconds),
        login=LoginService(uow, keys, sessions, clock, settings.server_id),
        characters=CharacterService(uow, templates, GridCastlePlacement()),
        templates=templates,
        keys=keys,
        clock=clock,
    )


async def _register_server(database: Database, settings: Settings, clock: Clock) -> None:
    """Garante a linha deste servidor em ``game_servers`` (preserva a data de abertura)."""
    async with SqlAlchemyUnitOfWork(database.sessions) as uow:
        current = await uow.servers.get(settings.server_id)
        opened_at = current.opened_at if current else clock.now()
        await uow.servers.upsert(
            GameServer(settings.server_id, settings.server_name, settings.site, settings.public_host,
                       settings.http_port, settings.socket_port, opened_at)
        )
        await uow.commit()


class GameServerApp:
    def __init__(self, settings: Settings, services: Services) -> None:
        self.settings = settings
        self.services = services
        self.online = OnlinePlayers()
        registry = MessageRegistry.load_default()
        ctx = GameContext(registry, router, services.login, services.characters, services.templates,
                          services.clock, self.online)
        self.acceptor = ConnectionAcceptor(
            registry, lambda conn: GameSession(conn, ctx), idle_timeout=settings.idle_timeout_seconds
        )
        s = settings
        config_xml = render_client_config(
            load_template(s.config_template),
            request_url=s.public_http_url,
            resource_url=s.public_resource_url,
            socket_host=s.public_host,
            socket_port=s.socket_port,
            site=s.site,
            keys=services.keys,
        )
        self.http_app = build_http_app(
            HttpDeps(s, services.accounts, services.login, services.characters, config_xml)
        )

    async def serve(self, stop: asyncio.Event) -> None:
        s = self.settings
        runners: list[web.AppRunner] = []
        servers: list[asyncio.Server] = []
        try:
            for app, port in ((self.http_app, s.http_port), (websocket_app(self.acceptor), s.websocket_port)):
                runner = web.AppRunner(app, access_log=None)
                await runner.setup()
                await web.TCPSite(runner, s.bind_host, port).start()
                runners.append(runner)
            log.info("HTTP ouvindo", url=s.public_http_url, websocket=s.websocket_port)
            servers.append(await start_tcp(self.acceptor, s.bind_host, s.socket_port))
            if s.policy_port and (policy := await start_policy(s.bind_host, s.policy_port)):
                servers.append(policy)
            log.info("servidor pronto", servidor=s.server_id, nome=s.server_name)
            await stop.wait()
        finally:
            log.info("encerrando", online=len(self.online))
            for server in servers:
                server.close()
            self.acceptor.close_all()
            for server in servers:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(server.wait_closed(), 5)
            for runner in runners:
                await runner.cleanup()
            await self.services.database.dispose()
