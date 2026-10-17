"""Regras do coliseu e do torneio de fadas: contadores do dia, robôs, cópias de combate, prêmios.

Os handlers ficam em ``handlers/arena.py``; o protocolo e as fontes em ``docs/pvp.md``.
"""

from __future__ import annotations

import asyncio
import json
import math
import random
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

from ..domain.models import Arena, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates
from . import rules

COLOSSEUM, PETS = 0, 1  # ChallengeRequestMsg/ChallengeCoolTimeMsg.type e ChallengeLog.kind
FREE_COUNT, MAX_BUY = 10, 10  # coliseu: tentativas grátis e compráveis por dia (totalCount/totalBuyCount)
COLOSSEUM_COOL, PET_COOL = 600, 300  # segundos de espera depois de lutar (4176 nas capturas)
ATTACK_FREE = 5  # attackLeftCount do dia (PlayerMsg; o AttackAlertFrame mostra "x/5")
ROBOT_BASE = 1_300_000_000  # userId dos robôs (capturas: 13000xxxxx); nunca viram personagem
PET_ROBOT_BASE = ROBOT_BASE + 1400
REWARDS_FILE = Path("data/colosseum_rewards.json")
RANK_LOCK = asyncio.Lock()  # troca de posições do coliseu: ler, trocar e gravar sem outra luta no meio
LOGS = 10  # o cliente mostra ~10 lutas no histórico

NAMES = (
    "Kelsey", "Avery", "Mariss", "Wyat", "Highgarden", "DePiedra", "Sojust", "Brienne", "Corwin", "Dalia",
    "Elric", "Fiona", "Garret", "Helena", "Ivor", "Jessa", "Kaelan", "Liora", "Marek", "Nadia",
    "Orin", "Petra", "Quinn", "Rowan", "Selene", "Tobias", "Ursa", "Vance", "Willa", "Yorick",
)  # fmt: skip
DECOR = (("✿", "✿"), ("☆", "☆"), ("♡", "♥"), ("♫", "♫"), ("▷", "◁"))


@cache
def rewards() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(REWARDS_FILE.read_text(encoding="utf-8"))
    return data


def config(templates: GameTemplates, name: str, default: int) -> int:
    row = templates.get("ConfigInfos", name, key="ConfigName")
    return int(row["ConfigValue"]) if row is not None else default


# -- contadores do dia ----------------------------------------------------------------------------


def today(now: datetime) -> str:
    return now.date().isoformat()


def week(now: datetime) -> str:
    year, number, _ = now.isocalendar()
    return f"{year}-W{number:02d}"


def roll_day(arena: Arena, now: datetime) -> bool:
    """Zera os contadores se o dia virou. ``True`` se zerou algo que o cliente já mostrava (4202)."""
    if arena.day == today(now):
        return False
    used = bool(arena.challenge_count or arena.pet_count or arena.pet_buy_count or arena.attack_left != ATTACK_FREE)
    arena.day = today(now)
    arena.challenge_count = arena.pet_count = arena.pet_buy_count = 0
    arena.attack_left = ATTACK_FREE
    return used


def left(until: datetime | None, now: datetime) -> int:
    return max(0, math.ceil((until - now).total_seconds())) if until is not None else 0


def pet_total(arena: Arena, templates: GameTemplates) -> int:
    return config(templates, "Pet_Challenge_Count", 10) + arena.pet_buy_count


def cool_time(arena: Arena, kind: int, now: datetime, templates: GameTemplates) -> pb.ChallengeCoolTimeMsg:
    """4176. Coliseu: ``challengeCount`` = usadas; fadas: = restantes (cada tela lê de um jeito)."""
    if kind == COLOSSEUM:
        return pb.ChallengeCoolTimeMsg(
            leftTime=left(arena.cool_until, now),
            challengeCount=arena.challenge_count,
            totalCount=FREE_COUNT,
            type=COLOSSEUM,
            totalBuyCount=MAX_BUY,
        )
    remaining = max(0, pet_total(arena, templates) - arena.pet_count)
    return pb.ChallengeCoolTimeMsg(
        leftTime=left(arena.pet_cool_until, now), challengeCount=remaining, totalCount=0, type=PETS
    )


def data_reset(snap: PlayerSnapshot, now: datetime) -> pb.DataResetMsg:
    """4202: o cliente sobrescreve vigor, ataques e afins com estes valores, então vão os atuais."""
    c = snap.character
    return pb.DataResetMsg(
        weary=c.weary,
        hangupCount=0,
        transEnergy=0,
        attackCount=snap.arena.attack_left if snap.arena is not None else ATTACK_FREE,  # = attackLeftCount
        challengeCount=0,
        leftHangupWeary=0,
        tower1EnterCount=0,
        tower2EnterCount=0,
        blessingCount=c.bless_count_today(now),
        blessingBuff=c.seminary_effect,
        buyCount=0,
        king_Buff=False,
        serverName=snap.server.name,
        upRuneByPointTimes=0,
    )


def buy_cost(bought: int) -> int:
    """Diamantes da tentativa extra do coliseu (``ColosseumModel.buyCountNeedPay``)."""
    return min((bought + 1) * 2, 10)


def cool_cost(seconds: int) -> int:
    """Diamantes para zerar a espera (o que a confirmação do cliente mostra: ``ceil(s/60)*5``)."""
    return math.ceil(seconds / 60) * 5


def pay_diamonds(snap: PlayerSnapshot, cost: int, bind_ok: bool) -> bool:
    """Desconta ``cost``: diamante vinculado primeiro quando permitido (``payType``)."""
    c = snap.character
    bound = min(c.gift_token, cost) if bind_ok else 0
    if c.point < cost - bound:
        return False
    c.gift_token -= bound
    c.point -= cost - bound
    return True


# -- recompensa do coliseu ------------------------------------------------------------------------


def period(now: datetime) -> tuple[str, int]:
    """(chave do período de resgate, dias até o próximo)."""
    days = int(rewards()["period_days"])
    ordinal = now.date().toordinal()
    return str(ordinal // days), days - ordinal % days


def rank_reward(rank: int) -> tuple[int, int]:
    """(ouro, Ruh) da posição; (0, 0) fora do ranking."""
    for tier in rewards()["rank_rewards"]:
        first, last = tier["ranks"]
        if rank > 0 and first <= rank <= last:
            return int(tier["gold"]), int(tier["strategy"])
    return 0, 0


def can_claim(arena: Arena, rank: int, now: datetime) -> bool:
    return rank > 0 and arena.reward_day != period(now)[0]


def battle_gp(grade: int, won: bool) -> int:
    return grade * int(rewards()["win_gp_per_grade" if won else "lose_gp_per_grade"])


# -- robôs ----------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Robot:
    """Oponente gerado do id (mesmo id = mesmo robô na lista e na luta). Só existem robôs guerreiros
    nos templates (``GameHeroTemp`` HeroType 2: 11001-11030 e 14001-14030), até o nível 30."""

    id: int
    grade: int

    @property
    def _rng(self) -> random.Random:
        return random.Random(self.id)

    @property
    def female(self) -> bool:
        return self.id % 2 == 0

    @property
    def name(self) -> str:
        rng = self._rng
        left_mark, right_mark = rng.choice(DECOR)
        return f"{left_mark}{rng.choice(NAMES)}{right_mark}"

    @property
    def pics(self) -> int:
        return 4 if self.female else 1  # JobType: guerreira / guerreiro

    @property
    def hero_template(self) -> int:
        return (14000 if self.female else 11000) + max(1, min(self.grade, 30))

    def fighting_capacity(self, templates: GameTemplates) -> int:
        row = templates.get("GameHeroTemp", self.hero_template) or {}
        return int(row.get("Live", 0)) + 2 * int(row.get("Attack", 0))


def is_robot(user_id: int) -> bool:
    return user_id >= ROBOT_BASE


def robots(seed: str, count: int, grade: int, base: int = ROBOT_BASE) -> list[Robot]:
    rng = random.Random(seed)
    return [Robot(base + i, grade) for i in rng.sample(range(1, 999), count)]


def robot_player(robot: Robot, templates: GameTemplates) -> pb.SimplePlayerInfoMsg:
    return pb.SimplePlayerInfoMsg(
        userId=robot.id,
        nickName=robot.name,
        sexs=0 if robot.female else 1,
        pics=robot.pics,
        consortiaID=0,
        consortiaName="",
        grades=robot.grade,
        fightingCapacity=robot.fighting_capacity(templates),
        challengeRank=0,
        job=1,
    )


def snapshot_player(snap: PlayerSnapshot, templates: GameTemplates, rank: int) -> pb.SimplePlayerInfoMsg:
    c = snap.character
    return pb.SimplePlayerInfoMsg(
        userId=c.id or 0,
        nickName=c.nickname or "",
        sexs=c.sex,
        pics=c.icon,
        consortiaID=0,
        consortiaName="",
        grades=c.grades,
        fightingCapacity=rules.leader_stats(snap, templates).fighting_capacity,
        challengeRank=rank,
        job=rules.job_type(c.job),
    )


# -- montagem das batalhas ------------------------------------------------------------------------

ENEMY_HERO = 7  # livingId da captura do coliseu (#6)
PLAYER_LIVING, PLAYER_POS = 3, 6


def _npc_hero(**fields: Any) -> dict[str, Any]:
    """Herói do lado 2 como NPC: ``type 2``, ``userId 0`` (captura do coliseu #6)."""
    base: dict[str, Any] = {
        "heroId": ROBOT_BASE,
        "livingId": ENEMY_HERO,
        "userId": 0,
        "userPics": 0,
        "type": 2,
        "side": 2,
        "pos": 6,
        "hp2": 0,
        "sp": 0,
        "slotAvata": "",
        "clothAvate": "",
        "cloakPath": "",
        "hairPath": "",
        "captain": 0,
        "res": "",
        "qteTime": 0,
        "castTime": 4500,
        "pawnTempId": 0,
        "headId": 0,
        "isShow": False,
        "serverName": "",
        "wingAvata": "",
        "fashionArmAvata": "",
        "fashionClothAvata": "",
        "awake": 0,
        "livingId2": 0,
        "fateSkillTempIds": "",
        "isChange": False,
        "fightCapacity": 0,
        "hasShadow": False,
        "mateId": 0,
        "curturn": 0,
    }
    return base | fields


# Fração da vida e do ataque do jogador. Simulado (modo automático, 15 lutas por nível): guerreiro e
# mago ganham 15/15 dos níveis 11 a 50. ponytail: o caçador perde até o nível ~30 porque o ataque
# dele sai de PhyAttack (4x Força, baixo); corrigir com a fórmula real de ataque por classe.
ROBOT_HP, ROBOT_ATTACK = 0.35, 0.15


def robot_spec(
    robot: Robot, templates: GameTemplates, player_hp: int, player_attack: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(soldados, heróis) do robô. O herói é o do template, com vida e ataque proporcionais aos do
    jogador: o robô existe para o servidor vazio, e a primeira vitória é a porta do ranking.
    ponytail: a captura tem 2 arqueiros 10202 com o robô, mas lá o jogador também tinha soldados;
    aqui o jogador não tem, e com eles o robô do template ganhava quase sempre (simulado do nível
    11 ao 30). Voltar com os soldados quando o exército do jogador entrar na batalha."""
    row = templates.get("GameHeroTemp", robot.hero_template) or {}
    hp = max(1, int(player_hp * ROBOT_HP))
    hero = _npc_hero(
        tempId=robot.hero_template,
        nickName=robot.name,
        grade=int(row.get("Grades", robot.grade)),
        maxHp=hp,
        initHp=hp,
        hp=hp,
        skillId=[int(x) for x in row.get("SkillScript", "").split(",") if x],
        attack=max(1, int(player_attack * ROBOT_ATTACK)),
    )
    return [], [hero]


def copy_hero(snap: PlayerSnapshot, templates: GameTemplates) -> dict[str, Any]:
    """Cópia de combate de outro jogador (ou do próprio): o herói líder como NPC do lado 2."""
    leader = snap.leader
    assert leader is not None
    stats = rules.leader_stats(snap, templates)
    magic = rules.job_type(snap.character.job) == 3
    tpl = templates.get("GameHeroTemp", leader.template_id) or {}
    return _npc_hero(
        tempId=leader.template_id,
        nickName=leader.nickname,
        grade=leader.grades,
        maxHp=stats.live,
        initHp=stats.live,
        hp=stats.live,
        slotAvata=rules.arm_avatar(snap, templates),
        clothAvate=rules.cloth_avatar(snap, templates),
        skillId=[int(x) for x in leader.skill_script.split(",") if x],
        fightCapacity=stats.fighting_capacity,
        attack=stats.total["MagicAttack"] if magic else stats.total["PhyAttack"],
        defaultSkill=int(tpl.get("DefaultSkill", 0)),
    )


def colosseum_spec(soldiers: list[dict[str, Any]], heroes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "battleType": 16,
        "mapTempId": 992,
        "attackModel": 2,
        "battleScene": 7,
        "pvp": True,
        "soldiers": soldiers,
        "heroes": heroes,
        "player": {"livingId": PLAYER_LIVING, "pos": PLAYER_POS},
    }


# -- torneio de fadas -----------------------------------------------------------------------------

PET_ROBOT_PETS = (101102, 102102, 104102)  # captura: Amazon Kraliçesi, Liris, Pan, nível 50, qualidade 6
PET_ROBOT_GRADE, PET_ROBOT_QUALITY = 50, 6
PET_NOTICE_FRAME, PET_DAMAGE_IMPROVE = 1500, 50  # 4361 aos 60 s: dano +50%
PET_WIN_SCORE, PET_LOSE_SCORE = 5, 0  # "Puan +5" na captura; ponytail: perda não observada, não tira pontos


def pet_hp(template: int, grade: int, templates: GameTemplates) -> int:
    # ponytail: fórmula de vida do pet desconhecida; MaxHp + nível × GrowthRate / 9 dá ~5% da captura
    row = templates.get("PetTempInfos", template) or {}
    return int(row.get("MaxHp", 1000)) + grade * int(row.get("GrowthRate", 600)) // 9


def pet_unit(
    template: int,
    grade: int,
    quality: int,
    living: int,
    side: int,
    pos: int,
    user_id: int,
    pet_id: int,
    templates: GameTemplates,
    skills: str = "",
) -> dict[str, Any]:
    """Pet no ``BattlePrepareMsg.pets`` (captura do torneio #7). ``userId`` = dono no lado do jogador
    (o cliente acha "os meus" por ele; sem nenhum a batalha não inicializa) e 0 nos robôs."""
    row = templates.get("PetTempInfos", template) or {}
    hp = pet_hp(template, grade, templates)
    return {
        "livingId": living,
        "userId": user_id,
        "tempId": template,
        "type": int(row.get("PetType", 0)),
        "nickName": row.get("TemplateName", ""),
        "grade": grade,
        "side": side,
        "pos": pos,
        "maxHp": hp,
        "initHp": hp,
        "hp": hp,
        "hp2": 0,
        "qteTime": 0,
        "castTime": 5000,
        "skillId": [int(x) for x in (skills or row.get("ChangeSkills", "")).split(",") if x],
        "headId": pet_id,
        "serverName": "",
        "livingId2": 0,
        "petQuality": quality,
        "attack": hp // 14,  # ponytail: ~ o dano da captura (golpe básico ≈ vida/40)
        "defaultSkill": int(row.get("DefaultSkills", 0) or 0),
    }


def pet_robot_info(robot: Robot, templates: GameTemplates) -> pb.PlayerPetMsg:
    msg = pb.PlayerPetMsg(userId=robot.id, nickName=robot.name, order=0, score=1000)
    for template in PET_ROBOT_PETS:
        row = templates.get("PetTempInfos", template) or {}
        msg.petInfo.add(
            petId=0,
            templateId=template,
            petName=row.get("TemplateName", ""),
            curGrade=PET_ROBOT_GRADE,
            fightingCapacity=0,
            quality=PET_ROBOT_QUALITY,
        )
    return msg


def pet_spec(mine: list[dict[str, Any]], theirs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "battleType": 35,
        "mapTempId": 992,
        "attackModel": 1,
        "battleScene": 19,
        "pvp": True,
        "notice": PET_NOTICE_FRAME,
        "damageImprove": PET_DAMAGE_IMPROVE,
        "soldiers": [],
        "heroes": [],
        "pets": mine + theirs,
    }


def pet_robot_units(templates: GameTemplates, first_living: int) -> list[dict[str, Any]]:
    return [
        pet_unit(t, PET_ROBOT_GRADE, PET_ROBOT_QUALITY, first_living + i, 2, pos, 0, 0, templates)
        for i, (t, pos) in enumerate(zip(PET_ROBOT_PETS, (4, 3, 9), strict=True))
    ]


def pet_rewards(templates: GameTemplates, kind: int, order: int) -> list[tuple[int, int]]:
    """(item, quantidade) de ``PetChallengeRewards`` (Type 1 diária, 2 semanal) para a posição."""
    found = []
    for row in templates.find("PetChallengeRewards", Type=kind, RewardType=1):
        first, _, last = row["Ranking"].partition(",")
        if int(first) <= order <= int(last or first):
            found.append((int(row["TemplateId"]), int(row["Count"])))
    return found


def cool_until(now: datetime, seconds: int) -> datetime:
    return now + timedelta(seconds=seconds)


@dataclass(frozen=True, slots=True)
class Pet:
    """O que o torneio precisa de um pet do jogador. ``slot``: espaço da formação (0 a 5)."""

    id: int
    template: int
    grade: int
    quality: int
    name: str
    skills: str = ""  # ChangeSkills do próprio pet; "" = os do template
    slot: int = 0


def pets_of(snap: PlayerSnapshot) -> list[Pet]:
    """Pets do jogador (``snap.pets``, tabela ``pets``), os que já foram gravados (têm id)."""
    return [Pet(p.id or 0, p.template_id, p.grade, p.quality, p.name, p.change_skills) for p in snap.pets if p.id]


def formation(arena: Arena, snap: PlayerSnapshot) -> list[Pet]:
    """Pets da formação gravada (``chaPos``) que o jogador ainda tem, em cada espaço (``slot``)."""
    owned = {p.id: p for p in pets_of(snap)}
    ids = [int(x) for x in arena.pet_formation.split(",") if x.strip().lstrip("-").isdigit()]
    return [replace(owned[i], slot=n) for n, i in enumerate(ids) if i in owned]
