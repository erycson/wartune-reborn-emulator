"""Mensagens do login montadas a partir do banco (``PlayerSnapshot``) + templates.

Valores fixos vêm do que o servidor oficial manda para um personagem novo
(captura em ``tests/fixtures/pcap_samples.json``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from ...domain.models import Castle, Character, Hero, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates

NEVER = "2000-01-01 00:00:00"
QUEST_SITE_LEN = 200


def fmt_time(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def complete(msg: Message) -> Message:
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


@dataclass(frozen=True, slots=True)
class HeroStats:
    phy_attack: int
    phy_defence: int
    magic_attack: int
    magic_defence: int
    force_hit: int
    parry: int
    conat_army: int
    live: int

    @property
    def fighting_capacity(self) -> int:
        # AttackProrertyInfo.totalAttribute + parcela da vida; bate com o oficial (199 na maga nível 1)
        return (
            self.phy_attack + self.phy_defence + int(self.magic_attack * 1.05) + self.magic_defence + self.force_hit
        ) + int(self.live * 0.75)

    @classmethod
    def of(cls, hero: Hero, force_hit: int, parry: int, base_live: int) -> HeroStats:
        # ponytail: fórmulas calibradas só com a maga nível 1 da captura (o cliente não calcula
        # isso, o servidor manda pronto). Trocar pela tabela real quando houver mais capturas.
        return cls(
            phy_attack=2 * hero.power + 2 * hero.agility,
            phy_defence=hero.physique,
            magic_attack=4 * hero.intellect,
            magic_defence=int((hero.intellect + hero.physique) * 0.9),
            force_hit=force_hit,
            parry=parry,
            conat_army=hero.captain,
            live=base_live + 22 * hero.physique,
        )


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
    )
    for prefix in ("total", "base"):
        for name, value in (
            ("Power", hero.power),
            ("Agility", hero.agility),
            ("Intellect", hero.intellect),
            ("Captain", hero.captain),
            ("Physique", hero.physique),
            ("PhyAttack", stats.phy_attack),
            ("PhyDefence", stats.phy_defence),
            ("MagicAttack", stats.magic_attack),
            ("MagicDefence", stats.magic_defence),
            ("ForceHit", stats.force_hit),
            ("Parry", stats.parry),
            ("ConatArmy", stats.conat_army),
            ("Live", stats.live),
        ):
            setattr(msg, prefix + name, value)
    return msg


def player_msg(snap: PlayerSnapshot, fighting_capacity: int, now: datetime) -> pb.PlayerMsg:
    c: Character = snap.character
    msg = pb.PlayerMsg(
        playerId=c.id,
        nickName=c.nickname or "",
        sex=c.sex,
        pic=c.icon,
        camp=c.camp,
        point=c.point,
        giftToken=c.gift_token,
        state=7,
        questSiteLen=QUEST_SITE_LEN,
        questSite=bytes(QUEST_SITE_LEN),
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
    )
    msg.order.playerId = c.id or 0
    return msg


def army_msg(
    snap: PlayerSnapshot, castle: Castle, hero: pb.SimpleHeroInfoMsg, fighting_capacity: int
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
