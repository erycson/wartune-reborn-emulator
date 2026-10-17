"""Regras de progressão aplicadas ao ``PlayerSnapshot`` em memória: EXP e nível, crescimento do
herói, equipamentos, missões. Quem chama grava as entidades alteradas (``CharacterService.save``).
"""

from __future__ import annotations

from datetime import datetime

from ..domain.models import BagType, Item, PlayerSnapshot, Quest
from ..templates.repository import GameTemplates, Row
from .builders.login import QUEST_SITE_LEN, HeroStats

PLAYER_GRADE = "3"  # UpGradeTempInfo.Types do nível do jogador; Data = EXP do nível anterior até este
NOVICE_CONDITION = 23  # QuestConditionInfo: noviceProcess > Para1
WEAPON, CLOTH = "101", "104"  # ItemTempInfo.SonType

# ganho de atributos por nível, por JobType (1 guerreiro, 2 caçador, 3 mago). O mago foi medido na
# captura (níveis 1, 3 e 5); ponytail: guerreiro e caçador são o espelho dele, trocar quando houver captura.
GROWTH = {
    1: {"power": 3, "agility": 1, "captain": 10, "physique": 1},
    2: {"agility": 3, "power": 1, "captain": 10, "physique": 1},
    3: {"intellect": 3, "agility": 1, "captain": 10, "physique": 1},
}


def job_type(job: int) -> int:
    return (job - 1) % 3 + 1


def equipment(snap: PlayerSnapshot, templates: GameTemplates) -> list[Row]:
    """Linhas de template que somam nos atributos do líder: itens equipados e o atributo sorteado."""
    leader = snap.leader
    rows: list[Row] = []
    for item in snap.items:
        if item.bag_type != BagType.HERO or leader is None or item.object_id != leader.id:
            continue
        if (row := templates.get("ItemTempInfos", item.template_id)) is not None:
            rows.append(row)
        if item.random_skill and (bonus := templates.get("SkillPropertyTempInfos", item.random_skill)) is not None:
            rows.append(bonus)
    return rows


def leader_stats(snap: PlayerSnapshot, templates: GameTemplates) -> HeroStats:
    leader = snap.leader
    assert leader is not None
    return HeroStats.of(leader, templates.hero(leader.template_id), equipment(snap, templates))


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
        for attr, per_level in GROWTH[job_type(c.job)].items():
            setattr(leader, attr, getattr(leader, attr) + per_level * gained)
            setattr(leader, f"{attr}_point", getattr(leader, f"{attr}_point") + per_level * gained)
    return gained


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


def free_bag_pos(snap: PlayerSnapshot) -> int:
    used = {i.pos for i in snap.items if i.bag_type == BagType.BAG}
    return next(p for p in range(len(used) + 1) if p not in used)
