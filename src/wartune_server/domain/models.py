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
    # guilda: só o que o próprio jogador muda (a filiação fica em ``ConsortiaMember``)
    consortia_offer: int = 0  # contribuição disponível (gasta no mercado e nas habilidades)
    consortia_total_offer: int = 0
    skill_attack: int = 0  # habilidades aprendidas na guilda (tipos 6, 8-12 do ConsortiaLevelInfos)
    skill_agility: int = 0
    skill_ability: int = 0
    skill_captain: int = 0
    skill_gold: int = 0
    skill_physique: int = 0
    is_auto: bool = False  # saiu por conta própria: 24 h sem entrar em outra (PlayerMsg.isAuto)
    last_out_consortia: datetime | None = None

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
class Consortia:
    """Guilda (``ConsortiaInfoMsg``). Níveis por tipo do ``ConsortiaLevelInfos``."""

    server_id: int
    name: str
    creator_id: int
    creator_name: str
    chairman_id: int
    created_at: datetime
    id: int | None = None
    levels: int = 1  # tipo 1
    shop_level: int = 0  # 2
    altar_level: int = 0  # 3
    school_level: int = 0  # 4
    store_level: int = 0  # 5
    attack_level: int = 0  # 6..12: pesquisa das habilidades
    defence_level: int = 0
    agility_level: int = 0
    ability_level: int = 0
    captain_level: int = 0
    gold_level: int = 0
    physique_level: int = 0
    offer: int = 0  # riqueza (gasta nas melhorias)
    total_offer: int = 0
    placard: str = ""
    description: str = ""
    group_placard: str = ""
    open_app: bool = True
    code_type: int = 0  # tipo da última melhoria (o cliente conta a espera a partir de code_begin_at)
    code_need: int = 0  # segundos de espera
    code_begin_at: datetime | None = None
    kick_count: int = 0
    kick_at: datetime | None = None
    altar_state: int = 0
    altar_at: datetime | None = None
    max_wave: int = 0
    voting_state: int = 0
    voting_id: int = 0
    voting_at: datetime | None = None


@dataclass(eq=False)
class ConsortiaMember:
    """Filiação: 1 chefe, 2 vice, 3 ancião, 4 e 5 membros (``dutyId``)."""

    consortia_id: int
    character_id: int
    joined_at: datetime
    id: int | None = None
    duty_id: int = 5
    today_offer: int = 0
    offer_day: str = ""  # YYYY-MM-DD de ``today_offer``
    bless_count: int = 0
    bless_day: str = ""
    voted_for: int = 0  # eleição de chefe: em quem votou na eleição ``Consortia.voting_id``
    voted_id: int = 0


@dataclass(eq=False)
class ConsortiaInvite:
    """Candidatura (``from_type`` falso) ou convite da guilda para o jogador (verdadeiro)."""

    consortia_id: int
    user_id: int
    created_at: datetime
    id: int | None = None
    invite_id: int = 0  # quem convidou
    from_type: bool = False


@dataclass(eq=False)
class ConsortiaEvent:
    consortia_id: int
    created_at: datetime
    remark: str
    id: int | None = None
    type: int = 1


@dataclass(eq=False)
class ConsortiaItem:
    """Baú de prêmios da guilda (4466), distribuído pelo chefe (8578)."""

    consortia_id: int
    template_id: int
    id: int | None = None
    count: int = 1


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
