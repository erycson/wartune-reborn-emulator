"""Mochila e itens: mover (5005), usar (5006), vender (5007/8624), arrumar (8220), descartar (8346),
travar (8809), cristal (8484), espaços (5010/8819), ver equipamento de outro (8199), baú de campanha
(5129). Ver ``docs/itens.md``.
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timedelta

from google.protobuf.message import Message

from ...domain import gameday
from ...domain.models import BagType, EventState, Hero, Item, Pawn, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from ...services.ledger import item_entry
from ...templates.repository import Row
from .. import bag, buffs, daily, monsters, rewards, rules, space, taxas
from .. import events as ev
from ..builders import login as b
from ..builders.army import castle_pawns
from ..builders.player import fashion_book, item_info, item_moved
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from . import fashion
from .player import (
    CURRENCIES,
    S_ALERT,
    S_CASTLE_PAWNS,
    S_CHAT,
    S_ITEMS,
    _army,
    _player,
    alert,
    balens_changed,
    exp_text,
    hp_pack,
    push_level,
)
from .shop import send, send_blood

S_DETAIL, S_RENTAL, S_DROP_FAIL, S_FOG = 4125, 4709, 4268, 4939
S_GRADE_BOXES = 2  # U_C_PLAYER_GRADE (NoviceReqMsgMsg): só o gradeProcess; o cliente não lê, o 3 seguinte leva igual
S_COPIES = 4240  # MultiCampaignEnterCountMsg: entradas de campanha em grupo (The Empire Crusade)
S_EFFECT, S_ITEM_BUFFER = 110, 4188  # PropertyUpdatedMsg e ItemBufferRspMsg dos pergaminhos de efeito
BOX, USE, GEM_BOX, BLOOD, EFFECT = "298", "203", "206", "209", "201"  # ItemTempInfo.SonType usáveis
MOUNT_CARD = "218"  # carta de montaria
POWER_CARD = "600"  # carta de poder (systems.CARD_ITEM)
PROTECTION = buffs.PROTECTION  # City Protection Token (208006): o cliente conta pelo 4452 e para com o 8562
S_CASTLE_TIME = 4452
STORE_STONE = 208014  # Soul Crystal (SonType 293): Property1 = EXP do cristal (8484)
STORE_GRADE = "15"  # UpGradeTempInfos.Types do cristal; Data = custo do nível anterior a este
S_STORE_DONE = 4385  # 0x1121 ItemUseStoreRspMsg (result 1); o cliente inglês não escuta este código
BAG_ROW, BAG_MAX = 7, 175  # 5010 compra de 7 em 7 até 175 espaços (PlayerInfo.PLAYER_BAG_MAX)
MOVABLE = (BagType.STORE, BagType.BAG, BagType.RUNE, BagType.HONOR, BagType.HERO, BagType.GUILD, BagType.PET_EQUIP)
STACKABLE = (BagType.STORE, BagType.BAG, BagType.GUILD)
GUILD_ROW, GUILD_FULL = 5, 56  # ConsortiaModel.currentCasecellNum: storeLevel*5, a grade 7x8 inteira no nível 10
# PlayerBagCellClickMediator/PlayerBagCellDropMediator/PlayerEquipBagCellDropMediator: item livre que vai para o
# equipamento (4) ou as runas (2) pede "This operation will change this item to become bound" (Store.IntensifyView.Tip);
# no mascote (26) o PetBagCellDropMediator pede o prompt03 ("The sylph will become bound after putting equipment on")
BINDS_ON_EQUIP = (BagType.HERO, BagType.RUNE, BagType.PET_EQUIP)
# 203 por Property1 (Property2 = quantidade): campo do personagem e nome no texto do oficial
# nomes do inglês: ItemTempInfo -100/-400/-500/-300/-700 e language.txt (Honor, Multi-player Dungeon); Stamina: a
# captura EN escreve "deducted 20 stamina" na entrada da masmorra
USE_KINDS = {1: ("gold", "Gold"), 3: ("point", "Balens"), 4: ("gift_token", "Bound Balens"), 5: ("weary", "Stamina")}
# Honor Certificate (2030601-3, "Provides an honor increase"): a honra do cliente é o geste (thane.honer = geste em
# PlayerManager e ThaneInfoHelper; a loja confere NeedGeste com ela); repute é outro valor
USE_KINDS |= {6: ("geste", "Honor"), 7: ("gp", "Hero EXP"), 10: ("strategy", "Daru")}  # 191924 #1721
USE_KINDS[15] = ("copies", "Multi-player Dungeon")  # The Empire Crusade (2032101): +1 entrada de campanha em grupo
# Kyanite Pack (11, cristal do castelo) e Contribution Badge (8, contribuição da guilda): o campo pelo nome do item;
# (visto 183522 #15184 "Received:Guild Contribution x1350" de 27 badges); TODO(inventado): o texto do Kyanite
USE_KINDS |= {8: ("consortia_offer", "Guild Contribution"), 11: ("crystals", "Kyanite")}
S_CONSORTIA_OFF = 42  # contribuição da guilda mudou (ConsortiaMsg result), como na doação (guild/upgrades.py)
# Medallion (16): "permanently increase Honor by 500, unaffected by the daily Honor gain limit" -> geste, como o 6
USE_KINDS[16] = ("geste", "Honor")
ONE_CONTRACT = 14  # Pocket Market... (Property2 horas, Property3 = o contrato do rei 1-6)
TROOPS = 9  # Huntera Lvl. 5...: "Contains 200 Huntera" (Property2 soldados do PawnTempInfos Property3)
ITEM_EXP_KEY = "item_exp"  # event_state diário: EXP de herói vinda de itens (203 tipo 7) hoje
ITEM_EXP_FULL = "Today's EXP item limit has been reached."  # TODO(inventado): sem texto no cliente nem captura
VIP_CARD = 12  # VIP Trial Card (2031201): Property3 = horas de VIP (handlers/vip.use_trial_card)
COVENANT = 13  # Spirit Covenant (2031301): Property2 = horas dos contratos 1-6 (handlers/vip.use_covenant)
# Caixas de pedras (206, uma pedra aleatória por caixa): id -> (nível mínimo, máximo). É por id, não pelo nome,
# porque o nome depende do idioma ("Lvl. N Gem Pack" no inglês). O 2060006 fica de fora de propósito: são duas
# pedras Lv.3 e chance de Lv.4.
GEM_BOX_LEVELS = {
    2060008: (1, 1),
    2060009: (2, 2),
    2060010: (3, 3),
    2060011: (4, 4),
    2060012: (5, 5),
    2060013: (1, 3),
    2060014: (1, 5),
    2060020: (3, 5),
}


def _row(s: GameSession, item: Item) -> Row | None:
    return s.ctx.templates.get("ItemTempInfos", item.template_id)


def _hero(snap: PlayerSnapshot, hero_id: int) -> Hero | None:
    return next((h for h in snap.heroes if h.id == hero_id), None)


def _consume(snap: PlayerSnapshot, item: Item, n: int) -> tuple[list[Item], list[Item]]:
    return ([], [item]) if bag.take_one(snap, item, n) else ([item], [])


def _send_items(s: GameSession, changed: list[Item], gone: list[Item]) -> None:
    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))


# --- 5005 mover ---


def _guild_cells(s: GameSession) -> int:
    mine = s.ctx.guilds.of(s.player_id)
    level = mine[0].store_level if mine else 0
    return GUILD_FULL if level >= 10 else level * GUILD_ROW


def _place_ok(s: GameSession, item: Item, bag_type: int, obj: int, pos: int) -> bool:
    """O item pode ficar ali? Mochila e bancada: faixa de posição; bolsas do herói: o espaço do
    SonType (``GoodsSonType.getSonTypePos``) e classe/sexo/nível (``GoodsCheck``)."""
    snap = s.snapshot
    assert snap is not None
    if bag_type == BagType.BAG:
        return obj == 0 and 0 <= pos < bag.capacity(snap.character, s.ctx.clock.now())
    if bag_type == BagType.STORE:
        return obj == 0 and 0 <= pos < bag.STORE_SIZE
    if bag_type == BagType.GUILD:
        return obj == 0 and 0 <= pos < _guild_cells(s)
    if bag_type == BagType.PET_EQUIP:  # o cliente não confere qualidade nem nível (o prompt01 "Rare or above" é morto)
        row = _row(s, item)
        mine = any(p.id == obj for p in snap.pets)
        return mine and row is not None and bag.hero_slot_ok(snap, row, bag_type, pos)
    hero, row = _hero(snap, obj), _row(s, item)
    if hero is None or row is None or not bag.hero_slot_ok(snap, row, bag_type, pos):
        return False
    tpl = s.ctx.templates.hero(hero.template_id)
    return bag.fits_hero(snap, row, tpl.job, tpl.sex)


BENCH_FROM = "bench_from"  # EventState: item -> [bagType, objectId, pos] de onde o herói o mandou para a bancada


def _bench_from(snap: PlayerSnapshot) -> dict[str, list[int]]:
    st = ev.peek(snap, BENCH_FROM)
    return json.loads(st.text) if st and st.text else {}


def _set_bench_from(snap: PlayerSnapshot, benched: dict[str, list[int]], now: datetime) -> EventState:
    st = ev.state(snap, BENCH_FROM, now)
    st.text, st.updated_at = json.dumps(benched), now
    return st


@router.on(5005)
async def bag_move(s: GameSession, msg: pb.ItemReqMsg) -> None:
    """Move entre mochila (1), bancada (0), armazém da guilda (6), as bolsas do herói (2 runas, 3 medalha,
    4 equipamento) e o equipamento do mascote (26). Na 26 o mascote vem no ``objectId`` (``PetBagCellClickMediator``
    manda ``endObjId`` 0; ``PetEquipBagCellDropMediator`` manda o id nos dois).
    Destino ocupado: empilha se for o mesmo item, senão troca (o outro precisa caber na origem). Juntar livre com
    vinculado vincula a pilha, e equipar vincula o item (o cliente já pediu a confirmação).
    (visto) inglês: o equipamento que veio do herói para a bancada volta para o corpo dele quando sai da bancada
    (``endBagType`` 1: 153200 #815, 231733 #294/#1399/#3357/#4804, oficial_encantar #234/#290, tutorial_en #3217)."""
    snap = s.snapshot
    assert snap is not None
    pet = msg.objectId
    begin = (msg.beginBagType, msg.beginObjId or (pet if msg.beginBagType == BagType.PET_EQUIP else 0), msg.beginPos)
    end_bag, end_obj, end_pos = msg.endBagType, msg.endObjId, msg.endPos
    if end_bag == BagType.PET_EQUIP and not end_obj:
        end_obj = pet
    item = bag.at(snap, *begin)
    benched = _bench_from(snap)
    back = benched.get(str(item.id or 0)) if item is not None and begin[0] == BagType.STORE else None
    if back is not None and end_bag == BagType.BAG and bag.at(snap, *back) is None:
        end_bag, end_obj, end_pos = back[0], back[1], back[2]
    if begin[0] == BagType.STORE and end_bag == BagType.BAG and bag.at(snap, end_bag, 0, end_pos) is not None:
        # a bancada devolve sempre com endPos 0: o servidor escolhe o primeiro espaço livre
        free = bag.free_positions(snap, s.ctx.clock.now())
        end_pos = free[0] if free else -1
    end = (end_bag, end_obj, end_pos)
    other = bag.at(snap, *end)
    # (cliente) BottleBagCellClickMediator: clicar no armazém da árvore dourada leva a pilha para um espaço livre
    from_bottle = begin[0] == BagType.BOTTLE and end_bag == BagType.BAG and other is None
    ok = item is not None and (begin[0] in MOVABLE or from_bottle) and end_bag in MOVABLE and begin != end
    ok = ok and item is not None and _place_ok(s, item, *end)
    stack = (
        ok
        and item is not None
        and other is not None
        and other.template_id == item.template_id
        and not (item.valid_date or other.valid_date)  # com validade: cada um tem o seu relógio
        and {begin[0], end_bag} <= set(STACKABLE)
        and other.count < bag.max_count(s.ctx.templates, item.template_id)
    )
    if ok and other is not None and not stack:
        ok = _place_ok(s, other, *begin)
    if not ok or item is None:
        s.log.info("5005 recusado", pedido=str(msg))
        return

    live_before = rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now()).live if snap.leader is not None else 0
    hp_before = b.hero_hp(snap.leader, live_before) if snap.leader is not None else 0
    gone: tuple[Item, ...] = ()
    if stack and other is not None:
        use = min(item.count, bag.max_count(s.ctx.templates, item.template_id) - other.count)
        other.count += use
        other.is_binds = other.is_binds or item.is_binds  # GoodsCheck.isAddToChecker: a pilha fica vinculada
        if bag.take_one(snap, item, use):
            gone = (item,)
        first, second = (None if gone else item), other
    else:
        item.bag_type, item.object_id, item.pos, item.is_new = *end, False
        if other is not None:
            other.bag_type, other.object_id, other.pos = begin
        for placed in (item, other):
            if placed is not None and placed.bag_type in BINDS_ON_EQUIP:
                placed.is_binds = True
        first, second = other, item
    book = fashion.register(snap, s.ctx.templates, item.template_id) if end_bag == BagType.HERO else None
    wearer = next((p for p in snap.pets if p.id == end_obj), None) if end_bag == BagType.PET_EQUIP else None
    if wearer is not None:
        wearer.is_bind = True  # PetBagCellDropMediator.prompt02 "Sylph will become bound after putting on equipment"
    healed, dropped, trimmed = 0, False, False
    if BagType.HERO in (begin[0], end[0]) and snap.leader is not None:
        now = s.ctx.clock.now()
        # a vida máxima pode subir: a atual fica e a reserva completa (oficial_20261023-153200-1 #2182-#2185)
        healed = rules.heal_hero(snap, s.ctx.templates, now)
        live = rules.leader_stats(snap, s.ctx.templates, now).live
        dropped = live < live_before
        if hp_before > live:
            # (visto) a vida que passa do máximo novo volta para a reserva: 231733 #233/#300 (hp 1104 -> 984, blood
            # 95116 -> 95236), #4734/#4796 (-83 e +83)
            snap.leader.blood += hp_before - live
            snap.leader.hp = live
        trimmed = rules.trim_army(snap, s.ctx.templates, now)
    leader = snap.leader if healed or dropped else None
    kept: list[object] = [i for i in (item, other, book, wearer, leader) if i is not None and i not in gone]
    if begin[0] == BagType.STORE and benched.pop(str(item.id or 0), None) is not None:
        kept.append(_set_bench_from(snap, benched, s.ctx.clock.now()))
    if end_bag == BagType.STORE and begin[0] == BagType.HERO and not gone:
        benched[str(item.id or 0)] = list(begin)
        kept.append(_set_bench_from(snap, benched, s.ctx.clock.now()))
    await s.ctx.characters.save(*kept, *(snap.pawns if trimmed else ()), delete=gone)

    # (visto) oficial_20261023-171155-1 #2310-#2316, tirar a arma: 113 com a vida no máximo novo, 100 com as tropas
    # que voltaram ao castelo, 3, 150, 115, 115
    if dropped:
        send_blood(s)
    if trimmed:
        s.send(S_CASTLE_PAWNS, castle_pawns(snap, s.ctx.templates))
    # (visto) mochila <-> bancada: só os dois 115 (oficial_encantar #215, 171155 #2319); com o herói, 3, o 83 do HP
    # pack, 150 e os 115 (153200 #2182-#2187, 231733 #4804-#4809)
    if not {begin[0], end[0]} <= {BagType.BAG, BagType.STORE}:
        _player(s)
        hp_pack(s, healed)
        _army(s)
    moved = [item_moved(*begin, first, s.player_id), item_moved(*end, second, s.player_id)]
    if begin[0] == BagType.STORE and end[0] == BagType.HERO:
        moved.reverse()  # (visto) a volta para o herói: o 115 do herói antes do da bancada (231733 #4808-#4809)
    for m in moved:
        s.send(S_ITEMS, m)
    if book is not None:
        send(s, fashion.S_FASHION_BOOK, fashion_book(snap, s.ctx.templates))
    if BagType.HERO in (begin[0], end[0]):
        space.refresh_look(s)  # os outros na cidade do céu veem a arma/armadura nova
    for bag_type, obj, _ in (begin, end):
        if bag_type == BagType.PET_EQUIP and (owner := next((p for p in snap.pets if p.id == obj), None)):
            from .pets import S_PETS, pets_msg  # pets importa player, como este módulo

            s.send(S_PETS, pets_msg(snap, s.ctx.templates, [owner]))  # os bag* do mascote mudaram
            break


# --- 5006 usar ---


@router.on(5006)
async def use_item(s: GameSession, msg: pb.ItemUseMsg) -> None:
    """Usa um item da mochila conforme o SonType: pacote (298), recurso (203), caixa de pedras
    (206), poção de HP (209), pergaminho de efeito (201), Divine Light (316) ou carta de montaria (218). Os outros
    dependem de sistemas que não existem e são recusados."""
    snap = s.snapshot
    assert snap is not None
    item = bag.at(snap, BagType.BAG, 0, msg.pos) if msg.bagType == BagType.BAG else None
    row = _row(s, item) if item is not None else None
    if item is None or row is None or item.is_locked or snap.character.grades < int(row.get("NeedGrades") or 0):
        s.log.info("5006 recusado", pedido=str(msg))
        return
    n = max(1, min(msg.count, item.count))
    uses = {BOX: _open_box, USE: _use_resource, GEM_BOX: _open_gem_box, BLOOD: _use_blood, EFFECT: _use_effect}
    uses[monsters.FOG_SON_TYPE] = _use_divine_light
    uses[MOUNT_CARD] = _use_mount_card
    uses[POWER_CARD] = _use_power_card
    use = uses.get(row.get("SonType", ""))
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
    if drops and known and not fits:  # (visto) 215937 #585-#586, 231733 #210-#211: só o 111
        send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Inventory full, unable to retrieve item."))
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
    ref = f"5006:{box.template_id}"
    ledger = cash.change(c, point, gift, "item", ref, s.ctx.clock.now()) if point or gift else None
    logs = [item_entry(c.id or 0, box.template_id, -1, "use", ref)]
    logs += [item_entry(c.id or 0, i.template_id, i.count, "drop", ref) for i in new]
    grade = int(drops[0].get("Grade") or 0)
    boxes = ev.state(snap, ev.GRADE_BOXES, s.ctx.clock.now()) if grade else None
    if boxes is not None:
        # no ``text``: o bit 35/40 não cabe na coluna Integer. shortcut: o cliente faz int(gradeProcess) (32 bits) e
        # perde os bits acima do 31; sem captura do pacote de 35/40 não se sabe o que o oficial manda
        boxes.text = str(int(boxes.text or "0") | 1 << grade)
    await s.ctx.characters.save(
        c, *new, *logs, *([ledger] if ledger else []), *([boxes] if boxes else []), delete=(box,)
    )

    from . import events  # events importa login, que importa este módulo

    s.send(S_ITEMS, item_moved(BagType.BAG, 0, box.pos, None, s.player_id))
    if ledger:
        balens_changed(s)
    if -100 in ids:
        castle_yield(s)
    s.send(S_ITEMS, bag.moved(new, s.player_id))
    events.items_gained(s)  # (visto) 4476 e os 4484 depois do 115 dos itens: #677-#688, #3244-#3254

    def label(d: Row) -> str:
        name = (templates.get("ItemTempInfos", int(d["TemplateId"])) or {}).get("TemplateName", d["TemplateId"])
        tid, n = int(d["TemplateId"]), int(d["Data"])
        # (visto) captura EN #689: "Received:  10 Bound Balens, 3,000 Gold, Amethyst Ring x1, ..." (-500: espaço antes)
        return f"{' ' if tid == -500 else ''}{n:,} {name}" if tid < 0 else f"{name} x{n}"

    text = "Received: " + ", ".join(label(d) for d in reversed(drops))  # o oficial lista do fim para o começo
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    if boxes is not None:
        # (visto) 111, 2 com o gradeProcess, 3 e 83: tutorial_en #3255-#3258, 231733 #275-#278 (no #689-#692 o 83 veio
        # antes do 3)
        s.send(S_GRADE_BOXES, pb.NoviceReqMsgMsg(gradeProcess=boxes.text))
        _player(s)
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
        return True
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    _player(s)
    return True


async def _use_resource(s: GameSession, item: Item, row: Row, n: int) -> bool:
    """Recurso (SonType 203): Property1 = tipo, Property2 = quantidade por unidade."""
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    c, now = snap.character, s.ctx.clock.now()
    if int(row.get("Property1") or 0) == VIP_CARD:
        from . import vip  # vip -> player -> login; aqui evita o ciclo na carga dos handlers

        return await vip.use_trial_card(s, item, row, n)
    if int(row.get("Property1") or 0) == COVENANT:
        from . import vip

        return await vip.use_covenant(s, item, row, n)
    if int(row.get("Property1") or 0) == ONE_CONTRACT:  # Pocket Market, Bounty Helper...: o contrato Property3
        from . import vip

        return await vip.use_covenant(s, item, row, n, (int(row.get("Property3") or 0),))
    if int(row.get("Property1") or 0) == TROOPS:
        return await _use_troops(s, item, row, n)
    kind = USE_KINDS.get(int(row.get("Property1") or 0))
    amount = int(row.get("Property2") or 0) * n
    if kind is None or amount <= 0:
        return False
    field, label = kind
    if field == "copies":
        return await _use_copies(s, item, n, amount)
    if field == "weary":
        amount = min(amount, c.weary_limit - c.weary, daily.POTION_DAY - c.weary_potions)
        if amount <= 0:
            return False
        c.weary_potions += amount
    exp_day = None
    if field == "gp":  # teto diário (game_settings.item_exp_daily, migração 0108)
        exp_day = ev.daily(snap, ITEM_EXP_KEY, now)
        amount = min(amount, int(s.ctx.world.settings.get("item_exp_daily") or 0) - exp_day.value)
        if amount <= 0:
            alert(s, ITEM_EXP_FULL)
            return False
        exp_day.value, exp_day.updated_at = exp_day.value + amount, now
    changed, gone = _consume(snap, item, n)  # antes de qualquer await
    extra: list[object] = []
    gained = 0
    if field == "gp":
        gained = rules.add_gp(snap, s.ctx.templates, amount)
        extra += [snap.leader, *snap.pawns, exp_day]
    elif field in ("point", "gift_token"):
        point, gift = (amount, 0) if field == "point" else (0, amount)
        extra.append(cash.change(c, point, gift, "item", f"item:{item.template_id} x{n}", now))
    else:
        setattr(c, field, getattr(c, field) + amount)
    await s.ctx.characters.save(c, *changed, *extra, delete=tuple(gone))

    # (visto) 153200 #2188-#2192 (ouro: 115, 109, 111 "Received:Gold x1000", 3) e 231733 #4131-#4150 (Daru, Stamina:
    # 115, 111, 3); sem separador de milhar. O turco (essiz_can_ilaci_kullanimi) põe "Tebrikler! " na frente
    _send_items(s, changed, gone)
    if field in ("gold", "crystals"):
        castle_yield(s)
    if gained:  # (visto) 191924 #1725: 115, 83 da EXP, o nível (140, 100, 150), 111 e 3
        send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=exp_text(amount)))
        await push_level(s, c.grades - gained)
    if field == "consortia_offer":  # (visto) 183522 #15179-#15185: 115, 42 result, 111 e 3
        send(s, S_CONSORTIA_OFF, b.complete(pb.ConsortiaMsg(result=True)))
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Received:{label} x{amount}"))
    _player(s)
    if field == "gp" and not gained:  # (visto) 191924 #1720: 115, 111 "Received:Hero EXP x1000", 3 e 83
        send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=exp_text(amount)))
    return True


async def _use_troops(s: GameSession, item: Item, row: Row, n: int) -> bool:
    """Carta de soldados (203 tipo 9): ``Property2`` x n soldados do ``PawnTempInfos`` ``Property3`` no castelo.
    O tipo é achado pelo template exato (os 9001-9008 dividem o ``// 100``). TODO(inventado): não confere a
    população; o texto é o do recrutamento (5155)."""
    snap = s.snapshot
    assert snap is not None
    tid, amount = int(row.get("Property3") or 0), int(row.get("Property2") or 0) * n
    tpl = s.ctx.templates.get("PawnTempInfos", tid)
    if tpl is None or amount <= 0:
        return False
    pawn = next((p for p in snap.pawns if p.template_id == tid), None)
    if pawn is None:
        pawn = Pawn(snap.character.id or 0, tid)
        snap.pawns.append(pawn)
    pawn.castle_count += amount
    changed, gone = _consume(snap, item, n)  # antes de qualquer await
    await s.ctx.characters.save(pawn, *changed, delete=tuple(gone))
    _send_items(s, changed, gone)
    send(s, S_CASTLE_PAWNS, castle_pawns(snap, s.ctx.templates, [pawn]))
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Successfully Recruited {amount:,} {tpl['PawnName']}"))
    return True


async def _use_copies(s: GameSession, item: Item, n: int, times: int) -> bool:
    """The Empire Crusade (203, Property1 15): ``times`` entradas de campanha em grupo a mais, nas que sobram e no
    máximo do dia (4240 com os dois). (visto, só turco: buyuk_sefer_kullanimi_grup_sahne_yarari_1) 1/1 -> 2/2, o
    115 do item, o 111 com o aviso e o 3. Vale só no dia do uso (``Character.multi_copies``).
    *(dedução)* o texto com ``times`` > 1 não foi visto."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    count, top = c.multi_copies(rules.copies_base(s.ctx.templates), now)
    c.multi_copy_count, c.multi_copy_max, c.multi_copy_day = count + times, top + times, gameday.today(now)
    # ponytail: sem teto de uso por dia (a captura turca tem um uso só); o gasto da entrada não existe aqui, falta
    # captura de entrar numa campanha em grupo (5039 não tem handler)
    changed, gone = _consume(snap, item, n)  # antes de qualquer await
    await s.ctx.characters.save(c, *changed, delete=tuple(gone))

    _send_items(s, changed, gone)
    send(s, S_COPIES, pb.MultiCampaignEnterCountMsg(campaignCount=count + times, campaignMaxcount=top + times))
    # texto deduzido (sem fonte inglesa no cliente/captura)
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=f"Multi-player Dungeon attempts increased by {times}"))
    _player(s)
    return True


async def _open_gem_box(s: GameSession, box: Item, row: Row, n: int) -> bool:
    """Caixa de pedras (``GEM_BOX_LEVELS``): uma pedra aleatória do nível por caixa, entre as 8 do
    ``TransformInfos`` daquele nível. As outras caixas 206 têm o conteúdo só na descrição
    (Property1 = o próprio id, sem tabela de drop nos templates) e são recusadas."""
    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    kits = taxas.get(s.ctx.world.settings, "summoner_kits") or {}
    if str(box.template_id) in kits:
        cards = _kit_cards(s, kits[str(box.template_id)], n)
        return cards is not None and await _box_items(s, box, n, cards)
    if box.template_id not in GEM_BOX_LEVELS:
        return await _open_described(s, box, row, n)
    low, high = GEM_BOX_LEVELS[box.template_id]
    stones: dict[int, int] = {}
    for _ in range(n):
        level = templates.get("TransformInfos", random.randint(low, high), key="TransformId")
        if level is None:
            return False
        tid = int(level[f"Material{random.randint(1, 8)}"])
        stones[tid] = stones.get(tid, 0) + 1
    return await _box_items(s, box, n, stones)


def _kit_cards(s: GameSession, pool: list[list[int]], n: int) -> dict[int, int] | None:
    """Kit de invocador (2131016-2131018): uma carta por kit. A raridade é ``ItemTempInfos.Profile`` das cartas
    (SonType 600; 1 comum ... 5); a descrição do kit diz "high chance" de uma e "lower chance" da seguinte, o peso
    está em ``taxas.summoner_kits`` (0138). (visto) captura 20261029-121453-1 #4024-#4026: 5 Expert -> 4 de Profile 2
    e 1 de Profile 3, um item de carta por kit."""
    by_profile: dict[int, list[int]] = {}
    for r in s.ctx.templates.rows("ItemTempInfos"):
        if r.get("SonType") == POWER_CARD:
            by_profile.setdefault(int(r.get("Profile") or 0), []).append(int(r["TemplateId"]))
    cards: dict[int, int] = {}
    for _ in range(n):
        profile = random.choices([p for p, _ in pool], weights=[w for _, w in pool])[0]
        if not (choices := sorted(by_profile.get(int(profile), []))):
            return None
        tid = random.choice(choices)
        cards[tid] = cards.get(tid, 0) + 1
    return cards


async def _box_items(s: GameSession, box: Item, n: int, stones: dict[int, int]) -> bool:
    """Gasta ``n`` caixas e dá ``stones``: 115 da caixa, 115 do que entrou, 4476/4426/4484, 111, 3 e 83 (captura
    20261029-121453-1 #4024-#4040, kits; só turco: lvl1_degerli_tas_sandigi, pedras)."""
    snap = s.snapshot
    assert snap is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    if not bag.fits(snap, templates, stones.items(), now):
        return False
    changed, gone = _consume(snap, box, n)
    got = [i for tid, count in stones.items() for i in bag.add(snap, templates, tid, count, now)]
    await s.ctx.characters.save(*changed, *got, delete=tuple(gone))

    _send_items(s, changed, gone)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    from . import events  # events importa login, que importa este módulo

    events.items_gained(s)  # (só turco: lvl1_degerli_tas_sandigi) 4476, 4426 e os 4484 depois do 115 da pedra
    text = "Received: " + ", ".join(f"{bag.name(templates, tid)} x{count}" for tid, count in stones.items())
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    _player(s)
    send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    return True


_NAMES: dict[int, dict[str, int]] = {}  # id(templates) -> nome normalizado -> TemplateId (o menor)
_FIXED = re.compile(r"\b(?:Contents|Contains|containing):\s*", re.I)
_ONE_OF = re.compile(r"one of the following(?: items)?:\s*", re.I)
_MAYBE = re.compile(r"chance|may contain|random", re.I)
_TOKEN = re.compile(r"^(?:(\d[\d,]*) (.+)|(.+?) ?[x×\*] ?(\d[\d,]*)|(.+))$")  # sem número: 1


def _norm(name: str) -> str:
    return re.sub(r"[.\s]+", " ", name).strip().lower()


def _named(s: GameSession, name: str) -> int | None:
    index = _NAMES.get(id(s.ctx.templates))
    if index is None:
        index = {}
        for r in sorted(s.ctx.templates.rows("ItemTempInfos"), key=lambda r: abs(int(r["TemplateId"]))):
            index.setdefault(_norm(r.get("TemplateName", "")), int(r["TemplateId"]))
        _NAMES[id(s.ctx.templates)] = index
    key = _norm(name)  # plural/singular: "Runestones", "Crypt Token" (o nome é "Crypt Tokens")
    return index.get(key, index.get(key[:-1] if key.endswith("s") else key + "s"))


def box_contents(s: GameSession, description: str) -> tuple[list[tuple[int, int]], bool] | None:
    """O conteúdo de uma caixa 206 pela descrição inglesa (``ItemTempInfos.Description``): "Contents: 300,000 Gold,
    Bullhorn (Large) x10, ..." (tudo) ou "one of the following: 10000 Gold, 2000 Daru, ..." (um, ``True``). Tudo ou
    nada: um nome que não bate com um ``TemplateName`` (ou texto com "chance"/"May contain" fora da lista de um)
    recusa a caixa (None)."""
    one = _ONE_OF.search(description)
    fixed = _FIXED.search(description)
    if one is None and (fixed is None or _MAYBE.search(description)):
        return None
    start = (one or fixed).end()  # type: ignore[union-attr]
    body = re.split(r"\.(?=\s+[A-Z]|\s*$)|\bUnlocks\b", description[start:])[0]  # "Lvl. 3" não fecha a frase
    body = re.sub(r"([x×]\s?\d(?:[\d,]*\d)?)\s+(?=[A-Z\[])", r"\1, ", body)  # "Shard x5 Gold x100000" sem vírgula
    goods: list[tuple[int, int]] = []
    for part in re.split(r",(?!\d{3})\s*|\s+or\s+", body.strip().rstrip(".")):
        m = _TOKEN.match(part.strip())
        if m is None:
            return None
        count, name = (m[1], m[2]) if m[1] else (m[4], m[3]) if m[4] else ("1", m[5])
        tid = _named(s, name)
        if tid is None or (tid < 0 and tid not in CURRENCIES and tid != rewards.AMETHYST):
            return None
        goods.append((tid, int(count.replace(",", ""))))
    return (goods, one is not None) if goods else None


async def _open_described(s: GameSession, box: Item, row: Row, n: int) -> bool:
    """Caixa 206 sem tabela de drop (Property1 = o próprio id): o conteúdo vem da descrição (``box_contents``).
    "one of the following": TODO(inventado) sorteio uniforme entre as opções (a descrição não dá chance). Mochila
    cheia: recusa com o aviso do pacote 298 (visto 215937 #585)."""
    snap = s.snapshot
    assert snap is not None
    templates, now, c = s.ctx.templates, s.ctx.clock.now(), snap.character
    parsed = box_contents(s, row.get("Description", ""))
    if parsed is None:
        return False
    options, one = parsed
    drops: dict[int, int] = {}
    for _ in range(n):
        for tid, count in [random.choice(options)] if one else options:
            drops[tid] = drops.get(tid, 0) + count
    goods = [(t, k) for t, k in drops.items() if t > 0]
    if not bag.fits(snap, templates, goods, now):
        send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Inventory full, unable to retrieve item."))
        return False
    changed, gone = _consume(snap, box, n)  # antes de qualquer await
    got = [i for t, k in goods for i in bag.add(snap, templates, t, k, now)]
    point, gift = drops.pop(-400, 0), drops.pop(-500, 0)
    rewards.grant(snap, templates, [(t, k) for t, k in drops.items() if t < 0])
    ledger = cash.change(c, point, gift, "item", f"5006:{box.template_id}", now) if point or gift else None
    extra = [ledger] if ledger else []
    await s.ctx.characters.save(*rewards.owners(snap), *changed, *got, *extra, delete=tuple(gone))

    _send_items(s, changed, gone)
    if got:
        send(s, S_ITEMS, bag.moved(got, s.player_id))
        from . import events  # events importa login, que importa este módulo

        events.items_gained(s)
    if ledger:
        balens_changed(s)
    if -100 in drops:
        castle_yield(s)
    text = rewards.text(templates, [(t, k) for t, k in [*drops.items(), (-400, point), (-500, gift)] if k])
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
    healed = rules.heal_hero(snap, s.ctx.templates, s.ctx.clock.now())  # (dedução) como a compra do 5633
    await s.ctx.characters.save(leader, *changed, delete=tuple(gone))

    # (visto) oficial_20261023-171155-1 #7589-#7593: 115, 113, 150, 3 e o 83 "Used HP pack to restore HP." no fim
    _send_items(s, changed, gone)
    send_blood(s)
    _army(s, cards=False)  # (só turco: buyuk_hp_iksiri_kullanim #3-#6) 113, 150, 3 sem o 4902
    _player(s)
    hp_pack(s, healed)
    return True


async def _use_mount_card(s: GameSession, item: Item, row: Row, _: int) -> bool:
    """Carta de montaria (SonType 218, ``MountsManager.sendUseGoods``): ``Property1`` = montaria, ``Property2`` =
    dias (-1 = permanente), ``Property3`` = Beast Soul Lvl pedido ("Requires Beast Soul Lvl {0}"). Uma por uso; a
    temporária soma dias, a que já é permanente recusa."""
    from .systems import grant_mount, send_avatars, soul_grade  # systems importa hero, que vem antes deste módulo

    snap = s.snapshot
    assert snap is not None
    sy, mount = rules.systems(snap), int(row.get("Property1") or 0)
    if s.ctx.templates.get("MountTempInfos", mount) is None or int(row.get("Property3") or 0) > soul_grade(
        s.ctx.templates, sy
    ):
        return False
    if not grant_mount(sy, mount, int(row.get("Property2") or 0), s.ctx.clock.now()):
        return False
    changed, gone = _consume(snap, item, 1)
    await s.ctx.characters.save(sy, *changed, delete=tuple(gone))

    _send_items(s, changed, gone)
    send_avatars(s)
    return True


async def _use_power_card(s: GameSession, item: Item, row: Row, n: int) -> bool:
    """Carta de poder (SonType 600): ``n`` cópias entram na coleção (``systems.gain_cards``); a carta nova fica com
    ``isActive`` 1 e as outras 0 (o cliente toca o efeito, ``MagicCardInfo.isPlay``/``MagicCardSlotItem``). (visto)
    captura 20261029-121453-1 #4043-#4107: 115, 111, 4902, 150, 4903 (vazio fora de campanha), 83 "Congrats! You
    just received the 1st card, [coleção]." quando é a primeira da coleção, 83 "Card {nome} has been successfully
    activated!", 4905, 4902 e 3. O 111 é o primeiro dos dois textos. Só abre uma cópia, e só se a carta é nova; a
    repetida é recusada (fica na mochila para o op 3 do 9505 engolir)."""
    from .systems import S_CAMP_BUFFS, cards, gain_cards, send_cards, store_cards

    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    sy = rules.systems(snap)
    temp = int(row.get("Property1") or 0)
    suite = int((templates.get("PowcardTempInfos", temp) or {}).get("SuiteId") or 0)
    first = not any(int((templates.get("PowcardTempInfos", t) or {}).get("SuiteId") or 0) == suite for t in cards(sy))
    n = 1  # gain_cards abre uma cópia por item
    copy = Item(item.character_id, item.template_id, count=n)
    if not gain_cards(sy, templates, [copy]):
        return False
    found = cards(sy)
    for t, card in found.items():
        card[2] = int(t == temp)
    store_cards(sy, found)
    changed, gone = _consume(snap, item, n)
    await s.ctx.characters.save(sy, *changed, delete=tuple(gone))

    texts = [f"Card {row.get('TemplateName', '')} has been successfully activated!"]
    if first:
        name = (templates.get("PowCardSuiteTemInfos", suite) or {}).get("TemplateName", "")
        texts.insert(0, f"Congrats! You just received the 1st card, [{name}].")
    _send_items(s, changed, gone)
    send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=texts[0]))
    _army(s)
    s.send(S_CAMP_BUFFS, pb.PowCardBufListMsg())
    for text in texts:
        send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    send_cards(s)
    _player(s)
    return True


async def _use_divine_light(s: GameSession, item: Item, row: Row, n: int) -> bool:
    """Divine Light (SonType 316): tira a névoa do mapa do castelo por ``FOG_SECONDS`` para todos (help: "when
    anyone uses Divine Light the fog around is cleared"), um item por uso. 4939 = ``MapBossMsg`` só com
    ``leftFogTime`` (cliente) a quem vê o mapa; o 4938 dele leva o que sobra. Só no processo: são 20 s."""
    from .outer_city import viewers  # outer_city importa events, que importa player e este módulo

    snap = s.snapshot
    assert snap is not None and snap.castle is not None
    map_id = snap.castle.map_id
    changed, gone = _consume(snap, item, 1)  # antes de qualquer await
    s.ctx.wilds.clear_fog(map_id, s.ctx.clock.now())
    await s.ctx.characters.save(*changed, delete=tuple(gone))

    _send_items(s, changed, gone)
    for other in {s, *viewers(s, map_id)}:
        send(other, S_FOG, pb.MapBossMsg(leftFogTime=monsters.FOG_SECONDS))
    return True


def _effect_type(s: GameSession, effect: int) -> int:
    return buffs.stat_type(s.ctx.templates, effect)


def send_buffers(s: GameSession, states: list[EventState]) -> None:
    """4188 com os efeitos (``validityDate`` 0 tira o ícone)."""
    send(s, S_ITEM_BUFFER, buffs.buffer_list(states, s.ctx.clock.now()))


async def _use_effect(s: GameSession, item: Item, row: Row, n: int) -> bool:
    """Pergaminho de efeito (SonType 201): Property1 = EffectTempInfo, Property2 = minutos, Property3 = grau
    (``game/buffs.py``). 2013002 (Lvl. 2 Bonus EXP Scroll): 110 ``{propertyType 30 (PropertyType1 do 2030), value
    100}``, 4188 ``{2030, validityDate 60, grade 100, type 2, typeTemplateid 2013002}``, sem texto (turco
    ``exp_kitabi_kullanim`` #2-#10 e 191924 #2241)."""
    snap = s.snapshot
    assert snap is not None
    effect, minutes, level = (int(row.get(f"Property{i}") or 0) for i in (1, 2, 3))
    if minutes <= 0 or (effect != PROTECTION and not _effect_type(s, effect)):
        return False
    st = buffs.apply(snap, effect, item.template_id, level, minutes * n, s.ctx.clock.now())
    if st is None:
        return False  # grau menor que o ativo
    changed, gone = _consume(snap, item, n)  # antes de qualquer await
    await s.ctx.characters.save(st, *changed, delete=tuple(gone))
    if effect == PROTECTION:  # trégua: o fim fica gravado; o ícone e o relógio vêm só do 4452 (segundos)
        _send_items(s, changed, gone)
        send(s, S_CASTLE_TIME, pb.BaseCastleMsg(defenceLefttime=buffs.protection_left(snap, s.ctx.clock.now())))
        return True

    # (visto) oficial_20261024-191924-1 #1737 (Crit Scroll): 115, 150, 4434, 110, 150, 4188, 150, 3; #2241 (Lvl. 2
    # Bonus EXP Scroll): 115, 150, 4434, 110, 4188, 150, 3. O 110 dos atributos o cliente ignora (PlayerEffectHelper):
    # o 150 leva os total* novos. (#3379, Magic Defense Scroll, tem dois 150 antes do 4188; aqui um)
    _send_items(s, changed, gone)
    balens_changed(s)
    send(s, S_EFFECT, pb.PropertyUpdatedMsg(propertyType=_effect_type(s, effect), value=level))
    if effect not in (buffs.EXP_BOOST, buffs.GOLD_MAX, buffs.POPULATION):  # (dedução) ouro/população como o EXP
        _army(s)
    send_buffers(s, [st])
    if effect in (buffs.GOLD_MAX, buffs.POPULATION):
        castle_yield(s)  # (dedução) teto do armazém/população novos na barra
    _army(s)
    _player(s)
    return True


@router.on(8283)
async def effect_stop(s: GameSession, msg: pb.EffectRemoveReqMsg) -> None:
    """C_EFFECT_STOP: o relógio do ícone chegou a 0 no cliente ou o jogador tirou o efeito (``PlayerBufferItem``,
    "Are you sure you want to remove this buff?"). (visto) 20261030-151436 #2299-#2304 (EXP 2030): 110 {30, 0},
    4188 ``validityDate`` 0 e ``isCancel``, 150, 4434; #2910-#2917 (atributo 2138, grau 40): 110 {3, -40}, 150, 4188,
    150, 4434 (a mesma ordem do uso)."""
    snap = s.snapshot
    assert snap is not None
    st = buffs.stop(snap, msg.templateId, s.ctx.clock.now())
    if st is None:
        s.log.info("8283 sem efeito", pedido=str(msg))
        return
    await s.ctx.characters.save(st)
    kind = _effect_type(s, msg.templateId)
    stat = kind in buffs.STATS
    send(s, S_EFFECT, pb.PropertyUpdatedMsg(propertyType=kind, value=-st.value if stat else 0))
    if stat:
        _army(s)  # os total* sem a poção
    msg_out = buffs.buffer_list([st], s.ctx.clock.now())
    for d in msg_out.bufferData:
        d.isCancel = True
    send(s, S_ITEM_BUFFER, msg_out)
    if msg.templateId in (buffs.GOLD_MAX, buffs.POPULATION):
        castle_yield(s)
    balens_changed(s)


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
            # (visto) 231733 #224-#229 e #245-#253: 115 por item, 109 e o 111, sem 83
            total = sum(gold for _, _, gold in plan)
            send(
                s,
                S_ALERT,
                pb.ChatChannelMsg(channel=7, encodeMsg=f"Sale successful! You have received {total:,} gold."),
            )
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
    """Arrumar a mochila ou o armazém da guilda (``ConsortiaCaseView`` "Sort"): o cliente calcula a ordem
    (``arrangeInfo`` velho -> novo) e, com ``isStackItem``, o servidor junta as pilhas incompletas do mesmo item."""
    snap = s.snapshot
    assert snap is not None
    items = bag.in_bag(snap, msg.bagType)
    by_pos = {i.pos: i for i in items}
    moves = {a.oldplace: a.newplace for a in msg.arrangeInfo}
    cap = bag.capacity(snap.character, s.ctx.clock.now()) if msg.bagType == BagType.BAG else _guild_cells(s)
    final = {pos: moves.get(pos, pos) for pos in by_pos}
    valid = msg.bagType in (BagType.BAG, BagType.GUILD)
    valid = valid and len(moves) == len(msg.arrangeInfo) and set(moves) <= set(by_pos)
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
                if other.is_locked != item.is_locked or other.is_binds != item.is_binds:
                    continue
                if item.valid_date or other.valid_date:
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
    """Item vencido: *(cliente)* ``BaseBagListView``/``EquipBagII`` mandam ``{bagType, pos}`` ao desenhar um item com
    ``validDate`` > 0 e ``now - beginDate >= validDate`` minutos. O servidor confere a validade e apaga; o 115
    esvazia a posição. Resposta e silêncio (nenhum aviso): *(dedução)*, sem captura."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    # o pedido não traz objectId: na mochila é 0, nas bolsas do herói é o herói que tiver algo ali
    item = next((i for i in snap.items if (i.bag_type, i.pos) == (msg.bagType, msg.pos) and i.expired(now)), None)
    if item is None or item.bag_type not in MOVABLE:
        s.log.info("8346 recusado: item ausente ou ainda válido", pedido=str(msg))
        return
    snap.items.remove(item)
    await s.ctx.characters.save(delete=(item,))
    if item.bag_type != BagType.BAG:  # medalha/equipamento do herói: atributos mudam
        _player(s)
        _army(s)
    s.send(S_ITEMS, item_moved(item.bag_type, item.object_id, item.pos, None, s.player_id))


async def expire_items(s: GameSession) -> None:
    """Apaga os itens vencidos do snapshot (login e relógio de 60 s): o cliente só confere a mochila que está na
    tela, e a medalha vestida (bolsa 3) nunca passa por lá. *(dedução)*: o oficial faz o mesmo de algum jeito."""
    snap = s.snapshot
    assert snap is not None
    gone = bag.expire(snap, s.ctx.clock.now())
    if not gone:
        return
    await s.ctx.characters.save(delete=tuple(gone))
    if any(i.bag_type != BagType.BAG for i in gone):
        _player(s)
        _army(s)
    _send_items(s, [], gone)


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


# --- cristal (Soul Crystal) ---


@router.on(8484)
async def use_store(s: GameSession, msg: pb.ItemUseStoreReqMsg) -> None:
    """Gasta ``count`` Soul Crystal no cristal do jogador (``storeGp``/``storeGrade``)."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates
    row = templates.get("ItemTempInfos", STORE_STONE)
    if row is None or not 0 < msg.count <= bag.count_of(snap, STORE_STONE):
        s.log.info("8484 recusado", pedido=str(msg))
        return
    from . import events  # events importa login, que importa este módulo
    from .army import count_quest  # army importa player, que importa este pacote

    changed, gone = bag.take(snap, STORE_STONE, msg.count)
    gained = int(row.get("Property1") or 1) * msg.count
    old_grade = c.store_grade
    levels = list(templates.find("UpGradeTempInfos", Types=STORE_GRADE))
    c.store_grade, c.store_gp = store_level(levels, c.store_grade, c.store_gp + gained)
    await s.ctx.characters.save(c, *changed, delete=tuple(gone))
    # (visto) 20261101-220132-1 #1963-#1973 (subiu 0 -> 7): 115, 4484, 3, 3 (poder novo), 4902, 150, 111, 112 da 858,
    # 4385, 83; #1999-#2003 (sem subir): 115, 3, 111, 4385, 83. A EXP do herói não muda
    _send_items(s, changed, gone)
    if c.store_grade != old_grade:
        events.send_titles(s)
        _player(s)
    _player(s)
    if c.store_grade != old_grade:
        _army(s)
    alert(s, f"Received:EXP x{gained}")
    await count_quest(s, rules.ENGRAVE_CONDITION)
    s.send(S_STORE_DONE, pb.ItemUseStoreRspMsg(result=True))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Received:EXP x{gained}"))


def store_level(levels: list[Row], grade: int, gp: int) -> tuple[int, int]:
    """Sobe o cristal enquanto a EXP paga o próximo nível: ``Data`` do nível N = custo de N-1 a N; ``storeGp`` é a
    EXP dentro do nível. (visto) 0 + 566 -> 7/1 (10+30+52+76+102+131+164 = 565), +100 -> 7/101."""
    cost = {int(r["Grades"]): int(r["Data"]) for r in levels}
    while grade + 1 in cost and gp >= cost[grade + 1]:
        gp -= cost[grade + 1]
        grade += 1
    return grade, gp


# --- espaços da mochila ---


def bag_row_cost(index: int) -> int:
    """Diamantes da linha ``index`` (0 = primeira comprada), ``BagBuyFrame``: 10, 20 ... 100 e depois 100."""
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
    # (visto) oficial_20261024-191924-1 #3916-#3921 (1 linha) e oficial_20261027-152321-1 #9378-#9383 (3 linhas, o
    # texto muda com o número): 3, 150, 4434, 111 "Successfully unlocked N inventory row(s).", 3
    _player(s)
    balens_changed(s)
    alert(s, f"Successfully unlocked {rows} inventory row(s).")
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
    hero = _copy(
        b.hero_info(leader, cid, rules.leader_stats(snap, s.ctx.templates, s.ctx.clock.now())), pb.SimpleHeroMsg()
    )
    hero.tempateId, hero.nickName = leader.template_id, snap.character.nickname or ""
    out.army.CopyFrom(pb.SimpleArmyMsg(playerId=cid, nickName=snap.character.nickname or "", simpleHero=hero))
    out.army.storeGrade, out.army.appellid = snap.character.store_grade, snap.character.appell_id
    send(s, S_DETAIL, out)


# --- baú caído na campanha ---


@router.on(5129)
async def drop_take(s: GameSession, msg: pb.CampaignReqMsg) -> None:
    """Baú que caiu da luta (4103 com ``signId``/``baseItem``, ``CampaignSocketManger``). ``paraInt1`` 0 pega tudo
    (``BattleFallGoodsView``; inglesa #2924-#2939: 115, 4476, 111, 83); um ``templateId`` pega só ele (o
    ``HangUpMediator`` manda a posição do nó, que não é item: pega tudo). Mochila cheia: 4268 com o que o baú
    ainda tem, e o cliente o põe de volta no mapa (``CampaignMapController.__resetFallHandler``)."""
    snap = s.snapshot
    assert snap is not None
    fallen = s.campaign.fallen if s.campaign is not None else {}
    sign = msg.paraString1
    if not (goods := fallen.get(sign)):
        s.log.info("5129: baú desconhecido", sinal=sign)
        return
    templates, now = s.ctx.templates, s.ctx.clock.now()
    take = [d for d in goods if d[0] == msg.paraInt1] or goods
    if not bag.fits(snap, templates, take, now):
        base = [pb.BaseItemMsg(templateId=t, count=n) for t, n in goods]
        send(s, S_DROP_FAIL, pb.BattleReportMsg(signId=sign, baseItem=base))
        return
    if left := [d for d in goods if d not in take]:
        fallen[sign] = left
    else:
        del fallen[sign]
    new = [i for t, n in take for i in bag.add(snap, templates, t, n, now)]
    await s.ctx.characters.save(*new)
    from . import events  # events importa login, que importa este módulo

    send(s, S_ITEMS, rewards.items_msg(new, s.player_id))
    events.items_gained(s)
    texts = [rewards.received(templates, [d]) for d in take]
    for text in texts:
        send(s, S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    for text in texts:
        send(s, S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
