"""Minigames e atividades do operador que o servidor ainda não joga, mais o fundo novato (8751).

Os sistemas fechados respondem o estado que o cliente mostra sem eles (ícone escondido, tela vazia,
botão desabilitado): nenhum fica sem resposta, e nenhum manda aberto o que não consegue servir.
Fundo novato é real: custo em diamante via ``ledger``, prêmio pela tabela do banco (``game_settings``).
Fontes e dependências de cada opcode em docs/eventos.md (tabela "Minigames").
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from ...domain import gameday
from ...domain.models import EventState, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import bag, rewards, rules
from .. import events as ev
from .. import recover as rec
from ..builders import login as b
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from . import gemmaze, gold_tree
from .player import S_CHAT, S_ITEMS, _player, alert, granted

S_QUESTIONNAIRE, S_REBATE, S_FUND_NORMAL, S_FUND_NOVICE = 4428, 4461, 4612, 4640
S_REBATE_USER = 4463
S_LOTTERY, S_PRIVILEGE, S_CHARGE, S_CONSUM = 4637, 4543, 4745, 345
S_BUGLE_REQ, S_BUGLE_REWARD, S_SLOT = 4553, 4554, 4901
S_QUIZ, S_RECOVER, S_SEEK = 4908, 4912, 4914  # a pesca (9507) está em handlers/fishing.py
S_GOLDEN_CLOSE, S_GOLDEN, S_LEAD, S_ICON = 300, 4933, 4936, 4980
# (visto) 1026-225632-1 #2454: 36 casas (itemID, count); -1 = casa vazia
GOLDEN_BOARD = (
    (3020010, 10),
    (2120043, 6),
    (21260907, 1),
    (-1, 0),
    (21260907, 1),
    (-1, 0),
    (3020010, 2),
    (208023, 5),
    (208014, 2),
    (21260907, 5),
    (3020010, 3),
    (2031003, 1),
    (21260907, 1),
    (208017, 5),
    (3040001, 3),
    (21260907, 2),
    (2131057, 2),
    (2060014, 2),
    (2131057, 4),
    (-1, 0),
    (-1, 0),
    (2120043, 6),
    (21260907, 1),
    (-1, 0),
    (208014, 10),
    (21260907, 3),
    (208017, 2),
    (21260907, 1),
    (2131057, 3),
    (-1, 0),
    (21260907, 2),
    (2031003, 1),
    (2030102, 1),
    (2030202, 1),
    (-1, 0),
    (2030202, 1),
)
S_LUCKY_TEMP, S_LUCKY_INFO, S_CHAIRS_OPEN, S_CHAIRS = 363, 364, 414, 415
S_ORE, S_TOP_TOOL, S_SIGNIN, S_SIGNIN_TEMP = 190, 4590, 513, 514
SUPER_SIGNIN = 2059  # 4590 param1 da super assinatura (SuperSigninCardManager)
ORE_OP, SIGNIN_OP = 35, 38  # extend1 do 9645: StokesOreManager e SuperSigninCardManager (PackageOut(9645, 0, n))

FUND = "fund:novice"  # value = nível comprado (0 = nenhum), text = data da compra
FUND_GET = "fund:novice:get:{}"  # uma marca por vez (times) já resgatada
BUY, HARVEST = 1, 2  # DepositActiveMsg.opType do cliente (FundBuyItem, FundRewardItem)
DIAMOND, GIFT = -400, -500  # TemplateId das moedas (diamante e diamante vinculado)
RECOVER_LIST = 0  # RecoverReqMsg.type 0 = pedir a lista (9503)


def _send(s: GameSession, code: int, msg: Any) -> None:
    s.send(code, b.complete(msg))


# ---------------------------------------------------------------- fundos: novato (8751 / 4640) e normal (8703 / 4612)


@dataclass(frozen=True, slots=True)
class Fund:
    """Os dois fundos do ``FundManager`` usam a mesma mensagem e as mesmas operações; muda a regra do tier
    (*(cliente)* ``FundRewardItem``: no novato o ``interval`` é o nível; no normal, minutos depois do
    ``getStartDate``) e a janela (o normal tem datas de compra e de resgate; o novato não tem)."""

    reply: int  # 4640 / 4612
    setting: str  # chave em ``game_settings``
    novice: bool


NOVICE = Fund(S_FUND_NOVICE, "novice_fund", True)
NORMAL = Fund(S_FUND_NORMAL, "normal_fund", False)
CLOSED, BUYING, HARVESTING = 0, 1, 2  # DepositActiveMsg.activeType (cliente FundManager: 1 compra, 2 resgate)


def _fund_cfg(s: GameSession, fund: Fund = NOVICE) -> Mapping[str, Any]:
    """Fundo do banco (``game_settings``: ``novice_fund`` da 0033, tutorial_en #639; ``normal_fund`` da 0038, #86)."""
    return s.ctx.world.settings.get(fund.setting) or {}


def _key(fund: Fund, cfg: Mapping[str, Any]) -> str:
    """Compra do fundo. O normal é por ``activeId``: quem comprou numa edição compra de novo na seguinte."""
    return FUND if fund.novice else f"fund:normal:{cfg['activeId']}"


def _get_key(fund: Fund, cfg: Mapping[str, Any], times: int) -> str:
    return FUND_GET.format(times) if fund.novice else f"{_key(fund, cfg)}:get:{times}"


def _at(cfg: Mapping[str, Any], name: str) -> datetime:
    """Data do fundo normal (hora do jogo, como o cliente mostra e compara com o ``sysCurtime``)."""
    return datetime.strptime(str(cfg[name]), ev.TIME_FMT).replace(tzinfo=gameday.GAME_TZ)


def _phase(fund: Fund, cfg: Mapping[str, Any], now: datetime) -> int:
    """``activeType``. Novato: sempre 1 (visto #639). Normal: 1 entre ``setStartDate`` e ``setEndDate`` (visto #86,
    mandado no dia 18 com a compra até 18 23:59:59); 2 dali até ``getEndDate`` (*dedução*: o cliente só resgata com
    2, ``getCanGetGift``); 0 fora (o botão some, ``getShowBtn``)."""
    if fund.novice:
        return BUYING
    if _at(cfg, "setStartDate") <= now <= _at(cfg, "setEndDate"):
        return BUYING
    if _at(cfg, "setEndDate") < now <= _at(cfg, "getEndDate"):
        return HARVESTING
    return CLOSED


def _level_cfg(cfg: Mapping[str, Any], level: int) -> Mapping[str, Any] | None:
    return next((lv for lv in cfg["levels"] if int(lv["level"]) == level), None)


def _level(snap: PlayerSnapshot, fund: Fund = NOVICE, cfg: Mapping[str, Any] | None = None) -> int:
    st = ev.peek(snap, _key(fund, cfg or {}))
    return st.value if st is not None else 0


def _fund_msg(s: GameSession, snap: PlayerSnapshot, fund: Fund = NOVICE) -> pb.DepositActiveMsg:
    """DepositActiveMsg do fundo (4640/4612). Níveis e tiers vêm do banco; o total do
    cliente (``itemInfos``) é a soma dos tiers (conferido no tutorial_en #639: nível 1 = -500:250, -400:500;
    e no #86: 5 tiers de 5 x 2126025 = 25)."""
    cfg = _fund_cfg(s, fund)
    level = _level(snap, fund, cfg)
    msg = pb.DepositActiveMsg(
        activeId=str(cfg["activeId"]),
        activeType=_phase(fund, cfg, s.ctx.clock.now()),
        grades=int(cfg["minGrades"] if fund.novice else cfg.get("grades", 0)),  # #86 manda 0 no normal
        depositLevel=level,
    )
    st = ev.peek(snap, _key(fund, cfg))
    if not fund.novice:
        msg.title, msg.description = str(cfg.get("title", "")), str(cfg.get("description", ""))
        for name in ("setStartDate", "setEndDate", "getStartDate", "getEndDate"):
            setattr(msg, name, str(cfg[name]))
        if level and st is not None:
            msg.depositTime = st.text
    elif level and st is not None:
        msg.depositTime = st.text
        msg.getStartDate = st.text
        msg.getEndDate = str(cfg["endDate"])  # ponytail: janela de resgate desconhecida (2099 = sem fim)
    for lv in cfg["levels"]:
        p = msg.activeParams.add(
            level=int(lv["level"]), costDiamond=int(lv["costDiamond"]), harvestCount=len(lv["tiers"])
        )
        totals: dict[int, int] = {}
        for _interval, times, items in lv["tiers"]:
            g = p.getInfos.add(interval=int(_interval), times=int(times))
            for t, n in items:
                g.itemInfo.add(templateId=int(t), count=int(n))
                totals[int(t)] = totals.get(int(t), 0) + int(n)
        for t, n in totals.items():
            p.itemInfos.add(templateId=t, count=n)
    lv = _level_cfg(cfg, level) if level else None
    for _interval, times, items in lv["tiers"] if lv else []:
        mark = ev.peek(snap, _get_key(fund, cfg, int(times)))
        if mark is None:
            continue
        msg.logs.add(type=int(times), time=int(mark.updated_at.timestamp() * 1000))
        for t, n in items:
            _add_harvested(msg, int(t), int(n))
    return msg


def _add_harvested(msg: pb.DepositActiveMsg, template_id: int, count: int) -> None:
    """``harvestedInfos``: o que já saiu do fundo, somado por item."""
    for item in msg.harvestedInfos:
        if item.templateId == template_id:
            item.count += count
            return
    msg.harvestedInfos.add(templateId=template_id, count=count)


def _send_fund(s: GameSession, snap: PlayerSnapshot, fund: Fund = NOVICE) -> None:
    _send(s, fund.reply, _fund_msg(s, snap, fund))


async def _fund_op(s: GameSession, msg: pb.DepositActiveMsg, fund: Fund) -> None:
    """opType 0 = estado; 1 = compra o nível ``opParam`` (uma vez, só diamante, nível mínimo); 2 = resgata o tier
    ``opParam`` (= ``times``)."""
    snap = s.snapshot
    assert snap is not None
    cfg = _fund_cfg(s, fund)
    if not cfg:  # operador sem fundo: estado fechado (o cliente esconde o botão)
        _send(s, fund.reply, pb.DepositActiveMsg(activeType=CLOSED))
        return
    if msg.opType == BUY:
        await _buy(s, snap, fund, cfg, msg.opParam)
    elif msg.opType == HARVEST:
        await _harvest(s, snap, fund, cfg, msg.opParam)
    else:
        _send_fund(s, snap, fund)


@router.on(8751)
async def novice_fund(s: GameSession, msg: pb.DepositActiveMsg) -> None:
    """Fundo novato: o tier libera quando o nível do personagem chega ao ``interval``."""
    await _fund_op(s, msg, NOVICE)


@router.on(8703)
async def normal_fund(s: GameSession, msg: pb.DepositActiveMsg) -> None:
    """Fundo normal ("Diamond Vein" no #86): compra só na janela de compra; o tier libera ``interval`` minutos
    depois do ``getStartDate`` e até o ``getEndDate``."""
    await _fund_op(s, msg, NORMAL)


def _reason(fund: Fund) -> str:
    return "fund_novice" if fund.novice else "fund_normal"


async def _buy(s: GameSession, snap: PlayerSnapshot, fund: Fund, cfg: Mapping[str, Any], level: int) -> None:
    lv = _level_cfg(cfg, level)
    now = s.ctx.clock.now()
    # FundBuyItem: o botão some com depositLevel > 0 e a checagem do cliente é só diamante (point). Nível 11:
    # FundManager.getShowBtn (normal) e FundBuyItem (novato). Janela do normal: (dedução) o cliente não confere.
    if (
        lv is None
        or _level(snap, fund, cfg)
        or snap.character.grades < int(cfg["minGrades"])
        or _phase(fund, cfg, now) != BUYING
    ):
        s.log.info("fundo: compra recusada", fundo=fund.setting, nivel=level)
        _send_fund(s, snap, fund)
        return
    spent = ledger.spend(snap.character, int(lv["costDiamond"]), _reason(fund), now, bound=False, ref=str(level))
    if spent is None:
        s.log.info("fundo: sem diamante", fundo=fund.setting, nivel=level)
        _send_fund(s, snap, fund)
        return
    st = ev.state(snap, _key(fund, cfg), now)
    st.value, st.text, st.updated_at = level, b.fmt_time(now), now
    await s.ctx.characters.save(snap.character, st, spent)
    granted(s, [], [], "", chat=False)
    _send_fund(s, snap, fund)


def _tier_open(s: GameSession, snap: PlayerSnapshot, fund: Fund, cfg: Mapping[str, Any], interval: int) -> bool:
    """*(cliente)* ``FundRewardItem.getBtnEnable``: novato = nível >= ``interval``; normal = ``sysCurtime`` >=
    ``getStartDate`` + ``interval`` minutos (e, aqui, ainda na janela de resgate)."""
    if fund.novice:
        return snap.character.grades >= interval
    now = s.ctx.clock.now()
    return _phase(fund, cfg, now) == HARVESTING and now >= _at(cfg, "getStartDate") + timedelta(minutes=interval)


async def _harvest(s: GameSession, snap: PlayerSnapshot, fund: Fund, cfg: Mapping[str, Any], times: int) -> None:
    level = _level(snap, fund, cfg)
    lv = _level_cfg(cfg, level) if level else None
    tiers = lv["tiers"] if lv else []
    tier = next((t for t in tiers if int(t[1]) == times), None)
    key = _get_key(fund, cfg, times)
    if tier is None or ev.peek(snap, key) is not None or not _tier_open(s, snap, fund, cfg, int(tier[0])):
        s.log.info("fundo: resgate recusado", fundo=fund.setting, vez=times)
        _send_fund(s, snap, fund)
        return
    drops = [(int(t), int(n)) for t, n in tier[2]]
    if not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        s.log.info("fundo: mochila cheia", fundo=fund.setting, vez=times)
        _send_fund(s, snap, fund)
        return
    now = s.ctx.clock.now()
    mark = ev.state(snap, key, now)
    mark.value, mark.updated_at = 1, now
    new, text = rewards.grant(snap, s.ctx.templates, drops)  # ``grant`` já mexe em diamante/vinculado
    # o que volta do fundo entra no livro caixa (entrada), na mesma gravação do prêmio
    diamonds = sum(n for t, n in drops if t == DIAMOND)
    gifts = sum(n for t, n in drops if t == GIFT)
    refund = ledger.record_cash(snap.character, diamonds, gifts, _reason(fund), f"harvest:{times}", now)
    await s.ctx.characters.save(*rewards.owners(snap), mark, refund, *new)
    alert(s, text)
    granted(s, drops, new, text)
    _send_fund(s, snap, fund)


def login_push(s: GameSession) -> None:
    """Login do oficial: o 4922 do labirinto de gemas só com tabuleiro gravado (só turco: replay #10, #12; o
    tutorial_en, conta nova, não manda), o 4640 do fundo novato só a partir do nível ``openGrades`` (tutorial_en:
    o login no nível 1 não manda; o primeiro 4640, #639, sai no nível 6), o 4612
    do fundo normal (tutorial_en #86, já no nível 1), a árvore dourada (4497 e 295, #71-#72), a troca da sorte (363
    #88 e 364 #102, sem pedido; vazios: o servidor não tem as edições) e minério, super assinatura e cadeiras fechados
    (190, 4590, 414: #109, #110, #112)."""
    gemmaze.login_push(s)
    send_rebate(s)
    snap = s.snapshot
    assert snap is not None
    cfg = _fund_cfg(s)
    if cfg and snap.character.grades >= int(cfg.get("openGrades", 0)):
        _send_fund(s, snap)
    if _fund_cfg(s, NORMAL):
        _send_fund(s, snap, NORMAL)
    gold_tree.login_push(s)
    _send(s, S_LUCKY_TEMP, pb.LuckExchangeTempListMsg())
    _send(s, S_LUCKY_INFO, pb.LuckExchangeInfoListMsg())
    _send(s, S_ORE, pb.SimplePropertyMsg(param7=False))
    signin_login(s)
    _send(s, S_CHAIRS_OPEN, pb.SimplePropertyMsg(param7=False))


def fund_opened(s: GameSession, before: int) -> None:
    """Subiu do nível ``before`` até o ``openGrades`` ou além: 4640 logo depois do 150 (tutorial_en #639)."""
    snap = s.snapshot
    assert snap is not None
    cfg = _fund_cfg(s)
    if cfg and before < int(cfg.get("openGrades", 0)) <= snap.character.grades:
        _send_fund(s, snap)


# ---------------------------------------------------------------- super assinatura (9645 extend1 38 / 513 / 514 / 4590)
# Regras do cliente inglês (language.txt ``SuperSigninCardFrame.*`` e ``supersignincard...helpFrame.content``): o cartão
# custa ``cardPrice`` Balens; o dia 1 sai na compra e cada dia seguinte abre à meia-noite; quem estava no jogo naquele
# dia assina ("Login to collect"); o dia perdido assina por ``reSigninPrice`` Balens; o cartão vale até 8 dias.
# Estados do 513 (``SuperSigninCardItem.refreshView``): 0 ainda não, 1 pode receber, 2 recebido (sem botão), 3 perdido.

SIGNIN_BUY, SIGNIN_RECEIVE, SIGNIN_RESIGN = 2, 3, 4  # SuperSigninCardManager (1 = OPEN_FRAME, nunca mandado)
NOT_YET, READY, TAKEN, MISSED = 0, 1, 2, 3
TAKEN_SHIFT = 8  # EventState.value: bit k = dia k assinado; bit k + 8 = dia k recebido


def _signin_cfg(s: GameSession) -> Mapping[str, Any]:
    """``game_settings.super_signin`` (0054, oficial_encantar #118-#119)."""
    return s.ctx.world.settings.get("super_signin") or {}


def _signin_key(cfg: Mapping[str, Any]) -> str:
    return f"signin:super:{cfg['openTime']}"  # um cartão por edição


def _signin_day(now: datetime) -> date:
    return gameday.local(now).date()  # o dia do cartão vira à meia-noite (helpFrame), não às 5h


def _signin_current(card: EventState, now: datetime) -> int:
    """Dia do cartão hoje: 1 no dia da compra."""
    return (_signin_day(now) - date.fromisoformat(card.text)).days + 1


def _signin_window(cfg: Mapping[str, Any], now: datetime) -> bool:
    return _at(cfg, "openTime") <= now < _at(cfg, "stopTime")


def _signin_state(card: EventState, cfg: Mapping[str, Any], day: int, now: datetime) -> int:
    if card.value & 1 << (day + TAKEN_SHIFT):
        return TAKEN
    if card.value & 1 << day:
        return READY
    return MISSED if day < min(_signin_current(card, now), int(cfg["cardDays"]) + 1) else NOT_YET


def _signin_msg(s: GameSession, card: EventState | None) -> pb.SuperSigninCardRespMsg:
    """513: os 7 dias com cartão; vazio sem cartão (``SuperSigninCardFrame``: o botão de compra só vale vazio)."""
    cfg, now = _signin_cfg(s), s.ctx.clock.now()
    msg = pb.SuperSigninCardRespMsg()
    if card is not None:
        for day, _ in cfg["temp"]:
            msg.details.add(date=int(day), state=_signin_state(card, cfg, int(day), now))
    return msg


def _sign_today(cfg: Mapping[str, Any], card: EventState, now: datetime) -> bool:
    """Marca o dia de hoje como assinado (quem está no jogo assina). True se mudou."""
    day = _signin_current(card, now)
    if not 1 <= day <= len(cfg["temp"]) or card.value & 1 << day:
        return False
    card.value |= 1 << day
    card.updated_at = now
    return True


def _send_signin(s: GameSession, card: EventState | None) -> None:
    msg = _signin_msg(s, card)
    s.signin_sent = msg.SerializeToString()
    _send(s, S_SIGNIN, msg)


def signin_login(s: GameSession) -> None:
    """Login: 4590 e 514 como o oficial (#118-#119, mesmo sem cartão); com cartão, também o 513. O 4590 abre o ícone
    durante a edição e, depois dela, enquanto o cartão comprado vale. A assinatura do dia é gravada no primeiro
    ``refresh_signin`` (o login não espera o banco aqui)."""
    snap = s.snapshot
    assert snap is not None
    cfg, now = _signin_cfg(s), s.ctx.clock.now()
    if not cfg:
        _send(s, S_TOP_TOOL, pb.SimplePropertyMsg(param1=SUPER_SIGNIN, param7=False))
        return
    card = ev.peek(snap, _signin_key(cfg))
    active = card is not None and _signin_current(card, now) <= int(cfg["cardDays"])
    top = pb.SimplePropertyMsg(param1=SUPER_SIGNIN, param4=str(cfg["openTime"]), param5=str(cfg["stopTime"]))
    top.param7 = _signin_window(cfg, now) or active
    _send(s, S_TOP_TOOL, top)
    temp = pb.SuperSigninRewardMsg(cardPrice=int(cfg["cardPrice"]), reSigninPrice=int(cfg["reSigninPrice"]))
    for day, items in cfg["temp"]:
        temp.temp.add(date=int(day), itemMsg=str(items))
    _send(s, S_SIGNIN_TEMP, temp)
    if card is not None:
        _sign_today(cfg, card, now)
        _send_signin(s, card)
        s.signin_sent = None  # o refresh grava a assinatura de hoje


async def refresh_signin(s: GameSession) -> None:
    """Depois de cada pedido (``GameSession.on_packet``; o cliente manda 5015 a cada poucos segundos): na virada da
    meia-noite o dia novo fica assinado para quem está no jogo, e o 513 vai de novo se mudou."""
    snap = s.snapshot
    cfg = _signin_cfg(s)
    if snap is None or not cfg or s.battle is not None:
        return
    card = ev.peek(snap, _signin_key(cfg))
    if card is None:
        return
    signed = _sign_today(cfg, card, s.ctx.clock.now())
    if signed or _signin_msg(s, card).SerializeToString() != s.signin_sent:
        await s.ctx.characters.save(card)
        _send_signin(s, card)


def _signin_items(cfg: Mapping[str, Any], day: int) -> list[tuple[int, int]]:
    """``itemMsg`` do 514: ``"id,n|id,n"``."""
    text = next(str(items) for d, items in cfg["temp"] if int(d) == day)
    return [(int(t), int(n)) for t, n in (part.split(",") for part in text.split("|") if part)]


async def _signin_buy(s: GameSession, snap: PlayerSnapshot, cfg: Mapping[str, Any], card: EventState | None) -> None:
    """Compra: só sem cartão nesta edição, dentro da edição, nível ``minGrades``
    (``TopToolsBar.showSuperSigninCardBtn``). O cliente confere ``point`` (Balens livres): o vinculado não paga."""
    now = s.ctx.clock.now()
    if card is not None or not cfg or not _signin_window(cfg, now) or snap.character.grades < int(cfg["minGrades"]):
        s.log.info("super assinatura: compra recusada")
        _send_signin(s, card)
        return
    spent = ledger.spend(snap.character, int(cfg["cardPrice"]), "super_signin", now, bound=False, ref="card")
    if spent is None:
        s.log.info("super assinatura: sem Balens")
        _send_signin(s, card)
        return
    card = ev.state(snap, _signin_key(cfg), now)
    card.text = _signin_day(now).isoformat()
    _sign_today(cfg, card, now)
    await s.ctx.characters.save(snap.character, card, spent)
    granted(s, [], [], "", chat=False)
    _send_signin(s, card)


async def signin_op(s: GameSession, msg: pb.SuperSigninCardReqMsg) -> None:
    """9645 com ``extend1`` 38: comprar (2), receber o dia (3) ou assinar o dia perdido (4). Recusa: o 513 igual."""
    snap = s.snapshot
    assert snap is not None
    cfg, now = _signin_cfg(s), s.ctx.clock.now()
    card = ev.peek(snap, _signin_key(cfg)) if cfg else None
    if msg.opType == SIGNIN_BUY:
        await _signin_buy(s, snap, cfg, card)
        return
    days = {int(d) for d, _ in cfg.get("temp", [])}
    state = _signin_state(card, cfg, msg.date, now) if card is not None and msg.date in days else None
    if card is not None and msg.opType == SIGNIN_RESIGN and state == MISSED:
        price = int(cfg["reSigninPrice"])
        spent = ledger.spend(snap.character, price, "super_signin", now, bound=False, ref=str(msg.date))
        if spent is None:
            s.log.info("super assinatura: sem Balens para assinar", dia=msg.date)
        else:
            card.value |= 1 << msg.date
            card.updated_at = now
            await s.ctx.characters.save(snap.character, card, spent)
            granted(s, [], [], "", chat=False)
    elif card is not None and msg.opType == SIGNIN_RECEIVE and state == READY:
        drops = _signin_items(cfg, msg.date)
        if not rewards.can_grant(snap, s.ctx.templates, drops, now):
            s.log.info("super assinatura: mochila cheia", dia=msg.date)
        else:
            card.value |= 1 << (msg.date + TAKEN_SHIFT)
            card.updated_at = now
            new, text = rewards.grant(snap, s.ctx.templates, drops)
            await s.ctx.characters.save(*rewards.owners(snap), card, *new)
            alert(s, text)
            granted(s, drops, new, text)
    else:
        s.log.info("super assinatura: pedido recusado", op=msg.opType, dia=msg.date, estado=state)
    _send_signin(s, card)


# ---------------------------------------------------------------- recuperar EXP (9503)


@router.on(9503)
async def recover(s: GameSession, msg: pb.RecoverReqMsg) -> None:
    """Lista (type 0) ou resgate do ``sonType`` ``type`` (lista e fórmulas em ``game/recover``).

    ExpBackSignelFrame: ``count`` 1 = uma unidade, 2 = tudo; ``way`` 2 = ouro (ganha ``goldReward``), 1 = item
    2131020 (ganha ``itemReward``), 3 = item com diamante cobrindo o que falta (RECOVER_POINT por item, vinculado
    primeiro). (visto) d27 #749-#754, ouro: 109, 3, 111 "80,160 EXP gained through Recovery.", 83, 4912 sem a
    linha; #18452-#18479, way 3 no coliseu: 3, 115, 111 "Gained Insigniax150", 4912."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    if msg.type != RECOVER_LIST:
        await _recover_one(s, snap, msg, now)
    _send(s, S_RECOVER, rec.infos_msg(snap, s.ctx.templates, now))
    if msg.type == RECOVER_LIST:  # (visto) 191924-1 #9044, 1026 #2207 e 1027 #745: 4912 e depois 109 (só a lista)
        castle_yield(s)


async def _recover_one(s: GameSession, snap: PlayerSnapshot, msg: pb.RecoverReqMsg, now: datetime) -> None:
    templates, c = s.ctx.templates, snap.character
    left = rec.pending(snap, now)
    num = left.get(msg.type, 0)
    units = 1 if msg.count == 1 else num
    row = rec.info(snap, templates, msg.type, units) if num and msg.count in (1, 2) else None
    if row is None or msg.way not in (1, 2, 3):
        s.log.info("9503 recusado", tipo=msg.type, way=msg.way)
        return
    gold = msg.way == 2
    cost, reward = (row.goldCost, row.goldReward) if gold else (row.itemCost, row.itemReward)
    have = sum(i.count for i in bag.in_bag(snap) if i.template_id == rec.ITEM)
    short = 0 if gold else max(0, cost - have)
    price = short * int(rules.config(templates, "RECOVER_POINT", "10"))
    kind = rec.base(msg.type, snap, templates)[0]  # type: ignore[index]
    drops = rec.drops(msg.type, kind, reward)
    if (
        reward <= 0
        or (gold and c.gold < cost)
        or (short and msg.way != 3)
        or c.point + c.gift_token < price
        or not rewards.can_grant(snap, templates, drops, now)
    ):
        s.log.info("9503 recusado: sem saldo", tipo=msg.type, way=msg.way)
        return
    spent = ledger.pay(c, price, bind=True, reason="recover", ref=str(msg.type), now=now) if price else None
    changed, gone = ([], []) if gold else bag.take(snap, rec.ITEM, cost - short)
    c.gold -= cost if gold else 0
    left[msg.type] = num - units
    st = ev.daily(snap, rec.KEY, now)
    st.text, st.updated_at = json.dumps({str(k): v for k, v in left.items() if v > 0}), now
    new, _ = rewards.grant(snap, templates, drops)
    c.weary += reward if kind == rec.STAMINA else 0  # como a poção: pode passar do teto
    changed = [i for i in changed if i not in new]
    extra = [spent] if spent is not None else []
    await s.ctx.characters.save(*rewards.owners(snap), st, *changed, *new, *extra, delete=tuple(gone))
    if gold:
        castle_yield(s)
    _player(s)
    if changed or gone:
        s.send(S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    if kind == rewards.EXP:
        alert(s, f"{reward:,} EXP gained through Recovery.")
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=rules.exp_text(reward)))
    else:  # TODO(inventado): o texto de estamina/ouro/Daru segue o da insígnia (só ela tem captura)
        names = [(templates.get("ItemTempInfos", t) or {}).get("TemplateName", "") for t, _ in drops] or ["Stamina"]
        alert(s, ", ".join(f"Gained {n}x{reward}" for n in names))


# ---------------------------------------------------------------- fechados sem tabela no servidor


@router.on(8534)
async def questionnaire(s: GameSession, _: object) -> None:
    """Questionário (4428 id 0): nenhum questionário no servidor. Igual ao 4428 vazio do login."""
    s.send(S_QUESTIONNAIRE, pb.QuestionnarieInfoMsg())


REBATE_INFO, REBATE_GET = 1, 2  # RebateOpMsg.op: FeedBackManager (depois do 4461) e FeedBackItem (resgatar)


def _rebate_cfg(s: GameSession) -> Mapping[str, Any]:
    """``game_settings.rebate`` (0055): o Recharge Gift Pack do oficial_encantar #61."""
    return s.ctx.world.settings.get("rebate") or {}


def _rebate_open(cfg: Mapping[str, Any], now: datetime) -> bool:
    return bool(cfg) and _at(cfg, "beginDate") <= now <= _at(cfg, "endDate")


def send_rebate(s: GameSession) -> None:
    """4461 no login (oficial_encantar #61): a edição na janela; fora dela o ``id`` vazio esconde o botão
    (``FeedBackManager.__rebateActiveHandler``; tutorial_en #59). Com ``id`` o cliente pede o progresso (8574 op 1)."""
    cfg = _rebate_cfg(s)
    if not _rebate_open(cfg, s.ctx.clock.now()):
        _send(s, S_REBATE, pb.RebateInfoMsg())
        return
    msg = pb.RebateInfoMsg(id=cfg["id"], beginDate=cfg["beginDate"], endDate=cfg["endDate"], type=int(cfg["type"]))
    for pk in cfg["packages"]:
        p = msg.packages.add(packageId=pk["packageId"], order=int(pk["order"]), point=int(pk["point"]))
        p.price = int(pk["price"])
        for n in range(1, 9):  # o oficial manda os 8 pares, zerados os que sobram
            tid, count = pk["items"][n - 1] if n <= len(pk["items"]) else (0, 0)
            setattr(p, f"itemid{n}", int(tid))
            setattr(p, f"count{n}", int(count))
    _send(s, S_REBATE, msg)


async def _rebate_user(s: GameSession, cfg: Mapping[str, Any], taken: int) -> pb.UserRebateMsg:
    """4463 (#76): ``point`` = Balens recarregados na janela; ``isget`` por pacote."""
    since, until = _at(cfg, "beginDate"), _at(cfg, "endDate")
    point = await s.ctx.characters.read(lambda uow: uow.characters.recharged(s.player_id, since, until))
    msg = pb.UserRebateMsg(id=cfg["id"], userid=s.player_id, point=point, type=int(cfg["type"]))
    for i, pk in enumerate(cfg["packages"]):
        msg.packagestates.add(id=pk["packageId"], isget=bool(taken & 1 << i))
    return msg


@router.on(8574)
async def rebate(s: GameSession, msg: pb.RebateOpMsg) -> None:
    """Recharge Gift Pack: ``op`` 1 pede o progresso; 2 resgata o ``packageid`` quando a recarga da janela chega ao
    ``point`` dele (``FeedBackManager.__rebateDataHandler``: brilha com ``userPoint >= point`` e não resgatado).
    Fora da edição: 4461 vazio, como o tutorial_en #59."""
    snap = s.snapshot
    assert snap is not None
    cfg, now = _rebate_cfg(s), s.ctx.clock.now()
    if not _rebate_open(cfg, now) or msg.id != cfg["id"]:
        _send(s, S_REBATE, pb.RebateInfoMsg())
        return
    st = ev.state(snap, f"rebate:{cfg['id']}", now)  # bit i = pacote i do ``packages`` resgatado
    info = await _rebate_user(s, cfg, st.value)
    if msg.op == REBATE_GET:
        i = next((i for i, pk in enumerate(cfg["packages"]) if pk["packageId"] == msg.packageid), None)
        drops = [(int(t), int(n)) for t, n in cfg["packages"][i]["items"]] if i is not None else []
        if i is None or st.value & 1 << i or info.point < int(cfg["packages"][i]["point"]):
            s.log.info("rebate: resgate recusado", pacote=msg.packageid, recarga=info.point)
        elif not rewards.can_grant(snap, s.ctx.templates, drops, now):
            s.log.info("rebate: mochila cheia", pacote=msg.packageid)
        else:
            st.value, st.updated_at = st.value | 1 << i, now
            new, text = rewards.grant(snap, s.ctx.templates, drops)
            await s.ctx.characters.save(*rewards.owners(snap), st, *new)
            alert(s, text)
            granted(s, drops, new, text)
            info.packagestates[i].isget = True
    elif msg.op != REBATE_INFO:
        s.log.info("rebate: op desconhecida", op=msg.op)
    _send(s, S_REBATE_USER, info)


@router.on(8629, 8630, 8634, 8638, 8748, 9521, 9522)
async def no_reply(s: GameSession, _: object) -> None:
    """Pedidos que o cliente só manda com a tela aberta, que aqui nunca abre: sem resposta.
    História (8629/8630; nunca 4546), volta do jogador (8634; nunca 4550), pegar corneta (8638),
    giro da loteria (8748) e dados da estrada dourada (9521/9522). O labirinto de gemas (9508..9517) é
    ``handlers/gemmaze.py``."""
    s.log.debug("minigame fechado: pedido sem resposta")


@router.on(8639, 8640)
async def bugle(s: GameSession, msg: object) -> None:
    """Corneta do passe sem item (4553/4554 vazios). 8639 traz o índice da carta (VipRouletteMsg) e
    recebe o 4554; 8640 não traz corpo e recebe o 4553."""
    code = S_BUGLE_REWARD if isinstance(msg, pb.VipRouletteMsg) else S_BUGLE_REQ
    _send(s, code, pb.VipRouletteMsg())


@router.on(8722, 8723)
async def privilege_360(s: GameSession, _: object) -> None:
    """Privilégio 360 (4543 vazio). O botão só aparece com ``isIn360Agent`` (plataforma 360): não há
    como ligar aqui, então a lista de resgatados fica vazia."""
    _send(s, S_PRIVILEGE, pb.PrivilegeMsg())


@router.on(8750)
async def lottery(s: GameSession, _: object) -> None:
    """Loteria fechada (4637 isOpen falso). Sem tabela de prêmios nem janela no servidor."""
    _send(s, S_LOTTERY, pb.LotteryMsg(isOpen=False))


@router.on(8866)
async def recharge_rank(s: GameSession, _: object) -> None:
    """Ranking de recarga zerado (4745). A atividade não existe no servidor."""
    _send(s, S_CHARGE, pb.ChargeRewardMsg())


@router.on(9602)
async def cross_cost(s: GameSession, _: object) -> None:
    """Gasto entre servidores zerado (345). Sem atividade no servidor."""
    _send(s, S_CONSUM, pb.ChargeRewardMsg())


@router.on(8994)
async def new_year_box(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Caixa de ano novo fora do evento: (visto) oficial_20261023-215937-1 #751, #973, #1189, #1300 (``param1`` 3,
    ao entrar e sair do castelo) sem resposta nenhuma; o 4811 (nós coletados) fica para quando houver o evento."""
    s.log.info("8994 sem evento de ano novo", param1=msg.param1)


@router.on(9500)
async def slot(s: GameSession, _: object) -> None:
    """Caça-níquel fechado (4901 open falso): o ícone some e o evento não dispara."""
    _send(s, S_SLOT, pb.SlotActiveMsg(open=False, op=0))


@router.on(9501)
async def quiz(s: GameSession, _: object) -> None:
    """Quiz fechado (4908 sysState 0). A banca de perguntas (HeartTempInfos) não traz a resposta certa."""
    _send(s, S_QUIZ, pb.SysAnswerQuestionStateMsg(sysState=0))


@router.on(9502)
async def treasure_hunt(s: GameSession, _: object) -> None:
    """Caça ao tesouro fechada (4914 op 1, sem nós, seekCount 0). ``seekNodeList`` precisa existir:
    o cliente lê ``.seekNode`` quando ``op == 1``."""
    msg = pb.PlayerSeekInfoMsg(op=1, seekCount=0, state=0)
    msg.seekNodeList.SetInParent()
    _send(s, S_SEEK, msg)


@router.on(9520)
async def golden_road(s: GameSession, _: object) -> None:
    """Tabuleiro da estrada dourada (4933, GoldRoadManager.getOrRefreshGoldInfo -> __goldRoadInfoHandler).
    (visto) 1026-225632-1 #2453 e 1027-152321-1 #1353: 4933 e nada do 300 (o 300 só fecha o quadro se estiver
    aberto, GoldRoadManager.__closeGoldRoadFrameHanlder). O tabuleiro é o mesmo nas duas capturas (#2454, #1354).
    TODO(inventado): fixo porque não há outra captura para mostrar como o tabuleiro muda."""
    msg = pb.GoldenRoadMsg(playerStatue=0, score=0)
    for item_id, count in GOLDEN_BOARD:
        msg.cellInfo.add(itemID=item_id, count=count)
    _send(s, S_GOLDEN, msg)


@router.on(9523)
async def group_draw(s: GameSession, _: object) -> None:
    """Sorteio de grupo sem extrações (4936 leadExtractTimes 0)."""
    _send(s, S_LEAD, pb.LeadRewardMsg())


@router.on(9550)
async def icon_numbers(s: GameSession, _: object) -> None:
    """Números dos ícones: lista vazia (4980). Nenhum chamador no cliente depende de valor."""
    _send(s, S_ICON, pb.IconNumMsgList())


@router.on(9610)
async def lucky_exchange(s: GameSession, msg: pb.LuckExchangeOpMsg) -> None:
    """Troca da sorte (``LuckyExchangeManager.OperateLuckyExchange``: ``exchangeId`` x ``exchangeCount``). Sem edição
    vigente: no tutorial_en (#88, #102) "Little Windmill" terminou em 2026-10-14 e "Nostalgic Times Exchange" só começa
    em 2026-10-23, e o servidor não tem tabela das edições (o login manda as listas vazias): recusa sempre.
    ``(visto) oficial_20261027-152321-1 #11765-#11767``: a recusa do oficial é "Insufficient exchange items." e um 4247
    zerado. (dedução) o servidor não sabe o que a troca pede, então toda recusa diz isso."""
    from .events import send_empty_rate  # noqa: PLC0415  (events importa este módulo)

    s.log.info("9610 recusado: sem troca da sorte", troca=msg.exchangeId, vezes=msg.exchangeCount)
    alert(s, "Insufficient exchange items.")
    send_empty_rate(s)


@router.on(9638)
async def chairs(s: GameSession, _: object) -> None:
    """Cadeiras fechadas: 414 falso esconde o ícone; 415 vazio (obrigatório se a tela abrir)."""
    _send(s, S_CHAIRS_OPEN, pb.SimplePropertyMsg(param7=False))
    _send(s, S_CHAIRS, pb.ChairsListMsg())


@router.on(9645)
async def ore_or_super_signin(s: GameSession, _: object) -> None:
    """O mesmo código para o minério (``extend1`` 35, fechado: 190 falso) e a super assinatura (38). O corpo é relido
    do pacote: o registro decodifica como ``OreActiveClientOpMsg``, cujo campo 2 é bool (o ``date`` viraria 1)."""
    if s.packet.extend1 == SIGNIN_OP:
        await signin_op(s, pb.SuperSigninCardReqMsg.FromString(s.packet.body))
        return
    if s.packet.extend1 != ORE_OP:
        s.log.info("9645 com extend1 desconhecido", extend1=s.packet.extend1)
    _send(s, S_ORE, pb.SimplePropertyMsg(param7=False))
