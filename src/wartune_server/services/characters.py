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
    PlayerSystems,
    Quest,
    ShopBuy,
    TreasureMap,
    WildBox,
    WildLand,
)
from ..domain.repositories import UnitOfWork, UnitOfWorkFactory
from ..templates.repository import GameTemplates
from .clock import Clock, SystemClock

NICK_MIN, NICK_MAX = 2, 14  # nomes de guilda
# nome de personagem: (cliente) MainFigureView.loadCheckNickname e RenameView, 4 a 12 de StringUtils.checkStringLength
NAME_MIN, NAME_MAX = 4, 12
NAME_TAKEN = "Character name already in use."  # (cliente) noviceII.node.AddUserNameFrame.describt07
_FORBIDDEN = re.compile(r"[<>&\"'|\\/%\s]")


def _bad(nick: str) -> bool:
    return bool(_FORBIDDEN.search(nick)) or any(unicodedata.category(c).startswith("C") for c in nick)


def normalize_nickname(raw: str) -> str:
    nick = unicodedata.normalize("NFC", raw).strip()
    if not NICK_MIN <= len(nick) <= NICK_MAX:
        raise ValidationError(f"o nome deve ter de {NICK_MIN} a {NICK_MAX} caracteres")
    if _bad(nick):
        raise ValidationError("o nome contém caracteres não permitidos")
    return nick


def name_length(nick: str) -> int:
    """Tamanho como o cliente mede: bytes do ``writeMultiByte`` na página do sistema, ideograma vale 2 (a mesma faixa
    19968-40869 do ``StringUtils.substr``)."""
    return sum(2 if 19968 <= ord(c) <= 40869 else 1 for c in nick)


def character_name(raw: str) -> str:
    """Nome de personagem (registro, ``/nicknamecheck``, 8345). O ``@message`` do HTTP vai direto para a tela
    (``MainFigureView``: ``alertTxt = @message``), então os textos são os do ``AddUserNameFrame`` inglês."""
    nick = unicodedata.normalize("NFC", raw).strip()
    if not nick:
        raise ValidationError("Character name cannot be empty!")  # describt02
    if name_length(nick) < NAME_MIN:
        raise ValidationError("Character name is too short!")  # describt03
    if name_length(nick) > NAME_MAX:
        raise ValidationError("Character name is too long!")  # describt04
    if _bad(nick):
        raise ValidationError("Character name contains invalid characters!")  # describt05
    return nick


class CastlePlacement(Protocol):
    """Escolhe onde o castelo nasce no mapa-múndi."""

    def place(self, character_id: int) -> tuple[int, int, int]: ...


class GridCastlePlacement:
    """Distribui castelos numa grade fixa de um mapa.

    O padrão põe todo castelo novo em (26,46), como o oficial (inglês #532: castelo em 26,46; #3: exército em 24,44): o
    guia do tutorial procura o castelo no pixel (520,920) e as minas em volta (world_mines).
    ponytail: cada jogador só vê o próprio castelo, então dividir o ponto não colide; com mapa
    compartilhado, uma instância 100000xxx por grupo de jogadores, como o oficial.
    """

    def __init__(self, map_id: int = 100000313, origin: tuple[int, int] = (26, 46), cols: int = 1) -> None:
        self._map_id, self._origin, self._cols = map_id, origin, cols

    def place(self, character_id: int) -> tuple[int, int, int]:
        slot = character_id % (self._cols * self._cols)
        return self._map_id, self._origin[0] + (slot % self._cols) * 4, self._origin[1] + (slot // self._cols) * 4


# Nível 1 dos prédios com que o oficial começa: (visto) tutorial_en #582, 4130 com 120101, 40201 e 90101. O depósito,
# a academia e a Gold Refinery nascem pelo nível (``castle.level_buildings``, UpGradeTempInfos tipo 3).
# Os prédios 1501-1511 (templates 150101...) são criados pelo próprio cliente: não enviar.
STARTING_BUILDINGS = (
    90101,  # 901 conselho (prédio principal)
    40201,  # 402 quartel
    120101,  # 1201 casa
)


def starting_quests(templates: GameTemplates) -> list[int]:
    """Missões do tutorial (condição 23) sem pré-requisito que o nível 1 aceita: nascem com o personagem. (visto)
    captura EN #81: a 10 vem no 112 do login com o addDate da criação, e o cliente nunca manda o 5012 dela. Nos dados
    só a 10 passa (a 187, a outra 23 sem pré-requisito, pede nível 15)."""
    ids = {int(c["TemplateId"]) for c in templates.find("QuestCondictionInfos", CondictionType=23)}
    rows = [(i, templates.get("QuestTemps", i)) for i in sorted(ids)]
    return [i for i, row in rows if row is not None and not row.get("PreQuestId") and int(row["NeedMinLevel"]) <= 1]


@dataclass(frozen=True, slots=True)
class RegistrationRequest:
    character_id: int
    nickname: str
    sex: int
    camp: int
    icon: int


class CharacterService:
    def __init__(
        self, uow: UnitOfWorkFactory, templates: GameTemplates, placement: CastlePlacement, clock: Clock | None = None
    ) -> None:
        self._uow = uow
        self._templates = templates
        self._placement = placement
        self._clock = clock or SystemClock()

    async def register(self, req: RegistrationRequest) -> Character:
        nickname = character_name(req.nickname)
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
                raise ConflictError(NAME_TAKEN)

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
            for template_id in starting_quests(self._templates):
                await uow.save(Quest(character.id, template_id, self._clock.now()))
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
            pawns = await uow.pawns.by_character(character_id)
            stars = await uow.stars.by_character(character_id)
            pets = [p for p in await uow.pets.by_character(character_id) if not p.held]  # à venda: fora da lista
            systems = next(iter(await uow.systems.by_character(character_id)), None)
            treasure = await uow.by_character(TreasureMap, character_id)
            wild_lands = await uow.by_character(WildLand, character_id)
            wild_boxes = await uow.by_character(WildBox, character_id)
        if account is None or server is None:
            raise NotFoundError("conta ou servidor do personagem não encontrado")
        # linha nova só em memória: vai para o banco na primeira save() que a incluir
        systems = systems or PlayerSystems(character_id)
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
            pawns,
            stars,
            pets,
            systems,
            treasure,
            wild_lands,
            wild_boxes,
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
