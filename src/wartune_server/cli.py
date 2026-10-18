"""Linha de comando: ``wartune-server run | db init | character novice <id> <valor> | templates import|export|update``.

Contas e tickets são do portal (PHP).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import sys
import zlib
from pathlib import Path
from xml.etree import ElementTree

import aiohttp
import structlog

from .app import GameServerApp, build_services
from .config import Settings
from .domain.errors import DomainError
from .logging_setup import setup_logging
from .persistence.database import Database
from .templates import store as template_store
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
    try:
        if not await template_store.has_templates(services.database.engine):
            await _import(services.database, settings.templates_file.read_bytes(), str(settings.templates_file))
    finally:
        await services.database.dispose()
    print(f"banco pronto: {settings.database_url}")


async def _import(database: Database, data: bytes, source: str) -> None:
    result = await template_store.import_xml(database.engine, data, source)
    print(f"templates de {source}: {result.categories} categorias, {result.nodes} nós (sha256 {result.sha256[:12]})")


async def _import_templates(settings: Settings, path: Path | None) -> None:
    path = path or settings.templates_file
    database = Database(settings.database_url)
    try:
        await database.migrate()
        await _import(database, path.read_bytes(), str(path))
    except (ElementTree.ParseError, zlib.error, ValueError) as exc:
        raise SystemExit(f"erro: {path}: {exc} (templates do banco mantidos)") from exc
    finally:
        await database.dispose()
    print("reinicie o servidor")


async def _export_templates(settings: Settings, out: Path) -> None:
    database = Database(settings.database_url)
    try:
        await database.migrate()
        if not await template_store.has_templates(database.engine):
            raise SystemExit("erro: banco sem templates; rode `templates import` antes")
        data = await template_store.export_xml(database.engine)
        await asyncio.to_thread(_write, out, data)
    finally:
        await database.dispose()
    print(f"{out} gerado do banco")


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def _db_revision(settings: Settings, message: str) -> None:
    database = Database(settings.database_url)
    try:
        await database.migrate()
        await database.new_revision(message)
    finally:
        await database.dispose()


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
    print(f"{settings.templates_file} atualizado ({len(templates.categories)} categorias)")
    await _import_templates(settings, settings.templates_file)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="wartune-server")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="sobe o servidor")
    db = sub.add_parser("db", help="banco de dados").add_subparsers(dest="db_cmd", required=True)
    db.add_parser("init", help="cria o banco ou aplica as migrações pendentes")
    revision = db.add_parser("revision", help="gera uma migração a partir das mudanças em schema.py")
    revision.add_argument("mensagem")
    char = sub.add_parser("character", help="personagens").add_subparsers(dest="char_cmd", required=True)
    novice = char.add_parser("novice", help="muda o noviceProcess (0 refaz o tutorial)")
    novice.add_argument("id", type=int)
    novice.add_argument("valor", type=int)
    tpl = sub.add_parser("templates", help="tempinfos.xml").add_subparsers(dest="tpl_cmd", required=True)
    update = tpl.add_parser("update", help="baixa o tempinfos.xml da CDN para o arquivo local e importa no banco")
    update.add_argument("url", nargs="?", help="padrão: WARTUNE_TEMPLATES_URL")
    imp = tpl.add_parser("import", help="importa um tempinfos.xml no banco (troca o conjunto inteiro)")
    imp.add_argument("arquivo", nargs="?", type=Path, help="padrão: WARTUNE_TEMPLATES_FILE")
    exp = tpl.add_parser("export", help="gera o tempinfos.xml (zlib, como o oficial) a partir do banco")
    exp.add_argument("saida", type=Path)
    args = parser.parse_args(argv)

    settings = Settings()
    setup_logging(settings.log_dir, settings.log_level, settings.log_packets)
    try:
        if args.cmd == "run":
            asyncio.run(_run(settings))
        elif args.cmd == "db" and args.db_cmd == "revision":
            asyncio.run(_db_revision(settings, args.mensagem))
        elif args.cmd == "db":
            asyncio.run(_db_init(settings))
        elif args.cmd == "character":
            asyncio.run(_set_novice(settings, args.id, args.valor))
        elif args.cmd == "templates" and args.tpl_cmd == "import":
            asyncio.run(_import_templates(settings, args.arquivo))
        elif args.cmd == "templates" and args.tpl_cmd == "export":
            asyncio.run(_export_templates(settings, args.saida))
        elif args.cmd == "templates":
            asyncio.run(_update_templates(settings, args.url))
    except KeyboardInterrupt:
        structlog.get_logger(__name__).info("interrompido")
    except DomainError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        sys.exit(1)
