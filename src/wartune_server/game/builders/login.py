"""Mensagens do login montadas a partir do banco (``PlayerSnapshot``) + templates.

Valores fixos vêm do que o servidor oficial manda para um personagem novo
(captura em ``tests/fixtures/pcap_samples.json``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from ...domain.models import Castle, Character, Consortia, Hero, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates, HeroTemplate, Row

NEVER = "2000-01-01 00:00:00"
QUEST_SITE_LEN = 200


def fmt_time(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def complete[M: Message](msg: M) -> M:
    """Marca todo campo escalar ausente com o valor padrão, recursivamente.

    O servidor oficial escreve todos os campos; no AS3 uma string ausente vira
    ``null`` e quebra o cliente em ``.length``. Mensagens já presentes são completadas.
    """
    for field in msg.DESCRIPTOR.fields:
        if field.is_repeated:
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                for item in getattr(msg, field.name):
                    complete(item)
        elif field.type == FieldDescriptor.TYPE_MESSAGE:
            if msg.HasField(field.name):
                complete(getattr(msg, field.name))
        elif not msg.HasField(field.name):
            setattr(msg, field.name, field.default_value)
    return msg


ATTRS = ("Power", "Agility", "Intellect", "Captain", "Physique")
# atributo derivado -> coluna de ItemTempInfo/SkillPropertyTempInfo que soma direto no total
ITEM_BONUS = {
    "PhyAttack": "Attack",
    "PhyDefence": "Defence",
    "MagicAttack": "MagicAttack",
    "MagicDefence": "MagicDefence",
    "ForceHit": "ForceHit",
    "Parry": "Parry",
    "ConatArmy": "Conat",
    "Live": "Live",
}


@dataclass(frozen=True, slots=True)
class HeroStats:
    """Atributos ``base*`` (herói + atributos dos equipamentos) e ``total*`` (+ bônus fixos dos itens)."""

    base: dict[str, int]
    total: dict[str, int]

    @property
    def live(self) -> int:
        return self.total["Live"]

    @property
    def fighting_capacity(self) -> int:
        # ponytail: bate com o oficial no nível 1 (199); nível 3 dá 291 contra 278. Falta a fórmula real.
        t = self.total
        return (
            t["PhyAttack"] + t["PhyDefence"] + int(t["MagicAttack"] * 1.05) + t["MagicDefence"] + t["ForceHit"]
        ) + int(t["Live"] * 0.75)

    @classmethod
    def of(cls, hero: Hero, tpl: HeroTemplate, bonuses: Sequence[Row] = ()) -> HeroStats:
        """``bonuses``: linhas de template dos equipamentos e dos atributos sorteados deles.

        Fórmulas tiradas da captura (maga níveis 1, 3 e 5, com e sem arma); o cliente não calcula
        nada disso, o servidor manda pronto.
        """
        own = {"Power": hero.power, "Agility": hero.agility, "Intellect": hero.intellect}
        own |= {"Captain": hero.captain, "Physique": hero.physique}
        attrs = {k: own[k] + sum(int(r.get(k, 0)) for r in bonuses) for k in ATTRS}
        level = 3 * (hero.grades - 1)
        derived = {
            "PhyAttack": 4 * attrs["Power"],
            "PhyDefence": attrs["Physique"] + level,
            "MagicAttack": 4 * attrs["Intellect"],
            "MagicDefence": attrs["Intellect"] + attrs["Physique"] + level - 1,
            "ForceHit": tpl.force_hit,
            "Parry": tpl.parry,
            "ConatArmy": attrs["Captain"],
            "Live": tpl.live + 20 * attrs["Physique"] + 10 * hero.grades,
        }
        total = {k: v + sum(int(r.get(ITEM_BONUS[k], 0)) for r in bonuses) for k, v in derived.items()}
        return cls(own | derived, attrs | total)


def hero_info(hero: Hero, player_id: int, stats: HeroStats) -> pb.SimpleHeroInfoMsg:
    skills = [s for s in hero.skill_script.split(",") if s]
    msg = pb.SimpleHeroInfoMsg(
        heroId=hero.id or 0,
        nickName=hero.nickname,
        tempateId=hero.template_id,
        playerId=player_id,
        remainPoint=hero.remain_point,
        skillPoint=hero.skill_point,
        skillScript="".join(f"{s}," for s in skills),
        fastKey=hero.fast_key or "".join(f"{s[:3]}," for s in skills),
        hp=stats.live,
        powerPoint=hero.power_point,
        agilityPoint=hero.agility_point,
        intellectPoint=hero.intellect_point,
        captainPoint=hero.captain_point,
        physiquePoint=hero.physique_point,
        fightPos=hero.fight_pos,
        # o oficial omite; o complete() mandaria 0 e o cliente zera o nível do herói (hasGrade),
        # aí nenhuma missão com NeedMinLevel 1 fica disponível e o tutorial trava no 12000
        grade=hero.grades,
    )
    for name, value in stats.base.items():
        setattr(msg, "base" + name, value)
    for name, value in stats.total.items():
        setattr(msg, "total" + name, value)
    return msg


def player_msg(
    snap: PlayerSnapshot, fighting_capacity: int, now: datetime, quest_site: bytes, guild: Consortia | None = None
) -> pb.PlayerMsg:
    c: Character = snap.character
    msg = pb.PlayerMsg(
        playerId=c.id,
        nickName=c.nickname or "",
        sex=c.sex,
        pic=c.icon,
        camp=c.camp,
        point=c.point,
        giftToken=c.gift_token,
        strategy=c.strategy,
        state=7,
        questSiteLen=QUEST_SITE_LEN,
        questSite=quest_site,
        grades=c.grades,
        gp=c.gp,
        totalGp=c.total_gp,
        repute=c.repute,
        geste=c.geste,
        charm=c.charm,
        weary=c.weary,
        wearyLimit=0,
        attackLeftCount=5,
        noviceProcess=c.novice_process,
        fightingCapacity=fighting_capacity,
        gradeProcess="0",
        right=1,
        job=c.job,
        signDate=fmt_time(now),
        startFree=1,
        campaignCount=1,
        reloginCount=1,
        matchRoomCount=15,
        serverName=snap.server.name,
        warFieldCount=2,
        trialMaxCount=1,
        campaignMaxcount=1,
        lastFreeSkillLearnTime=NEVER,
        rentalBagTime=NEVER,
        status=-1,
        qteGuide=c.qte_guide,
        hasVicePassword=int(bool(c.vice_password)),
        isDuringToResetTime=int(c.vice_reset_at is not None),
        refuseFriend=c.refuse_friend,
        consortiaId=guild.id if guild else 0,
        consortiaName=guild.name if guild else "",
        consortiaOffer=c.consortia_offer,
        consortiaTotaloffer=c.consortia_total_offer,
        consortiaAttack=c.skill_attack,
        consortiaAgility=c.skill_agility,
        consortiaAbility=c.skill_ability,
        consortiaCaptain=c.skill_captain,
        consortiaGold=c.skill_gold,
        consortiaPhysique=c.skill_physique,
        isAuto=c.is_auto,
        lastOutConsortia=fmt_time(c.last_out_consortia) if c.last_out_consortia else NEVER,
    )
    msg.order.playerId = c.id or 0
    return msg


def army_msg(
    snap: PlayerSnapshot, castle: Castle, hero: pb.SimpleHeroInfoMsg, fighting_capacity: int, arm: str = ""
) -> pb.ArmyArmyMsg:
    c = snap.character
    msg = pb.ArmyArmyMsg(
        armyId=c.id,  # ponytail: 1 exército por personagem; tabela própria quando houver tropas extras
        playerId=c.id,
        nickName=c.nickname or "",
        mapId=castle.map_id,
        curPosX=castle.pos_x - 2,
        curPosY=castle.pos_y - 2,
        type=2,
        fightingCapacity=fighting_capacity,
        grades=c.grades,
        arm=arm,
    )
    msg.simpleHeroInfo.CopyFrom(hero)
    return msg


def castle_msg(snap: PlayerSnapshot, castle: Castle) -> pb.BaseCastleMsg:
    c = snap.character
    return pb.BaseCastleMsg(
        id=castle.id or 0,
        mapId=castle.map_id,
        posX=castle.pos_x,
        posY=castle.pos_y,
        type=1,
        occupyPlayerId=c.id,
        occupyPlayerName=c.nickname or "",
        state=castle.state,
        castleName=castle.name,
        leftEnergy=castle.energy,
        grade=castle.grade,
    )


def farm_msg(snap: PlayerSnapshot) -> pb.LoadFarmRsp:
    c = snap.character
    msg = pb.LoadFarmRsp()
    farm = msg.farm
    farm.userId, farm.nickName, farm.grades, farm.landGrades = c.id or 0, c.nickname or "", 1, 1
    for pos in range(3):
        farm.farmLandInfo.add(userId=c.id, pos=pos, plantingTime=NEVER, matureTime=NEVER)
    return msg


def system_property(now: datetime, opened_at: datetime) -> pb.SystemPropertyMsg:
    return pb.SystemPropertyMsg(sysCurtime=fmt_time(now), sysStarTime=fmt_time(opened_at))


def buildings_msg(snap: PlayerSnapshot, castle: Castle, templates: GameTemplates) -> pb.BuildingInfoListMsg:
    msg = pb.BuildingInfoListMsg(result=True)
    for building in snap.buildings:
        row = next(templates.find("BuildingTempInfos", TemplateId=building.template_id), None)
        msg.building.add(
            userId=snap.character.id or 0,
            buildingId=building.id or 0,
            castleId=castle.id or 0,
            createdDate=fmt_time(snap.character.created_at),
            isExist=True,
            templateId=building.template_id,
            sonType=int(row["SonType"]) if row else 0,
            propterty1=building.property1,
            propterty2=building.property2,
        )
    return msg
