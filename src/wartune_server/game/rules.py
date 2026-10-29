"""Regras de progressão aplicadas ao ``PlayerSnapshot`` em memória: EXP e nível, crescimento do
herói, equipamentos, missões. Quem chama grava as entidades alteradas (``CharacterService.save``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from ..domain import gameday
from ..domain.models import (
    BagType,
    Building,
    Character,
    Consortia,
    Hero,
    Item,
    Pawn,
    PlayerSnapshot,
    PlayerSystems,
    Quest,
    StarBag,
)
from ..templates.repository import GameTemplates, Row
from . import buffs
from . import events as ev
from .builders.login import QUEST_SITE_LEN, RESIST_COLS, HeroStats, hero_hp

PLAYER_GRADE = "3"  # UpGradeTempInfo.Types do nível do jogador; Data = EXP do nível anterior até este
NOVICE_CONDITION = 23  # QuestConditionInfo: noviceProcess > Para1
BUILDING_CONDITION = 2  # QuestConditionInfo: prédio SonType Para1 no nível Para2 (progresso = nível atual)
# 37: a cidade está no mapa Para2, igualdade e não "o maior" (cliente) TaskTemplate.checkMapId
MAP_CONDITION = 37
RUNE_STUDY, RUNE_COMBINE, RUNE_GRADE = 76, 77, 78  # símbolo aprendido (Para1 = RuneType), pedras gastas, grau
WEAPON, CLOTH = "101", "104"  # ItemTempInfo.SonType
WING, HAT, FASHION_CLOTH, FASHION_ARM = "109", "110", "112", "111"
HERO_BAGS = (BagType.RUNE, BagType.HONOR, BagType.HERO)  # bolsas do herói que somam atributos

# ganho de atributos por nível, por JobType (1 guerreiro, 2 caçador, 3 mago). O mago foi medido na
# captura inglesa (níveis 1 a 10, os 150 de builders/login.py); ponytail: guerreiro e caçador são o espelho
# dele, trocar quando houver captura.
GROWTH = {
    1: {"power": 3, "agility": 1, "captain": 10, "physique": 1},
    2: {"agility": 3, "power": 1, "captain": 10, "physique": 1},
    3: {"intellect": 3, "agility": 1, "captain": 10, "physique": 1},
}


def job_type(job: int) -> int:
    return (job - 1) % 3 + 1


STAT_KEYS = "Power Agility Intellect Captain Physique Attack Defence MagicAttack MagicDefence ForceHit Parry Live Conat"


def strengthened(row: Row, grade: int) -> Row:
    """Atributos do item reforçado: ``GoodsHelp.getStrengthenAddition`` = int(base*g*0.1) + g*5."""
    if grade <= 0:
        return row
    out = dict(row)
    for k in STAT_KEYS.split():
        if (base := int(row.get(k) or 0)) > 0:
            out[k] = str(base + int(base * grade * 0.1) + grade * 5)
    return out


# PetInfoMsg.bag*: o PetData soma cada um no ataque/defesa/vida mostrados (equipPhysicalAttack...)
PET_EQUIP_STATS = {"Attack": "bagAttack", "Defence": "bagDefence", "MagicAttack": "bagMagicattack"}
PET_EQUIP_STATS |= {"MagicDefence": "bagMagicdefence", "Live": "bagLiving"}


def pet_equipment(items: Sequence[Item], templates: GameTemplates) -> dict[str, int]:
    """``bag*`` do mascote pelas peças vestidas (bolsa 26): atributo do template + encantamento
    (``GoodsHelp.getPetEquipStrengAddition``: ``int(base × 1,08^g − base)``) + Almas engastadas + atributos sorteados.
    ponytail: o total é dedução (o cliente só lê o pronto). Na luta o mascote em batalha (``campaign.fighting_pet``)
    soma a vida (``maxHp`` do 4540) e o ataque; o torneio de fadas (``arena.pet_unit`` do 8724) não."""
    out = dict.fromkeys(PET_EQUIP_STATS.values(), 0)
    for item in items:
        row = templates.get("ItemTempInfos", item.template_id) or {}
        rows: list[Row] = [templates.get("ItemTempInfos", gem) or {} for gem in item.joins if gem > 0]
        rows += [templates.get("SkillPropertyTempInfos", k) or {} for k in item.random_skills if k]
        for stat, field_name in PET_EQUIP_STATS.items():
            base = int(row.get(stat) or 0)
            mould = int(base * 1.08**item.mould_grade - base) if base > 0 and item.mould_grade > 0 else 0
            out[field_name] += base + mould + sum(int(r.get(stat) or 0) for r in rows)
    return out


def equipment(snap: PlayerSnapshot, templates: GameTemplates) -> list[Row]:
    """Linhas de template que somam nos atributos do líder: itens equipados (com o reforço), os
    atributos sorteados (``SkillPropertyTempInfos``) e as pedras engastadas."""
    leader = snap.leader
    rows: list[Row] = []
    for item in snap.items:
        if item.bag_type not in HERO_BAGS or leader is None or item.object_id != leader.id:
            continue
        if (row := templates.get("ItemTempInfos", item.template_id)) is not None:
            rows.append(strengthened(row, item.strengthen_grade))
        for skill in item.random_skills:
            if skill and (bonus := templates.get("SkillPropertyTempInfos", skill)) is not None:
                rows.append(bonus)
        for gem in item.joins:
            if gem > 0 and (stone := templates.get("ItemTempInfos", gem)) is not None:
                rows.append(stone)
    # moda identificada: o livro inteiro soma, vestida ou não (cliente FashionModel.getIdentityedProperties)
    for book in snap.fashions if leader is not None else []:
        if book.appraisal_skill and (bonus := templates.get("SkillPropertyTempInfos", book.appraisal_skill)):
            rows.append(bonus)
    # gemas da guarda de batalha: as resistências (FireResi..DarkResi, ReduceResi) do template de cada uma
    for gems in guard(snap.systems).values() if leader is not None and snap.systems is not None else []:
        rows += [row for gem in gems if gem > 0 and (row := templates.get("ItemTempInfos", gem)) is not None]
    return rows


# guarda de batalha (cliente BattleGuardInfo): gridType 1 = Willpower (1 encaixe, gema Property1 100), 2 = os 6
# entalhes de resistência (Property1 101..106); 3 gemas por encaixe (BattleGuardSocketInfo length 3)
GUARD_WILL, GUARD_NOTCH, GUARD_JOINS, GUARD_NOTCHES = 1, 2, 3, 6
GUARD_GEM = "312"  # SonType das gemas da guarda (Will Crystal e Resistance Crystal)
RESISTS = RESIST_COLS[:6]  # as 6 resistências (sem ReduceResi, a da Willpower)


def guard(sy: PlayerSystems) -> dict[tuple[int, int], list[int]]:
    """Encaixes abertos -> as 3 gemas (0 = vazio)."""
    out = {}
    for entry in filter(None, sy.battle_guard.split(",")):
        kind, pos, *gems = (int(x) for x in entry.split(":"))
        out[kind, pos] = gems
    return out


def set_guard(sy: PlayerSystems, slots: dict[tuple[int, int], list[int]]) -> None:
    sy.battle_guard = ",".join(f"{k}:{p}:" + ":".join(map(str, g)) for (k, p), g in sorted(slots.items()))


def avatar(snap: PlayerSnapshot, templates: GameTemplates, son_type: str) -> str:
    """Arte (``Avata``) do item equipado com aquele SonType ("" se não houver)."""
    leader = snap.leader
    return next(
        (
            (templates.get("ItemTempInfos", i.template_id) or {}).get("Avata", "")
            for i in snap.items
            if i.bag_type == BagType.HERO
            and leader is not None
            and i.object_id == leader.id
            and (templates.get("ItemTempInfos", i.template_id) or {}).get("SonType") == son_type
        ),
        "",
    )


def systems(snap: PlayerSnapshot) -> PlayerSystems:
    assert snap.systems is not None  # CharacterService.snapshot sempre preenche
    return snap.systems


def refresh_star_day(sy: PlayerSystems, now: datetime) -> None:
    """O dia das estrelas vira às 5h (o cliente manda o 8325 nessa hora); quem estava offline
    recebe o sorteio grátis na próxima leitura. Idempotente: grava junto com a próxima save."""
    day = gameday.today(now)
    if sy.star_day != day:
        sy.star_day, sy.star_free = day, 1


MOUNT_ATTRS = ("Power", "Intellect", "Physique", "Agility")  # ordem de PlayerSystems.mount_gp
MOUNT_GRADE = "18"  # UpGradeTempInfo.Types: EXP acumulada de cada atributo da montaria


def mount_grade(templates: GameTemplates, gp: int, cap: int) -> int:
    steps = sorted((int(r["Grades"]), int(r["Data"])) for r in templates.find("UpGradeTempInfos", Types=MOUNT_GRADE))
    return min(cap, max((g for g, need in steps if gp >= need), default=0))


def mount_stats(snap: PlayerSnapshot, templates: GameTemplates) -> dict[str, int]:
    """Atributos da montaria em uso: valor do template + 5 por grau (só turco: login.json,
    1610 de EXP = grau 11 = 10 + 55 de força)."""
    sy = systems(snap)
    tpl = templates.get("MountTempInfos", sy.mount_template) if sy.mount_template else None
    if tpl is None:
        return {}
    cap = mount_level_max(tpl)
    gps = [int(x) for x in sy.mount_gp.split(",")]
    star, adds = mount_stars(sy).get(sy.mount_template, (0, 0))[0], star_additions(tpl)
    bonus = adds[star - 1] if 0 < star <= len(adds) else 0  # MountsPromotionView: o mesmo valor nos 4 atributos
    return {
        a: int(tpl.get(a, 0)) + 5 * mount_grade(templates, gp, cap) + bonus
        for a, gp in zip(MOUNT_ATTRS, gps, strict=True)
    }


def mount_stars(sy: PlayerSystems) -> dict[int, tuple[int, int]]:
    """Estrela e bênção de cada montaria (op 6)."""
    return {int(m): (int(a), int(b)) for m, a, b in (x.split(":") for x in sy.mount_stars.split(",") if x)}


def star_additions(tpl: Row) -> list[int]:
    """``MountTempInfo.StarAddition``: o bônus de cada estrela (cumulativo, absoluto); o tamanho é a estrela máxima
    (``MountTemplate.maxStarGrade``)."""
    return [int(x) for x in (tpl.get("StarAddition") or "").split(",") if x.strip().isdigit()]


def mount_level_max(tpl: Row) -> int:
    return 20 + int(tpl.get("ExpandLevel", 0))  # 1103: ExpandLevel 5 -> levelMax 25 (visto)


def star_bonuses(snap: PlayerSnapshot, templates: GameTemplates) -> list[Row]:
    """Estrelas equipadas: cada coluna de atributo do template vezes o grau."""
    rows: list[Row] = []
    for star in snap.stars:
        if star.bag_type == StarBag.EQUIP and (tpl := templates.get("starTempInfos", star.template_id)):
            attrs = {k: v for k, v in tpl.items() if k in STAR_ATTRS and v.lstrip("-").isdigit()}
            rows.append({k: str(int(v) * star.grade) for k, v in attrs.items()})
    return rows


STAR_ATTRS = {"Power", "Agility", "Intellect", "Captain", "Physique", "Attack", "Defence", "MagicAttack"}
STAR_ATTRS |= {"MagicDefence", "ForceHit", "Parry", "Live", "Conat"}


FREE_HEAL_GRADE = 10  # (cliente) BaseManager.showAlertTip: o aviso de vida sem poção só a partir do nível 10
HEALING_CONTRACT = 3  # KingContracts 3 "Power of Healing": "HP Packs won't be consumed when you restore HP."
BOOST_CONTRACT = 7  # KingContracts 7: +10% de PATK, PDEF, MATK, MDEF, HP e tropa nas masmorras (texto do template)
BOOST_PCT = 10
BOOST_TYPES = frozenset({0, 4})  # Campaigns.Types: masmorras (0) e Forgotten Catacombs/Tormented Necropolis (4)


def heal_hero(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> int:
    """A reserva das poções (``blood``) completa a vida do líder; devolve quanto gastou. (visto)
    oficial_20261023-153200-1: 529 depois de cada derrota (#804, #1320, #1445, #1896: 9471 -> 7884) e 120 ao vestir
    um item que sobe a vida máxima (#2185). Com o contrato Power of Healing a vida enche sem gastar a reserva
    (texto do template)."""
    leader = snap.leader
    assert leader is not None
    live = leader_stats(snap, templates, now).live
    hp = hero_hp(leader, live)
    if ev.has_contract(snap, HEALING_CONTRACT, now):
        # TODO(inventado): se o oficial ainda manda o 83 "Used HP pack to restore HP." com o contrato
        leader.hp = live
        return live - hp
    use = min(leader.blood, live - hp)
    leader.blood -= use
    leader.hp = hp + use
    return use


def hero_after_fight(snap: PlayerSnapshot, templates: GameTemplates, now: datetime, left: int, free: int) -> int:
    """Vida do líder depois da luta: a derrota deixa 1 (#774, sem reserva); abaixo do nível ``free`` volta cheia
    de graça (tutorial_en: o herói chega a 0 em #1466 e #1657 e o 150 seguinte mostra a vida cheia, sem reserva).
    Depois a reserva cura (``heal_hero``); devolve quanto gastou."""
    assert snap.leader is not None
    snap.leader.hp = 0 if snap.character.grades < free else max(1, left)
    return heal_hero(snap, templates, now)


def leader_stats(snap: PlayerSnapshot, templates: GameTemplates, now: datetime | None) -> HeroStats:
    """Atributos do líder: herói + equipamentos + montaria + estrelas equipadas + poções ativas (``buffs``; ``now``
    ``None`` = sem as poções).

    Talento, runas, destino e alma do dragão não somam atributo fixo: nos templates eles são
    skills/buffs (SkillTempInfos/TalentEffectTempInfos) que agem na batalha.
    """
    leader = snap.leader
    assert leader is not None
    potions = buffs.stat_bonuses(snap, templates, now) if now is not None else []
    bonuses = equipment(snap, templates) + star_bonuses(snap, templates) + potions
    if mount := mount_stats(snap, templates):
        bonuses.append({k: str(v) for k, v in mount.items()})
    skills = guild_skills(snap.character, templates)
    base = {attr: skills.get(kind, 0) for kind, attr in GUILD_SKILL_ATTRS.items()}
    if hero := {HERO_TECH[k]: str(v) for k, v in tech_effects(snap, templates).items() if k in HERO_TECH}:
        bonuses.append(hero)
    return HeroStats.of(leader, templates.hero(leader.template_id), bonuses, base)


# tecnologias de atributo (BuildingTempInfos MasterType 14): EffectTempInfos.PropertyType1 -> coluna do template, com
# Property1 x nível (cliente: o Activity do template, "MATK +228" no Hero MATK 19). As Adv. (2xxx) usam o tipo + 100.
# A roda da bênção (``seminary_effect``) multiplica cada tecnologia por (100 + bênção)/100, com floor: (só turco:
# city_city_upgrade #14-#137) 444 -> 488 com 10% e 666 com 50%, 35 -> 38 e 52; teknoloji_upgrade 342 = 12 x 19 x 1,5.
# Cliente: "Technology boosts strengthen the effects of any technology" (blessHelpContent)
HERO_TECH = {141: "Attack", 142: "MagicAttack", 143: "Defence", 144: "MagicDefence", 145: "Live", 146: "Conat"}
TROOP_TECH = {120: "Live", 121: "Attack", 122: "Defence", 123: "MagicAttack", 124: "MagicDefence"}
TECH_ATTR, ADV_TECH = "14", 100


def boosted(value: int, bless: int) -> int:
    """Efeito de uma tecnologia com a bênção ``bless`` (%)."""
    return value * (100 + bless) // 100


def attr_techs(snap: PlayerSnapshot, templates: GameTemplates) -> list[tuple[int, int, int, Building]]:
    """(tipo sem o Adv., tipo do efeito, Property1 x nível sem a bênção, prédio) de cada tecnologia de atributo."""
    out = []
    for building in snap.buildings:
        row = templates.get("BuildingTempInfos", building.template_id)
        if row is None or row["MasterType"] != TECH_ATTR:
            continue
        effect = templates.get("EffectTempInfos", int(row["Property1"])) or {}
        raw = int(effect.get("PropertyType1", 0))
        kind = raw - (ADV_TECH if raw >= 2 * ADV_TECH else 0)
        out.append((kind, raw, int(effect.get("Property1", 0)) * int(row["BuildingGrade"]), building))
    return out


def tech_effects(snap: PlayerSnapshot, templates: GameTemplates) -> dict[int, int]:
    """Tipo (141, 120...) -> soma das tecnologias de atributo construídas, normal e Adv. juntas, com a bênção."""
    out: dict[int, int] = {}
    for kind, _, base, _ in attr_techs(snap, templates):
        out[kind] = out.get(kind, 0) + boosted(base, snap.character.seminary_effect)
    return out


def troop_tech(snap: PlayerSnapshot, templates: GameTemplates) -> dict[str, int]:
    """Coluna do PawnTempInfos (Live, Attack...) -> bônus das tecnologias de tropa (o ``effect_Data`` do pawnLive)."""
    return {TROOP_TECH[k]: v for k, v in tech_effects(snap, templates).items() if k in TROOP_TECH}


# habilidades aprendidas na guilda (5147): ConsortiaLevelInfos.Types -> campo do personagem e atributo do herói
GUILD_SKILL_FIELDS = {6: "skill_attack", 8: "skill_agility", 9: "skill_ability", 10: "skill_captain",
                      11: "skill_gold", 12: "skill_physique"}  # fmt: skip
GUILD_SKILL_ATTRS = {6: "Power", 8: "Agility", 9: "Intellect", 10: "Captain", 12: "Physique"}
GUILD_GOLD = 11  # "Gold Production +N%"


def guild_skills(c: Character, templates: GameTemplates) -> dict[int, int]:
    """Tipo -> bônus do nível aprendido, o número do ``Description`` ("Strength +40 (Hero)", "Charisma +20",
    "Gold Production +1%"; o template não tem outra coluna com ele: ``Property2`` = ``NeedOffer``)."""
    out = {}
    for kind, name in GUILD_SKILL_FIELDS.items():
        level = getattr(c, name)
        row = next(templates.find("ConsortiaLevelInfos", Types=kind, Levels=level), None) if level else None
        if row is not None and (found := re.search(r"\+(\d+)", str(row.get("Description") or ""))):
            out[kind] = int(found.group(1))
    return out


HOUSE, BARRACKS = "1201", "402"  # BuildingTempInfo.SonType


def building_row(snap: PlayerSnapshot, templates: GameTemplates, son_type: str) -> Row | None:
    """Template do prédio do jogador com esse SonType (casa, quartel...)."""
    for b in snap.buildings:
        row = next(templates.find("BuildingTempInfos", TemplateId=b.template_id), None)
        if row is not None and row["SonType"] == son_type:
            return row
    return None


def population(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> tuple[int, int]:
    """``(ocupada, máxima)``: soldados no castelo + exército x NeedPopulation; teto = Property2 da casa
    (900 no nível 1, visto no inglês #712) + o Population Expansion Scroll (``buffs.POPULATION``)."""
    used = 0
    for pawn in snap.pawns:
        tpl = templates.get("PawnTempInfos", pawn.template_id) or {}
        used += (pawn.castle_count + pawn.army_count) * int(tpl.get("NeedPopulation", 1))
    house = building_row(snap, templates, HOUSE)
    return used, buffs.boost(int(house["Property2"]) if house else 0, snap, buffs.POPULATION, now)


def army_pawn(snap: PlayerSnapshot) -> Pawn | None:
    """Tropa no exército (slot 0), se houver. Para a batalha: ``battle_pawn``."""
    return next((p for p in snap.pawns if p.army_count > 0), None)


def battle_pawn(snap: PlayerSnapshot, templates: GameTemplates) -> tuple[Row, int] | None:
    """Função pura para a batalha: ``(linha de PawnTempInfos, quantidade)`` da tropa que luta com
    o herói, ou ``None``. Os atributos de cada soldado são as colunas Attack/Defence/MagicAttack/
    MagicDefence/Live/ForceHit/Parry do template (o que vai em ``pawnLive``)."""
    pawn = army_pawn(snap)
    tpl = templates.get("PawnTempInfos", pawn.template_id) if pawn else None
    return (tpl, pawn.army_count) if pawn and tpl else None


def quest_event(snap: PlayerSnapshot, templates: GameTemplates, kind: int, para1: int, value: int) -> list[Quest]:
    """Avança, em cada missão aberta, cada linha de QuestCondictionInfos com CondictionType ``kind`` e Para1
    que casa (0 = qualquer; em ``EXACT_PARA1`` tem que ser igual; em ``MIN_CONDITIONS`` o ``para1`` (grau
    atingido) tem que passar do Para1). A linha N grava no contador condition_N. Tipos de contagem somam
    ``value``; os de nível (``LEVEL_CONDITIONS``) e de grau guardam o maior."""
    changed = []
    for q in snap.quests:
        if q.completed:
            continue
        for k, cond in enumerate(conditions(templates, q.template_id)):
            if int(cond["CondictionType"]) != kind or not _para1_ok(kind, cond["Para1"], para1):
                continue
            old = progress_of(q, k)
            new = max(old, value) if kind in LEVEL_CONDITIONS | MIN_CONDITIONS else old + value
            if new != old:
                set_progress(q, k, new)
                if q not in changed:
                    changed.append(q)
    return changed


def para1_ids(raw: str) -> set[int]:
    """Para1 pode ser lista ("9004,9104": normal e grupo). 0 = qualquer. (visto) tempinfos: só tipos 14 e 26."""
    return {int(x) for x in raw.split(",") if x}


def _para1_ok(kind: int, raw: str, para1: int) -> bool:
    if kind in MIN_CONDITIONS:
        return para1 > int(raw)
    ids = para1_ids(raw)
    if kind in EXACT_PARA1:
        return para1 in ids
    return 0 in ids or para1 in ids


# Missões sociais e de guilda (QuestCondictionInfos.CondictionType)
# (cliente) TaskTemplate.as: os tipos 21, 22, 29 e 51 conferem o estado, não a contagem
FRIEND_CONDITION = 21  # ter amigo: checkFriendsCount, tamanho da lista de amigos
# estar em guilda: checkJoinConsortia, consortiaID > 0. (visto) oficial_20261023-171155-1: o servidor não conta, o
# condition_1 fica 0 na entrada da guilda (sem 112) e na entrega (#4218, #4919); ``quest_done`` lê a guilda agora
GUILD_JOIN_CONDITION = 22
OFFER_CONDITION = 29  # contribuição total: checkConsortiaOffer, consortiaTotalOffer >= Para2
GUILD_LEVEL_CONDITION = 51  # nível da guilda: checkConsortuaGrade; Para1 = prédio (GUILD_LEVEL_ATTRS)
# (visto) tempinfos QuestTemps 241 Detail: [Guild] > [Guild Territory] > [Altar] > [spin] = altar (5145)
BLESS_CONDITION = 30  # bênção do altar, uma por dia (5145)
# (visto) tempinfos QuestTemps 260 = própria (Para1 1); 22, 261 e 271 = de amigo (Para1 0)
TREE_CONDITION = 20  # regar a árvore (15017); (só turco) captura #5 de ciftlik.json é a própria
# (visto) tempinfos QuestTemps 825 Detail: [Market] > Auction any item = pôr à venda (8448)
SELL_CONDITION = 56  # pôr item no leilão (8448), +1 por anúncio
# (visto) tempinfos QuestTemps 857 Detail: [Academy] > [Blessing Wheel] > Start the [Blessing Wheel];
# (cliente) SeminaryBlessFrame.as manda 8489 no confirmar
SEMINARY_CONDITION = 57  # bênção do seminário (8489)
# Masmorra (campanha): só o servidor sabe quando o jogador passou; (cliente) TaskTemplate.as checkCount só lê o contador
CAMPAIGN_CONDITION = 14  # passar a campanha Para1 (CampaignId, ex. 70 -> 1001); (visto) inglês #1098 -> #1103
# (visto) tempinfos: a 80 pede o chefe 1011 ('Wulfgar') na campanha 1001 (Para3); (visto) inglês #1513: o 112 do chefe
HERO_KILL_CONDITION = 26  # matar o chefe Para1 (GameHeroTemp); Para3 = campanha
# (dedução) 25 conta os soldados do lado 2 da batalha vencida pelo tempId; nenhuma missão de 25 aponta para a 1001
PAWN_KILL_CONDITION = 25  # matar Para2 soldados do tipo Para1 (PawnTempInfos) numa campanha
SOLO_CONDITION = 31  # passar cena com Para1 jogadores (Campaigns.Capacity); (visto) tempinfos: 313 = 1, 371 = 2
# Os de nível guardam o maior valor: evoluir tropa até Para2 (10) e os que o cliente confere pelo estado
# 63: Devotion (total da atividade diária); 78: grau do símbolo; 14: passou a campanha (um sim, não soma)
LEVEL_CONDITIONS = {
    10,
    63,
    RUNE_GRADE,
    FRIEND_CONDITION,
    GUILD_JOIN_CONDITION,
    OFFER_CONDITION,
    GUILD_LEVEL_CONDITION,
    CAMPAIGN_CONDITION,
}
# (visto) tempinfos: QuestConditionInfo 121, tipo 17, Para1 2; Detail "3 lv": grau > Para1
MIN_CONDITIONS = {17}
# Para1 0 não é coringa aqui: regar a própria (1) não avança as de amigo (0); colher (60): 0 a própria fazenda
# (263/860), 1 roubar na de amigo (266/861)
EXACT_PARA1 = {TREE_CONDITION, 60}
# Para1 de 51 -> Consortia: (cliente) TaskTemplate.as checkConsortuaGrade, Para1 1-5 = levels, shopLevel,
# altarLevel, schoolLevel, storeLevel (mesma numeração de guild.LEVEL_TYPES; 6-12 são pesquisas, fora da 51)
GUILD_LEVEL_ATTRS = {1: "levels", 2: "shop_level", 3: "altar_level", 4: "school_level", 5: "store_level"}


def social_state_quests(snap: PlayerSnapshot, templates: GameTemplates, guild: Consortia | None) -> list[Quest]:
    """Missões que o cliente confere pelo estado (amigos, guilda, contribuição, nível da guilda): sobe o
    progresso até o valor atual. Chamado no 5014: o cliente mostra a missão cumprida quando o estado bate,
    então o servidor precisa do mesmo progresso para concluir (e para quem agiu offline ou antes de aceitar)."""
    changed = quest_event(snap, templates, FRIEND_CONDITION, 0, len(snap.relations))
    changed += quest_event(snap, templates, OFFER_CONDITION, 0, snap.character.consortia_total_offer)
    if guild is not None:
        for kind, attr in GUILD_LEVEL_ATTRS.items():
            changed += quest_event(snap, templates, GUILD_LEVEL_CONDITION, kind, getattr(guild, attr))
    return changed


PLAYER_LEVEL_CONDITION = 1  # nível do jogador >= Para2, lido na hora (cliente: TaskTemplate.checkPlayerGrades)
LOGIN_DAY_CONDITION = 39  # entrar num dia diferente do da aceitação (cliente: checkSencondLogin)
TALK_CONDITION = 85  # falar com o NPC do nó Para4 ("mapa,nó"): vem do 8692 ou do aceite (cliente: finishStory)
# Tipos sem gancho (quem tem o sistema chama quest_event); nenhum pacote no cliente nem nas capturas para 33 e 48
MINI_CLIENT_CONDITION = 33  # "Login/Use Mini-client" (missões 1 e 150); sem pacote nem texto no cliente: pendente
CATACOMBS_CONDITION = 38  # passar a Forgotten Catacombs (Para1 8001, Para2 = vezes): gancho em campaign.py
WORLDBOSS_DAMAGE_CONDITION = 41  # dano total no chefe mundial (missão 762, Para2 50000): gancho em worldboss.py
BATTLEGROUND_JOIN_CONDITION = 44  # entrar numa battleground (758, 766): sistema de battleground ainda não existe
BATTLEGROUND_KILL_CONDITION = 45  # kills na battleground (16, 767): idem
PHONE_CONDITION = 48  # cadastro de celular (missão 816): sem pedido no cliente nem nas capturas: pendente
BATTLEGROUND_WIN_CONDITION = 50  # vitória na battleground / war camp (18, 818): idem
AMETHYST_CONDITION = 86  # Amethyst Rush (503): cada coleta na pilha da mina (warfield.callback, 5032 cmd 2)
# (visto) tempinfos QuestTemps Detail de cada missão; +1 por ação, Para1 0 salvo indicação
ALCHEMY_CONDITION = 64  # 184 "Use Alchemy 3 times": alquimia de ouro (vip.alchemy, 8321)
DARU_ALCHEMY_CONDITION = 65  # 185 "Use Daru Alchemy 3 times": alquimia de Daru (vip.soul, 8467)
SPIRE_CONDITION = 74  # 799 "Enter [The Spire]": entrada que gasta a vez do dia (campaign, torres.SPIRE)
TANK_JOIN_CONDITION = 79  # 912 (Para1 0) e 914 (Para1 3001): entrar na batalha de tanques (vehicle.match_up)
TANK_WIN_CONDITION = 80  # 913 e 915: vencer a batalha de tanques (vehicle.settle; empate BOTH conta para os dois)
EXPLORE_CONDITION = 91  # 930 "Click Explore -> Go on an exploration": 9502 op 3 (treasure_hunt)
RESIST_CRYSTAL_CONDITION = 90  # 926 "Socket Resistance Crystal": gema 101..106 na guarda de batalha (tower, 8742)
LOST_TREASURE_CONDITION = 89  # 925 "Lost Treasure": entrar na luta do mapa do tesouro (8744 op 3/5, reforço 8745)
ARENA_PARTY_CONDITION = 16  # 421/422 "Arena (Party)": cada luta da sala PvP, vitória ou derrota (arena_grupo)
# Sem a ação no servidor (contam quando ela existir):
# TODO(58): "Soul Engraving" 858: o cliente decompilado só tem GoodsSonType SOUL_CRYSTAL 293, sem tela nem pacote
ENGRAVE_CONDITION = 58
# TODO(93): "Win a Sky Trail battle" 932 (General William, Cloud City): sistema não identificado; (dedução) candidato
# as fases do SinglePass (8753/8755), que não existem (handlers/singlepass.py)
SKY_TRAIL_CONDITION = 93
PROGRESS_FIELDS = ("progress", "progress_2", "progress_3", "progress_4")  # condition_1..4 do 112
# bolsa: quantidade do item Para1 (templateId) >= Para2 (cliente: checkGoodsCount). O condition_N fica em 0: (visto)
# captura EN, a 90 e a 102 só têm 112 com 0 (#1140, #1572, #1800, #2081), nem nos drops do Worg Tooth (#1276, #1408)
GOODS_CONDITIONS = {27, 28, 32, 49}
# (visto) só estes tipos mandam o 112 do progresso antes da entrega (5014): captura EN 23 (#211), 2 (#631), 10 (#2180);
# oficial_20261023-171155-1 21 (#4274, missão 200), 29 (#4978, 221) e 51 (#5889, 819). Sem ele: 8, 20, 22, 26, 27, 42
PROGRESS_BEFORE_FINISH = {NOVICE_CONDITION, BUILDING_CONDITION, 10, 21, 29, 51}
QUEST_GOODS_SON = "210"  # SonType do item só de missão (2100001): a entrega tira todas as unidades (goods_to_take)
# (cliente) newbie.xml (espelho inglês res134 ui/zh_cn), saveId: o maior salto do guia é 28500 -> 32000 (3500)
# ponytail: teto de salto em vez da lista exata de saveId; a lista seria o próximo passo
NOVICE_STEP_MAX = 3500
NOVICE_FIRST_MAX = 11000  # (cliente) primeiro saveId do newbie.xml; de noviceProcess 0 o avanço não passa daqui


def conditions(templates: GameTemplates, template_id: int) -> list[Row]:
    """Linhas de QuestCondictionInfos da missão, na ordem do arquivo. A N-ésima é condition_N no 112: o cliente
    lê ``taskInfo["condition" + (i + 1)]`` para a i-ésima linha (TaskTemplate.checkCount) e só conclui com todas.

    ponytail: busca linear nas 352 linhas a cada chamada; indexar por TemplateId em GameTemplates se pesar.
    """
    return list(templates.find("QuestCondictionInfos", TemplateId=template_id))


def progress_of(q: Quest, k: int) -> int:
    return int(getattr(q, PROGRESS_FIELDS[k]))


def set_progress(q: Quest, k: int, value: int) -> None:
    setattr(q, PROGRESS_FIELDS[k], value)


def quest_goods_wanted(snap: PlayerSnapshot, templates: GameTemplates, template_id: int, campaign_id: int) -> bool:
    """O drop ``template_id`` na campanha sai? Item de missão de coleta (tipo 27 com Para3 = a campanha) só com a
    missão aberta: (visto) oficial_20261023-171155-1, Perene Bone (190) só na 2ª volta da 1003, depois do aceite
    (#2949), e nenhum nas lutas depois da entrega (#3558: 103103, 103104, 103106); os outros drops saem sempre.
    (dedução) para na entrega: o 5º (Para2) veio antes dela, então a captura não separa "missão fechada" de "já tem
    os 5"."""
    quests = {
        int(c["TemplateId"])
        for c in templates.find("QuestCondictionInfos", CondictionType=27, Para1=template_id, Para3=campaign_id)
    }
    return not quests or any(q.template_id in quests and not q.completed for q in snap.quests)


def goods_count(snap: PlayerSnapshot, template_id: int) -> int:
    """Unidades do item na mochila, como ``goodsCountByTempId`` no cliente (TaskTemplate.checkGoodsCount)."""
    return sum(i.count for i in snap.items if i.bag_type == BagType.BAG and i.template_id == template_id)


def arm_avatar(snap: PlayerSnapshot, templates: GameTemplates) -> str:
    """``ArmyArmyMsg.arm``: arte da arma equipada (``/wizard_arms002``)."""
    return next((r.get("Avata", "") for r in equipment(snap, templates) if r.get("SonType") == WEAPON), "")


def cloth_avatar(snap: PlayerSnapshot, templates: GameTemplates) -> str:
    """``RoomPlayerMsg.cloth``: arte da armadura equipada (``/warrior_body023``)."""
    return next((r.get("Avata", "") for r in equipment(snap, templates) if r.get("SonType") == CLOTH), "")


def grade_steps(templates: GameTemplates, types: str = PLAYER_GRADE) -> list[tuple[int, int]]:
    """``(nível, EXP total para chegar nele)`` em ordem, da tabela ``UpGradeTempInfos`` de ``types``."""
    rows = sorted((int(r["Grades"]), int(r["Data"])) for r in templates.find("UpGradeTempInfos", Types=types))
    steps, total = [], 0
    for grade, data in rows:
        total += data
        steps.append((grade, total))
    return steps


EXP_BONUS = {"min_grade": 40, "world_percent": 1000}  # ``game_settings.exp_bonus`` (migração 0081)


def exp_bonus(c: Character, settings: Mapping[str, Any], base: int) -> tuple[int, int, int]:
    """EXP de luta e de missão com os bônus do oficial: ``(total, mundo, descansada)``. (só turco: transfer_kampi #23,
    peri_uyanis #82, meydan_okuma #27, peri_turnuvasi #71, yeralti_labirenti #22/#78) a EXP do mundo é 10x a base em
    todos e a descansada dobra base + mundo, gasta do ``leave_gp`` (o leaveGp cai exatamente isso: transfer_kampi
    #17 -> #20 -220.000, yeralti #7 -> #13 -4.400). O inglês (níveis 1 a 19) não tem nenhum dos dois e o leaveGp fica
    0. TODO(inventado): o nível ``min_grade`` em que os dois começam (entre 20 e 80)."""
    rule = EXP_BONUS | dict(settings.get("exp_bonus") or {})
    if base <= 0 or c.grades < int(rule["min_grade"]):
        return max(base, 0), 0, 0
    world = base * int(rule["world_percent"]) // 100
    rested = min(c.leave_gp, base + world)
    c.leave_gp -= rested
    return base + world + rested, world, rested


def exp_text(gp: int, world: int = 0, rested: int = 0) -> str:
    """(visto) captura EN #218, #506, #909: "Received 3,000 EXP ", com vírgula de milhar e o espaço no fim. Com bônus,
    (só turco: "220,000 EXP kazanıldı(Dahil100,000 Dünya EXP,110,000 çevrimdışı EXP)", peri_turnuvasi #71)
    TODO(inventado): a tradução inglesa, que nenhuma captura inglesa mostra."""
    if world or rested:
        return f"Received {gp:,} EXP (Including {world:,} World EXP, {rested:,} Offline EXP)"
    return f"Received {gp:,} EXP "


def rest(c: Character, settings: Mapping[str, Any], gp: int) -> None:
    """O tempo offline vira EXP descansada do nível ``min_grade`` em diante. TODO(inventado): quanto acumula
    (usa ``gp``, a conta do ``timebox.offline_gp``)."""
    rule = EXP_BONUS | dict(settings.get("exp_bonus") or {})
    if gp > 0 and c.grades >= int(rule["min_grade"]):
        c.leave_gp += gp
        c.offline_seconds = 0


def add_gp(snap: PlayerSnapshot, templates: GameTemplates, gp: int) -> int:
    """Soma EXP ao jogador; sobe o nível dele e do líder. Devolve quantos níveis subiu."""
    c, leader = snap.character, snap.leader
    c.total_gp += gp
    grade, floor = 1, 0
    for g, need in grade_steps(templates):
        if c.total_gp < need:
            break
        grade, floor = g, need
    gained = grade - c.grades
    c.grades, c.gp = grade, c.total_gp - floor
    if leader is not None and gained > 0:
        leader.grades = grade
        leader.hp = 0  # subir de nível enche a vida sem a reserva (oficial_20261023-153200-1 #2132: 530 -> 560)
        refresh_skill_point(leader, templates)
        for attr, per_level in GROWTH[job_type(c.job)].items():
            setattr(leader, attr, getattr(leader, attr) + per_level * gained)
            setattr(leader, f"{attr}_point", getattr(leader, f"{attr}_point") + per_level * gained)
        top_up_army(snap, templates)
    return gained


def top_up_army(snap: PlayerSnapshot, templates: GameTemplates) -> None:
    """Subiu de nível: completa o exército até a liderança nova com soldados do castelo do mesmo tipo. (visto) EN
    #1132/#1133 e #1587/#1588: a liderança sobe 10, o castelo cai 10 (748 -> 738) e o exército sobe 10
    (152 -> 162). Sem ninguém no exército, o tipo é o primeiro do castelo (*dedução*: as capturas só têm esse caso
    com o castelo vazio). Quem chama ``add_gp`` grava ``snap.pawns``; o que faltou vira o 139 (``handlers.player``)."""
    pawn = army_pawn(snap) or next(iter(snap.pawns), None)
    if pawn is not None and snap.leader is not None:
        # ponytail: sem a poção de Captain (add_gp não recebe a hora); passar now por add_gp/grant se pesar
        moved = max(0, min(leader_stats(snap, templates, None).total["ConatArmy"] - pawn.army_count, pawn.castle_count))
        pawn.castle_count, pawn.army_count = pawn.castle_count - moved, pawn.army_count + moved


def trim_army(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> bool:
    """A liderança caiu (tirar equipamento): o que passa dela volta ao castelo. (visto) oficial_20261023-171155-1
    #2310-#2314: exército 218 -> 212, castelo 769 -> 775. Devolve se mexeu (quem chama grava ``snap.pawns``)."""
    pawn = army_pawn(snap)
    if pawn is None or snap.leader is None:
        return False
    extra = pawn.army_count - leader_stats(snap, templates, now).total["ConatArmy"]
    if extra <= 0:
        return False
    pawn.army_count, pawn.castle_count = pawn.army_count - extra, pawn.castle_count + extra
    return True


def skill_grades(templates: GameTemplates, script: str) -> int:
    return sum(int((templates.get("SkillTempInfos", int(t)) or {}).get("Grades", 0)) for t in script.split(",") if t)


def skill_points(hero: Hero, templates: GameTemplates, script: str) -> int:
    """1 ponto a cada 2 níveis, já contando as skills iniciais (nível 6 com 2 skills = 1: visto)."""
    return max(0, hero.grades // 2 - skill_grades(templates, script))


def active_script(hero: Hero) -> str:
    return hero.skill_script2 if hero.skill_index == 1 else hero.skill_script


def refresh_skill_point(hero: Hero, templates: GameTemplates) -> None:
    hero.skill_point = skill_points(hero, templates, active_script(hero))


def talent_points(hero: Hero, templates: GameTemplates) -> int:
    """1 ponto por grau de talento menos o que já foi aprendido."""
    return max(0, hero.talent_grade - skill_grades(templates, hero.talent_script))


def ever_completed(q: Quest) -> bool:
    """Já foi concluída alguma vez. O bit do ``states`` continua ligado quando a repetível reabre
    (só turco: login.json #89, id 241 aberta com o bit 1), e a pré-missão do cliente (checkPreTask, IsTaskFinish)
    lê esse bit."""
    return q.completed or q.completed_at is not None


def quest_bitmap(snap: PlayerSnapshot) -> bytes:
    """``questSite``/``states``: bit ``id-1`` (LSB primeiro) de cada missão já concluída."""
    bits = bytearray(QUEST_SITE_LEN)
    for q in snap.quests:
        if ever_completed(q) and 0 < q.template_id <= QUEST_SITE_LEN * 8:
            bits[(q.template_id - 1) // 8] |= 1 << ((q.template_id - 1) % 8)
    return bytes(bits)


def quest(snap: PlayerSnapshot, template_id: int) -> Quest | None:
    return next((q for q in snap.quests if q.template_id == template_id), None)


def _utc(value: datetime) -> datetime:
    """Relógio em UTC sem fuso, para comparar com StartDate e EndDate (o cliente usa o tempo do servidor)."""
    return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value


def _template_time(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")


def _game_day(value: datetime) -> date:
    return gameday.game_day(value if value.tzinfo else value.replace(tzinfo=UTC))


def _pre_done(snap: PlayerSnapshot, templates: GameTemplates, pre_id: str) -> bool:
    """(cliente) TaskManage.checkPreTask: pré-requisito que não existe nos templates é ignorado (getTaskByID nulo)."""
    if templates.get("QuestTemps", int(pre_id)) is None:
        return True
    pre = quest(snap, int(pre_id))
    return pre is not None and ever_completed(pre)


def can_accept(snap: PlayerSnapshot, templates: GameTemplates, row: Row, now: datetime, in_guild: bool) -> bool:
    """Regras de TaskManage.isAvailableTask no servidor: janela de datas, nível (NeedMinLevel..NeedMaxLevel),
    guilda (IsLeague) e pré-requisitos (lista com vírgula é E). NeedItemTemp, NeedBuildingTemp e NeedPos são 0 em
    todas as linhas, então não têm regra. Missão aberta e repetição ficam em ``accept_quest``."""
    if not _template_time(row["StartDate"]) <= _utc(now) <= _template_time(row["EndDate"]):
        return False
    if not int(row["NeedMinLevel"]) <= snap.character.grades <= int(row["NeedMaxLevel"]):
        return False
    if row.get("IsLeague") == "true" and not in_guild:
        return False
    return all(_pre_done(snap, templates, pre) for pre in row.get("PreQuestId", "").split(",") if pre)


def is_repeat(templates: GameTemplates, template_id: int) -> bool:
    return (templates.get("QuestTemps", template_id) or {}).get("IsRepeat") == "true"


def _repeat_ok(row: Row, q: Quest, now: datetime) -> bool:
    """Repetível concluída volta a aceitar quando o dia do jogo mudou desde a conclusão (cliente: checkRepeatMax
    com checkInRepeatTime). RepeatMax é 1 em todas as linhas e repeatFinish fica 1, como o oficial manda."""
    return row.get("IsRepeat") == "true" and q.completed_at is not None and _game_day(q.completed_at) != _game_day(now)


def accept_quest(
    snap: PlayerSnapshot, templates: GameTemplates, template_id: int, now: datetime, in_guild: bool
) -> tuple[Quest, list[Quest]] | None:
    """Aceita a missão se o cliente também aceitaria (``can_accept``) e ela não está aberta. Repetível concluída
    volta a abrir na mesma linha (a tabela tem uma linha por personagem e missão). Devolve a missão e as que a
    aceitação mudou (tutorial, prédio, estado): quem chama grava e manda todas."""
    row = templates.get("QuestTemps", template_id)
    if row is None:
        return None
    q = quest(snap, template_id)
    if q is not None and not (q.completed and _repeat_ok(row, q, now)):
        return None
    if not can_accept(snap, templates, row, now, in_guild):
        return None
    if q is None:
        q = Quest(snap.character.id or 0, template_id, now)
        snap.quests.append(q)
    else:
        q.completed, q.added_at = False, now
        q.progress = q.progress_2 = q.progress_3 = q.progress_4 = 0
    changed = [q, *update_novice_quests(snap, templates), *update_building_quests(snap, templates)]
    changed += update_state_quests(snap, templates, [q])
    return q, changed


def update_novice_quests(snap: PlayerSnapshot, templates: GameTemplates) -> list[Quest]:
    """Missões do tutorial (condição tipo 23) que passaram a cumprir a condição."""
    changed = []
    for q in snap.quests:
        if q.completed:
            continue
        for k, cond in enumerate(conditions(templates, q.template_id)):
            if int(cond["CondictionType"]) != NOVICE_CONDITION or progress_of(q, k):
                continue
            if snap.character.novice_process > int(cond["Para1"]):
                set_progress(q, k, int(cond["Para2"]))
                if q not in changed:
                    changed.append(q)
    return changed


def novice_pushes(templates: GameTemplates, q: Quest) -> bool:
    """O 112 do progresso tipo 23 sai sem pedido só com ``Para3`` 1. *(dedução)*: o cliente não lê o ``Para3``; no
    tutorial_en as missões 10-45 (``Para3`` 1) mandam o 112 no 5017 e a 50 (``Para3`` 0) não (#584)."""
    return any(
        int(c["CondictionType"]) == NOVICE_CONDITION and c.get("Para3") == "1"
        for c in conditions(templates, q.template_id)
    )


def update_building_quests(snap: PlayerSnapshot, templates: GameTemplates) -> list[Quest]:
    """Missões "evolua o prédio X" (tipo 2) cujo progresso mudou: vale o nível atual do prédio."""
    grades: dict[str, int] = {}
    for building in snap.buildings:
        row = templates.get("BuildingTempInfos", building.template_id)
        if row is not None:
            grades[row["SonType"]] = max(grades.get(row["SonType"], 0), int(row["BuildingGrade"]))
    changed = []
    for q in snap.quests:
        if q.completed:
            continue
        for k, cond in enumerate(conditions(templates, q.template_id)):
            if int(cond["CondictionType"]) != BUILDING_CONDITION:
                continue
            grade = min(grades.get(cond["Para1"], 0), int(cond["Para2"]))
            if grade != progress_of(q, k):
                set_progress(q, k, grade)
                if q not in changed:
                    changed.append(q)
    return changed


def learned_runes(snap: PlayerSnapshot, templates: GameTemplates) -> list[Row]:
    """Linhas de RuneTempInfos dos símbolos do herói (o id gravado é o grau atual)."""
    leader = snap.leader
    ids = [int(r.split(":")[0]) for r in leader.runes.split(",") if r] if leader is not None else []
    return [row for rid in ids if (row := templates.get("RuneTempInfos", rid)) is not None]


def update_state_quests(snap: PlayerSnapshot, templates: GameTemplates, quests: list[Quest]) -> list[Quest]:
    """Missões de estado: o cliente (TaskTemplate.checkMapId, checkRuneStudy, checkRuneGrade) julga pelo que
    já existe, não pelo ato. Quem aceita depois do fato já nasce com o progresso dele (como as de prédio)."""
    changed = []
    runes = learned_runes(snap, templates)
    for q in quests:
        if q.completed:
            continue
        for k, cond in enumerate(conditions(templates, q.template_id)):
            kind, para2 = int(cond["CondictionType"]), int(cond["Para2"])
            old = progress_of(q, k)
            if kind == MAP_CONDITION:  # vale o mapa de agora: sair dele desfaz (checkMapId)
                here = snap.castle is not None and snap.castle.map_id == para2
                value = para2 if here else 0
            elif kind in (RUNE_STUDY, RUNE_GRADE):
                para1 = int(cond["Para1"])  # só aqui: o Para1 de outros tipos pode ser lista (14 e 26)
                mine = [r for r in runes if para1 in (0, int(r["RuneType"]))]
                value = len(mine) if kind == RUNE_STUDY else max((int(r["RuneGrade"]) for r in mine), default=0)
                value = max(value, old)
            else:  # bolsa (GOODS_CONDITIONS) fica em 0: o cliente conta a mochila (checkGoodsCount), quest_done também
                continue
            if value != old:
                set_progress(q, k, value)
                if q not in changed:
                    changed.append(q)
    return changed


def quest_done(snap: PlayerSnapshot, templates: GameTemplates, q: Quest, now: datetime, in_guild: bool = False) -> bool:
    """Concluída quando todas as condições batem, como no cliente. Nível do jogador, dia do login, bolsa e guilda são
    lidos agora; os de contagem usam o contador gravado (condition_N). Sem linha de condição não conclui: nenhuma
    missão dos dados está assim, e o cliente a acharia pronta sem nada a cumprir."""
    rows = conditions(templates, q.template_id)
    if not rows:
        return False
    for k, cond in enumerate(rows):
        kind, need = int(cond["CondictionType"]), int(cond.get("Para2", "1"))
        if kind == PLAYER_LEVEL_CONDITION:
            have = snap.character.grades
        elif kind == LOGIN_DAY_CONDITION:  # dia em UTC, o mesmo fuso do addDate mandado no 112
            have = int(_game_day(now) > _game_day(q.added_at))
        elif kind in GOODS_CONDITIONS:
            have = goods_count(snap, int(cond["Para1"]))
        elif kind == GUILD_JOIN_CONDITION:
            have = int(in_guild)
        else:
            have = progress_of(q, k)
        if have < need:
            return False
    return True


def finish_progress(snap: PlayerSnapshot, templates: GameTemplates, q: Quest) -> bool:
    """Na entrega já aceita: o tipo 23 grava o noviceProcess de agora (visto: captura EN #211, 12000 na 10; #483, 18500
    na 45). Devolve se a missão manda o 112 do progresso antes da conclusão (``PROGRESS_BEFORE_FINISH``)."""
    first = False
    for k, cond in enumerate(conditions(templates, q.template_id)):
        kind = int(cond["CondictionType"])
        if kind == NOVICE_CONDITION:
            set_progress(q, k, snap.character.novice_process)
        first = first or kind in PROGRESS_BEFORE_FINISH
    return first


def goods_to_take(snap: PlayerSnapshot, templates: GameTemplates, template_id: int) -> list[tuple[int, int]]:
    """(templateId, quantidade) que a entrega consome, de cada condição de bolsa. (visto) inglês #1397 -> #1570: o
    2100001 (SonType 210, item de missão) saiu inteiro, 10 unidades, na entrega da 90, cuja condição pede 8. Por isso
    esse tipo tira tudo. (dedução) Os demais (comprados ou de receita) só a quantidade pedida, para não zerar a reserva
    do jogador; a captura não cobre esse caso."""
    take: list[tuple[int, int]] = []
    for cond in conditions(templates, template_id):
        if int(cond["CondictionType"]) in GOODS_CONDITIONS:
            tid = int(cond["Para1"])
            have = goods_count(snap, tid)
            son = (templates.get("ItemTempInfos", tid) or {}).get("SonType")
            take.append((tid, have if son == QUEST_GOODS_SON else min(have, int(cond["Para2"]))))
    return take


def pay_quest_rewards(
    snap: PlayerSnapshot, templates: GameTemplates, row: Row, settings: Mapping[str, Any] | None = None
) -> tuple[int, int, int, int]:
    """Paga EXP (com o bônus diário), ouro, RewardStrategy (Daru), RewardCrystal e RewardPlayerOffer, como a tela do
    cliente (TaskRewardViewII._rewardList). Os itens (QuestGoods) são de quem chama, que confere a mochila. Devolve
    ``(EXP, RewardConsortiaOffer, EXP do mundo, EXP descansada)`` (``exp_bonus``; a EXP já com os dois): quem chama
    credita a oferta da guilda se o jogador tiver guilda. RewardMoney,
    RewardHeroGP e RewardDower não são pagos: a tela não mostra o primeiro (só a missão 1, expirada) e os outros dois
    são 0 em todas as linhas."""
    c = snap.character
    gp = int(row.get("RewardPlayGP", 0))
    if gp > 0 and row.get("TemplateType") == "1":  # bônus diário que a tela soma (TaskRewardViewII.as:207-209)
        gp += (c.grades - int(row["NeedMinLevel"])) * 500
    gp, world, rested = exp_bonus(c, settings or {}, gp)
    add_gp(snap, templates, gp)
    c.gold += int(row.get("RewardGold", 0))
    c.strategy += int(row.get("RewardStrategy", 0))
    c.crystals += int(row.get("RewardCrystal", 0))
    offer = int(row.get("RewardPlayerOffer", 0))
    c.consortia_offer += offer
    c.consortia_total_offer += offer
    return gp, int(row.get("RewardConsortiaOffer", 0)), world, rested


def novice_step_ok(current: int, new: int) -> bool:
    """(cliente) ``sendSaveProcess`` só manda múltiplo de 100 positivo; a ordem é a do guia. Aceita um passo plausível
    (até ``NOVICE_STEP_MAX``); de noviceProcess 0 (conta nova) o primeiro passo vai até ``NOVICE_FIRST_MAX``."""
    if new <= current or new % 100:
        return False
    return new <= (NOVICE_FIRST_MAX if current == 0 else current + NOVICE_STEP_MAX)


def talk_nodes(templates: GameTemplates, template_id: int) -> list[int]:
    """Nós (NPCs) das condições de conversa (85) da missão: o Para4 é "mapa,nó"."""
    rows = conditions(templates, template_id)
    return [int(c["Para4"].partition(",")[2]) for c in rows if c["CondictionType"] == str(TALK_CONDITION)]


def talk_event(
    snap: PlayerSnapshot, templates: GameTemplates, target: str, only: Sequence[Quest] | None = None
) -> list[Quest]:
    """Conversa com o alvo "mapa,nó": a condição 85 cujo Para4 é esse alvo vira 1 (uma vez basta). ``only``
    limita às missões recém aceitas; sem ele, vale para todas as abertas."""
    changed = []
    for q in snap.quests if only is None else only:
        if q.completed:
            continue
        hit = False
        for k, cond in enumerate(conditions(templates, q.template_id)):
            if cond["CondictionType"] == str(TALK_CONDITION) and cond["Para4"] == target and not progress_of(q, k):
                set_progress(q, k, 1)
                hit = True
        if hit:
            changed.append(q)
    return changed


def quest_rewards(
    snap: PlayerSnapshot, templates: GameTemplates, template_id: int
) -> tuple[Row, list[tuple[int, int]]]:
    """Template da missão e os itens de recompensa (templateId, quantidade) da classe do jogador."""
    row = templates.get("QuestTemps", template_id)
    assert row is not None
    jt = job_type(snap.character.job)
    goods = [
        (int(g["RewardItemID"]), int(g["RewardItemCount"]))
        for g in templates.find("QuestGoods", TemplateId=template_id)
        if int(g.get("ToJob", "0")) in (0, jt)
    ]
    return row, goods


def pay_soul(c: Character, cost: int) -> bool:
    if cost < 0 or c.strategy < cost:
        return False
    c.strategy -= cost
    return True


def bag_count(snap: PlayerSnapshot, templates: GameTemplates, son_type: str) -> int:
    return sum(i.count for i in bag_items(snap, templates, son_type))


def bag_items(snap: PlayerSnapshot, templates: GameTemplates, son_type: str) -> list[Item]:
    """Itens da mochila com esse ItemTempInfo.SonType, por posição (os da frente são gastos antes)."""
    found = []
    for item in sorted(snap.items, key=lambda i: i.pos):
        row = templates.get("ItemTempInfos", item.template_id)
        if item.bag_type == BagType.BAG and row is not None and row.get("SonType") == son_type:
            found.append(item)
    return found


def take_items(snap: PlayerSnapshot, items: list[Item], count: int) -> tuple[list[Item], list[Item]]:
    """Gasta ``count`` unidades de ``items`` (já no snapshot). Devolve ``(alterados, apagados)``; quem
    chama confere antes que há o bastante e grava os dois numa save só."""
    changed, deleted = [], []
    for item in items:
        if count <= 0:
            break
        used = min(count, item.count)
        item.count -= used
        count -= used
        if item.count == 0:
            snap.items.remove(item)
            deleted.append(item)
        else:
            changed.append(item)
    return changed, deleted


def config(templates: GameTemplates, name: str, default: str = "0") -> str:
    row = next(templates.find("ConfigInfos", ConfigName=name), None)
    return row["ConfigValue"] if row else default


def copies_base(templates: GameTemplates) -> int:
    """Entradas de campanha em grupo por dia sem item (``ConfigInfos`` MultiCampaign_MaxCount = 1)."""
    return int(config(templates, "MultiCampaign_MaxCount", "1"))


def upgrade_row(templates: GameTemplates, types: str, grade: int) -> Row | None:
    """UpGradeTempInfo de ``Types`` no grau ``grade`` (tabelas de custo/EXP por nível)."""
    return next(templates.find("UpGradeTempInfos", Types=types, Grades=grade), None)


def free_bag_pos(snap: PlayerSnapshot) -> int:
    used = {i.pos for i in snap.items if i.bag_type == BagType.BAG}
    return next(p for p in range(len(used) + 1) if p not in used)
