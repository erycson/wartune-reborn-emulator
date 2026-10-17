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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import registry
from sqlalchemy.types import TypeDecorator

from ..domain.models import (
    Account,
    Arena,
    ArenaRank,
    Building,
    BuildOrder,
    CashLedger,
    Castle,
    ChallengeLog,
    Character,
    Consortia,
    ConsortiaEvent,
    ConsortiaInvite,
    ConsortiaItem,
    ConsortiaMember,
    EventState,
    FarmLand,
    FashionBook,
    FriendGroup,
    GameServer,
    Hero,
    Item,
    ItemLog,
    LoginHistory,
    Mail,
    MailAnnex,
    Marriage,
    MysteryShop,
    PlayTicket,
    Quest,
    Relation,
    ShopBuy,
    SnsProfile,
    TreasureMap,
)

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
    _int("websocket_port"),
    Column("rsa_modulus", Text, nullable=False, default="", server_default=""),
    Column("rsa_exponent", String(32), nullable=False, default="", server_default=""),
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
    _int("strategy"),
    _int("crystals", 1000),
    _int("weary", 200),
    _int("weary_limit", 200),
    _int("novice_process"),
    _int("fighting_capacity"),
    _int("repute"),
    _int("geste"),
    _int("charm"),
    _int("space_x", 72),  # último tile na cidade do céu (o oficial nasce em 72,74)
    _int("space_y", 74),
    _int("qte_guide"),  # 8302: guia da skill QTE visto (PlayerMsg.qteGuide)
    Column("vice_password", String(64), nullable=False, default="", server_default=""),  # sha256; "" = sem senha
    Column("vice_reset_at", UTCDateTime),  # 8806 op 4: pedido de reset da senha secundária
    _int("vehicle_exp"),  # 4515 PlayerVehicleProfileMsg
    _int("vehicle_score"),
    _int("vehicle_default", 1),
    Column("vehicles", String(255), nullable=False, default="1", server_default="1"),  # templateIds possuídos
    Column("created_at", UTCDateTime, nullable=False),
    Column("last_login_at", UTCDateTime),
    Column("refuse_friend", Boolean, nullable=False, default=False, server_default="0"),
    _int("bugle_free_used"),
    Column("bugle_free_day", String(10), nullable=False, default="", server_default=""),
    _int("consortia_offer"),
    _int("consortia_total_offer"),
    _int("skill_attack"),
    _int("skill_agility"),
    _int("skill_ability"),
    _int("skill_captain"),
    _int("skill_gold"),
    _int("skill_physique"),
    Column("is_auto", Boolean, nullable=False, default=False, server_default="0"),
    Column("last_out_consortia", UTCDateTime),
    _int("bag_count"),
    Column("rental_bag_until", UTCDateTime),
    _int("store_grade"),
    _int("store_gp"),
    _int("appell_id"),
    _int("box_period"),
    _int("box_seconds"),
    Column("box_counted_at", UTCDateTime),
    Column("offline_at", UTCDateTime),
    _int("offline_seconds"),
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
    Column("hide_fashion", Boolean, nullable=False, default=False, server_default="0"),
    _int("blood"),
    _int("blood_id"),
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
    Column("produced_at", UTCDateTime),
    _int("impose_used"),
    Column("imposed_at", UTCDateTime),
    _int("farm_grade", 1),
    _int("farm_gp"),
    _int("tree_water"),
    _int("tree_fruit"),
    Column("tree_watered_at", UTCDateTime),
    Column("tree_picked_at", UTCDateTime),
)

farm_lands = Table(
    "farm_lands",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("pos", Integer, nullable=False),
    Column("item_template_id", Integer, nullable=False),
    Column("planted_at", UTCDateTime, nullable=False),
    Column("mature_at", UTCDateTime, nullable=False),
    _int("reward_count"),
    _int("worm"),
    _int("grass"),
    Column("accelerated", Boolean, nullable=False, default=False, server_default="0"),
    UniqueConstraint("character_id", "pos"),
)

build_orders = Table(
    "build_orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("order_id", Integer, nullable=False),
    Column("order_type", Integer, nullable=False),
    Column("begin_at", UTCDateTime, nullable=False),
    _int("need_time"),
    UniqueConstraint("character_id", "order_id"),
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

quests = Table(
    "quests",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("template_id", Integer, nullable=False),
    Column("completed", Boolean, nullable=False, default=False, server_default="0"),
    _int("progress"),
    Column("added_at", UTCDateTime, nullable=False),
    Column("completed_at", UTCDateTime),
    UniqueConstraint("character_id", "template_id"),
)

items = Table(
    "items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("template_id", Integer, nullable=False),
    _int("bag_type", 1),
    _int("object_id"),
    _int("pos"),
    _int("count", 1),
    _int("random_skill"),
    Column("is_new", Boolean, nullable=False, default=True, server_default="1"),
    _int("random_skill_2"),
    _int("random_skill_3"),
    _int("random_skill_4"),
    _int("random_skill_5"),
    _int("strengthen_grade"),
    _int("join_1", -1),
    _int("join_2", -1),
    _int("join_3", -1),
    _int("join_4", -1),
    Column("is_locked", Boolean, nullable=False, default=False, server_default="0"),
    _int("mould_grade"),
)

shop_buys = Table(
    "shop_buys",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    _int("good_id"),
    Column("day", String(10), nullable=False, default="", server_default=""),
    _int("counts"),
    UniqueConstraint("character_id", "good_id"),
)

fashion_books = Table(
    "fashion_books",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    _int("template_id"),
    Column("is_switch", Boolean, nullable=False, default=True, server_default="1"),
    _int("appraisal_skill"),
    UniqueConstraint("character_id", "template_id"),
)

mystery_shops = Table(
    "mystery_shops",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("fresh_at", UTCDateTime, nullable=False, server_default=func.current_timestamp()),
    Column("goods", Text, nullable=False, default="", server_default=""),
    Column("bought", Text, nullable=False, default="", server_default=""),
    Column("day", String(10), nullable=False, default="", server_default=""),
    _int("buy_count"),
)


def _created_at() -> Column[datetime]:
    # o portal PHP também grava nestas tabelas e deixa a data por conta do banco
    return Column("created_at", UTCDateTime, nullable=False, server_default=func.current_timestamp(), index=True)


def _text(name: str) -> Column[str]:
    return Column(name, Text, nullable=False, default="", server_default="")


login_history = Table(
    "login_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="SET NULL")),
    Column("source", Text, nullable=False, server_default="game"),
    _text("ip"),
    Column("user_agent", Text),
    _created_at(),
)

cash_ledger = Table(
    "cash_ledger",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    _int("delta_point"),
    _int("delta_gift_token"),
    _int("balance_point"),
    _int("balance_gift_token"),
    _text("reason"),
    _text("ref"),
    Column("gm", Text),
    _created_at(),
)

item_log = Table(
    "item_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    _int("template_id"),
    _int("count"),
    _text("action"),
    _text("ref"),
    _created_at(),
)


def _owner(name: str = "character_id", **kw: Any) -> Column[int]:
    return Column(name, Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, **kw)


relations = Table(
    "relations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner(index=True),
    _owner("other_id", index=True),  # quem me tem na lista: avisos 160/161
    Column("relation", Integer, nullable=False),
    _int("group_id", -1),
    UniqueConstraint("character_id", "other_id"),
)

friend_groups = Table(
    "friend_groups",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner(index=True),
    Column("group_id", Integer, nullable=False),
    Column("name", String(32), nullable=False),
    UniqueConstraint("character_id", "group_id"),
)

sns_profiles = Table(
    "sns_profiles",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner(unique=True),
    Column("sign_desc", String(255), nullable=False, default="", server_default=""),
    *(
        _int(name)
        for name in (
            "sex",
            "birthday_type",
            "birth_year",
            "birth_month",
            "birth_day",
            "star_id",
            "blood_type",
            "country",
            "province",
            "city",
            "head_id",
        )
    ),
)

mails = Table(
    "mails",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner("receiver_id", index=True),
    _int("sender_id"),  # sem FK: 0 = sistema, e o correio sobrevive ao remetente
    Column("sender_nick", String(32), nullable=False, default="", server_default=""),
    _int("sender_grades"),
    _int("mail_type", 1),
    _int("send_type", 1),
    Column("title", String(64), nullable=False),
    Column("contents", Text, nullable=False),
    Column("sent_at", UTCDateTime, nullable=False),
    Column("read_at", UTCDateTime),
    _int("validity_days", 30),
)

mail_annexes = Table(
    "mail_annexes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("mail_id", Integer, ForeignKey("mails.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("slot", Integer, nullable=False),
    Column("template_id", Integer, nullable=False),
    Column("count", Integer, nullable=False),
    Column("taken", Boolean, nullable=False, default=False, server_default="0"),
    UniqueConstraint("mail_id", "slot"),
)

marriages = Table(
    "marriages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner(unique=True),
    _owner("mate_id"),
    Column("state", Integer, nullable=False),
    _int("spec_id"),
    Column("since", UTCDateTime, nullable=False),
    Column("married_at", UTCDateTime),
)


def _str(name: str, size: int) -> Column[str]:
    return Column(name, String(size), nullable=False, default="", server_default="")


treasure_maps = Table(
    "treasure_maps",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner(unique=True),
    _str("day", 10),
    _int("join_count"),
    _int("reward_count"),
)

arenas = Table(
    "arenas",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner(unique=True),
    _str("day", 10),
    _int("challenge_count"),
    Column("cool_until", UTCDateTime),
    _int("win_streak"),
    _str("reward_day", 10),
    _int("pet_count"),
    _int("pet_buy_count"),
    Column("pet_cool_until", UTCDateTime),
    _int("pet_score", 1000),
    _str("pet_formation", 128),
    _str("pet_reward_day", 10),
    _str("pet_reward_week", 10),
    _int("attack_left", 5),
)

# posição do coliseu; trocas entre dois jogadores acontecem sob a trava de game/arena.py, por isso
# sem UNIQUE em "rank" (a troca passaria por um estado repetido no meio da transação)
arena_ranks = Table(
    "arena_ranks",
    metadata,
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
    _int("rank"),
)

challenge_logs = Table(
    "challenge_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    _owner(index=True),
    _int("kind"),
    Column("created_at", UTCDateTime, nullable=False),
    _int("target_id"),
    _str("target_name", 32),
    Column("is_attack", Boolean, nullable=False, default=False, server_default="0"),
    Column("won", Boolean, nullable=False, default=False, server_default="0"),
    _int("rank"),
    _int("forward"),
    _int("target_grades"),
    _int("target_job"),
)


consortias = Table(
    "consortias",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("server_id", Integer, ForeignKey("game_servers.id"), nullable=False),
    Column("name", String(32), nullable=False),
    _int("creator_id"),
    _str("creator_name", 32),
    _int("chairman_id"),
    Column("created_at", UTCDateTime, nullable=False),
    _int("levels", 1),
    *(_int(f"{k}_level") for k in ("shop", "altar", "school", "store", "attack", "defence", "agility")),
    *(_int(f"{k}_level") for k in ("ability", "captain", "gold", "physique")),
    _int("offer"),
    _int("total_offer"),
    _str("placard", 255),
    _str("description", 255),
    _str("group_placard", 255),
    Column("open_app", Boolean, nullable=False, default=True, server_default="1"),
    _int("code_type"),
    _int("code_need"),
    Column("code_begin_at", UTCDateTime),
    _int("kick_count"),
    Column("kick_at", UTCDateTime),
    _int("altar_state"),
    Column("altar_at", UTCDateTime),
    _int("max_wave"),
    _int("voting_state"),
    _int("voting_id"),
    Column("voting_at", UTCDateTime),
    UniqueConstraint("server_id", "name"),
)

consortia_members = Table(
    "consortia_members",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("consortia_id", Integer, ForeignKey("consortias.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("joined_at", UTCDateTime, nullable=False),
    _int("duty_id", 5),
    _int("today_offer"),
    _str("offer_day", 10),
    _int("bless_count"),
    _str("bless_day", 10),
    _int("voted_for"),
    _int("voted_id"),
)

consortia_invites = Table(
    "consortia_invites",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("consortia_id", Integer, ForeignKey("consortias.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("user_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created_at", UTCDateTime, nullable=False),
    _int("invite_id"),
    Column("from_type", Boolean, nullable=False, default=False, server_default="0"),
)

consortia_events = Table(
    "consortia_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("consortia_id", Integer, ForeignKey("consortias.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created_at", UTCDateTime, nullable=False),
    _str("remark", 255),
    _int("type", 1),
)

consortia_items = Table(
    "consortia_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("consortia_id", Integer, ForeignKey("consortias.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("template_id", Integer, nullable=False),
    _int("count", 1),
)

event_states = Table(
    "event_states",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("key", String(96), nullable=False),
    _int("value"),
    Column("text", Text, nullable=False, default="", server_default=""),
    Column("updated_at", UTCDateTime, nullable=False),
    UniqueConstraint("character_id", "key"),
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
        (Quest, quests),
        (Item, items),
        (LoginHistory, login_history),
        (CashLedger, cash_ledger),
        (ItemLog, item_log),
        (Relation, relations),
        (FriendGroup, friend_groups),
        (SnsProfile, sns_profiles),
        (Mail, mails),
        (MailAnnex, mail_annexes),
        (Marriage, marriages),
        (Arena, arenas),
        (TreasureMap, treasure_maps),
        (ArenaRank, arena_ranks),
        (ChallengeLog, challenge_logs),
        (Consortia, consortias),
        (ConsortiaMember, consortia_members),
        (ConsortiaInvite, consortia_invites),
        (ConsortiaEvent, consortia_events),
        (ConsortiaItem, consortia_items),
        (ShopBuy, shop_buys),
        (FashionBook, fashion_books),
        (MysteryShop, mystery_shops),
        (BuildOrder, build_orders),
        (FarmLand, farm_lands),
        (EventState, event_states),
    ):
        mapper_registry.map_imperatively(entity, table)
    _mapped = True
