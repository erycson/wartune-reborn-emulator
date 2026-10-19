"""Pedidos do jogador fora de batalha: missões, atalhos, relógio, ouro. Mochila em ``items.py``."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace

from ...domain.models import Consortia, Item
from ...domain.world import Announcement
from ...protocol.messages import wartune_pb2 as pb
from .. import bag, daily, rewards, rules
from ..arena import data_reset
from ..builders import login as b
from ..builders.army import castle_pawns, unlocked_pawns
from ..builders.player import quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .login import army, player_info
from .space import talk

S_PLAYER, S_FULL_ARMY, S_QUESTS, S_ITEMS, S_QUEST_DONE = 3, 150, 112, 115, 52
S_CHAT, S_ALERT, S_FAST_KEY, S_TIME, S_RESET = 83, 111, 64, 4234, 4202
S_SHORT, S_CASTLE_PAWNS = 139, 100  # U_C_ARMY_SUPPROT (vazio): faltou soldado para completar o exército
CURRENCIES = {-100: "gold", -300: "strategy", -400: "point", -500: "gift_token", -600: "crystals"}  # TemplateId < 0
# (dedução) a captura EN não tem a mochila cheia na entrega: o texto é o do language.txt inglês
# (ConsortiaCaseCellClickMediator.command01)
BAG_FULL = "Inventory Full"


def exp_text(gp: int) -> str:
    """(visto) captura EN #218, #506: "Received 3,000 EXP ", com vírgula de milhar e o espaço no fim."""
    return f"Received {gp:,} EXP "


def _player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _army(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]))


def push_level(s: GameSession, before: int) -> None:
    """Subiu do nível ``before`` (o exército já foi completado em ``rules.add_gp``). Ordem do oficial (tutorial_en
    #636-#639, #1132-#1133, #1587-#1588, #3191-#3192): 139 se ainda falta soldado no exército (o cliente mostra
    "Insufficient Troops!", ``BaseManager.__addPawnHandler``; #636 com o castelo vazio), 100 com o castelo (só
    depois do 8281 e com tropa ou quartel: nos níveis 2-5 da captura ainda não há prédio), 150 e, ao chegar no
    ``openGrades`` do fundo novato, o 4640 (#639)."""
    from .minigames import fund_opened  # minigames importa este módulo

    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    pawns = castle_pawns(snap, templates)
    # os prédios do oficial nascem no 8281 (EN #578, antes o 4154 do login vem vazio); aqui nascem com o personagem,
    # então "castelo aberto" é a produção já iniciada pelo 8281
    if pawns.armyPawn and snap.castle is not None and snap.castle.produced_at is not None:
        target = rules.army_pawn(snap) or next(iter([*snap.pawns, *unlocked_pawns(snap, templates)]), None)
        lead = rules.leader_stats(snap, templates, s.ctx.clock.now()).total["ConatArmy"]
        if target is not None and target.army_count < lead:
            s.send(S_SHORT)
        s.send(S_CASTLE_PAWNS, pawns)
    _army(s)
    fund_opened(s, before)


def granted(s: GameSession, drops: Sequence[rewards.Drop], new: list[Item], text: str, chat: bool = True) -> None:
    """Depois de um ``rewards.grant`` gravado: 3 (moedas), 150 (EXP), 109 (ouro e cristais), 115 (itens) e o 83."""
    _player(s)
    if any(t == rewards.EXP for t, _ in drops):
        # ponytail: só o 150; quem chama não passa o nível antigo, então sem o 139/100/4640 do push_level
        # (o exército já foi completado em rules.add_gp). Passar o nível antigo se um pacote com EXP subir alguém.
        _army(s)
    if any(t in (-100, -600) for t, _ in drops):  # o 109 leva ouro e cristais
        castle_yield(s)
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    if chat:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


def alert(s: GameSession, text: str) -> None:
    """Aviso no meio da tela (111, canal 7)."""
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))


def _announce(s: GameSession, a: Announcement) -> None:
    """Anúncio agendado para todos os online, como o oficial (#3029/#3030: 83 canal 12, ``otherId`` -1,
    ``userType`` 1, ``name`` vazio)."""
    msg = pb.ChatChannelMsg(channel=a.channel, encodeMsg=a.text, otherId=-1, userType=a.user_type,
                            isCenterTip=a.is_center_tip)  # fmt: skip
    for o in s.ctx.online.sessions():
        if o.snapshot is not None:
            o.send(S_CHAT, msg)


@router.on(20008)
async def synchronized_time(s: GameSession, _: object) -> None:
    """Relógio (a cada ~60 s). Também vira o dia de quem está online (4202 com os valores novos e o 3) e os
    monstros da cidade externa que ele está vendo, e solta os anúncios agendados (``game/announcements.py``)."""
    from .outer_city import roll_monsters  # outer_city importa events, que importa este módulo
    from .worldboss import close_windows, push_states  # worldboss importa este módulo

    now = s.ctx.clock.now()
    s.send(S_TIME, pb.SynchronizedTimeMsg(sysCurtime=b.fmt_time(now)))
    roll_monsters(s)
    for a in s.ctx.announcer.tick(s.ctx.world.announcements, now):
        _announce(s, a)
    await close_windows(s)
    push_states(s)
    if s.snapshot is not None and (changed := daily.roll(s.snapshot, s.ctx.templates, now)):
        await s.ctx.characters.save(*changed)
        s.send(S_RESET, data_reset(s.snapshot, now))
        _player(s)
    if s.snapshot is not None:
        from .items import expire_items  # items importa este módulo

        await expire_items(s)


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
    # Ordem da captura EN (#210-#218, #482-#507, #1569-#1576, #2077-#2085, #2242-#2265): 112 do progresso (só tipos
    # 23, 2 e 10), 115 do que a entrega gasta, 3 (já com o bit da missão), 112 concluída, 3 da RewardStrategy, 109,
    # 150 (só quando sobe de nível), 3, 115 dos itens ganhos, 111 de cada item, 52, 83 da EXP e 83 de cada item.
    if rules.finish_progress(snap, templates, q):
        s.send(S_QUESTS, quest_update([q], rules.quest_bitmap(snap)))
    taken: list[Item] = []
    gone: list[Item] = []
    for template_id, count in take:
        changed, deleted = bag.take(snap, template_id, count)
        taken += changed
        gone += deleted
    q.completed, q.completed_at = True, now
    before = b.complete(player_info(s, snap))  # o 3 antes da recompensa
    grades, strategy = snap.character.grades, snap.character.strategy
    gp, guild_offer = rules.pay_quest_rewards(snap, templates, row)
    new = _unique(i for template_id, count in goods for i in bag.add(snap, templates, template_id, count, now))
    guilds_changed: list[Consortia] = []
    if guild_offer and guild is not None:  # RewardConsortiaOffer: a riqueza da guilda (sem guilda, não há onde pôr)
        guild.offer += guild_offer
        guild.total_offer += guild_offer
        guilds_changed.append(guild)
    items = _unique([*taken, *new])  # uma pilha pode ser gasta e completada
    await s.ctx.characters.save(
        snap.character, snap.leader, *snap.pawns, *items, *refresh, *guilds_changed, delete=tuple(gone)
    )

    if taken or gone:
        s.send(S_ITEMS, bag.moved(_unique(taken), s.player_id, empty=gone))
    s.send(S_PLAYER, before)
    s.send(S_QUESTS, quest_update(refresh, rules.quest_bitmap(snap)))  # concluída
    if snap.character.strategy != strategy:  # (visto #1573, #2183) um 3 só com a RewardStrategy, o EXP vem no seguinte
        paid = pb.PlayerMsg()
        paid.CopyFrom(before)
        paid.strategy = snap.character.strategy
        s.send(S_PLAYER, paid)
    if int(row.get("RewardGold", 0)) or int(row.get("RewardCrystal", 0)):  # o 109 leva ouro e cristais
        castle_yield(s)
    if snap.character.grades > grades:
        push_level(s, grades)
    from . import events  # events importa este módulo

    if q.template_id == events.SERVEN_QUEST:  # tutorial_en #3192-#3194: o 4638 entre o 150 e o 3
        events.send_serven(s)
    _player(s)
    if new:
        s.send(S_ITEMS, bag.moved(new, s.player_id))
    texts = [f"Received: {bag.name(templates, template_id)} x{count}" for template_id, count in goods]
    for text in texts:
        alert(s, text)
    s.send(S_QUEST_DONE, pb.QuestFinishedRspMsg(templateId=q.template_id))
    if gp:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=exp_text(gp)))
    for text in texts:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if row.get("TemplateType") == "1":  # (cliente) TaskTraceItem: tipo 1 = "Daily"; leed 20 "Complete a daily quest"
        await events.leed_done(s, events.DAILY_QUEST_LEED)
