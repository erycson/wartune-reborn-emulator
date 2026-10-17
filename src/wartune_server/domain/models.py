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
    talent_grade: int = 0
    talent_script: str = ""  # talentSkill: templateIds de talento aprendidos
    runes: str = ""  # "runeId:gp:swallow,..." (HeroRuneInfoMsg)
    rune_key: str = ""  # runas equipadas, como o cliente lê: "204,-1,"
    skill_script2: str = ""  # segundo conjunto de skills (8479/8480)
    fast_key2: str = ""
    skill_index: int = 0  # conjunto em uso
    active_second: bool = False


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
class Pawn:
    """Tropa (``ArmyPawnInfoMsg``): uma linha por tipo (SonType), no castelo e/ou no exército.

    O exército tem um único slot (``sites`` 0); ``army_count`` > 0 diz que este tipo está nele.
    """

    character_id: int
    template_id: int  # muda a cada evolução (NextLevelTemplateId)
    id: int | None = None
    castle_count: int = 0
    army_count: int = 0
    specials: str = ""  # specialTempIds (especialidade salva)
    comprehend: str = ""  # comprehednTempIds (sorteada no 8455, ainda não salva)
    bless: int = 0
    fight_pos: int = 3  # posição na formação (8276); o oficial manda 3 por padrão


class StarBag(IntEnum):
    TEMP = 0  # sorteadas, ainda não recolhidas
    BAG = 1
    EQUIP = 2


@dataclass(eq=False)
class Star:
    """Estrela (``StarInfoMsg``)."""

    character_id: int
    template_id: int
    id: int | None = None
    bag_type: int = StarBag.TEMP
    pos: int = 0
    grade: int = 1
    gp: int = 0
    locked: bool = False


@dataclass(eq=False)
class Pet:
    """Pet (``PetInfoMsg``). Atributos derivados vêm do template + nível; aqui só o que muda."""

    character_id: int
    template_id: int
    name: str
    id: int | None = None
    grade: int = 1
    gp: int = 0
    power: int = 0  # pontos distribuídos
    intel: int = 0
    physi: int = 0
    armor: int = 0
    power_apti: int = 0
    intel_apti: int = 0
    physi_apti: int = 0
    armor_apti: int = 0
    growth_rate: int = 0
    quality: int = 0
    is_fight: bool = False
    follow_skills: str = ""
    change_skills: str = ""
    fast_key: str = ""
    pos: int = 0  # ordem na lista (14 = mover para o topo)


@dataclass(eq=False)
class PlayerSystems:
    """Estado de uma linha por personagem dos sistemas do herói (criada na primeira vez que é usada)."""

    character_id: int
    id: int | None = None
    mount_template: int = 0  # montaria em uso (0 = nenhuma)
    mount_gp: str = "0,0,0,0"  # EXP de força, inteligência, físico, agilidade
    mount_avatars: str = ""  # montarias possuídas: "1000,1103"
    dragon_type: int = 0  # 101 alma do dragão, 102 depois da transferência
    dragon_grade: int = 0
    dragon_gp: int = 0
    fate: str = ""  # destino: "sonType:gp,..."
    fate_turns: int = 0  # giros da roda no dia ``fate_day``
    fate_day: str = ""
    star_sites: str = "1,0,0,0,0"  # cristais abertos para sortear estrelas
    star_bag: int = 0  # espaços comprados na mochila de estrelas
    star_point: int = 0  # moeda da loja de estrelas (PlayerMsg.starpoint)
    star_free: int = 1  # sorteios grátis do dia (PlayerMsg.startFree)
    star_day: str = ""
    powcards: str = ""  # cartas: "tempId:grade:gp,..."
    pet_slots: int = 0  # limites de pet comprados


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
    pawns: list[Pawn] = field(default_factory=list)
    stars: list[Star] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)
    systems: PlayerSystems | None = None  # o serviço cria em memória quando não existe

    @property
    def leader(self) -> Hero | None:
        return next((h for h in self.heroes if h.is_leader), None)
