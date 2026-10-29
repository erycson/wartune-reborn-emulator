"""Mochila no snapshot em memória: espaços, empilhar, consumir e montar os 115.

Nada aqui grava: quem chama altera o snapshot antes de qualquer ``await``, grava tudo numa ``save`` e
depois manda os pacotes. Regras do cliente: ``PlayerInfo.bagTotalCount`` (42 + comprados, 217 com a
mochila alugada), ``GoodsSonType.getSonTypePos`` (espaço do herói por SonType) e ``GoodsCheck``.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import datetime
from functools import cache

from ..domain.models import BagType, Character, Item, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from .builders.player import item_moved

BAG_BASE = 42  # PlayerInfo.bagDefaultCount
RENTAL_SIZE = 217  # PlayerInfo.PLAYER_BAG_MAX_1 (mochila alugada)
STORE_SIZE = 12  # bancada: 0 equipamento, 1 pedra da sorte; 0..11 na decomposição
RANDOM_SKILLS = range(70000, 77200)  # SkillTempInfos dos atributos sorteados (randomSkill)
_random_pool: list[int] = []
# (dedução) os tipos 701-711 (Power ... Live): os sorteados nas capturas são 702-711 (711 só turco: Kronos' Authority);
# 701 é da mesma família (7xx01-7xx11); 721 e 751-771 ficam de fora. TODO(inventado): 701 entra sem amostra
RANDOM_TYPES = range(701, 712)
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
# GoodsSonType.getSonTypePos dos SonType 113-116: posições do equipamento do mascote (bagType 26)
PET_SLOTS = {113: (0, 1), 114: (2,), 115: (3, 4), 116: (5,)}
EQUIP_MASTER, PET_MASTER = "1", "5"  # ItemTempInfo.MasterType do equipamento do herói e do mascote
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
    # Grades 0 são placeholders (+0 com valor 500000, "Troop Count" inteiro): nenhum dos 7 atributos
    # sorteados na captura inglesa tem Grades 0 (têm 2 a 4); os demais têm 1 a 10
    if not _random_pool:
        _random_pool.extend(
            int(r["TemplateId"])
            for r in templates.rows("SkillTempInfos")
            if int(r["TemplateId"]) in RANDOM_SKILLS
            and int(r.get("Grades") or 0) > 0
            and templates.get("SkillPropertyTempInfos", int(r["TemplateId"]))
        )
    return _random_pool


@cache
def _bands(templates: GameTemplates) -> dict[int, list[list[int]]]:
    """Tipo -> faixas de atributos: cada faixa é uma subida de ``Grades`` (2, 3, 4 | 2, 4, 6 | ...; ``Grades`` 0 fica
    de fora), na ordem do id."""
    out: dict[int, list[list[int]]] = {}
    last: dict[int, int] = {}
    for r in sorted(templates.rows("SkillTempInfos"), key=lambda r: int(r["TemplateId"])):
        sid, grade = int(r["TemplateId"]), int(r.get("Grades") or 0)
        if sid // 100 not in RANDOM_TYPES or grade <= 0 or not templates.get("SkillPropertyTempInfos", sid):
            continue
        bands = out.setdefault(sid // 100, [])
        if not bands or grade <= last[sid // 100]:
            bands.append([])
        bands[-1].append(sid)
        last[sid // 100] = grade
    return out


def roll_random_skill(
    templates: GameTemplates, need_grades: int, rng: random.Random, skip_types: Iterable[int] = ()
) -> int:
    """Um atributo sorteado para um item de nível ``need_grades``: um tipo de ``RANDOM_TYPES`` fora de
    ``skip_types``, na faixa ``need_grades // 10`` dele (a última, se passar). (visto) oficial_20261023-153200-1/
    171155-1 e tutorial_en, 11 sorteios: itens de nível 3 e 8 só na 1ª faixa (70905, 70705, 71004); de 12 e 15 a
    2ª (70709, 70611, 70908: 7xx07-12 nos tipos 706-710; 70304, 70505, 70204, 70305: 7xx04-06 nos tipos 702-705);
    (visto, só turco) o Kronos' Authority (1991017, nível 20, 5 atributos) com os 5 na 3ª (70407, 71123, 70509, 70719,
    70209).
    TODO(inventado): dentro da faixa e entre os tipos o sorteio é uniforme (amostra pequena)."""
    bands = _bands(templates)
    types = [t for t in bands if t not in set(skip_types)] or list(bands)
    if not types:
        return 0
    chosen = bands[rng.choice(types)]
    return rng.choice(chosen[min(max(0, need_grades) // 10, len(chosen) - 1)])


def roll_random_skills(templates: GameTemplates, template_id: int, rng: random.Random | None = None) -> list[int]:
    """Os ``randomSkill_1..5`` de um item novo. Com ``DefaultSkill``, os dele (visto: 1013103 com 70306, 70406 e
    70506; 1013002 com 70302); senão ``RandomSkillCount`` atributos de tipos distintos (visto: 1030103 com 70611,
    70304 e 70505; 1043103 com 70908, 70204 e 70305)."""
    row = templates.get("ItemTempInfos", template_id) or {}
    fixed = [int(x) for x in str(row.get("DefaultSkill") or "").split(",") if x.strip().isdigit()]
    if fixed:
        return (fixed + [0] * 5)[:5]
    if row.get("MasterType") != EQUIP_MASTER:  # todos os sorteios vistos são de equipamento (MasterType 1)
        return [0] * 5
    rng = rng or random.Random()
    need, out = int(row.get("NeedGrades") or 0), list[int]()
    for _ in range(min(5, int(row.get("RandomSkillCount") or 0))):
        out.append(roll_random_skill(templates, need, rng, [k // 100 for k in out]))
    return out + [0] * (5 - len(out))


def max_count(templates: GameTemplates, template_id: int) -> int:
    row = templates.get("ItemTempInfos", template_id)
    return max(1, int(row.get("MaxCount", 1))) if row else 1


def new_item(
    snap: PlayerSnapshot, templates: GameTemplates, template_id: int, count: int = 1, binds: bool = True
) -> Item:
    """Item novo como o oficial cria: equipamento nasce com ``Property1`` furos abertos (``join`` 0)."""
    row = templates.get("ItemTempInfos", template_id) or {}
    item = Item(snap.character.id or 0, template_id, count=count, is_binds=binds)
    item.random_skills = roll_random_skills(templates, template_id)
    if row.get("MasterType") in (EQUIP_MASTER, PET_MASTER):
        holes = min(4, int(row.get("Property1") or 0))
        item.joins = [0] * holes + [-1] * (4 - holes)
    return item


def fits(
    snap: PlayerSnapshot,
    templates: GameTemplates,
    goods: Iterable[tuple[int, ...]],
    now: datetime,
    valid: int = 0,
    binds: bool = True,
) -> bool:
    """Cabe tudo na mochila (empilhando onde der)? ``goods`` = (templateId, quantidade), moedas ignoradas.
    ``valid`` > 0: item com validade, não entra nas pilhas que já existem (cada um tem o seu relógio).
    ``binds``: só empilha nas pilhas de mesmo vínculo (como o ``add``); (templateId, quantidade, vínculo) escolhe
    o vínculo de cada um."""
    free = len(free_positions(snap, now))
    room: dict[tuple[int, bool], int] = {}
    for tid, count, *own in goods:
        if tid < 0:
            continue
        top, key = max_count(templates, tid), (tid, bool(own[0]) if own else binds)
        if key not in room:
            room[key] = (
                0
                if valid
                else sum(
                    top - i.count
                    for i in in_bag(snap)
                    if i.template_id == tid and i.is_binds == key[1] and i.count < top
                )
            )
        use = min(room[key], count)
        room[key] -= use
        count -= use
        while count > 0:
            free -= 1
            room[key] += max(0, top - count)
            count -= top
        if free < 0:
            return False
    return True


def add(
    snap: PlayerSnapshot,
    templates: GameTemplates,
    template_id: int,
    count: int,
    now: datetime,
    valid: int = 0,
    binds: bool = True,
) -> list[Item]:
    """Põe ``count`` na mochila: completa as pilhas que já existem e abre espaços novos.

    ``valid``: minutos de validade (``ShopTempInfos.ValidDate``) contados de ``now``; com validade não empilha.
    ``binds``: vínculo do que entra; só completa pilhas de mesmo vínculo (o cliente pede confirmação para juntar
    livre com vinculado, ``GoodsCheck.isAddToChecker``: aqui não junta sozinho).
    Devolve os itens alterados/criados. Chame ``fits`` antes: sem espaço o resto é descartado.
    """
    top, changed = max_count(templates, template_id), []
    for item in [] if valid else sorted(in_bag(snap), key=lambda i: i.pos):
        if count <= 0:
            break
        if item.template_id == template_id and item.is_binds == binds and item.count < top:
            use = min(top - item.count, count)
            item.count += use
            count -= use
            changed.append(item)
    for pos in free_positions(snap, now):
        if count <= 0:
            break
        item = new_item(snap, templates, template_id, min(top, count), binds)
        item.pos = pos
        if valid:
            item.valid_date, item.begin_date = valid, now.replace(microsecond=0)  # o cliente lê só os segundos
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


def side_fits(
    snap: PlayerSnapshot, templates: GameTemplates, goods: Iterable[tuple[int, int]], bag: int, size: int
) -> bool:
    """Cabem todos os ``(item, quantidade)`` numa bolsa de prêmios (labirinto 24, árvore dourada 22) de ``size``
    espaços? Empilha até o ``MaxCount``; o que sobra abre espaço."""
    held = in_bag(snap, bag)
    free = size - len(held)
    room: dict[int, int] = {}
    for tid, n in goods:
        top = max_count(templates, tid)
        if tid not in room:
            room[tid] = sum(top - i.count for i in held if i.template_id == tid and i.count < top)
        while n > 0:
            if room[tid] == 0:
                free -= 1
                room[tid] = top
            take = min(n, room[tid])
            room[tid] -= take
            n -= take
    return free >= 0


def side_add(snap: PlayerSnapshot, templates: GameTemplates, tid: int, count: int, bag: int, size: int) -> list[Item]:
    """Um prêmio numa bolsa de prêmios: empilha na primeira pilha com espaço, senão no menor espaço livre.
    Quem chama já conferiu com ``side_fits``."""
    top = max_count(templates, tid)
    out: list[Item] = []
    while count > 0:
        held = sorted(in_bag(snap, bag), key=lambda i: i.pos)
        stack = next((i for i in held if i.template_id == tid and i.count < top), None)
        if stack is None:
            used = {i.pos for i in held}
            stack = new_item(snap, templates, tid, 0)
            stack.bag_type = bag
            stack.pos = next(p for p in range(size) if p not in used)
            snap.items.append(stack)
        take = min(count, top - stack.count)
        stack.count += take
        count -= take
        out.append(stack)
    return out


def take(
    snap: PlayerSnapshot, template_id: int, count: int, binds: bool | None = None
) -> tuple[list[Item], list[Item]]:
    """Consome ``count`` das pilhas da mochila: vinculadas primeiro, depois pela posição (cliente:
    ``sortOn(["isBinds","pos"],[DESCENDING,NUMERIC])`` em PetLearnSkillView, e ``isBinds`` DESCENDING no cartão de
    nome, InformationView); ``binds`` só das de esse vínculo. Devolve (alterados, apagados)."""
    changed, gone = [], []
    held = (i for i in in_bag(snap) if i.template_id == template_id and binds in (None, i.is_binds))
    for item in sorted(held, key=lambda i: (not i.is_binds, i.pos)):
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
    if bag == BagType.PET_EQUIP:
        return str(master) == PET_MASTER and pos in PET_SLOTS.get(son, ())
    return False
