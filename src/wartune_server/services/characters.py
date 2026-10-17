"""Criação (ativação) de personagem e progresso do tutorial."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from ..domain.errors import ConflictError, NotFoundError, ValidationError
from ..domain.models import (
    Building,
    Castle,
    Character,
    Consortia,
    ConsortiaEvent,
    ConsortiaInvite,
    ConsortiaItem,
    ConsortiaMember,
    Hero,
    Job,
    PlayerSnapshot,
)
from ..domain.repositories import UnitOfWorkFactory
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
            items = await uow.items.by_character(character_id)
        if account is None or server is None:
            raise NotFoundError("conta ou servidor do personagem não encontrado")
        return PlayerSnapshot(account, server, character, heroes, castle, buildings, quests, items)

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

    async def save(self, *entities: object, delete: tuple[object, ...] = ()) -> None:
        """Grava entidades do snapshot alteradas em memória (personagem, herói, missões, itens) e
        apaga ``delete``, tudo numa transação: consumir um item e dar a recompensa é atômico."""
        async with self._uow() as uow:
            for entity in delete:
                await uow.delete(entity)
            for entity in entities:
                await uow.save(entity)
            await uow.commit()
