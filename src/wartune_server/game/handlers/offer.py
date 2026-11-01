"""Painel de recompensas (OfferReward 8288-8291/8298) e tarefas em anel (RingTask 8729-8732).
Regras e fontes em docs/eventos.md.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from datetime import datetime

from ...domain.models import EventState, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import Row
from .. import bag, rewards, rules, taxas
from .. import events as ev
from ..builders import login as b
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import S_ITEMS, _player, alert, granted

S_REWARD, S_FRESH, S_COUNT = 4198, 4197, 4360
# 4196 (0x1064): sem ouvinte no cliente; leva o TemplateId entregue (visto) 121659 #505 "0818", 151436 #659 "088d01"
S_CHAT, S_CLICK_ADD, S_OFFER_DONE = 83, 4413, 4196
TREE_FRIEND = 5  # RewardCondictionInfos.CondictionType "Energize the Tree of Ancients (Friends)"
# os outros tipos (títulos do RewardCondictionInfos; ganchos em docs/eventos.md)
RECRUIT, ENCHANT, SOCKET, COLLECT, ASTRAL, KILL_SAME, WILD_MINE, GUILD_OFFER = 1, 2, 3, 4, 6, 7, 8, 9
SYNTH, BALEN_BUY, QTE, CAPTURE, MOUSE, MESSAGE, SYLPH_MAP, SACRIFICE_PET, CIRCUIT = 10, 11, 12, 14, 15, 16, 17, 20, 21
ELIMINATE, FETCH = 18, 19
# (cliente) RingTask.getProgress: 1 conta as tropas do SonType Para1, 4 os itens Para1, 19 ter o item; 12 (QTE), 15
# (Whack-a-Mouse) e 16 (conversa) são resultados que só o cliente vê (nenhum pacote leva): o servidor confia no 8729
CLIENT_ONLY = (QTE, MOUSE, MESSAGE)
S_RING, S_RING_SUM = 4614, 4616
SLOTS, OPEN_GRADE, BASE_COUNT = 4, 14, 20  # OfferRewardModel: MAX_OFFER_TASK_NUM, OPEN_REWARD_GRADE, BASE_REWARD_COUNT
AUTO_REFRESH, FREE_REFRESH, REFRESH_COST = 1800, 2, 10  # AUTO_REFRESH_INTERVAL, botão grátis some em 2, NEEDPAY
CAN_ACCEPT, ACCEPTED, COMPLETED = 1, 2, 3  # REWARD_STATE_*
PASS_CONTRACT = 2  # KingContracts 2 "Bounty Helper": termina a tarefa na hora
OFFER, RING = 0, 1  # RewardTemps.Type
ARREST_TYPE, ARREST_SCENE = 12, 9  # 8298: battleType da 157 e battleScene do 4103 (visto) 20261030-145704 #247, #285
RING_GRADE, RING_MAX, RING_COST, RING_ITEM = 35, 200, 35, 2131021  # RingTaskManager/TaskFrameII


def _json(st: EventState) -> dict:  # type: ignore[type-arg]
    return json.loads(st.text) if st.text else {}


def _reward_info(
    tid: int,
    quality: int,
    *,
    complete: bool = False,
    accept: bool = True,
    repeat: int = 0,
    progress: Sequence[int] = (),
    done_at: datetime | None = None,
) -> pb.RewardInfo:
    n = [*progress, 0, 0, 0, 0]
    return pb.RewardInfo(
        templateId=tid,
        isComplete=complete,
        condition_1=n[0],
        condition_2=n[1],
        condition_3=n[2],
        condition_4=n[3],
        completedDate=b.fmt_time(done_at or datetime(2000, 1, 1)),
        repeatFinish=repeat,
        isAccept=accept,
        isSelect=True,
        quality=quality,
    )


def _task_info(task: EventState, *, done_at: datetime | None = None) -> pb.RewardInfo:
    """A tarefa do painel como o oficial manda: (visto) oficial_20261023-231733-1 #1465 e 121659 #230/#241/#502,
    ``repeatFinish`` 1, ``isAccept`` falso em andamento e verdadeiro só na entrega, ``condition_N`` = andamento."""
    info = _json(task)
    done = done_at is not None
    return _reward_info(task.value, int(info.get("q", 1)), complete=done, accept=done, repeat=1,
                        progress=info.get("n", []), done_at=done_at)  # fmt: skip


def _conditions(s: GameSession, tid: int) -> list[Row]:
    """As condições da tarefa (RewardCondictionInfos, na ordem de condition_1..4); ``Para2`` = quantas vezes."""
    return [r for r in s.ctx.templates.rows("RewardCondictionInfos") if int(r["TemplateId"]) == tid][:4]


def _bump(s: GameSession, st: EventState, tid: int, condition: int, value: int, para1: int | None) -> bool:
    """+``value`` (até o ``Para2``) nas condições ``condition`` da tarefa ``tid`` guardada em ``st.text["n"]``;
    ``para1`` filtra as condições com ``Para1`` (mapa, item...) diferente de 0."""
    conds = _conditions(s, tid)
    info = _json(st)
    n = [*info.get("n", []), *[0] * len(conds)][: len(conds)]
    hits = [
        i
        for i, r in enumerate(conds)
        if int(r["CondictionType"]) == condition
        and n[i] < int(r["Para2"])
        and (para1 is None or int(r["Para1"] or 0) in (0, para1))
    ]
    for i in hits:
        n[i] = min(int(conds[i]["Para2"]), n[i] + value)
    if hits:
        info["n"] = n
        st.text, st.updated_at = json.dumps(info), s.ctx.clock.now()
    return bool(hits)


async def progress(s: GameSession, condition: int, value: int = 1, para1: int | None = None) -> None:
    """A ação do tipo ``condition`` aconteceu: soma nas condições desse tipo da tarefa do painel aceita e do anel em
    andamento. (visto) oficial_20261024-121659-1 #229-#230 e #240-#241: tipo 5 "Energize the Tree of Ancients
    (Friends)" a cada rega de árvore de amigo, logo depois do 112, com o 4198 do andamento. O anel manda o 4614
    (dedução: o mesmo ``RewardInfo`` com ``condition_N``). Os ganchos de cada tipo estão em docs/eventos.md."""
    changed = _progress_now(s, condition, value, para1)
    if changed:
        await s.ctx.characters.save(*changed)


def _progress_now(s: GameSession, condition: int, value: int = 1, para1: int | None = None) -> list[EventState]:
    """O ``progress`` sem gravar: soma, manda o 4198/4614 e devolve o que mudou (quem chama grava)."""
    snap = s.snapshot
    if snap is None:
        return []
    now = s.ctx.clock.now()
    task, ring = _task(snap, now), _ring(snap, now)
    tid = int(_json(ring).get("t", 0))
    task_hit = bool(task.value) and _bump(s, task, task.value, condition, value, para1)
    ring_hit = bool(tid) and _bump(s, ring, tid, condition, value, para1)
    if task_hit:
        s.send(S_REWARD, pb.RewardUpdatedRspMsg(reward=[_task_info(task)]))
    if ring_hit:
        _send_ring(s, snap, now)
    return [*([task] if task_hit else []), *([ring] if ring_hit else [])]


def _met(s: GameSession, task: EventState, tid: int | None = None) -> bool:
    """Todas as condições cumpridas, pela regra do cliente (``BaseOfferReward``/``RingTask.getProgress``)."""
    snap = s.snapshot
    assert snap is not None
    conds = _conditions(s, task.value if tid is None else tid)
    n = [*_json(task).get("n", []), *[0] * len(conds)]

    def done(i: int, r: Row) -> bool:
        kind, para1, para2 = int(r["CondictionType"]), int(r["Para1"] or 0), int(r["Para2"])
        if kind == RECRUIT:  # ArmyManager.getTotalPawnsNumberBySonType(Para1) >= Para2: castelo e exército
            return sum(p.castle_count + p.army_count for p in snap.pawns if _son(s, p.template_id) == para1) >= para2
        if kind == COLLECT:  # GoodsManager.goodsCountByTempId[Para1] >= Para2
            return bag.count_of(snap, para1) >= para2
        if kind == FETCH:  # checkGoodsCount2: um item de Para1 na mochila
            return bag.count_of(snap, para1) >= 1
        return kind in CLIENT_ONLY or n[i] >= para2

    return bool(conds) and all(done(i, r) for i, r in enumerate(conds))


def ring_collects(s: GameSession, template_id: int) -> bool:
    """O anel em andamento pede para coletar ``template_id`` (condição 4, ``Para1``) e ainda falta: o que o cliente
    confere antes de mandar o 8692 do nó de coleta (``SpaceArmyViewHelper.nodeTrigger``, ``param3`` "12")."""
    snap = s.snapshot
    assert snap is not None
    tid = int(_json(_ring(snap, s.ctx.clock.now())).get("t", 0))
    return any(
        int(r["CondictionType"]) == COLLECT and int(r["Para1"] or 0) == template_id
        and bag.count_of(snap, template_id) < int(r["Para2"])
        for r in (_conditions(s, tid) if tid else [])
    )  # fmt: skip


def _son(s: GameSession, template_id: int) -> int:
    row = s.ctx.templates.get("PawnTempInfos", template_id) or {}
    return int(row.get("SonType") or 0)


# ---------------------------------------------------------------- painel de recompensas


def _board(snap: PlayerSnapshot, now: datetime) -> EventState:
    return ev.state(snap, "offer:list", now)


def _roll(s: GameSession, snap: PlayerSnapshot, now: datetime) -> EventState:
    """Sorteia as 4 tarefas do painel (RewardTemps tipo 0 do nível, peso ``Rands``)."""
    grade = snap.character.grades
    pool = [
        r
        for r in s.ctx.templates.find("RewardTemps", Type=OFFER)
        if int(r["NeedMinLevel"]) <= grade < int(r["NeedMaxLevel"]) and int(r["Rands"]) > 0
    ]
    # com reposição: (visto) oficial_20261024-121659-1 #501 com a 24 duas vezes no mesmo painel
    picks = random.choices(pool, weights=[int(r["Rands"]) for r in pool], k=SLOTS) if pool else []
    ids = [int(r["TemplateId"]) for r in picks]
    quality = random.choices(range(1, 6), weights=taxas.get(s.ctx.world.settings, "offer_quality_weights"), k=len(ids))
    st = _board(snap, now)
    st.text, st.updated_at = json.dumps({"ids": ids, "q": quality, "st": [CAN_ACCEPT] * len(ids)}), now
    return st


def _fresh_msg(s: GameSession, snap: PlayerSnapshot, now: datetime) -> pb.RewardFreshRspMsg:
    st = _board(snap, now)
    data = _json(st)
    msg = pb.RewardFreshRspMsg(
        rewardTimes=ev.daily(snap, "offer:count", now).value, freeTimes=ev.daily(snap, "offer:free", now).value
    )
    if data:
        msg.rewardLastdate = b.fmt_time(st.updated_at)
        msg.templateId.extend(data["ids"])
        msg.isIsValid.extend(data["st"])
        msg.qualitys.extend(data["q"])
    return msg


def _task(snap: PlayerSnapshot, now: datetime) -> EventState:
    """Tarefa aceita: ``value`` = TemplateId (0 = nenhuma), ``text`` = {"q": qualidade, "pos": slot}."""
    return ev.state(snap, "offer:task", now)


def _send_board(s: GameSession, snap: PlayerSnapshot, now: datetime) -> None:
    s.send(S_FRESH, b.complete(_fresh_msg(s, snap, now)))


@router.on(8290)
async def offer_refresh(s: GameSession, msg: pb.RewardFreshReqMsg) -> None:
    """``isButton`` falso: o painel abriu ou o relógio de 30 min zerou (sorteia de novo se venceu).
    Verdadeiro: renova já, 2 vezes grátis por dia e depois 2 diamantes (``payType`` 0 aceita vinculado)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    board = _board(snap, now)
    if snap.character.grades < OPEN_GRADE:
        s.log.info("8290 recusado: nível", nivel=snap.character.grades)
        return
    changed: list[object] = []
    if not msg.isButton:
        if not board.text or (now - board.updated_at).total_seconds() >= AUTO_REFRESH:
            changed.append(_roll(s, snap, now))
    else:
        free = ev.daily(snap, "offer:free", now)
        if free.value < FREE_REFRESH:
            free.value, free.updated_at = free.value + 1, now
            changed.append(free)
        else:
            spent = ledger.spend(snap.character, REFRESH_COST, "offer_refresh", now, bound=msg.payType == 0)
            if spent is None:
                s.log.info("8290 sem diamante")
                return
            changed += [snap.character, spent]
        changed.append(_roll(s, snap, now))
    if changed:
        await s.ctx.characters.save(*changed)
    if snap.character in changed:
        await granted(s, [], [], "", chat=False)
    _send_board(s, snap, now)


@router.on(8288)
async def offer_accept(s: GameSession, msg: pb.RewardAddedMsg) -> None:
    """Aceita a tarefa da posição ``rewardId`` do painel: uma por vez, até 20 + rewardCount por dia."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    board, task = _board(snap, now), _task(snap, now)
    data = _json(board)
    pos = msg.rewardId
    done = ev.daily(snap, "offer:count", now).value
    if task.value or done >= BASE_COUNT or not data or not 0 <= pos < len(data["ids"]) or data["st"][pos] != CAN_ACCEPT:
        s.log.info("8288 recusado", pos=pos, aceita=task.value, feitas=done)
        return
    data["st"][pos] = ACCEPTED
    board.text = json.dumps(data)
    task.value, task.text, task.updated_at = data["ids"][pos], json.dumps({"q": data["q"][pos], "pos": pos}), now
    await s.ctx.characters.save(board, task)
    s.send(S_REWARD, pb.RewardUpdatedRspMsg(reward=[_task_info(task)]))  # (visto) 231733 #1465-#1466: 4198, 4197
    _send_board(s, snap, now)


def _clear(snap: PlayerSnapshot, now: datetime, state: int) -> tuple[EventState, EventState, int, int]:
    board, task = _board(snap, now), _task(snap, now)
    data, info = _json(board), _json(task)
    if data and info.get("pos", -1) < len(data["ids"]) and data["ids"][info["pos"]] == task.value:
        data["st"][info["pos"]] = state
        board.text = json.dumps(data)
    tid = task.value
    task.value, task.text, task.updated_at = 0, "", now
    return board, task, tid, int(info.get("q", 1))


@router.on(8289)
async def offer_remove(s: GameSession, msg: pb.RewardRemovedMsg) -> None:
    """Desiste da tarefa: volta a ficar disponível no painel."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    if not msg.templateId or _task(snap, now).value != msg.templateId:
        s.log.info("8289 recusado", tarefa=msg.templateId)
        return
    board, task, tid, quality = _clear(snap, now, CAN_ACCEPT)
    await s.ctx.characters.save(board, task)
    # o cliente só tira a tarefa da lista com isComplete (TaskGainMovie.isGiveUp pula a animação)
    s.send(S_REWARD, pb.RewardUpdatedRspMsg(reward=[_reward_info(tid, quality, complete=True)]))
    _send_board(s, snap, now)


@router.on(8291)
async def offer_finish(s: GameSession, msg: pb.RewardFinishedReqMsg) -> None:
    """Entrega a tarefa com as condições cumpridas (``progress``) ou com ``isPass`` (contrato 2 ativo).

    Prêmio como o OfferTaskItem mostra: RewardPlayGP/RewardGold x qualidade x nível (qualidade 5 = x6): (visto)
    oficial_20261024-121659-1 #498-#506, tarefa 24 qualidade 5 no nível 19: 18.240 de EXP e 2.280 de ouro. Pacotes:
    109, 3, 4197, 4198 (``isAccept`` e a data), 4152 (leed 24, até completar), 4413 {"reward", total do dia, hora
    do 1º}, 4196 {TemplateId} e o 83 só com a EXP (visto 145704 #225-#233, 151436 #653-#660)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    task = _task(snap, now)
    row = s.ctx.templates.get("RewardTemps", task.value) if task.value == msg.templateId else None
    quality = int(_json(task).get("q", 1))
    mult = (quality + 1 if quality == 5 else quality) * snap.character.grades
    drops = [
        (t, int(row[k]) * mult)
        for t, k in ((rewards.EXP, "RewardPlayGP"), (-100, "RewardGold"), (-300, "RewardStrategy"))
        if row and int(row[k])
    ]
    passed = msg.isPass and ev.has_contract(snap, PASS_CONTRACT, now)
    if row is None or not (passed or _met(s, task)):
        s.log.info("8291 recusado", tarefa=msg.templateId, passe=msg.isPass)
        return
    if not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        return
    shown = _task_info(task, done_at=now)
    board, task, tid, _ = _clear(snap, now, COMPLETED)
    count = ev.daily(snap, "offer:count", now)
    count.value, count.updated_at = count.value + 1, now
    # painel (DayGuideManager "reward" -> atividade 9): 4413 com o contador; o 4412 do 8518 leva o mesmo
    clicked = ev.click(snap, "reward", now)
    new, _ = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), board, task, count, clicked, *new)
    from . import events  # handlers.events importa este módulo

    if any(t == -100 for t, _ in drops):
        castle_yield(s)
    _player(s)
    _send_board(s, snap, now)
    s.send(S_REWARD, pb.RewardUpdatedRspMsg(reward=[shown]))
    await events.leed_done(s, events.BOUNTY_LEED)  # "Complete Bounty Quest" (PassCount 5)
    s.send(S_CLICK_ADD, pb.ClickDatasRspMsg(info=[events.click_info(clicked)]))
    s.send(S_OFFER_DONE, pb.RewardRemovedMsg(templateId=tid))
    gp = sum(n for t, n in drops if t == rewards.EXP)
    # TODO(inventado): o texto do Daru (RewardStrategy) sem captura; o oficial não fala do ouro
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=rules.exp_text(gp)))


@router.on(8298)
async def offer_arrest(s: GameSession, msg: pb.RewardArrestMsg) -> None:
    """ "Capturar" o NPC ``param1`` da condição tipo 14 ("Apprehend Claren the Swordsman": Para1 20000 é o herói
    NPC do ``GameHeroTemp``): luta das tropas e do herói do jogador contra ele (type 3, como o chefe do Sky Trails);
    vencendo, a condição conta. (visto) 20261030-145704 #245-#290 (Azimo 20003): 140 em luta, 157 battleType 12
    mapTempId 1 e, no fim, 150, 109, 3, 4198 do andamento, 83 do HP pack, 4103 (battleScene 9, Daru = tropa
    perdida), 140 parado, 150 e 100; o 4382 vem no 8747 da volta."""
    from ..battle import Battle
    from .campaign import player_hero  # campaign importa player, que importa este módulo
    from .outer_city import ARMY_FIGHTING, ARMY_IDLE, MAP_ARMY, _army_brief, _casualties
    from .outer_city import S_MAP_SYNC as MAP_SYNC
    from .singlepass import boss_spec

    snap, npc = s.snapshot, msg.param1
    # só os NPCs de alguma condição 14 (o cliente não escolhe herói qualquer); a contagem vale para a tarefa aceita
    wanted = next(s.ctx.templates.find("RewardCondictionInfos", CondictionType=str(CAPTURE), Para1=str(npc)), None)
    row = s.ctx.templates.get("GameHeroTemp", npc) if wanted else None
    if snap is None or snap.castle is None or row is None or s.battle is not None or msg.condictionType != CAPTURE:
        s.log.info("8298 captura recusada", tipo=msg.condictionType, npc=npc)
        return
    spec = boss_spec(s, row, max(1, int(row.get("Live") or 1)), ARREST_TYPE) | {"battleScene": ARREST_SCENE}
    spec["heroes"][0]["castTime"] = 6000  # (visto) #247

    async def finished(battle: Battle, won: bool) -> None:
        s.battle, s.hero_sp, s.outer_fight_over = None, battle.player_sp, True
        changed: list[EventState] = []

        def before_report() -> None:
            if won:
                changed.extend(_progress_now(s, CAPTURE, 1, npc))

        def idle() -> None:  # (visto) #286: o 140 parado logo depois do 4103
            s.send(MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s, ARMY_IDLE)))

        await _casualties(s, battle, won, ARREST_SCENE, before_report, after_report=idle, heal_first=True)
        if changed:
            await s.ctx.characters.save(*changed)

    s.send(MAP_SYNC, pb.MapUpdatedMsg(updatedType=MAP_ARMY, army=_army_brief(s, ARMY_FIGHTING)))  # um só (#246)
    s.battle = Battle(
        spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings
    )
    s.battle.start()


# ---------------------------------------------------------------- tarefas em anel


def _ring(snap: PlayerSnapshot, now: datetime) -> EventState:
    """``value`` = anéis feitos hoje; ``text`` = {"t": TemplateId atual}."""
    return ev.daily(snap, "ring", now)


def _send_ring(s: GameSession, snap: PlayerSnapshot, now: datetime, *, complete: int = 0) -> None:
    st = _ring(snap, now)
    s.send(S_RING_SUM, pb.SimplePropertyMsg(param1=st.value))
    tid = complete or _json(st).get("t", 0)
    if tid:
        info = _reward_info(tid, 0, complete=bool(complete), accept=False, progress=_json(st).get("n", []))
        s.send(S_RING, pb.RewardUpdatedRspMsg(reward=[info]))


@router.on(8731)
async def ring_state(s: GameSession, _: object) -> None:
    assert s.snapshot is not None
    _send_ring(s, s.snapshot, s.ctx.clock.now())


def _roll_ring(s: GameSession, snap: PlayerSnapshot) -> int:
    grade = snap.character.grades
    pool = [
        int(r["TemplateId"])
        for r in s.ctx.templates.find("RewardTemps", Type=RING)
        if int(r["NeedMinLevel"]) <= grade < int(r["NeedMaxLevel"])
    ]
    return random.choice(pool) if pool else 0


@router.on(8732)
async def ring_accept(s: GameSession, _: object) -> None:
    """Pega o próximo anel (nível 35+, até 200 por dia)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    st = _ring(snap, now)
    tid = _roll_ring(s, snap)
    if _json(st).get("t") or snap.character.grades < RING_GRADE or st.value >= RING_MAX or not tid:
        s.log.info("8732 recusado", feitos=st.value)
        _send_ring(s, snap, now)
        return
    st.text, st.updated_at = json.dumps({"t": tid}), now
    await s.ctx.characters.save(st)
    _send_ring(s, snap, now)


def _ring_drops(s: GameSession, snap: PlayerSnapshot, tid: int, number: int) -> list[rewards.Drop]:
    """Prêmio do anel (RewardGold/Strategy/PlayGP) + RewardGoods do passo ``number`` (a cada 10)."""
    row = s.ctx.templates.get("RewardTemps", tid) or {}
    drops = [
        (t, int(row.get(k, 0)))
        for t, k in ((rewards.EXP, "RewardPlayGP"), (-100, "RewardGold"), (-300, "RewardStrategy"))
        if int(row.get(k, 0))
    ]
    grade = snap.character.grades
    for g in s.ctx.templates.rows("RewardGoods"):
        steps = g["RepeatStep"].split(",")
        if str(number) in steps and int(g["RepeatMinLevel"]) <= grade < int(g["RepeatMaxLevel"]):
            drops.append((int(g["RewardItemID"]), int(g["RewardItemCount"])))
    return drops


@router.on(8730)
async def ring_finish_now(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Termina o anel na hora: gasta 1x item 2131021 se tiver, senão 35 diamantes (TaskFrameII)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    st = _ring(snap, now)
    tid = int(_json(st).get("t", 0))
    drops = _ring_drops(s, snap, tid, st.value + 1)
    if not tid or not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        s.log.info("8730 recusado", anel=tid)
        return
    used = rewards.take_one(snap, RING_ITEM)
    spent = None if used else ledger.spend(snap.character, RING_COST, "ring_task", now, bound=False, ref=str(tid))
    if used is None and spent is None:
        s.log.info("8730 sem diamante")
        return
    extra: list[object] = []
    gone: tuple[object, ...] = ()
    if spent:
        extra.append(spent)
    elif used and used[1]:
        gone = (used[0],)
    elif used:
        extra.append(used[0])
    await _ring_done(s, st, tid, drops, extra, gone, used)


async def _ring_done(
    s: GameSession,
    st: EventState,
    tid: int,
    drops: list[rewards.Drop],
    extra: list[object],
    gone: tuple[object, ...],
    used: tuple[Item, bool] | None = None,
) -> None:
    """Fecha o anel ``tid``: +1 no dia, o prêmio, grava e responde (4616/4614, 111 e o ganho)."""
    snap = s.snapshot
    assert snap is not None
    st.value, st.text, st.updated_at = st.value + 1, "", s.ctx.clock.now()
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new, *extra, delete=gone)
    if used:
        s.send(S_ITEMS, rewards.taken_msg(used[0], used[1], s.player_id))
    _send_ring(s, snap, s.ctx.clock.now(), complete=tid)
    alert(s, text)
    await granted(s, drops, new, text)
    await progress(s, CIRCUIT)  # "Complete Circuit Quests" do painel


@router.on(8729)
async def ring_submit(s: GameSession, _: object) -> None:
    """Entrega o anel com as condições cumpridas (``progress``): o mesmo prêmio do 8730, sem custo. Sem as
    condições só devolve o estado. TODO(inventado): a resposta é a do 8730 (sem captura da entrega normal)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    st = _ring(snap, now)
    tid = int(_json(st).get("t", 0))
    drops = _ring_drops(s, snap, tid, st.value + 1) if tid else []
    if not tid or not _met(s, st, tid) or not rewards.can_grant(snap, s.ctx.templates, drops, now):
        s.log.info("8729 recusado", anel=tid)
        _send_ring(s, snap, now)
        return
    await _ring_done(s, st, tid, drops, [], ())


def login_push(s: GameSession) -> None:
    """tutorial_en #46 (4360), #53 (4616 do anel) e #54 (4198, vazio sem tarefa): o anel vem antes do 4198.
    O 4614 do anel em andamento e o 4198 com tarefa: só turco (login.json #56, #58)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    # vagas além das 20 (OfferRewardManager: max = 20 + rewardCount): o cliente não tem tela nem pacote que compre
    # vagas (nem do painel nem do anel, RingTaskManager só manda 8729-8732) e o pergaminho (SonType 213) gasta uma
    # das 20 (PlayerBagCellClickMediator); tutorial_en #46 manda 0. Bloqueio real (sem pacote): fica 0.
    s.send(S_COUNT, pb.RewardCountUpdateRspMsg(rewardCount=0))
    _send_ring(s, snap, now)
    task = _task(snap, now)
    msg = pb.RewardUpdatedRspMsg()
    if task.value:
        msg.reward.append(_task_info(task))
    s.send(S_REWARD, msg)
