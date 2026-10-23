"""VIP (8505/8513/8519/8521/8756), contrato do rei (8540), alquimia (8320/8321), refino de alma
(8466/8467) e loja do teste (8582). Regras e fontes em docs/eventos.md.
"""

from __future__ import annotations

import json
import random
from collections.abc import Collection, Mapping, Sequence
from datetime import datetime, timedelta

from ...domain.models import Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import bag, rewards, rules
from .. import events as ev
from .. import guild as gd
from ..builders import login as b
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import S_CHAT, S_ITEMS, _player, alert, granted

S_VIP, S_ROULETTE, S_VIP_TIPS, S_KING = 4410, 4414, 4416, 4434
S_LUCKY, S_SOUL, S_TRIAL = 4224, 4372, 4468
VIP_DAYS = {31: "One_MonthPoint", 93: "Three_MonthPoint", 186: "Six_MonthPoint"}  # OpenVipItem: index*31
VIP_GRADE = 4  # UpGradeTempInfos.Types da VIP (Data = vipGp acumulado)
ALCHEMY_RIGHT, SOUL_RIGHT = 8, 9  # VipPrerogativeTempInfos.type: usos extras por dia
VIP_COOL = 16  # VIPModel.VIP_COOL: type do "Speed up cool down timer for free"
VIP_MYSTERY = 14  # type "Add Mystery Shop Attempts": compras a mais por dia, +10 no VIP 4 até +60 no 9
VIP_EXP = 6  # type "Bonus EXP": "Bonus 50% Dungeon EXP" no VIP 1 até 150% no 9 (language VipPrivilegeFrame)
VIP_FRIEND, VIP_FRIEND_BONUS = 6, 50  # VIPModel.VIP_FRIEND (procurado em para2) e o 50 fixo de vipFriendPrivilege
ALCHEMY_COUNT = 20  # remainCount 20 sem VIP (só turco: login.json #9; o tutorial_en não manda o 4224)
ALCHEMY_GRADE = 14  # MainToolBar: o cliente pede o 8320 de novo ao chegar no nível 14
MAX_COST = 200  # AlchemyFrame/SoulMakeFrame: o 1º uso do dia é grátis, depois 40 + 10 x usos, no máximo 200
KING_BUFF, KING_BUFF_FROM = rules.BOOST_CONTRACT, 6  # o 6 dá o buff 7 (30 min) 1x por dia (KingContractFrame)
KING_ALL = (1, 2, 3, 4, 5, 6)  # "comprar todos" = All_KingContract
S_VIP_FIRST, S_WHEEL_RESULT = 4539, 4415
S_GUILD_VIP = 4455  # VipToConsortiaMsg (U_C_CONSORTIA_VIP)
GIFT_NEXT, VIP_TYPE, WHEEL = "vipgift:next", "vip:type", "vipwheel"  # event_states
TRIAL_TYPE = 2  # vipType depois do cartão de teste 2031201 (tutorial_en #3262)
VIP_TOKEN, WHEEL_SPINS = 208015, 8  # VIP Token (SonType 292) e giros por roleta (VipBoxFrame: 8 desliga o botão)
QUICK = 1  # VipRouletteMsg.opType: 1 = girar com todas as fichas (VipBoxFrame._quickStartRolette)
_rng = random.Random()  # sorteio da roleta (os testes trocam por um com semente)


def _cfg(s: GameSession, name: str) -> int:
    return int(ev.config(s.ctx.templates, name, "0"))


def _building(s: GameSession, snap: PlayerSnapshot, son_type: int) -> Mapping[str, str]:
    """Linha ``BuildingTempInfos`` do prédio ``SonType`` do castelo (vazia se não tiver)."""
    for bld in snap.buildings:
        row = s.ctx.templates.get("BuildingTempInfos", bld.template_id)
        if row and row.get("SonType") == str(son_type):
            return row
    return {}


# ---------------------------------------------------------------- VIP


def _vip_expiry(snap: PlayerSnapshot) -> datetime | None:
    st = ev.peek(snap, "vip")
    return ev.parse_time(st.text) if st and st.text else None


def is_vip(snap: PlayerSnapshot, now: datetime) -> bool:
    end = _vip_expiry(snap)
    return end is not None and end > now


def vip_type(snap: PlayerSnapshot) -> int:
    kind = ev.peek(snap, VIP_TYPE)
    return kind.value if kind else 0


def vip_grade(s: GameSession, snap: PlayerSnapshot) -> int:
    st = ev.peek(snap, "vip")
    gp = st.value if st else 0
    grades = [
        int(r["Grades"]) for r in s.ctx.templates.find("UpGradeTempInfos", Types=VIP_GRADE) if int(r["Data"]) <= gp
    ]
    return max(grades, default=1)


def vip_right(s: GameSession, snap: PlayerSnapshot, kind: int) -> int:
    """``para1`` do privilégio ``kind`` no nível VIP atual (0 sem VIP)."""
    if not is_vip(snap, s.ctx.clock.now()):
        return 0
    row = next(s.ctx.templates.find("VipPrerogativeTempInfos", type=kind, grade=vip_grade(s, snap)), None)
    return int(row["para1"] or 0) if row else 0


def friend_bonus(s: GameSession, snap: PlayerSnapshot) -> int:
    """Amigos a mais do VIP, igual ao cliente (``VIPModel.vipFriendPrivilege``): procura pelo ``para2`` 6
    (``getTemplatesByType`` filtra ``para2``, não ``type``) no nível VIP e dá 50 fixos se ``para1`` != 0.
    Com os templates de hoje isso pega o ``type`` 20 (para1 1 em todo nível): +50 para qualquer VIP, embora o
    ``type`` 4 "Increased Friend Limit" diga +0 no VIP 1-2. O cliente é que limita a tela, então vale o dele."""
    if not is_vip(snap, s.ctx.clock.now()):
        return 0
    grade = vip_grade(s, snap)
    row = next((r for r in s.ctx.templates.rows("VipPrerogativeTempInfos") if r.get("para2") == str(VIP_FRIEND)
                and int(r.get("grade") or 0) == grade), None)  # fmt: skip
    return VIP_FRIEND_BONUS if row is not None and int(row.get("para1") or 0) != 0 else 0


def free_cool(s: GameSession, snap: PlayerSnapshot) -> bool:
    """Acelerar a fila de graça (5172 index 0): ``VIPModel.vipCoolPrivilege`` = VIP ativo e ``type`` 16 com
    ``para1`` != 0 no nível (todos os níveis têm 1 hoje)."""
    return vip_right(s, snap, VIP_COOL) != 0


def next_gift(now: datetime) -> datetime:
    """Próxima liberação do presente semanal: a segunda-feira da semana seguinte, com a semana começando no
    domingo. *(visto)* tutorial_en #3280: resgatado no domingo 2026-10-18, ``takeGiftDate`` 2026-10-26 00:00.
    *(dedução)* um ponto só; "segunda da semana de domingo seguinte" é a regra que dá 10-26 a partir de domingo."""
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = day + timedelta(days=(6 - day.weekday()) % 7 or 7)  # weekday: segunda 0 ... domingo 6
    return sunday + timedelta(days=1)


def _gift_at(snap: PlayerSnapshot) -> datetime | None:
    st = ev.peek(snap, GIFT_NEXT)
    return ev.parse_time(st.text) if st and st.text else None


def _vip_msg(s: GameSession, snap: PlayerSnapshot) -> pb.VipInfoMsg:
    """4410. Sem resgate ainda, ``takeGiftDate`` (e ``expirtDate`` sem VIP) = criação do personagem (#96, #3262);
    depois do resgate, a próxima liberação (#3280)."""
    now = s.ctx.clock.now()
    st = ev.peek(snap, "vip")
    vip = is_vip(snap, now)
    gift_at = _gift_at(snap)
    return pb.VipInfoMsg(
        isVip=vip,
        vipGp=st.value if st else 0,
        vipGrade=vip_grade(s, snap),
        expirtDate=b.fmt_time(_vip_expiry(snap) or snap.character.created_at),
        isTakeGift=vip and (gift_at is None or now >= gift_at),  # VipGiftItem: true = botão de resgatar
        vipType=vip_type(snap),  # 2 = cartão de teste (#3262); ponytail: o 1 não tem regra conhecida
        isExpirt=not vip,
        takeGiftDate=b.fmt_time(gift_at or snap.character.created_at),
    )


def send_vip(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_VIP, b.complete(_vip_msg(s, s.snapshot)))


def vip_changed(s: GameSession) -> None:
    """4410 para o jogador e o 4455 para a guilda online: o ``ConsortiaGroupChatControler`` troca o ícone VIP do
    membro no chat em grupo. ponytail: o VIP que vence sozinho não avisa a guilda (não há relógio de vencimento)."""
    send_vip(s)
    snap, mine = s.snapshot, s.ctx.guilds.of(s.player_id)
    if snap is None or mine is None:
        return
    vip = is_vip(snap, s.ctx.clock.now())
    msg = pb.VipToConsortiaMsg(userid=s.player_id, isVip=vip, vipType=vip_type(snap), consortiaId=mine[0].id)
    for other in gd.online_members(s.ctx, mine[0].id or 0):
        other.send(S_GUILD_VIP, msg)


@router.on(8513)
async def vip_open(s: GameSession, msg: pb.VipOpenInfoMsg) -> None:
    """Abre/renova o VIP por ``days`` (31/93/186) pelo preço One/Three/Six_MonthPoint (só Balens livres).
    *(cliente)* o inglês não manda o 8513: os botões do ``OpenSelfView`` vão para a página de pagamento
    (``__joinVipHandler``; o ``__openVipHandler`` não está ligado) e o ``VIPFrame`` não cria o ``OpenFriendView``.
    Fica para o GM e os testes."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    key = VIP_DAYS.get(msg.days)
    if key is None or msg.isFriend:
        # ponytail: presentear um amigo exige gravar o snapshot de outro personagem (o inglês nem tem a tela)
        s.log.info("8513 recusado", dias=msg.days, amigo=msg.isFriend)
        return
    spent = ledger.spend(snap.character, _cfg(s, key), "vip", now, bound=False, ref=str(msg.days))
    if spent is None:
        s.log.info("8513 sem diamante", dias=msg.days)
        return
    st = ev.state(snap, "vip", now)
    start = max(now, _vip_expiry(snap) or now)
    # ponytail: o oficial soma Vip_DailyAddGp a cada dia de VIP; aqui entra tudo na compra
    st.value += msg.days * _cfg(s, "Vip_DailyAddGp")
    st.text, st.updated_at = b.fmt_time(start + timedelta(days=msg.days)), now
    await s.ctx.characters.save(snap.character, st, spent)
    granted(s, [], [], "", chat=False)
    vip_changed(s)
    s.send(S_VIP_TIPS)


@router.on(8505)
async def vip_gift(s: GameSession, _: object) -> None:
    """Presente semanal do VIP: ``VipDrop.site`` = nível VIP; de novo só a partir de ``next_gift``. Repetido: sem
    resposta. Ordem do oficial (tutorial_en #3266-#3282): 115, 111, 4410, 4539 (vazio), 83."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    drops = [(int(r["itemId"]), int(r["count"])) for r in s.ctx.templates.find("VipDrop", site=vip_grade(s, snap))]
    if not _vip_msg(s, snap).isTakeGift or not drops or not rewards.can_grant(snap, s.ctx.templates, drops, now):
        s.log.info("8505 recusado")
        return
    st = ev.state(snap, GIFT_NEXT, now)
    st.text, st.updated_at = b.fmt_time(next_gift(now)), now
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)
    if new:
        from . import events  # events importa este módulo

        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
        events.items_gained(s)  # (visto) tutorial_en #3268
    if any(t < 0 for t, _ in drops):  # ponytail: a captura só tem itens; moeda vai como nas outras recompensas
        granted(s, [(t, n) for t, n in drops if t < 0], [], text, chat=False)
    alert(s, text)
    send_vip(s)
    s.send(S_VIP_FIRST)
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


async def use_trial_card(s: GameSession, item: Item, row: Mapping[str, str], n: int) -> bool:
    """Cartão VIP de teste (SonType 203, ``Property1`` 12): ``Property3`` horas de VIP por unidade, somadas ao que
    falta. Ordem do oficial (tutorial_en #3259-#3263): 115, 111, 4410 (``vipType`` 2), 3."""
    snap = s.snapshot
    assert snap is not None
    hours = int(row.get("Property3") or 0) * n
    if hours <= 0:
        return False
    now = s.ctx.clock.now()
    gone = bag.take_one(snap, item, n)  # antes de qualquer await
    st, kind = ev.state(snap, "vip", now), ev.state(snap, VIP_TYPE, now)
    end = max(now, _vip_expiry(snap) or now) + timedelta(hours=hours)
    st.text, st.updated_at = b.fmt_time(end), now
    kind.value, kind.updated_at = TRIAL_TYPE, now
    if gone:
        await s.ctx.characters.save(st, kind, delete=(item,))
    else:
        await s.ctx.characters.save(st, kind, item)
    s.send(S_ITEMS, bag.moved([] if gone else [item], s.player_id, empty=[item] if gone else []))
    alert(s, f"Your VIP service has been extended {hours} hours; new expiration date is {end:%Y-%m-%d}.")
    vip_changed(s)
    granted(s, [], [], "", chat=False)
    return True


def _wheel_taken(snap: PlayerSnapshot) -> list[int]:
    st = ev.peek(snap, WHEEL)
    return list(json.loads(st.text)) if st and st.text else []


def wheel_pick(weights: Sequence[float], taken: Collection[int], rng: random.Random) -> int | None:
    """Posição do prêmio que sai, entre as que ainda não saíram, pelo peso (``vip_wheel_prizes.weight``, 0035;
    padrão 1 = uniforme). Peso 0 nunca sai; ``None`` quando só sobram pesos 0 (o giro é recusado)."""
    left = [i for i, w in enumerate(weights) if i not in taken and w > 0]
    return rng.choices(left, [weights[i] for i in left])[0] if left else None


def _wheel_cost(s: GameSession, spins: int) -> int:
    """VIP Tokens do próximo giro (``vip_wheel_costs`` no banco: o giro k custa k, #3325/#3335)."""
    costs = s.ctx.world.settings.get("vip_wheel_costs") or [1]
    return int(costs[min(spins, len(costs) - 1)])


def _wheel_msg(s: GameSession, taken: list[int]) -> pb.VipRouletteMsg:
    """``takeItem`` = tudo o que já saiu, o último por último (VipBoxFrame.__effctComplete lê o fim)."""
    wheel = s.ctx.world.vip_wheel
    msg = pb.VipRouletteMsg(leftCount=WHEEL_SPINS - len(taken), needVipItem=_wheel_cost(s, len(taken)))
    for i in taken:
        msg.takeItem.add(tempId=wheel[i][0], count=wheel[i][1])
    return msg


@router.on(8521)
async def vip_wheel_open(s: GameSession, _: object) -> None:
    """Abre a roleta usando o VIP Token da mochila, ou "atualizar" (o mesmo pedido): tabuleiro novo com os 18
    prêmios (#3325) e o custo de volta a 1. O cliente põe máscara e só tira no 4414; com menos de 18 ``leftItem``
    ele ignora, que é a resposta de quem não é VIP.

    *(dedução)* abrir zera o tabuleiro: o cliente avisa que atualizar "reset all items on the wheel" e redesenha
    tudo no 4414. ponytail: se o oficial cobra a atualização, o preço não está na evidência."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    if not is_vip(snap, now) or len(s.ctx.world.vip_wheel) < 18:
        s.log.info("8521 recusado", vip=is_vip(snap, now))
        s.send(S_ROULETTE, pb.VipRouletteMsg())
        return
    st = ev.state(snap, WHEEL, now)
    st.text, st.updated_at = "[]", now
    await s.ctx.characters.save(st)
    msg = _wheel_msg(s, [])
    for t, n in s.ctx.world.vip_wheel:
        msg.leftItem.add(tempId=t, count=n)
    s.send(S_ROULETTE, msg)


@router.on(8519)
async def vip_wheel_spin(s: GameSession, msg: pb.VipRouletteMsg) -> None:
    """Gira: ``opType`` 0 uma vez, 1 enquanto houver fichas (#3331-#3335: 5 fichas -> 2 giros, 1 + 2). Prêmio
    sorteado entre os que faltam pelo peso do banco (``wheel_pick``; a captura não tem probabilidades). Ordem
    do oficial: 115 (fichas e prêmios), 109, 3, 4415. O texto do chat o cliente monta sozinho
    (VipBoxFrame.senChatData)."""
    snap = s.snapshot
    assert snap is not None
    now, templates, wheel = s.ctx.clock.now(), s.ctx.templates, s.ctx.world.vip_wheel
    taken = _wheel_taken(snap)
    opened: list[int] = []
    changed: list[Item] = []
    gone: list[Item] = []
    new: list[Item] = []
    st = ev.peek(snap, WHEEL)
    while st is not None and is_vip(snap, now) and len(taken) < min(WHEEL_SPINS, len(wheel)):
        cost = _wheel_cost(s, len(taken))
        index = wheel_pick(s.ctx.world.vip_wheel_weights or (1.0,) * len(wheel), taken, _rng)
        if index is None or bag.count_of(snap, VIP_TOKEN) < cost:
            break
        if not rewards.can_grant(snap, templates, [wheel[index]], s.ctx.clock.now()):
            break
        used, deleted = bag.take(snap, VIP_TOKEN, cost)
        changed += used
        gone += deleted
        new += rewards.grant(snap, templates, [wheel[index]])[0]
        taken.append(index)
        opened.append(index)
        if msg.opType != QUICK:
            break
    if not opened or st is None:
        s.log.info("8519 recusado", fichas=bag.count_of(snap, VIP_TOKEN), giros=len(taken))
        s.send(S_WHEEL_RESULT, _wheel_msg(s, taken))  # isStart falso: o cliente só reabilita os botões
        return
    st.text, st.updated_at = json.dumps(taken), now
    kept = list(dict.fromkeys(i for i in changed if i not in gone))  # a mesma pilha pode pagar dois giros
    await s.ctx.characters.save(*rewards.owners(snap), st, *kept, *new, delete=tuple(gone))
    s.send(S_ITEMS, bag.moved([*kept, *new], s.player_id, empty=gone))
    prizes = [wheel[i] for i in opened]
    if any(t in (-100, -600) for t, _ in prizes):
        castle_yield(s)
    _player(s)
    out = _wheel_msg(s, taken)
    out.openIndex.extend(opened)  # só os abertos agora: o cliente tira cada um da roda que sobra
    out.isStart, out.opType = True, msg.opType
    s.send(S_WHEEL_RESULT, out)


@router.on(8756)
async def vip_custom(s: GameSession, _: object) -> None:
    """Clique no atendimento VIP (QQ) do cliente chinês: só registro, o cliente não espera resposta."""
    s.log.info("atendimento VIP clicado")


# ---------------------------------------------------------------- contrato do rei (8540)


def send_king(s: GameSession) -> None:
    """Só os contratos já comprados: (visto) tutorial_en #10-#11, conta nova = 4434 vazio; (cliente)
    KingContractInfo.endData null = sem contrato (leftTime -1)."""
    snap = s.snapshot
    assert snap is not None
    msg = pb.KingContractMsg()
    for row in s.ctx.templates.rows("KingContracts"):
        cid = int(row["Id"])
        if (end := ev.contract_end(snap, cid)) is not None:
            msg.kingContractInfos.add(contractId=cid, endData=b.fmt_time(end))
    s.send(S_KING, msg)


@router.on(8540)
async def king_contract(s: GameSession, msg: pb.KingContractBuyMsg) -> None:
    """Compra contratos (``NeedPoint`` cada, os seis juntos por ``All_KingContract``; só diamante) ou,
    com ``__use``, ativa o buff diário (contrato 7, 30 min) de quem tem o contrato 6."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    rows = {int(r["Id"]): r for r in s.ctx.templates.rows("KingContracts")}
    if getattr(msg, "__use"):
        day = ev.daily(snap, "king:fetch", now)
        if not ev.has_contract(snap, KING_BUFF_FROM, now) or day.value or KING_BUFF not in rows:
            s.log.info("8540 buff recusado")
            return
        st = ev.state(snap, f"king:{KING_BUFF}", now)
        st.text = b.fmt_time(now + timedelta(minutes=int(rows[KING_BUFF]["Duration"])))
        st.updated_at = now
        day.value, day.updated_at = 1, now
        await s.ctx.characters.save(st, day)
        send_king(s)
        return
    ids = sorted(set(msg.ids))
    own = msg.friendId in (0, s.player_id)
    if not ids or not own or any(i not in rows or i == KING_BUFF for i in ids):
        # ponytail: presente para amigo (friendId de outro) igual ao VIP: precisa gravar outro personagem
        s.log.info("8540 recusado", ids=ids, amigo=msg.friendId)
        return
    cost = _cfg(s, "All_KingContract") if tuple(ids) == KING_ALL else sum(int(rows[i]["NeedPoint"]) for i in ids)
    spent = ledger.spend(snap.character, cost, "king_contract", now, bound=False, ref=",".join(map(str, ids)))
    if spent is None:
        s.log.info("8540 sem diamante", ids=ids)
        return
    changed = []
    for i in ids:
        st = ev.state(snap, f"king:{i}", now)
        start = max(now, ev.contract_end(snap, i) or now)  # renovar soma ao que falta
        st.text, st.updated_at = b.fmt_time(start + timedelta(minutes=int(rows[i]["Duration"]))), now
        changed.append(st)
    await s.ctx.characters.save(snap.character, spent, *changed)
    granted(s, [], [], "", chat=False)
    send_king(s)


# ---------------------------------------------------------------- alquimia (8320/8321) e alma (8466/8467)


def _cost(used: int) -> int:
    return min(40 + 10 * used, MAX_COST) if used else 0


def _alchemy_gold(s: GameSession, snap: PlayerSnapshot) -> int:
    """AlchemyFrame.refreshView: Town Hall (901) Property1 x 10 + Gold Refinery (101) Property1 x 5."""
    return int(_building(s, snap, 901).get("Property1", 0)) * 10 + int(_building(s, snap, 101).get("Property1", 0)) * 5


def _lucky_msg(s: GameSession, snap: PlayerSnapshot) -> pb.PlayerLuckyMsg:
    used = ev.daily(snap, "alchemy", s.ctx.clock.now()).value
    left = max(0, ALCHEMY_COUNT + vip_right(s, snap, ALCHEMY_RIGHT) - used)
    return pb.PlayerLuckyMsg(luckyCount=used, remainCount=left, point=_cost(used), gold=_alchemy_gold(s, snap))


@router.on(8320)
async def alchemy_info(s: GameSession, _: object) -> None:
    """4224 a partir do nível 14: o cliente pede no início e de novo ao chegar no 14 (``MainToolBar``); o oficial não
    responde ao pedido do nível 1 (tutorial_en #17)."""
    assert s.snapshot is not None
    if s.snapshot.character.grades >= ALCHEMY_GRADE:
        s.send(S_LUCKY, _lucky_msg(s, s.snapshot))


@router.on(8321)
async def alchemy(s: GameSession, _: object) -> None:
    """Troca Balens (não vinculados) por ouro: o custo é ``_cost`` (o cliente só olha ``point``)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    info = _lucky_msg(s, snap)
    spent = ledger.spend(snap.character, info.point, "alchemy", now, bound=False) if info.point else None
    if not info.remainCount or (info.point and spent is None):
        s.log.info("8321 recusado", restam=info.remainCount, custo=info.point)
        s.send(S_LUCKY, info)
        return
    st = ev.daily(snap, "alchemy", now)
    st.value, st.updated_at = st.value + 1, now
    snap.character.gold += info.gold
    counted = ev.count(snap, s.ctx.events, ev.ALCHEMY, now)  # atividade "Gold Alchemy" (tipo 21)
    await s.ctx.characters.save(snap.character, st, *([spent] if spent else []), *counted)
    granted(s, [(-100, info.gold)], [], "", chat=False)  # 3 + 109
    s.send(S_LUCKY, _lucky_msg(s, snap))  # gold = quanto cada uso rende (texto do cliente)


def _soul_amount(s: GameSession, snap: PlayerSnapshot) -> int:
    """Barracks (402) e Cottage (1201) pelo nível x RefiningSoul_ArmyHouseMut / _PeopleMut (só turco:
    login.json #10)."""
    barracks = int(_building(s, snap, 402).get("BuildingGrade", 0))
    people = int(_building(s, snap, 1201).get("BuildingGrade", 0))
    return barracks * _cfg(s, "RefiningSoul_ArmyHouseMut") + people * _cfg(s, "RefiningSoul_PeopleMut")


def _soul_msg(s: GameSession, snap: PlayerSnapshot) -> pb.PlayerRefiningSoulMsg:
    used = ev.daily(snap, "soul", s.ctx.clock.now()).value
    left = max(0, _cfg(s, "RefiningSoul_Count") + vip_right(s, snap, SOUL_RIGHT) - used)
    return pb.PlayerRefiningSoulMsg(count=used, remainCount=left, point=_cost(used), soul=_soul_amount(s, snap))


@router.on(8466)
async def soul_info(s: GameSession, _: object) -> None:
    """4372 a partir do ``RefiningSoul_Grades`` (24; o cliente pede de novo no 24, ``MainToolBar``); abaixo o oficial
    não responde (tutorial_en #18)."""
    assert s.snapshot is not None
    if s.snapshot.character.grades >= _cfg(s, "RefiningSoul_Grades"):
        s.send(S_SOUL, _soul_msg(s, s.snapshot))


@router.on(8467)
async def soul(s: GameSession, _: object) -> None:
    """Troca Balens (não vinculados) por alma (``strategy``), a partir do nível RefiningSoul_Grades; custo ``_cost``."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    info = _soul_msg(s, snap)
    ok = info.remainCount and snap.character.grades >= _cfg(s, "RefiningSoul_Grades")
    spent = ledger.spend(snap.character, info.point, "refining_soul", now, bound=False) if ok and info.point else None
    if not ok or (info.point and spent is None):
        s.log.info("8467 recusado", restam=info.remainCount, custo=info.point)
        s.send(S_SOUL, info)
        return
    st = ev.daily(snap, "soul", now)
    st.value, st.updated_at = st.value + 1, now
    snap.character.strategy += info.soul
    counted = ev.count(snap, s.ctx.events, ev.REFINE_SOUL, now)  # atividade "Daru Alchemy" (tipo 22)
    await s.ctx.characters.save(snap.character, st, *([spent] if spent else []), *counted)
    granted(s, [], [], "", chat=False)
    s.send(S_SOUL, _soul_msg(s, snap))


# ---------------------------------------------------------------- loja do teste (8582)


@router.on(8582)
async def trial_buy(s: GameSession, msg: pb.TrialInfoMsg) -> None:
    """Compra de buff (TrialSkill) dentro do mapa do teste; responde 4468 com a loja.

    ponytail: o mapa do teste (andar, buffs na batalha) não existe no servidor; sem ele não há onde
    o buff valer, então recusa sem cobrar e devolve a loja cheia."""
    s.log.info("8582 recusado: teste não implementado", skill=msg.skillId)
    shop = pb.PlayerTrialMsg(userId=s.player_id)
    for i, part in enumerate(ev.config(s.ctx.templates, "TrialSkill").split("|")):
        if part:
            skill, _cur, top, cost = (int(x) for x in part.split(","))
            shop.trialInfos.add(index=i, skillId=skill, param1=0, param2=top, param3=cost)
    s.send(S_TRIAL, shop)


def login_push(s: GameSession) -> None:
    """Estados que o oficial manda no login: 4434 (tutorial_en #58) e 4410 (#96). O 4224 e o 4372 não: o tutorial_en
    (nível 1) não manda nenhum dos dois, nem em resposta ao 8320/8466 (#17-#18)."""
    assert s.snapshot is not None
    send_king(s)
    send_vip(s)
