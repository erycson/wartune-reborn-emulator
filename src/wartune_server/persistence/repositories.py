"""Implementações SQLAlchemy das portas de ``domain.repositories``."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..domain.models import (
    Account,
    Arena,
    ArenaRank,
    Building,
    Castle,
    ChallengeLog,
    Character,
    GameServer,
    Hero,
    Item,
    PlayTicket,
    Quest,
)


class _Repo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session


class SqlAccountRepository(_Repo):
    async def add(self, account: Account) -> Account:
        self._s.add(account)
        await self._s.flush()
        return account

    async def get(self, account_id: int) -> Account | None:
        return await self._s.get(Account, account_id)

    async def by_username(self, username: str) -> Account | None:
        return await self._s.scalar(select(Account).where(Account.username == username))  # type: ignore[arg-type]


class SqlPlayTicketRepository(_Repo):
    async def add(self, ticket: PlayTicket) -> PlayTicket:
        self._s.add(ticket)
        await self._s.flush()
        return ticket

    async def get(self, token: str) -> PlayTicket | None:
        return await self._s.get(PlayTicket, token)


class SqlGameServerRepository(_Repo):
    async def get(self, server_id: int) -> GameServer | None:
        return await self._s.get(GameServer, server_id)

    async def list(self) -> list[GameServer]:
        return list(await self._s.scalars(select(GameServer).order_by(GameServer.id)))  # type: ignore[arg-type]

    async def upsert(self, server: GameServer) -> GameServer:
        merged = await self._s.merge(server)
        await self._s.flush()
        return merged


class SqlCharacterRepository(_Repo):
    async def add(self, character: Character) -> Character:
        self._s.add(character)
        await self._s.flush()
        return character

    async def get(self, character_id: int) -> Character | None:
        return await self._s.get(Character, character_id)

    async def by_nickname(self, server_id: int, nickname: str) -> Character | None:
        stmt = select(Character).where(
            Character.server_id == server_id,  # type: ignore[arg-type]
            Character.nickname == nickname,  # type: ignore[arg-type]
        )
        return await self._s.scalar(stmt)

    async def by_account(self, account_id: int, server_id: int) -> Character | None:
        stmt = select(Character).where(
            Character.account_id == account_id,  # type: ignore[arg-type]
            Character.server_id == server_id,  # type: ignore[arg-type]
        )
        return await self._s.scalar(stmt)

    async def nickname_taken(self, server_id: int, nickname: str) -> bool:
        stmt = select(
            exists().where(
                Character.server_id == server_id,  # type: ignore[arg-type]
                Character.nickname == nickname,  # type: ignore[arg-type]
            )
        )
        return bool(await self._s.scalar(stmt))


class SqlHeroRepository(_Repo):
    async def add(self, hero: Hero) -> Hero:
        self._s.add(hero)
        await self._s.flush()
        return hero

    async def by_character(self, character_id: int) -> list[Hero]:
        stmt = select(Hero).where(Hero.character_id == character_id).order_by(Hero.id)  # type: ignore[arg-type]
        return list(await self._s.scalars(stmt))


class SqlCastleRepository(_Repo):
    async def add(self, castle: Castle) -> Castle:
        self._s.add(castle)
        await self._s.flush()
        return castle

    async def by_character(self, character_id: int) -> Castle | None:
        return await self._s.scalar(select(Castle).where(Castle.character_id == character_id))  # type: ignore[arg-type]


class SqlBuildingRepository(_Repo):
    async def add(self, building: Building) -> Building:
        self._s.add(building)
        await self._s.flush()
        return building

    async def by_character(self, character_id: int) -> list[Building]:
        query = select(Building).where(Building.character_id == character_id).order_by(Building.id)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))


class SqlQuestRepository(_Repo):
    async def add(self, quest: Quest) -> Quest:
        self._s.add(quest)
        await self._s.flush()
        return quest

    async def by_character(self, character_id: int) -> list[Quest]:
        query = select(Quest).where(Quest.character_id == character_id).order_by(Quest.id)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))


class SqlItemRepository(_Repo):
    async def add(self, item: Item) -> Item:
        self._s.add(item)
        await self._s.flush()
        return item

    async def by_character(self, character_id: int) -> list[Item]:
        query = select(Item).where(Item.character_id == character_id).order_by(Item.id)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))


class SqlArenaRepository(_Repo):
    """Coliseu e torneio de fadas. Os rankings são por servidor (``characters.server_id``)."""

    async def by_character(self, character_id: int) -> Arena | None:
        return await self._s.scalar(select(Arena).where(Arena.character_id == character_id))  # type: ignore[arg-type]

    async def rank(self, character_id: int) -> int:
        row = await self._s.get(ArenaRank, character_id)
        return row.rank if row is not None else 0

    def _ranked(self, server_id: int) -> Any:
        on = ArenaRank.character_id == Character.id
        return select(ArenaRank).join(Character, on).where(Character.server_id == server_id)  # type: ignore[arg-type]

    async def last_rank(self, server_id: int) -> int:
        ranks = [r.rank for r in await self._s.scalars(self._ranked(server_id))]
        return max(ranks, default=0)

    async def ranks(self, server_id: int, low: int, high: int) -> list[ArenaRank]:
        """Posições de ``low`` a ``high`` (inclusive), em ordem."""
        rank = ArenaRank.rank
        query = self._ranked(server_id).where(rank >= low, rank <= high).order_by(rank)
        return list(await self._s.scalars(query))

    async def set_rank(self, character_id: int, rank: int) -> None:
        await self._s.merge(ArenaRank(character_id, rank))

    def _pets(self, server_id: int) -> Any:
        on = Arena.character_id == Character.id
        return select(Arena).join(Character, on).where(Character.server_id == server_id)  # type: ignore[arg-type]

    async def pet_order(self, server_id: int, score: int) -> int:
        """Posição de quem tem ``score`` pontos no torneio de fadas (1 = mais pontos)."""
        higher = self._pets(server_id).where(Arena.pet_score > score, Arena.pet_formation != "")
        return int(await self._s.scalar(select(func.count()).select_from(higher.subquery())) or 0) + 1

    async def pet_board(self, server_id: int, limit: int, below: int | None = None) -> list[Arena]:
        """Os ``limit`` com formação e mais pontos (só os com menos que ``below``, se dado)."""
        score = Arena.pet_score
        query = self._pets(server_id).where(Arena.pet_formation != "")
        if below is not None:
            query = query.where(score < below)
        query = query.order_by(score.desc(), Arena.character_id).limit(limit)  # type: ignore[attr-defined]
        return list(await self._s.scalars(query))

    async def logs(self, character_id: int, kind: int, limit: int) -> list[ChallengeLog]:
        query = (
            select(ChallengeLog)
            .where(ChallengeLog.character_id == character_id, ChallengeLog.kind == kind)  # type: ignore[arg-type]
            .order_by(ChallengeLog.id.desc())  # type: ignore[union-attr]
            .limit(limit)
        )
        return list(await self._s.scalars(query))


class SqlAlchemyUnitOfWork:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def __aenter__(self) -> Self:
        self._session = self._sessions()
        self.accounts = SqlAccountRepository(self._session)
        self.tickets = SqlPlayTicketRepository(self._session)
        self.servers = SqlGameServerRepository(self._session)
        self.characters = SqlCharacterRepository(self._session)
        self.heroes = SqlHeroRepository(self._session)
        self.castles = SqlCastleRepository(self._session)
        self.buildings = SqlBuildingRepository(self._session)
        self.quests = SqlQuestRepository(self._session)
        self.items = SqlItemRepository(self._session)
        self.arena = SqlArenaRepository(self._session)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        # close() desfaz a transação pendente sem expirar os objetos já carregados/commitados,
        # que continuam utilizáveis (destacados) depois do bloco.
        await self._session.close()

    async def save(self, entity: object) -> None:
        # nova: add (o próprio objeto ganha o id); já gravada e destacada: merge copia o estado
        if getattr(entity, "id", None) is None:
            self._session.add(entity)
        else:
            await self._session.merge(entity)

    async def delete(self, entity: object) -> None:
        await self._session.delete(await self._session.merge(entity))

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
