"""Criação (ativação) de personagem e progresso do tutorial."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from ..domain.errors import ConflictError, NotFoundError, ValidationError
from ..domain.models import (
    OUT_OF_SNAPSHOT,
    Arena,
    ArenaRank,
    Building,
    Castle,
    ChallengeLog,
    Character,
    Consortia,
    ConsortiaEvent,
    ConsortiaInvite,
    ConsortiaItem,
    ConsortiaMember,
    FashionBook,
    Hero,
    Job,
    MysteryShop,
    PlayerSnapshot,
    ShopBuy,
)
from ..domain.repositories import UnitOfWork, UnitOfWorkFactory
from ..templates.repository import GameTemplates

NICK_MIN, NICK_MAX = 2, 14
_FORBIDDEN = re.compile(r"[<>&\"'|\\/%\s]")


def normalize_nickname(raw: str) -> str:
    nick = unicodedata.normalize("NFC", raw).strip()
    if not NICK_MIN <= len(nick) <= NICK_MAX:
        raise ValidationError(f"o nome deve ter de {NICK_MIN} a {NICK_MAX} caracteres")
    if _FORBIDDEN.search(nick) or any(unicodedata.category(c).startswith("C") for c in nick):
        raise ValidationError("o nome contém caracteres não permitidos")
    return nick


class CastlePlacement(Protocol):
    """Escolhe onde o castelo nasce no mapa-múndi."""

    def place(self, character_id: int) -> tuple[int, int, int]: ...


class GridCastlePlacement:
    """Distribui castelos numa grade fixa de um mapa.

    ponytail: não consulta ocupação real nem terreno; troque por uma busca em
    MapNodeInfos/MapPhysicsTempInfos quando o mapa-múndi for implementado.
    """

    def __init__(self, map_id: int = 100000313, origin: tuple[int, int] = (10, 10), cols: int = 20) -> None:
        self._map_id, self._origin, self._cols = map_id, origin, cols

    def place(self, character_id: int) -> tuple[int, int, int]:
        slot = character_id % (self._cols * self._cols)
        return self._map_id, self._origin[0] + (slot % self._cols) * 4, self._origin[1] + (slot // self._cols) * 4


# Nível 1 dos prédios centrais. O cliente não tem como construí-los (só tecnologias),
# e vários pontos da HUD buscam um deles por sonType sem checar null (901, 402, 501, 1201...).
# Os prédios 1501-1511 (templates 150101...) são criados pelo próprio cliente: não enviar.
STARTING_BUILDINGS = (
    90101,  # 901 conselho (prédio principal)
    10101,  # 101 mina de ouro
    30101,  # 301 depósito
    40201,  # 402 quartel
    50101,  # 501 academia
    120101,  # 1201 casa
)


@dataclass(frozen=True, slots=True)
class RegistrationRequest:
    character_id: int
    nickname: str
    sex: int
    camp: int
    icon: int


class CharacterService:
    def __init__(self, uow: UnitOfWorkFactory, templates: GameTemplates, placement: CastlePlacement) -> None:
        self._uow = uow
        self._templates = templates
        self._placement = placement

    async def register(self, req: RegistrationRequest) -> Character:
        nickname = normalize_nickname(req.nickname)
        try:
            job = Job(req.icon)
        except ValueError:
            raise ValidationError("classe inválida") from None
        template = self._templates.hero(job.value)

        async with self._uow() as uow:
            character = await uow.characters.get(req.character_id)
            if character is None or character.id is None:
                raise NotFoundError("personagem não encontrado")
            if character.active:
                raise ConflictError("personagem já criado")
            if await uow.characters.nickname_taken(character.server_id, nickname):
                raise ConflictError("este nome já está em uso")

            character.nickname = nickname
            character.job = job.value
            character.sex = int(job.sex)  # o ícone define o sexo; ignora divergência do cliente
            character.camp = req.camp or 1
            character.active = True

            await uow.heroes.add(
                Hero(
                    character_id=character.id,
                    template_id=template.template_id,
                    nickname=nickname,
                    power=template.power,
                    agility=template.agility,
                    intellect=template.intellect,
                    captain=template.captain,
                    physique=template.physique,
                    skill_script=template.skill_script,
                    is_leader=True,
                )
            )
            map_id, x, y = self._placement.place(character.id)
            await uow.castles.add(Castle(character.id, nickname, map_id, x, y))
            for template_id in STARTING_BUILDINGS:
                if next(self._templates.find("BuildingTempInfos", TemplateId=template_id), None) is None:
                    raise NotFoundError(f"template de prédio {template_id} ausente no tempinfos")
                await uow.buildings.add(Building(character.id, template_id))
            await uow.commit()
            return character

    async def set_novice_process(self, character_id: int, value: int) -> None:
        async with self._uow() as uow:
            character = await uow.characters.get(character_id)
            if character is None:
                raise NotFoundError("personagem não encontrado")
            character.novice_process = max(0, value)
            await uow.commit()

    async def snapshot(self, character_id: int) -> PlayerSnapshot:
        async with self._uow() as uow:
            character = await uow.characters.get(character_id)
            if character is None:
                raise NotFoundError("personagem não encontrado")
            account = await uow.accounts.get(character.account_id)
            server = await uow.servers.get(character.server_id)
            heroes = await uow.heroes.by_character(character_id)
            castle = await uow.castles.by_character(character_id)
            buildings = await uow.buildings.by_character(character_id)
            quests = await uow.quests.by_character(character_id)
            # correio e mercado: o item sai do snapshot até ser retirado (5022, cancelamento, compra)
            items = [i for i in await uow.items.by_character(character_id) if i.bag_type not in OUT_OF_SNAPSHOT]
            relations = await uow.relations.by_character(character_id)
            groups = await uow.friend_groups.by_character(character_id)
            sns = await uow.sns.by_character(character_id)
            marriage = await uow.marriages.by_character(character_id)
            arena = await uow.arena.by_character(character_id) or Arena(character_id)
            shop_buys = await uow.by_character(ShopBuy, character_id)
            fashions = await uow.by_character(FashionBook, character_id)
            mystery = await uow.by_character(MysteryShop, character_id)
            orders = await uow.orders.by_character(character_id)
            lands = await uow.lands.by_character(character_id)
            events = await uow.events.by_character(character_id)
        if account is None or server is None:
            raise NotFoundError("conta ou servidor do personagem não encontrado")
        return PlayerSnapshot(
            account,
            server,
            character,
            heroes,
            castle,
            buildings,
            quests,
            items,
            relations,
            groups,
            sns,
            marriage,
            arena,
            shop_buys,
            fashions,
            mystery,
            orders,
            lands,
            events,
        )

    async def read[T](self, query: Callable[[UnitOfWork], Awaitable[T]]) -> T:
        """Consulta avulsa numa transação só de leitura (outros jogadores, correio, busca)."""
        async with self._uow() as uow:
            return await query(uow)

    async def write[T](self, change: Callable[[UnitOfWork], Awaitable[T]]) -> T:
        """Como ``read``, mas grava no fim: inserts que dependem de ids gerados (correio + anexos)."""
        async with self._uow() as uow:
            result = await change(uow)
            await uow.commit()
            return result

    async def guild_state(
        self, server_id: int
    ) -> tuple[
        list[Consortia], list[ConsortiaMember], list[ConsortiaInvite], list[ConsortiaEvent], list[ConsortiaItem]
    ]:
        async with self._uow() as uow:
            return await uow.guilds.load(server_id)

    async def characters(self, ids: list[int]) -> list[Character]:
        if not ids:
            return []
        async with self._uow() as uow:
            return await uow.guilds.characters(ids)

    async def save(self, *entities: object, delete: tuple[object, ...] = (), ranks: tuple[ArenaRank, ...] = ()) -> None:
        """Grava entidades do snapshot alteradas em memória (personagem, herói, missões, itens) e
        apaga ``delete``, tudo numa transação: consumir um item e dar a recompensa é atômico.
        ``ranks``: posições do coliseu (de qualquer jogador) trocadas na mesma transação."""
        async with self._uow() as uow:
            for entity in delete:
                await uow.delete(entity)
            for entity in entities:
                await uow.save(entity)
            for r in ranks:
                await uow.arena.set_rank(r.character_id, r.rank)
            await uow.commit()

    # -- coliseu e torneio de fadas (leituras fora do snapshot: dados de outros jogadores) --------

    async def arena_rank(self, character_id: int) -> int:
        async with self._uow() as uow:
            return await uow.arena.rank(character_id)

    async def arena_last_rank(self, server_id: int) -> int:
        async with self._uow() as uow:
            return await uow.arena.last_rank(server_id)

    async def arena_ranks(self, server_id: int, low: int, high: int) -> list[ArenaRank]:
        async with self._uow() as uow:
            return await uow.arena.ranks(server_id, low, high)

    async def pet_order(self, server_id: int, score: int) -> int:
        async with self._uow() as uow:
            return await uow.arena.pet_order(server_id, score)

    async def pet_board(self, server_id: int, limit: int, below: int | None = None) -> list[Arena]:
        async with self._uow() as uow:
            return await uow.arena.pet_board(server_id, limit, below)

    async def challenge_logs(self, character_id: int, kind: int, limit: int) -> list[ChallengeLog]:
        async with self._uow() as uow:
            return await uow.arena.logs(character_id, kind, limit)
