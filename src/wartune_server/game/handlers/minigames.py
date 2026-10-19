"""Minigames e atividades do operador que o servidor ainda não joga, mais o fundo novato (8751).

Os sistemas fechados respondem o estado que o cliente mostra sem eles (ícone escondido, tela vazia,
botão desabilitado): nenhum fica sem resposta, e nenhum manda aberto o que não consegue servir.
Fundo novato é real: custo em diamante via ``ledger``, prêmio pela tabela do banco (``game_settings``).
Fontes e dependências de cada opcode em docs/eventos.md (tabela "Minigames").
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ...domain import gameday
from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import events as ev
from .. import rewards
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import gemmaze, gold_tree
from .player import alert, granted

S_QUESTIONNAIRE, S_REBATE, S_FUND_NORMAL, S_FUND_NOVICE = 4428, 4461, 4612, 4640
S_LOTTERY, S_PRIVILEGE, S_CHARGE, S_CONSUM = 4637, 4543, 4745, 345
S_BUGLE_REQ, S_BUGLE_REWARD, S_NEW_YEAR, S_SLOT = 4553, 4554, 4811, 4901
S_QUIZ, S_RECOVER, S_SEEK, S_FISH_POOL, S_FISH_INFOS = 4908, 4912, 4914, 4916, 4918
S_GOLDEN_CLOSE, S_GOLDEN, S_LEAD, S_ICON = 300, 4933, 4936, 4980
S_LUCKY_TEMP, S_LUCKY_INFO, S_CHAIRS_OPEN, S_CHAIRS = 363, 364, 414, 415
S_ORE, S_TOP_TOOL = 190, 4590

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
    """Fundo do banco (``game_settings``: ``novice_fund`` da 0033, tutorial_en #639; ``normal_fund`` da 0041, #86)."""
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
    """Login do oficial: o 4922 do labirinto (replay), o 4640 do fundo novato (login.json #94), este só a partir
    do nível ``openGrades`` (tutorial_en: o login no nível 1 não manda; o primeiro 4640, #639, sai no nível 6), o 4612
    do fundo normal (tutorial_en #86, já no nível 1) e a árvore dourada (4497 e 295, #71-#72)."""
    gemmaze.login_push(s)
    snap = s.snapshot
    assert snap is not None
    cfg = _fund_cfg(s)
    if cfg and snap.character.grades >= int(cfg.get("openGrades", 0)):
        _send_fund(s, snap)
    if _fund_cfg(s, NORMAL):
        _send_fund(s, snap, NORMAL)
    gold_tree.login_push(s)


# ---------------------------------------------------------------- recuperar EXP (9503)


@router.on(9503)
async def recover(s: GameSession, msg: pb.RecoverReqMsg) -> None:
    """Lista de recuperação (4912) sempre vazia: o servidor não conta as atividades perdidas de ontem
    (campanha, arena, boss, imposto...). Com a lista vazia o cliente não mostra o aviso de EXP.

    Custos da lista conferidos na captura (login.json #54) como fórmula, para quando a contagem existir:
    ``itemCost = num*ItemCount``, ``goldCost = num*Gold``, ``goldReward = itemReward*GoldPercent/ItemPercent``
    (linhas de RecoverInfos). Pedido de resgate (type != 0) é recusado: não há EXP para recuperar."""
    if msg.type != RECOVER_LIST:
        s.log.info("9503 recusado: sem atividade perdida", tipo=msg.type)
    _send(s, S_RECOVER, pb.RecoverInfosMsg())


# ---------------------------------------------------------------- fechados sem tabela no servidor


@router.on(8534)
async def questionnaire(s: GameSession, _: object) -> None:
    """Questionário (4428 id 0): nenhum questionário no servidor. Igual ao 4428 vazio do login."""
    s.send(S_QUESTIONNAIRE, pb.QuestionnarieInfoMsg())


@router.on(8574)
async def rebate(s: GameSession, _: object) -> None:
    """Reembolso (4461 com ``id`` vazio = esconde). A única captura (2026-05-18..20) já terminou."""
    _send(s, S_REBATE, pb.RebateInfoMsg())


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
async def new_year_box(s: GameSession, _: object) -> None:
    """Caixa de ano novo: lista de nós coletados vazia (4811). Sem nós de campanha para ela."""
    _send(s, S_NEW_YEAR, pb.QueryCollectCampaignNodeRspMsg())


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


@router.on(9507)
async def fishing(s: GameSession, _: object) -> None:
    """Pesca fechada: piscina vazia (4916) e sem peixes (4918). Os pesos de spawn não estão em lugar nenhum."""
    _send(s, S_FISH_POOL, pb.FishPoolMsg())
    _send(s, S_FISH_INFOS, pb.FishInfosMsg())


@router.on(9520)
async def golden_road(s: GameSession, _: object) -> None:
    """Estrada dourada fechada: 300 fecha o quadro (só o GoldRoadManager escuta o 300)."""
    s.send(S_GOLDEN_CLOSE)


@router.on(9523)
async def group_draw(s: GameSession, _: object) -> None:
    """Sorteio de grupo sem extrações (4936 leadExtractTimes 0)."""
    _send(s, S_LEAD, pb.LeadRewardMsg())


@router.on(9550)
async def icon_numbers(s: GameSession, _: object) -> None:
    """Números dos ícones: lista vazia (4980). Nenhum chamador no cliente depende de valor."""
    _send(s, S_ICON, pb.IconNumMsgList())


@router.on(9610)
async def lucky_exchange(s: GameSession, _: object) -> None:
    """Troca da sorte sem tabela vigente: a da captura (login.json #96) terminou em 2026-05-17.
    364 vem antes do 363 (o cliente busca o valor da sorte pelo id)."""
    _send(s, S_LUCKY_INFO, pb.LuckExchangeInfoListMsg())
    _send(s, S_LUCKY_TEMP, pb.LuckExchangeTempListMsg())


@router.on(9638)
async def chairs(s: GameSession, _: object) -> None:
    """Cadeiras fechadas: 414 falso esconde o ícone; 415 vazio (obrigatório se a tela abrir)."""
    _send(s, S_CHAIRS_OPEN, pb.SimplePropertyMsg(param7=False))
    _send(s, S_CHAIRS, pb.ChairsListMsg())


@router.on(9645)
async def ore_or_super_signin(s: GameSession, _: object) -> None:
    """Minério (190) e super assinatura (4590) fechados. O código não diz qual dos dois é (o extend1
    do cabeçalho não chega ao handler), e os dois fechados é o estado certo para ambos."""
    _send(s, S_ORE, pb.SimplePropertyMsg(param7=False))
    _send(s, S_TOP_TOOL, pb.SimplePropertyMsg(param1=2059, param7=False))
