"""Casamento: pedido, noivado, escolha do casamento (MarrySpecTempInfo), divórcio e buscas.

``MarrySender`` e ``MarryManager`` (cliente) definem os ``opType`` e as respostas; o módulo de
UI do casamento não está no cliente decompilado, então os detalhes de tela são dedução (docs/social.md).
O casal tem duas linhas em ``marriages``; quem está online tem a sua no snapshot.

ponytail: pedidos, ofertas de casamento e pedidos de divórcio ficam em memória (somem se o
servidor reiniciar); a cerimônia (sala, carro, juramento) depende da cena de campanha e é pulada:
quem aceita a oferta já sai casado.
"""

from __future__ import annotations

from datetime import datetime

from ...domain.models import Character, Marriage, MarriageState
from ...protocol.messages import wartune_pb2 as pb
from .. import social
from ..builders import login as b
from ..mail import send_system_mail
from ..router import router
from ..session import GameContext, GameSession
from .login import player_info

S_PROPOSALS, S_QUALITY, S_LOVER, S_ROOMS, S_TASKS = 4656, 4658, 4659, 4662, 4675
S_DEAL_DIVORCE, S_MATES, S_MATE_SHOP, S_PLAYER = 358, 359, 365, 3
PROPOSE, ANSWER, QUALITY_ANSWER, DIVORCE, PROPOSE_INFO, ROOM_LIST = 1, 3, 5, 8, 9, 10
CANCEL, FREE_DIVORCE, CONSULT, AGREE, FIND_MATES = 14, 15, 16, 17, 20
POINT = 1  # payType 1 = diamante (DivorceAlert confere ``point`` antes de mandar payType 1)
FREE_DIVORCE_DAYS = 5  # DivorceAlert: cônjuge offline há 5 dias ou mais
MIN_GRADE = 36  # TopToolsBar mostra o casamento a partir do nível 36
MATES_MAX = 10
TASK_ACCEPT = 2001
SINGLE = (MarriageState.ENGAGE_CANCELLED, MarriageState.DIVORCED)

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


def _single(m: Marriage | None) -> bool:
    return m is None or m.state in SINGLE


async def _set(ctx: GameContext, cid: int, mate: int, state: int, now: datetime, spec: int = 0) -> Marriage:
    """Atualiza (ou cria) a linha de ``cid`` e a coloca no snapshot dele se estiver online."""
    m = await _row(ctx, cid)
    if m is None:
        m = Marriage(cid, mate, state, now)
    if m.mate_id != mate or state == MarriageState.ENGAGED:
        m.mate_id, m.since, m.married_at, m.spec_id = mate, now, None, 0
    m.state = state
    if state == MarriageState.MARRIED:
        m.spec_id, m.married_at = spec, now
    session = ctx.online.get(cid)
    if session is not None and session.snapshot is not None:
        object.__setattr__(session.snapshot, "marriage", m)  # snapshot é frozen
    return m


async def _announce(ctx: GameContext, *rows: Marriage) -> None:
    for m in rows:
        if (session := ctx.online.get(m.character_id)) is not None:
            session.send(social.S_MARRIAGE, await social.marriage_msg(ctx, m))


def _charge(c: Character, cost: int, pay_type: int) -> bool:
    field = "point" if pay_type == POINT else "gift_token"
    if cost < 0 or getattr(c, field) < cost:
        return False
    setattr(c, field, getattr(c, field) - cost)
    return True


async def _couple(s: GameSession, state: int, spec: int = 0, paid: Character | None = None) -> None:
    """Muda as duas linhas do casal (e grava quem pagou) numa transação e avisa os dois."""
    snap = s.snapshot
    assert snap is not None and snap.marriage is not None
    now, mate = s.ctx.clock.now(), snap.marriage.mate_id
    rows = [
        await _set(s.ctx, s.player_id, mate, state, now, spec),
        await _set(s.ctx, mate, s.player_id, state, now, spec),
    ]
    await s.ctx.characters.save(*rows, *([paid] if paid else []))
    await _announce(s.ctx, *rows)
    if paid is not None and (payer := s.ctx.online.get(paid.id or 0)) and payer.snapshot:
        payer.send(S_PLAYER, b.complete(player_info(payer, payer.snapshot)))


def _mate_player(c: Character) -> pb.FriendPlayer:
    return b.complete(pb.FriendPlayer(playerId=c.id, nickName=c.nickname or "", level=c.grades, sex=c.sex, job=c.job))


@router.on(8759)
async def marriage_request(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    c, now, op = snap.character, s.ctx.clock.now(), msg.opType
    mine = snap.marriage
    if op == PROPOSE:
        other = s.ctx.online.get(msg.property1)  # o pedido é feito em time de 2: o alvo está online
        target = other.snapshot.character if other is not None and other.snapshot else None
        ok = target is not None and target.id != c.id and target.sex != c.sex and _single(mine)
        ok = ok and c.grades >= MIN_GRADE and target is not None and target.grades >= MIN_GRADE
        if not ok or other is None or other.snapshot is None or not _single(other.snapshot.marriage):
            s.log.info("pedido de casamento recusado", alvo=msg.property1)
            return
        text = msg.property3[:60]
        _proposals.setdefault(msg.property1, {})[s.player_id] = (text, now)
        pro = pb.MarriageProMsg(userIdA=c.id, nickNameA=c.nickname or "", jobA=c.job, property4=b.fmt_time(now))
        pro.property5 = text
        other.send(S_PROPOSALS, pb.EngageMsg(engageInfos=[b.complete(pro)]))
    elif op == ANSWER:
        asked = _proposals.get(s.player_id, {}).pop(msg.property1, None)
        proposer = s.ctx.online.get(msg.property1)
        if asked is None or not msg.property5 or not _single(mine):
            return
        if proposer is None or proposer.snapshot is None or not _single(proposer.snapshot.marriage):
            return
        _proposals.pop(s.player_id, None)
        rows = [
            await _set(s.ctx, s.player_id, msg.property1, MarriageState.ENGAGED, now),
            await _set(s.ctx, msg.property1, s.player_id, MarriageState.ENGAGED, now),
        ]
        await s.ctx.characters.save(*rows)
        await _announce(s.ctx, *rows)
    elif op == QUALITY_ANSWER:
        await _quality_answer(s, msg.property5)
    elif op == DIVORCE and mine is not None and mine.state == MarriageState.MARRIED:
        if _charge(c, _config(s.ctx, "divorce_need", 3999), msg.payType):
            await _couple(s, MarriageState.DIVORCED, paid=c)
    elif op == CANCEL and mine is not None and mine.state == MarriageState.ENGAGED:
        # o próprio cliente manda (14, 1) quando o prazo do noivado acaba
        if _charge(c, _config(s.ctx, "cancel_engage_need", 500), msg.payType):
            await _couple(s, MarriageState.ENGAGE_CANCELLED, paid=c)
    elif op == FREE_DIVORCE and mine is not None and mine.state == MarriageState.MARRIED:
        mate = (await social.characters(s.ctx, [mine.mate_id])).get(mine.mate_id)
        away = mate is not None and s.ctx.online.get(mine.mate_id) is None and mate.last_login_at is not None
        if away and mate is not None and mate.last_login_at and (now - mate.last_login_at).days >= FREE_DIVORCE_DAYS:
            await _couple(s, MarriageState.DIVORCED)
    elif op == CONSULT and mine is not None and mine.state == MarriageState.MARRIED:
        if (mate_session := s.ctx.online.get(mine.mate_id)) is not None:
            _divorce_asks[mine.mate_id] = s.player_id
            mate_session.send(S_DEAL_DIVORCE)
    elif op == AGREE and mine is not None and mine.state == MarriageState.MARRIED:
        asked_by = _divorce_asks.pop(s.player_id, None)
        cost = _config(s.ctx, "marriage_deal_divorce_point", 1799)
        if asked_by == mine.mate_id and msg.property5 and _charge(c, cost, POINT):
            await _couple(s, MarriageState.DIVORCED, paid=c)
    elif op == PROPOSE_INFO:
        other_c = (await social.characters(s.ctx, [msg.property1])).get(msg.property1)
        if other_c is not None:
            lover = pb.MarriageProMsg(userIdA=other_c.id, nickNameA=other_c.nickname or "", property6=other_c.job)
            lover.property1 = _single(await _row(s.ctx, msg.property1))
            s.send(S_LOVER, b.complete(lover))
    elif op == ROOM_LIST:
        s.send(S_ROOMS, pb.EngageMsg())  # sem salas: a cerimônia depende da cena de campanha
    elif op == FIND_MATES:
        out = pb.RecommendListMsg()
        for other in s.ctx.online.sessions():
            o = other.snapshot
            if o is None or o.character.sex == c.sex or o.character.grades < MIN_GRADE or not _single(o.marriage):
                continue
            if len(out.girlList) + len(out.boyList) < MATES_MAX:
                (out.boyList if o.character.sex else out.girlList).append(_mate_player(o.character))
        s.send(S_MATES, out)
    else:
        # 6 sala, 7 carro, 12 anel, 13 entrar na sala, 18 ajudar a árvore: cena/árvore/anel ainda não existem
        s.log.info("operação de casamento sem suporte", op=op)


@router.on(15049)
async def buy_spec(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Escolhe o casamento (MarrySpecTempInfo ``property1``); o cônjuge confirma (4658 -> op 5).

    Preço ``Points`` com ``Discount``% nas primeiras ``DiscountTime`` horas do noivado.
    """
    snap = s.snapshot
    assert snap is not None
    m, spec = snap.marriage, s.ctx.templates.get("MarrySpecTempInfos", msg.property1)
    mate = s.ctx.online.get(m.mate_id) if m is not None else None
    if m is None or m.state != MarriageState.ENGAGED or spec is None or mate is None:
        s.log.info("15049 recusado", spec=msg.property1)
        return
    if _price(s, m, spec) > (snap.character.point if msg.payType == POINT else snap.character.gift_token):
        return
    _offers[m.mate_id] = (s.player_id, msg.property1, msg.payType)
    offer = pb.MarriageProMsg(userIdA=s.player_id, nickNameA=snap.character.nickname or "")
    offer.property2, offer.property3 = msg.property1, msg.payType
    mate.send(S_QUALITY, b.complete(offer))


def _price(s: GameSession, m: Marriage, spec: dict[str, str] | object) -> int:
    row = spec if isinstance(spec, dict) else dict(spec)  # type: ignore[call-overload]
    price = int(row["Points"])
    if (s.ctx.clock.now() - m.since).total_seconds() < int(row["DiscountTime"]) * 3600:
        price = price * int(row["Discount"]) // 100
    return price


async def _quality_answer(s: GameSession, accept: bool) -> None:
    snap = s.snapshot
    assert snap is not None
    offer = _offers.pop(s.player_id, None)
    m = snap.marriage
    if offer is None or not accept or m is None or m.state != MarriageState.ENGAGED or offer[0] != m.mate_id:
        return
    payer_id, spec_id, pay_type = offer
    payer = s.ctx.online.get(payer_id)
    spec = s.ctx.templates.get("MarrySpecTempInfos", spec_id)
    if payer is None or payer.snapshot is None or spec is None:
        return
    if not _charge(payer.snapshot.character, _price(s, m, spec), pay_type):
        return
    await _couple(s, MarriageState.MARRIED, spec_id, paid=payer.snapshot.character)
    goods = [(int(t), int(n)) for t, n in (part.split(",") for part in spec["Rewards"].split("|") if part)]
    for cid in (s.player_id, payer_id):  # presentes do casamento pelo correio (até 5 por correio)
        for i in range(0, len(goods), 5):
            await send_system_mail(s.ctx, cid, spec["TemplateName"], spec["TemplateName"], goods[i : i + 5])


@router.on(8760)
async def wedding_campaign(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Sala da cerimônia (presentes, senha, convidados, diálogos): depende da cena de campanha."""
    s.log.info("cerimônia de casamento sem suporte", op=msg.opType)


@router.on(8773)
async def marriage_tree(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Árvore do casal (``mar_tree_*``): depende do sistema de árvore/fazenda e de timers."""
    s.log.info("árvore do casamento sem suporte", op=msg.opType)


@router.on(8774)
async def marriage_task(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Missões do casal (op 2001 pegar, 2004 usar item, 2005): sem missões de casal, 4675 vazio."""
    snap = s.snapshot
    if msg.opType == TASK_ACCEPT and snap is not None and snap.marriage is not None:
        s.send(S_TASKS, pb.RewardUpdatedRspMsg())
    s.log.info("missão de casamento sem suporte", op=msg.opType)


@router.on(8802)
async def marriage_heart(s: GameSession, msg: pb.MarriageOpMsg) -> None:
    """Jogo do coração (3001 começar, 3002 aceitar, 3003 responder): perguntas não estão nos templates."""
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
