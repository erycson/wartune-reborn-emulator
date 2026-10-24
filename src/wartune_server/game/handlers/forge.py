"""Forja (bancada = bagType 0): reforço (5150), engaste (5151/5152), composição (5153), refino
(8336/8339/8464), decomposição (8340), conversão de pedras (8538), encantamento do equipamento de mascote (8644).
Ver ``docs/itens.md``.

A bancada guarda o equipamento na posição 0 e a pedra da sorte na 1; o cliente põe e tira os itens
com o 5005. Fórmulas do cliente: ``GoodsHelp.getStrengthenGold``/``StoreIntensifyView``.
"""

from __future__ import annotations

import random

from ...domain.models import BagType, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from ...templates.repository import GameTemplates, Row
from .. import bag, rules
from ..builders.player import quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import _army, _player
from .shop import alert, send

S_ITEMS, S_STRENGTHEN, S_COMPOSE = 115, 86, 89
S_REFRESH, S_REPLACE, S_RESOLVE, S_REFRESH_PROPERTY = 4258, 4259, 4260, 4368
S_MOULD = 4558  # StoreRspMsg.strengResult do 8644 (PetEquipStrengView.__mouldResult)
S_QUESTS = 112  # QuestUpdatedRspMsg
STRENGTHEN, GEM_INLAY, GEM_COMPOSE, REFINE = 17, 18, 19, 47  # QuestCondictionInfos.CondictionType
MOSAIC_PARA1 = 1  # (visto) tempinfos: 281 Para1 1; Detail "Socket any gem" = qualquer pedra
LUCK, GEM, DRILL = "204", "205", 208004  # SonType da pedra da sorte e das pedras; Socketing Rod
# equipamento de mascote (PetEquipGodHeadView/GodHeadItemView): Divinity Soul e Soul Socketing Rod
SOUL, SOUL_DRILL = "329", 3280101
EQUIP, PET_EQUIP = bag.EQUIP_MASTER, bag.PET_MASTER  # MasterType do equipamento do herói e do mascote
# PetEquipStrengView: 3 Light of Magic + 3 Glint of Magic por tentativa (PetData.PET_EQUIP_STRENG_COST)
MOULD_ITEMS, MOULD_COST = (3250101, 3260101), 3
BLESS_MAX = 100  # "Blessing N/100"; com 100 a taxa mostrada é 100%
MAX_COMPOSE = 999
# ComposeTempInfo.Types do avanço: 5 equipamento do herói (StoreModel.updateEquipList, composeType 4), 10 equipamento
# do mascote (PetEquipUpgradeView, getEquipUpdateComposeTempleteByMainMaterialId)
HERO_UPGRADE, PET_UPGRADE = "5", "10"
RESOLVE_GOLD = 1000  # ResolveView.updateMateView: 1.000 de ouro por equipamento
# pedras de refino pelo Profile: ResolveView.mateMaterial (o que a decomposição dá) e RefreshView.updateMateMaterial
# (o que o refino gasta), a mesma tabela
RESOLVE_STONES = {2: 1, 3: 4, 4: 18, 5: 18}
PET_STONES = RESOLVE_STONES | {6: 24}  # PetEquipRefineryView.getNeedPro (outro Profile: 100)
LOCK_ITEM, LOCK_PRICE = 208027, 45  # RefreshView.REFRESHLOCK_TEMPID; cada cadeado: 1 Refinement Lock ou 45 Balens
UNBOUND_ONLY = 2  # SmithFreshReqMsg.bindType: 0 = vinculado primeiro ("Use bound material first"), 2 = só livre

# ponytail: o refino sorteado fica na memória até o 8339 (some se o servidor reiniciar)
_pending: dict[int, list[int]] = {}


def _gained(s: GameSession) -> None:
    """A regra inglesa: 4476 depois de todo 115 que dá item (``events.items_gained``)."""
    from . import events  # events importa este módulo

    events.items_gained(s)


def _store(snap: PlayerSnapshot, pos: int = 0) -> Item | None:
    return bag.at(snap, BagType.STORE, 0, pos)


def _equip(s: GameSession, master: str = EQUIP) -> tuple[Item, Row] | None:
    """Equipamento (do herói, ou do mascote com ``PET_EQUIP``) na posição 0 da bancada."""
    snap = s.snapshot
    assert snap is not None
    item = _store(snap)
    row = s.ctx.templates.get("ItemTempInfos", item.template_id) if item else None
    return (item, row) if item is not None and row is not None and row.get("MasterType") == master else None


def _any_equip(s: GameSession) -> tuple[Item, Row] | None:
    """Equipamento do herói ou do mascote na bancada (engaste, furo e refino servem aos dois)."""
    return _equip(s) or _equip(s, PET_EQUIP)


def _pet(row: Row) -> bool:
    return row.get("MasterType") == PET_EQUIP


def strengthen_gold(row: Row, grade: int) -> int:
    """Ouro para reforçar do nível ``grade`` para o próximo (``GoodsHelp.getStrengthenGold``)."""
    ng, p = int(row.get("NeedGrades") or 0), int(row.get("Profile") or 0)
    if ng >= 80:
        return int((ng // 10 + 1) ** 2 * p * (grade + 1) ** 2.1 * 10)
    return int(1.5 ** (ng // 10 + 1) * (p + 1) * (grade + 1) ** 2.2 * 5 + 500)


def strengthen_rate(grade: int, luck: Row | None) -> int:
    return max(10, min(100, 100 - grade * 10)) + (int(luck.get("Property1") or 0) if luck else 0)


@router.on(5150)
async def strengthen(s: GameSession, _: object) -> None:
    """Reforço: a pedra da sorte é gasta mesmo na falha e a falha não baixa o nível. O item fica vinculado
    (``store.StoreControler.helpContent01``: "Enchantment will cause any unbound items to become bound")."""
    snap = s.snapshot
    assert snap is not None
    c, templates = snap.character, s.ctx.templates
    found = _equip(s)
    luck = _store(snap, 1)
    luck_row = templates.get("ItemTempInfos", luck.template_id) if luck else None
    if luck_row is not None and luck_row.get("SonType") != LUCK:
        found = None
    if found is None or found[0].strengthen_grade >= int(found[1].get("StrengthenMax") or 0):
        s.log.info("5150 recusado")
        return
    item, row = found
    cost = strengthen_gold(row, item.strengthen_grade)
    if c.gold < cost:
        s.log.info("5150 recusado: sem ouro", custo=cost)
        return
    ok = random.randint(1, 100) <= strengthen_rate(item.strengthen_grade, luck_row)
    c.gold -= cost
    gone = [luck] if luck is not None and bag.take_one(snap, luck, 1) else []
    changed = [luck] if luck is not None and not gone else []
    bound = not item.is_binds
    item.is_binds = True
    if ok:
        item.strengthen_grade += 1
    if ok or bound:
        changed.append(item)
    quests = rules.quest_event(snap, templates, STRENGTHEN, item.strengthen_grade, 1) if ok else []
    await s.ctx.characters.save(c, *changed, *quests, delete=tuple(gone))

    # o oficial manda o 109 duas vezes antes de tudo, no sucesso e na falha (inglês #219-#220 e #3209-#3210, turco
    # "atölye item basma ve mozaik" #9-#10); a falha só leva strengResult no 86
    castle_yield(s)
    castle_yield(s)
    if luck is not None:
        send(s, S_ITEMS, bag.moved([i for i in changed if i is luck], s.player_id, empty=gone))
    if ok or bound:
        send(s, S_ITEMS, bag.moved([item], s.player_id))
    if ok:
        grade = item.strengthen_grade
        out = pb.StoreRspMsg(strengResult=True, strengthenGrade=grade, pos=0, objectId=0, bagType=BagType.STORE)
    else:
        out = pb.StoreRspMsg(strengResult=False)
    if quests:  # o 112 vem antes do 86 (oficial_encantar #288-#289)
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    s.send(S_STRENGTHEN, out)  # como está: o oficial não manda os campos que faltam


# --- engaste ---


def _gem_types(templates: GameTemplates, item: Item, skip: int) -> set[str]:
    rows = (templates.get("ItemTempInfos", j) for n, j in enumerate(item.joins, 1) if j > 0 and n != skip)
    return {r.get("Property1", "") for r in rows if r is not None}


@router.on(5151)
async def inlay(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """Engasta a pedra (``bagType``/``bagPos``) no furo ``mountPos`` (1..4) do item da bancada.
    Furo aberto e vazio: grátis. Ocupado: troca, cobrando o ouro para tirar a antiga (Property3),
    que volta para a mochila. Nunca duas pedras do mesmo atributo no item. O item fica vinculado
    (``store.StoreControler.helpContent02``: "Socketing will cause unbound items to become bound").
    No equipamento de mascote a pedra é a Divinity Soul (SonType 329, ``PetBagCellDropMediator``), com a mesma
    regra de atributo repetido (``JoinGem``) e de troca (prompt07 "Spend {0} gold to replace")."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    found = _any_equip(s)
    stone = bag.at(snap, msg.bagType, 0, msg.bagPos) if msg.bagType == BagType.BAG else None
    stone_row = templates.get("ItemTempInfos", stone.template_id) if stone else None
    gem = SOUL if found and _pet(found[1]) else GEM
    ok = found is not None and stone is not None and stone_row is not None and stone_row.get("SonType") == gem
    ok = ok and 1 <= msg.mountPos <= 4
    if not ok or found is None or stone is None or stone_row is None:
        s.log.info("5151 recusado", pedido=str(msg))
        return
    item, _ = found
    joins = item.joins
    old = joins[msg.mountPos - 1]
    old_row = templates.get("ItemTempInfos", old) if old > 0 else None
    cost = int(old_row.get("Property3") or 0) if old_row else 0
    room = stone.count == 1 or bag.fits(snap, templates, [(old, 1)], now) if old > 0 else True
    duplicate = stone_row.get("Property1") in _gem_types(templates, item, msg.mountPos)
    if old == -1 or duplicate or c.gold < cost or not room:
        s.log.info("5151 recusado", pedido=str(msg), furo=old, repetida=duplicate)
        return
    c.gold -= cost
    if old > 0:
        # (visto) oficial_20261024-121659-1 #302-#321: a troca é a remoção inteira (109, 115 do item sem a pedra,
        # 115 da antiga de volta, 4476/4426/4484, 111 e 83 da remoção) e depois o engaste (115 da pedra, 115 do
        # item) com o 111 "Swap Successful", sem 83
        joins[msg.mountPos - 1] = 0
        item.joins = joins
        back = bag.add(snap, templates, old, 1, now)
        castle_yield(s)
        send(s, S_ITEMS, bag.moved([item], s.player_id))
        send(s, S_ITEMS, bag.moved(back, s.player_id))
        _removed(s, old)
    else:
        back = []
    gone = [stone] if bag.take_one(snap, stone, 1) else []
    changed = [] if gone else [stone]
    joins[msg.mountPos - 1] = stone.template_id
    item.joins, item.is_binds = joins, True
    # (visto) tempinfos: 281 "Socket a Gem" = tipo 18 ("[Blacksmith] > [Socket]")
    quests = rules.quest_event(snap, templates, GEM_INLAY, MOSAIC_PARA1, 1) if gem == GEM else []
    await s.ctx.characters.save(c, item, *changed, *back, *quests, delete=tuple(gone))

    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    send(s, S_ITEMS, bag.moved([item], s.player_id))
    # (visto) 231733 #1392-#1397: 115 da pedra, 115 do item, 112 da missão, o 111 e o 83 com o mesmo texto
    if quests:
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    if old > 0:
        send(s, 111, pb.ChatChannelMsg(channel=7, encodeMsg="Swap Successful"))
    else:
        alert(s, "Successfully Socketed Gem!")


def _removed(s: GameSession, gem: int) -> None:
    """(visto) oficial_20261024-121659-1 #306-#318 e #326-#339: 4476/4426/4484, 111 "Remove successful!" e 83
    "Removal successful! You received: Lvl. 1 Charisma Gem x1!"."""
    _gained(s)
    send(s, 111, pb.ChatChannelMsg(channel=7, encodeMsg="Remove successful!"))
    text = f"Removal successful! You received: {bag.name(s.ctx.templates, gem)} x1!"
    send(s, 83, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(5152)
async def inlay_join(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """``operate`` true: abre o furo ``holePos`` com um Socketing Rod (o 4º só em item Profile 5).
    false: tira a pedra do furo (custa o Property3 dela em ouro) e devolve para a mochila.
    Equipamento de mascote: Soul Socketing Rod, e o furo abre só abaixo do ``Profile`` (``PetEquipGodHeadView``:
    estado 1 = pode abrir quando ``Profile − 1 > índice``)."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    found = _any_equip(s)
    if found is None or not 1 <= msg.holePos <= 4:
        s.log.info("5152 recusado", pedido=str(msg))
        return
    item, row = found
    joins = item.joins
    hole = joins[msg.holePos - 1]
    if msg.operate:
        pet, profile = _pet(row), int(row.get("Profile") or 0)
        allowed = hole == -1 and (msg.holePos < profile if pet else msg.holePos < 4 or profile == 5)
        drill = SOUL_DRILL if pet else DRILL
        if not allowed or bag.count_of(snap, drill) < 1:
            s.log.info("5152 recusado: furo", pedido=str(msg), furo=hole)
            return
        changed, gone = bag.take(snap, drill, 1)
        joins[msg.holePos - 1] = 0
        item.joins = joins
        await s.ctx.characters.save(item, *changed, delete=tuple(gone))
        send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
        send(s, S_ITEMS, bag.moved([item], s.player_id))
        # (visto) oficial_20261024-121659-1 #434-#437: 115 da broca, 115 do item e o 111, sem 83
        send(s, 111, pb.ChatChannelMsg(channel=7, encodeMsg="Socket open successfully!"))
        return
    stone_row = templates.get("ItemTempInfos", hole) if hole > 0 else None
    cost = int(stone_row.get("Property3") or 0) if stone_row else 0
    if stone_row is None or c.gold < cost or not bag.fits(snap, templates, [(hole, 1)], now):
        s.log.info("5152 recusado: sem pedra/ouro/espaço", pedido=str(msg))
        return
    c.gold -= cost
    joins[msg.holePos - 1] = 0
    item.joins = joins
    back = bag.add(snap, templates, hole, 1, now)
    await s.ctx.characters.save(c, item, *back)

    # (visto) oficial_20261024-121659-1 #322-#339: 109, 115 do item, 115 da pedra, 4476/4426/4484, 111 e 83
    castle_yield(s)
    send(s, S_ITEMS, bag.moved([item], s.player_id))
    send(s, S_ITEMS, bag.moved(back, s.player_id))
    _removed(s, hole)


# --- composição ---


@router.on(5153)
async def compose(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """Receita de ``ComposeTempInfos``: Material1..4 × Count × ``composeNum`` + NeedGold → NewMaterial."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    recipe = templates.get("ComposeTempInfos", msg.composeId, key="Id")
    if recipe is not None and recipe.get("Types") in (HERO_UPGRADE, PET_UPGRADE):
        await _upgrade(s, recipe, msg)
        return
    n = msg.composeNum
    if recipe is None or not 1 <= n <= MAX_COMPOSE or msg.autoBuy:  # ponytail: autoBuy (comprar o que falta) não
        s.log.info("5153 recusado", pedido=str(msg))
        return
    need = [
        (int(recipe[f"Material{i}"]), int(recipe[f"Count{i}"]) * n)
        for i in range(1, 5)
        if int(recipe.get(f"Material{i}") or 0) > 0
    ]
    product, made = int(recipe["NewMaterial"]), int(recipe.get("Counts") or 1) * n
    gold = int(recipe.get("NeedGold") or 0) * n
    has = all(bag.count_of(snap, tid) >= count for tid, count in need)
    level_ok = c.grades >= int(recipe.get("NeedMinLevel") or 0)
    # ponytail: o espaço é conferido antes de consumir (pode recusar quando os materiais liberariam lugar)
    if not (has and level_ok and c.gold >= gold and templates.get("ItemTempInfos", product)):
        s.log.info("5153 recusado: material/nível/ouro", pedido=str(msg))
        return
    if not bag.fits(snap, templates, [(product, made)], now):
        s.log.info("5153 recusado: mochila cheia", pedido=str(msg))
        return
    changed: list[Item] = []
    gone: list[Item] = []
    for tid, count in need:
        ch, go = bag.take(snap, tid, count)
        changed += ch
        gone += go
    c.gold -= gold
    got = bag.add(snap, templates, product, made, now)
    changed = [i for i in changed if i not in got]
    # (visto) tempinfos: 311 "Synthesize a Gem" = tipo 19, Para1 0, Para2 1; (visto, só turco:
    # degerli_tas_birlestirme) 5153 gera pedras;
    # só conta pedra (SonType 205); cada receita conta 1 (dedução)
    product_row = templates.get("ItemTempInfos", product)
    gem = product_row is not None and product_row.get("SonType") == GEM
    quests = rules.quest_event(snap, templates, GEM_COMPOSE, 0, 1) if gem else []
    await s.ctx.characters.save(c, *changed, *got, *quests, delete=tuple(gone))

    # (visto) oficial_20261023-231733-1 #1493-#1511: 115, 109, 109 (iguais), 115, 4476, 4426, 4484 ×9, 111, 112, 89, 83
    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    castle_yield(s)
    castle_yield(s)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    _gained(s)
    text = f"Received: {bag.name(templates, product)} x{made}"  # (visto) #1508 "Received: Lvl. 2 HP Gem x1"
    send(s, 111, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    if quests:
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    send(s, S_COMPOSE, pb.StoreRspMsg(composeResult=False, composeTemplateId=-1))  # como o oficial
    send(s, 83, pb.ChatChannelMsg(channel=3, encodeMsg=text))


def _upgrade_piece(s: GameSession, recipe: Row) -> Item | None:
    """A peça do avanço (``Material1``). Mascote: a da bancada, com o encantamento no máximo ("Only fully enchanted
    equipment can be upgraded"). Herói: a equipada no líder primeiro ("Equipped items ... will be used first",
    ``StoreModel.getCurrentUpgradeEquipGoodsInfo``), senão a da mochila."""
    snap = s.snapshot
    assert snap is not None
    tid = int(recipe.get("Material1") or 0)
    if recipe.get("Types") == PET_UPGRADE:
        found = _equip(s, PET_EQUIP)
        ok = found is not None and found[0].template_id == tid
        return found[0] if found and ok and found[0].mould_grade >= int(found[1].get("StrengthenMax") or 0) else None
    leader = snap.leader
    worn = (i for i in snap.items if i.bag_type == BagType.HERO and leader and i.object_id == leader.id)
    return next((i for i in worn if i.template_id == tid), None) or next(
        (i for i in bag.in_bag(snap) if i.template_id == tid), None
    )


async def _upgrade(s: GameSession, recipe: Row, msg: pb.StoreReqMsg) -> None:
    """Avanço (5153 com receita Types 5/10): a **mesma** peça troca de template e herda o reforço, os furos (com o
    furo extra do template novo, ``Property1``) e os atributos sorteados (``helpContent03``; a prévia do
    ``PetEquipUpgradeView`` monta o item novo com o mesmo ``id``, joins e randomSkills). No mascote o encantamento
    volta a 0 (``mouldGrade = 0`` na prévia). Materiais 2..4 da mochila e ``NeedGold``; no mascote o que faltar do
    material sai em Balens pelo ``Point`` da loja ("Spend {0} Balens to instantly upgrade?"). Fica vinculada. O 89
    vai com ``composeResult`` true: o ``PetEquipUpgradeView`` só fecha com ele, e o ``StoreControler`` não lê."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    piece, pet = _upgrade_piece(s, recipe), recipe.get("Types") == PET_UPGRADE
    new_row = templates.get("ItemTempInfos", int(recipe.get("NewMaterial") or 0))
    need = [
        (int(recipe[f"Material{i}"]), int(recipe[f"Count{i}"]))
        for i in range(2, 5)
        if int(recipe.get(f"Material{i}") or 0)
    ]
    have = {tid: min(n, bag.count_of(snap, tid)) for tid, n in need}
    missing = sum((n - have[tid]) * _shop_point(s, tid) for tid, n in need) if pet else 0
    short = any(have[tid] < n and (not pet or not _shop_point(s, tid)) for tid, n in need)
    gold = int(recipe.get("NeedGold") or 0)
    level_ok = c.grades >= int(recipe.get("NeedMinLevel") or 0)
    if piece is None or new_row is None or short or not level_ok or c.gold < gold:
        s.log.info("5153 avanço recusado", pedido=str(msg), peca=piece is not None)
        return
    ledger = cash.pay(c, missing, msg.payType, "upgrade", f"upgrade:{piece.template_id}", now) if missing else None
    if missing and ledger is None:
        s.log.info("5153 avanço recusado: Balens", pedido=str(msg), custo=missing)
        return
    changed: list[Item] = []
    gone: list[Item] = []
    for tid, n in have.items():
        ch, go = bag.take(snap, tid, n) if n else ([], [])
        changed += ch
        gone += go
    c.gold -= gold
    holes = min(4, int(new_row.get("Property1") or 0))
    piece.joins = [0 if j == -1 and n < holes else j for n, j in enumerate(piece.joins)]
    piece.template_id, piece.is_binds = int(recipe["NewMaterial"]), True
    if pet:
        piece.mould_grade, piece.bless_value = 0, 0
    await s.ctx.characters.save(c, piece, *changed, *([ledger] if ledger else []), delete=tuple(gone))

    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    castle_yield(s)
    if ledger is not None:
        _player(s)
    send(s, S_ITEMS, bag.moved([piece], s.player_id))
    if piece.bag_type == BagType.HERO:
        _player(s)
        _army(s)
    if not pet:  # o texto do mascote o cliente monta ("Upgrade successful, received {0} x1")
        text = f"Received: {bag.name(templates, piece.template_id)} x1"
        send(s, 111, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        send(s, 83, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    send(s, S_COMPOSE, pb.StoreRspMsg(composeResult=True, composeTemplateId=piece.template_id))


# --- refino dos atributos sorteados ---


@router.on(8336)
async def refresh_random(s: GameSession, msg: pb.SmithFreshReqMsg) -> None:
    """Sorteia os atributos do item da bancada (``RefreshView``). Gasta as pedras de refino dele
    (``ItemTempInfo.Refresh``) pelo ``Profile`` (``RESOLVE_STONES``): ``bindType`` 0 as vinculadas primeiro (e o
    equipamento livre fica vinculado, ``Store.IntensifyView.Tip``), 2 só as livres. ``lock[i]`` mantém o atributo i:
    cada cadeado gasta um Refinement Lock e o que faltar custa 45 Balens (``payType`` 0 vinculado primeiro); travar
    todos é recusado ("No Stats to Refine"). Equipamento travado não refina. O resultado só vale depois do 8339."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    found = _any_equip(s)
    stone = int(found[1].get("Refresh") or 0) if found else 0
    slots = int(found[1].get("RandomSkillCount") or 0) if found else 0
    if found is None or found[0].is_locked or stone <= 0 or slots <= 0:
        s.log.info("8336 recusado", pedido=str(msg))
        return
    item, row = found
    pet, profile = _pet(row), int(row.get("Profile") or 0)
    need = PET_STONES.get(profile, 100) if pet else RESOLVE_STONES.get(profile, 1)
    bound = sum(i.count for i in bag.in_bag(snap) if i.template_id == stone and i.is_binds)
    use_bound = 0 if msg.bindType == UNBOUND_ONLY else min(bound, need)
    locks = (list(msg.lock) + [False] * 5)[:slots]
    # o PetEquipRefineryView não usa o Refinement Lock: cada cadeado é pago (mostra 45 Balens)
    lock_items = 0 if pet else min(sum(locks), bag.count_of(snap, LOCK_ITEM))
    balens = (sum(locks) - lock_items) * LOCK_PRICE
    loose = bag.count_of(snap, stone) - bound
    # mascote: as pedras que faltam saem em Balens ("auto buy" da tela), pelo Point da loja
    buy = max(0, need - use_bound - loose) if pet else 0
    balens += buy * _shop_point(s, stone) if buy else 0
    enough = loose >= need - use_bound - buy and (not buy or _shop_point(s, stone) > 0)
    rolled = sum(k > 0 for k in item.random_skills)
    if not enough or (rolled and sum(locks) >= rolled):  # tudo travado: "No Stats to Refine"
        s.log.info("8336 recusado: pedras/cadeados", pedido=str(msg), pedras=need)
        return
    ledger = cash.pay(c, balens, msg.payType, "refine", f"refine:{item.template_id} cadeados", now) if balens else None
    if balens and ledger is None:
        s.log.info("8336 recusado: Balens dos cadeados", pedido=str(msg), custo=balens)
        return
    changed: list[Item] = []
    gone: list[Item] = []
    for tid, n, binds in (
        (stone, use_bound, True),
        (stone, need - use_bound - buy, False),
        (LOCK_ITEM, lock_items, None),
    ):
        ch, go = bag.take(snap, tid, n, binds) if n else ([], [])
        changed += ch
        gone += go
    if use_bound and not item.is_binds:
        item.is_binds = True
        changed.append(item)
    # TODO(inventado): o refino sorteia como o item novo (``bag.roll_random_skill``: faixa do nível do item, tipos
    # distintos dos travados e dos já sorteados); falta captura 8336 -> 4258 para conferir. Mascote: uniforme entre
    # todos os atributos com Grades > 0
    need, rng, pool = int(row.get("NeedGrades") or 0), random.Random(), bag.random_skill_pool(s.ctx.templates)
    skills = [cur if locks[i] else 0 for i, cur in enumerate(item.random_skills[:slots])]
    for i, cur in enumerate(skills):
        if cur:
            continue
        taken = [k // 100 for k in skills if k]
        skills[i] = rng.choice(pool) if pet else bag.roll_random_skill(s.ctx.templates, need, rng, taken)
    _pending[item.id or 0] = skills
    # (visto) tempinfos: 769 "Refine a Piece of Equipment" = tipo 47, Para1 0, Para2 1; conta no 8336, não no 8339
    # (dedução)
    quests = rules.quest_event(snap, s.ctx.templates, REFINE, 0, 1)
    await s.ctx.characters.save(c, *changed, *quests, *([ledger] if ledger else []), delete=tuple(gone))

    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    if ledger is not None:
        _player(s)
    send(s, S_REFRESH, pb.SmithFreshRspMsg(randomSkill=skills))
    if quests:
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(8339)
async def refresh_replace(s: GameSession, _: object) -> None:
    """Aceita o último sorteio do 8336 no item da bancada."""
    found = _any_equip(s)
    skills = _pending.pop(found[0].id or 0, None) if found else None
    if found is None or skills is None:
        s.log.info("8339 recusado: nada sorteado")
        send(s, S_REPLACE, pb.SmithFreshReplaceRspMsg(result=False))
        return
    item = found[0]
    item.random_skills = skills + item.random_skills[len(skills) :]
    await s.ctx.characters.save(item)
    send(s, S_REPLACE, pb.SmithFreshReplaceRspMsg(result=True))
    send(s, S_ITEMS, bag.moved([item], s.player_id))


@router.on(8464)
async def refresh_property(s: GameSession, msg: pb.RefreshPropertyReqMsg) -> None:
    """Atributos sorteados de um item (o pendente do 8336, se houver), sem cadeados."""
    snap = s.snapshot
    assert snap is not None
    item = next((i for i in snap.items if i.id == msg.itemId), None)
    if item is None:
        send(s, S_REFRESH_PROPERTY, pb.RefreshPropertyRepMsg(result=0))
        return
    skills = _pending.get(item.id or 0, item.random_skills)
    send(s, S_REFRESH_PROPERTY, pb.RefreshPropertyRepMsg(randomSkill=skills, lockPos=[False] * len(skills), result=1))


@router.on(8340)
async def resolve(s: GameSession, _: object) -> None:
    """Decompõe os equipamentos da bancada (posições 0..11, ``ResolveView``): 1.000 de ouro cada; cada um dá a pedra
    de refino dele (``ItemTempInfo.Refresh``) pelo ``Profile`` (``RESOLVE_STONES``), com o vínculo do equipamento
    (``helpContent05``: "Recycling unbound equipment will produce unbound Refinement Crystals"). Só equipamento sem
    pedra (``StoreBagCellDropMediator.isResolePoint``) e sem cadeado. Recusa: não responde (o ``ResolveView`` limpa a
    bancada com qualquer 4260, até com ``result`` false, e os itens ficariam lá sem aparecer)."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    equips = [i for i in bag.in_bag(snap, BagType.STORE) if i.object_id == 0 and 0 <= i.pos < bag.STORE_SIZE]
    rows = [templates.get("ItemTempInfos", i.template_id) or {} for i in equips]
    stones: dict[tuple[int, bool], int] = {}
    for item, row in zip(equips, rows, strict=True):
        tid, n = int(row.get("Refresh") or 0), RESOLVE_STONES.get(int(row.get("Profile") or 0), 0)
        if tid > 0 and n:
            stones[tid, item.is_binds] = stones.get((tid, item.is_binds), 0) + n
    gold = RESOLVE_GOLD * len(equips)
    bad = any(
        r.get("MasterType") != EQUIP or i.is_locked or any(j > 0 for j in i.joins)
        for i, r in zip(equips, rows, strict=True)
    )
    goods = [(tid, n, binds) for (tid, binds), n in stones.items()]
    if not equips or bad or c.gold < gold or not bag.fits(snap, templates, goods, now):
        s.log.info("8340 recusado", itens=[i.template_id for i in equips], ouro=c.gold)
        return
    for item in equips:
        snap.items.remove(item)
    c.gold -= gold
    got = [i for tid, n, binds in goods for i in bag.add(snap, templates, tid, n, now, binds=binds)]
    await s.ctx.characters.save(c, *got, delete=tuple(equips))

    send(s, S_ITEMS, bag.moved(got, s.player_id, empty=equips))
    castle_yield(s)
    send(s, S_RESOLVE, pb.SmithResolveRspMsg(result=True))


# --- conversão de pedras ---


@router.on(8538)
async def transform(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """Troca ``count`` pedras ``srcItemid`` por outra do mesmo nível (``TransformInfos``), CostGold cada."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    level = next(
        (
            r
            for r in templates.rows("TransformInfos")
            if {str(msg.srcItemid), str(msg.desItemid)} <= {r.get(f"Material{i}") for i in range(1, 9)}
        ),
        None,
    )
    n, gold = msg.count, (int(level.get("CostGold") or 0) * msg.count if level else 0)
    ok = level is not None and msg.srcItemid != msg.desItemid and 1 <= n <= MAX_COMPOSE
    if not ok or bag.count_of(snap, msg.srcItemid) < n or c.gold < gold:
        s.log.info("8538 recusado", pedido=str(msg))
        return
    if not bag.fits(snap, templates, [(msg.desItemid, n)], now):  # conferido antes de consumir
        s.log.info("8538 recusado: mochila cheia", pedido=str(msg))
        return
    changed, gone = bag.take(snap, msg.srcItemid, n)
    c.gold -= gold
    got = bag.add(snap, templates, msg.desItemid, n, now)
    await s.ctx.characters.save(c, *changed, *got, delete=tuple(gone))

    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    castle_yield(s)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    _gained(s)  # (só turco: degerli_tas_nitelik_sistemi #6-#7)
    # texto deduzido (sem fonte no cliente/captura); termo conversion do language.txt
    alert(s, "Conversion successful")


def mould_rate(item: Item) -> int:
    """``PetEquipStrengView.strengRate``: ``max(1, 50 − 10 × nível) + bênção``, no máximo 100."""
    return min(100, max(1, 50 - 10 * item.mould_grade) + item.bless_value)


def _shop_point(s: GameSession, template_id: int) -> int:
    """Preço em Balens do material (a linha ShopType 99; as outras linhas do mesmo item têm ``Point`` 0)."""
    rows = s.ctx.templates.find("ShopTempInfos", ItemId=str(template_id))
    return max((int(r.get("Point") or 0) for r in rows), default=0)


@router.on(8644)
async def mould(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Encantamento do equipamento de mascote na bancada (``PetEquipStrengView``): gasta 3 Light of Magic e 3 Glint
    of Magic da mochila, e o que faltar sai em Balens (``payType`` 0 vinculado primeiro, 1 só Balens; o cliente pede a
    confirmação). Taxa ``mould_rate``; sucesso: nível +1; falha: bênção +5 abaixo do nível 10, +3 depois
    ("Enchantment failed, Enchantment Blessing +{0}"), até 100. O item fica vinculado (``Store.IntensifyView.Tip``).
    O preço do que falta é o ``Point`` da loja (80): o cliente soma o ``GiftToken`` dela, que é 0 nos templates.
    ponytail: a bênção zera no sucesso (o cliente não diz; a barra recomeça do 0 no próximo nível)."""
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    found = _equip(s, PET_EQUIP)
    if found is None or found[0].mould_grade >= int(found[1].get("StrengthenMax") or 0):
        s.log.info("8644 recusado", pedido=str(msg))
        return
    item = found[0]
    have = {tid: min(MOULD_COST, bag.count_of(snap, tid)) for tid in MOULD_ITEMS}
    cost = sum((MOULD_COST - n) * _shop_point(s, tid) for tid, n in have.items())
    ledger = cash.pay(c, cost, msg.payType, "pet_mould", f"mould:{item.template_id}", now) if cost else None
    if cost and ledger is None:
        s.log.info("8644 recusado: Balens", pedido=str(msg), custo=cost)
        return
    changed: list[Item] = []
    gone: list[Item] = []
    for tid, n in have.items():
        ch, go = bag.take(snap, tid, n) if n else ([], [])
        changed += ch
        gone += go
    ok = random.randint(1, 100) <= mould_rate(item)
    if ok:
        item.mould_grade, item.bless_value = item.mould_grade + 1, 0
    else:
        item.bless_value = min(BLESS_MAX, item.bless_value + (5 if item.mould_grade < 10 else 3))
    item.is_binds = True
    await s.ctx.characters.save(c, item, *changed, *([ledger] if ledger else []), delete=tuple(gone))

    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    if ledger is not None:
        _player(s)
    send(s, S_ITEMS, bag.moved([item], s.player_id))
    send(s, S_MOULD, pb.StoreRspMsg(strengResult=ok, pos=0, bagType=BagType.STORE))
