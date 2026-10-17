"""Mochila e itens: mover (5005), usar (5006), vender (5007/8624), arrumar (8220), descartar (8346),
travar (8809), cristal (8484), espaços (5010/8819), ver equipamento de outro (8199), baú de campanha
(5129). Ver ``docs/itens.md``.
"""

from __future__ import annotations

import random
import re
from datetime import timedelta

from google.protobuf.message import Message

from ...domain.models import BagType, Hero, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from ...templates.repository import Row
from .. import bag, rules
from ..builders import login as b
from ..builders.player import fashion_book, item_info, item_moved
from ..router import router
from ..session import GameSession
from . import fashion
from .player import CURRENCIES, S_ALERT, S_CHAT, S_ITEMS, _army, _player, castle_yield
from .shop import send, send_blood

S_DETAIL, S_RENTAL, S_DROP_FAIL = 4125, 4709, 4268
BOX, USE, GEM_BOX, BLOOD = "298", "203", "206", "209"  # ItemTempInfo.SonType usáveis
STORE_STONE = 208014  # Şeytan Kristali (SonType 293): Property1 = EXP do cristal (8484)
STORE_GRADE = "15"  # UpGradeTempInfos.Types do cristal; Data = EXP total do nível
BAG_ROW, BAG_MAX = 7, 175  # 5010 compra de 7 em 7 até 175 espaços (PlayerInfo.PLAYER_BAG_MAX)
MOVABLE = (BagType.STORE, BagType.BAG, BagType.RUNE, BagType.HONOR, BagType.HERO)
STACKABLE = (BagType.STORE, BagType.BAG)
# 203 por Property1 (Property2 = quantidade): campo do personagem e nome no texto do oficial
USE_KINDS = {1: ("gold", "Altın"), 3: ("point", "Elmas"), 4: ("gift_token", "Bağlı Elmas"), 5: ("weary", "Beden")}
USE_KINDS |= {6: ("repute", "Prestij"), 7: ("gp", "Lord EXP"), 10: ("strategy", "Ruh")}
GEM_BOX_NAME = re.compile(r"Değerli Taş Kutusu Lv\.(\d)(?:-(\d))?$")


def _row(s: GameSession, item: Item) -> Row | None:
    return s.ctx.templates.get("ItemTempInfos", item.template_id)


def _hero(snap: PlayerSnapshot, hero_id: int) -> Hero | None:
    return next((h for h in snap.heroes if h.id == hero_id), None)


def _consume(snap: PlayerSnapshot, item: Item, n: int) -> tuple[list[Item], list[Item]]:
    return ([], [item]) if bag.take_one(snap, item, n) else ([item], [])


def _send_items(s: GameSession, changed: list[Item], gone: list[Item]) -> None:
    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))


# --- 5005 mover ---


def _place_ok(s: GameSession, item: Item, bag_type: int, obj: int, pos: int) -> bool:
    """O item pode ficar ali? Mochila e bancada: faixa de posição; bolsas do herói: o espaço do
    SonType (``GoodsSonType.getSonTypePos``) e classe/sexo/nível (``GoodsCheck``)."""
    snap = s.snapshot
    assert snap is not None
    if bag_type == BagType.BAG:
        return obj == 0 and 0 <= pos < bag.capacity(snap.character, s.ctx.clock.now())
    if bag_type == BagType.STORE:
        return obj == 0 and 0 <= pos < bag.STORE_SIZE
    hero, row = _hero(snap, obj), _row(s, item)
    if hero is None or row is None or not bag.hero_slot_ok(snap, row, bag_type, pos):
        return False
    tpl = s.ctx.templates.hero(hero.template_id)
    return bag.fits_hero(snap, row, tpl.job, tpl.sex)


@router.on(5005)
async def bag_move(s: GameSession, msg: pb.ItemReqMsg) -> None:
    """Move entre mochila (1), bancada (0) e as bolsas do herói (2 runas, 3 medalha, 4 equipamento).
    Destino ocupado: empilha se for o mesmo item, senão troca (o outro precisa caber na origem)."""
    snap = s.snapshot
    assert snap is not None
    begin = (msg.beginBagType, msg.beginObjId, msg.beginPos)
    end_bag, end_obj, end_pos = msg.endBagType, msg.endObjId, msg.endPos
    item = bag.at(snap, *begin)
    if begin[0] == BagType.STORE and end_bag == BagType.BAG and bag.at(snap, end_bag, 0, end_pos) is not None:
        # a bancada devolve sempre com endPos 0: o servidor escolhe o primeiro espaço livre
        free = bag.free_positions(snap, s.ctx.clock.now())
        end_pos = free[0] if free else -1
    end = (end_bag, end_obj, end_pos)
    other = bag.at(snap, *end)
    ok = item is not None and begin[0] in MOVABLE and end_bag in MOVABLE and begin != end
    ok = ok and item is not None and _place_ok(s, item, *end)
    stack = (
        ok
        and item is not None
        and other is not None
        and other.template_id == item.template_id
        and {begin[0], end_bag} <= set(STACKABLE)
        and other.count < bag.max_count(s.ctx.templates, item.template_id)
    )
    if ok and other is not None and not stack:
        ok = _place_ok(s, other, *begin)
    if not ok or item is None:
        s.log.info("5005 recusado", pedido=str(msg))
        return

    gone: tuple[Item, ...] = ()
    if stack and other is not None:
        use = min(item.count, bag.max_count(s.ctx.templates, item.template_id) - other.count)
        other.count += use
        if bag.take_one(snap, item, use):
            gone = (item,)
        first, second = (None if gone else item), other
    else:
        item.bag_type, item.object_id, item.pos, item.is_new = *end, False
        if other is not None:
            other.bag_type, other.object_id, other.pos = begin
        first, second = other, item
    book = fashion.register(snap, s.ctx.templates, item.template_id) if end_bag == BagType.HERO else None
    kept = (i for i in (item, other, book) if i is not None and i not in gone)
    await s.ctx.characters.save(*kept, delete=gone)

    _player(s)
    _army(s)
    s.send(S_ITEMS, item_moved(*begin, first, s.player_id))
    s.send(S_ITEMS, item_moved(*end, second, s.player_id))
    if book is not None:
        send(s, fashion.S_FASHION_BOOK, fashion_book(snap, s.ctx.templates))


# --- 5006 usar ---


@router.on(5006)
async def use_item(s: GameSession, msg: pb.ItemUseMsg) -> None:
    """Usa um item da mochila conforme o SonType: pacote (298), recurso (203), caixa de pedras
    (206) ou poção de HP (209). Os outros dependem de sistemas que não existem e são recusados."""
    snap = s.snapshot
    assert snap is not None
    item = bag.at(snap, BagType.BAG, 0, msg.pos) if msg.bagType == BagType.BAG else None
    row = _row(s, item) if item is not None else None
    if item is None or row is None or item.is_locked or snap.character.grades < int(row.get("NeedGrades") or 0):
        s.log.info("5006 recusado", pedido=str(msg))
        return
    n = max(1, min(msg.count, item.count))
    use = {BOX: _open_box, USE: _use_resource, GEM_BOX: _open_gem_box, BLOOD: _use_blood}.get(row.get("SonType", ""))
    if use is None or not await use(s, item, row, n):
        s.log.info("5006 recusado", pedido=str(msg), item=item.template_id, sontype=row.get("SonType"))


async def _open_box(s: GameSession, box: Item, row: Row, _: int) -> bool:
    """Pacote (SonType 298): troca o item pelo GradeDrop dele (Property1 = DropId)."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates
    drops = list(templates.find("GradeDrop", DropId=row.get("Property1")))
    ids = [int(d["TemplateId"]) for d in drops]
    known = all(t in CURRENCIES or (t > 0 and templates.get("ItemTempInfos", t)) for t in ids)
    goods = [d for d in drops if int(d["TemplateId"]) > 0]
    fits = len(bag.in_bag(snap)) - 1 + len(goods) <= bag.capacity(c, s.ctx.clock.now())
    if not (drops and known and fits):
        return False

    snap.items.remove(box)  # antes de qualquer await: o próximo pacote já não acha a caixa
    new: list[Item] = []
    free = iter(sorted({*bag.free_positions(snap, s.ctx.clock.now())}))
    for d in goods:
        item = bag.new_item(snap, templates, int(d["TemplateId"]), int(d["Data"]))
        item.pos = next(free)
        snap.items.append(item)
        new.append(item)
    point = gift = 0
    for d in drops:
        if (field := CURRENCIES.get(int(d["TemplateId"]))) in ("point", "gift_token"):
            point, gift = (point + int(d["Data"]), gift) if field == "point" else (point, gift + int(d["Data"]))
        elif field is not None:
            setattr(c, field, getattr(c, field) + int(d["Data"]))
    ledger = (
        cash.change(c, point, gift, "item", f"item:{box.template_id}", s.ctx.clock.now()) if point or gift else None
    )
    await s.ctx.characters.save(c, *new, *([ledger] if ledger else []), delete=(box,))

    s.send(S_ITEMS, item_moved(BagType.BAG, 0, box.pos, None, s.player_id))
    _army(s)
    if -100 in ids:
        castle_yield(s)
    s.send(S_ITEMS, bag.moved(new, s.player_id))

    def label(d: Row) -> str:
        name = (templates.get("ItemTempInfos", int(d["TemplateId"])) or {}).get("TemplateName", d["TemplateId"])
        return f"{name} {int(d['Data']):,}" if int(d["TemplateId"]) < 0 else f"{name} x{d['Data']}"

    text = "Kazanılan:" + ", ".join(label(d) for d in reversed(drops))  # o oficial lista do fim para o começo
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _player(s)
    return True


async def _use_resource(s: GameSession, item: Item, row: Row, n: int) -> bool:
    """Recurso (SonType 203): Property1 = tipo, Property2 = quantidade por unidade."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    c, now = snap.character, s.ctx.clock.now()
    kind = USE_KINDS.get(int(row.get("Property1") or 0))
    amount = int(row.get("Property2") or 0) * n
    if kind is None or amount <= 0:
        return False  # cristal, guilda, VIP, buffs...: sistemas que não existem aqui
    field, label = kind
    if field == "weary":
        # ponytail: sem o teto diário de poções de Beden; só o limite do personagem
        amount = min(amount, c.weary_limit - c.weary)
        if amount <= 0:
            return False
    changed, gone = _consume(snap, item, n)  # antes de qualquer await
    extra: list[object] = []
    gained = 0
    if field == "gp":
        gained = rules.add_gp(snap, s.ctx.templates, amount)
        extra.append(snap.leader)
    elif field in ("point", "gift_token"):
        point, gift = (amount, 0) if field == "point" else (0, amount)
        extra.append(cash.change(c, point, gift, "item", f"item:{item.template_id} x{n}", now))
    else:
        setattr(c, field, getattr(c, field) + amount)
    await s.ctx.characters.save(c, *changed, *extra, delete=tuple(gone))

    _send_items(s, changed, gone)
    text = f"Kazanılan:{label} x{amount}" if field == "weary" else f"Tebrikler! Kazanılan:{label} x{amount}"
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    if field == "gold":
        castle_yield(s)
        return True
    _player(s)
    if field == "gp":
        send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"{amount:,} EXP kazanıldı"))
        if gained:
            _army(s)
    return True


async def _open_gem_box(s: GameSession, box: Item, row: Row, n: int) -> bool:
    """Caixa de pedras "Değerli Taş Kutusu Lv.N" (ou Lv.A-B): uma pedra aleatória do nível por caixa,
    entre as 8 do ``TransformInfos`` daquele nível. As outras caixas 206 têm o conteúdo só na descrição
    (Property1 = o próprio id, sem tabela de drop nos templates) e são recusadas."""
    snap = s.snapshot
    assert snap is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    m = GEM_BOX_NAME.match(row.get("TemplateName", ""))
    if m is None or "*" in row.get("Description", ""):
        return False
    low, high = int(m[1]), int(m[2] or m[1])
    stones: dict[int, int] = {}
    for _ in range(n):
        level = templates.get("TransformInfos", random.randint(low, high), key="TransformId")
        if level is None:
            return False
        tid = int(level[f"Material{random.randint(1, 8)}"])
        stones[tid] = stones.get(tid, 0) + 1
    if not bag.fits(snap, templates, stones.items(), now):
        return False
    changed, gone = _consume(snap, box, n)
    got = [i for tid, count in stones.items() for i in bag.add(snap, templates, tid, count, now)]
    await s.ctx.characters.save(*changed, *got, delete=tuple(gone))

    _send_items(s, changed, gone)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    text = "Kazanılan:" + ", ".join(f"{bag.name(templates, tid)} x{count}" for tid, count in stones.items())
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    _player(s)
    send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    return True


async def _use_blood(s: GameSession, item: Item, row: Row, n: int) -> bool:
    """Poção de HP (SonType 209): Property1 vai para a reserva ``blood`` do líder."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    leader = snap.leader
    changed, gone = _consume(snap, item, n)
    leader.blood += int(row.get("Property1") or 0) * n
    leader.blood_id = item.template_id
    await s.ctx.characters.save(leader, *changed, delete=tuple(gone))

    _send_items(s, changed, gone)
    send_blood(s)
    _army(s)
    _player(s)
    return True


# --- vender ---


def sell_gold(row: Row, item: Item, count: int) -> int:
    """``GoodsHelp.getSellGold``: SellGold + 70% do ouro gasto no reforço, por unidade."""
    ng, profile = int(row.get("NeedGrades") or 0), int(row.get("Profile") or 0)
    spent = sum(1.5 ** (ng // 10 + 1) * (profile + 1) * i**2.2 * 5 + 500 for i in range(1, item.strengthen_grade + 1))
    return int(int(row.get("SellGold") or 0) + 0.7 * spent) * count


async def _sell(s: GameSession, wanted: list[tuple[int, int]], code: int) -> None:
    """Vende (posição, quantidade) da mochila. Item travado, com pedra ou de preço 0 não sai."""
    snap = s.snapshot
    assert snap is not None
    plan: list[tuple[Item, int, int]] = []
    for pos, count in wanted:
        item = bag.at(snap, BagType.BAG, 0, pos)
        row = _row(s, item) if item is not None else None
        if item is None or row is None or item in (p[0] for p in plan):
            break
        n = item.count if count <= 0 else count
        gold = sell_gold(row, item, n)
        if item.is_locked or any(j > 0 for j in item.joins) or not 0 < n <= item.count or gold <= 0:
            break
        plan.append((item, n, gold))
    else:
        if plan:
            changed: list[Item] = []
            gone: list[Item] = []
            for item, n, gold in plan:
                snap.character.gold += gold
                (gone if bag.take_one(snap, item, n) else changed).append(item)
            await s.ctx.characters.save(snap.character, *changed, delete=tuple(gone))
            _send_items(s, changed, gone)
            castle_yield(s)
            return
    s.log.info(f"{code} recusado", itens=wanted)


@router.on(5007)
async def bag_sell(s: GameSession, msg: pb.ItemReqMsg) -> None:
    await _sell(s, [(msg.beginPos, 0)], 5007)


@router.on(8624)
async def bag_batch_sell(s: GameSession, msg: pb.ItemSellReqMsg) -> None:
    await _sell(s, [(i.pos, i.count) for i in msg.selledItemInfos[:200]], 8624)


# --- arrumar, descartar, travar ---


@router.on(8220)
async def bag_arrange(s: GameSession, msg: pb.ArrangeReq) -> None:
    """Arrumar a mochila: o cliente calcula a ordem (``arrangeInfo`` velho -> novo) e, com
    ``isStackItem``, o servidor junta as pilhas incompletas do mesmo item."""
    snap = s.snapshot
    assert snap is not None
    items = bag.in_bag(snap)
    by_pos = {i.pos: i for i in items}
    moves = {a.oldplace: a.newplace for a in msg.arrangeInfo}
    cap = bag.capacity(snap.character, s.ctx.clock.now())
    final = {pos: moves.get(pos, pos) for pos in by_pos}
    valid = msg.bagType == BagType.BAG and len(moves) == len(msg.arrangeInfo) and set(moves) <= set(by_pos)
    if not valid or len(set(final.values())) != len(final) or any(not 0 <= p < cap for p in final.values()):
        s.log.info("8220 recusado", pedido=str(msg))
        return
    for pos, item in by_pos.items():
        item.pos = final[pos]
    gone: list[Item] = []
    if msg.isStackItem:
        for item in sorted(items, key=lambda i: i.pos):
            top = bag.max_count(s.ctx.templates, item.template_id)
            if item in gone or item.count >= top:
                continue
            for other in sorted(items, key=lambda i: i.pos):
                if other is item or other in gone or other.pos < item.pos or other.template_id != item.template_id:
                    continue
                if other.is_locked != item.is_locked:
                    continue
                use = min(top - item.count, other.count)
                item.count += use
                if bag.take_one(snap, other, use):
                    gone.append(other)
    kept = sorted((i for i in items if i not in gone), key=lambda i: i.pos)
    if gone:  # ponytail: depois de juntar pilhas, fecha os buracos na mesma ordem (dedução)
        for pos, item in enumerate(kept):
            item.pos = pos
    await s.ctx.characters.save(*kept, delete=tuple(gone))
    old = [Item(0, 0, pos=p) for p in by_pos if p not in {i.pos for i in kept}]
    _send_items(s, kept, old)


@router.on(8346)
async def bag_remove(s: GameSession, msg: pb.ItemRemoveMsg) -> None:
    # o cliente só manda para tirar item vencido (validDate); aqui nenhum item tem validade
    s.log.info("8346 recusado: item sem validade", pedido=str(msg))


LOCK_BAGS = {1: BagType.BAG, 3: BagType.HERO, 4: BagType.HONOR}  # LockAndUnlockMsg.opType


@router.on(8809)
async def lock_item(s: GameSession, msg: pb.LockAndUnlockMsg) -> None:
    """Trava/destrava (item travado não é vendido nem consumido)."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    bag_type = LOCK_BAGS.get(msg.opType)
    obj = 0 if bag_type == BagType.BAG else snap.leader.id or 0
    item = bag.at(snap, bag_type, obj, msg.itemPos) if bag_type is not None else None
    if item is None:
        s.log.info("8809 recusado", pedido=str(msg))  # opType 2 = mascote: não existe
        return
    item.is_locked = not item.is_locked
    await s.ctx.characters.save(item)
    _send_items(s, [item], [])


# --- cristal (Şeytan Kristali) ---


@router.on(8484)
async def use_store(s: GameSession, msg: pb.ItemUseStoreReqMsg) -> None:
    """Gasta ``count`` Şeytan Kristali no cristal do jogador (``storeGp``/``storeGrade``)."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates
    row = templates.get("ItemTempInfos", STORE_STONE)
    if row is None or not 0 < msg.count <= bag.count_of(snap, STORE_STONE):
        s.log.info("8484 recusado", pedido=str(msg))
        return
    changed, gone = bag.take(snap, STORE_STONE, msg.count)
    c.store_gp += int(row.get("Property1") or 1) * msg.count
    levels = templates.find("UpGradeTempInfos", Types=STORE_GRADE)
    c.store_grade = max((int(r["Grades"]) for r in levels if int(r["Data"]) <= c.store_gp), default=0)
    await s.ctx.characters.save(c, *changed, delete=tuple(gone))
    _send_items(s, changed, gone)
    _player(s)


# --- espaços da mochila ---


def bag_row_cost(index: int) -> int:
    """Elmas da linha ``index`` (0 = primeira comprada), ``BagBuyFrame``: 10, 20 ... 100 e depois 100."""
    return (index + 1) * 10 if index < 10 else 100


@router.on(5010)
async def bag_buy(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Compra ``property1`` linhas de 7 espaços; a resposta é o PlayerMsg com o bagCount novo."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    rows, first = msg.property1, c.bag_count // BAG_ROW
    ledger = None
    if rows > 0 and bag.BAG_BASE + c.bag_count + rows * BAG_ROW <= BAG_MAX:
        cost = sum(bag_row_cost(i) for i in range(first, first + rows))
        ledger = cash.pay(c, cost, msg.payType, "bag", f"bag:+{rows * BAG_ROW}", now)
    if ledger is None:
        s.log.info("5010 recusado", pedido=str(msg))
        return
    c.bag_count += rows * BAG_ROW
    await s.ctx.characters.save(c, ledger)
    _player(s)


def _rental_prices(s: GameSession) -> dict[str, int]:
    row = next(s.ctx.templates.find("ConfigInfos", ConfigName="rental_bag_day_cost"), None)
    text = row["ConfigValue"] if row else ""
    return {d: int(v) for d, v in (p.split(",") for p in text.split("|") if "," in p)}


@router.on(8819)
async def rental_bag(s: GameSession, msg: pb.RentalBagOpReqMsg) -> None:
    """Aluga a mochila grande (217 espaços) por ``param2`` dias; ``param1`` = payType.
    Preço: ``rental_bag_day_cost`` × 2 páginas (``RentalBagAlertFrame``)."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    price = _rental_prices(s).get(msg.param2)
    ledger = None
    if msg.opType == 1 and price is not None:
        ledger = cash.pay(c, price * 2, msg.param1, "rental_bag", f"days:{msg.param2}", now)
    if ledger is None:
        s.log.info("8819 recusado", pedido=str(msg))
        return
    start = c.rental_bag_until if bag.rental_active(c, now) and c.rental_bag_until else now
    c.rental_bag_until = start + timedelta(days=int(msg.param2))
    await s.ctx.characters.save(c, ledger)
    _player(s)
    out = pb.RentalBagOpResMsg(opType=1, rentalBagTime=b.fmt_time(c.rental_bag_until), status=1)
    send(s, S_RENTAL, out)


# --- ver equipamento de outro jogador ---


def _copy[M: Message](src: Message, dst: M) -> M:
    """Copia os campos escalares de mesmo nome (ItemInfoMsg -> SimpleItemInfoMsg etc.)."""
    names = {f.name for f in dst.DESCRIPTOR.fields if f.message_type is None and not f.is_repeated}
    for f, value in src.ListFields():
        if f.name in names:
            setattr(dst, f.name, value)
    return dst


@router.on(8199)
async def equip_look(s: GameSession, msg: pb.DetailReqMsg) -> None:
    """Ficha de outro jogador (4125): equipamento do líder e os atributos dele."""
    other = s.ctx.online.get(msg.otherId)
    try:
        snap = other.snapshot if other is not None and other.snapshot else await s.ctx.characters.snapshot(msg.otherId)
    except Exception:  # noqa: BLE001  (id que não existe)
        snap = None
    if snap is None or snap.leader is None:
        s.log.info("8199 recusado: jogador não encontrado", pedido=str(msg))
        return
    leader, cid = snap.leader, snap.character.id or 0
    out = pb.DetailRspMsg(otherId=cid, serverName=snap.server.name, hideFashion=leader.hide_fashion)
    for item in snap.items:
        if item.bag_type in rules.HERO_BAGS and item.object_id == leader.id:
            out.item.append(_copy(item_info(item, cid), pb.SimpleItemInfoMsg()))
    hero = _copy(b.hero_info(leader, cid, rules.leader_stats(snap, s.ctx.templates)), pb.SimpleHeroMsg())
    hero.tempateId, hero.nickName = leader.template_id, snap.character.nickname or ""
    out.army.CopyFrom(pb.SimpleArmyMsg(playerId=cid, nickName=snap.character.nickname or "", simpleHero=hero))
    out.army.storeGrade, out.army.appellid = snap.character.store_grade, snap.character.appell_id
    send(s, S_DETAIL, out)


# --- baú caído na campanha ---


@router.on(5129)
async def drop_take(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    # os baús que caem no mapa de campanha (4267) dependem dos drops da campanha, que ainda não
    # existem: o 4268 diz ao cliente que o baú não tem nada e ele limpa o nó (``__resetFallHandler``)
    s.log.info("5129: baú sem drop", sinal=msg.paraString1)
    send(s, S_DROP_FAIL, pb.BattleReportMsg(signId=msg.paraString1))
