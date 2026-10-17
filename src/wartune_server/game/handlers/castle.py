"""Castelo: prédios, tecnologias, filas de construção, cobrança de ouro e recursos (docs/castelo.md).

O upgrade (8203) e a construção de tecnologia (8202) são imediatos, como no oficial: o 4130 já sai
com o template novo e a fila fica ocupada ``UpgradeTime`` segundos (151). Toda validação é daqui:
dono do prédio, nível do jogador, pré-requisitos, fila livre e custo.
"""

from __future__ import annotations

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

S_PLAYER, S_CHAT, S_ALERT, S_QUESTS = 3, 83, 111, 112
S_BUILDINGS, S_ORDER_USE, S_ORDER_ADD, S_ORDER_QUICK, S_ORDER_LIST = 4130, 151, 104, 102, 4187
S_IMPOSE, S_TRANSFER, S_UNOCCUPY, S_CASTLE_TIME, S_ARMY_PAWN = 4242, 103, 108, 4452, 100
BUY_ORDER_PRICE = 100  # "mainBar.QueueBar.content" (QueueBar.buyQueueItem)
IMPOSE_GRADE, IMPOSE_COOLDOWN = 14, 3600  # LevyView: nível mínimo; captura: 151 com remainTime 3600
S_BLESSING = 4391  # BlessingMsg: bênção do seminário (8489)


def _send_player(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_PLAYER, b.complete(player_info(s, s.snapshot)))


def _buildings(s: GameSession, only: list[Building]) -> pb.BuildingInfoListMsg:
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    return b.buildings_msg(snap, snap.castle, s.ctx.templates, only, cs.impose_used(snap.castle, s.ctx.clock.now()))


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
    if after != paid:  # o oficial manda o segundo 109 só quando rendimento/teto/população mudam
        s.send(cs.S_CASTLE_YIELD, after)
    s.send(S_ORDER_USE, cs.order_info(order, now))
    s.send(S_BUILDINGS, _buildings(s, [building, *unlocked]))
    # tipo de tropa que este nível do quartel libera (NeedBuilding = o template novo) vem com 0; subir
    # sem liberar nada não manda o 100 (replay #649-#653, Kışla Lv.2)
    fresh = [p for p in unlocked_pawns(snap, templates) if _need_building(templates, p.template_id) in {
        b.template_id for b in (building, *unlocked)}]  # fmt: skip
    if fresh:
        s.send(S_ARMY_PAWN, castle_pawns(snap, templates, fresh))
    text = f"Geliştirilen Seviye: {target['BuildingName']} Lv.{target['BuildingGrade']}"
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
    """Acelera com diamante: 1 por 10 minutos. index 1 = só diamante, 2 = vinculado primeiro,
    0 = privilégio VIP grátis (sem VIP aqui: recusado). orderId 0 = todas as filas de prédio."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    if msg.orderId:
        orders = [o for o in snap.orders if o.order_id == msg.orderId and o.remain(now) > 0]
    else:
        orders = [o for o in cs.orders_of(snap, cs.BUILD) if o.remain(now) > 0]
    cost = sum(cs.quick_cost(o.remain(now)) for o in orders)
    valid = bool(orders) and msg.index in (1, 2)  # validar antes: pay() já debita
    ref = f"order:{msg.orderId}"
    entry = pay(c, cost, bind=msg.index == 2, reason="order_quick", ref=ref, now=now) if valid else None
    if entry is None:
        _refuse(s, 5172, "sem ordem, VIP ou sem diamante", order=msg.orderId, index=msg.index, cost=cost)
        return
    for o in orders:
        o.begin_at, o.need_time = now, 0
    await s.ctx.characters.save(c, entry, *orders)
    _send_player(s)
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Bekleme Süresi kaldırıldı."))
    s.send(S_ORDER_QUICK, pb.OrderQuickRspMsg(orderInfo=[cs.order_info(o, now) for o in orders]))


@router.on(5175)
async def order_add(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Compra a segunda fila de prédios (100 diamantes; payType 0 = pode usar vinculado)."""
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
    fila tipo 3 ocupada por 1 hora. Login.json/city: 46.620 = 7320*6 + 900*3."""
    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    council, mine = cs.by_son_type(snap, templates, cs.COUNCIL), cs.by_son_type(snap, templates, cs.MINE)
    order, used = cs.free_order(snap, cs.IMPOSE, now), cs.impose_used(snap.castle, s.ctx.clock.now())
    if council is None or order is None or used >= b.MAX_IMPOSE or c.grades < IMPOSE_GRADE:
        _refuse(s, 8327, "sem conselho, fila ocupada, sem cobranças ou nível", used=used)
        return
    p1 = int((cs.template(templates, council.template_id) or {}).get("Property1", 0))
    mine_p1 = int((cs.template(templates, mine.template_id) or {}).get("Property1", 0)) if mine else 0
    gold = p1 * 6 + mine_p1 * 3
    cs.settle(snap, templates, now)  # antes de somar: a cobrança pode passar do teto
    c.gold += gold
    snap.castle.impose_used, snap.castle.imposed_at = used + 1, now
    order.begin_at, order.need_time = now, IMPOSE_COOLDOWN
    await s.ctx.characters.save(c, snap.castle, order)
    castle_yield(s)
    text = f"{gold:,} Altın başarıyla alındı."
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


@router.on(5179)
async def unoccupy_wild_land(s: GameSession, _: pb.BuildingReqMsg) -> None:
    # terras selvagens são do mapa-múndi (outro sistema): nenhuma ocupada, posição vazia = nada a mostrar
    s.send(S_UNOCCUPY, pb.GiveupWildLandMsg(wildLandPos=""))


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
    c.seminary_count, c.seminary_day = count + 1, now.date().isoformat()
    await s.ctx.characters.save(c)
    s.send(S_BLESSING, b.complete(pb.BlessingMsg(increase=c.seminary_effect, usedCount=c.seminary_count)))
    castle_yield(s)  # 109: o contador de cristais do cliente
