"""VIP (8505/8513/8519/8521/8756), contrato do rei (8540), alquimia (8320/8321), refino de alma
(8466/8467) e loja do teste (8582). Regras e fontes em docs/eventos.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta

from ...domain.models import PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import events as ev
from .. import rewards
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .player import alert, granted

S_VIP, S_ROULETTE, S_VIP_TIPS, S_KING = 4410, 4414, 4416, 4434
S_LUCKY, S_SOUL, S_TRIAL = 4224, 4372, 4468
VIP_DAYS = {31: "One_MonthPoint", 93: "Three_MonthPoint", 186: "Six_MonthPoint"}  # OpenVipItem: index*31
VIP_GRADE = 4  # UpGradeTempInfos.Types da VIP (Data = vipGp acumulado)
ALCHEMY_RIGHT, SOUL_RIGHT = 8, 9  # VipPrerogativeTempInfos.type: usos extras por dia
ALCHEMY_COUNT = 20  # login.json #9: remainCount 20 sem VIP
MAX_COST = 40  # AlchemyFrame/SoulMakeFrame: (usos+1)*2, no máximo 40
KING_BUFF, KING_BUFF_FROM = 7, 6  # contrato 6 dá o buff 7 (30 min) uma vez por dia (KingContractFrame)
KING_ALL = (1, 2, 3, 4, 5, 6)  # "comprar todos" = All_KingContract


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


def _next_monday(now: datetime) -> datetime:
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return day + timedelta(days=7 - day.weekday())


def _week(now: datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-{week}"


def _vip_msg(s: GameSession, snap: PlayerSnapshot) -> pb.VipInfoMsg:
    now = s.ctx.clock.now()
    st = ev.peek(snap, "vip")
    vip = is_vip(snap, now)
    gift = ev.peek(snap, "vipgift")
    can_take = vip and (gift is None or gift.text != _week(now))
    return pb.VipInfoMsg(
        isVip=vip,
        vipGp=st.value if st else 0,
        vipGrade=vip_grade(s, snap),
        expirtDate=b.fmt_time(_vip_expiry(snap) or snap.character.created_at),
        isTakeGift=can_take,  # VipGiftItem: true = botão de resgatar
        vipType=0,  # ponytail: o tipo 1 (ícone especial) não tem regra conhecida
        isExpirt=not vip,
        takeGiftDate=b.fmt_time(_next_monday(now)),
    )


def send_vip(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_VIP, b.complete(_vip_msg(s, s.snapshot)))


@router.on(8513)
async def vip_open(s: GameSession, msg: pb.VipOpenInfoMsg) -> None:
    """Abre/renova o VIP por ``days`` (31/93/186) pelo preço One/Three/Six_MonthPoint (só diamante)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    key = VIP_DAYS.get(msg.days)
    if key is None or msg.isFriend:
        # ponytail: presentear um amigo exige gravar o snapshot de outro personagem (talvez offline)
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
    send_vip(s)
    s.send(S_VIP_TIPS)


@router.on(8505)
async def vip_gift(s: GameSession, _: object) -> None:
    """Presente semanal do VIP: ``VipDrop.site`` = nível VIP; uma vez por semana (segunda 00:00)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    drops = [(int(r["itemId"]), int(r["count"])) for r in s.ctx.templates.find("VipDrop", site=vip_grade(s, snap))]
    if not _vip_msg(s, snap).isTakeGift or not drops or not rewards.can_grant(snap, s.ctx.templates, drops):
        s.log.info("8505 recusado")
        return
    st = ev.state(snap, "vipgift", now)
    st.text, st.updated_at = _week(now), now
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)
    alert(s, text)
    send_vip(s)
    granted(s, drops, new, text)


@router.on(8519, 8521)
async def vip_roulette(s: GameSession, msg: object) -> None:
    """Roleta VIP / moeda VIP. O cliente põe máscara antes do 8521 e só tira no 4414, então sempre
    responde; com menos de 18 ``leftItem`` o cliente ignora (fecha nada, abre nada).

    ponytail: a tabela de prêmios da roleta não está nos templates nem nas capturas."""
    s.log.info("roleta VIP sem tabela de prêmios", pedido=str(msg))
    s.send(S_ROULETTE, pb.VipRouletteMsg())


@router.on(8756)
async def vip_custom(s: GameSession, _: object) -> None:
    """Clique no atendimento VIP (QQ) do cliente chinês: só registro, o cliente não espera resposta."""
    s.log.info("atendimento VIP clicado")


# ---------------------------------------------------------------- contrato do rei (8540)


def _king_end(snap: PlayerSnapshot, cid: int) -> datetime | None:
    st = ev.peek(snap, f"king:{cid}")
    return ev.parse_time(st.text) if st and st.text else None


def has_contract(snap: PlayerSnapshot, cid: int, now: datetime) -> bool:
    end = _king_end(snap, cid)
    return end is not None and end > now


def send_king(s: GameSession) -> None:
    snap = s.snapshot
    assert snap is not None
    msg = pb.KingContractMsg()
    for row in s.ctx.templates.rows("KingContracts"):
        cid = int(row["Id"])
        msg.kingContractInfos.add(contractId=cid, endData=b.fmt_time(_king_end(snap, cid) or snap.character.created_at))
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
        if not has_contract(snap, KING_BUFF_FROM, now) or day.value or KING_BUFF not in rows:
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
        start = max(now, _king_end(snap, i) or now)  # renovar soma ao que falta
        st.text, st.updated_at = b.fmt_time(start + timedelta(minutes=int(rows[i]["Duration"]))), now
        changed.append(st)
    await s.ctx.characters.save(snap.character, spent, *changed)
    granted(s, [], [], "", chat=False)
    send_king(s)


# ---------------------------------------------------------------- alquimia (8320/8321) e alma (8466/8467)


def _cost(used: int) -> int:
    return min((used + 1) * 2, MAX_COST)


def _alchemy_gold(s: GameSession, snap: PlayerSnapshot) -> int:
    """AlchemyFrame.refreshView: Meclis (901) Property1 x 10 + Altın Ocağı (101) Property1 x 5."""
    return int(_building(s, snap, 901).get("Property1", 0)) * 10 + int(_building(s, snap, 101).get("Property1", 0)) * 5


def _lucky_msg(s: GameSession, snap: PlayerSnapshot) -> pb.PlayerLuckyMsg:
    used = ev.daily(snap, "alchemy", s.ctx.clock.now()).value
    left = max(0, ALCHEMY_COUNT + vip_right(s, snap, ALCHEMY_RIGHT) - used)
    return pb.PlayerLuckyMsg(luckyCount=used, remainCount=left, point=_cost(used), gold=_alchemy_gold(s, snap))


@router.on(8320)
async def alchemy_info(s: GameSession, _: object) -> None:
    assert s.snapshot is not None
    s.send(S_LUCKY, _lucky_msg(s, s.snapshot))


@router.on(8321)
async def alchemy(s: GameSession, _: object) -> None:
    """Troca diamante por ouro: custo (usos+1)*2 até 40 (o cliente só olha ``point``)."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    info = _lucky_msg(s, snap)
    spent = ledger.spend(snap.character, info.point, "alchemy", now, bound=False) if info.remainCount else None
    if spent is None:
        s.log.info("8321 recusado", restam=info.remainCount)
        s.send(S_LUCKY, info)
        return
    st = ev.daily(snap, "alchemy", now)
    st.value, st.updated_at = st.value + 1, now
    snap.character.gold += info.gold
    await s.ctx.characters.save(snap.character, st, spent)
    granted(s, [(-100, info.gold)], [], "", chat=False)  # 3 + 109
    s.send(S_LUCKY, _lucky_msg(s, snap))  # gold = quanto cada uso rende (texto do cliente)


def _soul_amount(s: GameSession, snap: PlayerSnapshot) -> int:
    """Kışla (402) e 1201 pelo nível x RefiningSoul_ArmyHouseMut / _PeopleMut (login.json #10)."""
    barracks = int(_building(s, snap, 402).get("BuildingGrade", 0))
    people = int(_building(s, snap, 1201).get("BuildingGrade", 0))
    return barracks * _cfg(s, "RefiningSoul_ArmyHouseMut") + people * _cfg(s, "RefiningSoul_PeopleMut")


def _soul_msg(s: GameSession, snap: PlayerSnapshot) -> pb.PlayerRefiningSoulMsg:
    used = ev.daily(snap, "soul", s.ctx.clock.now()).value
    left = max(0, _cfg(s, "RefiningSoul_Count") + vip_right(s, snap, SOUL_RIGHT) - used)
    return pb.PlayerRefiningSoulMsg(count=used, remainCount=left, point=_cost(used), soul=_soul_amount(s, snap))


@router.on(8466)
async def soul_info(s: GameSession, _: object) -> None:
    assert s.snapshot is not None
    s.send(S_SOUL, _soul_msg(s, s.snapshot))


@router.on(8467)
async def soul(s: GameSession, _: object) -> None:
    """Troca diamante por alma (``strategy``), a partir do nível RefiningSoul_Grades."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    info = _soul_msg(s, snap)
    ok = info.remainCount and snap.character.grades >= _cfg(s, "RefiningSoul_Grades")
    spent = ledger.spend(snap.character, info.point, "refining_soul", now, bound=False) if ok else None
    if spent is None:
        s.log.info("8467 recusado", restam=info.remainCount)
        s.send(S_SOUL, info)
        return
    st = ev.daily(snap, "soul", now)
    st.value, st.updated_at = st.value + 1, now
    snap.character.strategy += info.soul
    await s.ctx.characters.save(snap.character, st, spent)
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
    """Estados que o oficial manda no login (login.json #9, #10, #15, #107)."""
    assert s.snapshot is not None
    s.send(S_LUCKY, _lucky_msg(s, s.snapshot))
    s.send(S_SOUL, _soul_msg(s, s.snapshot))
    send_king(s)
    send_vip(s)
