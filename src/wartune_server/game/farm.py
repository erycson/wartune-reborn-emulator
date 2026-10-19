"""Fazenda e árvore sobre o ``PlayerSnapshot``: estado das terras, EXP da fazenda e mensagens.

Sementes são itens SonType 216: ``Property1`` = minutos para amadurecer (e o tempo que a planta
madura aguenta antes de morrer, ``FarmLandInfo.isDie``), ``Property2`` = o que rende (moeda < 0 ou
item), ``Property3`` = quanto, ``Property4`` != 0 = pode ter inseto/mato.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from ..domain import gameday
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
MAX_STOLEN, MIN_STEAL_OUTPUT = 3, 10  # FarmModel.MAX_STOLEN_COUNT; FarmLandInfo.canBeStolen (outputCount < 10)
# (cliente) language EN farm.view.FarmResourcesView.helpContent: "energize your Tree of Ancients 3 times a day",
# "energize the Tree of Ancients for your friends 200 times a day", "a friend's Tree of Ancients once a day"
OWN_TREE_DAILY, FRIEND_TREE_DAILY = 3, 200
# (internet) https://breezewiki.discard.no/wartune/wiki/Farm (espelho de wartune.fandom.com/wiki/Farm): o amigo
# leva "a small portion of the plant's value (10%)", até 3 vezes; configurável em game_settings farm_steal_percent
STEAL_PERCENT = 10


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


def is_alive_mature(land: FarmLand, row: Row | None, now: datetime) -> bool:
    return is_mature(land, now) and not is_dead(land, row, now)


def stolen_by(land: FarmLand) -> list[int]:
    return [int(x) for x in land.stolen_by.split(",") if x]


def can_steal(land: FarmLand, row: Row | None, thief_id: int, now: datetime) -> bool:
    """``FarmLandInfo.canBeStolen`` + ``checkHasOperNow(5)``: madura e viva, não roubada por ele, menos de 3
    roubos e ao menos 10 de produção."""
    taken = stolen_by(land)
    return (
        is_alive_mature(land, row, now)
        and thief_id not in taken
        and len(taken) < MAX_STOLEN
        and land.reward_count >= MIN_STEAL_OUTPUT
    )


def roll_day(castle: Castle, now: datetime) -> None:
    """Zera os contadores do dia da fazenda (o dia do jogo vira às 5h)."""
    if castle.farm_day != gameday.today(now):
        castle.farm_day = gameday.today(now)
        castle.farm_friend_gp = castle.farm_steals = castle.tree_water_today = castle.tree_friend_today = 0


def add_friend_gp(castle: Castle, player_grade: int, templates: GameTemplates, gp: int, cap: int) -> int:
    """EXP da fazenda vinda de amigo, até ``cap`` (Farm_TodayFromFriend_GP) no dia; no teto a ação vale e
    rende 0 (FarmModel.expByOper, "dayGpFull"). Devolve o que entrou."""
    gp = max(0, min(gp, cap - castle.farm_friend_gp))
    castle.farm_friend_gp += gp
    add_farm_gp(castle, player_grade, templates, gp)
    return gp


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
        stolenCount=len(stolen_by(land)),
        stolenUsers=stolen_by(land),
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
    # os contadores do dia só valem na própria fazenda (o cliente lê do myFarm); a de amigo vem 0 (ciftlik #80)
    today = own and castle.farm_day == gameday.today(now)
    return pb.FarmInfoRspMsg(
        userId=c.id or 0,
        nickName=c.nickname or "",
        grades=castle.farm_grade,
        landGrades=1,
        gp=castle.farm_gp,
        totalGp=castle.farm_gp,
        todayFromFriendGp=castle.farm_friend_gp if today else 0,
        farmLandInfo=[land_msg(c.id or 0, pos, by_pos.get(pos)) for pos in range(OPEN_LANDS)],
        treeInfo=tree_msg(snap, now, own=own),
        todayStolenCount=castle.farm_steals if today else 0,
    )


def waters_today(castle: Castle, now: datetime) -> tuple[int, int]:
    """Regas do dia (própria, de amigos) sem gravar a virada."""
    return (castle.tree_water_today, castle.tree_friend_today) if castle.farm_day == gameday.today(now) else (0, 0)


def own_state(snap: PlayerSnapshot, now: datetime) -> pb.FriendFarmStateMsg:
    """O 4190 do oficial começa pelo próprio jogador: ``isChargeEnergy`` libera regar a própria árvore."""
    assert snap.castle is not None
    can_water = (
        tree_left(snap.castle, now) <= 0
        and snap.castle.tree_fruit == 0
        and waters_today(snap.castle, now)[0] < OWN_TREE_DAILY
    )
    return pb.FriendFarmStateMsg(userId=snap.character.id or 0, isChargeEnergy=can_water)


def friend_state(
    viewer_id: int, target: PlayerSnapshot, templates: GameTemplates, now: datetime, *, can_water: bool
) -> pb.FriendFarmStateMsg:
    """4190 de um amigo (visto ciftlik #3): o que ``viewer_id`` pode fazer na fazenda dele agora."""
    rows = [(land, seed(templates, land.item_template_id)) for land in target.lands]
    return pb.FriendFarmStateMsg(
        userId=target.character.id or 0,
        isReap=any(can_steal(land, row, viewer_id, now) for land, row in rows),
        isChargeEnergy=can_water,
        isRevive=any(is_dead(land, row, now) for land, row in rows),
        isWorm=any(has_worm(land, now) for land, _ in rows),
        isGrass=any(has_grass(land, now) for land, _ in rows),
        isFeed=False,
    )
