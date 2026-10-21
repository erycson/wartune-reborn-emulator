"""Fazenda e árvore sobre o ``PlayerSnapshot``: estado das terras, EXP da fazenda e mensagens.

Sementes são itens SonType 216: ``Property1`` = minutos para amadurecer (e o tempo que a planta
madura aguenta antes de morrer, ``FarmLandInfo.isDie``), ``Property2`` = o que rende (moeda < 0 ou
item), ``Property3`` = quanto, ``Property4`` != 0 = pode ter inseto/mato.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from ..domain import gameday
from ..domain.models import Castle, FarmLand, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from .builders import login as b

SEED = "216"
DEFAULT_LANDS, MAX_LANDS = 3, 9  # FarmModel.DEFAULT_OPEN_LAND / MAX_OPEN_LAND
LANDUP_GRADE, MAX_LAND_GRADE = 30, 10  # FarmBuildLayer.__onLandUpClick: fazenda 30, terra até o nível 10
FARM_GRADE, TREE_GRADE = 17, 7  # UpGradeTempInfos.Types da fazenda e da carga da árvore (WaterExpItem)
TREE_COOLDOWN = 600  # TreeInfo.remainWaerTime: lastWaterTime + 10 min
REWARD_PERCENT = 80  # (só turco: ciftlik) rewardCount de moeda = 80% do Property3 (2400/3000, 20000/25000, 8000/10000)
WORM_AT, GRASS_AT = (0.4, 0.6), (0.3, 0.5)  # FarmLandInfo.isWormNow / isGrassNow
MAX_STOLEN, MIN_STEAL_OUTPUT = 3, 10  # FarmModel.MAX_STOLEN_COUNT; FarmLandInfo.canBeStolen (outputCount < 10)
# (cliente) language EN farm.view.FarmResourcesView.helpContent: "energize your Tree of Ancients 3 times a day",
# "energize the Tree of Ancients for your friends 200 times a day", "a friend's Tree of Ancients once a day"
OWN_TREE_DAILY, FRIEND_TREE_DAILY = 3, 200
# (internet) resumo da busca sobre https://breezewiki.discard.no/wartune/wiki/Farm (espelho de
# wartune.fandom.com/wiki/Farm; a página não abriu): o amigo leva uma pequena parte (10%) do valor, até 3 vezes.
# Configurável em game_settings farm_steal_percent
STEAL_PERCENT = 10
# game_settings tree_fruit (0041, internet: wiki Farm): [base, por nível acima do 1] de Daru e Kyanite
TREE_FRUIT = {"daru": [3800, 3800], "kyanite": [1000, 100]}


def open_lands(farm_grade: int) -> int:
    """FarmLandLayer.addLandInfoToItem: a terra p (3..8) abre com a fazenda no nível (p - 2) * 5; 9..11 nunca."""
    return min(MAX_LANDS, DEFAULT_LANDS + farm_grade // 5)


def land_up_cost(land_grade: int) -> int:
    """FarmSocketSendManager.sendLandUp: n(n+1)(n+2)/2 + 15 do nível n para n+1 (18, 27, 45... como a wiki)."""
    return land_grade * (land_grade + 1) * (land_grade + 2) // 2 + 15


def tree_need(templates: GameTemplates, farm_grade: int) -> int | None:
    """Regas para a carga cheia: ``UpGradeTempInfos`` tipo 7 no grau da fazenda (WaterExpItem, 10..30)."""
    row = next(templates.find("UpGradeTempInfos", Types=TREE_GRADE, Grades=farm_grade), None)
    return int(row["Data"]) if row else None


def tree_charge(castle: Castle, templates: GameTemplates) -> None:
    """Carga cheia vira fruto (WaterViewContainer: cheia, a rega para; ``fruitCount`` > 0 libera a colheita)."""
    need = tree_need(templates, castle.farm_grade)
    if need is not None and castle.tree_water >= need:
        castle.tree_fruit = 1


def tree_reward(config: Mapping[str, Any], farm_grade: int) -> tuple[int, int]:
    """Daru e Kyanite da colheita da árvore no grau da fazenda (a árvore sobe junto com a fazenda, wiki)."""
    up = farm_grade - 1
    (daru, daru_step), (kyanite, kyanite_step) = config["daru"], config["kyanite"]
    return int(daru) + int(daru_step) * up, int(kyanite) + int(kyanite_step) * up


def next_pick(picked_at: datetime) -> datetime:
    """``TreeInfo.remainPickTime``: depois de colher, só na próxima meia-noite (não às 5h) do fuso do jogo."""
    day = gameday.local(picked_at).date() + timedelta(days=1)
    return datetime.combine(day, datetime.min.time(), gameday.GAME_TZ)


def tree_pick_left(castle: Castle, now: datetime) -> int:
    if castle.tree_picked_at is None:
        return 0
    return max(0, int((next_pick(castle.tree_picked_at) - now).total_seconds()))


def seed(templates: GameTemplates, template_id: int) -> Row | None:
    row = templates.get("ItemTempInfos", template_id)
    return row if row is not None and row.get("SonType") == SEED else None


def plant(snap: PlayerSnapshot, row: Row, pos: int, now: datetime, faster: int = 0, more: int = 0) -> FarmLand:
    """``faster``/``more``: % a menos de tempo e a mais de produção da terra melhorada (LandUpTip)."""
    minutes = int(row["Property1"]) * (100 - faster) / 100  # (dedução) arredondamento sem fonte
    pests = int(row.get("Property4") or 0) != 0
    land = FarmLand(
        snap.character.id or 0,
        pos,
        int(row["TemplateId"]),
        now,
        # (só turco: ciftlik.json) amadurece 1 minuto antes do Property1 (60 -> 59 min, 720 -> 719 min)
        now + timedelta(minutes=max(minutes - 1, 0)),
        int(row["Property3"]) * (REWARD_PERCENT if int(row["Property2"]) < 0 else 100) * (100 + more) // 10000,
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
        nextPickTime=b.fmt_time(next_pick(castle.tree_picked_at)) if castle.tree_picked_at else b.NEVER,
        property1=0,
        property2=0,
    )
    if castle.tree_watered_at is not None:
        msg.lastWaterTime = b.fmt_time(castle.tree_watered_at)
    if own:  # leftTime/leftPickTime só valem para a árvore do próprio jogador
        msg.leftTime, msg.leftPickTime = tree_left(castle, now), tree_pick_left(castle, now)
    return msg


def farm_info(snap: PlayerSnapshot, now: datetime, *, own: bool) -> pb.FarmInfoRspMsg:
    c, castle = snap.character, snap.castle
    assert castle is not None
    by_pos = {land.pos: land for land in snap.lands}
    # os contadores do dia só valem na própria fazenda (o cliente lê do myFarm); a amiga vem 0 (só turco: ciftlik #80)
    today = own and castle.farm_day == gameday.today(now)
    return pb.FarmInfoRspMsg(
        userId=c.id or 0,
        nickName=c.nickname or "",
        grades=castle.farm_grade,
        landGrades=castle.land_grade,
        gp=castle.farm_gp,
        totalGp=castle.farm_gp,
        todayFromFriendGp=castle.farm_friend_gp if today else 0,
        farmLandInfo=[land_msg(c.id or 0, pos, by_pos.get(pos)) for pos in range(open_lands(castle.farm_grade))],
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
    """4190 de um amigo (só turco: ciftlik #3): o que ``viewer_id`` pode fazer na fazenda dele agora."""
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
