"""Pets (``PlayerPetOpMsg`` 8621, ficha de outro jogador 8702).

Fonte: login #30 (4540 com um pet completo, ``petCount`` 6) e ``ConfigInfos`` (pet_reset_att,
add_pet_count). O 4540 é incremental: só os pets que mudaram (``isDel`` apaga).
"""

from __future__ import annotations

from ...domain.models import Pet, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import rules
from ..builders.login import complete
from ..router import router
from ..session import GameSession
from .player import _army, _player

S_PETS, S_OTHER_PETS = 4540, 4608
ADD_POINTS, RESET_POINTS, FIGHT, REST, FAST_KEY, MORE_SLOTS, TO_TOP = 2, 3, 9, 10, 11, 12, 14
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


@router.on(8621)
async def pet_op(s: GameSession, msg: pb.PlayerPetOpMsg) -> None:
    """opType 2 distribui ``attributes`` [força, int, físico, armadura]; 3 zera os pontos
    (pet_reset_att diamantes); 9 manda para a batalha (só um); 10 descansa; 11 atalhos de skill
    (``petName``); 12 compra vaga (add_pet_count por compra); 14 põe no topo da lista.
    Resposta: 4540 com os pets alterados (+3 quando paga)."""
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
    else:
        # ponytail: devorar, crescimento, skills, sacrifício, treino, resistência e fusões dependem de
        # tabelas (PetComponseInfos...) e de capturas que não temos; ficam no log
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
