"""Pedidos do jogador fora de batalha: missões, atalhos, relógio, ouro. Mochila em ``items.py``."""

from __future__ import annotations

from collections.abc import Sequence

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from .. import rewards, rules
from ..builders import login as b
from ..builders.player import item_moved, quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .login import army, player_info
from .space import talk

S_PLAYER, S_FULL_ARMY, S_QUESTS, S_ITEMS, S_QUEST_DONE = 3, 150, 112, 115, 52
S_CHAT, S_ALERT, S_FAST_KEY, S_TIME = 83, 111, 64, 4234
CURRENCIES = {-100: "gold", -300: "strategy", -400: "point", -500: "gift_token", -600: "crystals"}  # TemplateId < 0


def _player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _army(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]))


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
    for node in sorted({n for q in added for n in rules.talk_nodes(s.ctx.templates, q.template_id)}):
        talk(s, node, added)  # missão de conversa: o cliente aceita no último passo do diálogo
    if added:
        await s.ctx.characters.save(*added)
        s.send(S_QUESTS, quest_update(added, rules.quest_bitmap(snap)))


@router.on(5014)
async def quest_finish(s: GameSession, msg: pb.QuestFinishedReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    # missões de estado (amigos, guilda, contribuição, nível): o cliente mostra cumprida quando o estado bate
    mine = s.ctx.guilds.of(s.player_id)
    synced = rules.social_state_quests(snap, s.ctx.templates, mine[0] if mine is not None else None)
    q = rules.quest(snap, msg.templateId)
    if q is None or q.completed or not rules.quest_done(snap, s.ctx.templates, q, s.ctx.clock.now()):
        s.log.info("5014 recusado", quest=msg.templateId)
        if synced:
            await s.ctx.characters.save(*synced)
            s.send(S_QUESTS, quest_update(synced, rules.quest_bitmap(snap)))
        return
    s.send(S_QUESTS, quest_update(synced if q in synced else [*synced, q], rules.quest_bitmap(snap)))
    row, goods = rules.quest_rewards(snap, s.ctx.templates, q.template_id)
    gp, gold = int(row.get("RewardPlayGP", 0)), int(row.get("RewardGold", 0))
    strategy = int(row.get("RewardStrategy", 0))  # (visto) tempinfos: 90 dá Ruh 1000; (dedução) o template manda
    used, gone = rules.take_quest_goods(snap, s.ctx.templates, q)  # condição 27: a bolsa paga a entrega (dedução)
    q.completed, q.completed_at = True, s.ctx.clock.now()
    rules.add_gp(snap, s.ctx.templates, gp)
    snap.character.gold += gold
    snap.character.strategy += strategy
    for item in goods:
        item.pos = rules.free_bag_pos(snap)
        snap.items.append(item)
    await s.ctx.characters.save(snap.character, snap.leader, q, *goods, *synced, *used, delete=tuple(gone))

    _player(s)
    s.send(S_QUESTS, quest_update([q], rules.quest_bitmap(snap)))
    for item in gone:
        s.send(S_ITEMS, item_moved(item.bag_type, 0, item.pos, None, s.player_id))
    for item in used:
        s.send(S_ITEMS, item_moved(item.bag_type, 0, item.pos, item, s.player_id))
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
