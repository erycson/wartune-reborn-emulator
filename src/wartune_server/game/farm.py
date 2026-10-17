"""Fazenda e árvore sobre o ``PlayerSnapshot``: estado das terras, EXP da fazenda e mensagens.

Sementes são itens SonType 216: ``Property1`` = minutos para amadurecer (e o tempo que a planta
madura aguenta antes de morrer, ``FarmLandInfo.isDie``), ``Property2`` = o que rende (moeda < 0 ou
item), ``Property3`` = quanto, ``Property4`` != 0 = pode ter inseto/mato.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from ..domain.models import Castle, FarmLand, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from .builders import login as b

SEED = "216"
OPEN_LANDS = 3  # FarmModel.DEFAULT_OPEN_LAND; ponytail: sem upgrade de terra (opType 9 não tem sender)
FARM_GRADE = 17  # UpGradeTempInfos.Types da fazenda
TREE_COOLDOWN = 600  # TreeInfo.remainWaerTime: lastWaterTime + 10 min
REWARD_PERCENT = 80  # ciftlik.json: rewardCount de moeda = 80% do Property3 (2400/3000, 20000/25000, 8000/10000)
WORM_AT, GRASS_AT = (0.4, 0.6), (0.3, 0.5)  # FarmLandInfo.isWormNow / isGrassNow


def seed(templates: GameTemplates, template_id: int) -> Row | None:
    row = templates.get("ItemTempInfos", template_id)
    return row if row is not None and row.get("SonType") == SEED else None


def plant(snap: PlayerSnapshot, row: Row, pos: int, now: datetime) -> FarmLand:
    minutes = int(row["Property1"])
    pests = int(row.get("Property4") or 0) != 0
    land = FarmLand(
        snap.character.id or 0,
        pos,
        int(row["TemplateId"]),
        now,
        # ciftlik.json: amadurece 1 minuto antes do Property1 (60 -> 59 min, 720 -> 719 min)
        now + timedelta(minutes=max(minutes - 1, 0)),
        int(row["Property3"]) * (REWARD_PERCENT if int(row["Property2"]) < 0 else 100) // 100,
        random.choice((1, 2)) if pests else 0,
        random.choice((1, 2)) if pests else 0,
    )
    snap.lands.append(land)
    return land


def is_mature(land: FarmLand, now: datetime) -> bool:
    return land.mature_at <= now


def is_dead(land: FarmLand, row: Row | None, now: datetime) -> bool:
    return row is not None and now > land.mature_at + timedelta(minutes=int(row["Property1"]))


def _pest_now(land: FarmLand, which: int, at: tuple[float, float], now: datetime) -> bool:
    if which == 0 or is_mature(land, now):
        return False
    cycle = (land.mature_at - land.planted_at).total_seconds()
    return now > land.planted_at + timedelta(seconds=cycle * at[which - 1])


def has_worm(land: FarmLand, now: datetime) -> bool:
    return _pest_now(land, land.worm, WORM_AT, now)


def has_grass(land: FarmLand, now: datetime) -> bool:
    return _pest_now(land, land.grass, GRASS_AT, now)


def add_farm_gp(castle: Castle, player_grade: int, templates: GameTemplates, gp: int) -> None:
    """Soma EXP da fazenda e sobe de nível; parada no nível do jogador, a EXP enche e trava
    (``FarmModel.expByOper``). No nível máximo não ganha mais nada."""
    castle.farm_gp += gp
    while need := next(templates.find("UpGradeTempInfos", Types=FARM_GRADE, Grades=castle.farm_grade + 1), None):
        if castle.farm_gp < int(need["Data"]):
            return
        if castle.farm_grade >= player_grade:
            castle.farm_gp = int(need["Data"])
            return
        castle.farm_gp -= int(need["Data"])
        castle.farm_grade += 1
    castle.farm_gp = 0  # nível máximo


# --- mensagens -----------------------------------------------------------------------------------


def land_msg(user_id: int, pos: int, land: FarmLand | None) -> pb.FarmLandInfoMsg:
    """Nunca preencher ``param1``/``param2``: o cliente responde com o 8598 (anti-cheat)."""
    if land is None:
        return pb.FarmLandInfoMsg(userId=user_id, pos=pos, plantingTime=b.NEVER, matureTime=b.NEVER, rewardCount=0)
    return pb.FarmLandInfoMsg(
        userId=user_id,
        pos=pos,
        itemTemplateId=land.item_template_id,
        plantingTime=b.fmt_time(land.planted_at),
        matureTime=b.fmt_time(land.mature_at),
        accelerateCount=int(land.accelerated),
        stolenCount=0,
        isWormParam1=land.worm == 1,
        isWormParam2=land.worm == 2,
        isGrassParam1=land.grass == 1,
        isGrassParam2=land.grass == 2,
        rewardCount=land.reward_count,
    )


def tree_left(castle: Castle, now: datetime) -> int:
    if castle.tree_watered_at is None:
        return 0
    return max(0, int((castle.tree_watered_at - now).total_seconds()) + TREE_COOLDOWN)


def tree_msg(snap: PlayerSnapshot, now: datetime, *, own: bool) -> pb.TreeInfoMsg:
    """``nextPickTime`` nunca vazio: o cliente faz ``DateFormatter.parse`` e compara."""
    c, castle = snap.character, snap.castle
    assert castle is not None
    msg = pb.TreeInfoMsg(
        userId=c.id or 0,
        nickName=c.nickname or "",
        waterCount=castle.tree_water,
        fruitCount=castle.tree_fruit,
        nextPickTime=b.fmt_time(castle.tree_picked_at) if castle.tree_picked_at else b.NEVER,
        property1=0,
        property2=0,
    )
    if castle.tree_watered_at is not None:
        msg.lastWaterTime = b.fmt_time(castle.tree_watered_at)
    if own:  # leftTime/leftPickTime só valem para a árvore do próprio jogador
        msg.leftTime, msg.leftPickTime = tree_left(castle, now), 0
    return msg


def farm_info(snap: PlayerSnapshot, now: datetime, *, own: bool) -> pb.FarmInfoRspMsg:
    c, castle = snap.character, snap.castle
    assert castle is not None
    by_pos = {land.pos: land for land in snap.lands}
    return pb.FarmInfoRspMsg(
        userId=c.id or 0,
        nickName=c.nickname or "",
        grades=castle.farm_grade,
        landGrades=1,
        gp=castle.farm_gp,
        totalGp=castle.farm_gp,
        todayFromFriendGp=0,
        farmLandInfo=[land_msg(c.id or 0, pos, by_pos.get(pos)) for pos in range(OPEN_LANDS)],
        treeInfo=tree_msg(snap, now, own=own),
        todayStolenCount=0,
    )


def own_state(snap: PlayerSnapshot, now: datetime) -> pb.FriendFarmStateMsg:
    """O 4190 do oficial começa pelo próprio jogador: ``isChargeEnergy`` libera regar a própria árvore."""
    assert snap.castle is not None
    can_water = tree_left(snap.castle, now) <= 0 and snap.castle.tree_fruit == 0
    return pb.FriendFarmStateMsg(userId=snap.character.id or 0, isChargeEnergy=can_water)
