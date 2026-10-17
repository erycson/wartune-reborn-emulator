"""Pedidos do jogador fora de batalha: missões, mochila/equipamento, atalhos, relógio, ouro."""

from __future__ import annotations

from collections.abc import Sequence

from ...domain.models import BagType, Item
from ...protocol.messages import wartune_pb2 as pb
from .. import rewards, rules
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..router import router
from ..session import GameSession
from .login import army, player_info

S_PLAYER, S_FULL_ARMY, S_QUESTS, S_ITEMS, S_QUEST_DONE = 3, 150, 112, 115, 52
S_CHAT, S_ALERT, S_CASTLE_YIELD, S_FAST_KEY, S_TIME = 83, 111, 109, 64, 4234
GOLD_MAX, CRYSTALS = 10000, 1000  # ponytail: armazém e cristais fixos até existirem no banco
BOX = "298"  # ItemTempInfo.SonType do pacote que abre um GradeDrop (Property1 = DropId)


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


def granted(s: GameSession, drops: Sequence[rewards.Drop], new: list[Item], text: str, chat: bool = True) -> None:
    """Depois de um ``rewards.grant`` gravado: 3 (moedas), 150 (EXP), 109 (ouro), 115 (itens) e o 83."""
    _player(s)
    if any(t == rewards.EXP for t, _ in drops):
        _army(s)
    if any(t == -100 for t, _ in drops):
        castle_yield(s)
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    if chat:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


def alert(s: GameSession, text: str) -> None:
    """Aviso no meio da tela (111, canal 7)."""
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))


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
    rows = templates.find("GradeDrop", DropId=row.get("Property1")) if row is not None else ()
    drops = [(int(d["TemplateId"]), int(d["Data"])) for d in rows]
    usable = box is not None and row is not None and row.get("SonType") == BOX and msg.bagType == BagType.BAG
    ok = usable and drops and rewards.can_grant(snap, templates, drops, freed=1)
    if not ok or c.grades < int(row.get("NeedGrades", 0)):  # type: ignore[union-attr]
        s.log.info("5006 recusado", pedido=str(msg), item=box and box.template_id, drops=len(drops))
        return
    assert box is not None

    snap.items.remove(box)  # antes de qualquer await: o próximo pacote já não acha a caixa
    new, _ = rewards.grant(snap, templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), *new, delete=(box,))

    s.send(S_ITEMS, item_moved(BagType.BAG, 0, box.pos, None, s.player_id))
    _army(s)
    if any(t == -100 for t, _ in drops):
        castle_yield(s)
    s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    text = rewards.text(templates, drops[::-1])  # o oficial lista do fim para o começo
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _player(s)
