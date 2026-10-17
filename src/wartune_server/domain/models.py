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
    space_x: int = 72  # tile na cidade do céu ao sair
    space_y: int = 74
    qte_guide: int = 0
    vice_password: str = ""  # sha256 da senha secundária; "" = sem senha
    vice_reset_at: datetime | None = None
    vehicle_exp: int = 0
    vehicle_score: int = 0
    vehicle_default: int = 1
    vehicles: str = "1"  # templateIds de VehicleObjectTempInfos possuídos, separados por vírgula
    last_login_at: datetime | None = None
    refuse_friend: bool = False  # PlayerMsg.refuseFriend: recusa pedidos de amizade (8285)
    bugle_free_used: int = 0  # cornetas pequenas grátis usadas em ``bugle_free_day``
    bugle_free_day: str = ""  # "YYYY-MM-DD"; outro dia = cota cheia de novo
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


@dataclass(eq=False)
class LoginHistory:
    """Uma entrada no portal (``source="portal"``, gravada pelo PHP) ou no jogo (``"game"``)."""

    account_id: int
    source: str
    ip: str
    created_at: datetime
    character_id: int | None = None
    user_agent: str | None = None


class RelationType(IntEnum):
    """``FriendRelationMsg.relation`` do lado de quem tem a linha."""

    FRIEND = 1  # amizade dos dois lados
    BLACKLIST = 2
    PENDING = 3  # eu adicionei, o outro ainda não me adicionou


@dataclass(eq=False)
class Relation:
    """Linha da lista de amigos de ``character_id`` apontando para ``other_id``."""

    character_id: int
    other_id: int
    relation: int
    id: int | None = None
    group_id: int = -1  # 2 = grupo padrão "amigos" do cliente; -1 pendente/lista negra


@dataclass(eq=False)
class FriendGroup:
    character_id: int
    group_id: int  # >= 3: 1, 2, -1 e -2 são do cliente
    name: str
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


@dataclass(eq=False)
class SnsProfile:
    """Perfil social (``SNSInfoMsg``): assinatura, aniversário, signo, local, avatar."""

    character_id: int
    id: int | None = None
    sign_desc: str = ""
    sex: int = 0
    birthday_type: int = 0
    birth_year: int = 0
    birth_month: int = 0
    birth_day: int = 0
    star_id: int = 0
    blood_type: int = 0
    country: int = 0
    province: int = 0
    city: int = 0
    head_id: int = 0


class MailType(IntEnum):
    """``EmailInfo.MailType``: 3 é relatório de batalha, 4 traz estrelas (outra mochila)."""

    PLAYER = 1
    SYSTEM = 2


@dataclass(eq=False)
class Mail:
    receiver_id: int
    sent_at: datetime
    title: str
    contents: str
    id: int | None = None
    sender_id: int = 0  # 0 = sistema
    sender_nick: str = ""
    sender_grades: int = 0
    mail_type: int = MailType.PLAYER
    send_type: int = 1  # EmailInfo.SendType: 1 jogador, 2 GM/sistema (ícone de GM)
    read_at: datetime | None = None
    validity_days: int = 30


@dataclass(eq=False)
class MailAnnex:
    """Anexo de correio por template (``AnnexN <= 0`` no cliente): TemplateId e quantidade."""

    mail_id: int
    slot: int  # 1..5 (AnnexN)
    template_id: int
    count: int
    id: int | None = None
    taken: bool = False


class MarriageState(IntEnum):
    """``MarriageMsg.state`` (MarryModel: isEngaged 1, isEnEngaged 2, isMarry 3, isDivorce 4)."""

    ENGAGED = 1
    ENGAGE_CANCELLED = 2
    MARRIED = 3
    DIVORCED = 4


@dataclass(eq=False)
class Marriage:
    """Situação de ``character_id`` com ``mate_id``; o casal tem duas linhas espelhadas."""

    character_id: int
    mate_id: int
    state: int
    since: datetime  # noivado
    id: int | None = None
    spec_id: int = 0  # MarrySpecTempInfo do casamento (0 = nenhum)
    married_at: datetime | None = None


@dataclass(eq=False)
class Arena:
    """Coliseu e torneio de fadas do personagem: contadores do dia, espera, pontos, formação.

    A posição no ranking do coliseu fica fora do snapshot (``ArenaRank``): ela muda quando outro
    jogador vence este, e a sessão dele gravaria por cima.
    """

    character_id: int
    id: int | None = None
    day: str = ""  # AAAA-MM-DD dos contadores; noutro dia eles zeram (4202)
    challenge_count: int = 0  # coliseu: tentativas usadas hoje (as além das grátis foram compradas)
    cool_until: datetime | None = None  # coliseu: espera depois de lutar
    win_streak: int = 0  # ChallengeInfoMsg.lastWinCount
    reward_day: str = ""  # dia em que a recompensa do coliseu foi resgatada
    pet_count: int = 0  # torneio de fadas: tentativas usadas hoje
    pet_buy_count: int = 0
    pet_cool_until: datetime | None = None
    pet_score: int = 1000  # pontos iniciais da captura
    pet_formation: str = ""  # chaPos: "petId,-1,..."
    pet_reward_day: str = ""  # dia da recompensa diária resgatada
    pet_reward_week: str = ""  # semana ISO (AAAA-Wnn) da recompensa semanal resgatada


@dataclass(eq=False)
class ArenaRank:
    """Posição única no coliseu (1 = primeiro). Só existe depois da primeira vitória."""

    character_id: int
    rank: int


@dataclass(eq=False)
class ChallengeLog:
    """Uma luta no histórico de quem atacou e de quem foi atacado (``ChallengeLogMsg``)."""

    character_id: int
    kind: int  # 0 coliseu, 1 torneio de fadas
    created_at: datetime
    target_id: int
    target_name: str
    is_attack: bool
    won: bool
    rank: int = 0  # coliseu: posição depois da luta; fadas: pontos ganhos/perdidos
    forward: int = 0  # coliseu: 0 posição igual, 1 subiu, 2 desceu (ChallengeLogMsg.forward)
    target_grades: int = 0
    target_job: int = 0
    id: int | None = None


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
    relations: list[Relation] = field(default_factory=list)
    groups: list[FriendGroup] = field(default_factory=list)
    sns: SnsProfile | None = None
    marriage: Marriage | None = None
    arena: Arena | None = None  # None até a primeira visita ao coliseu/torneio
    shop_buys: list[ShopBuy] = field(default_factory=list)
    fashions: list[FashionBook] = field(default_factory=list)
    mystery: list[MysteryShop] = field(default_factory=list)  # zero ou um

    @property
    def leader(self) -> Hero | None:
        return next((h for h in self.heroes if h.is_leader), None)
