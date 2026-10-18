"""Pedidos do jogador fora de batalha: missões, atalhos, relógio, ouro. Mochila em ``items.py``."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace

from ...domain.models import Consortia, Item
from ...protocol.messages import wartune_pb2 as pb
from .. import bag, daily, rewards, rules
from ..arena import data_reset
from ..builders import login as b
from ..builders.player import quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .login import army, player_info
from .space import talk

S_PLAYER, S_FULL_ARMY, S_QUESTS, S_ITEMS, S_QUEST_DONE = 3, 150, 112, 115, 52
S_CHAT, S_ALERT, S_FAST_KEY, S_TIME, S_RESET = 83, 111, 64, 4234, 4202
CURRENCIES = {-100: "gold", -300: "strategy", -400: "point", -500: "gift_token", -600: "crystals"}  # TemplateId < 0
# (dedução) texto sem fonte: o cliente monta esses avisos com chave de idioma, que não está no decompilado
BAG_FULL = "Çantanız dolu."


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
    """Relógio (a cada ~60 s). Também vira o dia de quem está online (4202 com os valores novos e o 3) e os
    monstros da cidade externa que ele está vendo."""
    from .outer_city import roll_monsters  # outer_city importa events, que importa este módulo

    now = s.ctx.clock.now()
    s.send(S_TIME, pb.SynchronizedTimeMsg(sysCurtime=b.fmt_time(now)))
    roll_monsters(s)
    if s.snapshot is not None and (changed := daily.roll(s.snapshot, s.ctx.templates, now)):
        await s.ctx.characters.save(*changed)
        s.send(S_RESET, data_reset(s.snapshot, now))
        _player(s)


@router.on(5167)
async def fast_key(s: GameSession, msg: pb.HeroFastKeyMsg) -> None:
    leader = s.snapshot.leader if s.snapshot else None
    if leader is None:
        return
    leader.fast_key = msg.fastKey
    await s.ctx.characters.save(leader)
    s.send(S_FAST_KEY, pb.HeroFastKeyMsg(fastKey=msg.fastKey, setResult=True))


def _unique[T](items: Iterable[T]) -> list[T]:
    return list(dict.fromkeys(items))  # Quest e Item são por identidade (eq=False)


@router.on(5012)
async def quest_add(s: GameSession, msg: pb.QuestAddedMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    mine = s.ctx.guilds.of(s.player_id)
    guild = mine[0] if mine is not None else None
    accepted = [
        r
        for qid in msg.questId
        if (r := rules.accept_quest(snap, s.ctx.templates, qid, now, guild is not None)) is not None
    ]
    added = [q for q, _ in accepted]
    for node in sorted({n for q in added for n in rules.talk_nodes(s.ctx.templates, q.template_id)}):
        talk(s, node, added)  # missão de conversa: o cliente aceita no último passo do diálogo
    # a missão e as que a aceitação mudou (tutorial, prédio), mais as de estado que já valiam (amigos, guilda, bolsa)
    moved = [c for _, cs in accepted for c in cs]
    changed = _unique([*moved, *rules.social_state_quests(snap, s.ctx.templates, guild)])
    if changed:
        await s.ctx.characters.save(*changed)
        s.send(S_QUESTS, quest_update(changed, rules.quest_bitmap(snap)))


@router.on(5014)
async def quest_finish(s: GameSession, msg: pb.QuestFinishedReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    mine = s.ctx.guilds.of(s.player_id)
    guild = mine[0] if mine is not None else None
    q = rules.quest(snap, msg.templateId)
    if q is None or q.completed:
        s.log.info("5014 sem missão aberta", quest=msg.templateId)
        return
    # estado que o cliente confere sozinho (amigos, guilda, contribuição, nível da guilda, bolsa): atualiza antes
    rules.update_state_quests(snap, templates, [q])
    refresh = _unique([q, *rules.social_state_quests(snap, templates, guild)])
    if not rules.quest_done(snap, templates, q, now):
        s.log.info("5014 recusado", quest=msg.templateId)
        await s.ctx.characters.save(*refresh)
        s.send(S_QUESTS, quest_update(refresh, rules.quest_bitmap(snap)))  # resposta: progresso atual, sem concluir
        return
    row, goods = rules.quest_rewards(snap, templates, q.template_id)
    take = rules.goods_to_take(snap, templates, q.template_id)
    # a recompensa tem que caber depois de tirar o que a entrega consome: conferido numa cópia, sem mexer no snapshot
    trial = replace(snap, items=[replace(i) for i in snap.items])
    for template_id, count in take:
        bag.take(trial, template_id, count)
    if not bag.fits(trial, templates, goods, now):
        s.log.info("5014 recusado: mochila cheia", quest=msg.templateId)
        alert(s, BAG_FULL)
        await s.ctx.characters.save(*refresh)
        s.send(S_QUESTS, quest_update(refresh, rules.quest_bitmap(snap)))
        return
    # progresso antes da entrega (o oficial manda o 112 do progresso, depois a bolsa, o jogador e a 112 concluída)
    s.send(S_QUESTS, quest_update(refresh, rules.quest_bitmap(snap)))
    changed: list[Item] = []
    gone: list[Item] = []
    for template_id, count in take:
        taken, deleted = bag.take(snap, template_id, count)
        changed += taken
        gone += deleted
    for template_id, count in goods:
        changed += bag.add(snap, templates, template_id, count, now)
    changed = _unique(changed)  # uma pilha pode ser completada mais de uma vez
    rules.update_state_quests(snap, templates, [q])  # a bolsa depois da entrega (condition_N volta ao que sobrou)
    gp, guild_offer = rules.pay_quest_rewards(snap, templates, row)
    q.completed, q.completed_at = True, now
    guilds_changed: list[Consortia] = []
    if guild_offer and guild is not None:  # RewardConsortiaOffer: a riqueza da guilda (sem guilda, não há onde pôr)
        guild.offer += guild_offer
        guild.total_offer += guild_offer
        guilds_changed.append(guild)
    await s.ctx.characters.save(snap.character, snap.leader, *changed, *refresh, *guilds_changed, delete=tuple(gone))

    if changed or gone:
        s.send(S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    _player(s)
    s.send(S_QUESTS, quest_update([q], rules.quest_bitmap(snap)))  # concluída
    if int(row.get("RewardGold", 0)) or int(row.get("RewardCrystal", 0)):  # o 109 leva ouro e cristais
        castle_yield(s)
    if gp:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"{gp:,} EXP kazanıldı"))
    _army(s)
    _player(s)
    for template_id, count in goods:
        text = f"Kazanılan:{bag.name(templates, template_id)} x{count}"
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    s.send(S_QUEST_DONE, pb.QuestFinishedRspMsg(templateId=q.template_id))
