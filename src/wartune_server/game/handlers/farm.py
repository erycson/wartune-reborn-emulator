"""Fazenda (15044), árvore (15017, 5178, 8219, 8231) (8565 árvore da guilda: guild_events.py). Ver docs/castelo.md.

Na própria fazenda: plantar, praga, colher, acelerar e limpar. Na de amigo (relação ``FRIEND``, que é dos dois
lados): praga (2/3), roubar (5), reviver (6) e regar a árvore dele (15017 com ``userId``). O dono pode estar
online (mexe-se no snapshot da sessão dele, como ``social.row_of``) ou offline (snapshot do banco).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ...domain import gameday
from ...domain.errors import NotFoundError
from ...domain.models import BagType, FarmLand, Item, PlayerSnapshot, Relation, RelationType
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import pay, record_cash
from ...templates.repository import GameTemplates
from .. import bag, farm, rewards, rules, social
from .. import castle as cs
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..router import router
from ..session import GameSession
from . import offer, shop
from .login import player_info
from .player import CURRENCIES, balens_changed, push_level

S_PLAYER, S_CHAT, S_ALERT, S_ITEMS, S_QUESTS = 3, 83, 111, 115, 112
S_FARM_INFO, S_FARM_LAND, S_TREE, S_FRIEND_TREE, S_CAN_WATER = 4386, 4387, 147, 4146, 4190
S_HARVEST, S_WATER_LOG, S_FRIEND_UPDATE, S_TREE_PICK, S_PICK_HARVEST = 146, 4158, 165, 106, 4189
S_FARM_LOG = 145  # aviso ao dono online do que o amigo fez (FarmLogRsp)
LOG_WATER, LOG_PEST = 1, 2  # FarmLogRsp.type: (visto) oficial_20261023-215937-1 #1028 e #1033
HELPED = 2  # 4387.result que o dono recebe quando o amigo ajudou (215937 #1034)
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
REVIVE_BACK = timedelta(minutes=1)  # matureTime 1 minuto antes de agora (visto, ver ``_revive``)
# pacote de sementes comprado sozinho no plantio: 9 (visto) oficial_20261024-191924-1 #351 (goodId 2000, Gold Seed).
# TODO(inventado): outras sementes sem captura de compra automática; usam o mesmo pacote.
SEED_PACK = 9


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


def _info(s: GameSession, target: PlayerSnapshot, now: datetime) -> pb.FarmInfoRspMsg:
    from .farm_pets import land_msgs  # noqa: PLC0415  (pets -> player -> ... -> farm)
    from .pets import guard_msg  # noqa: PLC0415

    templates = s.ctx.templates
    msg = farm.farm_info(target, now, templates, own=target is s.snapshot, guard=guard_msg(target, templates))
    msg.petInfo.extend(land_msgs(target, templates))
    return msg


async def _friend(s: GameSession, user_id: int) -> tuple[PlayerSnapshot, Relation] | None:
    """Amigo (``FRIEND`` já é a amizade dos dois lados, docs/social.md) com castelo."""
    r = social.relation_to(s, user_id)
    if r is None or r.relation != RelationType.FRIEND:
        return None
    target = await _other(s, user_id)
    return (target, r) if target is not None else None


def _land_reply(
    s: GameSession, owner_id: int, pos: int, land: FarmLand | None, op: int, result: int, harvested: int = 0
) -> None:
    """4387 com o ``userId`` do dono da terra: o cliente só aplica na fazenda de mesmo ``userId``. ``harvested``:
    a colheita, que a terra já vazia não carrega (visto) oficial_20261024-191924-1 #221 rewardCount 3000."""
    msg = farm.land_msg(owner_id, pos, land)
    msg.opType, msg.result = op, result
    if land is None:
        msg.rewardCount = harvested
    s.send(S_FARM_LAND, pb.FarmInfoRspMsg(farmLandInfo=[msg]))


@router.on(15044)
async def farm_operate(s: GameSession, msg: pb.FarmOperReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    now = s.ctx.clock.now()
    if msg.opType == REQ:
        target = snap if msg.friendId in (0, s.player_id) else await _other(s, msg.friendId)
        if target is not None:
            s.send(S_FARM_INFO, b.complete(_info(s, target, now)))
        return
    own = msg.friendId in (0, s.player_id)
    if msg.opType > LAND_UP:  # terras de mascote e guarda (farm_pets); 10 e 11 não saem do cliente pelo 15044
        from . import farm_pets  # noqa: PLC0415  (pets -> player -> ... -> farm)

        pal = None if own or msg.opType != farm_pets.FEED else await _friend(s, msg.friendId)
        owner = snap if own else (pal[0] if pal else None)
        if farm_pets.START <= msg.opType <= farm_pets.DEFENSE and owner is not None:
            await farm_pets.operate(s, owner, msg, own)
        else:
            s.log.info("15044 recusado", op=msg.opType, friend=msg.friendId)
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


async def _buy_seed(s: GameSession, snap: PlayerSnapshot, template_id: int, now: datetime) -> Item | None:
    """Compra o pacote da semente na loja (ShopTempInfos com esse ``ItemId``, tipo 6: o preço e as regras são os da
    loja) e devolve o item da mochila. Sem loja ou sem dinheiro, ``None``. Ordem do oficial (visto)
    oficial_20261024-191924-1 #349-#352: 111, 83, 90 (BuyInfo result 1), 115; sem 109 do ouro nem 4476."""
    templates = s.ctx.templates
    row = next((r for r in templates.find("ShopTempInfos", ItemId=template_id) if r.get("ShopType") == "6"), None)
    if row is None or shop.check(s, row, SEED_PACK) != shop.OK:
        return None
    column, unit = shop.price(row)  # type: ignore[misc]
    paid = shop.charge(snap, column, unit * SEED_PACK, 0, f"seed:{template_id} x{SEED_PACK}", now)
    if paid is None:
        return None
    tid, good = int(row["ItemId"]), int(row["Id"])
    got = bag.add(snap, templates, tid, SEED_PACK, now, shop.valid_minutes(row), shop.binds(column))
    rec = shop.count_buy(snap, good, SEED_PACK, now)
    bought = shop.purchase(snap, "farm_seed", good, tid, SEED_PACK, column, unit * SEED_PACK, now)
    extra = [paid.ledger] if paid.ledger else []
    await s.ctx.characters.save(snap.character, *paid.changed, *got, rec, *extra, bought, delete=tuple(paid.gone))
    shop.alert(s, shop.bought_text(bag.name(templates, tid), SEED_PACK))
    shop.send(
        s, shop.S_SHOP_BUY, pb.BuyInfo(goodId=good, count=SEED_PACK, receiveId=s.player_id, result=shop.OK, type=1)
    )
    shop.send(s, shop.S_ITEMS, bag.moved(got, s.player_id))
    return next((i for i in got if i.template_id == tid), None)


async def _plant(
    s: GameSession, snap: PlayerSnapshot, _: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    c, now = snap.character, s.ctx.clock.now()
    row = farm.seed(s.ctx.templates, msg.templateId)
    if land is not None or row is None or int(row.get("NeedGrades") or 0) > c.grades:
        return False
    special = row.get("Property5") or "0"
    if special != "0" and any(
        (farm.seed(s.ctx.templates, x.item_template_id) or {}).get("Property5") == special for x in snap.lands
    ):
        return False  # FarmManager: só uma semente especial de cada tipo plantada por vez
    item = next((i for i in snap.items if (i.bag_type, i.pos) == (BagType.BAG, msg.bagPos)), None)
    if item is None:  # sem semente no slot: compra sozinha (o oficial faz isso no mesmo 15044)
        item = await _buy_seed(s, snap, msg.templateId, now)
    if item is None or item.template_id != msg.templateId:
        return False
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


def _helper_gp(s: GameSession, snap: PlayerSnapshot, target: PlayerSnapshot, gp: int) -> int:
    """EXP da fazenda de quem ajudou: na própria, direto; na de amigo, até o teto do dia (expByOper). Devolve o
    grau de antes para o ``_farm_up`` depois do 4387 (oficial_20261024-121659-1 #217-#221)."""
    assert snap.castle is not None
    grade, templates, before = snap.character.grades, s.ctx.templates, snap.castle.farm_grade
    if target is snap:
        farm.add_farm_gp(snap.castle, grade, templates, gp)
    else:
        farm.roll_day(snap.castle, s.ctx.clock.now())
        farm.add_friend_gp(snap.castle, grade, templates, gp, _config(s, "Farm_TodayFromFriend_GP", 200))
    return before


def _farm_up(s: GameSession, snap: PlayerSnapshot, before: int) -> bool:
    """A fazenda subiu de ``before``: 111, 4386 (a própria) e 83 "Your farm has been upgraded to level N!".
    (visto) oficial_20261023-215937-1 #1279-#1281, regando a árvore de um amigo (fazenda 2 -> 3)."""
    assert snap.castle is not None
    if snap.castle.farm_grade <= before:
        return False
    text = f"Your farm has been upgraded to level {snap.castle.farm_grade}!"
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_FARM_INFO, b.complete(_info(s, snap, s.ctx.clock.now())))
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
    land.reward_count += farm.pest_cut(farm.seed(s.ctx.templates, land.item_template_id))
    before = _helper_gp(s, snap, target, _config(s, "FarmCrop_Operate_GP", 1))
    quests = rules.quest_event(snap, s.ctx.templates, QUEST_BUG, BUG_PARA1, 1) if worm else []  # o mato não conta
    await s.ctx.characters.save(land, snap.castle, *quests)
    _land_reply(s, target.character.id or 0, msg.pos, land, msg.opType, OK)
    _farm_up(s, snap, before)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    if target is not snap and (owner := s.ctx.online.get(target.character.id or 0)) is not None:
        _tell_pest(s, owner, target, land, msg.opType)
    return True


def _farm_log(s: GameSession, desc: str, kind: int) -> pb.FarmLogRsp:
    c = s.snapshot.character if s.snapshot is not None else None
    assert c is not None
    when = b.fmt_time(s.ctx.clock.now())
    return pb.FarmLogRsp(operUserId=c.id, operNickName=c.nickname or "", desc=desc, operDate=when, type=kind)


def _tell_pest(s: GameSession, owner: GameSession, target: PlayerSnapshot, land: FarmLand, op: int) -> None:
    """O dono online vê: 145 type 2, 4387 da terra com ``result`` 2 e 83 com o link de quem ajudou. (visto)
    oficial_20261023-215937-1 #1033-#1035, praga (opType 2). TODO(inventado): os textos do mato (opType 3) sem
    captura; vão os da praga."""
    owner.send(S_FARM_LOG, _farm_log(s, "just exterminated pests from your crops!", LOG_PEST))
    shown = farm.land_msg(target.character.id or 0, land.pos, land)
    shown.opType, shown.result = op, HELPED
    owner.send(S_FARM_LAND, pb.FarmInfoRspMsg(farmLandInfo=[shown]))
    assert s.snapshot is not None
    link = social.player_link(s.ctx, s.snapshot.character)
    owner.send(
        S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"{link} just helped exterminate the bugs in your crops!")
    )


def _payout(
    s: GameSession, snap: PlayerSnapshot, reward: int, count: int, ref: str, reason: str = "farm_pick"
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
            changed.append(record_cash(c, *delta, reason=reason, ref=ref, now=now))
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
    """Colhe: moeda (ouro, alma, cristal, diamante vinculado), EXP (-700) ou item, e libera a terra. (visto)
    oficial_20261023-171155-1 #183-#189: 109, 111 e 83 "Received: 2,400 Gold", 4387, 4152 e o 83 da devoção."""
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

    await _payout_sent(s, snap, reward, item, gained)
    text = _reward_text(templates, reward, land.reward_count)  # (dedução) a EXP como no roubo
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    # (visto) o 83 do ouro vem logo depois do 111 (171155 #185-#186); o do Daru, depois do 4387 e do 4152 e antes do
    # 83 da devoção (oficial_20261024-121659-1 #155-#160, #162-#165)
    late = CURRENCIES.get(reward) != "gold"
    if not late:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _land_reply(s, s.player_id, msg.pos, None, PICK, OK, harvested=land.reward_count)
    if quests:  # (dedução) sem captura; junto da terra
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    devotion = events.devotion(s)
    await events.leed_done(s, events.FARM_LEED, say=False)  # leed 25 "Harvest from your own farm"
    if late:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if events.devotion(s) > devotion:
        events.say_devotion(s)
    return True


async def _steal(
    s: GameSession, snap: PlayerSnapshot, target: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    """Rouba da terra madura do amigo (FarmLandInfo.canBeStolen): uma vez por terra, até 3 ladrões, produção
    de 10 ou mais; até ``Farm_TodayStolen_Count`` roubos no dia. Leva ``farm_steal_percent`` % do que resta
    (visto 10%: oficial_20261024-191924-1 #248, 4000 -> 3600; #253, 28000 -> 25200), que sai do ``rewardCount`` do
    dono. Sem EXP da fazenda (``expByOper`` não tem o caso 5; 191924: o todayFromFriendGp não sobe nos roubos)."""
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
    # (visto) oficial_20261024-191924-1 #244-#263: 109, 111 e 83 "Received: 400 Kyanite", 4387; da EXP, 111, 3, 83
    # "Received 2,800 EXP " e o 4387
    text = _reward_text(templates, reward, amount)
    if reward == EXP:
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    await _payout_sent(s, snap, reward, item, gained)
    if reward != EXP:
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _land_reply(s, target.character.id or 0, msg.pos, land, STEAL, OK)
    if quests:  # (dedução) sem captura; junto da terra, como na colheita
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    return True


def _reward_text(templates: GameTemplates, reward: int, count: int) -> str:
    """EXP sai como "Received 2,800 EXP " (oficial_20261024-191924-1 #250); o resto, ``rewards.received``."""
    return rules.exp_text(count) if reward == EXP else rewards.received(templates, [(reward, count)])


async def _revive(
    s: GameSession, snap: PlayerSnapshot, target: PlayerSnapshot, msg: pb.FarmOperReqMsg, land: FarmLand | None
) -> bool:
    """Revive a planta morta do amigo (só amigo revive: "Dead crops must be revived by friends"). (visto)
    oficial_20261024-191924-1 #236-#237 e oficial_20261027-152321-1 #19855-#19864: só o 4387 (opType 6, result 0),
    sem 111 nem 83; só o ``matureTime`` muda, para 1 minuto antes de agora; produção, roubos e pragas ficam.
    EXP ``FarmCrop_Operate_GP`` (expByOper, caso 6)."""
    assert snap.castle is not None
    now = s.ctx.clock.now()
    if land is None or not farm.is_dead(land, farm.seed(s.ctx.templates, land.item_template_id), now):
        return False
    land.mature_at = now - REVIVE_BACK
    before = _helper_gp(s, snap, target, _config(s, "FarmCrop_Operate_GP", 1))
    await s.ctx.characters.save(land, snap.castle)
    _land_reply(s, target.character.id or 0, msg.pos, land, REVIVE, OK)
    _farm_up(s, snap, before)  # (dedução) como na praga
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
    from . import events  # handlers.events importa login

    # (visto) oficial_20261024-121659-1 #204-#210: 3, 4152 (leed 15), 150 e 4434 do gasto (fase 176 s; o tique veio à
    # parte no #212), 4387 com a metade do que faltava (3533 s -> 08:47:22) e o 83 da devoção
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    devotion = events.devotion(s)
    await events.leed_done(s, events.BALEN_LEED, say=False)
    s.balen_leed_sent = True
    balens_changed(s)
    _land_reply(s, s.player_id, msg.pos, land, ACCELERATE, OK)
    if events.devotion(s) > devotion:
        events.say_devotion(s)
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
    s.send(S_FARM_INFO, b.complete(_info(s, snap, now)))
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
    if quests:  # (visto) oficial_20261023-171155-1 #7769-#7774: o 112 antes do 111/4386/83 da subida
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    await offer.progress(s, offer.TREE_FRIEND)  # (visto) 121659 #229-#231: o 4198 entre o 112 e o 147
    up = _farm_up(s, snap, before)  # (visto) oficial_20261023-215937-1 #1277-#1281: 4158, 109, 111, 4386, 83, 147
    trees = [farm.tree_msg(target, now, own=False), farm.tree_msg(snap, now, own=True)]
    s.send(S_TREE, pb.TreeUpdateRsp(tree=[b.complete(t) for t in trees]))
    s.send(S_FRIEND_UPDATE, social.friend_update(s.ctx, user_id, mine))
    if (other := s.ctx.online.get(user_id)) is not None:
        # (visto) oficial_20261023-215937-1 #1028-#1032 e 171155 #8005-#8009: o dono vê 145, 147 (a dele primeiro),
        # 165 e os dois 83 com o link de quem regou
        other.send(S_FARM_LOG, _farm_log(s, "You received energy + 1, friendliness +1", LOG_WATER))
        owner_trees = [farm.tree_msg(target, now, own=True), farm.tree_msg(snap, now, own=False)]
        other.send(S_TREE, pb.TreeUpdateRsp(tree=[b.complete(t) for t in owner_trees]))
        if theirs is not None:
            other.send(S_FRIEND_UPDATE, social.friend_update(s.ctx, s.player_id, theirs))
        link = social.player_link(s.ctx, c)
        other.send(
            S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Friendliness for you and {link} has increased by 1.")
        )
        energized = f"{link} has energized your Tree of Ancients. Ancient Energy +1"
        other.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=energized))
    # (visto) #2242-#2243, com os dois espaços de "Friendliness  +1"
    lines = [f"Tree of the Ancients EXP +{gp}", f"Gold +{gold:,}", "Friendliness  +1"]
    s.send(S_HARVEST, pb.TreeUpdateRsp(harvestMsg=lines, isUpGrade=up))  # (visto) #1284 true, #1294 false
    text = f"Gold +{gold:,},Tree of the Ancients EXP +{gp},Friendliness  +1"
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(5178)
async def tree_pick(s: GameSession, msg: pb.BuildingReqMsg) -> None:
    """Colhe a árvore cheia (TreeInfo.canPick: a própria, ``fruitCount`` > 0, fora da espera até a meia-noite).
    Rende Daru, Kyanite e ouro (``farm.tree_reward``) e ``TREE_PICK_GP`` de EXP da fazenda; a carga volta a 0.
    (visto) oficial_20261025-232017-1 #218-#227 (grau 6): 109 (Kyanite já somado), 3, 111 "Received: 2,400 Kyanite,
    6,100 Daru", 109 (ouro), 4189 ["Gold +160", "Tree of the Ancients EXP +1"], 147 duas vezes, 106 com pickMsg vazio
    e o 83. oficial_20261027-152321-1 #5075-#5086 (grau 10): igual, com ouro +300 e o 4152 da leed 25 antes do 147."""
    from . import events  # handlers.events importa login

    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, castle, templates, now = snap.character, snap.castle, s.ctx.templates, s.ctx.clock.now()
    if castle.tree_fruit <= 0 or farm.tree_pick_left(castle, now) > 0:
        s.log.info("5178 recusado", motivo="sem fruto ou em espera", index=msg.index)
        return
    daru, kyanite, gold = farm.tree_reward(s.ctx.world.settings.get("tree_fruit", farm.TREE_FRUIT), castle.farm_grade)
    c.strategy, c.crystals = c.strategy + daru, c.crystals + kyanite
    castle.tree_water = castle.tree_fruit = 0
    castle.tree_picked_at = now
    before, devotion = castle.farm_grade, events.devotion(s)
    farm.add_farm_gp(castle, c.grades, templates, TREE_PICK_GP)
    await s.ctx.characters.save(c, castle)
    cs.castle_yield(s)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Received: {kyanite:,} Kyanite, {daru:,} Daru"))
    cs.settle(snap, templates, now)
    c.gold += gold
    await s.ctx.characters.save(c, castle)
    cs.castle_yield(s)
    up = _farm_up(s, snap, before)
    s.send(
        S_PICK_HARVEST,
        pb.TreeUpdateRsp(harvestMsg=[f"Gold +{gold:,}", f"Tree of the Ancients EXP +{TREE_PICK_GP}"], isUpGrade=up),
    )
    await events.leed_done(s, events.FARM_LEED, say=False)  # leed 25 "Harvest from your own farm"
    tree = pb.TreeUpdateRsp(tree=[b.complete(farm.tree_msg(snap, now, own=True))])
    s.send(S_TREE, tree)
    s.send(S_TREE, tree)  # (visto) o oficial manda o 147 duas vezes
    s.send(S_TREE_PICK, pb.TreeUpdateRsp(pickMsg=[""]))  # (visto) pickMsg vazio nas duas colheitas
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Received: {kyanite:,} Kyanite, {daru:,} Daru"))
    if events.devotion(s) > devotion:
        events.say_devotion(s)


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
    states = [farm.own_state(snap, s.ctx.templates, now)]
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
