"""Logging estruturado para console e arquivos rotativos.

* ``logs/server.log``  - tudo (JSON por linha), para acompanhar/depurar.
* ``logs/packets.log`` - um registro por pacote (direção, opcode, nome, mensagem decodificada).
* console             - formato legível.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

import structlog

PACKET_LOGGER = "wartune.packets"


def setup_logging(log_dir: Path, level: str = "INFO", packets: bool = True) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.stdlib.add_logger_name,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    def formatter(renderer: structlog.types.Processor) -> structlog.stdlib.ProcessorFormatter:
        return structlog.stdlib.ProcessorFormatter(foreign_pre_chain=shared, processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer])

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter(structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())))

    server_file = _rotating(log_dir / "server.log")
    server_file.setFormatter(formatter(structlog.processors.JSONRenderer(ensure_ascii=False)))

    root = logging.getLogger()
    root.handlers[:] = [console, server_file]
    root.setLevel(level.upper())

    packet_logger = logging.getLogger(PACKET_LOGGER)
    packet_logger.propagate = False
    packet_logger.handlers.clear()
    if packets:
        packet_file = _rotating(log_dir / "packets.log")
        packet_file.setFormatter(formatter(structlog.processors.JSONRenderer(ensure_ascii=False)))
        packet_logger.addHandler(packet_file)
        packet_logger.setLevel(logging.DEBUG)
    else:
        packet_logger.disabled = True

    for noisy in ("aiohttp.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _rotating(path: Path) -> logging.Handler:
    return logging.handlers.RotatingFileHandler(path, maxBytes=20 * 1024 * 1024, backupCount=5, encoding="utf-8")
