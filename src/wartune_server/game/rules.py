"""Regras de progressão aplicadas ao ``PlayerSnapshot`` em memória: EXP e nível, crescimento do
herói, equipamentos, missões. Quem chama grava as entidades alteradas (``CharacterService.save``).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime

from ..domain import gameday
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
from . import buffs
from .builders.login import QUEST_SITE_LEN, HeroStats

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
    day = gameday.today(now)
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


def population(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> tuple[int, int]:
    """``(ocupada, máxima)``: soldados no castelo + exército x NeedPopulation; teto = Property2 da casa
    (900 no nível 1, visto no relay #642/#646) + o Population Expansion Scroll (``buffs.POPULATION``)."""
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
# Masmorra (campanha): só o servidor sabe quando o jogador passou; (cliente) TaskTemplate.as checkCount só lê o contador
CAMPAIGN_CONDITION = 14  # passar a campanha Para1 (CampaignId, ex. 70 -> 1001); (visto) captura #1215 -> #1222
# (visto) tempinfos: a 80 pede o chefe 1011 ('Çene') na campanha 1001 (Para3); (visto) captura #1714: o 112 do chefe
HERO_KILL_CONDITION = 26  # matar o chefe Para1 (GameHeroTemp); Para3 = campanha
# (dedução) 25 conta os soldados do lado 2 da batalha vencida pelo tempId; nenhuma missão de 25 aponta para a 1001
PAWN_KILL_CONDITION = 25  # matar Para2 soldados do tipo Para1 (PawnTempInfos) numa campanha
SOLO_CONDITION = 31  # passar cena com Para1 jogadores (Campaigns.Capacity); (visto) tempinfos: 313 = 1, 371 = 2
# Os de nível guardam o maior valor: evoluir tropa até Para2 (10) e os que o cliente confere pelo estado
# 63: Emek Oranı (total da atividade diária); 78: grau do símbolo; 14: passou a campanha (um sim, não soma)
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


PLAYER_LEVEL_CONDITION = 1  # nível do jogador >= Para2, lido na hora (cliente: TaskTemplate.checkPlayerGrades)
LOGIN_DAY_CONDITION = 39  # entrar num dia diferente do da aceitação (cliente: checkSencondLogin)
TALK_CONDITION = 85  # falar com o NPC do nó Para4 ("mapa,nó"): vem do 8692 ou do aceite (cliente: finishStory)
PROGRESS_FIELDS = ("progress", "progress_2", "progress_3", "progress_4")  # condition_1..4 do 112
# bolsa: quantidade do item Para1 (templateId) >= Para2 (cliente: checkGoodsCount). O condition_N fica em 0: (visto)
# captura EN, a 90 e a 102 só têm 112 com 0 (#1140, #1572, #1800, #2081), nem nos drops do Worg Tooth (#1276, #1408)
GOODS_CONDITIONS = {27, 28, 32, 49}
# (visto) captura EN: só estes tipos mandam o 112 do progresso antes da entrega (5014): 23 (#211), 2 (#631), 10 (#2180)
PROGRESS_BEFORE_FINISH = {NOVICE_CONDITION, BUILDING_CONDITION, 10}
QUEST_GOODS_SON = "210"  # SonType do item só de missão (2100001): a entrega tira todas as unidades (goods_to_take)
# (cliente) newbie.xml (overlay/ui/zh_cn), saveId: o maior salto do guia é 28500 -> 32000 (3500)
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


def goods_count(snap: PlayerSnapshot, template_id: int) -> int:
    """Unidades do item na mochila, como ``goodsCountByTempId`` no cliente (TaskTemplate.checkGoodsCount)."""
    return sum(i.count for i in snap.items if i.bag_type == BagType.BAG and i.template_id == template_id)


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


def ever_completed(q: Quest) -> bool:
    """Já foi concluída alguma vez. O bit do ``states`` continua ligado quando a repetível reabre (login.json #89:
    id 241 aberta com o bit 1), e a pré-missão do cliente (checkPreTask, IsTaskFinish) lê esse bit."""
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


def quest_done(snap: PlayerSnapshot, templates: GameTemplates, q: Quest, now: datetime) -> bool:
    """Concluída quando todas as condições batem, como no cliente. Nível do jogador, dia do login e bolsa são lidos
    agora; os de contagem usam o contador gravado (condition_N). Sem linha de condição não conclui: nenhuma missão
    dos dados está assim, e o cliente a acharia pronta sem nada a cumprir."""
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
    """(templateId, quantidade) que a entrega consome, de cada condição de bolsa. (visto) captura #1609 (replay): o
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


def pay_quest_rewards(snap: PlayerSnapshot, templates: GameTemplates, row: Row) -> tuple[int, int]:
    """Paga EXP (com o bônus diário), ouro, RewardStrategy (ruh), RewardCrystal e RewardPlayerOffer, como a tela do
    cliente (TaskRewardViewII._rewardList). Os itens (QuestGoods) são de quem chama, que confere a mochila. Devolve
    ``(EXP, RewardConsortiaOffer)``: quem chama credita a oferta da guilda se o jogador tiver guilda. RewardMoney,
    RewardHeroGP e RewardDower não são pagos: a tela não mostra o primeiro (só a missão 1, expirada) e os outros dois
    são 0 em todas as linhas."""
    c = snap.character
    gp = int(row.get("RewardPlayGP", 0))
    if gp > 0 and row.get("TemplateType") == "1":  # bônus diário que a tela soma (TaskRewardViewII.as:207-209)
        gp += (c.grades - int(row["NeedMinLevel"])) * 500
    add_gp(snap, templates, gp)
    c.gold += int(row.get("RewardGold", 0))
    c.strategy += int(row.get("RewardStrategy", 0))
    c.crystals += int(row.get("RewardCrystal", 0))
    offer = int(row.get("RewardPlayerOffer", 0))
    c.consortia_offer += offer
    c.consortia_total_offer += offer
    return gp, int(row.get("RewardConsortiaOffer", 0))


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


def copies_base(templates: GameTemplates) -> int:
    """Entradas de campanha em grupo por dia sem item (``ConfigInfos`` MultiCampaign_MaxCount = 1)."""
    return int(config(templates, "MultiCampaign_MaxCount", "1"))


def upgrade_row(templates: GameTemplates, types: str, grade: int) -> Row | None:
    """UpGradeTempInfo de ``Types`` no grau ``grade`` (tabelas de custo/EXP por nível)."""
    return next(templates.find("UpGradeTempInfos", Types=types, Grades=grade), None)


def free_bag_pos(snap: PlayerSnapshot) -> int:
    used = {i.pos for i in snap.items if i.bag_type == BagType.BAG}
    return next(p for p in range(len(used) + 1) if p not in used)
