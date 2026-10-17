"""Linha de comando: ``wartune-server run | db init | character novice <id> <valor> | templates update``.

Contas e tickets são do portal (PHP).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys
import zlib
from xml.etree import ElementTree

import aiohttp
import structlog

from .app import GameServerApp, build_services
from .config import Settings
from .domain.errors import DomainError
from .logging_setup import setup_logging
from .templates.repository import GameTemplates


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


async def _set_novice(settings: Settings, character_id: int, value: int) -> None:
    services = await build_services(settings)
    try:
        await services.characters.set_novice_process(character_id, value)
    finally:
        await services.database.dispose()
    print(f"personagem {character_id}: noviceProcess = {value}")


async def _update_templates(settings: Settings, url: str | None) -> None:
    url = url or settings.templates_url
    if not url:
        raise SystemExit("erro: passe a URL ou defina WARTUNE_TEMPLATES_URL")
    try:
        templates = await GameTemplates.download(url, settings.templates_file)
    except (aiohttp.ClientError, TimeoutError, ElementTree.ParseError, zlib.error) as exc:
        raise SystemExit(f"erro: {url}: {exc or type(exc).__name__} (arquivo local mantido)") from exc
    print(f"{settings.templates_file} atualizado ({len(templates.categories)} categorias); reinicie o servidor")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wartune-server")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="sobe o servidor")
    db = sub.add_parser("db", help="banco de dados").add_subparsers(dest="db_cmd", required=True)
    db.add_parser("init", help="cria as tabelas que faltam")
    char = sub.add_parser("character", help="personagens").add_subparsers(dest="char_cmd", required=True)
    novice = char.add_parser("novice", help="muda o noviceProcess (0 refaz o tutorial)")
    novice.add_argument("id", type=int)
    novice.add_argument("valor", type=int)
    tpl = sub.add_parser("templates", help="tempinfos.xml").add_subparsers(dest="tpl_cmd", required=True)
    update = tpl.add_parser("update", help="baixa o tempinfos.xml da CDN para o arquivo local")
    update.add_argument("url", nargs="?", help="padrão: WARTUNE_TEMPLATES_URL")
    args = parser.parse_args(argv)

    settings = Settings()
    setup_logging(settings.log_dir, settings.log_level, settings.log_packets)
    try:
        if args.cmd == "run":
            asyncio.run(_run(settings))
        elif args.cmd == "db":
            asyncio.run(_db_init(settings))
        elif args.cmd == "character":
            asyncio.run(_set_novice(settings, args.id, args.valor))
        elif args.cmd == "templates":
            asyncio.run(_update_templates(settings, args.url))
    except KeyboardInterrupt:
        structlog.get_logger(__name__).info("interrompido")
    except DomainError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        sys.exit(1)
