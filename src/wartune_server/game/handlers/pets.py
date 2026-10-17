"""Pets (``PlayerPetOpMsg`` 8621, ficha de outro jogador 8702).

Fonte: login #30 (4540 com um pet completo, ``petCount`` 6) e ``ConfigInfos`` (pet_reset_att,
add_pet_count). O 4540 é incremental: só os pets que mudaram (``isDel`` apaga).
Composição de um pet (13, cliente ``PetSocketOut.composePet``): receitas de ``PetComponseInfos``.
"""

from __future__ import annotations

from ...domain.models import Item, Pet, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates, Row
from .. import bag, rules
from ..builders.login import complete
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import _army, _player
from .shop import send

S_PETS, S_OTHER_PETS, S_ITEMS = 4540, 4608, 115
ADD_POINTS, RESET_POINTS, FIGHT, REST, FAST_KEY, MORE_SLOTS, TO_TOP = 2, 3, 9, 10, 11, 12, 14
COMPOSE = 13  # composePet: receita de um pet só (PetComponseInfos com Pet2Types 0)
BASE_SLOTS = 3  # login: petCount 6 = 3 + as 3 compras de add_pet_count
POINTS_PER_GRADE = 5  # ponytail: pontos livres por nível do pet; o oficial não publica a regra
ATTRS = ("power", "intel", "physi", "armor")
TPL_ATTRS = ("Power", "Intel", "Physi", "Armor")
RESISTS = ("fire", "water", "elect", "wind", "dark", "light")


def remain_points(pet: Pet) -> int:
    return POINTS_PER_GRADE * (pet.grade - 1) - (pet.power + pet.intel + pet.physi + pet.armor)


def pet_info(pet: Pet, templates: GameTemplates) -> pb.PetInfoMsg:
    tpl = templates.get("PetTempInfos", pet.template_id) or {}
    msg = pb.PetInfoMsg(
        petId=pet.id or 0,
        templateId=pet.template_id,
        petName=pet.name,
        curGp=pet.gp,
        curGrade=pet.grade,
        remainPoints=remain_points(pet),
        growthRate=pet.growth_rate,
        followSkills=pet.follow_skills,
        changeSkills=pet.change_skills,
        isFight=pet.is_fight,
        isBind=True,
        totalGp=pet.gp,
        quality=pet.quality,
        chaSkillIndexs="-1,-1,-1",
        fastKey=pet.fast_key,
        initQuality=int(tpl.get("Quality", 1)),
    )
    for attr, col in zip(ATTRS, TPL_ATTRS, strict=True):
        apti = getattr(pet, f"{attr}_apti")
        # ponytail: atributo = template + pontos + nível x aptidão/100 (aproxima o login #30; fórmula real
        # fica no servidor oficial)
        setattr(msg, attr, int(tpl.get(col, 0)) + getattr(pet, attr) + pet.grade * apti // 100)
        name = attr.capitalize()
        for prefix in ("init", "", "next"):
            setattr(msg, f"{prefix}{name}Apti" if prefix else f"{attr}Apti", apti)
    msg.maxHp = int(tpl.get("MaxHp", 0)) + 10 * msg.physi  # ponytail: mesma aproximação
    for r in RESISTS:
        setattr(msg, f"{r}Resi", int(tpl.get(f"{r.capitalize()}Resi", 0)))
    return complete(msg)


def pets_msg(snap: PlayerSnapshot, templates: GameTemplates, pets: list[Pet] | None = None) -> pb.PlayerPetMsg:
    c = snap.character
    msg = pb.PlayerPetMsg(userId=c.id, nickName=c.nickname or "", petCount=BASE_SLOTS + rules.systems(snap).pet_slots)
    for pet in sorted(snap.pets if pets is None else pets, key=lambda p: p.pos):
        msg.petInfo.append(pet_info(pet, templates))
    return msg


def pet_template_id(pet_type: int, tier: int, star: int) -> int:
    """Template de um pet: tipo, tier (``NeedGrade``) e estrela (``Quality``). 104101 = Pan, tier 1, estrela 1."""
    return pet_type * 1000 + tier * 100 + star


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


async def _compose(
    s: GameSession, snap: PlayerSnapshot, templates: GameTemplates, pet: Pet, msg: pb.PlayerPetOpMsg
) -> None:
    """composePet (13): o pet troca de template pela receita (tipo, tier e estrela) e gasta os materiais e o
    ouro dela. Nível, pontos, aptidões, skills e nome ficam (dedução: o oficial não publica o que muda).
    Valida tudo antes de mexer; um save só."""
    found = compose_recipe(templates, pet)
    if found is None:
        s.log.info("8621 recusado: sem receita para o pet", pedido=str(msg))
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


@router.on(8621)
async def pet_op(s: GameSession, msg: pb.PlayerPetOpMsg) -> None:
    """opType 2 distribui ``attributes`` [força, int, físico, armadura]; 3 zera os pontos
    (pet_reset_att diamantes); 9 manda para a batalha (só um); 10 descansa; 11 atalhos de skill
    (``petName``); 12 compra vaga (add_pet_count por compra); 13 compõe (``_compose``); 14 põe no topo
    da lista. Resposta: 4540 com os pets alterados (+3 quando paga)."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    pet = next((p for p in snap.pets if p.id == msg.petId), None)
    sy, c = rules.systems(snap), snap.character
    changed: list[object] = []
    paid = False
    if msg.opType == MORE_SLOTS:
        prices = [int(x) for x in rules.config(templates, "add_pet_count", "100,100,300").split(",")]
        if sy.pet_slots >= len(prices) or not rules.pay_point(c, prices[sy.pet_slots], bind=msg.payType == 0):
            s.log.info("8621 recusado", pedido=str(msg))
            return
        sy.pet_slots += 1
        changed, paid = [sy, c], True
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
        if not rules.pay_point(c, cost, bind=msg.payType == 0):
            s.log.info("8621 recusado: sem diamantes", pedido=str(msg))
            return
        for attr in ATTRS:
            setattr(pet, attr, 0)
        changed, paid = [pet, c], True
    elif msg.opType in (FIGHT, REST):
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
    else:
        # ponytail: devorar, crescimento, skills, sacrifício, treino, resistência e a fusão de 2 pets (15)
        # dependem de tabelas e capturas que não temos (a fusão de 2 dá tipos 117-119, sem template)
        s.log.info("8621 op sem implementação", pedido=str(msg))
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
    other = s.ctx.online.get(msg.petId)  # ponytail: só jogador online
    if other is None or other.snapshot is None:
        s.log.info("8702 recusado: jogador offline", pedido=str(msg))
        return
    s.send(S_OTHER_PETS, pets_msg(other.snapshot, s.ctx.templates))
