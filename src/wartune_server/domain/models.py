"""Entidades do domínio (sem dependência de banco ou rede).

Modelo multi-servidor: uma ``Account`` é global (login do portal) e pode ter um
``Character`` em cada ``GameServer`` (S1, S2...). Tudo que pertence ao jogo
(herói, castelo, itens...) pendura no personagem, nunca na conta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum

from . import gameday


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
    timezone: str = "UTC"  # fuso do jogo (Settings.game_timezone): o portal mostra na lista de servidores


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
    strategy: int = 0  # Daru, moeda -300
    crystals: int = 1000  # cristais (-600): custo das tecnologias; o oficial começa com 1000
    weary: int = 200
    weary_limit: int = 200
    novice_process: int = 0
    fighting_capacity: int = 0
    repute: int = 0
    geste: int = 0
    charm: int = 0
    space_x: int = 76  # tile na cidade do céu ao sair; o personagem novo nasce em 76,76 (tutorial_en #7, #2123)
    space_y: int = 76
    qte_guide: int = 0
    vice_password: str = ""  # sha256 da senha secundária; "" = sem senha
    vice_reset_at: datetime | None = None
    vehicle_exp: int = 0
    vehicle_score: int = 0
    vehicle_default: int = 1
    vehicles: str = "1"  # templateIds de VehicleObjectTempInfos possuídos, separados por vírgula
    last_login_at: datetime | None = None
    refuse_friend: bool = False  # PlayerMsg.refuseFriend: recusa pedidos de amizade (8285)
    refuse_invite: bool = False  # PlayerMsg.refuseInvite: recusa convites de guilda e de sala (8286)
    refuse_team_invite: bool = False  # PlayerMsg.refuseTeamInvite: recusa convites de time (8746)
    seminary_effect: int = 0  # PlayerMsg.blessingBuff: bênção do seminário, 0..200 (8489)
    seminary_count: int = 0  # bênçãos feitas em ``seminary_day`` (PlayerMsg.blessingCount, tarefa do dia)
    seminary_day: str = ""  # "YYYY-MM-DD"; outro dia zera a contagem
    bugle_free_used: int = 0  # cornetas pequenas grátis usadas em ``bugle_free_day``
    bugle_free_day: str = ""  # "YYYY-MM-DD"; outro dia = cota cheia de novo
    mall_spent: int = 0  # diamante pago no mercado (lances e preço fixo) em ``mall_day`` (limite diário, -52)
    mall_day: str = ""  # "YYYY-MM-DD"; outro dia zera
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
    # caixa por tempo (5019): último período recebido hoje e segundos online contados até ``box_counted_at``
    box_period: int = 0
    box_seconds: int = 0
    box_counted_at: datetime | None = None
    offline_at: datetime | None = None  # saída do jogo (recompensa offline)
    offline_seconds: int = 0  # tempo offline ainda não resgatado (8287)
    leave_gp: int = 0  # EXP descansada (PlayerMsg.leaveGp, "Rested EXP" da barra): o ganho de luta e missão gasta dela
    # campanha em grupo (4240): entradas que sobram e o máximo de ``multi_copy_day``; outro dia = o base
    multi_copy_count: int = 0  # PlayerMsg.campaignCount
    multi_copy_max: int = 0  # PlayerMsg.campaignMaxcount (base + The Empire Crusade usados no dia)
    multi_copy_day: str = ""  # "YYYY-MM-DD"
    reset_day: str = ""  # último dia do jogo já virado (energia, stamina): game/daily.py
    weary_potions: int = 0  # stamina tomada em poções no dia (PlayerMsg.wearyLimit; teto 300)
    # monstros dos Wilds abatidos no dia que contaram para o prêmio (MapBossMsg.count1-3; zera no daily.roll)
    kills_normal: int = 0
    kills_elite: int = 0
    kills_boss: int = 0

    @property
    def icon(self) -> int:
        """O cliente usa o mesmo número para ``pic``/``icon`` e ``job``."""
        return self.job

    def bless_count_today(self, now: datetime) -> int:
        """Bênçãos do seminário no dia (``PlayerMsg.blessingCount``, tarefa do dia). Outro dia = zero."""
        return self.seminary_count if self.seminary_day == gameday.today(now) else 0

    def multi_copies(self, base: int, now: datetime) -> tuple[int, int]:
        """(sobram, máximo) das entradas de campanha em grupo hoje. Outro dia volta ao ``base``
        (``MultiCampaign_MaxCount``): o item de +1 vale só no dia em que foi usado."""
        if self.multi_copy_day == gameday.today(now):
            return self.multi_copy_count, self.multi_copy_max
        return base, base


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
    hp: int = 0  # vida atual do líder; 0 = cheia (o máximo de agora). A reserva ``blood`` completa
    talent_grade: int = 0
    talent_script: str = ""  # talentSkill: templateIds de talento aprendidos
    runes: str = ""  # "runeId:gp:swallow,..." (HeroRuneInfoMsg)
    rune_key: str = ""  # runas equipadas, como o cliente lê: "204,-1,"
    skill_script2: str = ""  # segundo conjunto de skills (8479/8480)
    fast_key2: str = ""
    skill_index: int = 0  # conjunto em uso
    active_second: bool = False
    awake: int = 0  # despertar do mascote (0 a 3000); passa de uma luta para outra (visto peri_uyanis #50)


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
    # ouro produzido até este instante; None = produção ainda parada (antes do 8281 do tutorial)
    produced_at: datetime | None = None
    impose_used: int = 0  # cobranças de ouro (8327) feitas no dia de ``imposed_at``
    imposed_at: datetime | None = None
    farm_grade: int = 1
    farm_gp: int = 0  # EXP dentro do nível (UpGradeTempInfos tipo 17)
    land_grade: int = 1  # nível das terras (15044 op 9, até 10)
    tree_water: int = 0  # regas da árvore
    tree_fruit: int = 0
    tree_watered_at: datetime | None = None
    tree_picked_at: datetime | None = None
    mines_at: datetime | None = None  # começo do ciclo de 12 h das minas do mapa 100 (outer_city.cycle_start)
    # contadores do dia da fazenda (``farm.roll_day``; dia do jogo em ``farm_day``)
    farm_day: str = ""
    farm_friend_gp: int = 0  # EXP da fazenda vinda de amigos (teto Farm_TodayFromFriend_GP)
    farm_steals: int = 0  # roubos feitos (teto Farm_TodayStolen_Count)
    tree_water_today: int = 0  # regas da própria árvore (3 por dia)
    tree_friend_today: int = 0  # regas de árvores de amigos (200 por dia)


@dataclass(eq=False)
class BuildOrder:
    """Fila de construção (``OrderInfoMsg``): o upgrade é imediato, a ordem só fica ocupada até
    ``begin_at + need_time``. ``order_type``: 1 prédio, 2 tecnologia, 3 cobrança de ouro."""

    character_id: int
    order_id: int  # número da fila do jogador (1, 2...), não o id do banco
    order_type: int
    begin_at: datetime
    need_time: int = 0  # segundos
    id: int | None = None

    def remain(self, now: datetime) -> int:
        return max(0, int((self.begin_at - now).total_seconds()) + self.need_time)


@dataclass(eq=False)
class FarmLand:
    """Terra plantada (``FarmLandInfoMsg``). Terra vazia não tem linha. ``worm``/``grass``: qual
    das duas janelas (1 = 40%/30% do ciclo, 2 = 60%/50%) tem praga; 0 = já tirada."""

    character_id: int
    pos: int
    item_template_id: int
    planted_at: datetime
    mature_at: datetime
    reward_count: int = 0
    worm: int = 0
    grass: int = 0
    accelerated: bool = False
    stolen_by: str = ""  # ids de quem roubou, separados por vírgula (``FarmLandInfoMsg.stolenUsers``)
    id: int | None = None


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
    progress_2: int = 0  # condition_2: missões com mais de uma linha em QuestCondictionInfos
    progress_3: int = 0  # condition_3
    progress_4: int = 0  # condition_4
    completed_at: datetime | None = None


class BagType(IntEnum):
    STORE = 0  # bancada da forja/moda: o item vai para cá (5005) antes da operação
    BAG = 1
    RUNE = 2  # runas de batalha do herói (SonType 214)
    HONOR = 3  # medalha de honra do herói (MasterType 3)
    HERO = 4  # equipado; ``object_id`` = id do herói
    GUILD = 6  # armazém da guilda (``ConsortiaCaseBag``): itens do próprio jogador, espaços pelo ``storeLevel``
    MAIL = 10  # item anexado a um correio, esperando o 5022 (``BagType.mail`` do cliente)
    AUCTION = 11  # item à venda no mercado (``BagType.auction`` do cliente)
    BOTTLE = 22  # armazém da árvore dourada (8604) até tirar/vender; ``GoodsManager.isBottleBagGoods`` do cliente
    MAZE = 24  # prêmios do labirinto de gemas até o "receber tudo" (9517); ``BagType.Maze`` do cliente
    PET_EQUIP = 26  # equipamento vestido no mascote; ``object_id`` = id do mascote (``BagType.PetEquipment``)


# bolsas que não ficam no snapshot: o item só volta a ele quando é retirado (5022, cancelamento)
OUT_OF_SNAPSHOT = (BagType.MAIL, BagType.AUCTION)


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
    mould_grade: int = 0  # encantamento do equipamento de mascote (8644)
    bless_value: int = 0  # bênção do encantamento: soma na taxa, até 100 (PetEquipStrengView)
    # ItemInfoMsg.property1: no Sylph à venda (item -900) é o pet em ``PetData.createWidthString``
    property1: str = ""
    # vinculado (ItemInfoMsg.bind, tooltip "Bound"/"Unbound"): só o não vinculado vai ao leilão (Auction.ResultAlert7).
    # Nasce vinculado (a captura inglesa só tem bind true); a loja de Balens dá livre (handlers/shop.py)
    is_binds: bool = True
    # validade (ItemInfoMsg.validDate em minutos, beginDate): 0 = para sempre (cliente GoodsInfo.leftTime)
    valid_date: int = 0
    begin_date: datetime | None = None

    def expired(self, now: datetime) -> bool:
        """Venceu? Mesma conta do cliente (``BaseBagListView``: ``now - beginDate >= validDate`` minutos)."""
        return self.valid_date > 0 and self.begin_date is not None and now >= self.expires_at

    @property
    def expires_at(self) -> datetime:
        assert self.begin_date is not None
        return self.begin_date + timedelta(minutes=self.valid_date)

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
    friend_gp: int = 0  # amizade (``relationGp``); o grau sai de ``social.friend_grade``
    tree_day: str = ""  # dia do jogo em que ``character_id`` regou a árvore de ``other_id`` (uma por dia)


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
class Purchase:
    """Uma compra: o que o jogador levou (``template_id``) e o que pagou, no preço do momento. ``good_id`` é a
    linha de ``ShopTempInfos`` (loja) ou o anúncio (mercado); ``currency`` é a coluna de preço (``Point``,
    ``GiftToken``, ``Gold``, moeda-item...)."""

    character_id: int
    source: str
    good_id: int
    template_id: int
    count: int
    currency: str
    price: int
    created_at: datetime
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
    BATTLE_REPORT = 3


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
    item_id: int = 0  # item de verdade (linha de ``Item`` na bolsa MAIL) em vez de template; 0 = nenhum


@dataclass(eq=False)
class MallListing:
    """Item à venda no mercado (8448). O item fica na bolsa AUCTION do vendedor até sair; ``point`` é o
    lance inicial ou o último lance; ``fix_point`` 0 = sem compra imediata; ``bidder_id`` 0 = sem lance."""

    server_id: int
    seller_id: int
    item_id: int
    seller_nick: str
    point: int
    fix_point: int
    hour: int
    started_at: datetime
    ends_at: datetime
    bidder_id: int = 0
    id: int | None = None


@dataclass(eq=False)
class MallBid:
    """Lances de um jogador num anúncio aberto (8452). Um por (anúncio, jogador): o último lance."""

    listing_id: int
    bidder_id: int
    price: int
    bid_at: datetime
    id: int | None = None


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
    tree: str = ""  # árvore do casal em JSON, igual nas duas linhas (``game/marriage_tree.py``)


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
    pet_score: int = 1000  # pontos iniciais (só turco: captura do torneio de fadas, peri_turnuvasi)
    pet_formation: str = ""  # chaPos: "petId,-1,..."
    pet_reward_day: str = ""  # dia da recompensa diária resgatada
    pet_reward_week: str = ""  # semana ISO (AAAA-Wnn) da recompensa semanal resgatada
    attack_left: int = 5  # PlayerMsg.attackLeftCount: ataques da cidade externa; zera com o dia (4202)


@dataclass(eq=False)
class ArenaRank:
    """Posição única no coliseu (1 = primeiro). Só existe depois da primeira vitória."""

    character_id: int
    rank: int


@dataclass(eq=False)
class TreasureMap:
    """Mapa do tesouro do personagem: mapas recebidos no dia (``join_tremap_count``) e escavações."""

    character_id: int
    id: int | None = None
    day: str = ""  # AAAA-MM-DD da contagem de mapas recebidos; noutro dia zera
    join_count: int = 0  # mapas recebidos hoje (8744 op 1)
    reward_count: int = 0  # escavações concluídas hoje; o servidor não escava, então fica em 0


@dataclass(eq=False)
class WildLand:
    """Mina de ouro (``WildLandMsg`` type 20) que o personagem ocupou (5160): do mapa do castelo ou do mundo."""

    character_id: int
    wild_id: int  # world_mines.id ou a gerada (``mines.world_mines_in``)
    occupied_at: datetime
    id: int | None = None
    template_id: int = 0  # nível sorteado no ciclo da ocupação (MapPhysicsTempInfos)
    pos_x: int = 0
    pos_y: int = 0
    map_id: int = 100  # BASE_MAP; 1 a 5 = mapa do mundo
    cycle_at: datetime | None = None  # começo do ciclo do mundo (só nos mapas 1 a 5)
    capacity: int = 0  # poder de quem ocupou, para o 4129 dos outros


@dataclass(eq=False)
class WildMonsterKill:
    """Monstro dos Wilds abatido no ciclo (``game/monsters.py``): some do mapa para todos até o refresh."""

    map_id: int
    monster_id: int
    cycle_at: datetime
    character_id: int
    killed_at: datetime


@dataclass
class TreasureCacheOpen:
    """Treasure Cache aberto (``game/caches.py``): some do mapa para todos até a próxima vida dele."""

    map_id: int
    cache_id: int
    born_at: datetime
    character_id: int
    opened_at: datetime


@dataclass(eq=False)
class WildBox:
    """Baú que o monstro dos Wilds deixou no mapa para quem o matou (4940), até ser aberto (9526). O que tem
    dentro é sorteado ao abrir, pela tabela ``world_monster_drops``."""

    character_id: int
    map_id: int
    pos_x: int
    pos_y: int
    boss_type: int  # 1 normal, 2 elite, 3 BOSS: também o desenho (BossBoxMc<type>)
    grade: int  # nível do monstro
    created_at: datetime
    id: int | None = None  # ArmyBoxMsg.boxId (como texto)


@dataclass(eq=False)
class WorldBossFight:
    """Uma janela de um chefe do mundo: vida cheia, quem deu o último golpe e se o fim já foi pago. A vida
    atual é ``total_hp`` menos a soma dos danos (``WorldBossWound``), então um restart só perde a luta em curso."""

    campaign_id: int
    opened_at: datetime
    total_hp: int
    id: int | None = None
    killer_id: int = 0
    killed_at: datetime | None = None
    settled: bool = False
    next_hp: int = 0  # vida cheia da próxima janela, decidida no fim desta


@dataclass(eq=False)
class WorldBossWound:
    """Dano somado de um jogador numa janela (o ranking e os prêmios saem daqui)."""

    fight_id: int
    character_id: int
    nickname: str
    job: int
    wound: int = 0
    id: int | None = None


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
    forward: int = 0  # coliseu: 0 posição igual, 1 subiu, -1 desceu (ChallengeLogMsg.forward)
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
    # árvore da terra secreta (game/fam.py): nível, EXP, energia da invocação e a hora da invocação (pickTime)
    tree_grade: int = 1
    tree_gp: int = 0
    tree_power: int = 0
    tree_called_at: datetime | None = None
    max_wave: int = 0
    voting_state: int = 0
    voting_id: int = 0
    voting_at: datetime | None = None
    speak_day: str = ""  # YYYY-MM-DD do dia do jogo de ``speak_count`` (anúncios de recrutamento, 8335)
    speak_count: int = 0


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
    bless_item: int = 0  # prêmio da bênção por pegar (8216); 0 = nenhum
    bless_item_count: int = 0
    voted_for: int = 0  # eleição de chefe: em quem votou na eleição ``Consortia.voting_id``
    voted_id: int = 0
    # terra secreta: a invocação (``Consortia.tree_called_at``) em que energizou e em que comprou o buff (8566)
    fam_power_at: datetime | None = None
    fam_buff_at: datetime | None = None


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


@dataclass(eq=False)
class EventState:
    """Contador/marca de evento do personagem (``key`` única por personagem, ex. ``sign``,
    ``leed:16``, ``sum:<activeId>:<packageId>``). ``updated_at`` decide os zerados diários."""

    character_id: int
    key: str
    updated_at: datetime
    id: int | None = None
    value: int = 0
    text: str = ""


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
    # PetInfoMsg.isBind: só o livre vai ao leilão. ponytail: nasce vinculado; o selo livre dar mascote livre não
    # está escrito no cliente
    is_bind: bool = True
    cha_skills: str = "-1,-1,-1"  # PetInfoMsg.chaSkillIndexs: skills do torneio (8726)
    held: bool = False  # no leilão ou no correio (item -900): fora da lista até alguém pegar (5022) ou cancelar
    quality_gp: int = 0  # PetInfoMsg.curQualityGp: a barra de bênção do avanço (8621 op 4) dentro da estrela


@dataclass(eq=False)
class PlayerSystems:
    """Estado de uma linha por personagem dos sistemas do herói (criada na primeira vez que é usada)."""

    character_id: int
    id: int | None = None
    mount_template: int = 0  # montaria em uso (0 = nenhuma)
    mount_gp: str = "0,0,0,0"  # EXP de força, inteligência, físico, agilidade
    mount_avatars: str = ""  # montarias possuídas: "1000,1103"
    mount_expiry: str = ""  # as temporárias (carta com Property2 dias): "1107:<fim em segundos Unix>"
    mount_fly: str = ""  # voo comprado com Flystone (op 13, AvatarInfoMsg.isBuyFly): "1001,1002"
    mount_stars: str = ""  # estrela e bênção de cada montaria (op 6, AvatarInfoMsg.starLevel/blessing): "1000:2:30"
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
    # PlayerMsg.lastFreeSkillLearnTime: o último aprendizado aleatório grátis de skill de pet (8621 op 5)
    pet_free_skill_at: datetime | None = None


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
    orders: list[BuildOrder] = field(default_factory=list)
    lands: list[FarmLand] = field(default_factory=list)
    events: list[EventState] = field(default_factory=list)
    pawns: list[Pawn] = field(default_factory=list)
    stars: list[Star] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)
    systems: PlayerSystems | None = None  # o serviço cria em memória quando não existe
    treasure: list[TreasureMap] = field(default_factory=list)  # zero ou um: mapa do tesouro (8744)
    wild_lands: list[WildLand] = field(default_factory=list)  # minas de ouro ocupadas (5160)
    wild_boxes: list[WildBox] = field(default_factory=list)  # baús dos monstros dos Wilds ainda fechados

    @property
    def leader(self) -> Hero | None:
        return next((h for h in self.heroes if h.is_leader), None)
