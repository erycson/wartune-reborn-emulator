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
    bag_count: int = 0  # espaços comprados além dos 42 da mochila (5010), de 7 em 7
    rental_bag_until: datetime | None = None  # mochila alugada (8819): 217 espaços até esta data
    store_grade: int = 0  # nível do cristal (8484, PlayerMsg.storeGrade)
    store_gp: int = 0
    appell_id: int = 0  # título em uso

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
    hide_fashion: bool = False  # 5008: esconder a moda
    blood: int = 0  # reserva de HP das poções (SonType 209), SimpleHeroInfoMsg.blood
    blood_id: int = 0  # última poção usada (bloodId)


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
    STORE = 0  # bancada da forja/moda: o item vai para cá (5005) antes da operação
    BAG = 1
    RUNE = 2  # runas de batalha do herói (SonType 214)
    HONOR = 3  # medalha de honra do herói (MasterType 3)
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
    random_skill_2: int = 0
    random_skill_3: int = 0
    random_skill_4: int = 0
    random_skill_5: int = 0
    strengthen_grade: int = 0
    join_1: int = -1  # furos: -1 fechado, 0 aberto e vazio, >0 templateId da pedra
    join_2: int = -1
    join_3: int = -1
    join_4: int = -1
    is_locked: bool = False
    mould_grade: int = 0

    @property
    def random_skills(self) -> list[int]:
        return [self.random_skill, self.random_skill_2, self.random_skill_3, self.random_skill_4, self.random_skill_5]

    @random_skills.setter
    def random_skills(self, value: list[int]) -> None:
        v = (list(value) + [0] * 5)[:5]
        self.random_skill, self.random_skill_2, self.random_skill_3, self.random_skill_4, self.random_skill_5 = v

    @property
    def joins(self) -> list[int]:
        return [self.join_1, self.join_2, self.join_3, self.join_4]

    @joins.setter
    def joins(self, value: list[int]) -> None:
        self.join_1, self.join_2, self.join_3, self.join_4 = value


@dataclass(eq=False)
class CashLedger:
    """Movimento de moeda premium (``point``/``gift_token``) com o saldo depois dele.

    Gravado na mesma transação da compra (``services.cash``); só cresce, nunca é editado.
    """

    character_id: int
    delta_point: int
    delta_gift_token: int
    balance_point: int
    balance_gift_token: int
    reason: str  # 'shop', 'gm', 'recharge', 'forge', ...
    ref: str
    created_at: datetime
    gm: str | None = None
    id: int | None = None


@dataclass(eq=False)
class ShopBuy:
    """Quanto o personagem comprou de um ``ShopTempInfo`` no dia ``day`` (limite diário VIP0Count)."""

    character_id: int
    good_id: int
    day: str  # AAAA-MM-DD; outro dia = contagem zerada
    counts: int = 0
    id: int | None = None


@dataclass(eq=False)
class FashionBook:
    """Moda registrada no livro de moda (4542 ``FashionBook``)."""

    character_id: int
    template_id: int
    is_switch: bool = True
    appraisal_skill: int = 0
    id: int | None = None


@dataclass(eq=False)
class MysteryShop:
    """Loja misteriosa (ShopType 5) do personagem: os itens sorteados e as compras do dia."""

    character_id: int
    fresh_at: datetime
    goods: str = ""  # Ids de ShopTempInfo separados por vírgula
    bought: str = ""  # índices já comprados, separados por vírgula
    day: str = ""
    buy_count: int = 0
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
    shop_buys: list[ShopBuy] = field(default_factory=list)
    fashions: list[FashionBook] = field(default_factory=list)
    mystery: list[MysteryShop] = field(default_factory=list)  # zero ou um

    @property
    def leader(self) -> Hero | None:
        return next((h for h in self.heroes if h.is_leader), None)
