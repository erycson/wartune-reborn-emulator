"""Pets (``PlayerPetOpMsg`` 8621, ficha de outro jogador 8702).

Fonte: só turco, login.json #30 (4540 com um pet completo, ``petCount`` 6) e ``ConfigInfos`` (pet_reset_att,
add_pet_count). O 4540 é incremental: só os pets que mudaram (``isDel`` apaga).
Composição de um pet (13, cliente ``PetSocketOut.composePet``): receitas de ``PetComponseInfos``. Avanço (4),
aprender skill (5) e encantar aptidão (7): telas m14 ``PetAdvancedView``, ``PetLearnSkillView`` e
``PetStrengthenView`` do cliente inglês.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from ...domain.models import BagType, Item, Pet, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates, Row
from .. import bag, rules
from ..builders.login import complete
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import _army, _player, snapshot_of
from .shop import send
from .vip import vip_right

S_PETS, S_OTHER_PETS, S_ITEMS, S_FARM_LAND = 4540, 4608, 115, 4387
ADD_POINTS, RESET_POINTS, FIGHT, REST, FAST_KEY, MORE_SLOTS, TO_TOP = 2, 3, 9, 10, 11, 12, 14
COMPOSE = 13  # composePet: receita de um pet só (PetComponseInfos com Pet2Types 0)
SWALLOW, SACRIFICE = 1, 6  # PetSocketOut.swallowPet (value = o secundário) e sacrifice
PET_GRADE = "25"  # UpGradeTempInfo.Types do nível do mascote (PetData.upgradeTemplates); Data = EXP do nível anterior
HALF, FULL_BALENS, FULL_ANY, FULL_STONE = -1, 1, 2, 3  # payType do devorar (PetSwallowView.getPayType)
HERITAGE_STONE, SEPULCRUM = 208029, 3040001  # 100% de EXP sem Balens; o que o sacrifício dá (Sylph Sepulcrum)
# PetListView inglês: compradas = petMaxCount - 6; teto PetData.petCarryLimit 12 (sem pet_maxCount nos templates)
BASE_SLOTS, MAX_SLOTS = 6, 12
POINTS_PER_GRADE = 5  # PetData: remainPoint = (grade - 1) * 5 - pontos gastos
GROWTH_DIV = 80  # PetData.growWithGrade = growthRate / 80
ATTRS = ("power", "intel", "physi", "armor")
TPL_ATTRS = ("Power", "Intel", "Physi", "Armor")
RESISTS = ("fire", "water", "elect", "wind", "dark", "light")

ADVANCE, LEARN, ENCHANT, RESIST = (
    4,
    5,
    7,
    8,
)  # trainGrowthRate (o avanço de qualidade), learnSkill, trainCoe, trainResistance
MAX_UNITS = 9999  # PetAdvancedView / PetStrengthenView: a caixa de quantidade vai de 1 a 9999
# PetData.qualityUpgradeTemplates pelo NeedGrade: tabela da bênção, item (Mahra, Adv. Mahra) e o preço sem item
ADVANCE_RULES = {
    1: ("27", 208023, "pet_up_quality"),
    2: ("29", 208023, "pet_up_quality"),
    3: ("107", 208045, "pet_up_qualityupgrade"),
}
ADVANCE_GP, BLESSING = 10, 5  # PetAdvancedView: 10 de EXP por unidade; a bênção do Sylph dá 5x ("EXP x5")
BLESSING_CHANCE = 10  # ponytail: a chance da bênção não está no cliente; 10% até haver captura
ADV_SEPULCRUM = 3040002  # PetStrengthenView: o NeedGrade 3 gasta o Adv. Sepulcrum; os outros, o Sylph Sepulcrum
# ponytail: quanto um Sepulcrum dá na aptidão não está no cliente ("Randomly improves one aptitude that is not maxed")
ENCHANT_GAIN = (1, 10)
LEARN_BOOK, LEARN_RANDOM = 1, 2  # PlayerPetOpMsg.value do learnSkill
SKILL_BOOK = "303"  # ItemTempInfos.SonType do livro de skill de pet: Property1 = a skill
SKILL_SHOP_AREA = "7"  # ShopTempInfos.Area dos livros (ShopModel.petSkillBookDic)
ANY_PET = "107"  # SkillTempInfo.MasterType das skills de qualquer tipo de pet
ACTIVE, PASSIVE = "1", "2"  # SkillTempInfo.UseWay
SKILL_SLOTS = {ACTIVE: 5, PASSIVE: 3}  # PetData.activeSkillIsFull (>= 5) e passiveSkillIsFull (>= 3)
FAST_SLOTS = 5  # fastKey: 5 SonTypes das ativas ("-1" = vazio), cada um seguido de vírgula
VIP_SKILL_WAIT = 205  # VipPrerogativeTempInfo: minutos a menos na espera do aleatório grátis
COMPOSE_GRADE = 60  # PetComposeView.checkCanComposeAndTip: "Requires Character Level 60 or above to refine"
APT_FIELDS = tuple(f"{a}Apt" for a in TPL_ATTRS)  # PetTempInfo.PowerApt...: "mín,máx"


def tier(star: int) -> int:
    """``PetData.tempToQuality``: a cor (1-6) da estrela ``star`` (1-31)."""
    return (star - 1) // 5 + (1 if star < 26 else 0)


def tier_star(star: int) -> int:
    """``PetData.tempToStar``: a estrela dentro da cor (1-5; na cor 5, 1-10)."""
    return (star % 5 or 5) if star < 21 else (star % 10 or 10)


def pet_star(pet: Pet, tpl: Row) -> int:
    """Estrela do pet (``PetInfoMsg.quality``, 1-31). Sem estrela gravada, a primeira da cor do template."""
    color = int(tpl.get("Quality") or 1)
    return pet.quality or (31 if color >= 6 else (color - 1) * 5 + 1)


def coe_limit(templates: GameTemplates, tpl: Row, star: int, field: str) -> int:
    """``PetData.calculateCoeLimit``: o teto de ``field`` na estrela: o do template da cor, mais a fração até o da
    cor seguinte pela estrela dentro da cor (10 passos na cor 5, 5 nas outras). Aptidão: o máximo de "mín,máx"."""
    color = tier(star)
    a = templates.get("PetTempInfos", int(tpl["TemplateId"]) + color - int(tpl.get("Quality") or 1))
    if a is None:
        return 0
    b = templates.get("PetTempInfos", int(a["TemplateId"]) + 1)

    def value(row: Row) -> int:
        return int((row.get(field) or "0").split(",")[-1])

    if b is None:
        return value(a)
    return value(a) + int((value(b) - value(a)) / (10 if color == 5 else 5)) * (tier_star(star) - 1)


def remain_points(pet: Pet) -> int:
    return POINTS_PER_GRADE * (pet.grade - 1) - (pet.power + pet.intel + pet.physi + pet.armor)


def _floor(steps: list[tuple[int, int]], grade: int) -> int:
    return next((need for g, need in steps if g == grade), 0)


def cur_gp(pet: Pet, templates: GameTemplates) -> int:
    """EXP dentro do nível (``PetData.curExp``); ``pet.gp`` guarda a total (``totalExp``)."""
    return max(0, pet.gp - _floor(rules.grade_steps(templates, PET_GRADE), pet.grade))


def full_exp(pet: Pet, templates: GameTemplates, hero_grade: int) -> bool:
    """``PetData.isFullExp``: no último nível, acima do herói, ou no nível do herói com a EXP do próximo cheia."""
    steps = rules.grade_steps(templates, PET_GRADE)
    nxt = _floor(steps, pet.grade + 1) - _floor(steps, pet.grade)
    return (
        not steps
        or pet.grade >= steps[-1][0]
        or pet.grade > hero_grade
        or (pet.grade == hero_grade and cur_gp(pet, templates) >= nxt)
    )


def share_gp(s: GameSession, gp: int) -> Pet | None:
    """O mascote em batalha ganha a mesma EXP do herói nas lutas e missões (só turco: peri_uyanis #78 e meydan_okuma
    #26, petGpBonus = gpBonus; a missão manda o 4540 depois do 3, transfer_kampi #21, peri_turnuvasi #65, e o quanto
    é dedução). Devolve o mascote para quem chama gravar e mandar com ``send_gained``."""
    snap = s.snapshot
    assert snap is not None
    pet = next((p for p in snap.pets if p.is_fight), None) if gp > 0 else None
    if pet is not None:
        add_pet_gp(pet, s.ctx.templates, gp, snap.character.grades)
    return pet


def guard_msg(snap: PlayerSnapshot, templates: GameTemplates) -> pb.FarmPetInfoMsg | None:
    """O guarda da fazenda (``FarmInfo.defender``) é o mascote em batalha: (dedução) o cliente não tem tela para o
    PET_DEFENSE (FarmOperateType 16, nenhum ``sendFarmOper`` com ele) e em todas as turcas o guarda é o mascote em
    batalha (login #49 e os 4387 depois do 4540); o inglês, sem mascote em batalha, não manda guarda."""
    pet = next((p for p in snap.pets if p.is_fight), None)
    if pet is None:
        return None
    tpl = templates.get("PetTempInfos", pet.template_id) or {}
    return pb.FarmPetInfoMsg(
        userId=snap.character.id or 0, petId=pet.id or 0, petTemplateId=pet.template_id, petName=pet.name,
        quality=pet_star(pet, tpl),
    )  # fmt: skip


def send_gained(s: GameSession, *pets: Pet) -> None:
    """Depois da luta ou da EXP do mascote: 4540, 4387 com o guarda (``pos`` 0) e o 150, com o 4902 na frente (só
    turco: transfer_kampi #21-#25, meydan_okuma #22-#25, peri_turnuvasi #48-#51 e #65-#68, peri_uyanis #73-#77)."""
    snap = s.snapshot
    assert snap is not None
    s.send(S_PETS, pets_msg(snap, s.ctx.templates, list(pets)))
    guard = guard_msg(snap, s.ctx.templates)
    if guard is not None:
        guard.pos = 0
        s.send(S_FARM_LAND, pb.FarmInfoRspMsg(userId=s.player_id, guardPetInfo=guard))
    _army(s)


def add_pet_gp(pet: Pet, templates: GameTemplates, gp: int, hero_grade: int) -> None:
    """Soma EXP total; o nível não passa do herói ("A Sylph cannot exceed player's level") nem do último da tabela,
    e no teto a EXP para no que falta para o próximo nível (como o ``getAfterSwallowGrade``)."""
    steps = rules.grade_steps(templates, PET_GRADE)
    top = min(hero_grade, steps[-1][0]) if steps else pet.grade
    pet.gp += gp
    for g, need in steps:
        if g > top or pet.gp < need:
            break
        pet.grade = max(pet.grade, g)
    pet.gp = min(pet.gp, _floor(steps, top + 1) or _floor(steps, top))


def pet_info(pet: Pet, templates: GameTemplates, equip: Sequence[Item] = ()) -> pb.PetInfoMsg:
    tpl = templates.get("PetTempInfos", pet.template_id) or {}
    msg = pb.PetInfoMsg(
        petId=pet.id or 0,
        templateId=pet.template_id,
        petName=pet.name,
        curGp=cur_gp(pet, templates),
        curGrade=pet.grade,
        remainPoints=remain_points(pet),
        growthRate=pet.growth_rate,
        followSkills=pet.follow_skills,
        changeSkills=pet.change_skills,
        isFight=pet.is_fight,
        isBind=pet.is_bind,
        totalGp=pet.gp,
        quality=pet_star(pet, tpl),
        curQualityGp=pet.quality_gp,
        chaSkillIndexs=pet.cha_skills,
        fastKey=pet.fast_key,
        initQuality=int(tpl.get("Quality", 1)),
    )
    growth = (pet.grade - 1) * pet.growth_rate // GROWTH_DIV
    for attr, col in zip(ATTRS, TPL_ATTRS, strict=True):
        apti = getattr(pet, f"{attr}_apti")
        # PetData inglês (strengthBase...): template + floor((grade-1) x growthRate/80), mais os pontos
        setattr(msg, attr, int(tpl.get(col, 0)) + growth + getattr(pet, attr))
        name = attr.capitalize()
        for prefix in ("init", "", "next"):
            setattr(msg, f"{prefix}{name}Apti" if prefix else f"{attr}Apti", apti)
    for name, value in rules.pet_equipment(equip, templates).items():
        setattr(msg, name, value)
    # PetData.hp = MaxHp + floor(6 × stamina × coe / 1000) + equipHp (o bagLiving)
    msg.maxHp = int(tpl.get("MaxHp", 0)) + 6 * msg.physi * pet.physi_apti // 1000 + msg.bagLiving
    for r in RESISTS:
        setattr(msg, f"{r}Resi", int(tpl.get(f"{r.capitalize()}Resi", 0)))
    return complete(msg)


def pets_msg(snap: PlayerSnapshot, templates: GameTemplates, pets: list[Pet] | None = None) -> pb.PlayerPetMsg:
    c = snap.character
    msg = pb.PlayerPetMsg(userId=c.id, nickName=c.nickname or "", petCount=BASE_SLOTS + rules.systems(snap).pet_slots)
    for pet in sorted(snap.pets if pets is None else pets, key=lambda p: p.pos):
        msg.petInfo.append(pet_info(pet, templates, pet_items(snap, pet)))
    return msg


def pet_items(snap: PlayerSnapshot, pet: Pet) -> list[Item]:
    """Peças vestidas no mascote (bolsa 26, ``object_id`` = id do mascote)."""
    return [i for i in snap.items if i.bag_type == BagType.PET_EQUIP and i.object_id == pet.id]


def pet_string(pet: Pet, templates: GameTemplates) -> str:
    """O pet no ``property1`` do Sylph à venda, como o ``PetData.createWidthString`` lê: template, qualidade,
    EXP de qualidade, (sem uso), nível, EXP do nível, EXP total, qualidade inicial | aptidões e atributos |
    resistências | skills seguidoras | skills de batalha."""
    m = pet_info(pet, templates)
    head = (m.templateId, m.quality, m.curQualityGp, 0, m.curGrade, m.curGp, m.totalGp, m.initQuality)
    stats = [getattr(m, f"{a}Apti") for a in ATTRS] + [getattr(m, a) for a in ATTRS]
    resists = [getattr(m, f"{r}Resi") for r in RESISTS]
    return "|".join([*(",".join(map(str, part)) for part in (head, stats, resists)), m.followSkills, m.changeSkills])


def roster_full(snap: PlayerSnapshot) -> bool:
    """Sem vaga na lista (``petCount``): "You cannot accept the Sylph if your roster is full" (auctionFrame.helpPet)."""
    return len(snap.pets) >= BASE_SLOTS + rules.systems(snap).pet_slots


def take_back(snap: PlayerSnapshot, pet: Pet) -> None:
    """O Sylph do leilão entra na lista de ``snap`` (cancelou o anúncio ou pegou do correio), no fim da fila."""
    pet.character_id, pet.held = snap.character.id or 0, False
    pet.pos = max((p.pos for p in snap.pets), default=-1) + 1
    snap.pets.append(pet)


def _in_arena(snap: PlayerSnapshot, pet: Pet) -> bool:
    """Na equipe do Sylph Arena (``chaPos``): "cannot be engulfed/sacrificed while in a Sylph Arena party"."""
    return snap.arena is not None and str(pet.id) in snap.arena.pet_formation.split(",")


def sepulcrum(quality: int) -> tuple[int, int]:
    """Faixa de Sepulcrum do sacrifício pela estrela do cliente (``PetShowView.getSacrificeTip``; a estrela é
    ``(Quality - 1) / 5 + 1`` abaixo de 26, como o ``PetData``)."""
    star = (quality - 1) // 5 + (1 if quality < 26 else 0)
    if star <= 1:
        return 1, 1
    if star == 2:
        return 2, 3
    k = 10 ** (star - 3)
    return 16 * k, 20 * k


def pet_template_id(pet_type: int, tier: int, star: int) -> int:
    """Template de um pet: tipo, tier (``NeedGrade``) e estrela (``Quality``). 104101 = Pan, tier 1, estrela 1."""
    return pet_type * 1000 + tier * 100 + star


# ponytail: família (tipo, NeedGrade, cor) = template: é a leitura que fecha os 24 pares de receita com um
# template existente; confirmar com captura de uma composição. (O PetController.canComposePet do NeedGrade 50 não tem
# chamador: a trava de verdade é a do PetComposeView, ``can_compose``.)
def can_compose(tpl: Row, hero_grade: int) -> bool:
    """``PetComposeView.checkCanComposeAndTip``: herói nível 60; NeedGrade 1 de cor roxa (4) ou laranja (5), NeedGrade
    2 só laranja ("Only [{0}] of orange quality can be refined"); NeedGrade 3 e o legado 50 não ("High-ranked sylphs
    cannot be refined")."""
    need, color = int(tpl.get("NeedGrade") or 0), int(tpl.get("Quality") or 0)
    return hero_grade >= COMPOSE_GRADE and ((need == 1 and color >= 4) or (need == 2 and color == 5))


def compose_recipe(templates: GameTemplates, pet: Pet) -> tuple[Row, int] | None:
    """Receita de um pet só (``PetComponseInfos``, Pet2Types 0) para o template do pet, e o template que sai.
    ``None`` se não há receita, se ela pede diamante (só as de 2 pets pedem) ou se o pet resultante não tem
    template em ``PetTempInfos``: os tipos 117-119 não têm, então as receitas 19, 26, 29 e 32 ficam de fora."""
    tpl = templates.get("PetTempInfos", pet.template_id)
    if tpl is None:
        return None
    key = (int(tpl["PetType"]), int(tpl["NeedGrade"]), int(tpl["Quality"]))
    recipe = next(
        (
            r
            for r in templates.rows("PetComponseInfos")
            if int(r["Pet2Types"]) == 0
            and int(r["NeedPoint"]) == 0
            and (int(r["Pet1Types"]), int(r["Pet1Grade"]), int(r["Pet1Quality"])) == key
        ),
        None,
    )
    if recipe is None:
        return None
    result = pet_template_id(int(recipe["ResultPetTypes"]), int(recipe["ResultPetGrade"]), int(recipe["ResultQuality"]))
    return (recipe, result) if templates.get("PetTempInfos", result) is not None else None


async def _swallow(
    s: GameSession, snap: PlayerSnapshot, templates: GameTemplates, pet: Pet, msg: pb.PlayerPetOpMsg
) -> None:
    """swallowPet (1): o principal ``petId`` ganha a EXP total do secundário ``value``: metade (payType -1) ou toda
    (1 Balens ``swallow_fullgp_points``, 2 vinculado primeiro, 3 uma Heritage Stone). O secundário some (``isDel``)
    e o principal fica vinculado (showConfirmFrameContent2). Recusas do ``PetSwallowView``: secundário em batalha,
    com equipamento, na equipe do Sylph Arena, principal com a EXP cheia ou nada a ganhar."""
    c = snap.character
    second = next((p for p in snap.pets if p.id == msg.value and p is not pet), None)
    full = msg.payType in (FULL_BALENS, FULL_ANY, FULL_STONE)
    gain = (second.gp if full else second.gp // 2) if second else 0
    if (
        second is None
        or second.is_fight
        or pet_items(snap, second)
        or _in_arena(snap, second)
        or full_exp(pet, templates, c.grades)
        or gain <= 0
        or (msg.payType == FULL_STONE and bag.count_of(snap, HERITAGE_STONE) < 1)
    ):
        s.log.info("8621 devorar recusado", pedido=str(msg))
        return
    spent = None
    if msg.payType in (FULL_BALENS, FULL_ANY):
        cost = int(rules.config(templates, "swallow_fullgp_points", "50"))
        now = s.ctx.clock.now()
        spent = ledger.pay(c, cost, bind=msg.payType == FULL_ANY, reason="pet_swallow", ref=str(pet.id), now=now)
        if spent is None:
            s.log.info("8621 devorar recusado: sem Balens", pedido=str(msg), custo=cost)
            return
    changed, gone = bag.take(snap, HERITAGE_STONE, 1) if msg.payType == FULL_STONE else ([], [])
    add_pet_gp(pet, templates, gain, c.grades)
    pet.is_bind = True
    snap.pets.remove(second)
    await s.ctx.characters.save(pet, *changed, *([c, spent] if spent else []), delete=(second, *gone))

    out = pets_msg(snap, templates, [pet])
    out.petInfo.add(petId=second.id or 0, isDel=True)
    s.send(S_PETS, out)
    if changed or gone:
        send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
        castle_yield(s)
    if spent:
        _player(s)


async def _sacrifice(s: GameSession, snap: PlayerSnapshot, templates: GameTemplates, pet: Pet) -> None:
    """sacrifice (6): o mascote some e dá Sylph Sepulcrum pela estrela (``sepulcrum``). Recusas do
    ``PetShowView``: em batalha, na equipe do Sylph Arena, com equipamento; e o último ("Cannot sacrifice your last
    Sylph"), que o cliente só tem como texto."""
    now = s.ctx.clock.now()
    # ponytail: sorteio uniforme na faixa da dica; a distribuição oficial não está no cliente
    n = random.randint(*sepulcrum(pet.quality))
    if (
        pet.is_fight
        or _in_arena(snap, pet)
        or pet_items(snap, pet)
        or len(snap.pets) <= 1
        or not bag.fits(snap, templates, [(SEPULCRUM, n)], now)
    ):
        s.log.info("8621 sacrifício recusado", pet=pet.id)
        return
    got = bag.add(snap, templates, SEPULCRUM, n, now)
    snap.pets.remove(pet)
    await s.ctx.characters.save(*got, delete=(pet,))

    out = pets_msg(snap, templates, [])
    out.petInfo.add(petId=pet.id or 0, isDel=True)
    s.send(S_PETS, out)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    castle_yield(s)
    from . import offer  # offer importa player, que importa este módulo

    await offer.progress(s, offer.SACRIFICE_PET)  # "Sacrifice Sylph"


async def _compose(
    s: GameSession, snap: PlayerSnapshot, templates: GameTemplates, pet: Pet, msg: pb.PlayerPetOpMsg
) -> None:
    """composePet (13): o pet troca de template pela receita (tipo, tier e estrela) e gasta os materiais e o
    ouro dela. Nível, pontos, aptidões, skills e nome ficam (dedução: o oficial não publica o que muda).
    Valida tudo antes de mexer; um save só."""
    tpl = templates.get("PetTempInfos", pet.template_id)
    found = compose_recipe(templates, pet) if tpl and can_compose(tpl, snap.character.grades) else None
    if found is None:
        s.log.info("8621 recusado: sem receita para o pet ou fora da trava", pedido=str(msg))
        return
    recipe, result = found
    need = [
        (int(recipe[f"NeedItemTempId{i}"]), int(recipe[f"NeedItemTempIdCount{i}"]))
        for i in (1, 2, 3)
        if int(recipe[f"NeedItemTempId{i}"]) > 0
    ]
    c, gold = snap.character, int(recipe["NeedGold"])
    if c.gold < gold or any(bag.count_of(snap, tid) < n for tid, n in need):
        s.log.info("8621 recusado: material ou ouro", pedido=str(msg))
        return
    changed: list[Item] = []
    gone: list[Item] = []
    for tid, n in need:
        ch, go = bag.take(snap, tid, n)
        changed += ch
        gone += go
    c.gold -= gold
    pet.template_id = result
    await s.ctx.characters.save(pet, c, *changed, delete=tuple(gone))

    s.send(S_PETS, pets_msg(snap, templates, [pet]))
    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    castle_yield(s)
    if pet.is_fight:
        _army(s)  # o 150 leva o template do pet em batalha (petTempId)


def _spent_bound(c_gift_before: int, c_gift_after: int, items: Sequence[Item]) -> bool:
    return c_gift_after < c_gift_before or any(i.is_binds for i in items)


async def _advance(
    s: GameSession, snap: PlayerSnapshot, templates: GameTemplates, pet: Pet, msg: pb.PlayerPetOpMsg
) -> None:
    """trainGrowthRate (4, ``PetAdvancedView``): ``value`` unidades de avanço. Cada uma dá 10 de EXP de qualidade
    (``curQualityGp``), 50 com a bênção do Sylph; a barra cheia (``Data`` da estrela seguinte na tabela do
    ``NeedGrade``: 27, 29 ou 107) sobe a estrela e o resto fica (**dedução**). Sem estrela seguinte: "Blessing full,
    cannot advance". Gasta primeiro o Mahra (Adv. Mahra no NeedGrade 3), o que falta a 35 Balens a unidade (payType 0
    aceita vinculados); sem saldo para o resto, recusa (o cliente abre a recarga). Na cor nova o pet passa ao
    template da cor (mesmo tipo e NeedGrade, **dedução**) e o ``growthRate`` segue o ``calculateCoeLimit``. Item ou
    Balens vinculado vincula o pet (``PetAdvancedView.useBindPointTip``)."""
    tpl = templates.get("PetTempInfos", pet.template_id)
    rule = ADVANCE_RULES.get(int(tpl.get("NeedGrade") or 0)) if tpl else None
    need = {int(r["Grades"]): int(r["Data"]) for r in templates.find("UpGradeTempInfos", Types=rule[0])} if rule else {}
    star = pet_star(pet, tpl) if tpl else 0
    if tpl is None or rule is None or not 1 <= msg.value <= MAX_UNITS or star + 1 not in need:
        s.log.info("8621 avanço recusado", pedido=str(msg))
        return
    _, item, price_key = rule
    used, gp = 0, pet.quality_gp
    while used < msg.value and star + 1 in need:
        used += 1
        gp += ADVANCE_GP * (BLESSING if random.randrange(100) < BLESSING_CHANCE else 1)
        while star + 1 in need and gp >= need[star + 1]:
            gp, star = gp - need[star + 1], star + 1
    gp = gp if star + 1 in need else 0  # na última estrela a barra para
    c, now = snap.character, s.ctx.clock.now()
    from_bag = min(used, bag.count_of(snap, item))
    cost = (used - from_bag) * int(rules.config(templates, price_key, "35"))
    gift = c.gift_token
    spent = ledger.pay(c, cost, bind=msg.payType == 0, reason="pet_advance", ref=str(pet.id), now=now) if cost else None
    if cost and spent is None:
        s.log.info("8621 avanço recusado: sem Balens", pedido=str(msg), custo=cost)
        return
    changed, gone = bag.take(snap, item, from_bag) if from_bag else ([], [])
    old_template = pet.template_id
    if tier(star) != tier(pet_star(pet, tpl)):
        family = pet_template_id(int(tpl["PetType"]), int(tpl["NeedGrade"]), tier(star))
        pet.template_id = family if templates.get("PetTempInfos", family) else pet.template_id
    pet.quality, pet.quality_gp = star, gp
    pet.growth_rate = coe_limit(templates, tpl, star, "GrowthRate") or pet.growth_rate
    pet.is_bind = pet.is_bind or _spent_bound(gift, c.gift_token, [*changed, *gone])
    await s.ctx.characters.save(pet, *changed, *([c, spent] if spent else []), delete=tuple(gone))

    s.send(S_PETS, pets_msg(snap, templates, [pet]))
    if changed or gone:
        send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    if spent:
        _player(s)
    if pet.is_fight and pet.template_id != old_template:
        _army(s)  # o 150 leva o template do pet em batalha


async def _enchant(
    s: GameSession, snap: PlayerSnapshot, templates: GameTemplates, pet: Pet, msg: pb.PlayerPetOpMsg
) -> None:
    """trainCoe (7, ``PetStrengthenView``): ``value`` Sepulcrums (Adv. Sepulcrum no NeedGrade 3), sem Balens. Cada
    um melhora uma aptidão sorteada entre as abaixo do teto (``calculateCoeLimit`` do máximo de ``PowerApt``... na
    estrela do pet) sem passar dele. Recusa sem itens bastantes ou com as 4 no teto ("Attributes maxed, please advance
    Sylph's max limit."). Item vinculado vincula o pet (``GrowthInfoView.useBindGoodsTip``)."""
    tpl = templates.get("PetTempInfos", pet.template_id)
    item = ADV_SEPULCRUM if tpl and tpl.get("NeedGrade") == "3" else SEPULCRUM
    caps = (
        {a: coe_limit(templates, tpl, pet_star(pet, tpl), f) for a, f in zip(ATTRS, APT_FIELDS, strict=True)}
        if tpl
        else {}
    )
    room = [a for a in caps if getattr(pet, f"{a}_apti") < caps[a]]
    if tpl is None or not 1 <= msg.value <= MAX_UNITS or bag.count_of(snap, item) < msg.value or not room:
        s.log.info("8621 encantar recusado", pedido=str(msg))
        return
    used = 0
    while used < msg.value and room:
        used += 1
        a = random.choice(room)
        setattr(pet, f"{a}_apti", min(caps[a], getattr(pet, f"{a}_apti") + random.randint(*ENCHANT_GAIN)))
        room = [a for a in caps if getattr(pet, f"{a}_apti") < caps[a]]
    changed, gone = bag.take(snap, item, used)
    pet.is_bind = pet.is_bind or _spent_bound(0, 0, [*changed, *gone])
    await s.ctx.characters.save(pet, *changed, delete=tuple(gone))

    s.send(S_PETS, pets_msg(snap, templates, [pet]))
    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))


def sync_fast_key(pet: Pet, templates: GameTemplates, swap: tuple[str, str] | None = None) -> None:
    """``fastKey`` com o SonType de toda ativa (sem isso o ``PetLearnSkillView`` não as desenha): a trocada fica no
    mesmo lugar, a nova entra no primeiro "-1"."""
    skills = [templates.get("SkillTempInfos", x) or {} for x in pet.change_skills.split(",") if x]
    actives = [sk["SonType"] for sk in skills if sk.get("UseWay") == ACTIVE]
    keys = [k for k in pet.fast_key.split(",") if k][:FAST_SLOTS]
    keys += ["-1"] * (FAST_SLOTS - len(keys))
    keys = [swap[1] if swap and k == swap[0] else k for k in keys]
    keys = [k if k in actives else "-1" for k in keys]
    for son in actives:
        if son not in keys and "-1" in keys:
            keys[keys.index("-1")] = son
    pet.fast_key = "".join(f"{k}," for k in keys)


def place_skill(pet: Pet, templates: GameTemplates, skill: Row) -> None:
    """Põe a skill nas de batalha (``changeSkills``): 5 ativas e 3 passivas; cheio, troca uma do mesmo tipo
    sorteada ("If skill slots are full, a learned skill will be randomly replaced"), no mesmo lugar: os índices do
    torneio (``chaSkillIndexs``) continuam valendo."""
    ids = [x for x in pet.change_skills.split(",") if x]
    way, new = skill["UseWay"], skill["TemplateId"]
    same = [i for i, x in enumerate(ids) if (templates.get("SkillTempInfos", x) or {}).get("UseWay") == way]
    swap = None
    if len(same) < SKILL_SLOTS[way]:
        ids.append(new)
    else:
        at = random.choice(same)
        swap = ((templates.get("SkillTempInfos", ids[at]) or {}).get("SonType", ""), skill["SonType"])
        ids[at] = new
    pet.change_skills = ",".join(ids)
    sync_fast_key(pet, templates, swap)


async def _learn(
    s: GameSession, snap: PlayerSnapshot, templates: GameTemplates, pet: Pet, msg: pb.PlayerPetOpMsg
) -> None:
    """learnSkill (5, ``PetLearnSkillView``). ``value`` 1: a skill ``skillId`` de um livro (ItemTempInfos SonType 303,
    ``Property1``): com o livro na mochila gasta o livro, sem ele paga o preço da loja de livros (``ShopTempInfos``
    Area 7, Point + GiftToken; payType 0 aceita vinculados). ``value`` 2: uma skill sorteada entre as dos livros que
    o pet pode aprender, grátis a cada ``pet_learn_random_skill_interval`` minutos menos o VIP (privilégio 205), senão
    ``pet_learn_random_skill`` Balens. A skill tem de ser do tipo do pet ou de qualquer um (MasterType 107), com
    ``NeedPlayerGrade`` até o herói, e não aprendida ("You already have this skill!")."""
    tpl = templates.get("PetTempInfos", pet.template_id) or {}
    c, sy, now = snap.character, rules.systems(snap), s.ctx.clock.now()
    learned = {x for x in pet.change_skills.split(",") if x}

    def fits(skill: Row | None) -> bool:
        return (
            skill is not None
            and skill.get("MasterType") in (tpl.get("PetType"), ANY_PET)
            and skill.get("UseWay") in SKILL_SLOTS
            and int(skill.get("NeedPlayerGrade") or 0) <= c.grades
            and skill["TemplateId"] not in learned
        )

    books = {r["Property1"]: int(r["TemplateId"]) for r in templates.find("ItemTempInfos", SonType=SKILL_BOOK)}
    skill: Row | None = None
    cost, book, free = 0, 0, False
    if msg.value == LEARN_BOOK and str(msg.skillId) in books:
        skill, book = templates.get("SkillTempInfos", msg.skillId), books[str(msg.skillId)]
        if bag.count_of(snap, book) <= 0:
            shop = next(templates.find("ShopTempInfos", Area=SKILL_SHOP_AREA, ItemId=book), None)
            cost = int(shop["Point"] or 0) + int(shop["GiftToken"] or 0) if shop else 0
            book = 0
            skill = skill if cost > 0 else None
    elif msg.value == LEARN_RANDOM:
        # ponytail: o sorteio é uniforme entre as skills dos livros; o cliente não tem a lista nem os pesos
        pool = [sk for sid in books if fits(sk := templates.get("SkillTempInfos", sid))]
        skill = random.choice(pool) if pool else None
        wait = (
            int(rules.config(templates, "pet_learn_random_skill_interval", "480")) - vip_right(s, snap, VIP_SKILL_WAIT)
        ) * 60
        free = sy.pet_free_skill_at is None or (now - sy.pet_free_skill_at).total_seconds() > wait
        cost = 0 if free else int(rules.config(templates, "pet_learn_random_skill", "100"))
    if skill is None or not fits(skill) or not tpl:
        s.log.info("8621 aprender recusado", pedido=str(msg))
        return
    spent = ledger.pay(c, cost, bind=msg.payType == 0, reason="pet_skill", ref=str(pet.id), now=now) if cost else None
    if cost and spent is None:
        s.log.info("8621 aprender recusado: sem Balens", pedido=str(msg), custo=cost)
        return
    changed, gone = bag.take(snap, book, 1) if book else ([], [])
    if free:
        sy.pet_free_skill_at = now
    place_skill(pet, templates, skill)
    await s.ctx.characters.save(
        pet, *changed, *([c, spent] if spent else []), *([sy] if free else []), delete=tuple(gone)
    )

    s.send(S_PETS, pets_msg(snap, templates, [pet]))
    if changed or gone:
        send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    if spent or free:
        _player(s)  # Balens e o lastFreeSkillLearnTime


@router.on(8621)
async def pet_op(s: GameSession, msg: pb.PlayerPetOpMsg) -> None:
    """opType 1 devora (``_swallow``); 2 distribui ``attributes`` [força, int, físico, armadura]; 3 zera os pontos
    (pet_reset_att diamantes); 6 sacrifica (``_sacrifice``); 9 manda para a batalha (só um; pede o ``NeedGrade``
    do template e nível até o do herói, e vincula: "Active Sylphs become bound"); 10 descansa; 11 atalhos de skill
    (``petName``); 12 compra ``value`` vagas (add_pet_count "a,b,c": cada uma min(a + k x b, c), k = já
    compradas, como o diálogo PetListView.openPos); 13 compõe (``_compose``); 14 põe no topo
    da lista; 4 avança (``_advance``), 5 aprende skill (``_learn``), 7 encanta aptidão (``_enchant``). Resposta: 4540
    com os pets alterados (+3 quando paga)."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    pet = next((p for p in snap.pets if p.id == msg.petId), None)
    sy, c = rules.systems(snap), snap.character
    changed: list[object] = []
    paid = False
    if msg.opType == MORE_SLOTS:
        base, step, top = (int(x) for x in rules.config(templates, "add_pet_count", "100,100,300").split(","))
        n = max(msg.value, 1)
        cost = sum(min(base + k * step, top) for k in range(sy.pet_slots, sy.pet_slots + n))
        spent = None
        if BASE_SLOTS + sy.pet_slots + n <= MAX_SLOTS:
            spent = ledger.pay(c, cost, bind=msg.payType == 0, reason="pet_slots", ref="", now=s.ctx.clock.now())
        if spent is None:
            s.log.info("8621 recusado", pedido=str(msg))
            return
        sy.pet_slots += n
        changed, paid = [sy, c, spent], True
    elif pet is None:
        s.log.info("8621 recusado: pet não existe", pedido=str(msg))
        return
    elif msg.opType == ADD_POINTS:
        add = list(msg.attributes)
        if len(add) != len(ATTRS) or min(add) < 0 or sum(add) > remain_points(pet):
            s.log.info("8621 recusado", pedido=str(msg))
            return
        for attr, n in zip(ATTRS, add, strict=True):
            setattr(pet, attr, getattr(pet, attr) + n)
        changed = [pet]
    elif msg.opType == RESET_POINTS:
        cost = int(rules.config(templates, "pet_reset_att", "100"))
        if (
            spent := ledger.pay(
                c, cost, bind=msg.payType == 0, reason="pet_reset", ref=str(pet.id), now=s.ctx.clock.now()
            )
        ) is None:
            s.log.info("8621 recusado: sem diamantes", pedido=str(msg))
            return
        for attr in ATTRS:
            setattr(pet, attr, 0)
        changed, paid = [pet, c, spent], True
    elif msg.opType == FIGHT and (
        c.grades < int((templates.get("PetTempInfos", pet.template_id) or {}).get("NeedGrade", 0))
        or pet.grade > c.grades
    ):
        s.log.info("8621 batalha recusada: nível", pedido=str(msg))
        return
    elif msg.opType in (FIGHT, REST):
        pet.is_bind = pet.is_bind or msg.opType == FIGHT
        for other in snap.pets:
            if other.is_fight and other is not pet:
                other.is_fight = False
                changed.append(other)
        pet.is_fight = msg.opType == FIGHT
        changed.append(pet)
    elif msg.opType == FAST_KEY:
        pet.fast_key = msg.petName[:255]
        changed = [pet]
    elif msg.opType == TO_TOP:
        for other in snap.pets:
            other.pos = 0 if other is pet else other.pos + 1
        changed = list(snap.pets)
    elif msg.opType == COMPOSE:
        await _compose(s, snap, templates, pet, msg)
        return
    elif msg.opType == SWALLOW:
        await _swallow(s, snap, templates, pet, msg)
        return
    elif msg.opType == SACRIFICE:
        await _sacrifice(s, snap, templates, pet)
        return
    elif msg.opType == ADVANCE:
        await _advance(s, snap, templates, pet, msg)
        return
    elif msg.opType == ENCHANT:
        await _enchant(s, snap, templates, pet, msg)
        return
    elif msg.opType == LEARN:
        await _learn(s, snap, templates, pet, msg)
        return
    else:
        # 8 (trainResistance) e 15 (fusão de 2 pets, mixDoublePet) não têm chamador no cliente inglês; a fusão dá os
        # tipos 117-119, sem template. Nada a responder: ficam no log
        s.log.info("8621 op sem tela no cliente inglês", pedido=str(msg))
        return
    await s.ctx.characters.save(*changed)
    pets = [p for p in snap.pets if p in changed]
    s.send(S_PETS, pets_msg(snap, templates, pets))
    if paid:
        _player(s)
    if msg.opType in (FIGHT, REST):
        _army(s)  # o 150 leva o pet em batalha (petTempId/petName)


@router.on(8702)
async def other_pets(s: GameSession, msg: pb.PlayerPetOpMsg) -> None:
    """Ficha dos pets de outro jogador (``petId`` = userId) -> 4608."""
    other = await snapshot_of(s, msg.petId)  # online: a sessão; offline: o banco
    if other is None:
        s.log.info("8702 recusado: jogador não existe", pedido=str(msg))
        return
    s.send(S_OTHER_PETS, pets_msg(other, s.ctx.templates))
