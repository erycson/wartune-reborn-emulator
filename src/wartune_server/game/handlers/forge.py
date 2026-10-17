"""Forja (bancada = bagType 0): reforço (5150), engaste (5151/5152), composição (5153), refino
(8336/8339/8464), decomposição (8340), conversão de pedras (8538), moldagem (8644).
Ver ``docs/itens.md``.

A bancada guarda o equipamento na posição 0 e a pedra da sorte na 1; o cliente põe e tira os itens
com o 5005. Fórmulas do cliente: ``GoodsHelp.getStrengthenGold``/``StoreIntensifyView``.
"""

from __future__ import annotations

import random

from ...domain.models import BagType, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates, Row
from .. import bag, rules
from ..builders.player import quest_update
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .shop import alert, send

S_ITEMS, S_STRENGTHEN, S_COMPOSE = 115, 86, 89
S_REFRESH, S_REPLACE, S_RESOLVE, S_REFRESH_PROPERTY = 4258, 4259, 4260, 4368
S_QUESTS = 112  # QuestUpdatedRspMsg
STRENGTHEN, GEM_INLAY, GEM_COMPOSE, REFINE = 17, 18, 19, 47  # QuestCondictionInfos.CondictionType
LUCK, GEM, DRILL = "204", "205", 208004  # SonType da pedra da sorte e das pedras; Elmas Delici
EQUIP = "1"  # MasterType dos equipamentos
MAX_COMPOSE = 999

# ponytail: o refino sorteado fica na memória até o 8339 (some se o servidor reiniciar)
_pending: dict[int, list[int]] = {}


def _store(snap: PlayerSnapshot, pos: int = 0) -> Item | None:
    return bag.at(snap, BagType.STORE, 0, pos)


def _equip(s: GameSession) -> tuple[Item, Row] | None:
    """Equipamento na posição 0 da bancada."""
    snap = s.snapshot
    assert snap is not None
    item = _store(snap)
    row = s.ctx.templates.get("ItemTempInfos", item.template_id) if item else None
    return (item, row) if item is not None and row is not None and row.get("MasterType") == EQUIP else None


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
    """Reforço: a pedra da sorte é gasta mesmo na falha e a falha não baixa o nível."""
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
    if ok:
        item.strengthen_grade += 1
        changed.append(item)
    quests = rules.quest_event(snap, templates, STRENGTHEN, item.strengthen_grade, 1) if ok else []
    await s.ctx.characters.save(c, *changed, *quests, delete=tuple(gone))

    if luck is not None:
        send(s, S_ITEMS, bag.moved([i for i in changed if i is luck], s.player_id, empty=gone))
    castle_yield(s)
    if ok:
        send(s, S_ITEMS, bag.moved([item], s.player_id))
    out = pb.StoreRspMsg(strengResult=ok, strengthenGrade=item.strengthen_grade, pos=0, bagType=BagType.STORE)
    send(s, S_STRENGTHEN, out)
    if quests:
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


# --- engaste ---


def _gem_types(templates: GameTemplates, item: Item, skip: int) -> set[str]:
    rows = (templates.get("ItemTempInfos", j) for n, j in enumerate(item.joins, 1) if j > 0 and n != skip)
    return {r.get("Property1", "") for r in rows if r is not None}


@router.on(5151)
async def inlay(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """Engasta a pedra (``bagType``/``bagPos``) no furo ``mountPos`` (1..4) do item da bancada.
    Furo aberto e vazio: grátis. Ocupado: troca, cobrando o ouro para tirar a antiga (Property3),
    que volta para a mochila. Nunca duas pedras do mesmo atributo no item."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    found = _equip(s)
    stone = bag.at(snap, msg.bagType, 0, msg.bagPos) if msg.bagType == BagType.BAG else None
    stone_row = templates.get("ItemTempInfos", stone.template_id) if stone else None
    ok = found is not None and stone is not None and stone_row is not None and stone_row.get("SonType") == GEM
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
    gone = [stone] if bag.take_one(snap, stone, 1) else []
    changed = [] if gone else [stone]
    back = bag.add(snap, templates, old, 1, now) if old > 0 else []
    joins[msg.mountPos - 1] = stone.template_id
    item.joins = joins
    # (visto) tempinfos: 281 = tipo 18, Para1 1; (visto) captura atolye_item_basma_ve_mozaik: "mozaik yapıldı";
    # Para1 comparado ao Property1 da pedra (dedução)
    quests = rules.quest_event(snap, templates, GEM_INLAY, int(stone_row.get("Property1") or 0), 1)
    await s.ctx.characters.save(c, item, *changed, *back, *quests, delete=tuple(gone))

    castle_yield(s)
    send(s, S_ITEMS, bag.moved([*changed, *back], s.player_id, empty=gone))
    send(s, S_ITEMS, bag.moved([item], s.player_id))
    alert(s, "Başarıyla mozaik yapıldı!")
    if quests:
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(5152)
async def inlay_join(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """``operate`` true: abre o furo ``holePos`` com um Elmas Delici (o 4º só em item Profile 5).
    false: tira a pedra do furo (custa o Property3 dela em ouro) e devolve para a mochila."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    found = _equip(s)
    if found is None or not 1 <= msg.holePos <= 4:
        s.log.info("5152 recusado", pedido=str(msg))
        return
    item, row = found
    joins = item.joins
    hole = joins[msg.holePos - 1]
    if msg.operate:
        allowed = hole == -1 and (msg.holePos < 4 or row.get("Profile") == "5")
        if not allowed or bag.count_of(snap, DRILL) < 1:
            s.log.info("5152 recusado: furo", pedido=str(msg), furo=hole)
            return
        changed, gone = bag.take(snap, DRILL, 1)
        joins[msg.holePos - 1] = 0
        item.joins = joins
        await s.ctx.characters.save(item, *changed, delete=tuple(gone))
        send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
        send(s, S_ITEMS, bag.moved([item], s.player_id))
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

    castle_yield(s)
    send(s, S_ITEMS, bag.moved([item], s.player_id))
    send(s, S_ITEMS, bag.moved(back, s.player_id))
    send(s, 111, pb.ChatChannelMsg(channel=7, encodeMsg="Başarıyla söküldü!"))
    send(s, 83, pb.ChatChannelMsg(channel=3, encodeMsg=f"Başarıyla söküldü! Kazanılan:{bag.name(templates, hole)} x1!"))


# --- composição ---


@router.on(5153)
async def compose(s: GameSession, msg: pb.StoreReqMsg) -> None:
    """Receita de ``ComposeTempInfos``: Material1..4 × Count × ``composeNum`` + NeedGold → NewMaterial."""
    snap = s.snapshot
    assert snap is not None
    c, templates, now = snap.character, s.ctx.templates, s.ctx.clock.now()
    recipe = templates.get("ComposeTempInfos", msg.composeId, key="Id")
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
    # (visto) tempinfos: 311 = tipo 19, Para1 0; (visto) captura degerli_tas_birlestirme: 5153 gera pedras;
    # só conta pedra (SonType 205); cada receita conta 1 (dedução)
    product_row = templates.get("ItemTempInfos", product)
    gem = product_row is not None and product_row.get("SonType") == GEM
    quests = rules.quest_event(snap, templates, GEM_COMPOSE, 0, 1) if gem else []
    await s.ctx.characters.save(c, *changed, *got, *quests, delete=tuple(gone))

    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    castle_yield(s)
    send(s, S_ITEMS, bag.moved(got, s.player_id))
    text = f"Kazanılan:{bag.name(templates, product)} x{made}"
    send(s, 111, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    send(s, S_COMPOSE, pb.StoreRspMsg(composeResult=False, composeTemplateId=-1))  # como o oficial
    send(s, 83, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if quests:
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


# --- refino dos atributos sorteados ---


@router.on(8336)
async def refresh_random(s: GameSession, msg: pb.SmithFreshReqMsg) -> None:
    """Sorteia os atributos do item da bancada gastando 1 pedra de refino (``ItemTempInfo.Refresh``);
    ``lock[i]`` mantém o atributo i. O resultado só vale depois do 8339."""
    snap = s.snapshot
    assert snap is not None
    found = _equip(s)
    stone = int(found[1].get("Refresh") or 0) if found else 0
    slots = int(found[1].get("RandomSkillCount") or 0) if found else 0
    if found is None or stone <= 0 or slots <= 0 or bag.count_of(snap, stone) < 1:
        s.log.info("8336 recusado", pedido=str(msg))
        return
    item = found[0]
    # ponytail: a tabela de sorteio do oficial não está nos templates: sorteio uniforme entre os atributos
    # com Grades > 0 (sem peso por nível: precisa de captura 8336 -> 4258); cadeados de graça (custo não achado)
    pool, locks = bag.random_skill_pool(s.ctx.templates), list(msg.lock) + [False] * 5
    skills = [cur if locks[i] else random.choice(pool) for i, cur in enumerate(item.random_skills[:slots])]
    changed, gone = bag.take(snap, stone, 1)
    _pending[item.id or 0] = skills
    # (visto) tempinfos: 769 = tipo 47, Para1 0; conta no 8336 (gasta a pedra), não no aceite 8339 (dedução)
    quests = rules.quest_event(snap, s.ctx.templates, REFINE, 0, 1)
    await s.ctx.characters.save(*changed, *quests, delete=tuple(gone))

    send(s, S_ITEMS, bag.moved(changed, s.player_id, empty=gone))
    send(s, S_REFRESH, pb.SmithFreshRspMsg(randomSkill=skills))
    if quests:
        send(s, S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(8339)
async def refresh_replace(s: GameSession, _: object) -> None:
    """Aceita o último sorteio do 8336 no item da bancada."""
    found = _equip(s)
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
    # decompor devolve materiais por uma tabela que não está nos templates nem no cliente:
    # recusa com result false (o cliente mostra a falha e não mexe nos itens)
    s.log.info("8340 recusado: sem tabela de decomposição")
    send(s, S_RESOLVE, pb.SmithResolveRspMsg(result=False))


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
    alert(s, "Dönüşüm başarılı")


@router.on(8644)
async def mould(s: GameSession, msg: pb.PayTypeMsg) -> None:
    # moldagem gasta os materiais 2120100-2120103, que não existem nos templates deste servidor
    # (recurso desligado no oficial também): sem resposta, como item que não pode ser moldado
    s.log.info("8644 recusado: moldagem sem materiais nos templates", pedido=str(msg))
