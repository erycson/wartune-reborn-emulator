"""Casamento: pedido, noivado, escolha do casamento (MarrySpecTempInfo), divórcio e buscas.

``MarrySender`` e ``MarryManager`` (cliente) definem os ``opType`` e as respostas; as telas estão no cliente inglês
(``m9/scripts/marry``, ``2/scripts/marry/view``, ``m3/.../MarryUIMediator``, ``m7/scripts/farm/marrytree``).
Fluxo do cliente (MarryRingView, ``helpContent02``): pedido com o Engagement Ring 208033 em time de 2, noivado de
20 dias, cerimônia reservada na Andrew (15049 -> 4658 -> op 5), sala de casamento e troca de alianças.
O casal tem duas linhas em ``marriages``; quem está online tem a sua no snapshot.

ponytail: pedidos, ofertas de casamento e pedidos de divórcio ficam em memória (somem se o
servidor reiniciar); a sala da cerimônia (8760, 4662/4673/4674/4672) não existe e é pulada:
quem aceita a oferta já sai casado.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any

from ...domain.models import BagType, Character, Item, Marriage, MarriageState, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import castle as cs
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
    106 expulsar, 110/111 convidar; MarryWeddingDialogFrame): a sala não existe."""
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
    granted(s, drops, new, text)
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


@router.on(8774)
async def marriage_task(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Missões do casal (op 2001 pegar, 2004 usar o mapa da missão, 2005 falar com a NPC): sem missões de casal,
    4675 vazio (o cliente só oferece casado: SpaceDialogFrame ``isMarry``)."""
    snap = s.snapshot
    if msg.opType == TASK_ACCEPT and snap is not None and snap.marriage is not None and snap.marriage.state == MARRIED:
        s.send(S_TASKS, pb.RewardUpdatedRspMsg())
    s.log.info("missão de casamento sem suporte", op=msg.opType)


@router.on(8802)
async def marriage_heart(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Jogo do coração (3001 começar, 3002 aceitar, 3003 responder, 3004 tempo esgotado, 3005 desistir; perguntas
    em ``HeartTempInfos``, respostas 4690/4691): ainda não implementado."""
    s.log.info("jogo do coração sem suporte", op=msg.opType)


@router.on(9611)
async def mate_skill_shop(s: GameSession, msg: pb.AltarShopListMsg) -> None:
    """Loja do altar da Guerra de Vênus (ConfigInfo ``Mate_Shop``: modelo,preço,máximo,tipo).

    Sem a Guerra de Vênus não há pontos de altar: lista com ``altarScore`` 0 e compra recusada.
    """
    row = next(s.ctx.templates.find("ConfigInfos", ConfigName="Mate_Shop"), None)
    out = pb.AltarShopListMsg(op=msg.op, altarScore=0)
    for part in row["ConfigValue"].split("|") if row else []:
        template_id, price, max_count, _ = (int(x) for x in part.split(","))
        out.info.add(templateId=template_id, price=price, leftCount=max_count, maxCount=max_count, skillTempId=0)
    s.send(S_MATE_SHOP, out)
