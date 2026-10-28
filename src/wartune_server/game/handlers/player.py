"""Pedidos do jogador fora de batalha: missões, atalhos, relógio, ouro. Mochila em ``items.py``."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
from datetime import datetime

from ...domain.models import Consortia, Item
from ...domain.world import Announcement
from ...protocol.messages import wartune_pb2 as pb
from .. import bag, daily, rewards, rules
from .. import castle as cs
from ..arena import data_reset
from ..builders import login as b
from ..builders.army import castle_pawns, unlocked_pawns
from ..builders.player import quest_update
from ..castle import castle_yield, impose_order, order_info
from ..router import router
from ..session import GameSession
from .login import army, player_info
from .space import talk

S_PLAYER, S_FULL_ARMY, S_QUESTS, S_ITEMS, S_QUEST_DONE = 3, 150, 112, 115, 52
S_EFFECT, S_POLITICS, S_BUILDINGS = 110, 152, 4130
S_MAP_SYNC, MAP_CASTLE = 140, 2  # MapUpdatedMsg.updatedType 2 = baseCastle
S_CHAT, S_ALERT, S_FAST_KEY, S_TIME, S_RESET = 83, 111, 64, 4234, 4202
S_SHORT, S_CASTLE_PAWNS, S_ORDER_ADD = (
    139,
    100,
    104,
)  # U_C_ARMY_SUPPROT (vazio): faltou soldado para completar o exército
CURRENCIES = {-100: "gold", -300: "strategy", -400: "point", -500: "gift_token", -600: "crystals"}  # TemplateId < 0
# (dedução) a captura EN não tem a mochila cheia na entrega: o texto é o do language.txt inglês
# (ConsortiaCaseCellClickMediator.command01)
BAG_FULL = "Inventory Full"


exp_text = rules.exp_text


def _player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _army(s: GameSession, cards: bool = True) -> None:
    assert s.snapshot is not None
    s.send(S_FULL_ARMY, b.complete(army(s, s.snapshot)[0]), cards=cards)


HP_PACK = "Used HP pack to restore HP."  # (visto) oficial_20261023-153200-1 #807, #1332, #1450, #1901, #2184


def hero_after_fight(s: GameSession, left: int | None) -> int:
    """Acerta a vida do líder com o que sobrou na luta (``None``: sem herói, não mexe) e cura pela reserva;
    o chamador grava o líder e manda ``hp_pack``. Nível da cura grátis: ``game_settings.hero_free_heal_grade``."""
    snap = s.snapshot
    assert snap is not None
    if left is None or snap.leader is None:
        return 0
    free = int(s.ctx.world.settings.get("hero_free_heal_grade", rules.FREE_HEAL_GRADE))
    return rules.hero_after_fight(snap, s.ctx.templates, s.ctx.clock.now(), left, free)


HP_GONE = "HP Pack has been exhausted."  # (visto) oficial_20261023-171155-1 #7513: derrota, herói ferido, sem reserva


def hp_pack(s: GameSession, used: int) -> None:
    """O 83 da cura pela reserva; sem gastar nada com o herói ferido e a reserva vazia, o "exhausted"."""
    snap = s.snapshot
    if used:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=HP_PACK))
    elif snap is not None and (leader := snap.leader) is not None and leader.blood <= 0:
        live = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now()).live
        if b.hero_hp(leader, live) < live:
            s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=HP_GONE))


async def push_level(s: GameSession, before: int) -> None:
    """Subiu do nível ``before`` (o exército já foi completado em ``rules.add_gp``). Ordem do oficial (tutorial_en
    #636-#639, #1132-#1133, #1587-#1588, #3191-#3192): 139 se ainda falta soldado no exército (o cliente mostra
    "Insufficient Troops!", ``BaseManager.__addPawnHandler``; #636 com o castelo vazio), 100 com o castelo (só
    depois do 8281 e com tropa ou quartel: nos níveis 2-5 da captura ainda não há prédio), 150 e, ao chegar no
    ``openGrades`` do fundo novato, o 4640 (#639)."""
    from .minigames import fund_opened  # minigames importa este módulo

    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    # (visto) oficial_20261023-171155-1 #5840: no 14 a fila de cobrança nasce com o 104, antes do 100/150; quem chama
    # grava o personagem, e a fila se grava na primeira cobrança (no login ``castle.ensure`` a recria igual)
    if (order := impose_order(snap, s.ctx.clock.now())) is not None:
        s.send(S_ORDER_ADD, order_info(order, s.ctx.clock.now()))
    await _level_buildings(s)
    # (visto) só a subida 19 -> 20 (191924 #1728) manda o 140 do castelo no mapa (``grade`` novo); as dez de 10 -> 11
    # a 18 -> 19 não. TODO(inventado): a cada múltiplo de 10 (o visual do castelo no mapa)
    if snap.castle is not None and snap.character.grades // 10 > before // 10:
        own = b.complete(b.castle_msg(snap, snap.castle))
        s.send(S_MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_CASTLE, baseCastle=own))
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


async def _level_buildings(s: GameSession) -> None:
    """Os prédios do nível novo (``castle.level_buildings``). (visto) oficial_20261023-231733-1 #3939-#3944, academia
    no 18: 110/109/152 da tecnologia de ouro que ela libera, 4130 da tecnologia, 104 da fila de tecnologia e 4130 da
    academia, antes do 100/150; tutorial_en #2245-#2246, depósito no 9: o 109 já com o teto novo (10000 -> 450000)
    e o 4130."""
    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None
    born = cs.level_buildings(snap, templates)
    if not born or snap.castle is None:
        return
    unlocked = [u for x in born for u in cs.unlock(snap, templates, x)]
    order = cs.tech_order(snap, templates, now)
    await s.ctx.characters.save(*born, *unlocked, *([order] if order else []))
    used = cs.impose_used(snap.castle, now)
    for u in unlocked:
        row = cs.template(templates, u.template_id)
        if row is not None and (tech := cs.gold_tech(templates, row)) is not None:
            s.send(S_EFFECT, pb.PropertyUpdatedMsg(propertyType=tech[0], value=tech[1] * int(row["BuildingGrade"])))
            castle_yield(s)
            s.send(S_POLITICS, cs.politics_msg(snap, templates))
    if unlocked:
        s.send(S_BUILDINGS, b.buildings_msg(snap, templates, unlocked, used))
    if order is not None:
        s.send(S_ORDER_ADD, order_info(order, now))
    if any(cs.by_son_type(snap, templates, cs.DEPOT) is x for x in born):
        castle_yield(s)
    s.send(S_BUILDINGS, b.buildings_msg(snap, templates, born, used))


def granted(
    s: GameSession,
    drops: Sequence[rewards.Drop],
    new: list[Item],
    text: str,
    chat: bool = True,
    player: bool | None = True,
) -> None:
    """Depois de um ``rewards.grant`` gravado: 3 (moedas), 150 (EXP), 109 (ouro e cristais), 115 (itens) e o 83.
    ``player=False``: o 3 vai depois dos itens, logo antes do 83 (login acumulado); ``None``: sem o 3."""
    if player:
        _player(s)
    if any(t == rewards.EXP for t, _ in drops):
        # ponytail: só o 150; quem chama não passa o nível antigo, então sem o 139/100/4640 do push_level
        # (o exército já foi completado em rules.add_gp). Passar o nível antigo se um pacote com EXP subir alguém.
        _army(s)
    if any(t in (-100, -600) for t, _ in drops):  # o 109 leva ouro e cristais
        castle_yield(s)
    if new:
        from . import events  # events importa este módulo

        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
        events.items_gained(s)
    if player is False:
        _player(s)
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


ARMY_REFRESH = 300  # segundos
ARMY_PHASE = 0.0  # segundos depois do múltiplo de 300 do epoch; o oficial usa ~180,7 (o boot do servidor dele)


def army_tick(now: datetime) -> int:
    return int((now.timestamp() - ARMY_PHASE) // ARMY_REFRESH)


def _army_refresh(s: GameSession, now: datetime) -> None:
    """150 (com o 4902 quando há cartas) e 4434 uma vez por janela de 5 min do servidor, para todos: (visto) nas
    seis capturas inglesas, de 300 em 300 s, todos com ``time % 300`` ≈ 180,7 (oficial_encantar #230, #487, #744;
    171155 #292, #774), quase sempre logo antes do 20008 do cliente e do 4234; também nas turcas (meydan_okuma
    #16-#18, no meio da luta). O oficial tem o próprio relógio; aqui vai no 20008 (a cada ~60 s)."""
    from .vip import send_king  # noqa: PLC0415  (vip importa este módulo)

    tick = army_tick(now)
    if s.army_tick is None:
        s.army_tick = tick
    elif tick != s.army_tick:
        s.army_tick = tick
        _army(s)
        send_king(s)


def balens_changed(s: GameSession) -> None:
    """150 e 4434 logo depois do 3 quando os Balens mudam fora do tique: (visto) o pacote de 5 com 10 Bound Balens
    (tutorial_en #674-#675; o de 10, sem Balens, não manda: #3241-#3245) e a aceleração de fila com 5 vinculados
    (oficial_20261024-191924-1 #1342-#1344, fase 75 s, fora do tique de 180,7)."""
    from .vip import send_king  # noqa: PLC0415  (vip importa este módulo)

    _army(s)
    send_king(s)


@router.on(20008)
async def synchronized_time(s: GameSession, _: object) -> None:
    """Relógio (a cada ~60 s). Também vira o dia de quem está online (4202 com os valores novos e o 3), os
    monstros da cidade externa que ele está vendo e o ciclo das minas (``outer_city.refresh`` com ``push``), e solta
    os anúncios agendados (``game/announcements.py``)."""
    from .outer_city import refresh, roll_monsters  # outer_city importa events, que importa este módulo
    from .warfield import clock as field_clock  # warfield importa este módulo
    from .warfield import push_states as push_fields
    from .worldboss import boss_clock, close_windows, push_states  # worldboss importa este módulo

    now = s.ctx.clock.now()
    if s.snapshot is not None:
        from .events import rate_refresh  # events importa este módulo

        _army_refresh(s, now)
        rate_refresh(s, now)
    s.send(S_TIME, pb.SynchronizedTimeMsg(sysCurtime=b.fmt_time(now)))
    roll_monsters(s)
    if s.snapshot is not None and s.snapshot.castle is not None:
        await refresh(s, push=True)
    for a in s.ctx.announcer.tick(s.ctx.world.announcements, now):
        _announce(s, a)
    from .arena import push_match  # arena importa este módulo
    from .fam import push_state as push_fam  # fam importa este módulo
    from .pet_defend import push_state as push_defend
    from .vehicle import push_state  # vehicle importa este módulo

    await boss_clock(s)
    await close_windows(s)
    await field_clock(s)
    await push_fam(s)
    push_states(s)
    push_fields(s)
    push_state(s)
    push_defend(s)
    push_match(s)
    if s.snapshot is not None and (changed := daily.roll(s.snapshot, s.ctx.templates, now)):
        await s.ctx.characters.save(*changed)
        s.send(S_RESET, data_reset(s.snapshot, now))
        _player(s)
    if s.snapshot is not None:
        from .items import expire_items  # items importa este módulo
        from .systems import expire_mount  # systems importa este módulo

        await expire_items(s)
        await expire_mount(s)


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
    if not rules.quest_done(snap, templates, q, now, guild is not None):
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
    # 150 (só quando sobe de nível), 3, 115 dos itens ganhos, 4476, 111 dos itens, 4152 da diária, 52, 83 da EXP e 83
    # dos itens. oficial_20261023-171155-1 manda o 112 do progresso também nos tipos 21, 29 e 51.
    # O 83 da EXP varia no oficial: antes do 100 nas subidas de nível (#630, #3187) e logo depois do 3 em
    # oficial_20261023-153200-1 #204 e #2130; fica depois do 52, como na maioria do tutorial (#700, #834, #2159).
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
    gp, guild_offer, world, rested = rules.pay_quest_rewards(snap, templates, row, s.ctx.world.settings)
    from .pets import share_gp  # noqa: PLC0415  (pets importa shop, que importa este módulo)

    pet = share_gp(s, gp)  # (só turco: transfer_kampi #21, peri_turnuvasi #65) o 4540 do mascote depois do 3
    new = _unique(i for template_id, count in goods for i in bag.add(snap, templates, template_id, count, now))
    guilds_changed: list[Consortia] = []
    if guild_offer and guild is not None:  # RewardConsortiaOffer: a riqueza da guilda (sem guilda, não há onde pôr)
        guild.offer += guild_offer
        guild.total_offer += guild_offer
        guilds_changed.append(guild)
    items = _unique([*taken, *new])  # uma pilha pode ser gasta e completada
    await s.ctx.characters.save(
        snap.character, snap.leader, *snap.pawns, *items, *refresh, *guilds_changed, *([pet] if pet else []),
        delete=tuple(gone),
    )  # fmt: skip

    if taken or gone:
        s.send(S_ITEMS, bag.moved(_unique(taken), s.player_id, empty=gone))
    s.send(S_PLAYER, before)
    s.send(S_QUESTS, quest_update(refresh, rules.quest_bitmap(snap)))  # concluída
    if int(row.get("RewardGold", 0)) or int(row.get("RewardCrystal", 0)):  # o 109 leva ouro e cristais
        castle_yield(s)
    # (visto oficial_20261026-225632-1 #8531-#8534, 761: 3, 112, 109, 3 com a Daru nova, 52): o 3 da RewardStrategy
    # sai depois do 109. Sem EXP, ele é o 3 final e o de depois não repete (761, 764)
    paid = snap.character.strategy != strategy
    if paid:
        strategy_msg = pb.PlayerMsg()
        strategy_msg.CopyFrom(before)
        strategy_msg.strategy = snap.character.strategy
        s.send(S_PLAYER, strategy_msg)
    if snap.character.grades > grades:
        await push_level(s, grades)
    from . import events  # events importa este módulo

    if q.template_id == events.SERVEN_QUEST:  # tutorial_en #3192-#3194: o 4638 entre o 150 e o 3
        events.send_serven(s)
    if not (paid and not gp):
        _player(s)
    if pet is not None:
        from .pets import send_gained  # noqa: PLC0415

        send_gained(s, pet)
    if new:
        s.send(S_ITEMS, bag.moved(new, s.player_id))
        events.items_gained(s)  # (visto) tutorial_en #490, oficial_20261023-153200-1 #205-#206
    # (visto) oficial_20261023-171155-1 #4994/#4996: um texto só, "Received: Moderate Stamina Potion x1, Skeleton
    # Key x1"
    texts = ["Received: " + ", ".join(f"{bag.name(templates, t)} x{n}" for t, n in goods)] if goods else []
    for text in texts:
        alert(s, text)
    # (visto) #6042, #7808: o 4152 da diária sai antes do 52
    if row.get("TemplateType") == "1":  # (cliente) TaskTraceItem: tipo 1 = "Daily"; leed 20 "Complete a daily quest"
        await events.leed_done(s, events.DAILY_QUEST_LEED)
    s.send(S_QUEST_DONE, pb.QuestFinishedRspMsg(templateId=q.template_id))
    if gp:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=exp_text(gp, world, rested)))
    for text in texts:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
