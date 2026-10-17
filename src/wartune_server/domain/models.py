"""Entidades do domínio (sem dependência de banco ou rede).

Modelo multi-servidor: uma ``Account`` é global (login do portal) e pode ter um
``Character`` em cada ``GameServer`` (S1, S2...). Tudo que pertence ao jogo
(herói, castelo, itens...) pendura no personagem, nunca na conta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum


class Sex(IntEnum):
    FEMALE = 0
    MALE = 1


class Job(IntEnum):
    """``JobType`` do cliente: 1-3 masculino, 4-6 feminino (guerreiro, caçador, mago)."""

    MALE_WARRIOR = 1
    MALE_HUNTER = 2
    MALE_WIZARD = 3
    FEMALE_WARRIOR = 4
    FEMALE_HUNTER = 5
    FEMALE_WIZARD = 6

    @property
    def sex(self) -> Sex:
        return Sex.MALE if self.value <= 3 else Sex.FEMALE


@dataclass(eq=False)
class Account:
    username: str
    password_hash: str
    created_at: datetime
    id: int | None = None
    last_login_at: datetime | None = None
    banned: bool = False


@dataclass(eq=False)
class PlayTicket:
    """Ticket emitido pelo portal para a conta entrar em um servidor.

    Vira o flashvar ``key`` do ``Loading.swf`` e volta cifrado no ``POST /login``.
    Pode ser reutilizado até expirar (recarregar a página não derruba o jogador).
    """

    token: str
    account_id: int
    server_id: int
    created_at: datetime
    expires_at: datetime

    def valid_for(self, server_id: int, now: datetime) -> bool:
        return self.server_id == server_id and now < self.expires_at


@dataclass(eq=False)
class GameServer:
    id: int
    name: str
    site: str
    public_host: str
    http_port: int
    socket_port: int
    opened_at: datetime
    websocket_port: int = 0  # ponte do Ruffle; 0 = sem ponte
    # chave pública do login (formato Hurlant) que o portal põe no config.xml deste servidor
    rsa_modulus: str = ""
    rsa_exponent: str = ""


@dataclass(eq=False)
class Character:
    """Personagem de uma conta em um servidor. ``id`` é o ``playerId``/``userId`` do cliente.

    Nasce **inativo** no primeiro ``POST /login`` naquele servidor (o cliente exige
    ``userId != 0``) e é ativado pelo ``visualizeregister`` com apelido/sexo/ícone.
    """

    account_id: int
    server_id: int
    created_at: datetime
    nickname: str | None = None
    sex: int = 0
    camp: int = 1
    job: int = 0
    active: bool = False
    id: int | None = None
    grades: int = 1
    gp: int = 0
    total_gp: int = 0
    gold: int = 0
    point: int = 0  # moeda premium
    gift_token: int = 0
    strategy: int = 0  # "Ruh" (alma), moeda -300
    weary: int = 200
    weary_limit: int = 200
    novice_process: int = 0
    fighting_capacity: int = 0
    repute: int = 0
    geste: int = 0
    charm: int = 0
    last_login_at: datetime | None = None

    @property
    def icon(self) -> int:
        """O cliente usa o mesmo número para ``pic``/``icon`` e ``job``."""
        return self.job


@dataclass(eq=False)
class Hero:
    """Herói líder do personagem (``SimpleHeroInfoMsg``)."""

    character_id: int
    template_id: int
    nickname: str
    id: int | None = None
    grades: int = 1
    gp: int = 0
    power: int = 0
    agility: int = 0
    intellect: int = 0
    captain: int = 0
    physique: int = 0
    power_point: int = 0
    agility_point: int = 0
    intellect_point: int = 0
    captain_point: int = 0
    physique_point: int = 0
    remain_point: int = 0
    skill_point: int = 0
    skill_script: str = ""
    fast_key: str = ""
    fight_pos: int = 1
    is_leader: bool = True


@dataclass(eq=False)
class Castle:
    character_id: int
    name: str
    map_id: int
    pos_x: int
    pos_y: int
    id: int | None = None
    grade: int = 1
    energy: int = 500
    state: int = 1


@dataclass(eq=False)
class Building:
    """Prédio do castelo (``BuildingInfoMsg``). Posição, nível e arte vêm do template."""

    character_id: int
    template_id: int
    id: int | None = None
    property1: int = 0
    property2: int = 0


@dataclass(eq=False)
class Quest:
    """Missão aceita (``QuestInfo``). As concluídas também formam o bitmap ``questSite``."""

    character_id: int
    template_id: int
    added_at: datetime
    id: int | None = None
    completed: bool = False
    progress: int = 0  # condition_1
    completed_at: datetime | None = None


class BagType(IntEnum):
    BAG = 1
    HERO = 4  # equipado; ``object_id`` = id do herói


@dataclass(eq=False)
class Item:
    character_id: int
    template_id: int
    id: int | None = None
    bag_type: int = BagType.BAG
    object_id: int = 0
    pos: int = 0
    count: int = 1
    random_skill: int = 0  # randomSkill_1 (atributo extra sorteado, ex. 70302 "Zeka+2")
    is_new: bool = True


@dataclass(eq=False)
class LoginHistory:
    """Uma entrada no portal (``source="portal"``, gravada pelo PHP) ou no jogo (``"game"``)."""

    account_id: int
    source: str
    ip: str
    created_at: datetime
    character_id: int | None = None
    user_agent: str | None = None
    id: int | None = None


@dataclass(eq=False)
class CashLedger:
    """Movimento de ``point``/``gift_token``: compras, pacotes, edições GM e recargas."""

    character_id: int
    delta_point: int
    delta_gift_token: int
    balance_point: int
    balance_gift_token: int
    reason: str
    ref: str
    created_at: datetime
    gm: str | None = None
    id: int | None = None


@dataclass(eq=False)
class ItemLog:
    character_id: int
    template_id: int
    count: int  # negativo = saiu da mochila
    action: str
    ref: str
    created_at: datetime
    id: int | None = None


@dataclass(frozen=True, slots=True)
class PlayerSnapshot:
    """Tudo que o login precisa de uma vez (carregado numa transação)."""

    account: Account
    server: GameServer
    character: Character
    heroes: list[Hero] = field(default_factory=list)
    castle: Castle | None = None
    buildings: list[Building] = field(default_factory=list)
    quests: list[Quest] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)

    @property
    def leader(self) -> Hero | None:
        return next((h for h in self.heroes if h.is_leader), None)
