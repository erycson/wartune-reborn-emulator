"""Minigames e atividades do operador que o servidor ainda não joga, mais o fundo novato (8751).

Os sistemas fechados respondem o estado que o cliente mostra sem eles (ícone escondido, tela vazia,
botão desabilitado): nenhum fica sem resposta, e nenhum manda aberto o que não consegue servir.
Fundo novato é real: custo em diamante via ``ledger``, prêmio pela tabela de ``data/events.json``.
Fontes e dependências de cada opcode em docs/eventos.md (tabela "Minigames").
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import events as ev
from .. import rewards
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import gemmaze
from .player import alert, granted

S_QUESTIONNAIRE, S_REBATE, S_FUND_NORMAL, S_FUND_NOVICE = 4428, 4461, 4612, 4640
S_LOTTERY, S_PRIVILEGE, S_CHARGE, S_CONSUM = 4637, 4543, 4745, 345
S_BUGLE_REQ, S_BUGLE_REWARD, S_NEW_YEAR, S_SLOT = 4553, 4554, 4811, 4901
S_QUIZ, S_RECOVER, S_SEEK, S_FISH_POOL, S_FISH_INFOS = 4908, 4912, 4914, 4916, 4918
S_GOLDEN_CLOSE, S_GOLDEN, S_LEAD, S_ICON = 300, 4933, 4936, 4980
S_LUCKY_TEMP, S_LUCKY_INFO, S_CHAIRS_OPEN, S_CHAIRS = 363, 364, 414, 415
S_ORE, S_TOP_TOOL, S_BOTTLE_DROP, S_BOTTLE_RESULT = 190, 4590, 295, 4526

FUND = "fund:novice"  # value = nível comprado (0 = nenhum), text = data da compra
FUND_GET = "fund:novice:get:{}"  # uma marca por vez (times) já resgatada
BUY, HARVEST = 1, 2  # DepositActiveMsg.opType do cliente (FundBuyItem, FundRewardItem)
DIAMOND, GIFT = -400, -500  # TemplateId das moedas (diamante e diamante vinculado)
RECOVER_LIST = 0  # RecoverReqMsg.type 0 = pedir a lista (9503)


def _send(s: GameSession, code: int, msg: Any) -> None:
    s.send(code, b.complete(msg))


# ---------------------------------------------------------------- fundo novato (8751 / 4640)


def _level_cfg(cfg: Mapping[str, Any], level: int) -> Mapping[str, Any] | None:
    return next((lv for lv in cfg["levels"] if int(lv["level"]) == level), None)


def _level(snap: PlayerSnapshot) -> int:
    st = ev.peek(snap, FUND)
    return st.value if st is not None else 0


def _fund_msg(s: GameSession, snap: PlayerSnapshot) -> pb.DepositActiveMsg:
    """DepositActiveMsg do fundo novato (4640). Níveis e tiers vêm de ``events.json``; o total do
    cliente (``itemInfos``) é a soma dos tiers (conferido na captura: nível 1 = -500:100, -400:200)."""
    cfg = s.ctx.events.novice_fund
    level = _level(snap)
    msg = pb.DepositActiveMsg(
        activeId=str(cfg["activeId"]), activeType=1, grades=int(cfg["minGrades"]), depositLevel=level
    )
    st = ev.peek(snap, FUND)
    if level and st is not None:
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
        mark = ev.peek(snap, FUND_GET.format(times))
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


def _send_fund(s: GameSession, snap: PlayerSnapshot) -> None:
    _send(s, S_FUND_NOVICE, _fund_msg(s, snap))


@router.on(8751)
async def novice_fund(s: GameSession, msg: pb.DepositActiveMsg) -> None:
    """Fundo novato: opType 0 = estado; 1 = compra o nível ``opParam`` (uma vez, só diamante, nível
    mínimo); 2 = resgata o tier ``opParam`` (= ``times``) quando o nível do personagem chega ao tier."""
    snap = s.snapshot
    assert snap is not None
    cfg = s.ctx.events.novice_fund
    if not cfg:  # operador sem fundo: mesmo estado fechado do 8703
        _send(s, S_FUND_NOVICE, pb.DepositActiveMsg(activeType=0))
        return
    if msg.opType == BUY:
        await _buy(s, snap, cfg, msg.opParam)
    elif msg.opType == HARVEST:
        await _harvest(s, snap, cfg, msg.opParam)
    else:
        _send_fund(s, snap)


async def _buy(s: GameSession, snap: PlayerSnapshot, cfg: Mapping[str, Any], level: int) -> None:
    lv = _level_cfg(cfg, level)
    # FundBuyItem: o botão some com depositLevel > 0 e a checagem do cliente é só diamante (point)
    if lv is None or _level(snap) or snap.character.grades < int(cfg["minGrades"]):
        s.log.info("8751 compra recusada", nivel=level)
        _send_fund(s, snap)
        return
    now = s.ctx.clock.now()
    spent = ledger.spend(snap.character, int(lv["costDiamond"]), "fund_novice", now, bound=False, ref=str(level))
    if spent is None:
        s.log.info("8751 sem diamante", nivel=level)
        _send_fund(s, snap)
        return
    st = ev.state(snap, FUND, now)
    st.value, st.text, st.updated_at = level, b.fmt_time(now), now
    await s.ctx.characters.save(snap.character, st, spent)
    granted(s, [], [], "", chat=False)
    _send_fund(s, snap)


async def _harvest(s: GameSession, snap: PlayerSnapshot, cfg: Mapping[str, Any], times: int) -> None:
    level = _level(snap)
    lv = _level_cfg(cfg, level) if level else None
    tiers = lv["tiers"] if lv else []
    tier = next((t for t in tiers if int(t[1]) == times), None)
    key = FUND_GET.format(times)
    # FundRewardItem.getBtnEnable (ramo do fundo novato): o "intervalo" do tier é o nível mínimo
    if tier is None or ev.peek(snap, key) is not None or snap.character.grades < int(tier[0]):
        s.log.info("8751 resgate recusado", vez=times)
        _send_fund(s, snap)
        return
    drops = [(int(t), int(n)) for t, n in tier[2]]
    if not rewards.can_grant(snap, s.ctx.templates, drops):
        s.log.info("8751 mochila cheia", vez=times)
        _send_fund(s, snap)
        return
    now = s.ctx.clock.now()
    mark = ev.state(snap, key, now)
    mark.value, mark.updated_at = 1, now
    new, text = rewards.grant(snap, s.ctx.templates, drops)  # ``grant`` já mexe em diamante/vinculado
    # o que volta do fundo entra no livro caixa (entrada), na mesma gravação do prêmio
    diamonds = sum(n for t, n in drops if t == DIAMOND)
    gifts = sum(n for t, n in drops if t == GIFT)
    refund = ledger.record_cash(snap.character, diamonds, gifts, "fund_novice", f"harvest:{times}", now)
    await s.ctx.characters.save(*rewards.owners(snap), mark, refund, *new)
    alert(s, text)
    granted(s, drops, new, text)
    _send_fund(s, snap)


@router.on(8703)
async def normal_fund(s: GameSession, _: object) -> None:
    """Fundo normal (4612): sem atividade no servidor, ``activeType`` 0 (o cliente não mostra botão)."""
    _send(s, S_FUND_NORMAL, pb.DepositActiveMsg(activeType=0))


def login_push(s: GameSession) -> None:
    """Login do oficial: o 4922 do labirinto (replay) e o 4640 do fundo novato (login.json #94)."""
    gemmaze.login_push(s)
    snap = s.snapshot
    assert snap is not None
    if s.ctx.events.novice_fund:
        _send_fund(s, snap)


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


@router.on(8604)
async def bottle(s: GameSession, _: object) -> None:
    """Garrafa fechada (295 open falso, 4526 openView falso). O ciclo (armazenamento, caixas por
    pontuação e andar, martelo) não tem dado no servidor; ver docs/eventos.md."""
    _send(s, S_BOTTLE_DROP, pb.BottleDropListMsg(open=False))
    _send(s, S_BOTTLE_RESULT, pb.BottleScoreMsg(openView=False))


@router.on(9645)
async def ore_or_super_signin(s: GameSession, _: object) -> None:
    """Minério (190) e super assinatura (4590) fechados. O código não diz qual dos dois é (o extend1
    do cabeçalho não chega ao handler), e os dois fechados é o estado certo para ambos."""
    _send(s, S_ORE, pb.SimplePropertyMsg(param7=False))
    _send(s, S_TOP_TOOL, pb.SimplePropertyMsg(param1=2059, param7=False))
