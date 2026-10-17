"""Sistemas do herói guardados em ``PlayerSystems``: montaria, destino (roda), alma do dragão e cartas.

Fontes: captura de login (4427/4426/4544/4555/4905) e a de treino de montaria
(``online_odul_..._binek_upgrade``); o resto do cliente (MountsManager, FateRotarySkillInfo,
PlayerManager.__dragonSoul*). Só pacotes S>C foram capturados: os campos dos pedidos vêm do cliente.
"""

from __future__ import annotations

import random

from ...domain.models import BagType, Item, PlayerSnapshot, PlayerSystems
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import rules
from ..builders.login import NEVER, fmt_time
from ..builders.player import quest_update
from ..router import router
from ..session import GameSession
from .hero import send_items
from .player import _army, _player

S_MOUNT_AVATARS, S_MOUNT, S_MOUNT_OTHER = 4427, 4426, 4459
S_FATE, S_FATE_TURN, S_DRAGON, S_TRANSFER, S_TRANSFER_GRADE = 4544, 4545, 4555, 4556, 4557
S_POWCARD = 4905
S_QUESTS = 112  # QuestUpdatedRspMsg
QUEST_MOUNT_TRAIN = 71  # QuestCondictionInfos: treinar a montaria (Para2 1; uma ação de treino)

# --- montaria -------------------------------------------------------------------------------
MOUNT_TRAIN, MOUNT_CHANGE, MOUNT_INFO = 1, 2, 5  # MountsOpType
FOOD = "290"  # SonType do item 208017 (comida de montaria)
FOOD_GP = 10  # visto: 9 comidas = +90 de EXP em força
PAY_POINT, PAY_FOOD = 0, 1  # DomesticatePayType
# MountEditMsg.propertyType (PropertyInfo.getPropertyValue) -> índice em mount_gp
MOUNT_PROPERTY = {0: 0, 2: 1, 5: 2, 1: 3}  # força, inteligência, físico (Stamina), agilidade (Armor)


def mount_gps(sy: PlayerSystems) -> list[int]:
    return [int(x) for x in sy.mount_gp.split(",")]


def mount_info(snap: PlayerSnapshot, templates: GameTemplates) -> pb.MountInfoMsg | None:
    """4426 (visto): atributos já com o grau, EXP de cada um e o total."""
    sy = rules.systems(snap)
    tpl = templates.get("MountTempInfos", sy.mount_template) if sy.mount_template else None
    if tpl is None:
        return None
    stats, gps = rules.mount_stats(snap, templates), mount_gps(sy)
    msg = pb.MountInfoMsg(mountTempId=sy.mount_template, speed=int(tpl.get("Speed", 0)), mountTotalGp=sum(gps))
    msg.levelMax = rules.mount_level_max(tpl)
    for name, attr, gp in zip(("power", "intellect", "physique", "agility"), rules.MOUNT_ATTRS, gps, strict=True):
        setattr(msg, name, stats[attr])
        setattr(msg, f"{name}Gp", gp)
    for name in ("Power", "Intellect", "Physique", "Agility"):
        setattr(msg, f"refiningSoul{name}Grade", 0)
    msg.refiningSoulExp = 0
    return msg


def avatars(sy: PlayerSystems) -> list[int]:
    return [int(x) for x in sy.mount_avatars.split(",") if x]


def avatar_msg(snap: PlayerSnapshot, templates: GameTemplates) -> pb.MountAvatarMsg:
    """4427 (visto): montarias possuídas; ``soulScore`` = soma dos SoulScore."""
    msg = pb.MountAvatarMsg(totalPage=1)
    since = fmt_time(snap.character.created_at)  # ponytail: a data de ativação não é guardada
    for mount in avatars(rules.systems(snap)):
        tpl = templates.get("MountTempInfos", mount) or {}
        msg.avatarInfo.add(mountTempId=mount, isExist=True, expairDate=NEVER, activeDate=since, validity=-1)
        msg.avatarInfo[-1].starLevel, msg.avatarInfo[-1].blessing, msg.avatarInfo[-1].isBuyFly = 0, 0, False
        msg.soulScore += int(tpl.get("SoulScore", 0))
    return msg


def send_mount(s: GameSession) -> None:
    assert s.snapshot is not None
    if (info := mount_info(s.snapshot, s.ctx.templates)) is not None:
        s.send(S_MOUNT, info)


@router.on(8530)
async def mount_avatar_list(s: GameSession, _: object) -> None:
    """Login (#11-12): 4427 e, com montaria, 4426."""
    assert s.snapshot is not None
    s.send(S_MOUNT_AVATARS, avatar_msg(s.snapshot, s.ctx.templates))
    send_mount(s)


@router.on(8529)
async def mount_edit(s: GameSession, msg: pb.MountEditMsg) -> None:
    """op 1 treina ``propertyType`` com ``param1`` unidades (comida 208017 ou Mount_Point diamantes
    cada; 10 de EXP por unidade, até o grau levelMax); op 2 monta ``param1`` (precisa possuir);
    op 5 manda a montaria do jogador ``param1`` (4459). Resposta do treino (visto #83-90):
    109, 115, 3, 150, 4426."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy = rules.systems(snap)
    if msg.op == MOUNT_INFO:
        other = s.ctx.online.get(msg.param1)  # ponytail: só jogador online; offline precisa do banco
        info = mount_info(other.snapshot, templates) if other and other.snapshot else None
        if info is not None:
            s.send(S_MOUNT_OTHER, info)
        return
    if msg.op == MOUNT_CHANGE:
        if msg.param1 not in avatars(sy):
            s.log.info("8529 recusado: montaria não possuída", pedido=str(msg))
            return
        sy.mount_template = msg.param1
        await s.ctx.characters.save(sy)
        send_mount(s)
        _army(s)
        return
    if msg.op != MOUNT_TRAIN:
        # ponytail: estrela/bênção, rei das montarias, loja, refino e voo dependem da UI que não foi
        # descompilada (só o MountsManager); ficam registrados no log
        s.log.info("8529 op sem implementação", pedido=str(msg))
        return
    tpl = templates.get("MountTempInfos", sy.mount_template) if sy.mount_template else None
    idx, n = MOUNT_PROPERTY.get(msg.propertyType), msg.param1
    gps = mount_gps(sy)
    if tpl is None or idx is None or n <= 0:
        s.log.info("8529 recusado", pedido=str(msg))
        return
    cap_row = rules.upgrade_row(templates, rules.MOUNT_GRADE, rules.mount_level_max(tpl))
    cap = int(cap_row["Data"]) if cap_row else 0
    n = min(n, -(-(cap - gps[idx]) // FOOD_GP))  # não cobra o que passaria do teto
    food = rules.bag_items(snap, templates, FOOD)
    point_cost = n * int(rules.config(templates, "Mount_Point", "10"))
    if n <= 0 or (msg.payType == PAY_FOOD and sum(i.count for i in food) < n):
        s.log.info("8529 recusado: sem comida ou no teto", pedido=str(msg))
        return
    if msg.payType == PAY_POINT and not rules.pay_point(snap.character, point_cost, bind=True):
        s.log.info("8529 recusado: sem diamantes", pedido=str(msg))
        return
    changed, deleted = rules.take_items(snap, food, n) if msg.payType == PAY_FOOD else ([], [])
    gps[idx] = min(cap, gps[idx] + n * FOOD_GP)
    sy.mount_gp = ",".join(map(str, gps))
    quests = rules.quest_event(snap, templates, QUEST_MOUNT_TRAIN, 0, 1)  # uma ação de treino, qualquer atributo
    await s.ctx.characters.save(sy, snap.character, *changed, *quests, delete=tuple(deleted))
    send_items(s, changed, deleted)
    _player(s)
    _army(s)
    send_mount(s)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(8843)
async def mount_activity(s: GameSession, _: object) -> None:
    # ponytail: atividade de montaria nova (evento); sem captura da resposta
    s.log.info("8843 sem implementação (evento de montaria)")


# --- destino (roda) -------------------------------------------------------------------------
FATE_LEVEL = 55
FATE_DEFAULT = "2000:0,3000:0"  # os dois tipos vistos no login (#34); 2100 e 2200 não sabemos abrir
FATE_GRADE = "26"  # UpGradeTempInfo.Types: Data = EXP de cada grau (FateRotarySkillInfo.currentGp)
FATE_STONE, FATE_STONE_ID = "307", 208024
# ponytail: pesos da roda tirados do tamanho das fatias (FateRotaryModel.rndDic, em graus)
WHEEL = {1: 144, 2: 90, 3: 63, 4: 45, 10: 18}


def fate(sy: PlayerSystems) -> dict[int, int]:
    return {int(k): int(v) for k, v in (e.split(":") for e in sy.fate.split(",") if e)}


def fate_grade(templates: GameTemplates, gp: int) -> int:
    grade = 0
    for row in sorted(templates.find("UpGradeTempInfos", Types=FATE_GRADE), key=lambda r: int(r["Grades"])):
        if int(row["Grades"]) == 0:
            continue
        if gp < int(row["Data"]):
            break
        gp -= int(row["Data"])
        grade = int(row["Grades"])
    return grade


def fate_list(snap: PlayerSnapshot, templates: GameTemplates, only: int | None = None) -> pb.FateListMsg:
    sy, msg = rules.systems(snap), pb.FateListMsg()
    for son_type, gp in fate(sy).items():
        if only is not None and son_type != only:
            continue
        grade = fate_grade(templates, gp)
        row = next(templates.find("SkillTempInfos", SonType=son_type, Grades=grade), None)
        msg.fateInfo.add(templateId=int(row["TemplateId"]) if row else 0, fateTypes=son_type, totalGp=gp)
        msg.fateInfo[-1].grades, msg.fateInfo[-1].property1, msg.fateInfo[-1].turnCount = grade, "1", sy.fate_turns
    return msg


def open_fate(s: GameSession) -> PlayerSystems | None:
    snap = s.snapshot
    assert snap is not None
    sy = rules.systems(snap)
    if snap.character.grades < FATE_LEVEL:
        return None
    if not sy.fate:
        sy.fate = FATE_DEFAULT
    today = s.ctx.clock.now().strftime("%Y-%m-%d")
    if sy.fate_day != today:
        sy.fate_day, sy.fate_turns = today, 0
    return sy


@router.on(8628)
async def fate_request(s: GameSession, _: object) -> None:
    """Login (#34): 4544 com os tipos abertos (nível 55)."""
    assert s.snapshot is not None
    if open_fate(s) is not None:
        s.send(S_FATE, fate_list(s.snapshot, s.ctx.templates))


@router.on(8626)
async def fate_train(s: GameSession, msg: pb.FateEditMsg) -> None:
    """Gasta ``useItemCount`` pedras do destino (SonType 307) no tipo ``skillSonType``.
    Resposta: 115 e 4544 do tipo."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy = open_fate(s)
    stones = rules.bag_items(snap, templates, FATE_STONE)
    n = msg.useItemCount
    if sy is None or msg.skillSonType not in fate(sy) or n <= 0 or sum(i.count for i in stones) < n:
        s.log.info("8626 recusado", pedido=str(msg))
        return
    changed, deleted = rules.take_items(snap, stones, n)
    gps = fate(sy)
    gps[msg.skillSonType] += n  # ponytail: 1 de EXP por pedra (sem captura do treino)
    sy.fate = ",".join(f"{k}:{v}" for k, v in gps.items())
    await s.ctx.characters.save(sy, *changed, delete=tuple(deleted))
    send_items(s, changed, deleted)
    s.send(S_FATE, fate_list(snap, templates, msg.skillSonType))


def turn_cost(paid_index: int) -> int:
    """Giro pago número k do dia: 10, 20, 30... e 300 do 30º em diante (cliente)."""
    return 300 if paid_index >= 30 else 10 * paid_index


def give_item(snap: PlayerSnapshot, template_id: int, count: int) -> Item:
    """Empilha no primeiro item igual da mochila, senão ocupa uma posição livre."""
    item = next((i for i in snap.items if i.bag_type == BagType.BAG and i.template_id == template_id), None)
    if item is None:
        item = Item(snap.character.id or 0, template_id, pos=rules.free_bag_pos(snap), count=0)
        snap.items.append(item)
    item.count += count
    return item


@router.on(8627)
async def fate_turn(s: GameSession, msg: pb.FateEditMsg) -> None:
    """Gira a roda ``turnNum`` vezes (Fate_FreeCount grátis por dia, depois diamantes); cada giro dá
    1/2/3/4/10 pedras do destino. Resposta: 4545 {isSuccess, currCount, count, turnNum}, 115, 3."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy = open_fate(s)
    turns = msg.turnNum or 1
    if sy is None or not 1 <= turns <= 50:
        s.log.info("8627 recusado", pedido=str(msg))
        return
    free = int(rules.config(templates, "Fate_FreeCount", "1"))
    cost = sum(turn_cost(k - free) for k in range(sy.fate_turns + 1, sy.fate_turns + turns + 1) if k > free)
    if not rules.pay_point(snap.character, cost, bind=msg.payType == 0):
        s.send(S_FATE_TURN, pb.FateEditMsg(isSuccess=False, currCount=sy.fate_turns, turnNum=turns))
        return
    rewards = random.choices(list(WHEEL), weights=list(WHEEL.values()), k=turns)
    sy.fate_turns += turns
    item = give_item(snap, FATE_STONE_ID, sum(rewards))
    await s.ctx.characters.save(sy, snap.character, item)
    s.send(S_FATE_TURN, pb.FateEditMsg(isSuccess=True, currCount=sy.fate_turns, count=rewards, turnNum=turns))
    send_items(s, [item], [])
    if cost:
        _player(s)


# --- alma do dragão -------------------------------------------------------------------------
DRAGON, DRAGON_DONE = 101, 102  # fateTypes antes e depois da transferência
DRAGON_GRADE = "101"  # UpGradeTempInfo.Types: Data = EXP para o próximo grau (login: grau 2 com 7)
DRAGON_FOOD = "319"  # item 208032
DRAGON_LEVELS = (40, 50, 60, 70, 80)  # grau máximo pelo nível do herói (1 a 5)


def dragon_list(sy: PlayerSystems) -> pb.FateListMsg:
    msg = pb.FateListMsg()
    if sy.dragon_type:
        msg.fateInfo.add(fateTypes=sy.dragon_type, totalGp=sy.dragon_gp, grades=sy.dragon_grade)
    return msg


def open_dragon(snap: PlayerSnapshot) -> PlayerSystems:
    sy = rules.systems(snap)
    if not sy.dragon_type and snap.character.grades >= DRAGON_LEVELS[0]:
        sy.dragon_type = DRAGON
    return sy


@router.on(8642)
async def dragon_request(s: GameSession, _: object) -> None:
    """Login (#37): 4555 {fateTypes 101, totalGp, grades}."""
    assert s.snapshot is not None
    s.send(S_DRAGON, dragon_list(open_dragon(s.snapshot)))


@router.on(8641)
async def dragon_feed(s: GameSession, msg: pb.FateEditMsg) -> None:
    """Alimenta com ``useItemCount`` itens SonType 319 (1 de EXP cada); sobe de grau até o limite do
    nível. Resposta: 115 e 4555."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy = open_dragon(snap)
    food, n = rules.bag_items(snap, templates, DRAGON_FOOD), msg.useItemCount
    cap = sum(1 for lv in DRAGON_LEVELS if snap.character.grades >= lv)
    nxt = rules.upgrade_row(templates, DRAGON_GRADE, sy.dragon_grade + 1)
    if sy.dragon_type != DRAGON or nxt is None or sy.dragon_grade >= cap or n <= 0 or sum(i.count for i in food) < n:
        s.log.info("8641 recusado", pedido=str(msg))
        return
    changed, deleted = rules.take_items(snap, food, n)
    sy.dragon_gp += n
    while sy.dragon_grade < cap and nxt is not None and sy.dragon_gp >= int(nxt["Data"]):
        sy.dragon_gp -= int(nxt["Data"])
        sy.dragon_grade += 1
        nxt = rules.upgrade_row(templates, DRAGON_GRADE, sy.dragon_grade + 1)
    await s.ctx.characters.save(sy, *changed, delete=tuple(deleted))
    send_items(s, changed, deleted)
    s.send(S_DRAGON, dragon_list(sy))


@router.on(8643)
async def dragon_transfer(s: GameSession, _: object) -> None:
    """Transferência (alma no grau 5): vira o tipo 102. Resposta (PlayerManager): 4556 {param1 userId,
    param2 job, param3 vocationGrades, param4 apelido, param5 guilda} e 4557 {grades, totalGp}."""
    snap = s.snapshot
    assert snap is not None
    sy = open_dragon(snap)
    if sy.dragon_type != DRAGON or sy.dragon_grade < len(DRAGON_LEVELS):
        s.log.info("8643 recusado", tipo=sy.dragon_type, grau=sy.dragon_grade)
        return
    # ponytail: a vocação (vocationGrades/Gp) que vem depois não tem tabela nem captura; começa no 1
    sy.dragon_type, sy.dragon_grade, sy.dragon_gp = DRAGON_DONE, 1, 0
    await s.ctx.characters.save(sy)
    c = snap.character
    s.send(S_TRANSFER, pb.SimplePropertyMsg(param1=c.id, param2=c.job, param3=1, param4=c.nickname or "", param5=""))
    s.send(S_TRANSFER_GRADE, pb.FateInfoMsg(fateTypes=DRAGON_DONE, grades=1, totalGp=0))


# --- cartas de poder ------------------------------------------------------------------------
CARD_LEVEL_UP, CARD_ACTIVATE, CARD_TIDY = 1, 2, 3  # PowCardReqMsg.op
CARD_GRADE_BASE = 29  # UpGradeTempInfo.Types = 29 + Profile (30-34); Data = EXP do próximo grau


def cards(sy: PlayerSystems) -> dict[int, list[int]]:
    """``powcards`` = "tempId:grade:gp:ativa,..."."""
    found = {}
    for entry in filter(None, sy.powcards.split(",")):
        temp, *rest = (int(x) for x in entry.split(":"))
        found[temp] = [*rest, 0, 0, 0][:3] if rest else [1, 0, 0]
    return found


def store_cards(sy: PlayerSystems, found: dict[int, list[int]]) -> None:
    sy.powcards = ",".join(f"{t}:{g}:{gp}:{a}" for t, (g, gp, a) in found.items())


def powcard_msg(snap: PlayerSnapshot, templates: GameTemplates) -> pb.PowCardSuiteListMsg:
    """4905 (login #76): cartas por coleção; buf = BufId + grau - 1 (10001 grau 2 -> 3041)."""
    msg, suites = pb.PowCardSuiteListMsg(), {}
    for temp, (grade, gp, active) in cards(rules.systems(snap)).items():
        tpl = templates.get("PowcardTempInfos", temp) or {}
        suite_id = int(tpl.get("SuiteId", 0))
        if suite_id not in suites:
            suites[suite_id] = msg.suites.add(suiteId=suite_id)
        card = suites[suite_id].cardInfos.add(tempId=temp, grade=grade, gp=gp, isActive=active)
        card.buf.sonType, card.buf.bufId = int(tpl.get("SonType", 0)), int(tpl.get("BufId", 0)) + grade - 1
        card.buf.fixValue, card.buf.percent = int(tpl.get("fixvalue", 0)), int(tpl.get("percent", 0))
    # ponytail: o buff da coleção completa (bufInfos da suíte, visto 40001) não tem tabela conhecida
    return msg


@router.on(9505)
async def powcard_op(s: GameSession, msg: pb.PowCardReqMsg) -> None:
    """op 1 sobe a carta ``cardId`` (gasta a EXP do próximo grau), 2 ativa todas, 3 organiza (só
    reenvia). Resposta: 4905. As cartas e a EXP vêm das batalhas (4902), fora deste módulo."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy = rules.systems(snap)
    found = cards(sy)
    if msg.op == CARD_LEVEL_UP:
        card, tpl = found.get(msg.cardId), templates.get("PowcardTempInfos", msg.cardId)
        types = str(CARD_GRADE_BASE + int(tpl["Profile"])) if tpl else ""
        nxt = rules.upgrade_row(templates, types, card[0] + 1) if card else None
        if card is None or nxt is None or card[1] < int(nxt["Data"]):
            s.log.info("9505 recusado", pedido=str(msg))
            return
        card[0], card[1] = card[0] + 1, card[1] - int(nxt["Data"])
    elif msg.op == CARD_ACTIVATE:
        for card in found.values():
            card[2] = 1
    elif msg.op != CARD_TIDY:
        s.log.info("9505 op desconhecida", pedido=str(msg))
        return
    if msg.op != CARD_TIDY:
        store_cards(sy, found)
        await s.ctx.characters.save(sy)
    s.send(S_POWCARD, powcard_msg(snap, templates))
