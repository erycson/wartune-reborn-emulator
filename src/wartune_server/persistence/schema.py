"""Tabelas e mapeamento imperativo das entidades do domínio.

Tipos escolhidos para funcionar igual em SQLite, MySQL e PostgreSQL:
strings sempre com tamanho (MySQL exige em índices), datas em UTC via
``UTCDateTime`` (SQLite não guarda fuso), ids ``Integer`` (o cliente usa int32).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Dialect,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import registry
from sqlalchemy.types import TypeDecorator

from ..domain.models import Account, Building, Castle, Character, GameServer, Hero, PlayTicket

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING)
mapper_registry = registry(metadata=metadata)


class UTCDateTime(TypeDecorator[datetime]):
    """Grava em UTC e devolve sempre ``datetime`` com fuso (SQLite perde o tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetime sem fuso horário; use datetime.now(UTC)")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        result: datetime = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return result


def _int(name: str, default: int = 0) -> Column[int]:
    return Column(name, Integer, nullable=False, default=default, server_default=str(default))


accounts = Table(
    "accounts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(32), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    Column("last_login_at", UTCDateTime),
    Column("banned", Boolean, nullable=False, default=False, server_default="0"),
)

play_tickets = Table(
    "play_tickets",
    metadata,
    Column("token", String(64), primary_key=True),
    Column("account_id", Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("server_id", Integer, ForeignKey("game_servers.id"), nullable=False),
    Column("created_at", UTCDateTime, nullable=False),
    Column("expires_at", UTCDateTime, nullable=False, index=True),
)

game_servers = Table(
    "game_servers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("name", String(64), nullable=False),
    Column("site", String(64), nullable=False, unique=True),
    Column("public_host", String(255), nullable=False),
    Column("http_port", Integer, nullable=False),
    Column("socket_port", Integer, nullable=False),
    Column("opened_at", UTCDateTime, nullable=False),
)

characters = Table(
    "characters",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("server_id", Integer, ForeignKey("game_servers.id"), nullable=False),
    Column("nickname", String(32)),  # NULL até o visualizeregister
    _int("sex"),
    _int("camp", 1),
    _int("job"),
    Column("active", Boolean, nullable=False, default=False, server_default="0"),
    _int("grades", 1),
    _int("gp"),
    _int("total_gp"),
    _int("gold"),
    _int("point"),
    _int("gift_token"),
    _int("weary", 200),
    _int("weary_limit", 200),
    _int("novice_process"),
    _int("fighting_capacity"),
    _int("repute"),
    _int("geste"),
    _int("charm"),
    Column("created_at", UTCDateTime, nullable=False),
    Column("last_login_at", UTCDateTime),
    UniqueConstraint("account_id", "server_id"),  # um personagem por conta em cada servidor
    UniqueConstraint("server_id", "nickname"),
)

heroes = Table(
    "heroes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("template_id", Integer, nullable=False),
    Column("nickname", String(32), nullable=False),
    _int("grades", 1),
    _int("gp"),
    _int("power"),
    _int("agility"),
    _int("intellect"),
    _int("captain"),
    _int("physique"),
    _int("power_point"),
    _int("agility_point"),
    _int("intellect_point"),
    _int("captain_point"),
    _int("physique_point"),
    _int("remain_point"),
    _int("skill_point"),
    Column("skill_script", String(255), nullable=False, default="", server_default=""),
    Column("fast_key", String(255), nullable=False, default="", server_default=""),
    _int("fight_pos", 1),
    Column("is_leader", Boolean, nullable=False, default=False, server_default="0"),
)

castles = Table(
    "castles",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("name", String(32), nullable=False),
    Column("map_id", Integer, nullable=False),
    Column("pos_x", Integer, nullable=False),
    Column("pos_y", Integer, nullable=False),
    _int("grade", 1),
    _int("energy", 500),
    _int("state", 1),
)

buildings = Table(
    "buildings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("template_id", Integer, nullable=False),  # muda a cada nível (NextGradeTemplateId)
    _int("property1"),
    _int("property2"),
)

_mapped = False


def map_entities() -> None:
    """Liga as dataclasses do domínio às tabelas (idempotente)."""
    global _mapped
    if _mapped:
        return
    for entity, table in (
        (Account, accounts),
        (PlayTicket, play_tickets),
        (GameServer, game_servers),
        (Character, characters),
        (Hero, heroes),
        (Castle, castles),
        (Building, buildings),
    ):
        mapper_registry.map_imperatively(entity, table)
    _mapped = True
