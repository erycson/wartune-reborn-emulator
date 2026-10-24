"""Fazenda (15044), árvore (15017, 5178, 8219, 8231) (8565 árvore da guilda: guild_events.py). Ver docs/castelo.md.

Na própria fazenda: plantar, praga, colher, acelerar e limpar. Na de amigo (relação ``FRIEND``, que é dos dois
lados): praga (2/3), roubar (5), reviver (6) e regar a árvore dele (15017 com ``userId``). O dono pode estar
online (mexe-se no snapshot da sessão dele, como ``social.row_of``) ou offline (snapshot do banco).
"""

from __future__ import annotations

from datetime import timedelta

from ...domain import gameday
from ...domain.errors import NotFoundError
from ...domain.models import BagType, FarmLand, Item, PlayerSnapshot, Relation, RelationType
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import pay, record_cash
from .. import bag, farm, rules, social
from .. import castle as cs
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..router import router
from ..session import GameSession
from .login import player_info
from .player import CURRENCIES, push_level

S_PLAYER, S_CHAT, S_ALERT, S_ITEMS, S_QUESTS = 3, 83, 111, 115, 112
S_FARM_INFO, S_FARM_LAND, S_TREE, S_FRIEND_TREE, S_CAN_WATER = 4386, 4387, 147, 4146, 4190
S_HARVEST, S_WATER_LOG, S_FRIEND_UPDATE, S_TREE_PICK, S_PICK_HARVEST = 146, 4158, 165, 106, 4189
REQ, PLANT, WORM, WEED, PICK, STEAL, REVIVE, ACCELERATE, CLEAR, LAND_UP = range(10)  # FarmOperateType
OK, FAIL = 0, 1
EXP = -700  # ItemTempInfos -700: as sementes de EXP rendem EXP do jogador
QUEST_PLANT, QUEST_HARVEST, QUEST_BUG = 59, 60, 61  # QuestCondictionInfos: plantar, colher, pegar praga
BUG_PARA1 = 1  # Para1 da praga: vale a fazenda própria ou de amigo (QuestTemps 267/862, Detail)
OWN_FARM, FRIEND_FARM = 0, 1  # Para1 do tipo 60: 263/860 a própria, 266/861 a de amigo
OWN_TREE, FRIEND_TREE = 1, 0  # Para1 do tipo 20: 260 a própria, 22/261/271 a de amigo
MAX_IDS = 100  # listas de amigos que o cliente manda (8219/8231)
TREE_PICK_GP = 1  # FarmModel._expTreePick (expByOper 11, somado pelo cliente no 4189)
TREE_GOLD = 20  # ouro por grau da fazenda do dono ao regar a árvore (oficial_20261023-153200-1 #2228, #2242)
REVIVE_BACK = timedelta(minutes=1)  # (visto, só turco: ciftlik #88-#89) reviver às 20:22:41 dá matureTime 20:21:42


def _config(s: GameSession, name: str, default: int) -> int:
    row = next(s.ctx.templates.find("ConfigInfos", ConfigName=name), None)
    return int(row["ConfigValue"]) if row else default


async def _other(s: GameSession, user_id: int) -> PlayerSnapshot | None:
    """Snapshot de outro jogador: o da sessão se online (mais novo que o banco), senão do banco."""
    online = s.ctx.online.get(user_id)
    if online is not None and online.snapshot is not None:
        return online.snapshot
    try:
        snap = await s.ctx.characters.snapshot(user_id)
    except NotFoundError:
        return None
    return snap if snap.castle is not None and snap.character.active else None


async def _friend(s: GameSession, user_id: int) -> tuple[PlayerSnapshot, Relation] | None:
    """Amigo (``FRIEND`` já é a amizade dos dois lados, docs/social.md) com castelo."""
    r = social.relation_to(s, user_id)
    if r is None or r.relation != RelationType.FRIEND:
        return None
    target = await _other(s, user_id)
    return (target, r) if target is not None else None


def _land_reply(s: GameSession, owner_id: int, pos: int, land: FarmLand | None, op: int, result: int) -> None:
    """4387 com o ``userId`` do dono da terra: o cliente só aplica na fazenda de mesmo ``userId``."""
    msg = farm.land_msg(owner_id, pos, land)
    msg.opType, msg.result = op, result
    s.send(S_FARM_LAND, pb.FarmInfoRspMsg(farmLandInfo=[msg]))


@router.on(15044)
async def farm_operate(s: GameSession, msg: pb.FarmOperReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    now = s.ctx.clock.now()
    if msg.opType == REQ:
        target = snap if msg.friendId in (0, s.player_id) else await _other(s, msg.friendId)
        if target is not None:
            s.send(S_FARM_INFO, b.complete(farm.farm_info(target, now, own=target is snap)))
        return
    own = msg.friendId in (0, s.player_id)
    if msg.opType > LAND_UP:  # 12-16 terras de mascote e guarda: o 4387 de falha cairia num canteiro (pos -1 no guarda)
        s.log.info("15044 recusado: cultivo de mascote sem regra (precisa captura)", op=msg.opType)
        return
    if msg.opType == LAND_UP:  # sem pos e sem 4387 (um 4387 de falha apagaria a terra 0 no cliente)
        if not own or not await _land_up(s, snap, msg):
            s.log.info("15044 recusado", op=LAND_UP, nivel=snap.castle.land_grade, fazenda=snap.castle.farm_grade)
        return
    owner_id = s.player_id if own else msg.friendId
    found = None if own else await _friend(s, msg.friendId)
    target = snap if own else (found[0] if found else None)
    lands = farm.open_lands(target.castle.farm_grade) if target is not None and target.castle is not None else 0
    if target is None or not 0 <= msg.pos < lands:
        s.log.info("15044 recusado", motivo="não é amigo ou terra fechada", op=msg.opType, friend=msg.friendId)
        _land_reply(s, owner_id, msg.pos, None, msg.opType, FAIL)
        return
    land = next((x for x in target.lands if x.pos == msg.pos), None)
    actions = (
        {PLANT: _plant, WORM: _pest, WEED: _pest, PICK: _pick, ACCELERATE: _accelerate, CLEAR: _clear}
        if own
        else {WORM: _pest, WEED: _pest, STEAL: _steal, REVIVE: _revive}
    )
    action = actions.get(msg.opType)
    if action is None or not await action(s, snap, target, msg, land):
        s.log.info("15044 recusado", op=msg.opType, pos=msg.pos, friend=msg.friendId)
        _land_reply(s, owner_id, msg.pos, land, msg.opType, FAIL)  # o cliente mostra a dica de falha


async def _plant(
    s: GameSession, snap: PlayerSnapshot, _: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    c, now = snap.character, s.ctx.clock.now()
    item = next((i for i in snap.items if (i.bag_type, i.pos) == (BagType.BAG, msg.bagPos)), None)
    row = farm.seed(s.ctx.templates, item.template_id) if item is not None else None
    if land is not None or item is None or row is None or item.template_id != msg.templateId:
        return False
    if int(row.get("NeedGrades") or 0) > c.grades:
        return False
    special = row.get("Property5") or "0"
    if special != "0" and any(
        (farm.seed(s.ctx.templates, x.item_template_id) or {}).get("Property5") == special for x in snap.lands
    ):
        return False  # FarmManager: só uma semente especial de cada tipo plantada por vez
    item.count -= 1
    if item.count <= 0:
        snap.items.remove(item)
    assert snap.castle is not None
    up = snap.castle.land_grade - 1  # LandUpTip: -2% de tempo e +3% de produção por nível da terra acima do 1
    faster, more = up * _config(s, "FarmCrop_Mature_Percent", 2), up * _config(s, "FarmCrop_Gains_Percent", 3)
    new = farm.plant(snap, row, msg.pos, now, faster, more)
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_PLANT, 0, 1)
    if item.count > 0:
        await s.ctx.characters.save(item, new, *quests)
    else:
        await s.ctx.characters.save(new, *quests, delete=(item,))
    s.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item if item.count > 0 else None, s.player_id))
    _land_reply(s, s.player_id, msg.pos, new, PLANT, OK)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    return True


def _helper_gp(s: GameSession, snap: PlayerSnapshot, target: PlayerSnapshot, gp: int) -> None:
    """EXP da fazenda de quem ajudou: na própria, direto; na de amigo, até o teto do dia (expByOper)."""
    assert snap.castle is not None
    grade, templates, before = snap.character.grades, s.ctx.templates, snap.castle.farm_grade
    if target is snap:
        farm.add_farm_gp(snap.castle, grade, templates, gp)
    else:
        farm.roll_day(snap.castle, s.ctx.clock.now())
        farm.add_friend_gp(snap.castle, grade, templates, gp, _config(s, "Farm_TodayFromFriend_GP", 200))
    _farm_up(s, snap, before)  # (dedução) na hora, como na rega do amigo


def _farm_up(s: GameSession, snap: PlayerSnapshot, before: int) -> bool:
    """A fazenda subiu de ``before``: 111, 4386 (a própria) e 83 "Your farm has been upgraded to level N!".
    (visto) oficial_20261023-215937-1 #1279-#1281, regando a árvore de um amigo (fazenda 2 -> 3)."""
    assert snap.castle is not None
    if snap.castle.farm_grade <= before:
        return False
    text = f"Your farm has been upgraded to level {snap.castle.farm_grade}!"
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_FARM_INFO, b.complete(farm.farm_info(snap, s.ctx.clock.now(), own=True)))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    return True


async def _pest(
    s: GameSession, snap: PlayerSnapshot, target: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    assert snap.castle is not None
    now = s.ctx.clock.now()
    worm = msg.opType == WORM
    if land is None or not (farm.has_worm(land, now) if worm else farm.has_grass(land, now)):
        return False
    if worm:
        land.worm = 0
    else:
        land.grass = 0
    _helper_gp(s, snap, target, _config(s, "FarmCrop_Operate_GP", 1))
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_BUG, BUG_PARA1, 1) if worm else []  # o mato não conta
    await s.ctx.characters.save(land, snap.castle, *quests)
    _land_reply(s, target.character.id or 0, msg.pos, land, msg.opType, OK)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    return True


def _payout(
    s: GameSession, snap: PlayerSnapshot, reward: int, count: int, ref: str
) -> tuple[list[object], Item | None, int] | None:
    """Dá ``count`` de ``reward`` (moeda < 0, EXP -700 ou item) a quem colhe ou rouba. ``None`` = não cabe: ouro no
    teto (FarmLandItem.checkGoldLimit, o cliente também bloqueia), mochila cheia ou item sem template."""
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    field = CURRENCIES.get(reward)
    if reward < 0 and field is None and reward != EXP:
        return None
    if field == "gold" and cs.yield_msg(snap, templates, now).goldTotalCount >= cs.gold_max(snap, templates, now):
        return None
    item = Item(c.id or 0, reward, count=count, pos=rules.free_bag_pos(snap)) if reward > 0 else None
    full = not bag.free_positions(snap, now)
    if item is not None and (full or not templates.get("ItemTempInfos", reward)):
        return None
    changed: list[object] = [c]
    gained = 0
    if item is not None:
        snap.items.append(item)
        changed.append(item)
    elif reward == EXP:
        gained = rules.add_gp(snap, templates, count)
        changed += [snap.leader, *snap.pawns]
    else:
        assert field is not None
        if field == "gold":
            cs.settle(snap, templates, now)
            changed.append(snap.castle)
        setattr(c, field, getattr(c, field) + count)
        if field in ("point", "gift_token"):
            delta = (count, 0) if field == "point" else (0, count)
            changed.append(record_cash(c, *delta, reason="farm_pick", ref=ref, now=now))
    return changed, item, gained


async def _payout_sent(s: GameSession, snap: PlayerSnapshot, reward: int, item: Item | None, gained: int) -> None:
    if item is not None:
        s.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
    if CURRENCIES.get(reward) in ("gold", "crystals"):
        cs.castle_yield(s)
    else:
        s.send(S_PLAYER, b.complete(player_info(s, snap)))
    if gained:
        await push_level(s, snap.character.grades - gained)  # (dedução) como na entrega de missão


async def _pick(
    s: GameSession, snap: PlayerSnapshot, _: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    """Colhe: moeda (ouro, alma, cristal, diamante vinculado), EXP (-700) ou item, e libera a terra."""
    templates, now = s.ctx.templates, s.ctx.clock.now()
    row = farm.seed(templates, land.item_template_id) if land is not None else None
    if land is None or row is None or not farm.is_alive_mature(land, row, now):
        return False
    reward = int(row["Property2"])
    paid = _payout(s, snap, reward, land.reward_count, f"seed:{land.item_template_id}")
    if paid is None:
        return False
    changed, item, gained = paid
    snap.lands.remove(land)
    quests = rules.quest_event(snap, templates, QUEST_HARVEST, OWN_FARM, 1)
    await s.ctx.characters.save(*changed, *quests, delete=(land,))
    from . import events  # handlers.events importa login

    await events.leed_done(s, events.FARM_LEED)  # (dedução) "Harvest from your own farm"; ordem sem captura
    _land_reply(s, s.player_id, msg.pos, None, PICK, OK)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    await _payout_sent(s, snap, reward, item, gained)
    return True


async def _steal(
    s: GameSession, snap: PlayerSnapshot, target: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    """Rouba da terra madura do amigo (FarmLandInfo.canBeStolen): uma vez por terra, até 3 ladrões, produção
    de 10 ou mais; até ``Farm_TodayStolen_Count`` roubos no dia. Leva ``farm_steal_percent`` % do que resta
    (internet: 10%), que sai do ``rewardCount`` do dono. Sem EXP (``expByOper`` não tem o caso 5)."""
    assert snap.castle is not None
    templates, now, me = s.ctx.templates, s.ctx.clock.now(), s.player_id
    row = farm.seed(templates, land.item_template_id) if land is not None else None
    if land is None or row is None or not farm.can_steal(land, row, me, now):
        return False
    farm.roll_day(snap.castle, now)
    if snap.castle.farm_steals >= _config(s, "Farm_TodayStolen_Count", 200):
        return False
    pct = int(s.ctx.world.settings.get("farm_steal_percent", farm.STEAL_PERCENT))
    amount = land.reward_count * pct // 100
    reward = int(row["Property2"])
    paid = _payout(s, snap, reward, amount, f"steal:{target.character.id}:{land.item_template_id}") if amount else None
    if paid is None:
        return False
    changed, item, gained = paid
    land.reward_count -= amount
    land.stolen_by = ",".join(str(x) for x in [*farm.stolen_by(land), me])
    snap.castle.farm_steals += 1
    quests = rules.quest_event(snap, templates, QUEST_HARVEST, FRIEND_FARM, 1)
    # ponytail: dono offline vem do banco; dois ladrões ao mesmo tempo em cópias diferentes podem se sobrepor
    await s.ctx.characters.save(*changed, land, snap.castle, *quests)
    _land_reply(s, target.character.id or 0, msg.pos, land, STEAL, OK)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    await _payout_sent(s, snap, reward, item, gained)
    return True


async def _revive(
    s: GameSession, snap: PlayerSnapshot, target: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    """Revive a planta morta do amigo (só amigo revive: "Dead crops must be revived by friends"). (visto, só
    turco: ciftlik #88-#105) só o ``matureTime`` muda, para 1 minuto antes de agora; produção, roubos e pragas ficam.
    EXP ``FarmCrop_Operate_GP`` (expByOper, caso 6)."""
    assert snap.castle is not None
    now = s.ctx.clock.now()
    if land is None or not farm.is_dead(land, farm.seed(s.ctx.templates, land.item_template_id), now):
        return False
    land.mature_at = now - REVIVE_BACK
    _helper_gp(s, snap, target, _config(s, "FarmCrop_Operate_GP", 1))
    await s.ctx.characters.save(land, snap.castle)
    _land_reply(s, target.character.id or 0, msg.pos, land, REVIVE, OK)
    return True


async def _accelerate(
    s: GameSession, snap: PlayerSnapshot, _: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    """Uma vez por plantio (hasAccelerateTip): "50% maturity speed-up will consume {0} Balens"
    (farm.view.FarmOperMenu.accelerateTip, ``Farm_Accelerate_Point`` = 35): metade do que falta."""
    c, now = snap.character, s.ctx.clock.now()
    if land is None or land.accelerated or farm.is_mature(land, now):
        return False
    cost = _config(s, "Farm_Accelerate_Point", 35)
    entry = pay(c, cost, bind=msg.payType == 0, reason="farm_accelerate", ref=f"land:{land.pos}", now=now)
    if entry is None:
        return False
    land.mature_at, land.accelerated = now + (land.mature_at - now) / 2, True
    await s.ctx.characters.save(c, land, entry)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    _land_reply(s, s.player_id, msg.pos, land, ACCELERATE, OK)
    return True


async def _land_up(s: GameSession, snap: PlayerSnapshot, msg: pb.FarmOperReqMsg) -> bool:
    """Melhora as terras (FarmBuildLayer.__onLandUpClick, FarmSocketSendManager.sendLandUp): fazenda no nível 30+,
    terra até o 10, custo ``farm.land_up_cost``; ``payType`` 0 = vinculados primeiro. O 4387 não lê ``landGrades``:
    a volta é o 4386 (readFarmInfoMsg -> LAND_GRADE_CHANGE)."""
    castle, c, now = snap.castle, snap.character, s.ctx.clock.now()
    assert castle is not None
    if castle.farm_grade < farm.LANDUP_GRADE or castle.land_grade >= farm.MAX_LAND_GRADE:
        return False
    cost, ref = farm.land_up_cost(castle.land_grade), f"land_grade:{castle.land_grade + 1}"
    entry = pay(c, cost, bind=msg.payType == 0, reason="farm_land_up", ref=ref, now=now)
    if entry is None:
        return False
    castle.land_grade += 1
    await s.ctx.characters.save(c, castle, entry)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    s.send(S_FARM_INFO, b.complete(farm.farm_info(snap, now, own=True)))
    return True


async def _clear(
    s: GameSession, snap: PlayerSnapshot, _: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    if land is None:
        return False
    snap.lands.remove(land)
    await s.ctx.characters.save(delete=(land,))
    _land_reply(s, s.player_id, msg.pos, None, CLEAR, OK)
    return True


@router.on(15017)
async def tree_water(s: GameSession, msg: pb.BuildingReqMsg) -> None:
    """Rega a própria árvore a cada 10 minutos, 3 vezes por dia (ouro, energia e EXP da fazenda; inglês:
    oficial_20261023-153200-1 #2226-#2230: 109, 146, 83, 147); com ``userId`` de amigo, a árvore dele
    (``_water_friend``)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    if msg.userId not in (0, s.player_id):
        await _water_friend(s, snap, msg.userId)
        return
    c, castle, templates, now = snap.character, snap.castle, s.ctx.templates, s.ctx.clock.now()
    farm.roll_day(castle, now)
    if farm.tree_left(castle, now) > 0 or castle.tree_fruit > 0 or castle.tree_water_today >= farm.OWN_TREE_DAILY:
        s.log.info("15017 recusado", motivo="em espera, com fruto ou 3 no dia", hoje=castle.tree_water_today)
        return
    # ouro = grau da fazenda do dono x 20: (visto) oficial_20261023-153200-1 #2226-#2229, 20 com a fazenda no grau 1
    # (o jogador no nível 12); #2236-#2243, 920 no amigo de fazenda 46. Bate com o turco (ciftlik: 220 e 1.320)
    gold = castle.farm_grade * TREE_GOLD
    cs.settle(snap, templates, now)
    c.gold += gold
    # o "Enerji + 1" do texto é a carga da árvore (waterCount), não a energia de teleporte
    # (internet) https://wartune.fandom.com/wiki/Tree_of_Ancients
    castle.tree_water, castle.tree_watered_at = castle.tree_water + 1, now
    castle.tree_water_today += 1
    before = castle.farm_grade
    farm.add_farm_gp(castle, c.grades, templates, 1)
    farm.tree_charge(castle, templates)
    quests = rules.quest_event(snap, templates, rules.TREE_CONDITION, OWN_TREE, 1)
    await s.ctx.characters.save(c, castle, *quests)
    # (visto) oficial_20261023-171155-1 #4933: 4158 da própria árvore antes do 109 na 3ª rega (waterCount 3); sem ele
    # na 1ª e 2ª (oficial_20261023-153200-1 #2227, 171155 #203). (cliente) WaterManager.__waterStateHandler só desliga o
    # ``canGivePower``; (dedução) por isso sai quando acaba a cota do dia
    if castle.tree_water_today >= farm.OWN_TREE_DAILY:
        s.send(S_WATER_LOG, pb.FarmLogRsp(playerId=s.player_id, operUserId=s.player_id))
    cs.castle_yield(s)
    up = _farm_up(s, snap, before)  # (dedução) no mesmo lugar da rega do amigo
    # (visto) oficial_20261023-153200-1 #2228-#2229: os textos ingleses (a vírgula de milhar é dedução)
    lines = ["Energy +1", f"Gold +{gold:,}", "Tree of the Ancients EXP +1"]
    s.send(S_HARVEST, pb.TreeUpdateRsp(harvestMsg=lines, isUpGrade=up))
    text = f"Energized Successfully,Gold +{gold:,},Energy +1,Tree of the Ancients EXP +1"
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    s.send(S_TREE, pb.TreeUpdateRsp(tree=[b.complete(farm.tree_msg(snap, now, own=True))]))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


async def _water_friend(s: GameSession, snap: PlayerSnapshot, user_id: int) -> None:
    """Rega a árvore de um amigo: uma vez por dia por amigo, até 200 no dia (help do cliente). Quem rega ganha
    ouro = grau da fazenda do dono x 20 (visto: 920 com a fazenda 46, oficial_20261023-153200-1 #2238; 1.320 com
    66 no turco) e EXP da fazenda = grau de amizade (+4 no grau 4, só turco ciftlik #85; +1 no grau 1, #2242;
    expByOper caso 8, dentro do teto do dia); a árvore do dono ganha 1 de carga (8 -> 9) sem mexer no tempo de
    espera dele; a amizade sobe 1. Pacotes (#2237-#2243): 4158, 109, 112 (missão), 147 (a dele, depois a minha),
    165, 146, 83."""
    assert snap.castle is not None
    found = await _friend(s, user_id)
    c, castle, templates, now = snap.character, snap.castle, s.ctx.templates, s.ctx.clock.now()
    farm.roll_day(castle, now)
    today = gameday.today(now)
    owner = found[0].castle if found is not None else None
    if (
        found is None
        or owner is None
        or found[1].tree_day == today
        or castle.tree_friend_today >= farm.FRIEND_TREE_DAILY
        or owner.tree_fruit > 0  # "Energy is already maxed out." (WaterViewContainer command03)
    ):
        s.log.info("15017 recusado", motivo="não é amigo, já regou hoje, 200 no dia ou cheia", user=user_id)
        return
    target, mine = found
    theirs = await social.row_of(s.ctx, user_id, s.player_id)
    gold = owner.farm_grade * TREE_GOLD
    cs.settle(snap, templates, now)
    c.gold += gold
    before = castle.farm_grade
    gp = farm.add_friend_gp(castle, c.grades, templates, social.friend_grade(s.ctx, mine),
                            _config(s, "Farm_TodayFromFriend_GP", 200))  # fmt: skip
    castle.tree_friend_today += 1
    owner.tree_water += 1
    farm.tree_charge(owner, templates)
    mine.tree_day, mine.friend_gp = today, mine.friend_gp + 1
    rows: list[object] = [c, castle, owner, mine]
    if theirs is not None:  # (dedução) a amizade sobe dos dois lados
        theirs.friend_gp += 1
        rows.append(theirs)
    quests = rules.quest_event(snap, templates, rules.TREE_CONDITION, FRIEND_TREE, 1)
    await s.ctx.characters.save(*rows, *quests)
    s.send(S_WATER_LOG, pb.FarmLogRsp(playerId=s.player_id, operUserId=user_id))
    cs.castle_yield(s)
    up = _farm_up(s, snap, before)  # (visto) oficial_20261023-215937-1 #1277-#1281: 4158, 109, 111, 4386, 83, 147
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    trees = [farm.tree_msg(target, now, own=False), farm.tree_msg(snap, now, own=True)]
    s.send(S_TREE, pb.TreeUpdateRsp(tree=[b.complete(t) for t in trees]))
    s.send(S_FRIEND_UPDATE, social.friend_update(s.ctx, user_id, mine))
    if theirs is not None and (other := s.ctx.online.get(user_id)) is not None:
        other.send(S_FRIEND_UPDATE, social.friend_update(s.ctx, s.player_id, theirs))
    # (visto) #2242-#2243, com os dois espaços de "Friendliness  +1"
    lines = [f"Tree of the Ancients EXP +{gp}", f"Gold +{gold:,}", "Friendliness  +1"]
    s.send(S_HARVEST, pb.TreeUpdateRsp(harvestMsg=lines, isUpGrade=up))  # (visto) #1284 true, #1294 false
    text = f"Gold +{gold:,},Tree of the Ancients EXP +{gp},Friendliness  +1"
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(5178)
async def tree_pick(s: GameSession, msg: pb.BuildingReqMsg) -> None:
    """Colhe a árvore cheia (TreeInfo.canPick: a própria, ``fruitCount`` > 0, fora da espera até a meia-noite).
    Rende Daru e Kyanite (``game_settings`` tree_fruit; internet, wiki Farm) e ``TREE_PICK_GP``; a carga volta a 0
    (wiki Farm). WaterViewContainer: 106 ``pickMsg`` (a animação mostra até 3 linhas), 4189 ``harvestMsg``.
    (dedução) ordem e textos sem captura."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, castle, templates, now = snap.character, snap.castle, s.ctx.templates, s.ctx.clock.now()
    if castle.tree_fruit <= 0 or farm.tree_pick_left(castle, now) > 0:
        s.log.info("5178 recusado", motivo="sem fruto ou em espera", index=msg.index)
        return
    daru, kyanite = farm.tree_reward(s.ctx.world.settings.get("tree_fruit", farm.TREE_FRUIT), castle.farm_grade)
    c.strategy, c.crystals = c.strategy + daru, c.crystals + kyanite
    castle.tree_water = castle.tree_fruit = 0
    castle.tree_picked_at = now
    before = castle.farm_grade
    farm.add_farm_gp(castle, c.grades, templates, TREE_PICK_GP)
    await s.ctx.characters.save(c, castle)
    s.send(S_TREE_PICK, pb.TreeUpdateRsp(pickMsg=[f"Daru + {daru:,}", f"Kyanite + {kyanite:,}"]))
    up = _farm_up(s, snap, before)  # (dedução) antes do 4189, como o 146 da rega
    s.send(S_PICK_HARVEST, pb.TreeUpdateRsp(harvestMsg=[f"Farm EXP + {TREE_PICK_GP}"], isUpGrade=up))
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    cs.castle_yield(s)
    s.send(S_TREE, pb.TreeUpdateRsp(tree=[b.complete(farm.tree_msg(snap, now, own=True))]))


@router.on(8219)
async def friend_trees(s: GameSession, msg: pb.FriendTreeReq) -> None:
    """4146 com a árvore de cada id pedido (o cliente pede a própria ao chegar no nível 11)."""
    snap = s.snapshot
    assert snap is not None
    now, trees = s.ctx.clock.now(), []
    for user_id in list(dict.fromkeys(msg.friendId))[:MAX_IDS]:
        other = snap if user_id == s.player_id else await _other(s, user_id)
        if other is not None:
            trees.append(b.complete(farm.tree_msg(other, now, own=other is snap)))
    s.send(S_FRIEND_TREE, pb.FriendTreeRsp(treeInfo=trees))


@router.on(8231)
async def friend_farm_state(s: GameSession, msg: pb.FriendUserIdsMsg) -> None:
    """4190: o que dá para fazer em cada fazenda. O oficial põe o próprio jogador primeiro (só turco: ciftlik #3)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    now = s.ctx.clock.now()
    states = [farm.own_state(snap, now)]
    room = farm.waters_today(snap.castle, now)[1] < farm.FRIEND_TREE_DAILY
    # ponytail: um snapshot por amigo (até 100); se pesar, ler só terras e castelos
    for user_id in [i for i in dict.fromkeys(msg.friendId) if i not in (0, s.player_id)][:MAX_IDS]:
        found = await _friend(s, user_id)
        if found is None:
            states.append(pb.FriendFarmStateMsg(userId=user_id))
            continue
        target, r = found
        full = target.castle is not None and target.castle.tree_fruit > 0
        can_water = room and r.tree_day != gameday.today(now) and not full
        states.append(farm.friend_state(s.player_id, target, s.ctx.templates, now, can_water=can_water))
    s.send(S_CAN_WATER, b.complete(pb.LoadFarmRsp(friendFarmState=states)))
