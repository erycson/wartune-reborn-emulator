"""Linha de comando: ``wartune-server run | db init | account create <user> <senha>``."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys

import structlog

from .app import GameServerApp, build_services
from .config import Settings
from .domain.errors import DomainError
from .logging_setup import setup_logging


async def _run(settings: Settings) -> None:
    services = await build_services(settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows: Ctrl+C vira KeyboardInterrupt
            loop.add_signal_handler(sig, stop.set)
    await GameServerApp(settings, services).serve(stop)


async def _db_init(settings: Settings) -> None:
    services = await build_services(settings)
    await services.database.dispose()
    print(f"banco pronto: {settings.database_url}")


async def _account_create(settings: Settings, username: str, password: str) -> None:
    services = await build_services(settings)
    try:
        account = await services.accounts.register(username, password)
        print(f"conta criada: {account.username} (id {account.id})")
    finally:
        await services.database.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wartune-server")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="sobe o servidor")
    db = sub.add_parser("db", help="banco de dados").add_subparsers(dest="db_cmd", required=True)
    db.add_parser("init", help="cria as tabelas que faltam")
    acc = sub.add_parser("account", help="contas").add_subparsers(dest="acc_cmd", required=True)
    create = acc.add_parser("create", help="cria uma conta")
    create.add_argument("username")
    create.add_argument("password")
    args = parser.parse_args(argv)

    settings = Settings()
    setup_logging(settings.log_dir, settings.log_level, settings.log_packets)
    try:
        if args.cmd == "run":
            asyncio.run(_run(settings))
        elif args.cmd == "db":
            asyncio.run(_db_init(settings))
        elif args.cmd == "account":
            asyncio.run(_account_create(settings, args.username, args.password))
    except KeyboardInterrupt:
        structlog.get_logger(__name__).info("interrompido")
    except DomainError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        sys.exit(1)
