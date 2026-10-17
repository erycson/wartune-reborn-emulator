"""Regras de progressão aplicadas ao ``PlayerSnapshot`` em memória: EXP e nível, crescimento do
herói, equipamentos, missões. Quem chama grava as entidades alteradas (``CharacterService.save``).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..domain.models import (
    BagType,
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
from .builders.login import QUEST_SITE_LEN, HeroStats

PLAYER_GRADE = "3"  # UpGradeTempInfo.Types do nível do jogador; Data = EXP do nível anterior até este
NOVICE_CONDITION = 23  # QuestConditionInfo: noviceProcess > Para1
BUILDING_CONDITION = 2  # QuestConditionInfo: prédio SonType Para1 no nível Para2 (progresso = nível atual)
WEAPON, CLOTH = "101", "104"  # ItemTempInfo.SonType
WING, HAT, FASHION_CLOTH, FASHION_ARM = "109", "110", "112", "111"
HERO_BAGS = (BagType.RUNE, BagType.HONOR, BagType.HERO)  # bolsas do herói que somam atributos

# ganho de atributos por nível, por JobType (1 guerreiro, 2 caçador, 3 mago). O mago foi medido na
# captura (níveis 1, 3 e 5); ponytail: guerreiro e caçador são o espelho dele, trocar quando houver captura.
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
    return rows


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
    day = (now - timedelta(hours=5)).strftime("%Y-%m-%d")
    if sy.star_day != day:
        sy.star_day, sy.star_free = day, 1


MOUNT_ATTRS = ("Power", "Intellect", "Physique", "Agility")  # ordem de PlayerSystems.mount_gp
MOUNT_GRADE = "18"  # UpGradeTempInfo.Types: EXP acumulada de cada atributo da montaria


def mount_grade(templates: GameTemplates, gp: int, cap: int) -> int:
    steps = sorted((int(r["Grades"]), int(r["Data"])) for r in templates.find("UpGradeTempInfos", Types=MOUNT_GRADE))
    return min(cap, max((g for g, need in steps if gp >= need), default=0))


def mount_stats(snap: PlayerSnapshot, templates: GameTemplates) -> dict[str, int]:
    """Atributos da montaria em uso: valor do template + 5 por grau (conferido na captura de login:
    1610 de EXP = grau 11 = 10 + 55 de força)."""
    sy = systems(snap)
    tpl = templates.get("MountTempInfos", sy.mount_template) if sy.mount_template else None
    if tpl is None:
        return {}
    cap = mount_level_max(tpl)
    gps = [int(x) for x in sy.mount_gp.split(",")]
    return {a: int(tpl.get(a, 0)) + 5 * mount_grade(templates, gp, cap) for a, gp in zip(MOUNT_ATTRS, gps, strict=True)}


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


def leader_stats(snap: PlayerSnapshot, templates: GameTemplates) -> HeroStats:
    """Atributos do líder: herói + equipamentos + montaria + estrelas equipadas.

    Talento, runas, destino e alma do dragão não somam atributo fixo: nos templates eles são
    skills/buffs (SkillTempInfos/TalentEffectTempInfos) que agem na batalha.
    """
    leader = snap.leader
    assert leader is not None
    bonuses = equipment(snap, templates) + star_bonuses(snap, templates)
    if mount := mount_stats(snap, templates):
        bonuses.append({k: str(v) for k, v in mount.items()})
    return HeroStats.of(leader, templates.hero(leader.template_id), bonuses)


HOUSE, BARRACKS = "1201", "402"  # BuildingTempInfo.SonType


def building_row(snap: PlayerSnapshot, templates: GameTemplates, son_type: str) -> Row | None:
    """Template do prédio do jogador com esse SonType (casa, quartel...)."""
    for b in snap.buildings:
        row = next(templates.find("BuildingTempInfos", TemplateId=b.template_id), None)
        if row is not None and row["SonType"] == son_type:
            return row
    return None


def population(snap: PlayerSnapshot, templates: GameTemplates) -> tuple[int, int]:
    """``(ocupada, máxima)``: soldados no castelo + exército x NeedPopulation; teto = Property2 da casa
    (900 no nível 1, visto no relay #642/#646)."""
    used = 0
    for pawn in snap.pawns:
        tpl = templates.get("PawnTempInfos", pawn.template_id) or {}
        used += (pawn.castle_count + pawn.army_count) * int(tpl.get("NeedPopulation", 1))
    house = building_row(snap, templates, HOUSE)
    return used, int(house["Property2"]) if house else 0


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
    """Avança missões abertas cuja condição é ``kind`` (QuestCondictionInfos.CondictionType) e cujo
    Para1 casa (0 = qualquer; em ``EXACT_PARA1`` tem que ser igual). Tipos de contagem somam ``value``;
    os de nível (``LEVEL_CONDITIONS``) guardam o maior."""
    changed = []
    for q in snap.quests:
        cond = templates.get("QuestCondictionInfos", q.template_id)
        if q.completed or cond is None or int(cond["CondictionType"]) != kind:
            continue
        ok = int(cond["Para1"]) == para1 if kind in EXACT_PARA1 else int(cond["Para1"]) in (0, para1)
        if not ok:
            continue
        new = max(q.progress, value) if kind in LEVEL_CONDITIONS else q.progress + value
        if new != q.progress:
            q.progress = new
            changed.append(q)
    return changed


# Missões sociais e de guilda (QuestCondictionInfos.CondictionType)
# (cliente) TaskTemplate.as: os tipos 21, 22, 29 e 51 conferem o estado, não a contagem
FRIEND_CONDITION = 21  # ter amigo: checkFriendsCount, tamanho da lista de amigos
GUILD_JOIN_CONDITION = 22  # estar em guilda: checkJoinConsortia, consortiaID > 0
OFFER_CONDITION = 29  # contribuição total: checkConsortiaOffer, consortiaTotalOffer >= Para2
GUILD_LEVEL_CONDITION = 51  # nível da guilda: checkConsortuaGrade; Para1 = prédio (GUILD_LEVEL_ATTRS)
# (visto) tempinfos QuestTemps 241 Detail: [Birlik İnşaatı] > [İbadethane] > [1 kez İbadet Et] = altar (5145)
BLESS_CONDITION = 30  # bênção do altar, uma por dia (5145)
# (visto) tempinfos QuestTemps 260 = própria (Para1 1); 22, 261 e 271 = de amigo (Para1 0)
TREE_CONDITION = 20  # regar a árvore (15017); (visto) captura #5 de ciftlik.json é a própria
# (visto) tempinfos QuestTemps 825 Detail: [Pazar] > ekipmanı [1 defa İhaleye Ver] = pôr à venda (8448)
SELL_CONDITION = 56  # pôr item no leilão (8448), +1 por anúncio
# (visto) tempinfos QuestTemps 857 Detail: [Akademi] > [Bereket Ruleti] > [Rulet Aç];
# (cliente) SeminaryBlessFrame.as manda 8489 no confirmar
SEMINARY_CONDITION = 57  # bênção do seminário (8489)
# Os de nível guardam o maior valor: evoluir tropa até Para2 (10) e os que o cliente confere pelo estado
LEVEL_CONDITIONS = {10, FRIEND_CONDITION, GUILD_JOIN_CONDITION, OFFER_CONDITION, GUILD_LEVEL_CONDITION}
EXACT_PARA1 = {TREE_CONDITION}  # Para1 0 não é coringa aqui: regar a própria (1) não avança as de amigo (0)
# Para1 de 51 -> Consortia: (cliente) TaskTemplate.as checkConsortuaGrade, Para1 1-5 = levels, shopLevel,
# altarLevel, schoolLevel, storeLevel (mesma numeração de guild.LEVEL_TYPES; 6-12 são pesquisas, fora da 51)
GUILD_LEVEL_ATTRS = {1: "levels", 2: "shop_level", 3: "altar_level", 4: "school_level", 5: "store_level"}


def social_state_quests(snap: PlayerSnapshot, templates: GameTemplates, guild: Consortia | None) -> list[Quest]:
    """Missões que o cliente confere pelo estado (amigos, guilda, contribuição, nível da guilda): sobe o
    progresso até o valor atual. Chamado no 5014: o cliente mostra a missão cumprida quando o estado bate,
    então o servidor precisa do mesmo progresso para concluir (e para quem agiu offline ou antes de aceitar)."""
    changed = quest_event(snap, templates, FRIEND_CONDITION, 0, len(snap.relations))
    changed += quest_event(snap, templates, GUILD_JOIN_CONDITION, 0, int(guild is not None))
    changed += quest_event(snap, templates, OFFER_CONDITION, 0, snap.character.consortia_total_offer)
    if guild is not None:
        for kind, attr in GUILD_LEVEL_ATTRS.items():
            changed += quest_event(snap, templates, GUILD_LEVEL_CONDITION, kind, getattr(guild, attr))
    return changed


def arm_avatar(snap: PlayerSnapshot, templates: GameTemplates) -> str:
    """``ArmyArmyMsg.arm``: arte da arma equipada (``/wizard_arms002``)."""
    return next((r.get("Avata", "") for r in equipment(snap, templates) if r.get("SonType") == WEAPON), "")


def cloth_avatar(snap: PlayerSnapshot, templates: GameTemplates) -> str:
    """``RoomPlayerMsg.cloth``: arte da armadura equipada (``/warrior_body023``)."""
    return next((r.get("Avata", "") for r in equipment(snap, templates) if r.get("SonType") == CLOTH), "")


def grade_steps(templates: GameTemplates) -> list[tuple[int, int]]:
    """``(nível, EXP total para chegar nele)`` em ordem."""
    rows = sorted((int(r["Grades"]), int(r["Data"])) for r in templates.find("UpGradeTempInfos", Types=PLAYER_GRADE))
    steps, total = [], 0
    for grade, data in rows:
        total += data
        steps.append((grade, total))
    return steps


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
        refresh_skill_point(leader, templates)
        for attr, per_level in GROWTH[job_type(c.job)].items():
            setattr(leader, attr, getattr(leader, attr) + per_level * gained)
            setattr(leader, f"{attr}_point", getattr(leader, f"{attr}_point") + per_level * gained)
    return gained


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


def quest_bitmap(snap: PlayerSnapshot) -> bytes:
    """``questSite``/``states``: bit ``id-1`` (LSB primeiro) de cada missão concluída."""
    bits = bytearray(QUEST_SITE_LEN)
    for q in snap.quests:
        if q.completed and 0 < q.template_id <= QUEST_SITE_LEN * 8:
            bits[(q.template_id - 1) // 8] |= 1 << ((q.template_id - 1) % 8)
    return bytes(bits)


def quest(snap: PlayerSnapshot, template_id: int) -> Quest | None:
    return next((q for q in snap.quests if q.template_id == template_id), None)


def accept_quest(snap: PlayerSnapshot, templates: GameTemplates, template_id: int, now: datetime) -> Quest | None:
    """Aceita a missão se existir e ainda não foi aceita; já avalia a condição."""
    if quest(snap, template_id) is not None or templates.get("QuestTemps", template_id) is None:
        return None
    q = Quest(snap.character.id or 0, template_id, now)
    snap.quests.append(q)
    update_novice_quests(snap, templates)
    update_building_quests(snap, templates)
    return q


def update_novice_quests(snap: PlayerSnapshot, templates: GameTemplates) -> list[Quest]:
    """Missões do tutorial (condição tipo 23) que passaram a cumprir a condição."""
    changed = []
    for q in snap.quests:
        if q.completed or q.progress:
            continue
        cond = templates.get("QuestCondictionInfos", q.template_id)
        novice = cond is not None and int(cond["CondictionType"]) == NOVICE_CONDITION
        if novice and cond is not None and snap.character.novice_process > int(cond["Para1"]):
            q.progress = int(cond["Para2"])
            changed.append(q)
    return changed


def update_building_quests(snap: PlayerSnapshot, templates: GameTemplates) -> list[Quest]:
    """Missões "evolua o prédio X" (tipo 2) cujo progresso mudou: vale o nível atual do prédio."""
    grades: dict[str, int] = {}
    for building in snap.buildings:
        row = templates.get("BuildingTempInfos", building.template_id)
        if row is not None:
            grades[row["SonType"]] = max(grades.get(row["SonType"], 0), int(row["BuildingGrade"]))
    changed = []
    for q in snap.quests:
        cond = templates.get("QuestCondictionInfos", q.template_id)
        if q.completed or cond is None or int(cond["CondictionType"]) != BUILDING_CONDITION:
            continue
        grade = min(grades.get(cond["Para1"], 0), int(cond["Para2"]))
        if grade != q.progress:
            q.progress = grade
            changed.append(q)
    return changed


def quest_done(snap: PlayerSnapshot, templates: GameTemplates, q: Quest) -> bool:
    cond = templates.get("QuestCondictionInfos", q.template_id)
    return cond is None or q.progress >= int(cond.get("Para2", "1"))


def quest_rewards(snap: PlayerSnapshot, templates: GameTemplates, template_id: int) -> tuple[Row, list[Item]]:
    """Template da missão e os itens de recompensa da classe do jogador (ainda não adicionados)."""
    row = templates.get("QuestTemps", template_id)
    assert row is not None
    jt = job_type(snap.character.job)
    goods = [
        Item(snap.character.id or 0, int(g["RewardItemID"]), count=int(g["RewardItemCount"]))
        for g in templates.find("QuestGoods", TemplateId=template_id)
        if int(g.get("ToJob", "0")) in (0, jt)
    ]
    return row, goods


def pay_point(c: Character, cost: int, bind: bool) -> bool:
    """Cobra diamantes; com ``bind`` gasta primeiro os vinculados (gift_token). False = sem saldo."""
    if cost < 0 or c.point + (c.gift_token if bind else 0) < cost:
        return False
    from_bind = min(c.gift_token, cost) if bind else 0
    c.gift_token, c.point = c.gift_token - from_bind, c.point - (cost - from_bind)
    return True


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


def upgrade_row(templates: GameTemplates, types: str, grade: int) -> Row | None:
    """UpGradeTempInfo de ``Types`` no grau ``grade`` (tabelas de custo/EXP por nível)."""
    return next(templates.find("UpGradeTempInfos", Types=types, Grades=grade), None)


def free_bag_pos(snap: PlayerSnapshot) -> int:
    used = {i.pos for i in snap.items if i.bag_type == BagType.BAG}
    return next(p for p in range(len(used) + 1) if p not in used)
