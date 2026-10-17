"""Implementações SQLAlchemy das portas de ``domain.repositories``."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..domain.models import Account, Castle, Character, GameServer, Hero, PlayTicket


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
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        # close() desfaz a transação pendente sem expirar os objetos já carregados/commitados,
        # que continuam utilizáveis (destacados) depois do bloco.
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
