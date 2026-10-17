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
    BuildOrder,
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
    FriendGroup,
    GameServer,
    Hero,
    Item,
    Mail,
    MailAnnex,
    Marriage,
    Pawn,
    Pet,
    PlayerSystems,
    PlayTicket,
    Quest,
    Relation,
    SnsProfile,
    Star,
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

    async def by_ids(self, ids: list[int]) -> list[Character]:
        if not ids:
            return []
        return list(await self._s.scalars(select(Character).where(Character.id.in_(ids))))  # type: ignore[union-attr]

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


class SqlRelationRepository(_Repo):
    async def by_character(self, character_id: int) -> list[Relation]:
        query = select(Relation).where(Relation.character_id == character_id).order_by(Relation.id)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))

    async def get(self, character_id: int, other_id: int) -> Relation | None:
        query = select(Relation).where(
            Relation.character_id == character_id,  # type: ignore[arg-type]
            Relation.other_id == other_id,  # type: ignore[arg-type]
        )
        return await self._s.scalar(query)


class SqlFriendGroupRepository(_Repo):
    async def by_character(self, character_id: int) -> list[FriendGroup]:
        query = select(FriendGroup).where(FriendGroup.character_id == character_id).order_by(FriendGroup.group_id)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))


class SqlSnsRepository(_Repo):
    async def by_character(self, character_id: int) -> SnsProfile | None:
        return await self._s.scalar(select(SnsProfile).where(SnsProfile.character_id == character_id))  # type: ignore[arg-type]

    async def search(self, filters: dict[str, int], offset: int, limit: int) -> tuple[int, list[SnsProfile]]:
        """Perfis com todos os ``filters`` iguais (0 = qualquer), mais o total para paginar."""
        where = [getattr(SnsProfile, k) == v for k, v in filters.items() if v]
        total = await self._s.scalar(select(func.count()).select_from(SnsProfile).where(*where))
        query = select(SnsProfile).where(*where).order_by(SnsProfile.id).offset(offset).limit(limit)  # type: ignore[arg-type]
        return int(total or 0), list(await self._s.scalars(query))


class SqlMailRepository(_Repo):
    async def by_receiver(self, receiver_id: int, ids: list[int] | None = None) -> list[Mail]:
        query = select(Mail).where(Mail.receiver_id == receiver_id)  # type: ignore[arg-type]
        if ids is not None:
            query = query.where(Mail.id.in_(ids))  # type: ignore[union-attr]
        return list(await self._s.scalars(query.order_by(Mail.id)))  # type: ignore[arg-type]

    async def annexes(self, mail_ids: list[int]) -> list[MailAnnex]:
        if not mail_ids:
            return []
        query = select(MailAnnex).where(MailAnnex.mail_id.in_(mail_ids)).order_by(MailAnnex.mail_id, MailAnnex.slot)  # type: ignore[attr-defined, arg-type]
        return list(await self._s.scalars(query))


class SqlMarriageRepository(_Repo):
    async def by_character(self, character_id: int) -> Marriage | None:
        return await self._s.scalar(select(Marriage).where(Marriage.character_id == character_id))  # type: ignore[arg-type]


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


class SqlGuildRepository(_Repo):
    """Leitura de tudo da guilda de um servidor (fica em memória no ``Guilds``; grava pelo ``save``)."""

    async def load(
        self, server_id: int
    ) -> tuple[
        list[Consortia], list[ConsortiaMember], list[ConsortiaInvite], list[ConsortiaEvent], list[ConsortiaItem]
    ]:
        guilds = list(await self._s.scalars(select(Consortia).where(Consortia.server_id == server_id)))  # type: ignore[arg-type]
        ids = [g.id for g in guilds]

        async def rows[T](cls: type[T]) -> list[T]:
            query = select(cls).where(cls.consortia_id.in_(ids)).order_by(cls.id)  # type: ignore[attr-defined]
            return list(await self._s.scalars(query))

        return (
            guilds,
            await rows(ConsortiaMember),
            await rows(ConsortiaInvite),
            await rows(ConsortiaEvent),
            await rows(ConsortiaItem),
        )

    async def characters(self, ids: list[int]) -> list[Character]:
        return list(await self._s.scalars(select(Character).where(Character.id.in_(ids))))  # type: ignore[union-attr]


class SqlBuildOrderRepository(_Repo):
    async def by_character(self, character_id: int) -> list[BuildOrder]:
        query = select(BuildOrder).where(BuildOrder.character_id == character_id).order_by(BuildOrder.order_id)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))


class SqlFarmLandRepository(_Repo):
    async def by_character(self, character_id: int) -> list[FarmLand]:
        query = select(FarmLand).where(FarmLand.character_id == character_id).order_by(FarmLand.pos)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))


class SqlEventStateRepository(_Repo):
    async def by_character(self, character_id: int) -> list[EventState]:
        query = select(EventState).where(EventState.character_id == character_id).order_by(EventState.id)  # type: ignore[arg-type]
        return list(await self._s.scalars(query))


class SqlOwnedRepository[T]:
    def __init__(self, session: AsyncSession, entity: type[T]) -> None:
        self._s, self._entity = session, entity

    async def by_character(self, character_id: int) -> list[T]:
        e: Any = self._entity
        return list(await self._s.scalars(select(e).where(e.character_id == character_id).order_by(e.id)))


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
        self.relations = SqlRelationRepository(self._session)
        self.friend_groups = SqlFriendGroupRepository(self._session)
        self.sns = SqlSnsRepository(self._session)
        self.mails = SqlMailRepository(self._session)
        self.marriages = SqlMarriageRepository(self._session)
        self.arena = SqlArenaRepository(self._session)
        self.guilds = SqlGuildRepository(self._session)
        self.orders = SqlBuildOrderRepository(self._session)
        self.lands = SqlFarmLandRepository(self._session)
        self.events = SqlEventStateRepository(self._session)
        self.pawns = SqlOwnedRepository(self._session, Pawn)
        self.stars = SqlOwnedRepository(self._session, Star)
        self.pets = SqlOwnedRepository(self._session, Pet)
        self.systems = SqlOwnedRepository(self._session, PlayerSystems)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        # close() desfaz a transação pendente sem expirar os objetos já carregados/commitados,
        # que continuam utilizáveis (destacados) depois do bloco.
        await self._session.close()

    async def by_character[T](self, entity: type[T], character_id: int) -> list[T]:
        query = select(entity).where(entity.character_id == character_id).order_by(entity.id)  # type: ignore[attr-defined]
        return list(await self._session.scalars(query))

    async def save(self, entity: object) -> None:
        # nova: add (o próprio objeto ganha o id); já gravada e destacada: merge copia o estado
        if getattr(entity, "id", None) is None:
            self._session.add(entity)
        else:
            await self._session.merge(entity)

    async def flush(self) -> None:
        await self._session.flush()

    async def delete(self, entity: object) -> None:
        await self._session.delete(await self._session.merge(entity))

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
