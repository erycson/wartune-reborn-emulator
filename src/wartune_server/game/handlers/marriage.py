"""Casamento: pedido, noivado, escolha do casamento (MarrySpecTempInfo), divórcio e buscas.

``MarrySender`` e ``MarryManager`` (cliente) definem os ``opType`` e as respostas; as telas estão no cliente inglês
(``m9/scripts/marry``, ``2/scripts/marry/view``, ``m3/.../MarryUIMediator``, ``m7/scripts/farm/marrytree``).
Fluxo do cliente (MarryRingView, ``helpContent02``): pedido com o Engagement Ring 208033 em time de 2, noivado de
20 dias, cerimônia reservada na Andrew (15049 -> 4658 -> op 5), sala de casamento e troca de alianças.
O casal tem duas linhas em ``marriages``; quem está online tem a sua no snapshot.

ponytail: pedidos, ofertas de casamento e pedidos de divórcio ficam em memória (somem se o
servidor reiniciar), como o jogo do coração. A sala da cerimônia (8760) é bloqueio real (ver ``wedding_campaign``).
Pontos do casal (``couple``): missões 8774, jogo do coração 8802 e rega da árvore; gastos na loja 9611.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ...domain.models import BagType, Character, Item, Marriage, MarriageState, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import castle as cs
from .. import events as ev
from .. import marriage_tree as tree
from .. import rewards, rules, social
from ..builders import login as b
from ..builders.player import item_moved
from ..mail import send_system_mail
from ..router import router
from ..session import GameContext, GameSession
from .hero import send_items
from .login import player_info
from .player import alert, granted

S_PROPOSALS, S_QUALITY, S_LOVER, S_ROOMS, S_TASKS = 4656, 4658, 4659, 4662, 4675
S_DEAL_DIVORCE, S_MATES, S_MATE_SHOP, S_PLAYER = 358, 359, 365, 3
S_TREE, S_ITEMS = 4678, 115
TREE_WATER, TREE_CULTIVATE, TREE_CLEAR, TREE_HARVEST, TREE_REFRESH = 1001, 1002, 1003, 1004, 1005
ROSE = 208034  # Rose Hazel: MarryTreeView, recompensa da colheita
CHESTS = ((200, 2060475), (tree.TREE_MAX, 2060476), (tree.TREE_MAX + 1, 2060477))  # MarryTreeView: por status
PROPOSE, ANSWER, QUALITY_ANSWER, DIVORCE, PROPOSE_INFO, ROOM_LIST = 1, 3, 5, 8, 9, 10
CANCEL, FREE_DIVORCE, CONSULT, AGREE, FIND_MATES = 14, 15, 16, 17, 20
POINT = 1  # payType 1 = só diamante (DivorceAlert confere ``point``); 0 = vinculados primeiro
FREE_DIVORCE_DAYS = 5  # DivorceAlert: cônjuge offline há 5 dias ou mais
MIN_GRADE = 36  # MarryQuestFrame.__proposeHandler: "thane.grades < 36" recusa o pedido
MATES_MAX = 5  # MateRecommendFrame cria 5 linhas
TASK_ACCEPT = 2001
RING = 208033  # MarryModel.PROPOSE_RING: o MarryQuestFrame só manda o pedido com o anel na mochila
ENGAGE_DAYS = 20  # MarryRingView._totalDay 1728000 s: "hold a wedding before {1}. Otherwise ... cancelled."
DISCOUNT_SECONDS = 259200  # MarryModel.getMarryQualityCosts: desconto nas 72 h depois de marTime
TEXT_MAX = 100  # o texto padrão (marry.propose.MarryQuestFrame.inputText) tem 80 caracteres
NOT_SINGLE = "Cannot propose because your teammate is married"  # DialogOptionItem.propose.teammateIsNotSingle
NO_RING = "You don't have an Engagement Ring."  # DialogOptionItem.propose.lackRing
MATE_AWAY = "Your spouse is offline."  # o language_en não tem texto para o 16 sem resposta
DIVORCE_REFUSED = "Your spouse refused the divorce."  # idem para o 17 recusado
SINGLE = (MarriageState.ENGAGE_CANCELLED, MarriageState.DIVORCED)
MARRIED = MarriageState.MARRIED

_proposals: dict[int, dict[int, tuple[str, datetime]]] = {}  # alvo -> {quem pediu: (texto, quando)}
_offers: dict[int, tuple[int, int, int]] = {}  # quem confirma -> (quem paga, spec, payType)
_divorce_asks: dict[int, int] = {}  # quem confirma -> quem pediu


def _config(ctx: GameContext, name: str, default: int) -> int:
    row = next(ctx.templates.find("ConfigInfos", ConfigName=name), None)
    return int(row["ConfigValue"]) if row else default


async def _row(ctx: GameContext, cid: int) -> Marriage | None:
    session = ctx.online.get(cid)
    if session is not None and session.snapshot is not None:
        return session.snapshot.marriage
    return await ctx.characters.read(lambda uow: uow.marriages.by_character(cid))


def _expired(m: Marriage | None, now: datetime) -> bool:
    return m is not None and m.state == MarriageState.ENGAGED and now - m.since >= timedelta(days=ENGAGE_DAYS)


def _single(m: Marriage | None, now: datetime) -> bool:
    return m is None or m.state in SINGLE or _expired(m, now)


async def _set(ctx: GameContext, cid: int, mate: int, state: int, now: datetime, spec: int = 0) -> Marriage:
    """Atualiza (ou cria) a linha de ``cid`` e a coloca no snapshot dele se estiver online."""
    m = await _row(ctx, cid)
    if m is None:
        m = Marriage(cid, mate, state, now)
    if m.mate_id != mate or state == MarriageState.ENGAGED:
        m.mate_id, m.since, m.married_at, m.spec_id = mate, now, None, 0
    if state == MarriageState.MARRIED:
        if m.state != MarriageState.MARRIED:
            m.married_at = now
        m.spec_id = spec
    m.state = state
    session = ctx.online.get(cid)
    if session is not None and session.snapshot is not None:
        object.__setattr__(session.snapshot, "marriage", m)  # snapshot é frozen
    return m


async def _announce(ctx: GameContext, *rows: Marriage) -> None:
    for m in rows:
        if (session := ctx.online.get(m.character_id)) is not None:
            session.send(social.S_MARRIAGE, await social.marriage_msg(ctx, m))


def _pay(s: GameSession, c: Character, cost: int, pay_type: int, reason: str) -> object | None:
    """Cobra ``cost`` pelo ledger (payType 0 usa os vinculados primeiro). None = sem saldo."""
    return ledger.pay(c, cost, bind=pay_type != POINT, reason=reason, ref=str(c.id), now=s.ctx.clock.now())


async def _couple(
    s: GameSession, state: int, spec: int = 0, paid: Character | None = None, entry: object | None = None
) -> None:
    """Muda as duas linhas do casal (e grava quem pagou e o ledger) numa transação e avisa os dois."""
    snap = s.snapshot
    assert snap is not None and snap.marriage is not None
    now, mate = s.ctx.clock.now(), snap.marriage.mate_id
    rows = [
        await _set(s.ctx, s.player_id, mate, state, now, spec),
        await _set(s.ctx, mate, s.player_id, state, now, spec),
    ]
    await s.ctx.characters.save(*rows, *([paid] if paid else []), *([entry] if entry else []))
    await _announce(s.ctx, *rows)
    if paid is not None and (payer := s.ctx.online.get(paid.id or 0)) and payer.snapshot:
        payer.send(S_PLAYER, b.complete(player_info(payer, payer.snapshot)))


async def expire(s: GameSession) -> None:
    """Noivado sem cerimônia em 20 dias cai sozinho, sem custo (MarryRingView.tipData2). O cliente inglês não
    manda o (14, 1) do prazo: ``MarryManager.checkTime`` não tem chamador."""
    snap = s.snapshot
    if snap is not None and _expired(snap.marriage, s.ctx.clock.now()):
        await _couple(s, MarriageState.ENGAGE_CANCELLED)


def _pro(s: GameSession, c: Character, **fields: object) -> pb.MarriageProMsg:
    """Quem pediu/pretendente como as telas leem (MarryQuestFrame/MarryAnswerFrame.refreshView): ``property3``
    nível, ``property4`` guilda, ``property6`` cabeça (o padrão do cliente é o template do herói, ``pics``)."""
    mine = s.ctx.guilds.of(c.id or 0)
    pro = pb.MarriageProMsg(userIdA=c.id, nickNameA=c.nickname or "", jobA=c.job, **fields)  # type: ignore[arg-type]
    pro.property3, pro.property4, pro.property6 = c.grades, mine[0].name if mine else "", c.icon
    return b.complete(pro)


def _drop(target: GameSession | None, proposers: list[int], **fields: object) -> None:
    """4656 com ``property1`` falso tira o pedido da lista (MarryModel.updateProposeList); ``property7`` 1 abre a
    escolha da cerimônia."""
    if target is not None and proposers:
        infos = [b.complete(pb.MarriageProMsg(userIdA=p, property1=False, **fields)) for p in proposers]  # type: ignore[arg-type]
        target.send(S_PROPOSALS, pb.EngageMsg(engageInfos=infos))


def _rings(s: GameSession) -> list[Item]:
    snap = s.snapshot
    assert snap is not None
    return sorted((i for i in snap.items if i.template_id == RING and i.bag_type == BagType.BAG), key=lambda i: i.pos)


def _mate_player(c: Character) -> pb.FriendPlayer:
    return b.complete(
        pb.FriendPlayer(
            playerId=c.id, nickName=c.nickname or "", level=c.grades, sex=c.sex, job=c.job, attack=c.fighting_capacity
        )
    )


@router.on(8759)
async def marriage_request(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    await _request(s, msg)
    await save_pending(s.ctx)


async def _request(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    await expire(s)
    c, now, op = snap.character, s.ctx.clock.now(), msg.opType
    mine = snap.marriage
    if op == PROPOSE:
        other = s.ctx.online.get(msg.property1)  # o pedido é feito em time de 2: o alvo está online
        target = other.snapshot.character if other is not None and other.snapshot else None
        ok = target is not None and target.id != c.id and target.sex != c.sex and _single(mine, now)
        ok = ok and c.grades >= MIN_GRADE and target is not None and target.grades >= MIN_GRADE
        if not ok or other is None or other.snapshot is None:
            s.log.info("pedido de casamento recusado", alvo=msg.property1)
            return
        if not _single(other.snapshot.marriage, now):
            alert(s, NOT_SINGLE)
            return
        if not _rings(s):
            alert(s, NO_RING)
            return
        text = msg.property3[:TEXT_MAX]
        _proposals.setdefault(msg.property1, {})[s.player_id] = (text, now)
        other.send(S_PROPOSALS, pb.EngageMsg(engageInfos=[_pro(s, c, property1=True, property5=text)]))
    elif op == ANSWER:
        asked = _proposals.get(s.player_id, {}).pop(msg.property1, None)
        proposer = s.ctx.online.get(msg.property1)
        _drop(s, [msg.property1] if asked else [])
        if asked is None or not msg.property5 or not _single(mine, now):
            return
        if proposer is None or proposer.snapshot is None or not _single(proposer.snapshot.marriage, now):
            return
        rings = _rings(proposer)
        if not rings:
            alert(proposer, NO_RING)
            return
        # (dedução) o anel sai de quem pediu quando o pedido é aceito ("the equipped engagement ring will be removed")
        changed, deleted = rules.take_items(proposer.snapshot, rings, 1)
        _drop(s, list(_proposals.pop(s.player_id, {})))  # os outros pedidos ao noivo caem
        rows = [
            await _set(s.ctx, s.player_id, msg.property1, MarriageState.ENGAGED, now),
            await _set(s.ctx, msg.property1, s.player_id, MarriageState.ENGAGED, now),
        ]
        await s.ctx.characters.save(*rows, *changed, delete=tuple(deleted))
        send_items(proposer, changed, deleted)
        await _announce(s.ctx, *rows)
        _drop(proposer, [s.player_id], property7=1)  # (dedução) quem pediu é o líder: abre o QUALITY_SELECT
    elif op == QUALITY_ANSWER:
        await _quality_answer(s, msg.property5)
    elif op == DIVORCE and mine is not None and mine.state == MarriageState.MARRIED:
        if entry := _pay(s, c, _config(s.ctx, "divorce_need", 3999), msg.payType, "divorce"):
            await _couple(s, MarriageState.DIVORCED, paid=c, entry=entry)
    elif op == CANCEL and mine is not None and mine.state == MarriageState.ENGAGED:
        # sem chamador na interface inglesa (o checkTime do prazo é código morto); o prazo é ``expire``
        if entry := _pay(s, c, _config(s.ctx, "cancel_engage_need", 500), msg.payType, "cancel_engage"):
            await _couple(s, MarriageState.ENGAGE_CANCELLED, paid=c, entry=entry)
    elif op == FREE_DIVORCE and mine is not None and mine.state == MarriageState.MARRIED:
        mate = (await social.characters(s.ctx, [mine.mate_id])).get(mine.mate_id)
        seen = social.last_seen(mate) if mate is not None else None
        if s.ctx.online.get(mine.mate_id) is None and seen is not None and (now - seen).days >= FREE_DIVORCE_DAYS:
            await _couple(s, MarriageState.DIVORCED)
    elif op == CONSULT and mine is not None and mine.state == MarriageState.MARRIED:
        if (mate_session := s.ctx.online.get(mine.mate_id)) is not None:
            _divorce_asks[mine.mate_id] = s.player_id
            mate_session.send(S_DEAL_DIVORCE)
        else:
            alert(s, MATE_AWAY)
    elif op == AGREE and mine is not None and mine.state == MarriageState.MARRIED:
        asked_by = _divorce_asks.pop(s.player_id, None)
        cost = _config(s.ctx, "marriage_deal_divorce_point", 1799)
        if asked_by != mine.mate_id:
            return
        if not msg.property5:
            if (asker := s.ctx.online.get(asked_by)) is not None:
                alert(asker, DIVORCE_REFUSED)
        elif entry := _pay(s, c, cost, POINT, "divorce_deal"):
            await _couple(s, MarriageState.DIVORCED, paid=c, entry=entry)
    elif op == PROPOSE_INFO:
        other_c = (await social.characters(s.ctx, [msg.property1])).get(msg.property1)
        if other_c is not None:
            single = _single(await _row(s.ctx, msg.property1), now)
            s.send(S_LOVER, _pro(s, other_c, property1=single))  # falso: "Player already has a spouse"
    elif op == ROOM_LIST:
        s.send(S_ROOMS, pb.EngageMsg())  # sem salas: a cerimônia é pulada
    elif op == FIND_MATES:  # sem chamador na interface inglesa (MarrySender.findMates)
        out = pb.RecommendListMsg()
        for other in s.ctx.online.sessions():
            o = other.snapshot
            if o is None or o.character.sex == c.sex or o.character.grades < MIN_GRADE or not _single(o.marriage, now):
                continue
            if len(out.girlList) + len(out.boyList) < MATES_MAX:
                (out.boyList if o.character.sex else out.girlList).append(_mate_player(o.character))
        s.send(S_MATES, out)
    else:
        # 6 sala, 7 carro, 13 entrar na sala (cerimônia); 12 aliança; 18 helpMateTrain (ajuda de satisfação, sem
        # chamador no inglês)
        s.log.info("operação de casamento sem suporte", op=op)


_CEREMONY = (MarriageState.ENGAGED, MarriageState.MARRIED)


@router.on(15049)
async def buy_spec(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    await _buy_spec(s, msg)
    await save_pending(s.ctx)


async def _buy_spec(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Escolhe o casamento (MarrySpecTempInfo ``property1``); o cônjuge confirma (4658 -> op 5).

    Noivo reserva a cerimônia; casado nas 72 h seguintes reserva com desconto (TopToolsBar "Wedding Ceremony").
    """
    snap = s.snapshot
    assert snap is not None
    await expire(s)
    m, spec = snap.marriage, s.ctx.templates.get("MarrySpecTempInfos", msg.property1)
    mate = s.ctx.online.get(m.mate_id) if m is not None else None
    if m is None or m.state not in _CEREMONY or spec is None or mate is None:
        s.log.info("15049 recusado", spec=msg.property1)
        return
    c, price = snap.character, _price(s, m, spec)
    if price > c.point + (c.gift_token if msg.payType != POINT else 0):
        return
    _offers[m.mate_id] = (s.player_id, msg.property1, msg.payType)
    offer = pb.MarriageProMsg(userIdA=s.player_id, nickNameA=c.nickname or "")
    offer.property2, offer.property3 = msg.property1, msg.payType
    mate.send(S_QUALITY, b.complete(offer))


def _price(s: GameSession, m: Marriage, spec: dict[str, str] | object) -> int:
    """MarryModel.getMarryQualityCosts: ``Points`` cheio, ou ``ceil(Points x Discount / 100)`` nas 72 h depois
    do casamento (``marTime``; noivo não tem data, então paga cheio)."""
    row = spec if isinstance(spec, dict) else dict(spec)  # type: ignore[call-overload]
    price = int(row["Points"])
    if m.married_at is not None and (s.ctx.clock.now() - m.married_at).total_seconds() < DISCOUNT_SECONDS:
        price = -(-price * int(row["Discount"]) // 100)
    return price


async def _quality_answer(s: GameSession, accept: bool) -> None:
    snap = s.snapshot
    assert snap is not None
    offer = _offers.pop(s.player_id, None)  # o MarryConfirmFrame manda true e, ao fechar, false: vale o primeiro
    m = snap.marriage
    if offer is None or not accept or m is None or m.state not in _CEREMONY or offer[0] != m.mate_id:
        return
    payer_id, spec_id, pay_type = offer
    payer = s.ctx.online.get(payer_id)
    spec = s.ctx.templates.get("MarrySpecTempInfos", spec_id)
    if payer is None or payer.snapshot is None or spec is None:
        return
    entry = _pay(s, payer.snapshot.character, _price(s, m, spec), pay_type, "wedding")
    if entry is None:
        return
    await _couple(s, MarriageState.MARRIED, spec_id, paid=payer.snapshot.character, entry=entry)
    await ensure_tree(s.ctx, snap)  # a árvore do casal nasce com o casamento (os dois estão online)
    goods = [(int(t), int(n)) for t, n in (part.split(",") for part in spec["Rewards"].split("|") if part)]
    for cid in (s.player_id, payer_id):  # presentes do casamento pelo correio (até 5 por correio)
        for i in range(0, len(goods), 5):
            await send_system_mail(s.ctx, cid, spec["TemplateName"], spec["TemplateName"], goods[i : i + 5])


@router.on(8760)
async def wedding_campaign(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Sala da cerimônia (101 alianças, 102-109 bolo/champanhe/doces/buquê/fogos, 104/112 presentes, 105 senha,
    106 expulsar, 110/111 convidar; MarryWeddingDialogFrame). Pendente: o cliente (m3
    MarryUIMediator/MarryWeddingDialogFrame, m9 marry/room) usa a sala do RoomManager; os mapas 4301-4303 não têm
    nós. Sem a sala, o 8353 tipo 1 fica sem destino.
    Quem aceita a oferta já sai casado (presentes pelo correio)."""
    s.log.info("cerimônia de casamento sem suporte", op=msg.opType)


async def ensure_tree(ctx: GameContext, snap: PlayerSnapshot) -> None:
    """Casado sem árvore: copia a do cônjuge ou planta uma nova nas duas linhas (o 4386 é montado sem ``await``)."""
    m = snap.marriage
    if m is None or m.state != MARRIED or m.tree:
        return
    mate = await _row(ctx, m.mate_id)
    if mate is not None and mate.tree:
        m.tree = mate.tree
        await ctx.characters.save(m)
        return
    other = (await social.characters(ctx, [m.mate_id])).get(m.mate_id)
    if other is None or mate is None:
        return
    m.tree = mate.tree = json.dumps(tree.new(snap.character, other, ctx.templates, ctx.clock.now()))
    await ctx.characters.save(m, mate)


async def _store(s: GameSession, t: dict[str, Any], *extra: object, delete: tuple[object, ...] = ()) -> None:
    """Grava ``t`` nas duas linhas (com ``extra``) e manda o 4678 a quem do casal estiver online."""
    snap = s.snapshot
    assert snap is not None and snap.marriage is not None
    m = snap.marriage
    mate = await _row(s.ctx, m.mate_id)
    rows = [m, *([mate] if mate is not None else [])]
    shown = tree.msg(t)
    t["feedUser"] = 0  # só o 4678 da rega leva quem regou (o cliente toca o efeito): não repete no próximo
    for row in rows:
        row.tree = json.dumps(t)
    await s.ctx.characters.save(*rows, *extra, delete=delete)
    for row in rows:
        if (session := s.ctx.online.get(row.character_id)) is not None:
            session.send(S_TREE, shown)


def _side(t: dict[str, Any], cid: int) -> str:
    return "A" if t["userIdA"] == cid else "B"


def _water(s: GameSession, t: dict[str, Any], now: datetime) -> bool:
    if t["start"] or t["feedCount"] >= _config(s.ctx, "mar_feed_count", 2):
        return False
    start, end = now.timestamp(), now.timestamp() + _config(s.ctx, "mar_tree_time", 300) * 60
    t |= {"start": start, "end": end, "startTime": tree.stamp(start), "endTime": tree.stamp(end), "stateValue": 0,
          "feedCount": t["feedCount"] + 1, "feedUser": s.player_id, "treeState": tree.pests(),
          "isGetA": False, "isGetB": False}  # fmt: skip
    return True


def _growing(t: dict[str, Any], now: datetime) -> bool:
    return bool(t["start"]) and now.timestamp() < t["end"]


async def _cultivate(s: GameSession, t: dict[str, Any], now: datetime) -> bool:
    """MarryTreeFosterFrame: os itens com ``Feed`` da bancada (0-9) somam ``Feed`` × quantidade, em dobro no item
    sorteado do lado; saem todos."""
    snap = s.snapshot
    assert snap is not None
    side = _side(t, s.player_id)
    count = f"train{side}Count"
    if not _growing(t, now) or t["stateValue"] >= tree.TREE_MAX:
        return False
    if t[count] >= _config(s.ctx, "mar_tree_train_count", 10):
        return False
    bench = [i for i in snap.items if i.bag_type == BagType.STORE and 0 <= i.pos < tree.BENCH]
    fed = [(i, int((s.ctx.templates.get("ItemTempInfos", i.template_id) or {}).get("Feed") or 0)) for i in bench]
    fed = [(i, f) for i, f in fed if f > 0]
    if not fed:
        return False
    gain = sum(f * i.count * (2 if i.template_id == t[f"train{side}Type"] else 1) for i, f in fed)
    t["stateValue"] = min(tree.TREE_MAX, t["stateValue"] + gain)
    t[count] += 1
    for i, _ in fed:
        snap.items.remove(i)
    await _store(s, t, delete=tuple(i for i, _ in fed))
    for i, _ in fed:
        s.send(S_ITEMS, item_moved(BagType.STORE, 0, i.pos, None, s.player_id))
    return True


def _clear(t: dict[str, Any], now: datetime) -> bool:
    """Tira o mato e a praga que já chegaram (as horas por vir continuam no ``treeState``)."""
    states = t["treeState"].split(",")
    reached = tree.passed(t, now)
    if not _growing(t, now) or all(x == "0" for x in states[:reached]):
        return False
    t["stateValue"] = tree.value(t, now)  # o desconto das que ficaram até agora vira definitivo
    t["treeState"] = ",".join("0" if n < reached else x for n, x in enumerate(states))
    return True


def _chest(value: int) -> int:
    return next(chest for cut, chest in CHESTS if value < cut)


async def _harvest(s: GameSession, t: dict[str, Any], now: datetime) -> bool:
    snap = s.snapshot
    assert snap is not None
    got = f"isGet{_side(t, s.player_id)}"
    if not t["start"] or now.timestamp() < t["end"] or t[got]:
        return False
    value = tree.value(t, now)
    # TODO(inventado): quantidade de Rose Hazel (o cliente só lista o item na recompensa)
    drops = [(ROSE, 1 + value // 100), (_chest(value), 1)]
    if not rewards.can_grant(snap, s.ctx.templates, drops, now):
        return False
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    t[got] = True
    if t["isGetA"] and t["isGetB"]:  # "Can be energized again once your spouse harvests it"
        t |= {"start": 0, "end": 0, "startTime": "", "endTime": "", "stateValue": 0, "treeState": tree.NO_PESTS,
              "isGetA": False, "isGetB": False}  # fmt: skip
    await _store(s, t, *rewards.owners(snap), *new)
    await granted(s, drops, new, text)
    return True


async def _refresh(s: GameSession, t: dict[str, Any], now: datetime) -> bool:
    """Troca o item em dobro do lado por ouro (``fresh_martree_item``)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    cost = _config(s.ctx, "fresh_martree_item", 100000)
    cs.settle(snap, s.ctx.templates, now)
    kind = f"train{_side(t, s.player_id)}Type"
    pool = [x for x in tree.feed_items(s.ctx.templates) if x != t[kind]]
    if snap.character.gold < cost or not pool:
        return False
    snap.character.gold -= cost
    t[kind] = random.choice(pool)
    await _store(s, t, snap.character, snap.castle)
    cs.castle_yield(s)
    return True


@router.on(8773)
async def marriage_tree(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Árvore do casal na fazenda (1001 regar, 1002 cultivar, 1003 limpar, 1004 colher, 1005 trocar o item;
    MarryTreeView/MarryTreeFosterFrame, resposta 4678; regras em ``game/marriage_tree.py``)."""
    snap = s.snapshot
    assert snap is not None
    await ensure_tree(s.ctx, snap)
    now = s.ctx.clock.now()
    t = tree.fresh(tree.load(snap.marriage), now) if snap.marriage and snap.marriage.state == MARRIED else {}
    ok = False
    if not t:
        pass
    elif msg.opType == TREE_WATER:
        ok = _water(s, t, now)
        if ok:
            await _store(s, t)
            await add_happy(s, int(_points_cfg(s)["water"]))
    elif msg.opType == TREE_CULTIVATE:
        ok = await _cultivate(s, t, now)
    elif msg.opType == TREE_CLEAR:
        ok = _clear(t, now)
        if ok:
            await _store(s, t)
    elif msg.opType == TREE_HARVEST:
        ok = await _harvest(s, t, now)
    elif msg.opType == TREE_REFRESH:
        ok = await _refresh(s, t, now)
    if not ok:
        s.log.info("8773 recusado", op=msg.opType)


# ---- pontos do casal ---------------------------------------------------------------------------------------------


def couple(m: Marriage | None) -> dict[str, Any]:
    """O JSON do casal (``marriages.couple``): ``happy`` (pontos do casal, o ``happy`` do 4657) e ``bought``."""
    data: dict[str, Any] = json.loads(m.couple) if m is not None and m.couple else {}
    return {"happy": 0, "bought": {}} | data


async def add_happy(s: GameSession, points: int, *extra: object) -> None:
    """Soma ``points`` aos pontos do casal nas duas linhas (o cônjuge offline pelo banco) e manda o 4657 novo."""
    snap = s.snapshot
    assert snap is not None
    m = snap.marriage
    if m is None or m.state != MARRIED or points <= 0:
        if extra:
            await s.ctx.characters.save(*extra)
        return
    mate = await _row(s.ctx, m.mate_id)
    data = couple(m)
    data["happy"] += points
    rows = [m, *([mate] if mate is not None else [])]
    for row in rows:
        row.couple = json.dumps(data)
    await s.ctx.characters.save(*rows, *extra)
    await _announce(s.ctx, *rows)


def _points_cfg(s: GameSession) -> dict[str, Any]:
    return {"water": 1} | dict(s.ctx.world.settings.get("couple_points") or {})


# ---- missões do casal -------------------------------------------------------------------------------------------

TASK_TYPE = 4  # RewardTemps.Type das missões do casal (4001-4005, ``RingTaskManager.getRewardTempByTempId``)
TASK_USE, TASK_TALK = 2004, 2005
TALK, KILL, FIREWORK = 16, 22, 23  # RewardCondictionInfos.CondictionType das missões do casal
TASK_KEY, TASKS_KEY = "marry:task", "marry:tasks"


def _task_info(tid: int, *, done: bool = False, accept: bool = True) -> pb.RewardInfo:
    return pb.RewardInfo(templateId=tid, isComplete=done, isAccept=accept, isSelect=True,
                         completedDate=b.fmt_time(datetime(2000, 1, 1)))  # fmt: skip


def _task_cond(s: GameSession, tid: int) -> Any:
    return next(s.ctx.templates.find("RewardCondictionInfos", TemplateId=tid), None)


@router.on(8774)
async def marriage_task(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Missões do casal (``RewardTemps`` ``Type`` 4; o cliente só oferece casado, SpaceDialogFrame ``isMarry``): 2001
    pega uma (``marriage_task_count`` por dia), 2005 fala com a NPC (condição 16, o cliente leva até ela), 2004 usa o
    item da missão (``property1`` a posição na mochila, MarryTaskMapFrame; 22 a flecha de Cupido, 23 os fogos: o
    item vai para a mochila ao pegar). Feita: ouro e Daru do template e ``RewardHappy`` +
    ``mar_task_add_happy`` nos pontos do casal; 4675 com ``isComplete``.
    (dedução) usar o item cumpre a 22/23: o cliente mostra o lugar, e a luta e o fogo no céu não têm pacote próprio."""
    snap = s.snapshot
    assert snap is not None
    m, now = snap.marriage, s.ctx.clock.now()
    if m is None or m.state != MARRIED:
        s.log.info("8774 sem casamento", op=msg.opType)
        return
    task = ev.state(snap, TASK_KEY, now)
    done_today = ev.daily(snap, TASKS_KEY, now)
    if msg.opType == TASK_ACCEPT:
        pool = [int(r["TemplateId"]) for r in s.ctx.templates.find("RewardTemps", Type=TASK_TYPE)]
        if task.value or done_today.value >= _config(s.ctx, "marriage_task_count", 10) or not pool:
            s.log.info("8774 recusado", ativa=task.value, hoje=done_today.value)
            return
        tid = random.choice(pool)
        cond = _task_cond(s, tid)
        carries = cond is not None and int(cond["CondictionType"]) in (KILL, FIREWORK)
        drops = [(int(cond["Para1"]), 1)] if carries else []
        if drops and not rewards.can_grant(snap, s.ctx.templates, drops, now):
            return
        new, text = rewards.grant(snap, s.ctx.templates, drops) if drops else ([], "")
        task.value, task.updated_at = tid, now
        await s.ctx.characters.save(task, *rewards.owners(snap), *new)
        if drops:
            await granted(s, drops, new, text)
        s.send(S_TASKS, pb.RewardUpdatedRspMsg(reward=[_task_info(tid)]))
        return
    cond = _task_cond(s, task.value) if task.value else None
    kind = int(cond["CondictionType"]) if cond is not None else 0
    para = int(cond["Para1"]) if cond is not None else 0
    used: list[Item] = []
    if msg.opType == TASK_TALK and kind == TALK:
        pass
    elif msg.opType == TASK_USE and kind in (KILL, FIREWORK):
        # MarrySender.useTaskGoods manda a posição na mochila (``info.pos``), não o modelo
        used = [i for i in snap.items if i.pos == msg.property1 and i.bag_type == BagType.BAG and i.template_id == para]
        if not used:
            return
    else:
        s.log.info("8774 sem missão para isso", op=msg.opType, missao=task.value)
        return
    row = s.ctx.templates.get("RewardTemps", task.value) or {}
    changed, deleted = rules.take_items(snap, used, 1) if used else ([], [])
    tid = task.value
    snap.character.gold += int(row.get("RewardGold") or 0)
    snap.character.strategy += int(row.get("RewardStrategy") or 0)
    task.value, task.updated_at = 0, now
    done_today.value += 1
    done_today.updated_at = now
    happy = int(row.get("RewardHappy") or 0) + _config(s.ctx, "mar_task_add_happy", 50)
    await add_happy(s, happy, snap.character, task, done_today, *changed)
    if deleted:
        await s.ctx.characters.save(delete=tuple(deleted))
    send_items(s, changed, deleted)
    s.send(S_PLAYER, b.complete(player_info(s, snap)))
    s.send(S_TASKS, pb.RewardUpdatedRspMsg(reward=[_task_info(tid, done=True)]))


# ---- jogo do coração --------------------------------------------------------------------------------------------

HEART_START, HEART_ACCEPT, HEART_ANSWER, HEART_TIMEOUT, HEART_QUIT = 3001, 3002, 3003, 3004, 3005
S_HEART_ASK, S_HEART = 4690, 4691
HEARTS_KEY = "marry:hearts"  # jogos do dia (``answerNum`` do 4657)


@dataclass
class Heart:
    """Um jogo do coração: ``a`` chamou, ``b`` aceitou. ``done``: [modelo, resposta de a, resposta de b] por pergunta
    (-1 = sem resposta, 0 = A; MarryHeartResultItem.getAnswer)."""

    a: int
    b: int
    questions: list[int]
    seconds: int
    order: int = 1
    asked_at: datetime | None = None
    answers: dict[int, int] = field(default_factory=dict)
    done: list[list[int]] = field(default_factory=list)


_heart_asks: dict[int, int] = {}  # cônjuge chamado -> quem chamou
_hearts: dict[int, Heart] = {}  # os dois do casal -> o jogo
NO_ANSWER = -1


def _heart_cfg(s: GameSession) -> dict[str, Any]:
    return {"questions": 10, "seconds": 30, "points": 2} | dict(s.ctx.world.settings.get("marriage_heart") or {})


def _options(s: GameSession, tid: int) -> list[int]:
    """MarryHeartFrame mostra ``Option(options[i]+1)`` se ``options[i]`` < opções preenchidas (``getAnswersNum``)."""
    row = s.ctx.templates.get("HeartTempInfos", tid) or {}
    return list(range(sum(1 for i in range(1, 5) if row.get(f"Option{i}"))))


def _sync(h: Heart) -> int:
    hits = sum(1 for _, x, y in h.done if x >= 0 and x == y)
    return hits * 100 // len(h.done) if h.done else 0


def _heart_msg(s: GameSession, h: Heart, viewer: int) -> pb.MarriageHeartMsg:
    """4691 para ``viewer``: ``optionA`` é a resposta dele e ``optionB`` a do cônjuge (MarryHeartResultItem
    "myAnswer"/"otherAnswer"; (dedução) por isso troca para ``b``); ``result`` 1 acerto, 0 erro."""
    out = pb.MarriageHeartMsg(maxOrder=len(h.questions), syncRate=_sync(h))
    for order, (tid, x, y) in enumerate(h.done, 1):
        mine, other = (x, y) if viewer == h.a else (y, x)
        out.lastQuestions.add(order=order, templateId=tid, options=_options(s, tid), optionA=mine, optionB=other,
                              result=int(x >= 0 and x == y), random=int(viewer != h.a))  # fmt: skip
    if h.order <= len(h.questions):
        tid = h.questions[h.order - 1]
        left = h.seconds - int((s.ctx.clock.now() - (h.asked_at or s.ctx.clock.now())).total_seconds())
        # random 0 = "You", 1 = "He/She" no texto da pergunta; (dedução) a pergunta é sobre quem chamou
        out.curQuestion.CopyFrom(pb.HeartMsg(order=h.order, templateId=tid, options=_options(s, tid),
                                             optionA=NO_ANSWER, optionB=NO_ANSWER, remainTime=max(0, left),
                                             random=int(viewer != h.a)))  # fmt: skip
    return out


def _heart_send(s: GameSession, h: Heart) -> None:
    for cid in (h.a, h.b):
        if (o := s.ctx.online.get(cid)) is not None:
            o.send(S_HEART, _heart_msg(s, h, cid))


async def _heart_reward(s: GameSession, h: Heart) -> None:
    """Fim: Rose Hazel x ``syncRate // 5`` a cada um (o MarryHeartFrame mostra 208034 x ``syncRate / 5``; mochila,
    senão correio) e, TODO(inventado), ``points`` por acerto nos pontos do casal."""
    count = _sync(h) // 5
    for cid in (h.a, h.b) if count else ():
        drops = [(ROSE, count)]
        o = s.ctx.online.get(cid)
        if o is not None and o.snapshot is not None and rewards.can_grant(o.snapshot, s.ctx.templates, drops,
                                                                          s.ctx.clock.now()):  # fmt: skip
            new, text = rewards.grant(o.snapshot, s.ctx.templates, drops)
            await s.ctx.characters.save(*rewards.owners(o.snapshot), *new)
            await granted(o, drops, new, text)
        else:
            await send_system_mail(s.ctx, cid, "Heart to Heart", "Heart to Heart", drops)  # TODO(inventado): título
    hits = sum(1 for _, x, y in h.done if x >= 0 and x == y)
    await add_happy(s, hits * int(_heart_cfg(s)["points"]))


async def _heart_next(s: GameSession, h: Heart) -> None:
    """Fecha a pergunta da vez e passa à próxima; depois da última, a recompensa e o jogo acaba."""
    h.done.append([h.questions[h.order - 1], h.answers.get(h.a, NO_ANSWER), h.answers.get(h.b, NO_ANSWER)])
    h.order, h.answers, h.asked_at = h.order + 1, {}, s.ctx.clock.now()
    _heart_send(s, h)
    if h.order > len(h.questions):
        _hearts.pop(h.a, None)
        _hearts.pop(h.b, None)
        await _heart_reward(s, h)


@router.on(8802)
async def marriage_heart(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Jogo do coração (``HeartTempInfos``; MarryManager/MarryHeartFrame do m9): 3001 chama o cônjuge (4690 abre o
    "aceita?"), 3002 aceita (4691 com a 1ª pergunta aos dois), 3003 responde (``property1`` a ordem, ``property2`` o
    ``selectIndex`` 0-based), 3004 o relógio da pergunta ``property1`` zerou, 3005 desiste (4691 sem pergunta).
    TODO(inventado): 10 perguntas de 30 s e acerto = mesma opção (``marriage_heart``, 0111)."""
    snap = s.snapshot
    assert snap is not None
    m, op = snap.marriage, msg.opType
    mate = s.ctx.online.get(m.mate_id) if m is not None and m.state == MARRIED else None
    limit = _config(s.ctx, "mar_heart_count", 1)  # MarryModel.canAnswer: ``answerNum`` do 4657 abaixo dele
    if op in (HEART_START, HEART_ACCEPT) and ev.daily(snap, HEARTS_KEY, s.ctx.clock.now()).value >= limit:
        s.log.info("jogo do coração: limite do dia")
        return
    if op == HEART_START:
        if mate is None or s.player_id in _hearts or m is None:
            s.log.info("jogo do coração: cônjuge offline ou já jogando")
            alert(s, MATE_AWAY) if mate is None else None
            return
        _heart_asks[m.mate_id] = s.player_id
        mate.send(S_HEART_ASK)
    elif op == HEART_ACCEPT:
        caller = _heart_asks.pop(s.player_id, None)
        if mate is None or m is None or caller != m.mate_id or s.player_id in _hearts:
            return
        cfg = _heart_cfg(s)
        pool = [int(r["TemplateId"]) for r in s.ctx.templates.rows("HeartTempInfos")]
        h = Heart(caller, s.player_id, random.sample(pool, min(int(cfg["questions"]), len(pool))), int(cfg["seconds"]))
        h.asked_at = now = s.ctx.clock.now()
        _hearts[h.a] = _hearts[h.b] = h
        counts = []
        for o in (s, mate):
            assert o.snapshot is not None
            st = ev.daily(o.snapshot, HEARTS_KEY, now)
            st.value, st.updated_at = st.value + 1, now
            counts.append(st)
        await s.ctx.characters.save(*counts)
        rows = [r for o in (s, mate) if o.snapshot is not None and (r := o.snapshot.marriage) is not None]
        await _announce(s.ctx, *rows)
        _heart_send(s, h)
    elif op in (HEART_ANSWER, HEART_TIMEOUT):
        game = _hearts.get(s.player_id)
        if game is None or msg.property1 != game.order:
            return
        h = game
        if op == HEART_ANSWER and 0 <= msg.property2 < len(_options(s, h.questions[h.order - 1])):
            h.answers.setdefault(s.player_id, msg.property2)
        if op == HEART_TIMEOUT or len(h.answers) == 2:
            await _heart_next(s, h)
    elif op == HEART_QUIT and (quit_game := _hearts.get(s.player_id)) is not None:
        _hearts.pop(quit_game.a, None)
        _hearts.pop(quit_game.b, None)
        quit_game.order = len(quit_game.questions) + 1
        _heart_send(s, quit_game)
    await save_pending(s.ctx)


# ---- loja do altar ----------------------------------------------------------------------------------------------

SHOP_BUY = 2  # AltarShopListMsg.op: (dedução) 2 compra ``templateId``; os outros listam


@router.on(9611)
async def mate_skill_shop(s: GameSession, msg: pb.AltarShopListMsg) -> None:
    """Loja do altar (ConfigInfo ``Mate_Shop``: modelo,preço,máximo,tipo; as habilidades da Guerra de Vênus) paga com
    os pontos do casal (``altarScore``). A compra (op 2) gasta os pontos das duas linhas e conta no máximo do casal; a
    resposta é a lista nova (365). TODO(inventado): o op da compra e os pontos do casal como ``altarScore``."""
    snap = s.snapshot
    assert snap is not None
    m = snap.marriage
    row = next(s.ctx.templates.find("ConfigInfos", ConfigName="Mate_Shop"), None)
    parts = (x.split(",") for x in (row["ConfigValue"].split("|") if row else []))
    shop = {int(t): (int(p), int(n)) for t, p, n, _ in parts}
    data = couple(m)
    if msg.op == SHOP_BUY:
        price, most = shop.get(msg.templateId, (0, 0))
        bought = int(data["bought"].get(str(msg.templateId), 0))
        if m is None or m.state != MARRIED or not price or bought >= most or data["happy"] < price:
            s.log.info("9611 compra recusada", modelo=msg.templateId, pontos=data["happy"])
        else:
            mate = await _row(s.ctx, m.mate_id)
            data["happy"] -= price
            data["bought"][str(msg.templateId)] = bought + 1
            rows = [m, *([mate] if mate is not None else [])]
            for r in rows:
                r.couple = json.dumps(data)
            await s.ctx.characters.save(*rows)
            await _announce(s.ctx, *rows)
    out = pb.AltarShopListMsg(op=msg.op, altarScore=int(data["happy"]))
    for tid, (price, most) in shop.items():
        left = most - int(data["bought"].get(str(tid), 0))
        out.info.add(templateId=tid, price=price, leftCount=left, maxCount=most, skillTempId=0)
    s.send(S_MATE_SHOP, out)


# ---- pendências em server_states ----------------------------------------------------------------------------------


def dump_pending() -> dict[str, Any]:
    """Pedidos, ofertas, pedidos de divórcio e jogos do coração para ``server_states`` (``game/server_state.py``)."""
    hearts = {id(h): h for h in _hearts.values()}.values()
    return {
        "proposals": {str(t): {str(p): [x, w.isoformat()] for p, (x, w) in d.items()} for t, d in _proposals.items()},
        "offers": {str(k): list(v) for k, v in _offers.items()},
        "divorce": {str(k): v for k, v in _divorce_asks.items()},
        "heart_asks": {str(k): v for k, v in _heart_asks.items()},
        "hearts": [{"a": h.a, "b": h.b, "questions": h.questions, "seconds": h.seconds, "order": h.order,
                    "asked_at": h.asked_at.isoformat() if h.asked_at else None,
                    "answers": {str(k): v for k, v in h.answers.items()}, "done": h.done} for h in hearts],
    }  # fmt: skip


def load_pending(data: dict[str, Any]) -> None:
    """Devolve o que ``dump_pending`` gravou (arranque)."""
    for t, d in data.get("proposals", {}).items():
        _proposals[int(t)] = {int(p): (x, datetime.fromisoformat(w)) for p, (x, w) in d.items()}
    _offers.update({int(k): (v[0], v[1], v[2]) for k, v in data.get("offers", {}).items()})
    _divorce_asks.update({int(k): v for k, v in data.get("divorce", {}).items()})
    _heart_asks.update({int(k): v for k, v in data.get("heart_asks", {}).items()})
    for raw in data.get("hearts", []):
        at = raw["asked_at"]
        h = Heart(raw["a"], raw["b"], raw["questions"], raw["seconds"], raw["order"],
                  datetime.fromisoformat(at) if at else None, {int(k): v for k, v in raw["answers"].items()},
                  raw["done"])  # fmt: skip
        _hearts[h.a] = _hearts[h.b] = h


async def save_pending(ctx: GameContext) -> None:
    from .. import server_state  # server_state é importado pela sessão, que este módulo importa

    await server_state.save(ctx, server_state.MARRIAGE)
