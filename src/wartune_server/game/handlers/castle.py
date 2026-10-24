"""Castelo: prédios, tecnologias, filas de construção, cobrança de ouro e recursos (docs/castelo.md).

O upgrade (8203) e a construção de tecnologia (8202) são imediatos, como no oficial: o 4130 já sai
com o template novo e a fila fica ocupada ``UpgradeTime`` segundos (151). Toda validação é daqui:
dono do prédio, nível do jogador, pré-requisitos, fila livre e custo.
"""

from __future__ import annotations

from ...domain import gameday
from ...domain.models import Building, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services.ledger import pay
from ...templates.repository import GameTemplates, Row
from .. import castle as cs
from .. import rules
from ..builders import login as b
from ..builders.army import castle_pawns, unlocked_pawns
from ..builders.player import quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .login import player_info
from .vip import free_cool

S_PLAYER, S_CHAT, S_ALERT, S_QUESTS = 3, 83, 111, 112
S_BUILDINGS, S_ORDER_USE, S_ORDER_ADD, S_ORDER_QUICK, S_ORDER_LIST = 4130, 151, 104, 102, 4187
S_IMPOSE, S_TRANSFER, S_CASTLE_TIME, S_ARMY_PAWN = 4242, 103, 4452, 100
BUY_ORDER_PRICE = 395  # (cliente inglês) QueueBar.buyQueueItem: "mainBar.QueueBar.content" com 395
IMPOSE_COOLDOWN = 3600  # só turco: city_city_upgrade #3, 151 remainTime 3600
S_BLESSING = 4391  # BlessingMsg: bênção do seminário (8489)
S_EFFECT, S_POLITICS = 110, 152
ATTR_EFFECT = 3  # 110.propertyType das tecnologias de atributo (só turco: teknoloji_upgrade #3)
# (visto) tempinfos: 111-113 ("Accelerate Building Construction Cooldown 1/3/7 times") e 763 ("Collect Levy")
ACCELERATE, LEVY = 12, 42  # QuestCondictionInfos.CondictionType


def _send_player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _buildings(s: GameSession, only: list[Building]) -> pb.BuildingInfoListMsg:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    return b.buildings_msg(snap, s.ctx.templates, only, cs.impose_used(snap.castle, s.ctx.clock.now()))


def _refuse(s: GameSession, code: int, why: str, **extra: object) -> None:
    s.log.info(f"{code} recusado", motivo=why, **extra)


@router.on(5015)
async def castle_update(s: GameSession, _: object) -> None:
    """Sincroniza recursos: acumula a produção no banco e manda o 109."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    if snap.castle.produced_at is not None:
        cs.settle(snap, s.ctx.templates, s.ctx.clock.now())
        await s.ctx.characters.save(snap.character, snap.castle)
    castle_yield(s)


@router.on(8281)
async def building_init(s: GameSession, _: object) -> None:
    """Fim do tutorial na cidade externa: prédios iniciais e a fila de prédios (``sendInitBuildAndQueue``)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    now = s.ctx.clock.now()
    cs.start_production(snap, now)
    new = [] if next(cs.orders_of(snap, cs.BUILD), None) else [cs.new_order(snap, cs.BUILD, now, 1)]
    await s.ctx.characters.save(snap.castle, *new)
    castle_yield(s)
    castle_yield(s)
    s.send(S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    s.send(S_BUILDINGS, _buildings(s, snap.buildings))
    for order in new:  # o cliente acrescenta sem checar repetição: só a ordem recém-criada
        s.send(S_ORDER_ADD, cs.order_info(order, now))


def _check_target(s: GameSession, snap: PlayerSnapshot, target: Row) -> str | None:
    if int(target["BuildingGrade"]) > int(_config(s, "BUILD_MAX_GRADE", 80)):
        return "nível máximo"
    if int(target["PlayerGrades"]) > snap.character.grades:
        return "nível do jogador"
    if cs.missing_requirements(snap, s.ctx.templates, target):
        return "pré-requisito"
    return None


def _config(s: GameSession, name: str, default: int) -> int:
    row = next(s.ctx.templates.find("ConfigInfos", ConfigName=name), None)
    return int(row["ConfigValue"]) if row else default


async def _build(s: GameSession, code: int, building: Building | None, target: Row) -> None:
    """Paga, troca o template, ocupa a fila e libera o que o nível novo libera (8202 e 8203)."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    why = _check_target(s, snap, target)
    order = cs.free_order(snap, cs.order_type_for(target), now)
    gold, crystals = int(target["GoldConsume"]), int(target["CrystalsConsume"])
    before = cs.yield_msg(snap, templates, now)  # já conta a produção pendente
    if why is None and order is None:
        why = "fila ocupada"
    if why is None and (before.goldTotalCount < gold or c.crystals < crystals):
        why = "recursos"
    if why is not None:
        _refuse(s, code, why, template=target["TemplateId"])
        return
    assert order is not None
    cs.settle(snap, templates, now)
    c.gold, c.crystals = c.gold - gold, c.crystals - crystals
    if building is None:
        building = Building(c.id or 0, int(target["TemplateId"]))
        snap.buildings.append(building)
    building.template_id = int(target["TemplateId"])
    order.begin_at, order.need_time = now, int(target["UpgradeTime"])
    unlocked = cs.unlock(snap, templates, building)
    quests = rules.update_building_quests(snap, templates)
    await s.ctx.characters.save(c, snap.castle, building, order, *unlocked, *quests)

    paid = pb.CastleYieldMsg()
    paid.CopyFrom(before)
    paid.goldTotalCount, paid.crystalsCount = before.goldTotalCount - gold, before.crystalsCount - crystals
    s.send(cs.S_CASTLE_YIELD, paid)
    after = cs.yield_msg(snap, templates, now)
    grade, attr_tech = int(target["BuildingGrade"]), target["MasterType"] == rules.TECH_ATTR
    # o efeito sai e volta: (dedução) o 1º 110 é o nível velho negativo (só turco: teknoloji_upgrade #3/#6, -324 e
    # +342 no Hero MATK 18 -> 19; no 0 -> 1 do inglês é -0 = 0). Só o novo quando o prédio nasce (8202)
    steps = ([(grade - 1, -1, paid)] if code == 8203 else []) + [(grade, 1, after)]
    if (tech := cs.gold_tech(templates, target)) is not None:
        # (visto) oficial_20261023-231733-1 #3971-#3978, Gold Production 0 -> 1: cada efeito com 110 (PropertyType1,
        # ouro do nível), 109 e 152; depois o 109 de sempre
        for g, sign, msg in steps:
            s.send(S_EFFECT, pb.PropertyUpdatedMsg(propertyType=tech[0], value=sign * tech[1] * g))
            s.send(cs.S_CASTLE_YIELD, msg)
            s.send(S_POLITICS, cs.politics_msg(snap, templates))
    elif attr_tech:
        # (só turco: teknoloji_upgrade #2-#10) cada efeito com 110 tipo 3 e 150 (o 4902 antes do 150 sai no
        # GameSession.send); o 109 final sai mesmo sem mudança. O cliente ignora o tipo 3 (PlayerEffectHelper)
        from .player import _army  # player importa castle (game)

        effect = templates.get("EffectTempInfos", int(target["Property1"])) or {}
        per, kind = int(effect.get("Property1", 0)), int(effect.get("PropertyType1", 0))
        troop = kind - (rules.ADV_TECH if kind >= 2 * rules.ADV_TECH else 0) in rules.TROOP_TECH
        for g, sign, _ in steps:
            s.send(S_EFFECT, pb.PropertyUpdatedMsg(propertyType=ATTR_EFFECT, value=sign * per * g))
            _army(s, cards=not troop)  # tropa: sem o 4902 (só turco: city_city_upgrade_academy_upgrade #52-#58)
    if after != paid or attr_tech:  # o oficial manda o segundo 109 só quando rendimento/teto/população mudam
        s.send(cs.S_CASTLE_YIELD, after)
    # nível do quartel que libera um tipo de tropa (NeedBuilding = o template novo): 100 com todas as tropas do
    # castelo e o tipo novo com 0, antes do 151 (tutorial_en #2208-#2213, Barracks Lvl. 4: 109, 100, 151, 4130, 83);
    # subir sem liberar nada não manda o 100 (tutorial_en #1577-#1581, Barracks Lvl. 2)
    fresh = [p for p in unlocked_pawns(snap, templates) if _need_building(templates, p.template_id) in {
        b.template_id for b in (building, *unlocked)}]  # fmt: skip
    if fresh:
        s.send(S_ARMY_PAWN, castle_pawns(snap, templates))
    s.send(S_ORDER_USE, cs.order_info(order, now))
    s.send(S_BUILDINGS, _buildings(s, [building, *unlocked]))
    # texto do oficial inglês (83, tutorial_en #594: "Town Hall has been upgraded to Lvl. 2")
    text = f"{target['BuildingName']} has been upgraded to Lvl. {target['BuildingGrade']}"
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


def _need_building(templates: GameTemplates, pawn_template: int) -> int:
    return int((templates.get("PawnTempInfos", pawn_template) or {}).get("NeedBuilding") or 0)


@router.on(8203)
async def building_upgrade(s: GameSession, msg: pb.BuildingOptionReqMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    building = next((x for x in snap.buildings if x.id == msg.buildingId and x.id), None)
    row = cs.template(s.ctx.templates, building.template_id) if building else None
    target = cs.template(s.ctx.templates, int(row["NextGradeTemplateId"] or 0)) if row else None
    if building is None or target is None:
        _refuse(s, 8203, "prédio inexistente ou no máximo", building=msg.buildingId)
        return
    await _build(s, 8203, building, target)


@router.on(8202)
async def building_create(s: GameSession, msg: pb.BuildingOptionReqMsg) -> None:
    """Só tecnologias (SeminaryFrameBottomView): constrói o nível 1 de um tipo que ainda não existe."""
    snap = s.snapshot
    assert snap is not None
    target = cs.first_grade(s.ctx.templates, msg.sonType)
    if target is None or target["MasterType"] not in cs.TECH or cs.by_son_type(snap, s.ctx.templates, msg.sonType):
        _refuse(s, 8202, "tipo inválido ou já existe", son_type=msg.sonType)
        return
    await _build(s, 8202, None, target)


@router.on(8279)
async def load_orders(s: GameSession, _: object) -> None:
    assert s.snapshot is not None
    s.send(S_ORDER_LIST, b.complete(cs.order_list(s.snapshot, s.ctx.clock.now())))


@router.on(5172)
async def order_quick(s: GameSession, msg: pb.BuildingReqMsg) -> None:
    """Acelera com diamante: 5 por 10 minutos (``cs.quick_cost``). index 1 = só diamante, 2 = vinculado primeiro,
    0 = privilégio VIP grátis (*(cliente)* ``QueueBar``/``SeminaryFrameBottomView`` mandam index 0 só com VIP:
    ``vip.free_cool``). orderId 0 = todas as filas de prédio."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    if msg.orderId:
        orders = [o for o in snap.orders if o.order_id == msg.orderId and o.remain(now) > 0]
    else:
        orders = [o for o in cs.orders_of(snap, cs.BUILD) if o.remain(now) > 0]
    cost = sum(cs.quick_cost(o.remain(now)) for o in orders)
    free = msg.index == 0 and free_cool(s, snap)
    valid = bool(orders) and (msg.index in (1, 2) or free)  # validar antes: pay() já debita
    ref = f"order:{msg.orderId}"
    entry = pay(c, cost, bind=msg.index == 2, reason="order_quick", ref=ref, now=now) if valid and not free else None
    if not valid or (entry is None and not free):
        _refuse(s, 5172, "sem ordem, VIP ou sem diamante", order=msg.orderId, index=msg.index, cost=cost)
        return
    for o in orders:
        o.begin_at, o.need_time = now, 0
    # (visto) tempinfos: Para1 1 = cs.BUILD (fila de prédio), Title "... 1 time" = 1 por ação;
    # (cliente) NewbieBaseActionMediator.as case 12 = QueueBar
    build = any(o.order_type == cs.BUILD for o in orders)
    quests = rules.quest_event(snap, s.ctx.templates, ACCELERATE, cs.BUILD, 1) if build else []
    await s.ctx.characters.save(c, *([entry] if entry else []), *orders, *quests)
    _send_player(s)
    from . import events  # handlers.events importa login, que importa este módulo

    # LeedTemp 15 "Consume Balens/Bound Balens": (visto, só turco: replay #1288-#1294) 3, 4152 (totalNum 25), 150,
    # 4434, 111, 102 e o 83 da devoção ("Your devotion level has increased to N.", tutorial_en #16); aqui o 83 vai
    # logo depois do 4152, como nos outros leeds
    # chamado aqui para sair antes do 111/102, como na captura; o gancho geral do on_packet (session.py) vê o leed
    # já feito no dia e não repete. VIP grátis (index 0) não gasta diamante: não conta
    if entry is not None:
        await events.leed_done(s, events.BALEN_LEED)
    # texto deduzido (sem fonte no cliente/captura)
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Cooldown removed."))
    s.send(S_ORDER_QUICK, pb.OrderQuickRspMsg(orderInfo=[cs.order_info(o, now) for o in orders]))
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(5175)
async def order_add(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Compra a segunda fila de prédios (395 diamantes; payType 0 = pode usar vinculado)."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    if sum(1 for _ in cs.orders_of(snap, cs.BUILD)) >= cs.BUILD_ORDER_LIMIT:
        _refuse(s, 5175, "limite de filas")
        return
    entry = pay(c, BUY_ORDER_PRICE, bind=msg.payType == 0, reason="order_add", ref="build_order", now=now)
    if entry is None:
        _refuse(s, 5175, "sem diamante")
        return
    order = cs.new_order(snap, cs.BUILD, now)
    await s.ctx.characters.save(c, entry, order)
    _send_player(s)
    s.send(S_ORDER_ADD, cs.order_info(order, now))


@router.on(8327)
async def gold_impose(s: GameSession, _: object) -> None:
    """Cobrança de ouro no conselho (LevyView): 901.Property1*6 + mina.Property1*3, 5 por dia,
    fila tipo 3 ocupada por 1 hora. (só turco: login.json/city) 46.620 = 7320*6 + 900*3; (visto)
    oficial_20261023-171155-1 #5876: 11.280 = 1880*6."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    council, mine = cs.by_son_type(snap, templates, cs.COUNCIL), cs.by_son_type(snap, templates, cs.MINE)
    cs.impose_order(snap, now)  # chegou ao 14 sem ``push_level`` (EXP de pacote, ``player.granted``): a fila nasce aqui
    order, used = cs.free_order(snap, cs.IMPOSE, now), cs.impose_used(snap.castle, s.ctx.clock.now())
    if council is None or order is None or used >= b.MAX_IMPOSE or c.grades < cs.IMPOSE_GRADE:
        _refuse(s, 8327, "sem conselho, fila ocupada, sem cobranças ou nível", used=used)
        return
    p1 = int((cs.template(templates, council.template_id) or {}).get("Property1", 0))
    mine_p1 = int((cs.template(templates, mine.template_id) or {}).get("Property1", 0)) if mine else 0
    gold = p1 * 6 + mine_p1 * 3
    cs.settle(snap, templates, now)  # antes de somar: a cobrança pode passar do teto
    c.gold += gold
    snap.castle.impose_used, snap.castle.imposed_at = used + 1, now
    order.begin_at, order.need_time = now, IMPOSE_COOLDOWN
    # (visto) tempinfos: 763 = tipo 42, Para1 0, "Collect Levy" no Town Hall; (cliente) case 16 = levyBtn
    quests = rules.quest_event(snap, templates, LEVY, 0, 1)  # cada cobrança conta 1 (dedução)
    await s.ctx.characters.save(c, snap.castle, order, *quests)
    # (visto) oficial_20261023-171155-1 #5875-#5880: 112 da missão 763, 109, 111, 151, 4242 e 83, com o texto
    # "Successfully levied 11,280 gold!"
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    castle_yield(s)
    text = f"Successfully levied {gold:,} gold!"
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_ORDER_USE, cs.order_info(order, now))  # antes do 4242: a LevyView redesenha nele
    s.send(S_IMPOSE, pb.GoldImposeMsg(leftImpose=used + 1, maxImpose=b.MAX_IMPOSE))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(5174)
async def transfer_energy(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Enche a energia de teleporte (TransferBuildFrame): (máximo - atual)/5 diamantes; payType 2 = vinculado."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, castle, now = snap.character, snap.castle, s.ctx.clock.now()
    top = cs.energy_max(s.ctx.templates)
    cost = (top - castle.energy) // 5
    entry = pay(c, cost, bind=msg.payType == 2, reason="transfer_energy", ref="castle", now=now) if cost > 0 else None
    if entry is None:
        _refuse(s, 5174, "energia cheia ou sem diamante", energy=castle.energy)
        return
    castle.energy = top
    await s.ctx.characters.save(c, castle, entry)
    _send_player(s)
    s.send(S_TRANSFER, pb.TransInfoMsg(currentEnergy=castle.energy, remainTime=0))


@router.on(5173)
async def transfer_cool(s: GameSession, _: pb.PayTypeMsg) -> None:
    # sem chamador no cliente decompilado e sem recarga de teleporte aqui: só devolve o estado
    assert s.snapshot is not None and s.snapshot.castle is not None
    s.send(S_TRANSFER, pb.TransInfoMsg(currentEnergy=s.snapshot.castle.energy, remainTime=0))


@router.on(8562)
async def castle_time_cancel(s: GameSession, _: object) -> None:
    """Cancela a trégua do castelo (buff 2001). ponytail: trégua ainda não existe; zera e confirma."""
    s.send(S_CASTLE_TIME, pb.BaseCastleMsg(defenceLefttime=0))


@router.on(8489)
async def seminary_bless(s: GameSession, _: object) -> None:
    """Bênção do seminário (``SeminaryBlessFrame``): gasta cristais e soma ``Blessing_Buffer`` até ``Blessing_Max``.

    Sempre responde 4391, também na recusa, com o valor atual: sem ele o cliente não reabre fechar e confirmar.
    O custo (``Blessing_Cast``) é do ConfigInfos; o ``Blessing_ItemId`` não entra, o botão só confere cristais."""
    assert s.snapshot is not None
    c, now = s.snapshot.character, s.ctx.clock.now()
    cost = _config(s, "Blessing_Cast", 2000)
    step = _config(s, "Blessing_Buffer", 10)
    top = _config(s, "Blessing_Max", 200)
    count = c.bless_count_today(now)
    if c.seminary_effect >= top or c.crystals < cost:
        s.log.info("8489 recusado", bencao=c.seminary_effect, cristais=c.crystals)
        s.send(S_BLESSING, pb.BlessingMsg(increase=c.seminary_effect, usedCount=count))
        return
    c.crystals -= cost
    c.seminary_effect = min(top, c.seminary_effect + step)
    c.seminary_count, c.seminary_day = count + 1, gameday.today(now)
    quests = rules.quest_event(s.snapshot, s.ctx.templates, rules.SEMINARY_CONDITION, 0, 1)  # missão 57 (8489)
    await s.ctx.characters.save(c, *quests)
    from . import events  # handlers.events importa login, que importa este módulo

    # LeedTemp 33 "Spin the Blessing Wheel" é esta bênção: (visto, só turco: city_city_upgrade #139-#140) 4152 antes
    # do 4391
    await events.leed_done(s, events.WHEEL_LEED)
    s.send(S_BLESSING, b.complete(pb.BlessingMsg(increase=c.seminary_effect, usedCount=c.seminary_count)))
    castle_yield(s)  # 109: o contador de cristais do cliente
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(s.snapshot)))
