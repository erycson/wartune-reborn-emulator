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
from .game import mall as market
from .game.events import EventCatalog
from .game.guild import Guilds
from .game.router import router
from .game.session import GameContext, GameSession, OnlinePlayers
from .http.app import HttpDeps, build_http_app
from .net.servers import ConnectionAcceptor, start_policy, start_tcp, websocket_app
from .persistence.database import Database
from .persistence.repositories import SqlAlchemyUnitOfWork
from .protocol.registry import MessageRegistry
from .security.rsa_keys import LoginKeyPair
from .services.characters import CharacterService, GridCastlePlacement
from .services.clock import Clock, SystemClock
from .services.login import LoginService
from .services.sessions import InMemoryLoginSessionStore
from .templates import store as template_store
from .templates.repository import GameTemplates

log = structlog.get_logger(__name__)


async def _templates(database: Database, settings: Settings) -> GameTemplates:
    """Do banco quando importados (``templates import``); senão do arquivo, como num banco novo de teste."""
    if await template_store.has_templates(database.engine):
        return await template_store.load(database.engine)
    log.warning("templates fora do banco: lendo o arquivo", arquivo=str(settings.templates_file))
    return await GameTemplates.load(settings.templates_file)


@dataclass
class Services:
    database: Database
    login: LoginService
    characters: CharacterService
    templates: GameTemplates
    keys: LoginKeyPair
    clock: Clock
    guilds: Guilds


async def build_services(settings: Settings, clock: Clock | None = None) -> Services:
    clock = clock or SystemClock()
    database = Database(settings.database_url, echo=settings.database_echo)
    await database.migrate()
    templates, keys = await asyncio.gather(
        _templates(database, settings),
        asyncio.to_thread(LoginKeyPair.load_or_create, settings.rsa_key_file),
    )
    await _register_server(database, settings, keys, clock)

    def uow() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(database.sessions)

    sessions = InMemoryLoginSessionStore(clock, settings.socket_session_ttl_seconds)
    characters = CharacterService(uow, templates, GridCastlePlacement())
    return Services(
        database=database,
        login=LoginService(uow, keys, sessions, clock, settings.server_id),
        characters=characters,
        templates=templates,
        keys=keys,
        clock=clock,
        guilds=await Guilds.load(characters, settings.server_id),
    )


async def _register_server(database: Database, settings: Settings, keys: LoginKeyPair, clock: Clock) -> None:
    """Publica este servidor em ``game_servers``: é dali que o portal tira endereço, portas e a
    chave RSA para montar o config.xml. Preserva a data de abertura."""
    async with SqlAlchemyUnitOfWork(database.sessions) as uow:
        current = await uow.servers.get(settings.server_id)
        opened_at = current.opened_at if current else clock.now()
        await uow.servers.upsert(
            GameServer(
                settings.server_id,
                settings.server_name,
                settings.site,
                settings.public_host,
                settings.http_port,
                settings.socket_port,
                opened_at,
                websocket_port=settings.websocket_port,
                rsa_modulus=keys.modulus_b64,
                rsa_exponent=keys.exponent_b64,
            )
        )
        await uow.commit()


class GameServerApp:
    def __init__(self, settings: Settings, services: Services) -> None:
        self.settings = settings
        self.services = services
        self.online = OnlinePlayers()
        registry = MessageRegistry.load_default()
        ctx = GameContext(
            registry,
            router,
            services.login,
            services.characters,
            services.templates,
            services.clock,
            self.online,
            services.guilds,
            EventCatalog.load(settings.events_file),
        )
        self.acceptor = ConnectionAcceptor(
            registry, lambda conn: GameSession(conn, ctx), idle_timeout=settings.idle_timeout_seconds
        )
        self.http_app = build_http_app(HttpDeps(settings, services.login, services.characters, self.online))

    async def serve(self, stop: asyncio.Event) -> None:
        s = self.settings
        runners: list[web.AppRunner] = []
        servers: list[asyncio.Server] = []
        sweeper: asyncio.Task[None] | None = None
        try:
            for app, port in ((self.http_app, s.http_port), (websocket_app(self.acceptor), s.websocket_port)):
                runner = web.AppRunner(app, access_log=None)
                await runner.setup()
                await web.TCPSite(runner, s.bind_host, port).start()
                runners.append(runner)
            log.info("HTTP ouvindo", porta=s.http_port, websocket=s.websocket_port)
            servers.append(await start_tcp(self.acceptor, s.bind_host, s.socket_port))
            if s.policy_port and (policy := await start_policy(s.bind_host, s.policy_port)):
                servers.append(policy)
            log.info("servidor pronto", servidor=s.server_id, nome=s.server_name)
            sweeper = asyncio.create_task(
                market.run(
                    self.services.characters, self.services.templates, self.online, self.services.clock, s.server_id
                ),
                name="mercado-encerramento",
            )
            await stop.wait()
        finally:
            if sweeper is not None:
                sweeper.cancel()
                await asyncio.gather(sweeper, return_exceptions=True)
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
