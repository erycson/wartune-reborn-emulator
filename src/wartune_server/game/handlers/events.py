"""Atividades e recompensas de login: SumActive (8586), assinatura (8266), login acumulado (8496),
guia de 7 dias (8749) e atividade diária "leed" (8234/8235/8322/8518). Regras em docs/eventos.md.
"""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from datetime import datetime

from ...domain import gameday
from ...domain.models import BagType, EventState, PlayerSnapshot, Quest, StarBag
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import Row
from .. import bag, castle, guild, rewards, rules, titles
from .. import events as ev
from ..builders import login as b
from ..builders.player import quest_update
from ..router import router
from ..session import GameSession
from . import campaign, gemmaze, hero, minigames, offer, shop, stars, systems, tower, vip
from .login import army
from .player import _player, alert, granted

S_SUM_TEMP, S_SUM_DATA, S_SIGN, S_SERVEN, S_TITLES = 4475, 4476, 4177, 4638, 4484
S_CHAT, S_LEED_UPDATE, S_LEED_RECEIVE, S_CLICK, S_RATE, S_ITEMS = 83, 4152, 4150, 4412, 4247, 115
SERVEN_QUEST = 130  # a conclusão dela abre o guia de 7 dias (4638)
# (visto) tutorial_en #60-#67: 4475 de 11961/11616/11762/3821 bytes; a página fecha antes de passar disso
PAGE_BYTES = 12000
LOGIN_BONUS, ONLINE, DEVOTION, EXCHANGE = 13, 14, 12, 10  # activeType com regra aqui (os contados: ev.COUNTED)
HAS_ITEM = 11  # condição da troca: ter ``conditionValue`` do item ``conditionBak`` (FunnyHelper.mutiMaxNum)
EVERYONE, VIP_ONLY = 1, 2  # condição 14 do Login Bonus (FunnyBagData: title14 "non-VIP", title15 "VIP")
CAN, TAKEN, NOT_YET = 1, 2, 3  # PackageData.status
GIFT_OK = "Gift pack retrieval successful."  # texto do oficial inglês (tutorial_en #2770)
LEED_BOX = (10, 40, 60, 80, 100)  # DayGuideCatecory.canPick: atividade mínima de cada baú 1..5
LOGIN_LEED, WORLD_CHAT_LEED = 1, 16  # LeedTemp "Daily Login", "Speak in world chat"
# LeedTemp "Complete a solo dungeon", "... multi-player dungeon", "Plunder another player", "Perform a guild blessing",
# "Challenge another player", "Complete a daily quest" (o 4 e o 10: tutorial_en #521 e #1649)
CAMPAIGN_LEED, MULTI_CAMPAIGN_LEED, PLUNDER_LEED, BLESS_LEED, CHALLENGE_LEED, DAILY_QUEST_LEED = 4, 5, 10, 12, 19, 20
# "Contribute to your Guild", "Consume Balens/Bound Balens", "Capture an Astral", "Spin the Blessing Wheel" (visto, só
# turco: birlik_katkisi #11, yeralti_labirenti #8, kader_sistemi #5, city_city_upgrade #139); "Fight a World BOSS",
# "Complete Bounty Quest", "Harvest from your own farm" (dedução: o nome do LeedTemp, sem captura)
GUILD_OFFER_LEED, BALEN_LEED, ASTRAL_LEED, WHEEL_LEED = 8, 15, 17, 33
WORLD_BOSS_LEED, BOUNTY_LEED, FARM_LEED = 18, 24, 25
VIP_DEVOTION = 2  # VipPrerogativeTempInfos.type "Devotion Bonus" (0, 0, 10, 10 ... 40 do VIP 1 ao 9)
DEVOTION_QUEST, S_QUESTS = 63, 112  # QuestCondictionInfos.CondictionType "Devotion"; QuestUpdatedRspMsg
# (visto) tutorial_en #16 (login), #522, #753, #1652: canal 3, quando o total (totalNum do 4152) sobe
DEVOTION_UP = "Your devotion level has increased to {}."
RELOGIN_DAYS = 7  # ReloginDrops.Times 1..7
# ServenDayLeadMsg: tarefas (SimpleTasks.TaskId) de cada dia, como o oficial agrupa (tutorial_en #3193)
SERVEN: dict[int, tuple[int, ...]] = {1: (1, 2, 3, 4), 2: (5, 6, 7, 8), 3: (9, 10, 11, 12), 4: (13, 14, 15, 16)}
SERVEN |= {5: (17, 18, 19, 20), 6: (21, 23, 27), 7: (26, 28, 29)}
ALL_DAYS = 0b11111110  # bits 1-7 do estado "serven": os 7 prêmios resgatados


# ---------------------------------------------------------------- login e PlayerMsg


def _value(snap: PlayerSnapshot, key: str) -> int:
    st = ev.peek(snap, key)
    return st.value if st is not None else 0


def touch_login(snap: PlayerSnapshot, now: datetime) -> list[EventState]:
    """Primeiro login do dia: soma um dia de login (8496) e marca o leed 1. Devolve as linhas alteradas (quem chama
    grava)."""
    day = ev.state(snap, "login", now)
    if day.value and gameday.same_day(day.updated_at, now):
        return []
    day.value, day.updated_at = day.value + 1, now
    return [day, leed_progress(snap, LOGIN_LEED, now)]


def fill_player(msg: pb.PlayerMsg, snap: PlayerSnapshot, now: datetime) -> None:
    """Campos de evento do ``PlayerMsg`` (3): assinatura, login acumulado, baús da atividade diária."""
    sign = _sign_state(snap, now)
    msg.signSite, msg.signTimes = sign.value, sign.value.bit_count()
    msg.reloginCount = max(1, _value(snap, "login"))
    msg.reloginProcess = _value(snap, "relogin")
    msg.leedProcess = ev.daily(snap, "leedbox", now).value


async def login_push(s: GameSession) -> None:
    """O que o oficial manda no 8224 ``user`` antes do 4598: atividade diária, SumActive, guia."""
    s.online_since = s.ctx.clock.now()
    await shop.send_offers(s)  # 4238 antes do 4428/4434 (oficial_encantar #57-#60)
    vip.login_push(s)
    assert s.snapshot is not None
    if vip.vip_right(s, s.snapshot, vip.VIP_AUTO_SIGN):
        # VipPrerogativeType.AUTO_SIGN_IN (3): "Auto Daily Check-In on Login" do VIP 2 em diante; o cliente não
        # manda nada (nenhum uso do tipo no decompilado), então o servidor assina. (dedução) o 4177 logo aqui
        await _sign(s, auto=True)
    offer.login_push(s)
    from . import dungeon  # dungeon importa player, que importa login, que importa este módulo

    await dungeon.login_push(s)
    _send_leeds(s)
    _send_actives(s)
    send_titles(s)  # (visto) tutorial_en #68-#71, 153200 #64-#66: 4476, 4484, 4497
    send_serven(s)
    await gemmaze.load_order(s)
    minigames.login_push(s)  # o 4640 vem logo depois do 4638, como no login do oficial (só turco: login.json #93-94)


def send_rate(s: GameSession) -> None:
    """4247: evento de EXP do servidor em curso (``exp_rate_events``), no login logo depois do 4686 (tutorial_en
    #44-#46). O cliente mostra "EXP received from dungeon increased by {rate}%" (PlayerBufferInfo, bufferType 0).

    O multiplicador não é aplicado aqui: a captura (tutorial_en #45) foi feita com o evento ativo, e o EXP das lutas
    e do fim da masmorra já vem dela (630 = BaseGp 600 x 1,05, sem dobrar)."""
    rates = ev.running_rates(s.ctx.world, s.ctx.clock.now())
    if rates:
        msg = pb.RateUpdateReqMsg()
        for r in rates:
            msg.rateInfo.add(
                rate=r.rate,
                beginTime=r.begin_time,
                endTime=r.end_time,
                beginDay=r.begin_day,
                endDay=r.end_day,
                bufferType=r.buffer_type,
            )
        s.send(S_RATE, msg)


async def leave(s: GameSession) -> None:
    """Desconexão: soma o tempo online nos presentes online (tipo 14)."""
    if s.snapshot is not None and s.online_since is not None:
        await s.ctx.characters.save(*_flush_online(s, s.ctx.clock.now()))


# ---------------------------------------------------------------- SumActive (4475/4476/8586)


def active_info(a: ev.Active) -> pb.SumActiveinfoMsg:
    """A atividade como o oficial manda no 4475 (tutorial_en #60-#67)."""
    info = pb.SumActiveinfoMsg(
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
        for t, count, kind in p.entries:
            pkg.items.add(templateId=t, templateType=kind, count=count, isbind=True, length=0, job=0)
        c = (*p.condition, 0, 0, 0, 0)
        pkg.conditions.add(conditionId=c[0], conditionValue=c[1], conditionBak=c[2], conditionBak2=c[3],
                           conditionBak3=c[4], conditionBak4=c[5])  # fmt: skip
    return info


def _send_actives(s: GameSession) -> None:
    """4475 em páginas de até ``PAGE_BYTES`` e logo depois o 4476 de todas, sem pedido (tutorial_en #68)."""
    now = s.ctx.clock.now()
    actives = s.ctx.events.listed(now)
    pages: list[list[pb.SumActiveinfoMsg]] = [[]]
    size = 0
    for info in map(active_info, actives):
        n = info.ByteSize() + 3  # + a etiqueta e o tamanho do campo
        if pages[-1] and size + n > PAGE_BYTES:
            pages.append([])
            size = 0
        pages[-1].append(info)
        size += n
    for n, page in enumerate(pages, 1):
        msg = pb.SumActivesMsg(dataStamp=s.ctx.events.data_stamp, curPage=n, maxPage=len(pages), actives=page)
        s.send(S_SUM_TEMP, b.complete(msg))
    _sum_data(s, actives)


def _sum_data(s: GameSession, actives: list[ev.Active]) -> None:
    """4476 e, com montaria, o 4426 logo depois: (visto) oficial_20261023-231733-1, os 28 4426 da sessão vêm depois
    de um 4476 (#63, #80, #265, #901...), e as sessões sem montaria (tutorial_en, 153200) não têm nenhum."""
    from .systems import send_mount  # systems importa este módulo

    s.send(S_SUM_DATA, _active_data(s, actives))
    send_mount(s)


def items_gained(s: GameSession) -> None:
    """4476 de todas logo depois do 115 que dá item (tutorial_en: 26 dos 61 115, todos de ganho: missão #490, carta
    #1112, drop #2927, caixa #678, presente VIP #3268); mover, vestir e gastar não mandam. Depois, os 4484 de
    ``titles.item_checks`` (tutorial_en #2760-#2769: 4476 e 9 4484; o 4476 do 8586 e o "só desta" vão sem)."""
    _sum_data(s, s.ctx.events.listed(s.ctx.clock.now()))
    for _ in range(titles.item_checks(s.ctx.templates)):
        send_titles(s)


def send_titles(s: GameSession) -> None:
    assert s.snapshot is not None
    owned = {i.template_id for i in s.snapshot.items}
    s.send(S_TITLES, titles.appells_msg(s.snapshot.character, s.ctx.templates, owned))


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


def _daily(a: ev.Active) -> bool:
    """Pacote que volta a valer no dia seguinte: Login Bonus ("Claim them once everyday."), presente online, devoção
    (zera no dia; *dedução*) e os contadores diários de ``ev.COUNTED``."""
    return a.active_type in (LOGIN_BONUS, ONLINE, DEVOTION) or ev.COUNTED.get(a.active_type, False)


def _taken(snap: PlayerSnapshot, a: ev.Active, p: ev.Package, now: datetime) -> bool:
    key = f"sum:{a.active_id}:{p.package_id}"
    st = ev.daily(snap, key, now) if _daily(a) else ev.peek(snap, key)
    return st is not None and st.value > 0


def _progress(s: GameSession, a: ev.Active, now: datetime) -> int | None:
    """Quanto o jogador fez para a atividade ``a`` (``ActiveData.value``, o ``finishNum`` do cliente); None = o
    servidor não conta esse tipo (fica "ainda não")."""
    snap = s.snapshot
    assert snap is not None
    if a.active_type == DEVOTION:  # condição 13 ACTIVE_VALUE: a devoção de hoje (totalNum do 4152)
        return _leeds(s, now)[1]
    if a.active_type in ev.COUNTED:
        key = f"sum:{a.active_id}"
        return ev.daily(snap, key, now).value if ev.COUNTED[a.active_type] else _value(snap, key)
    return None


def _exchanges_left(snap: PlayerSnapshot, a: ev.Active, p: ev.Package) -> int | None:
    """Trocas que ainda cabem no limite do pacote; ``None`` = sem limite."""
    if not p.limit:
        return None
    st = ev.peek(snap, f"sum:{a.active_id}:{p.package_id}")
    return max(0, p.limit - (st.value if st is not None else 0))


def _can_exchange(snap: PlayerSnapshot, p: ev.Package, times: int = 1) -> bool:
    """Tem ``times`` vezes o item pedido (condição 11: ``conditionValue`` de ``conditionBak``)."""
    if p.condition[0] != HAS_ITEM or len(p.condition) < 3:
        return False
    have = sum(i.count for i in bag.in_bag(snap) if i.template_id == p.condition[2])
    return have >= p.condition[1] * times


def _status(s: GameSession, a: ev.Active, now: datetime) -> list[tuple[ev.Package, int, int]]:
    """(pacote, status, countDown) de cada pacote da atividade para este jogador."""
    snap = s.snapshot
    assert snap is not None
    out = []
    if now < a.begin:  # listada antes de começar (tutorial_en #68: as de 10-22 em diante, todas 3)
        return [(p, NOT_YET, 0) for p in a.packages]
    if a.active_type == EXCHANGE:  # vale enquanto tiver o item e couber no limite (*dedução*: sem captura de troca)
        for p in a.packages:
            if _exchanges_left(snap, a, p) == 0:
                out.append((p, TAKEN, 0))
            else:
                out.append((p, CAN if _can_exchange(snap, p) else NOT_YET, 0))
        return out
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
    if a.active_type == LOGIN_BONUS:  # tutorial_en #68: o normal já vem 1; o VIP fica 3 até virar VIP (#3268)
        vip_now = vip.is_vip(snap, now)
        for p in a.packages:
            ok = p.condition[1] == EVERYONE or (p.condition[1] == VIP_ONLY and vip_now)
            out.append((p, TAKEN if _taken(snap, a, p, now) else CAN if ok else NOT_YET, 0))
        return out
    done = _progress(s, a, now)
    for p in a.packages:
        if _taken(snap, a, p, now):
            out.append((p, TAKEN, 0))
        else:
            # tipos sem contador no servidor (recarga, gasto, troca, montaria...) ficam "ainda não": docs/eventos.md
            ok = done is not None and done >= p.condition[1]
            out.append((p, CAN if ok else NOT_YET, 0))
    return out


def _active_data(s: GameSession, actives: Sequence[ev.Active]) -> pb.SumActiveDataMsg:
    now = s.ctx.clock.now()
    snap = s.snapshot
    assert snap is not None
    msg = pb.SumActiveDataMsg()
    for a in actives:
        # value = finishNum do cliente; nos tipos 13/14 o oficial manda 0 (tutorial_en #68); nos contados vai o
        # progresso, que o texto da tela mostra (FunnyHelper.processText, *dedução* sem captura)
        value = _progress(s, a, now) if a.active_type in ev.COUNTED else 0
        data = msg.datas.add(activeId=a.active_id, isShow=True, type=a.active_type, value=value or 0, activeCharge=0)
        for p, status, countdown in _status(s, a, now):
            pd = data.packdata.add(packId=p.package_id, status=status, isShow=True)
            if a.active_type == ONLINE:
                pd.countDown = countdown  # o oficial manda só isto no tipo 14
            else:
                # getCount da troca = quantas ainda cabem (o número no botão, FunnyBagItem; tutorial_en #68: 1, 10 e
                # 200 no personagem novo); 0 = sem limite
                pd.param1, pd.finishValue, pd.getCount = "", 0, _exchanges_left(snap, a, p) or 0
    return msg


@router.on(8586)
async def sum_active(s: GameSession, msg: pb.SumActiveGetPackageMsg) -> None:
    """type 1: progresso de todas as atividades (4476); type 2: resgata ``packageId`` (``count`` vezes na troca)."""
    now = s.ctx.clock.now()
    listed = s.ctx.events.listed(now)
    if msg.type != 2:
        _sum_data(s, listed)
        return
    snap = s.snapshot
    assert snap is not None
    a = next((x for x in s.ctx.events.running(now) if x.active_id == msg.activeId), None)
    if a is not None and a.active_type == EXCHANGE:
        await _exchange(s, a, msg, listed)
        return
    found = [(p, st) for p, st, _ in _status(s, a, now) if p.package_id == msg.packageId] if a else []
    if (
        a is None
        or not found
        or found[0][1] != CAN
        or not rewards.can_grant(snap, s.ctx.templates, found[0][0].items, s.ctx.clock.now())
    ):
        s.log.info("8586 recusado", atividade=msg.activeId, pacote=msg.packageId)
        return
    p = found[0][0]
    changed = _flush_online(s, now)
    key = f"sum:{a.active_id}:{p.package_id}"
    mark = ev.daily(snap, key, now) if _daily(a) else ev.state(snap, key, now)
    mark.value, mark.updated_at = 1, now
    if a.active_type == ONLINE:  # o próximo presente conta do zero
        st = ev.daily(snap, f"sum:{a.active_id}", now)
        st.value, st.updated_at = 0, now
    new, text = rewards.grant(snap, s.ctx.templates, p.items, style="active")
    await s.ctx.characters.save(*rewards.owners(snap), mark, *changed, *new)

    # ordem do oficial (tutorial_en #2753-#2772): 3, 109, 115, 4476 de todas (o granted manda depois do 115), 111,
    # 4476 só desta e o 83
    granted(s, p.items, new, text, chat=False)
    if not new:
        _sum_data(s, listed)
    alert(s, GIFT_OK)
    _sum_data(s, [a])
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


async def _exchange(s: GameSession, a: ev.Active, msg: pb.SumActiveGetPackageMsg, listed: list[ev.Active]) -> None:
    """Troca (tipo 10, ``getway`` 2): ``count`` vezes ``conditionValue`` do item ``conditionBak`` pelos itens do
    pacote (o FunnyMutiFrame escolhe o ``count``). *Dedução*, sem captura de troca: a resposta é a do resgate (3,
    109, 115 do que entrou, 4476, 111, 4476 desta, 83), com o 115 do que saiu antes."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    p = next((x for x in a.packages if x.package_id == msg.packageId), None)
    times = max(1, msg.count)
    left = _exchanges_left(snap, a, p) if p else 0
    drops = [(t, n * times) for t, n in p.items] if p else []
    if (
        p is None
        or (left is not None and times > left)
        or not _can_exchange(snap, p, times)
        or not rewards.can_grant(snap, s.ctx.templates, drops, now)
    ):
        s.log.info("8586 troca recusada", atividade=msg.activeId, pacote=msg.packageId, vezes=times)
        return
    changed, gone = bag.take(snap, p.condition[2], p.condition[1] * times)
    mark = ev.state(snap, f"sum:{a.active_id}:{p.package_id}", now)
    mark.value, mark.updated_at = mark.value + times, now
    new, text = rewards.grant(snap, s.ctx.templates, drops, style="active")
    changed = [i for i in changed if i not in new]
    await s.ctx.characters.save(*rewards.owners(snap), mark, *changed, *new, delete=tuple(gone))

    s.send(S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    granted(s, drops, new, text, chat=False)
    if not new:
        _sum_data(s, listed)
    alert(s, GIFT_OK)
    _sum_data(s, [a])
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


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
    await _sign(s, auto=False)


async def _sign(s: GameSession, auto: bool) -> None:
    """``auto``: a assinatura do login do VIP (``auto_sign``); já assinado não responde nada."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    st = _sign_state(snap, now)
    bit = 1 << (calendar.monthrange(now.year, now.month)[1] - now.day)
    times = (st.value | bit).bit_count()
    drops = [(int(r["TemplateId"]), int(r["Data"])) for r in s.ctx.templates.find("SignDrop", Times=times)]
    if st.value & bit or not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        s.log.info("8266 recusado", ja_assinado=bool(st.value & bit), auto=auto)
        if auto:
            return
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
        or not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now())
    ):
        s.log.info("8496 recusado", dia=msg.index, logins=days)
        return
    st.value, st.updated_at = st.value | bit, now
    new, _ = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)
    # (visto) oficial_20261023-153200-1 #1701-#1747, dias 1 a 3: 3 (se mudou moeda do jogador, o Daru), 109, 115,
    # 4476, os 4484 de títulos, 3 e o 83 sem o 111. Texto: ``Name xN`` também para moedas, na
    # ordem do oficial = linhas do ReloginDrops invertidas de 3 em 3 (*dedução* que bate com os três dias: Worn
    # Armor, Daru, Gold, 1-Day VIP Card, The Empire Crusade, Bounty Scroll)
    shown = [d for i in range(0, len(drops), 3) for d in reversed(drops[i : i + 3])]
    if any(t in rewards.CURRENCIES and t not in (-100, -600) for t, _ in drops):
        _player(s)
    granted(s, drops, new, rewards.text(s.ctx.templates, shown, "plain"), player=False)


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
    # (visto) tutorial_en #50: a lista do login vem do maior TemplateId para o menor
    for row in sorted(s.ctx.templates.rows("LeedTemp"), key=lambda r: -int(r["TemplateId"])):
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
    # (cliente) DayGuideCatecory.finishList: VIP 3+ ativo ganha a linha "VIP login" (templateId -1) já completa; o
    # valor é o "Devotion Bonus" (tipo 2), que só passa de 0 no VIP 3. O ProjectItem lê o tipo 9 para a dica, mas
    # nesta tempinfos o 9 é a alquimia de Daru: a dica mostra outro número (sem efeito no total).
    return out, total + vip.vip_right(s, snap, VIP_DEVOTION)


def _send_leeds(s: GameSession) -> None:
    assert s.snapshot is not None
    now = s.ctx.clock.now()
    leeds, total = _leeds(s, now)
    msg = pb.LeedUpdatedRspMsg(leedProcess=ev.daily(s.snapshot, "leedbox", now).value, totalNum=total)
    msg.leed.extend(leeds)
    s.send(S_LEED_UPDATE, msg)


def devotion_quests(s: GameSession) -> list[Quest]:
    """Missões de devoção (tipo 63) com o total de hoje. (visto) tutorial_en #16/#50 e #521-#522: a devoção é o
    totalNum do 4152; tempinfos: 863 "Increasing Devotion (VIP Daily)" = tipo 63, Para1 0, Para2 20: vale o maior
    total."""
    assert s.snapshot is not None
    return rules.quest_event(s.snapshot, s.ctx.templates, DEVOTION_QUEST, 0, _leeds(s, s.ctx.clock.now())[1])


def say_devotion(s: GameSession) -> None:
    """83 "Your devotion level has increased to N." com o total de hoje."""
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=DEVOTION_UP.format(_leeds(s, s.ctx.clock.now())[1])))


def leed_gain(s: GameSession, template_id: int, say: bool = True) -> list[EventState | Quest]:
    """A ação do ``LeedTemp`` aconteceu: +1 até o PassCount e manda, na ordem do oficial (tutorial_en #521-#522,
    #1649-#1652), o 4152 só com esse leed, o 83 quando o total sobe (``say=False``: quem chama manda depois, com
    ``say_devotion``, se ``devotion`` subiu) e o 112 das missões de devoção. Sem await: devolve as linhas para quem
    chama gravar (o ataque ao castelo grava depois de criar a luta)."""
    snap = s.snapshot
    assert snap is not None
    row = s.ctx.templates.get("LeedTemp", template_id)
    now = s.ctx.clock.now()
    if row is None or ev.daily(snap, f"leed:{template_id}", now).value >= int(row["PassCount"]):
        return []
    before = _leeds(s, now)[1]
    st = leed_progress(snap, template_id, now)
    leeds, total = _leeds(s, now)
    quests = devotion_quests(s)
    msg = pb.LeedUpdatedRspMsg(leedProcess=ev.daily(snap, "leedbox", now).value, totalNum=total)
    msg.leed.extend(x for x in leeds if x.templateId == template_id)
    s.send(S_LEED_UPDATE, msg)
    if total > before and say:  # (dedução) com PassCount > 1 os passos do meio não dão devoção, então sem 83
        say_devotion(s)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    return [st, *quests]


async def leed_done(s: GameSession, template_id: int, say: bool = True) -> None:
    """``leed_gain`` e grava."""
    if rows := leed_gain(s, template_id, say):
        await s.ctx.characters.save(*rows)


def devotion(s: GameSession) -> int:
    """A devoção de hoje (``totalNum`` do 4152)."""
    return _leeds(s, s.ctx.clock.now())[1]


@router.on(8234, 8322)
async def leed_client(s: GameSession, msg: object) -> None:
    """C_LEED_ADD (nenhuma tela manda) / C_LEED_CLIENT (``LoginInitDataAccept`` manda ``templateId`` 1 no login;
    o oficial devolve um 4152, oficial_encantar #25 e #52).
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
        or not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now())
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


GEM_SON = "205"  # pedras do equipamento do herói; o nível é o fim do id (Lvl. N = TemplateId % 100, nas 96)
PRIVATE_TITLE = 8  # AppellInfos "Private": CondtionType 7, honra (geste) >= Para


def _task_done(s: GameSession, task_id: int) -> bool:
    """``SimpleTasks`` por ``Type`` (``GuideTaskType`` do cliente); IParam5 é só o nível que mostra a tarefa
    (``GuideTaskItem``). O sentido dos IParam vem do ``Detail`` em inglês; fontes em docs/eventos.md."""
    snap = s.snapshot
    assert snap is not None
    t, c = s.ctx.templates, snap.character
    row = t.get("SimpleTasks", task_id, key="TaskId") or {}
    kind = int(row.get("Type", 0))
    p1, p2, p3 = (int(row.get(f"IParam{i}", 0)) for i in (1, 2, 3))
    sy = rules.systems(snap)
    worn = [i for i in snap.items if i.bag_type == BagType.HERO]
    worn_stars = [x for x in snap.stars if x.bag_type == StarBag.EQUIP]
    learned = [r for h in snap.heroes for r in hero.runes(h)]

    def tpl(category: str, template_id: int) -> Row:
        return t.get(category, template_id) or {}

    def num(r: Row, key: str) -> int:
        return int(r.get(key) or 0)

    if kind == 1:  # ARMY_LEVEL: alguma tropa no nível
        return any(num(tpl("PawnTempInfos", p.template_id), "Level") >= p1 for p in snap.pawns)
    if kind == 2:  # GUILD_SKILL: p1 habilidades da guilda no nível p2
        return sum(int(getattr(c, col)) >= p2 for col in guild.SKILLS.values()) >= p1
    if kind == 3:  # PERSONAL_SKILL (abre o SeminaryFrame): alguma tecnologia no nível
        techs = [
            r for b in snap.buildings if (r := tpl("BuildingTempInfos", b.template_id)).get("MasterType") in castle.TECH
        ]
        return any(num(r, "BuildingGrade") >= p1 for r in techs)
    if kind == 4:
        return c.grades >= p1
    if kind == 5:  # USE_STAR: p1 estrelas equipadas de qualidade p2+ (Profile 3 = rara; lixo e Energine não equipam)
        return sum(num(stars.star_tpl(t, x), "Profile") >= p2 for x in worn_stars) >= p1
    if kind == 6:  # USE_EQUIPMENT: p1 peças vestidas de nível p3+
        return sum(num(tpl("ItemTempInfos", i.template_id), "NeedGrades") >= p3 for i in worn) >= p1
    if kind == 7:  # STRENGTHEN_EQU: encantada a p3, de nível p1+ e qualidade p2+ (Profile 5 = [Legendary])
        return any(
            i.strengthen_grade >= p3 and num(r, "NeedGrades") >= p1 and num(r, "Profile") >= p2
            for i in snap.items
            if (r := tpl("ItemTempInfos", i.template_id))
        )
    if kind == 8:  # PASS_TOWER: recorde do Forgotten Catacombs (maxIndex do 4205)
        return p1 <= tower.MAZE_MAX_INDEX
    if kind == 9:  # STAR_LEVEL: estrela equipada no grau
        return any(x.grade >= p1 for x in worn_stars)
    if kind == 10:  # INLAY_STONE: p1 pedras de nível p2+ engastadas (a Divinity Soul do mascote não conta)
        gems = [j for i in snap.items for j in i.joins if j > 0 and tpl("ItemTempInfos", j).get("SonType") == GEM_SON]
        return sum(j % 100 >= p2 for j in gems) >= p1
    if kind == 11:  # LEARN_FU_WEN
        return bool(learned)
    if kind == 12:  # GET_MOUNT
        return bool(systems.avatars(sy, s.ctx.clock.now()))
    if kind == 13:  # PASS_CAMPAIGN: a masmorra p1 vencida (a nota só é gravada no fim, campaign._finish)
        return ev.peek(snap, campaign.RANK_KEY.format(p1)) is not None
    if kind == 14:  # GUILD_DEVOTE
        return c.consortia_total_offer >= p1
    if kind == 15:  # STAR_VALUE: o "Astral Value" do HoroscopeFrame (StarModel.getStarPow: EXP das equipadas / 10)
        return sum(stars.value(t, x) for x in worn_stars) // 10 >= p1
    if kind == 16:  # SOUL_IMPORT_PARVAT: FightingManager.getMarkingScore lê o SOUL de jewelGrades = storeGrade
        return c.store_grade >= p1
    if kind == 17:  # FU_WEN_LEVEL: alguma runa no nível p2
        return any(num(tpl("RuneTempInfos", r), "RuneGrade") >= p2 for r in learned)
    if kind == 18:  # TALENT_LEVEL
        return any(h.talent_grade >= p1 for h in snap.heroes)
    if kind == 19:  # GET_PET
        return bool(snap.pets)
    if kind == 20:  # MOUNT_LEVEL: o nível da tela de montaria (MountInfo.grade = Beast Soul Lvl)
        return bool(systems.avatars(sy)) and systems.soul_grade(t, sy) >= p1
    if kind == 21:  # HONOUR_SOLDIER: título Private, a honra (thane.honer = geste) no Para dele
        return c.geste >= num(tpl("AppellInfos", PRIVATE_TITLE), "Para") > 0
    if kind == 22:
        return army(s, snap)[1] >= p1
    # ponytail: 23 ENTER_CAMPAIGN (The Spire, 8201) não tem entrada no servidor; nada grava ter entrado
    return False


def serven_start(snap: PlayerSnapshot) -> datetime | None:
    """O guia de 7 dias começa na conclusão da missão 130 (tutorial_en #3187-#3193: ``beginTime`` = a
    ``completedDate`` dela, e o login do personagem novo não manda 4638)."""
    q = rules.quest(snap, SERVEN_QUEST)
    return q.completed_at if q is not None and q.completed else None


def _serven_msg(s: GameSession) -> pb.ServenDayLeadMsg:
    snap = s.snapshot
    assert snap is not None
    taken = _value(snap, "serven")
    start = serven_start(snap) or snap.character.created_at
    msg = pb.ServenDayLeadMsg(beginTime=b.fmt_time(start), statu=int(taken != ALL_DAYS))
    for day, tasks in SERVEN.items():
        d = msg.singleDay.add(day=day, getReward=int(bool(taken & 1 << day)))
        for t in tasks:
            d.simpleTask.add(taskId=t, isComplete=int(_task_done(s, t)))
    return msg


def send_serven(s: GameSession) -> None:
    """4638: no login de quem já concluiu a 130, na conclusão dela (``player.quest_finish``) e na volta da campanha
    (``campaign._leave_campaign``)."""
    assert s.snapshot is not None
    if serven_start(s.snapshot) is not None:
        msg = _serven_msg(s)
        s.serven_sent = msg.SerializeToString()
        s.send(S_SERVEN, msg)


def refresh_serven(s: GameSession) -> None:
    """Depois de cada pedido (``GameSession.on_packet``): manda o 4638 de novo se alguma tarefa ou prêmio mudou desde o
    último. O cliente nunca pede o painel (``GuideTaskManager`` só escuta o 4638), e o oficial manda o 4638 no meio da
    sessão (oficial_encantar #700-#706, na volta da campanha). (dedução) mandar também quando uma tarefa fecha fora da
    campanha; fora da campanha e da batalha, e só até os 7 prêmios saírem, para não refazer as contas à toa."""
    snap = s.snapshot
    if snap is None or s.serven_sent is None or s.battle is not None or (s.campaign and not s.campaign.finished):
        return
    if _value(snap, "serven") == ALL_DAYS:
        return
    msg = _serven_msg(s)
    if (raw := msg.SerializeToString()) != s.serven_sent:
        s.serven_sent = raw
        s.send(S_SERVEN, msg)


@router.on(8749)
async def serven_reward(s: GameSession, msg: pb.GetRewardMsg) -> None:
    """Prêmio do dia ``day`` do guia de 7 dias: todas as tarefas do dia feitas, dia já alcançado
    (dias desde a criação, GuideTaskManager.getCurrDay) e ainda não resgatado."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    st = ev.state(snap, "serven", now)
    start = serven_start(snap)
    current = (now.date() - start.date()).days + 1 if start is not None else 0
    drops = [(int(r["TemplateId"]), int(r["Count"])) for r in s.ctx.templates.find("ServenLeadRewards", Day=msg.day)]
    ok = msg.day in SERVEN and msg.day <= current and not st.value & 1 << msg.day
    if (
        not ok
        or not all(_task_done(s, t) for t in SERVEN[msg.day])
        or not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now())
    ):
        s.log.info("8749 recusado", dia=msg.day)
        return
    st.value, st.updated_at = st.value | 1 << msg.day, now
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)
    alert(s, text)
    send_serven(s)
    granted(s, drops, new, text)
