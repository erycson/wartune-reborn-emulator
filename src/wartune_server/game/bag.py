"""Mochila no snapshot em memória: espaços, empilhar, consumir e montar os 115.

Nada aqui grava: quem chama altera o snapshot antes de qualquer ``await``, grava tudo numa ``save`` e
depois manda os pacotes. Regras do cliente: ``PlayerInfo.bagTotalCount`` (42 + comprados, 217 com a
mochila alugada), ``GoodsSonType.getSonTypePos`` (espaço do herói por SonType) e ``GoodsCheck``.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from ..domain.models import BagType, Character, Item, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from .builders.player import item_moved

BAG_BASE = 42  # PlayerInfo.bagDefaultCount
RENTAL_SIZE = 217  # PlayerInfo.PLAYER_BAG_MAX_1 (mochila alugada)
STORE_SIZE = 12  # bancada: 0 equipamento, 1 pedra da sorte; 0..11 na decomposição
RANDOM_SKILLS = range(70000, 77200)  # SkillTempInfos dos atributos sorteados (randomSkill)
_random_pool: list[int] = []
# GoodsSonType.getSonTypePos: posições do equipamento do herói (bagType 4)
HERO_SLOTS = {
    101: (0,),
    103: (1,),
    104: (2,),
    106: (3,),
    107: (4, 5),
    108: (6, 7),
    109: (8,),
    110: (9,),
    112: (10,),
    111: (11,),
    117: (12,),
    118: (13,),
}
RUNE, HONOR_MASTER = 214, 3  # SonType das runas (bagType 2); MasterType das medalhas (bagType 3)
RUNE_LEVELS = (20, 30, 40)  # GoodsManager.getEmputyBattleRunesPos: 1 espaço a cada nível desses
GOLD, STRATEGY, POINT, GIFT = -100, -300, -400, -500  # TemplateId < 0 nas recompensas


def rental_active(c: Character, now: datetime) -> bool:
    return c.rental_bag_until is not None and c.rental_bag_until > now


def capacity(c: Character, now: datetime) -> int:
    return RENTAL_SIZE if rental_active(c, now) else BAG_BASE + c.bag_count


def at(snap: PlayerSnapshot, bag: int, obj: int, pos: int) -> Item | None:
    return next((i for i in snap.items if (i.bag_type, i.object_id, i.pos) == (bag, obj, pos)), None)


def in_bag(snap: PlayerSnapshot, bag: int = BagType.BAG) -> list[Item]:
    return [i for i in snap.items if i.bag_type == bag]


def free_positions(snap: PlayerSnapshot, now: datetime) -> list[int]:
    used = {i.pos for i in in_bag(snap)}
    return [p for p in range(capacity(snap.character, now)) if p not in used]


def count_of(snap: PlayerSnapshot, template_id: int) -> int:
    return sum(i.count for i in in_bag(snap) if i.template_id == template_id)


def random_skill_pool(templates: GameTemplates) -> list[int]:
    """Atributos que o refino (8336) e a carta da masmorra sorteiam."""
    # Grades 0 são placeholders (+0 com valor 500000, "Asker Miktarı" inteiro): nenhum dos 42 atributos
    # sorteados nas capturas tem Grades 0; os demais têm 1 a 10
    if not _random_pool:
        _random_pool.extend(
            int(r["TemplateId"])
            for r in templates.rows("SkillTempInfos")
            if int(r["TemplateId"]) in RANDOM_SKILLS
            and int(r.get("Grades") or 0) > 0
            and templates.get("SkillPropertyTempInfos", int(r["TemplateId"]))
        )
    return _random_pool


def max_count(templates: GameTemplates, template_id: int) -> int:
    row = templates.get("ItemTempInfos", template_id)
    return max(1, int(row.get("MaxCount", 1))) if row else 1


def new_item(snap: PlayerSnapshot, templates: GameTemplates, template_id: int, count: int = 1) -> Item:
    """Item novo como o oficial cria: equipamento nasce com ``Property1`` furos abertos (``join`` 0)."""
    row = templates.get("ItemTempInfos", template_id) or {}
    item = Item(snap.character.id or 0, template_id, count=count)
    # ponytail: o oficial sorteia randomSkill_1..N (RandomSkillCount); a tabela do sorteio não está nos
    # templates, então vai o DefaultSkill (vazio = nenhum)
    item.random_skill = int((row.get("DefaultSkill") or "0").split(",")[0] or 0)
    if row.get("MasterType") == "1":
        holes = min(4, int(row.get("Property1") or 0))
        item.joins = [0] * holes + [-1] * (4 - holes)
    return item


def fits(
    snap: PlayerSnapshot, templates: GameTemplates, goods: Iterable[tuple[int, int]], now: datetime, valid: int = 0
) -> bool:
    """Cabe tudo na mochila (empilhando onde der)? ``goods`` = (templateId, quantidade), moedas ignoradas.
    ``valid`` > 0: item com validade, não entra nas pilhas que já existem (cada um tem o seu relógio)."""
    free = len(free_positions(snap, now))
    room: dict[int, int] = {}
    for tid, count in goods:
        if tid < 0:
            continue
        top = max_count(templates, tid)
        if tid not in room:
            room[tid] = (
                0 if valid else sum(top - i.count for i in in_bag(snap) if i.template_id == tid and i.count < top)
            )
        use = min(room[tid], count)
        room[tid] -= use
        count -= use
        while count > 0:
            free -= 1
            room[tid] += max(0, top - count)
            count -= top
        if free < 0:
            return False
    return True


def add(
    snap: PlayerSnapshot, templates: GameTemplates, template_id: int, count: int, now: datetime, valid: int = 0
) -> list[Item]:
    """Põe ``count`` na mochila: completa as pilhas que já existem e abre espaços novos.

    ``valid``: minutos de validade (``ShopTempInfos.ValidDate``) contados de ``now``; com validade não empilha.
    Devolve os itens alterados/criados. Chame ``fits`` antes: sem espaço o resto é descartado.
    """
    top, changed = max_count(templates, template_id), []
    for item in [] if valid else sorted(in_bag(snap), key=lambda i: i.pos):
        if count <= 0:
            break
        if item.template_id == template_id and item.count < top:
            use = min(top - item.count, count)
            item.count += use
            count -= use
            changed.append(item)
    for pos in free_positions(snap, now):
        if count <= 0:
            break
        item = new_item(snap, templates, template_id, min(top, count))
        item.pos = pos
        if valid:
            item.valid_date, item.begin_date = valid, now
        count -= item.count
        snap.items.append(item)
        changed.append(item)
    return changed


def expire(snap: PlayerSnapshot, now: datetime) -> list[Item]:
    """Tira do snapshot os itens vencidos de qualquer bolsa (mochila, herói, medalha). Devolve os apagados."""
    gone = [i for i in snap.items if i.expired(now)]
    for item in gone:
        snap.items.remove(item)
    return gone


def take(snap: PlayerSnapshot, template_id: int, count: int) -> tuple[list[Item], list[Item]]:
    """Consome ``count`` das pilhas da mochila (as menores primeiro). Devolve (alterados, apagados)."""
    changed, gone = [], []
    for item in sorted((i for i in in_bag(snap) if i.template_id == template_id), key=lambda i: (i.count, i.pos)):
        if count <= 0:
            break
        use = min(item.count, count)
        item.count -= use
        count -= use
        if item.count == 0:
            snap.items.remove(item)
            gone.append(item)
        else:
            changed.append(item)
    return changed, gone


def take_one(snap: PlayerSnapshot, item: Item, count: int = 1) -> bool:
    """Consome ``count`` de uma pilha específica; True se ela acabou (apague-a)."""
    item.count -= count
    if item.count <= 0:
        snap.items.remove(item)
        return True
    return False


def moved(items: Iterable[Item], player_id: int, empty: Iterable[Item] = ()) -> pb.ItemMovedListMsg:
    """Um 115 com os itens (posição atual) e as posições que ficaram vazias."""
    msg = pb.ItemMovedListMsg()
    for item in empty:
        msg.moved.extend(item_moved(item.bag_type, item.object_id, item.pos, None, player_id).moved)
    for item in items:
        msg.moved.extend(item_moved(item.bag_type, item.object_id, item.pos, item, player_id).moved)
    return msg


def name(templates: GameTemplates, template_id: int) -> str:
    return (templates.get("ItemTempInfos", template_id) or {}).get("TemplateName", str(template_id))


def fits_hero(snap: PlayerSnapshot, row: Row, job: int, sex: int) -> bool:
    """``GoodsCheck.checkGoodsCanEquip`` + ``isGradeFix``: classe, sexo e nível do herói."""
    jobs = {int(j) for j in (row.get("Job") or "0").split(",") if j}
    sexs = int(row.get("Sexs", 2))
    need = int(row.get("NeedGrades", 0))
    leader = snap.leader
    return (0 in jobs or job in jobs) and sexs in (2, sex) and leader is not None and leader.grades >= need


def hero_slot_ok(snap: PlayerSnapshot, row: Row, bag: int, pos: int) -> bool:
    """O item pode ocupar ``pos`` naquela bolsa do herói?"""
    son, master = int(row.get("SonType", 0)), int(row.get("MasterType", 0))
    if bag == BagType.HERO:
        return master == 1 and pos in HERO_SLOTS.get(son, ())
    if bag == BagType.RUNE:
        leader = snap.leader
        open_slots = sum((leader.grades if leader else 0) >= g for g in RUNE_LEVELS)
        return son == RUNE and 0 <= pos < open_slots
    if bag == BagType.HONOR:
        return master == HONOR_MASTER and pos == 0
    return False
