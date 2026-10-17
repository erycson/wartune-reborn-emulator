"""Fazenda (15044), árvore (15017, 5178, 8219, 8231) (8565 árvore da guilda: guild_events.py). Ver docs/castelo.md.

Só a fazenda e a árvore do próprio jogador mudam aqui. Ações na fazenda de amigo (roubar, reviver,
tirar praga, regar a árvore dele) dependem da lista de amigos e são recusadas até ela existir.
"""

from __future__ import annotations

from ...domain.errors import NotFoundError
from ...domain.models import BagType, FarmLand, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import pay, record_cash
from .. import castle as cs
from .. import farm, rules
from ..bag import BAG_BASE as BAG_SIZE  # ponytail: só os 42 base; comprados via bag.capacity
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..router import router
from ..session import GameSession
from .login import player_info
from .player import CURRENCIES

S_PLAYER, S_CHAT, S_ITEMS = 3, 83, 115
S_FARM_INFO, S_FARM_LAND, S_TREE, S_FRIEND_TREE, S_CAN_WATER = 4386, 4387, 147, 4146, 4190
REQ, PLANT, WORM, WEED, PICK, ACCELERATE, CLEAR = 0, 1, 2, 3, 4, 7, 8  # FarmOperateType
OK, FAIL = 0, 1
EXP = -700  # ItemTempInfos -700: as sementes de EXP rendem EXP do jogador
QUEST_PLANT, QUEST_HARVEST, QUEST_BUG = 59, 60, 61  # QuestCondictionInfos: plantar, colher, pegar praga
BUG_PARA1 = 1  # Para1 da praga: vale a fazenda própria ou de amigo (QuestTemps 267/862, Detail)
S_QUESTS = 112  # QuestUpdatedRspMsg
MAX_IDS = 100  # listas de amigos que o cliente manda (8219/8231)


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


def _land_reply(s: GameSession, pos: int, land: FarmLand | None, op: int, result: int) -> None:
    msg = farm.land_msg(s.player_id, pos, land)
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
    if msg.friendId not in (0, s.player_id) or not 0 <= msg.pos < farm.OPEN_LANDS:
        s.log.info("15044 recusado", motivo="fazenda de amigo ou terra fechada", op=msg.opType, friend=msg.friendId)
        return
    land = next((x for x in snap.lands if x.pos == msg.pos), None)
    action = {PLANT: _plant, WORM: _pest, WEED: _pest, PICK: _pick, ACCELERATE: _accelerate, CLEAR: _clear}.get(
        msg.opType
    )
    if action is None or not await action(s, snap, msg, land):
        s.log.info("15044 recusado", op=msg.opType, pos=msg.pos)
        _land_reply(s, msg.pos, land, msg.opType, FAIL)  # o cliente mostra a dica de falha


async def _plant(s: GameSession, snap: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None) -> bool:
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
    new = farm.plant(snap, row, msg.pos, now)
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_PLANT, 0, 1)
    if item.count > 0:
        await s.ctx.characters.save(item, new, *quests)
    else:
        await s.ctx.characters.save(new, *quests, delete=(item,))
    s.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item if item.count > 0 else None, s.player_id))
    _land_reply(s, msg.pos, new, PLANT, OK)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    return True


async def _pest(s: GameSession, snap: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None) -> bool:
    assert snap.castle is not None
    now = s.ctx.clock.now()
    worm = msg.opType == WORM
    if land is None or not (farm.has_worm(land, now) if worm else farm.has_grass(land, now)):
        return False
    if worm:
        land.worm = 0
    else:
        land.grass = 0
    gp = _config(s, "FarmCrop_Operate_GP", 1)
    farm.add_farm_gp(snap.castle, snap.character.grades, s.ctx.templates, gp)
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_BUG, BUG_PARA1, 1) if worm else []  # o mato não conta
    await s.ctx.characters.save(land, snap.castle, *quests)
    _land_reply(s, msg.pos, land, msg.opType, OK)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    return True


async def _pick(s: GameSession, snap: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None) -> bool:
    """Colhe: moeda (ouro, alma, cristal, diamante vinculado), EXP (-700) ou item, e libera a terra."""
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    row = farm.seed(templates, land.item_template_id) if land is not None else None
    if land is None or row is None or not farm.is_mature(land, now) or farm.is_dead(land, row, now):
        return False
    reward, count = int(row["Property2"]), land.reward_count
    field = CURRENCIES.get(reward)
    if reward < 0 and field is None and reward != EXP:
        return False
    if field == "gold" and cs.yield_msg(snap, templates, now).goldTotalCount >= cs.gold_max(snap, templates):
        return False  # FarmLandItem.checkGoldLimit: o cliente também bloqueia
    item = Item(c.id or 0, reward, count=count, pos=rules.free_bag_pos(snap)) if reward > 0 else None
    full = sum(i.bag_type == BagType.BAG for i in snap.items) >= BAG_SIZE
    if item is not None and (full or not templates.get("ItemTempInfos", reward)):
        return False
    changed: list[object] = [c]
    if item is not None:
        snap.items.append(item)
        changed.append(item)
    elif reward == EXP:
        rules.add_gp(snap, templates, count)
        changed.append(snap.leader)
    else:
        assert field is not None
        if field == "gold":
            cs.settle(snap, templates, now)
            changed.append(snap.castle)
        setattr(c, field, getattr(c, field) + count)
        if field in ("point", "gift_token"):
            delta = (count, 0) if field == "point" else (0, count)
            changed.append(record_cash(c, *delta, reason="farm_pick", ref=f"seed:{land.item_template_id}", now=now))
    snap.lands.remove(land)
    quests = rules.quest_event(snap, templates, QUEST_HARVEST, 0, 1)  # só a fazenda própria (Para1 0)
    await s.ctx.characters.save(*changed, *quests, delete=(land,))
    _land_reply(s, msg.pos, None, PICK, OK)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    if item is not None:
        s.send(S_ITEMS, item_moved(BagType.BAG, 0, item.pos, item, s.player_id))
    if field in ("gold", "crystals"):
        cs.castle_yield(s)
    else:
        s.send(S_PLAYER, b.complete(player_info(s, snap)))
    return True


async def _accelerate(s: GameSession, snap: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None) -> bool:
    c, now = snap.character, s.ctx.clock.now()
    if land is None or land.accelerated or farm.is_mature(land, now):
        return False
    cost = _config(s, "Farm_Accelerate_Point", 10)
    entry = pay(c, cost, bind=msg.payType == 0, reason="farm_accelerate", ref=f"land:{land.pos}", now=now)
    if entry is None:
        return False
    # ponytail: o texto do oficial (farm.view.FarmOperMenu.accelerateTip) não está decompilado;
    # aqui a aceleração amadurece na hora
    land.mature_at, land.accelerated = now, True
    await s.ctx.characters.save(c, land, entry)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    _land_reply(s, msg.pos, land, ACCELERATE, OK)
    return True


async def _clear(s: GameSession, snap: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None) -> bool:
    if land is None:
        return False
    snap.lands.remove(land)
    await s.ctx.characters.save(delete=(land,))
    _land_reply(s, msg.pos, None, CLEAR, OK)
    return True


@router.on(15017)
async def tree_water(s: GameSession, msg: pb.BuildingReqMsg) -> None:
    """Rega a própria árvore a cada 10 minutos (ciftlik.json: ouro, energia e EXP da fazenda)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, castle, templates, now = snap.character, snap.castle, s.ctx.templates, s.ctx.clock.now()
    if msg.userId not in (0, s.player_id) or farm.tree_left(castle, now) > 0 or castle.tree_fruit > 0:
        s.log.info("15017 recusado", motivo="árvore de amigo, em espera ou com fruto", user=msg.userId)
        return
    # ouro = nível do dono x 20: visto em 2 capturas (220 no nível 11, 1.320 na árvore de amigo de nível 66)
    gold = c.grades * 20
    cs.settle(snap, templates, now)
    c.gold += gold
    castle.energy = min(castle.energy + 1, max(castle.energy, cs.energy_max(templates)))
    castle.tree_water, castle.tree_watered_at = castle.tree_water + 1, now
    farm.add_farm_gp(castle, c.grades, templates, 1)
    # ponytail: sem fruto (quando a árvore frutifica não está nas capturas nem no cliente decompilado)
    await s.ctx.characters.save(c, castle)
    cs.castle_yield(s)
    text = f"Doldurma başarılıAltın + {gold},Enerji + 1,Çiftlik EXP  + 1"  # sic, como no oficial
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    s.send(S_TREE, pb.TreeUpdateRsp(tree=[b.complete(farm.tree_msg(snap, now, own=True))]))


@router.on(5178)
async def tree_pick(s: GameSession, msg: pb.BuildingReqMsg) -> None:
    # sem fruto nunca há o que colher (ver 15017); recusado até a regra de frutificação existir
    s.log.info("5178 recusado", motivo="árvore sem fruto", index=msg.index)


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
    """4190: o que dá para fazer em cada fazenda. O oficial põe o próprio jogador primeiro."""
    snap = s.snapshot
    assert snap is not None
    states = [farm.own_state(snap, s.ctx.clock.now())]
    # ponytail: ações em fazenda de amigo ainda recusadas (lista de amigos), então tudo falso
    ids = [i for i in dict.fromkeys(msg.friendId) if i not in (0, s.player_id)][:MAX_IDS]
    states += [pb.FriendFarmStateMsg(userId=i) for i in ids]
    s.send(S_CAN_WATER, b.complete(pb.LoadFarmRsp(friendFarmState=states)))
