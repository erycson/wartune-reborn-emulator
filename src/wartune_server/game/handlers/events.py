"""Atividades e recompensas de login: SumActive (8586), assinatura (8266), login acumulado (8496),
guia de 7 dias (8749) e atividade diária "leed" (8234/8235/8322/8518). Regras em docs/eventos.md.
"""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from datetime import datetime

from ...domain.models import EventState, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from .. import events as ev
from .. import rewards, rules
from ..builders import login as b
from ..builders.player import quest_update
from ..router import router
from ..session import GameSession
from . import minigames, offer, vip
from .login import army
from .player import alert, granted

S_SUM_TEMP, S_SUM_DATA, S_SIGN, S_SERVEN = 4475, 4476, 4177, 4638
S_CHAT, S_LEED_UPDATE, S_LEED_RECEIVE, S_CLICK = 83, 4152, 4150, 4412
PAGE = 10  # atividades por 4475 (o oficial manda ~11 por página)
LOGIN_DAYS, ONLINE = 13, 14  # activeType com regra no servidor
CAN, TAKEN, NOT_YET = 1, 2, 3  # PackageData.status
GIFT_OK = "Hediye Paketi başarıyle alındı"  # texto do oficial (com o erro de digitação)
LEED_BOX = (10, 40, 60, 80, 100)  # DayGuideCatecory.canPick: atividade mínima de cada baú 1..5
LOGIN_LEED, WORLD_CHAT_LEED = 1, 16  # LeedTemp "Günlük Giriş", "Dünya Kanalında Sohbet"
EMEK, S_QUESTS = 63, 112  # QuestCondictionInfos.CondictionType "Emek Oranı"; QuestUpdatedRspMsg
RELOGIN_DAYS = 7  # ReloginDrops.Times 1..7
# ServenDayLeadMsg: tarefas (SimpleTasks.TaskId) de cada dia, como o oficial agrupa (login.json #93)
SERVEN: dict[int, tuple[int, ...]] = {1: (1, 2, 3, 4), 2: (5, 6, 7, 8), 3: (9, 10, 11, 12), 4: (13, 14, 15, 16)}
SERVEN |= {5: (17, 18, 19, 20), 6: (21, 23, 27), 7: (26, 28, 29)}


# ---------------------------------------------------------------- login e PlayerMsg


def _value(snap: PlayerSnapshot, key: str) -> int:
    st = ev.peek(snap, key)
    return st.value if st is not None else 0


def touch_login(snap: PlayerSnapshot, now: datetime, catalog: ev.EventCatalog) -> list[EventState]:
    """Primeiro login do dia: soma um dia de login (8496, atividades tipo 13) e marca o leed 1.
    Devolve as linhas alteradas (quem chama grava)."""
    day = ev.state(snap, "login", now)
    if day.value and day.updated_at.date() == now.date():
        return []
    day.value, day.updated_at = day.value + 1, now
    changed = [day, leed_progress(snap, LOGIN_LEED, now)]
    for a in catalog.running(now):
        if a.active_type == LOGIN_DAYS:
            st = ev.state(snap, f"sum:{a.active_id}", now)
            st.value, st.updated_at = st.value + 1, now
            changed.append(st)
    return changed


def fill_player(msg: pb.PlayerMsg, snap: PlayerSnapshot, now: datetime) -> None:
    """Campos de evento do ``PlayerMsg`` (3): assinatura, login acumulado, baús da atividade diária."""
    sign = _sign_state(snap, now)
    msg.signSite, msg.signTimes = sign.value, sign.value.bit_count()
    msg.reloginCount = max(1, _value(snap, "login"))
    msg.reloginProcess = _value(snap, "relogin")
    msg.leedProcess = ev.daily(snap, "leedbox", now).value


def login_push(s: GameSession) -> None:
    """O que o oficial manda no 8224 ``user`` antes do 4598: atividade diária, SumActive, guia."""
    s.online_since = s.ctx.clock.now()
    vip.login_push(s)
    offer.login_push(s)
    _send_leeds(s)
    _send_actives(s)
    _send_serven(s)
    minigames.login_push(s)  # o 4640 vem logo depois do 4638, como no login do oficial (#93-94)


async def leave(s: GameSession) -> None:
    """Desconexão: soma o tempo online nos presentes online (tipo 14)."""
    if s.snapshot is not None and s.online_since is not None:
        await s.ctx.characters.save(*_flush_online(s, s.ctx.clock.now()))


# ---------------------------------------------------------------- SumActive (4475/4476/8586)


def _send_actives(s: GameSession) -> None:
    now = s.ctx.clock.now()
    actives = s.ctx.events.running(now)
    pages = [actives[i : i + PAGE] for i in range(0, len(actives), PAGE)] or [[]]
    for n, page in enumerate(pages, 1):
        msg = pb.SumActivesMsg(dataStamp=s.ctx.events.data_stamp, curPage=n, maxPage=len(pages))
        for a in page:
            info = msg.actives.add(
                activeId=a.active_id,
                beginDate=b.fmt_time(a.begin),
                endDate=b.fmt_time(a.end),
                title=a.title,
                detail=a.detail,
                conditionDetail=a.condition_detail,
                getway=a.getway,
                activeType=a.active_type,
                startTime=b.fmt_time(a.begin),
                stopTime=b.fmt_time(a.end),
                order=a.order,
                appendParam="null",
            )
            for p in a.packages:
                pkg = info.packages.add(packageId=p.package_id, order=p.order)
                for t, count in p.items:
                    pkg.items.add(templateId=t, templateType=1, count=count, isbind=True, length=0, job=0)
                pkg.conditions.add(conditionId=p.condition[0], conditionValue=p.condition[1])
        s.send(S_SUM_TEMP, b.complete(msg))


def _online_seconds(s: GameSession, a: ev.Active, now: datetime) -> int:
    """Segundos online hoje desde o último resgate do presente online ``a``."""
    assert s.snapshot is not None
    live = int((now - s.online_since).total_seconds()) if s.online_since else 0
    return ev.daily(s.snapshot, f"sum:{a.active_id}", now).value + live


def _flush_online(s: GameSession, now: datetime) -> list[EventState]:
    assert s.snapshot is not None
    changed = []
    for a in s.ctx.events.running(now):
        if a.active_type == ONLINE:
            st = ev.daily(s.snapshot, f"sum:{a.active_id}", now)
            st.value, st.updated_at = _online_seconds(s, a, now), now
            changed.append(st)
    s.online_since = now
    return changed


def _taken(snap: PlayerSnapshot, a: ev.Active, p: ev.Package, now: datetime) -> bool:
    key = f"sum:{a.active_id}:{p.package_id}"
    st = ev.daily(snap, key, now) if a.active_type == ONLINE else ev.peek(snap, key)
    return st is not None and st.value > 0


def _status(s: GameSession, a: ev.Active, now: datetime) -> list[tuple[ev.Package, int, int]]:
    """(pacote, status, countDown) de cada pacote da atividade para este jogador."""
    snap = s.snapshot
    assert snap is not None
    out = []
    if a.active_type == ONLINE:  # um por vez, em ordem; o tempo zera a cada resgate
        elapsed = _online_seconds(s, a, now)
        ordered = sorted(a.packages, key=lambda p: p.order)
        nxt = next((p for p in ordered if not _taken(snap, a, p, now)), None)
        for p in ordered:
            if _taken(snap, a, p, now):
                out.append((p, TAKEN, 0))
            else:
                ready = p is nxt and elapsed >= p.condition[1]
                out.append((p, CAN if ready else NOT_YET, max(0, p.condition[1] - elapsed)))
        return out
    days = _value(snap, f"sum:{a.active_id}")
    for p in a.packages:
        if _taken(snap, a, p, now):
            out.append((p, TAKEN, 0))
        else:
            # ponytail: só os tipos 13 e 14 têm regra; os outros ficam "ainda não" até alguém implementar
            ok = a.active_type == LOGIN_DAYS and days >= p.condition[1]
            out.append((p, CAN if ok else NOT_YET, 0))
    return out


def _active_data(s: GameSession, actives: Sequence[ev.Active]) -> pb.SumActiveDataMsg:
    now = s.ctx.clock.now()
    msg = pb.SumActiveDataMsg()
    for a in actives:
        data = msg.datas.add(activeId=a.active_id, isShow=True, type=a.active_type, value=0, activeCharge=0)
        for p, status, countdown in _status(s, a, now):
            pd = data.packdata.add(packId=p.package_id, status=status, isShow=True)
            if a.active_type == ONLINE:
                pd.countDown = countdown  # o oficial manda só isto no tipo 14
            else:
                pd.param1, pd.finishValue, pd.getCount = "", 0, 0
    return msg


@router.on(8586)
async def sum_active(s: GameSession, msg: pb.SumActiveGetPackageMsg) -> None:
    """type 1: progresso de todas as atividades (4476); type 2: resgata ``packageId``."""
    now = s.ctx.clock.now()
    running = s.ctx.events.running(now)
    if msg.type != 2:
        s.send(S_SUM_DATA, _active_data(s, running))
        return
    snap = s.snapshot
    assert snap is not None
    a = next((x for x in running if x.active_id == msg.activeId), None)
    found = [(p, st) for p, st, _ in _status(s, a, now) if p.package_id == msg.packageId] if a else []
    if a is None or not found or found[0][1] != CAN or not rewards.can_grant(snap, s.ctx.templates, found[0][0].items):
        s.log.info("8586 recusado", atividade=msg.activeId, pacote=msg.packageId)
        return
    p = found[0][0]
    changed = _flush_online(s, now)
    mark = ev.state(snap, f"sum:{a.active_id}:{p.package_id}", now)
    mark.value, mark.updated_at = 1, now
    if a.active_type == ONLINE:  # o próximo presente conta do zero
        st = ev.daily(snap, f"sum:{a.active_id}", now)
        st.value, st.updated_at = 0, now
    new, text = rewards.grant(snap, s.ctx.templates, p.items, style="active")
    await s.ctx.characters.save(*rewards.owners(snap), mark, *changed, *new)

    alert(s, GIFT_OK)  # ordem do oficial (captura online_odul... #38-46)
    s.send(S_SUM_DATA, _active_data(s, [a]))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    s.send(S_SUM_DATA, _active_data(s, running))
    granted(s, p.items, new, text, chat=False)


# ---------------------------------------------------------------- assinatura (8266)


def _sign_state(snap: PlayerSnapshot, now: datetime) -> EventState:
    """``value`` = signSite do mês corrente (bit ``dias_do_mês - dia``, DayGuideCatecory.hasSigned)."""
    st = ev.state(snap, "sign", now)
    if st.text != now.strftime("%Y-%m"):
        st.value, st.text = 0, now.strftime("%Y-%m")
    return st


@router.on(8266)
async def sign(s: GameSession, _: object) -> None:
    """Assina o dia; ao chegar num ``SignDrop.Times`` (2/5/10/17/26 no mês) o servidor dá o pacote."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    st = _sign_state(snap, now)
    bit = 1 << (calendar.monthrange(now.year, now.month)[1] - now.day)
    times = (st.value | bit).bit_count()
    drops = [(int(r["TemplateId"]), int(r["Data"])) for r in s.ctx.templates.find("SignDrop", Times=times)]
    if st.value & bit or not rewards.can_grant(snap, s.ctx.templates, drops):
        s.log.info("8266 recusado", ja_assinado=bool(st.value & bit))
        s.send(S_SIGN, pb.PlayerSignRspMsg(signDate=b.fmt_time(now), signTimes=st.value.bit_count(), signSite=st.value))
        return
    st.value, st.updated_at = st.value | bit, now
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)

    s.send(S_SIGN, pb.PlayerSignRspMsg(signDate=b.fmt_time(now), signTimes=times, signSite=st.value))
    if drops:
        alert(s, text)
        granted(s, drops, new, text)


# ---------------------------------------------------------------- login acumulado (8496)


@router.on(8496)
async def relogin_reward(s: GameSession, msg: pb.TakeLoginReward) -> None:
    """Resgata o dia ``index`` (1..7) do login acumulado: ``ReloginDrops.Times`` = index."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    days = _value(snap, "login")
    st = ev.state(snap, "relogin", now)
    bit = 1 << (msg.index - 1) if 1 <= msg.index <= RELOGIN_DAYS else 0
    drops = [(int(r["ItemId"]), int(r["Data"])) for r in s.ctx.templates.find("ReloginDrops", Times=msg.index)]
    if (
        not bit
        or st.value & bit
        or msg.index > days
        or not drops
        or not rewards.can_grant(snap, s.ctx.templates, drops)
    ):
        s.log.info("8496 recusado", dia=msg.index, logins=days)
        return
    st.value, st.updated_at = st.value | bit, now
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)
    alert(s, text)
    granted(s, drops, new, text)


# ---------------------------------------------------------------- atividade diária (leed)


def leed_progress(snap: PlayerSnapshot, template_id: int, now: datetime, n: int = 1) -> EventState:
    """Soma ``n`` no contador de hoje do ``LeedTemp`` (outros sistemas chamam ao acontecer a ação:
    16 chat no mundo, 4 sala individual...). Devolve a linha para gravar."""
    st = ev.daily(snap, f"leed:{template_id}", now)
    st.value, st.updated_at = st.value + n, now
    return st


def _leeds(s: GameSession, now: datetime) -> tuple[list[pb.LeedData], int]:
    snap = s.snapshot
    assert snap is not None
    out, total = [], 0
    for row in s.ctx.templates.rows("LeedTemp"):
        tid = int(row["TemplateId"])
        st = ev.daily(snap, f"leed:{tid}", now)
        count = min(st.value, int(row["PassCount"]))
        done = count >= int(row["PassCount"])
        total += int(row["Num"]) if done else 0
        out.append(
            pb.LeedData(
                templateId=tid, userId=s.player_id, currentCount=count, beginDate=b.fmt_time(now), isComplete=done
            )
        )
    return out, total


def _send_leeds(s: GameSession) -> None:
    assert s.snapshot is not None
    now = s.ctx.clock.now()
    leeds, total = _leeds(s, now)
    msg = pb.LeedUpdatedRspMsg(leedProcess=ev.daily(s.snapshot, "leedbox", now).value, totalNum=total)
    msg.leed.extend(leeds)
    s.send(S_LEED_UPDATE, msg)


async def leed_done(s: GameSession, template_id: int) -> None:
    """A ação do ``LeedTemp`` aconteceu (o sistema dela chama): +1 até o PassCount, grava e manda o 4152."""
    snap = s.snapshot
    assert snap is not None
    row = s.ctx.templates.get("LeedTemp", template_id)
    now = s.ctx.clock.now()
    if row is None or ev.daily(snap, f"leed:{template_id}", now).value >= int(row["PassCount"]):
        return
    st = leed_progress(snap, template_id, now)
    # (visto) captura savasa_baskin_ve_elmas_ile_hizlandirma #11/#18: "Emek oranı" = totalNum do 4152;
    # (visto) tempinfos: 863 = tipo 63, Para1 0, Para2 20 "Emek Oranını 20 yap": vale o maior total
    quests = rules.quest_event(snap, s.ctx.templates, EMEK, 0, _leeds(s, now)[1])
    await s.ctx.characters.save(st, *quests)
    _send_leeds(s)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(8234, 8322)
async def leed_client(s: GameSession, msg: object) -> None:
    """C_LEED_ADD / C_LEED_CLIENT: nenhuma tela do cliente manda (só existem no SocketOutManager).
    O progresso vem do que o servidor vê (``leed_done``); aqui só devolve o estado."""
    s.log.info("leed pedido pelo cliente; só estado", pedido=str(msg))
    _send_leeds(s)


@router.on(8235)
async def leed_box(s: GameSession, msg: pb.LeedFinishedReqMsg) -> None:
    """Abre o baú ``site`` (1..5) da atividade diária: ``LeedDrop.site``."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    box = ev.daily(snap, "leedbox", now)
    bit = 1 << msg.site if 1 <= msg.site <= len(LEED_BOX) else 0
    drops = [(int(r["itemId"]), int(r["count"])) for r in s.ctx.templates.find("LeedDrop", site=msg.site)]
    total = _leeds(s, now)[1]
    if (
        not bit
        or box.value & bit
        or total < LEED_BOX[msg.site - 1]
        or not rewards.can_grant(snap, s.ctx.templates, drops)
    ):
        s.log.info("8235 recusado", bau=msg.site, atividade=total)
        s.send(S_LEED_RECEIVE, pb.LeedFinishedRspMsg(result=False, site=msg.site, leedProcess=box.value))
        return
    box.value, box.updated_at = box.value | bit, now
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), box, *new)
    alert(s, text)
    s.send(S_LEED_RECEIVE, pb.LeedFinishedRspMsg(result=True, site=msg.site, leedProcess=box.value))
    granted(s, drops, new, text)


@router.on(8518)
async def daily_counts(s: GameSession, _: object) -> None:
    """Painel de atividades do dia (4412): contadores por chave (``5001``, ``match``, ``reward``...).

    ponytail: nenhum desses sistemas conta ainda; lista vazia = tudo zerado no painel."""
    s.send(S_CLICK, pb.ClickDatasRspMsg())


# ---------------------------------------------------------------- guia de 7 dias (8749)


def _task_done(s: GameSession, task_id: int) -> bool:
    """``SimpleTasks``: só nível (4) e poder de combate (22) existem no servidor ainda."""
    snap = s.snapshot
    assert snap is not None
    row = s.ctx.templates.get("SimpleTasks", task_id, key="TaskId") or {}
    kind, need = int(row.get("Type", 0)), int(row.get("IParam1", 0))
    if kind == 4:
        return snap.character.grades >= need
    if kind == 22:
        return army(s, snap)[1] >= need
    return False


def _serven_msg(s: GameSession) -> pb.ServenDayLeadMsg:
    snap = s.snapshot
    assert snap is not None
    taken = _value(snap, "serven")
    msg = pb.ServenDayLeadMsg(beginTime=b.fmt_time(snap.character.created_at), statu=int(taken != 0b11111110))
    for day, tasks in SERVEN.items():
        d = msg.singleDay.add(day=day, getReward=int(bool(taken & 1 << day)))
        for t in tasks:
            d.simpleTask.add(taskId=t, isComplete=int(_task_done(s, t)))
    return msg


def _send_serven(s: GameSession) -> None:
    s.send(S_SERVEN, _serven_msg(s))


@router.on(8749)
async def serven_reward(s: GameSession, msg: pb.GetRewardMsg) -> None:
    """Prêmio do dia ``day`` do guia de 7 dias: todas as tarefas do dia feitas, dia já alcançado
    (dias desde a criação, GuideTaskManager.getCurrDay) e ainda não resgatado."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    st = ev.state(snap, "serven", now)
    current = (now.date() - snap.character.created_at.date()).days + 1
    drops = [(int(r["TemplateId"]), int(r["Count"])) for r in s.ctx.templates.find("ServenLeadRewards", Day=msg.day)]
    ok = msg.day in SERVEN and msg.day <= current and not st.value & 1 << msg.day
    if (
        not ok
        or not all(_task_done(s, t) for t in SERVEN[msg.day])
        or not rewards.can_grant(snap, s.ctx.templates, drops)
    ):
        s.log.info("8749 recusado", dia=msg.day)
        return
    st.value, st.updated_at = st.value | 1 << msg.day, now
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)
    alert(s, text)
    _send_serven(s)
    granted(s, drops, new, text)
