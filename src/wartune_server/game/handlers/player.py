"""Pedidos do jogador fora de batalha: missões, mochila/equipamento, atalhos, relógio, ouro."""

from __future__ import annotations

from ...domain.models import BagType, Item
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import cash_entry, item_entry
from ...templates.repository import Row
from .. import rules
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..router import router
from ..session import GameSession
from .login import army, player_info

S_PLAYER, S_FULL_ARMY, S_QUESTS, S_ITEMS, S_QUEST_DONE = 3, 150, 112, 115, 52
S_CHAT, S_ALERT, S_CASTLE_YIELD, S_FAST_KEY, S_TIME = 83, 111, 109, 64, 4234
GOLD_MAX, CRYSTALS = 10000, 1000  # ponytail: armazém e cristais fixos até existirem no banco
BOX = "298"  # ItemTempInfo.SonType do pacote que abre um GradeDrop (Property1 = DropId)
BAG_SIZE = 42  # PlayerInfo.bagDefaultCount; ponytail: sem espaços comprados (bagCount) ainda
CURRENCIES = {-100: "gold", -300: "strategy", -400: "point", -500: "gift_token"}  # TemplateId < 0


def _player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _army(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]))


def castle_yield(s: GameSession) -> None:
    assert s.snapshot is not None
    msg = pb.CastleYieldMsg(goldYield=0, goldTotalCount=s.snapshot.character.gold, goldMax=GOLD_MAX)
    msg.curPopulation, msg.maxPopulation, msg.crystalsCount = 0, 0, CRYSTALS
    s.send(S_CASTLE_YIELD, msg)


@router.on(5015)
async def castle_update(s: GameSession, _: object) -> None:
    castle_yield(s)


@router.on(20008)
async def synchronized_time(s: GameSession, _: object) -> None:
    s.send(S_TIME, pb.SynchronizedTimeMsg(sysCurtime=b.fmt_time(s.ctx.clock.now())))


@router.on(5167)
async def fast_key(s: GameSession, msg: pb.HeroFastKeyMsg) -> None:
    leader = s.snapshot.leader if s.snapshot else None
    if leader is None:
        return
    leader.fast_key = msg.fastKey
    await s.ctx.characters.save(leader)
    s.send(S_FAST_KEY, pb.HeroFastKeyMsg(fastKey=msg.fastKey, setResult=True))


@router.on(5012)
async def quest_add(s: GameSession, msg: pb.QuestAddedMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    added = [q for qid in msg.questId if (q := rules.accept_quest(snap, s.ctx.templates, qid, now)) is not None]
    if added:
        await s.ctx.characters.save(*added)
        s.send(S_QUESTS, quest_update(added, rules.quest_bitmap(snap)))


@router.on(5014)
async def quest_finish(s: GameSession, msg: pb.QuestFinishedReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    q = rules.quest(snap, msg.templateId)
    if q is None or q.completed or not rules.quest_done(snap, s.ctx.templates, q):
        s.log.info("5014 recusado", quest=msg.templateId)
        return
    s.send(S_QUESTS, quest_update([q], rules.quest_bitmap(snap)))
    row, goods = rules.quest_rewards(snap, s.ctx.templates, q.template_id)
    gp, gold = int(row.get("RewardPlayGP", 0)), int(row.get("RewardGold", 0))
    q.completed, q.completed_at = True, s.ctx.clock.now()
    rules.add_gp(snap, s.ctx.templates, gp)
    snap.character.gold += gold
    for item in goods:
        item.pos = rules.free_bag_pos(snap)
        snap.items.append(item)
    await s.ctx.characters.save(snap.character, snap.leader, q, *goods)

    _player(s)
    s.send(S_QUESTS, quest_update([q], rules.quest_bitmap(snap)))
    if gold:
        castle_yield(s)
    if gp:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"{gp:,} EXP kazanıldı"))
    _army(s)
    _player(s)
    for item in goods:
        s.send(S_ITEMS, item_moved(item.bag_type, 0, item.pos, item, s.player_id))
        row = s.ctx.templates.get("ItemTempInfos", item.template_id) or {}
        text = f"Kazanılan:{row.get('TemplateName', item.template_id)} x{item.count}"
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    s.send(S_QUEST_DONE, pb.QuestFinishedRspMsg(templateId=q.template_id))


@router.on(5005)
async def bag_move(s: GameSession, msg: pb.ItemReqMsg) -> None:
    """Move item entre mochila (1) e herói (4); se o destino estiver ocupado, troca."""
    snap = s.snapshot
    assert snap is not None

    def at(bag: int, obj: int, pos: int) -> Item | None:
        return next((i for i in snap.items if (i.bag_type, i.object_id, i.pos) == (bag, obj, pos)), None)

    item = at(msg.beginBagType, msg.beginObjId, msg.beginPos)
    if item is None or (msg.endBagType == BagType.HERO and (snap.leader is None or msg.endObjId != snap.leader.id)):
        s.log.info("5005 recusado", pedido=str(msg))
        return
    other = at(msg.endBagType, msg.endObjId, msg.endPos)
    item.bag_type, item.object_id, item.pos, item.is_new = msg.endBagType, msg.endObjId, msg.endPos, False
    if other is not None:
        other.bag_type, other.object_id, other.pos = msg.beginBagType, msg.beginObjId, msg.beginPos
    await s.ctx.characters.save(*(i for i in (item, other) if i is not None))

    _player(s)
    _army(s)
    s.send(S_ITEMS, item_moved(msg.beginBagType, msg.beginObjId, msg.beginPos, other, s.player_id))
    s.send(S_ITEMS, item_moved(msg.endBagType, msg.endObjId, msg.endPos, item, s.player_id))


@router.on(5006)
async def use_item(s: GameSession, msg: pb.ItemUseMsg) -> None:
    """Abre um pacote (SonType 298): troca o item pelo GradeDrop dele, numa transação só."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates
    box = next((i for i in snap.items if (i.bag_type, i.pos) == (BagType.BAG, msg.pos)), None)
    row = templates.get("ItemTempInfos", box.template_id) if box is not None else None
    drops = list(templates.find("GradeDrop", DropId=row.get("Property1"))) if row is not None else []
    usable = box is not None and row is not None and row.get("SonType") == BOX and msg.bagType == BagType.BAG
    ids = [int(d["TemplateId"]) for d in drops]
    known = all(t in CURRENCIES or (t > 0 and templates.get("ItemTempInfos", t)) for t in ids)
    goods = [d for d in drops if int(d["TemplateId"]) > 0]
    fits = sum(i.bag_type == BagType.BAG for i in snap.items) - 1 + len(goods) <= BAG_SIZE
    if not (usable and drops and known and fits) or c.grades < int(row.get("NeedGrades", 0)):  # type: ignore[union-attr]
        s.log.info("5006 recusado", pedido=str(msg), item=box and box.template_id, drops=len(drops))
        return
    assert box is not None

    snap.items.remove(box)  # antes de qualquer await: o próximo pacote já não acha a caixa
    new: list[Item] = []
    for d in goods:
        tpl = templates.get("ItemTempInfos", int(d["TemplateId"])) or {}
        # ponytail: o oficial sorteia randomSkill_1 nos equipamentos (RandomSkillCount); a tabela
        # do sorteio não está nos templates, então vai o DefaultSkill (vazio = nenhum)
        skill = int(tpl.get("DefaultSkill") or 0)
        item = Item(c.id or 0, int(d["TemplateId"]), count=int(d["Data"]), random_skill=skill)
        item.pos = rules.free_bag_pos(snap)
        snap.items.append(item)
        new.append(item)
    cash = {"point": 0, "gift_token": 0}
    for d in drops:
        if (field := CURRENCIES.get(int(d["TemplateId"]))) is not None:
            setattr(c, field, getattr(c, field) + int(d["Data"]))
            if field in cash:
                cash[field] += int(d["Data"])
    ref = f"5006:{box.template_id}"
    logs: list[object] = [item_entry(c.id or 0, box.template_id, -1, "use", ref)]
    logs += [item_entry(c.id or 0, i.template_id, i.count, "drop", ref) for i in new]
    if any(cash.values()):
        logs.append(cash_entry(c, cash["point"], cash["gift_token"], "item", ref))
    await s.ctx.characters.save(c, *new, *logs, delete=(box,))

    s.send(S_ITEMS, item_moved(BagType.BAG, 0, box.pos, None, s.player_id))
    _army(s)
    if -100 in ids:
        castle_yield(s)
    moved = pb.ItemMovedListMsg()
    for item in new:
        moved.moved.extend(item_moved(BagType.BAG, 0, item.pos, item, s.player_id).moved)
    s.send(S_ITEMS, moved)

    def label(d: Row) -> str:
        name = (templates.get("ItemTempInfos", int(d["TemplateId"])) or {}).get("TemplateName", d["TemplateId"])
        return f"{name} {int(d['Data']):,}" if int(d["TemplateId"]) < 0 else f"{name} x{d['Data']}"

    text = "Kazanılan:" + ", ".join(label(d) for d in reversed(drops))  # o oficial lista do fim para o começo
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _player(s)
