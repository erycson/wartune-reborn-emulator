"""Sistemas do herói guardados em ``PlayerSystems``: montaria, destino (roda), alma do dragão e cartas.

Fontes: login do tutorial_en (#20 4427 sem montaria, #42 4544 vazio no nível 1); com o sistema aberto, só
turco: login.json (#11-#12 4426/4427, #34 4544, #37 4555, #76 4905) e o treino de montaria
(``online_odul_..._binek_upgrade``); o resto do cliente (MountsManager, FateRotarySkillInfo,
PlayerManager.__dragonSoul*). Nas turcas só há pacotes S>C: os campos dos pedidos vêm do cliente.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from ...domain import gameday
from ...domain.models import BagType, Item, PlayerSnapshot, PlayerSystems
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates, Row
from .. import bag, rules, taxas
from .. import events as ev
from ..builders.login import NEVER, fmt_time
from ..builders.player import quest_update
from ..router import router
from ..session import GameSession
from .hero import send_items
from .player import _army, _player, alert, snapshot_of

S_MOUNT_AVATARS, S_MOUNT, S_MOUNT_OTHER, S_MOUNT_STAR = 4427, 4426, 4459, 4679
S_FATE, S_FATE_TURN, S_DRAGON, S_TRANSFER, S_TRANSFER_GRADE = 4544, 4545, 4555, 4556, 4557
S_POWCARD = 4905
S_QUESTS = 112  # QuestUpdatedRspMsg
QUEST_MOUNT_TRAIN = 71  # QuestCondictionInfos: treinar a montaria (Para2 1; uma ação de treino)

# --- montaria -------------------------------------------------------------------------------
MOUNT_TRAIN, MOUNT_CHANGE, MOUNT_RIDE, MOUNT_INFO = 1, 2, 3, 5  # MountsOpType (3 = ARMYMOUNT_AVATARCHANGE)
MOUNT_ACTIVATE, MOUNT_FLY = 4, 13  # MOUNTAVATAR_ACTIVE (WildSoulFrame) e OP_BUY_FLY (MountsFrame)
MOUNT_STAR = 6  # MOUNT_START (MountsPromotionView): refinar a estrela
STAR_GRADE = 70  # WildSoulItem/MountsFrame: o botão de estrela abre no nível 70 do herói
HOOF = 208035  # Mount Hoof (MountsManager.GOLDEN_HORSE_SHOE): 1 por refino
ADVANCED = 10  # MountsPromotionView.advCost: o "10x" (param1 1) gasta 10 Hoofs em 10 refinos
NO_STAR = ("3", "4")  # MountsManager.canShowStar: a de VIP (3) e o rei (4) não têm estrela
STAR_TABLE = "37"  # UpGradeTempInfo: TemplateId = GradeType da montaria, Grades = estrela, Data = bênção até ela
# WildSoulFrame: só MountType 1, 2 e 4 se ativam no clique (0 vem do Beast Soul Lvl, 3 é a de VIP); 4 = rei das
# montarias, que pede o mount_king_active_item
UNLOCKABLE, KING = ("1", "2", "4"), "4"
FLYSTONE = 208131  # MountsManager.STONE_TEMPID: "consume 1 Flystone to enable the mount to fly"
# UpGradeTempInfo.Types do Beast Soul Lvl (MountInfo.growExp = mountTotalGp; Data = o mínimo do nível) e a montaria
# que o nível dá (ActiveObject: 1006 no 2, 2001 no 3)
MOUNT_SOUL = "19"
DAY = 86400
MOUNT_REST_KEY = "mount:rest"  # 1 = desmontado (MountsFrame Rest: op 3 com param1 0)
FOOD = "290"  # SonType do item 208017 (comida de montaria)
FOOD_GP = 10  # 9 comidas = +90 de EXP em força (só turco: online_odul_..._binek_upgrade)
# MountsFrame inglês: payType 0 = pode usar vinculados (advDomesticateUseBind); "Mount Training Whips are consumed
# first" (mounts.tips02), o resto em Mount_Point diamantes
PAY_BIND = 0
# MountEditMsg.propertyType (PropertyInfo.getPropertyValue) -> índice em mount_gp
MOUNT_PROPERTY = {0: 0, 2: 1, 5: 2, 1: 3}  # força, inteligência, físico (Stamina), agilidade (Armor)


def mount_gps(sy: PlayerSystems) -> list[int]:
    return [int(x) for x in sy.mount_gp.split(",")]


def mount_info(snap: PlayerSnapshot, templates: GameTemplates) -> pb.MountInfoMsg | None:
    """4426 (visto: 231733 #14; turco login.json #12): atributos já com o grau, EXP de cada um e o total."""
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


def _ids(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x]


def expiry(sy: PlayerSystems) -> dict[int, int]:
    """Fim (segundos Unix) de cada montaria temporária."""
    return {int(a): int(b) for a, b in (x.split(":") for x in sy.mount_expiry.split(",") if x)}


def avatars(sy: PlayerSystems, now: datetime | None = None) -> list[int]:
    """Montarias possuídas; com ``now``, sem as temporárias vencidas (o cliente as mostra trancadas de novo)."""
    ends = expiry(sy) if now else {}
    return [m for m in _ids(sy.mount_avatars) if m not in ends or now is None or ends[m] > now.timestamp()]


def soul_grade(templates: GameTemplates, sy: PlayerSystems) -> int:
    """Beast Soul Lvl (``MountInfo.grade``): o maior nível com ``Data`` <= EXP total da montaria."""
    total = sum(mount_gps(sy))
    rows = templates.find("UpGradeTempInfos", Types=MOUNT_SOUL)
    return max((int(r["Grades"]) for r in rows if total >= int(r["Data"])), default=1)


def grant_mount(sy: PlayerSystems, mount: int, days: int, now: datetime) -> bool:
    """Põe a montaria nas possuídas. ``days`` > 0: temporária, somando ao que ainda resta; 0: permanente.
    False se ela já é permanente (nada a ganhar)."""
    ends, owned = expiry(sy), _ids(sy.mount_avatars)
    if mount in owned and mount not in ends:
        return False
    if mount not in owned:
        sy.mount_avatars = ",".join(map(str, [*owned, mount]))
        sy.mount_since = ",".join(x for x in (sy.mount_since, f"{mount}:{int(now.timestamp())}") if x)
    if days > 0:
        ends[mount] = max(ends.get(mount, 0), int(now.timestamp())) + days * DAY
    else:
        ends.pop(mount, None)
    sy.mount_expiry = ",".join(f"{m}:{end}" for m, end in ends.items())
    return True


def soul_mounts(templates: GameTemplates, sy: PlayerSystems, now: datetime) -> bool:
    """Dá as montarias do Beast Soul Lvl alcançado (``ActiveObject`` da tabela 19). True se ganhou alguma."""
    grade = soul_grade(templates, sy)
    rows = templates.find("UpGradeTempInfos", Types=MOUNT_SOUL)
    got = [int(r["ActiveObject"]) for r in rows if int(r["Grades"]) <= grade and int(r.get("ActiveObject") or 0)]
    return any([grant_mount(sy, m, 0, now) for m in got if m not in _ids(sy.mount_avatars)])


def avatar_msg(snap: PlayerSnapshot, templates: GameTemplates, now: datetime) -> pb.MountAvatarMsg:
    """4427: montarias possuídas; ``soulScore`` = soma dos SoulScore (tutorial_en #20 sem montaria: vazio e 0;
    com montaria, só turco: login.json #11). Temporária: ``expairDate`` e os dias que faltam (``validity``,
    arredondado para cima como o ``WildSoulInfo``); permanente: 2000-01-01 e -1. ``isBuyFly``: voo da Flystone."""
    sy = rules.systems(snap)
    msg = pb.MountAvatarMsg(totalPage=1)
    for mount in avatars(sy, now):
        msg.avatarInfo.append(avatar_info(snap, mount, now))
        msg.soulScore += int((templates.get("MountTempInfos", mount) or {}).get("SoulScore", 0))
    return msg


def avatar_info(snap: PlayerSnapshot, mount: int, now: datetime) -> pb.AvatarInfoMsg:
    """Uma montaria possuída do 4427 (e do 4679 da estrela), com estrela e bênção."""
    sy = rules.systems(snap)
    # ativação gravada no grant_mount (0109); as montarias de antes dela mostram a criação do personagem
    at = dict(x.split(":") for x in sy.mount_since.split(",") if x).get(str(mount))
    since = fmt_time(datetime.fromtimestamp(int(at), UTC) if at else snap.character.created_at)
    end = expiry(sy).get(mount)
    until = fmt_time(datetime.fromtimestamp(end, UTC)) if end else NEVER
    days = -(-(end - int(now.timestamp())) // DAY) if end else -1
    star, bless = rules.mount_stars(sy).get(mount, (0, 0))
    return pb.AvatarInfoMsg(
        mountTempId=mount,
        isExist=True,
        expairDate=until,
        activeDate=since,
        validity=days,
        starLevel=star,
        blessing=bless,
        isBuyFly=mount in _ids(sy.mount_fly),
    )


def drop_expired_mount(sy: PlayerSystems, now: datetime) -> bool:
    """A montaria em uso venceu (carta temporária): sai de uso, como sem montaria. True se mudou."""
    if sy.mount_template not in _ids(sy.mount_avatars) or sy.mount_template in avatars(sy, now):
        return False
    sy.mount_template = 0
    return True


async def expire_mount(s: GameSession) -> None:
    """Login (8530) e relógio de 60 s: tira de uso a montaria vencida; 150 sem ela e 4427 com ela trancada."""
    sy = s.snapshot.systems if s.snapshot else None
    if sy is None or not drop_expired_mount(sy, s.ctx.clock.now()):
        return
    await s.ctx.characters.save(sy)
    _player(s)
    _army(s)
    send_avatars(s)


def send_avatars(s: GameSession) -> None:
    assert s.snapshot is not None
    s.send(S_MOUNT_AVATARS, avatar_msg(s.snapshot, s.ctx.templates, s.ctx.clock.now()))


def send_mount(s: GameSession) -> None:
    assert s.snapshot is not None
    if (info := mount_info(s.snapshot, s.ctx.templates)) is not None:
        s.send(S_MOUNT, info)


@router.on(8530)
async def mount_avatar_list(s: GameSession, _: object) -> None:
    """Login: 4427 (tutorial_en #19-#20) e, com montaria, 4426 (visto: 231733 #13-#14, como o turco)."""
    from .vip import vip_mount_expired  # vip importa este módulo dentro do cartão

    await expire_mount(s)
    send_avatars(s)
    await vip_mount_expired(s)  # (visto) 232017 #18-#20: 4427, 4610, 4426
    send_mount(s)


async def _activate(s: GameSession, msg: pb.MountEditMsg) -> None:
    """op 4 (``WildSoulFrame.__resultHandler``): ativa a montaria ``param1`` trancada. Com a carta dela
    (``NeedItemId``; o rei das montarias usa o ``mount_king_active_item``) na mochila, gasta a carta e vale os dias
    dela (``Property2``, -1 = permanente: "mounts.command10"); sem a carta, ``Property1`` Balens, permanente
    ("mounts.command11"; payType 0 aceita vinculados, USEBINDPOINT_ALERT). Pede o ``NeedMountGrade`` de Beast Soul."""
    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None
    sy, c = rules.systems(snap), snap.character
    tpl = templates.get("MountTempInfos", msg.param1)
    king = tpl is not None and tpl.get("MountType") == KING
    need, n = (int(tpl.get("NeedItemId") or 0) if tpl else 0), 1
    if king:
        need, n = (int(x) for x in rules.config(templates, "mount_king_active_item", "2131500,1").split(","))
    price = int(tpl.get("Property1") or 0) if tpl else 0
    card = need > 0 and bag.count_of(snap, need) >= n
    if (
        tpl is None
        or tpl.get("MountType") not in UNLOCKABLE
        or msg.param1 in avatars(sy, now)
        or int(tpl.get("NeedMountGrade") or 0) > soul_grade(templates, sy)
        or not (card or price > 0)
    ):
        s.log.info("8529 ativar recusado", pedido=str(msg))
        return
    changed: list[Item] = []
    gone: list[Item] = []
    spent = None
    days = 0
    if card:
        changed, gone = bag.take(snap, need, n)
        days = int((templates.get("ItemTempInfos", need) or {}).get("Property2") or 0)
    else:
        spent = ledger.pay(c, price, bind=msg.payType == PAY_BIND, reason="mount_active", ref=str(msg.param1), now=now)
        if spent is None:
            s.log.info("8529 ativar recusado: sem Balens", pedido=str(msg), custo=price)
            return
    grant_mount(sy, msg.param1, days, now)
    await s.ctx.characters.save(sy, *changed, *([c, spent] if spent else []), delete=tuple(gone))

    send_items(s, changed, gone)
    if spent:
        _player(s)
    send_avatars(s)


async def _buy_fly(s: GameSession, msg: pb.MountEditMsg) -> None:
    """op 13 (``MountsFrame.__alertBackHandler``): uma Flystone dá voo à montaria ``param1`` (só as que não voam:
    ``IsFly`` 0 e sem voo comprado, o botão ``notFlyMountBtn``); sem a pedra, "Insufficient Flystone"."""
    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None
    sy = rules.systems(snap)
    tpl = templates.get("MountTempInfos", msg.param1)
    fly = _ids(sy.mount_fly)
    if (
        tpl is None
        or msg.param1 not in avatars(sy, now)
        or tpl.get("IsFly") == "1"
        or msg.param1 in fly
        or bag.count_of(snap, FLYSTONE) < 1
    ):
        s.log.info("8529 voo recusado", pedido=str(msg))
        return
    changed, gone = bag.take(snap, FLYSTONE, 1)
    sy.mount_fly = ",".join(map(str, [*fly, msg.param1]))
    await s.ctx.characters.save(sy, *changed, delete=tuple(gone))

    send_items(s, changed, gone)
    send_avatars(s)


async def _star(s: GameSession, msg: pb.MountEditMsg) -> None:
    """op 6 (``MountsPromotionView``): refina a estrela da montaria ``propertyType`` (não o ``param1``). Um refino
    gasta 1 Mount Hoof; ``param1`` 1 faz 10 com 10 Hoofs. Herói nível 70, montaria possuída e permanente
    (``validity`` -1), nem a de VIP nem o rei (``canShowStar``), abaixo da estrela máxima. A bênção enche a barra
    (``Data`` da tabela 37 para a estrela seguinte) e cheia sobe a estrela; volta a 0 na estrela nova (*dedução*: a
    barra é por estrela). O primeiro refino de quem nunca refinou (``WildSoulCollection.firstBless``) não gasta
    Hoof: o cliente o manda sem conferir a mochila. Resposta 4679 com a montaria; a em uso também manda 4426 e 150."""
    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None
    sy, c, mount = rules.systems(snap), snap.character, msg.propertyType
    tpl = templates.get("MountTempInfos", mount)
    adds = rules.star_additions(tpl) if tpl else []
    all_stars = rules.mount_stars(sy)
    star, bless = all_stars.get(mount, (0, 0))
    first = msg.param1 == 0 and not any(a + b for a, b in all_stars.values())
    tries = ADVANCED if msg.param1 == 1 else 1
    if (
        tpl is None
        or c.grades < STAR_GRADE
        or tpl.get("MountType") in NO_STAR
        or mount not in avatars(sy, now)
        or mount in expiry(sy)
        or star >= len(adds)
        or (not first and bag.count_of(snap, HOOF) < tries)
    ):
        s.log.info("8529 estrela recusada", pedido=str(msg))
        return
    need = {
        int(r["Grades"]): int(r["Data"])
        for r in templates.find("UpGradeTempInfos", Types=STAR_TABLE)
        if r.get("TemplateId") == tpl.get("GradeType")
    }
    used, before = 0, star
    while used < tries and star < len(adds):
        used += 1
        bless += int(taxas.get(s.ctx.world.settings, "mount_star_bless"))
        if bless >= need.get(star + 1, 0) or random.randrange(100) < int(
            taxas.get(s.ctx.world.settings, "mount_star_chance")
        ):
            star, bless = star + 1, 0
    all_stars[mount] = (star, bless)
    sy.mount_stars = ",".join(f"{m}:{a}:{b}" for m, (a, b) in all_stars.items())
    changed, gone = bag.take(snap, HOOF, used) if not first else ([], [])
    await s.ctx.characters.save(sy, *changed, delete=tuple(gone))

    send_items(s, changed, gone)
    s.send(S_MOUNT_STAR, avatar_info(snap, mount, now))
    if star != before and mount == sy.mount_template:
        send_mount(s)
        _army(s)


@router.on(8529)
async def mount_edit(s: GameSession, msg: pb.MountEditMsg) -> None:
    """op 1 treina ``propertyType`` com ``param1`` unidades (chicotes 208017 primeiro, o resto Mount_Point
    diamantes cada; 10 de EXP por unidade, até o grau levelMax); op 2 escolhe ``param1`` (precisa possuir);
    op 3 monta (``param1`` 1) ou descansa (0, MountsFrame Mount/Rest); op 5 manda a montaria do jogador ``param1``
    (4459). Resposta do treino (só turco: online_odul_..._binek_upgrade #83-#91): 109, 115, 3, 4902, 150, 4902, 4476
    da atividade 18 com o seu 4426 e o 4426 do treino."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy = rules.systems(snap)
    if msg.op == MOUNT_INFO:
        other = await snapshot_of(s, msg.param1)  # online: a sessão; offline: o banco
        info = mount_info(other, templates) if other is not None else None
        if info is not None:
            s.send(S_MOUNT_OTHER, info)
        return
    if msg.op == MOUNT_ACTIVATE:
        await _activate(s, msg)
        return
    if msg.op == MOUNT_FLY:
        await _buy_fly(s, msg)
        return
    if msg.op == MOUNT_STAR:
        await _star(s, msg)
        return
    if msg.op == MOUNT_CHANGE:
        if msg.param1 not in avatars(sy, s.ctx.clock.now()):
            s.log.info("8529 recusado: montaria não possuída", pedido=str(msg))
            return
        sy.mount_template = msg.param1
        await s.ctx.characters.save(sy)
        send_mount(s)
        _army(s)
        return
    if msg.op == MOUNT_RIDE:
        if not sy.mount_template:
            s.log.info("8529 recusado: sem montaria", pedido=str(msg))
            return
        rest = ev.state(snap, MOUNT_REST_KEY, s.ctx.clock.now())
        rest.value, rest.updated_at = int(msg.param1 == 0), s.ctx.clock.now()
        await s.ctx.characters.save(rest)
        _army(s)
        return
    if msg.op != MOUNT_TRAIN:
        # rei das montarias (7): o cliente inglês não tem MountType 4, tabela 109 nem o item 2131500, e a lista do
        # rei não tem ouvinte; loja (8-11): nenhum chamador; refino da alma (12): botão fora da tela, item 208070 e
        # tabelas 144-146 ausentes. Nada a responder: ficam no log
        s.log.info("8529 op sem tela no cliente inglês", pedido=str(msg))
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
    whips = min(n, sum(i.count for i in food))
    point_cost = (n - whips) * int(rules.config(templates, "Mount_Point", "35"))
    if n <= 0:
        s.log.info("8529 recusado: no teto", pedido=str(msg))
        return
    bind = msg.payType == PAY_BIND
    spent = (
        ledger.pay(snap.character, point_cost, bind=bind, reason="mount_train", ref="", now=s.ctx.clock.now())
        if point_cost
        else None
    )
    if point_cost and spent is None:
        s.log.info("8529 recusado: sem chicote nem diamantes", pedido=str(msg))
        return
    changed, deleted = rules.take_items(snap, food, whips) if whips else ([], [])
    gps[idx] = min(cap, gps[idx] + n * FOOD_GP)
    sy.mount_gp = ",".join(map(str, gps))
    new_mount = soul_mounts(templates, sy, s.ctx.clock.now())
    quests = rules.quest_event(snap, templates, QUEST_MOUNT_TRAIN, 0, 1)  # uma ação de treino, qualquer atributo
    counted = ev.count(snap, s.ctx.events, ev.MOUNT_TRAIN, s.ctx.clock.now(), n)
    await s.ctx.characters.save(
        sy, snap.character, *changed, *quests, *counted, *([spent] if spent else []), delete=tuple(deleted)
    )
    from ..castle import castle_yield
    from .events import progress  # events importa este módulo

    castle_yield(s)
    send_items(s, changed, deleted)
    _player(s)
    _army(s)
    if (add := fight_add_msg(snap, templates)) is not None:
        s.send(S_FIGHT_ADD, add)
    progress(s)
    send_mount(s)
    if new_mount:
        send_avatars(s)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))


@router.on(8843)
async def mount_activity(s: GameSession, _: object) -> None:
    """8843 (``MountActSocketOutManager.sendGetMountActInfo``): corpo vazio, sem chamador e sem código de resposta
    no cliente inglês; nada a mandar."""
    s.log.info("8843 sem resposta no cliente inglês (evento de montaria)")


# --- destino (roda) -------------------------------------------------------------------------
FATE_LEVEL = 55
FATE_DEFAULT = "2000:0,3000:0"  # os dois tipos do login (só turco: login.json #34); 2100 e 2200 não sabemos abrir
FATE_GRADE = "26"  # UpGradeTempInfo.Types: Data = EXP de cada grau (FateRotarySkillInfo.currentGp)
FATE_STONE, FATE_STONE_ID = "307", 208024


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
    # 2100/2200 (SkillTempInfos existem; o FateRotaryFrame mostra o que o 4544 manda): abrem pelo nível de
    # ``game_settings.fate_unlock`` (0116). TODO(inventado): os níveis
    gps = fate(sy)
    for son, level in (s.ctx.world.settings.get("fate_unlock") or {}).items():
        if snap.character.grades >= int(level) and int(son) not in gps:
            gps[int(son)] = 0
    sy.fate = ",".join(f"{k}:{v}" for k, v in gps.items())
    today = gameday.today(s.ctx.clock.now())
    if sy.fate_day != today:
        sy.fate_day, sy.fate_turns = today, 0
    return sy


@router.on(8628)
async def fate_request(s: GameSession, _: object) -> None:
    """4544 com os tipos abertos (nível 55; só turco: login.json #34)."""
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
    gps[msg.skillSonType] += n * int(taxas.get(s.ctx.world.settings, "fate_stone_exp"))  # EXP por pedra (0124)
    sy.fate = ",".join(f"{k}:{v}" for k, v in gps.items())
    counted = ev.count(snap, s.ctx.events, ev.FATE_EAT, s.ctx.clock.now(), n)  # atividade "Fate Stones" (tipo 109)
    await s.ctx.characters.save(sy, *changed, *counted, delete=tuple(deleted))
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
    spent = (
        ledger.pay(snap.character, cost, bind=msg.payType == 0, reason="fate_turn", ref="", now=s.ctx.clock.now())
        if cost
        else None
    )
    if cost and spent is None:
        s.send(S_FATE_TURN, pb.FateEditMsg(isSuccess=False, currCount=sy.fate_turns, turnNum=turns))
        return
    wheel = taxas.get(s.ctx.world.settings, "fate_wheel")  # FateRotaryModel.rndDic em graus (0124)
    rewards = random.choices([int(k) for k in wheel], weights=list(wheel.values()), k=turns)
    sy.fate_turns += turns
    item = give_item(snap, FATE_STONE_ID, sum(rewards))
    counted = ev.count(snap, s.ctx.events, ev.FATE_TURN, s.ctx.clock.now(), turns)  # "Wheel of Fate" (tipo 108)
    await s.ctx.characters.save(sy, snap.character, item, *counted, *([spent] if spent else []))
    s.send(S_FATE_TURN, pb.FateEditMsg(isSuccess=True, currCount=sy.fate_turns, count=rewards, turnNum=turns))
    send_items(s, [item], [])
    if cost:
        _player(s)


# --- alma do dragão -------------------------------------------------------------------------
DRAGON, DRAGON_DONE = 101, 102  # fateTypes antes e depois da transferência
DRAGON_GRADE = "101"  # UpGradeTempInfo.Types: Data = EXP para o próximo grau (login: grau 2 com 7)
DRAGON_FOOD = "319"  # item 208032
VOCATION_GRADE = "107"  # UpGradeTempInfo.Types da vocação depois da transferência (dedução, TODO(inventado))
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
    """4555 {fateTypes 101, totalGp, grades} (só turco: login.json #37; o tutorial_en não tem 4555)."""
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
    done = sy.dragon_type == DRAGON_DONE  # vocação: a mesma comida sobe o grau (``VOCATION_GRADE``)
    table = VOCATION_GRADE if done else DRAGON_GRADE
    cap = 10**6 if done else sum(1 for lv in DRAGON_LEVELS if snap.character.grades >= lv)
    nxt = rules.upgrade_row(templates, table, sy.dragon_grade + 1)
    if not sy.dragon_type or nxt is None or sy.dragon_grade >= cap or n <= 0 or sum(i.count for i in food) < n:
        s.log.info("8641 recusado", pedido=str(msg))
        return
    changed, deleted = rules.take_items(snap, food, n)
    sy.dragon_gp += n
    while sy.dragon_grade < cap and nxt is not None and sy.dragon_gp >= int(nxt["Data"]):
        sy.dragon_gp -= int(nxt["Data"])
        sy.dragon_grade += 1
        nxt = rules.upgrade_row(templates, table, sy.dragon_grade + 1)
    await s.ctx.characters.save(sy, *changed, delete=tuple(deleted))
    send_items(s, changed, deleted)
    if done:
        s.send(S_TRANSFER_GRADE, pb.FateInfoMsg(fateTypes=DRAGON_DONE, grades=sy.dragon_grade, totalGp=sy.dragon_gp))
    else:
        s.send(S_DRAGON, dragon_list(sy))


def vocation_percent(snap: PlayerSnapshot, settings: Mapping[str, Any]) -> dict[str, int]:
    """Bônus da transferência na luta: % por grau de vocação (``game_settings.dragon_vocation_bonus``, 0116).
    TODO(inventado): os atributos e o % (o DragonSoulView só mostra o nome da vocação)."""
    sy = snap.systems
    if sy is None or sy.dragon_type != DRAGON_DONE:
        return {}
    return {k: int(v) * sy.dragon_grade for k, v in (settings.get("dragon_vocation_bonus") or {}).items()}


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
    # a vocação começa no 1 e sobe pelo 8641 na tabela 107 (dedução: a única UpGradeTempInfos sem dono, 31 graus)
    sy.dragon_type, sy.dragon_grade, sy.dragon_gp = DRAGON_DONE, 1, 0
    await s.ctx.characters.save(sy)
    c = snap.character
    s.send(S_TRANSFER, pb.SimplePropertyMsg(param1=c.id, param2=c.job, param3=1, param4=c.nickname or "", param5=""))
    s.send(S_TRANSFER_GRADE, pb.FateInfoMsg(fateTypes=DRAGON_DONE, grades=1, totalGp=0))


# --- cartas de poder ------------------------------------------------------------------------
CARD_LEVEL_UP, CARD_ACTIVATE, CARD_TIDY = 1, 2, 3  # PowCardReqMsg.op
CARD_GRADE_BASE = 29  # UpGradeTempInfo.Types = 29 + Profile (30-34); Data = EXP do próximo grau
NO_CARDS = "There are no cards to be activated."  # (visto) captura 20261029-121453-1 #575
# (visto) captura 20261029-121453-1: os 150 do nível 31 (#6-#160) vêm sem 4902; do 32 em diante (#421) vem o 4902
# vazio sem nenhuma carta (#422, #536, #615). O mesmo 32 do TreasureHuntControler (setPreFrame "magiccard").
CARD_OPEN_GRADE = 32


def cards(sy: PlayerSystems) -> dict[int, list[int]]:
    """``powcards`` = "tempId:grade:gp:ativa,..."."""
    found = {}
    for entry in filter(None, sy.powcards.split(",")):
        temp, *rest = (int(x) for x in entry.split(":"))
        found[temp] = [*rest, 0, 0, 0][:3] if rest else [1, 0, 0]
    return found


def store_cards(sy: PlayerSystems, found: dict[int, list[int]]) -> None:
    sy.powcards = ",".join(f"{t}:{g}:{gp}:{a}" for t, (g, gp, a) in found.items())


CARD_ITEM = "600"  # ItemTempInfos.SonType das cartas ("Available after using the ... card"; Property1 = a carta)


def gain_cards(sy: PlayerSystems, templates: GameTemplates, items: list[Item]) -> list[Item]:
    """Cartas ganhas (itens SonType 600) entram no 4905: a primeira cópia abre a carta no grau 1 e cada cópia a mais
    soma 1 de ``gp``, a EXP que o 9505 op 1 gasta (``UpGradeTempInfos`` 30-34: 10, 30, 60...). Devolve os itens
    absorvidos (quem chama apaga). TODO(inventado): 1 de EXP por cópia; o cliente só mostra o ``gp``."""
    found, used = cards(sy), []
    for item in items:
        row = templates.get("ItemTempInfos", item.template_id) or {}
        temp = int(row.get("Property1") or 0)
        if row.get("SonType") != CARD_ITEM or templates.get("PowcardTempInfos", temp) is None:
            continue
        n = item.count
        if temp not in found:
            found[temp], n = [1, 0, 0], n - 1
        found[temp][1] += n
        used.append(item)
    if used:
        store_cards(sy, found)
    return used


# Bônus da coleção: 3 degraus (MagicCardSlotView.updateBuffData). (cliente) language EN
# card.CardSlotView.Notactive0..2: "4 cards from the same deck", "3 level 4 cards", "8 level 4 cards".
# (só turco: login.json #76) só a 1002, com 4 cartas, tem bufInfos (40001 = Property3); as de 3 cartas não têm.
# (dedução) leitura: [cartas, grau mínimo de cada] = 4 de qualquer grau, 4 no grau 3, 4 no grau 8.
# Configurável: game_settings ``powcard_suite_slots`` (0037).
SUITE_SLOTS = [[4, 1], [4, 3], [4, 8]]


def suite_buffs(suite: Row, owned: list[int], slots: list[list[int]]) -> list[tuple[int, int]]:
    """(sonType, bufId) de cada degrau aceso: o degrau k usa ``Template{3+k}s`` e ``Property{3+k}``
    da PowCardSuiteTemInfos (1002 com 4 cartas: Template3s 1004, Property3 40001, como no login.json #76, só turco)."""
    lit = []
    for k, (count, grade) in enumerate(slots):
        if sum(g >= grade for g in owned) < count:
            break
        lit.append((int(suite.get(f"Template{3 + k}s") or 0), int(suite.get(f"Property{3 + k}") or 0)))
    return lit


def powcard_msg(
    snap: PlayerSnapshot, templates: GameTemplates, slots: list[list[int]] | None = None
) -> pb.PowCardSuiteListMsg:
    """4905 (só turco: login.json #76): cartas por coleção; buf = BufId + grau - 1 (10001 grau 2 -> 3041);
    ``bufInfos`` da coleção pelos degraus (``suite_buffs``)."""
    msg, suites = pb.PowCardSuiteListMsg(), {}
    owned: dict[int, list[int]] = {}
    for temp, (grade, gp, active) in cards(rules.systems(snap)).items():
        tpl = templates.get("PowcardTempInfos", temp) or {}
        suite_id = int(tpl.get("SuiteId", 0))
        if suite_id not in suites:
            suites[suite_id] = msg.suites.add(suiteId=suite_id)
        owned.setdefault(suite_id, []).append(grade)
        card = suites[suite_id].cardInfos.add(tempId=temp, grade=grade, gp=gp, isActive=active)
        card.buf.sonType, card.buf.bufId = int(tpl.get("SonType", 0)), int(tpl.get("BufId", 0)) + grade - 1
        card.buf.fixValue, card.buf.percent = int(tpl.get("fixvalue", 0)), int(tpl.get("percent", 0))
    for suite_id, entry in suites.items():
        row = templates.get("PowCardSuiteTemInfos", suite_id)
        if row is None:
            continue
        for son_type, buf_id in suite_buffs(row, owned[suite_id], slots or SUITE_SLOTS):
            # (dedução) fixvalue/percent da linha da coleção (0/0 na 1002, igual ao login.json #76, só turco)
            entry.bufInfos.add(sonType=son_type, bufId=buf_id, fixValue=int(row.get("fixvalue") or 0),
                               percent=int(row.get("percent") or 0))  # fmt: skip
    return msg


S_FIGHT_ADD = 4902
BUFF_FLAT = ("Attack", "Defence", "MagicDefence", "Crit", "Block", "Leadpawn")  # CampaignBufferTemps


def fight_add_msg(
    snap: PlayerSnapshot, templates: GameTemplates, slots: list[list[int]] | None = None
) -> pb.PowcardFightAddMsg | None:
    """4902: o poder que as cartas somam em cada tipo de luta (CampaignBufferTemps.Types, 800-807; o cliente só
    mostra na dica do botão das cartas, MagicCardModel.getFightText). Os buffs das cartas e das coleções (os mesmos
    bufIds do 4905) somados por Types, com a fórmula do ``HeroStats.fighting_capacity`` (flat + 1,05 MAtk +
    Vida/5). (só turco: login #3, teknoloji_upgrade #4) 608/768/608/1521/768 batem exatos com as cartas do
    login #76, todas com isActive 0: conta toda carta que o jogador tem. (dedução) Crit/Block/Leadpawn no flat
    como ForceHit/Parry/ConatArmy; nenhum buff das cartas tem esses três. Sem cartas: vazio do nível
    ``CARD_OPEN_GRADE`` em diante (captura 20261029-121453-1 #422, #536), None antes (o nível 31 não manda)."""
    if not cards(rules.systems(snap)):
        return pb.PowcardFightAddMsg() if snap.character.grades >= CARD_OPEN_GRADE else None
    totals: dict[int, dict[str, int]] = {}
    for suite in powcard_msg(snap, templates, slots).suites:
        for buf in [*(c.buf for c in suite.cardInfos), *suite.bufInfos]:
            row = templates.get("CampaignBufferTemps", buf.bufId) or {}
            got = totals.setdefault(int(row.get("Types") or 0), {})
            for key in (*BUFF_FLAT, "MagicAttack", "Live"):
                got[key] = got.get(key, 0) + int(row.get(key) or 0)
    msg = pb.PowcardFightAddMsg()
    for camp, t in totals.items():
        if camp:
            power = (20 * sum(t[k] for k in BUFF_FLAT) + 21 * t["MagicAttack"] + 4 * t["Live"]) // 20
            # (visto) captura 20261029-121453-1 #4046-#4107: sem userid, na ordem em que a coleção entrou
            msg.singlefightadd.add(op=0, campType=camp, add=power)
    return msg


S_CAMP_BUFFS = 4903
# CampaignBufferTemps.Types dos lugares (cliente MagicCardModel.cardType): masmorra de vários (MultiCampaign, 多人副本),
# torre de provação, labirinto (TowerCampaign), arena e campo de batalha
CAMP_MULTI, CAMP_TRIAL, CAMP_TOWER, CAMP_ARENA, CAMP_WARFIELD = 800, 801, 802, 806, 807
CARD_STATS = {"Attack": "PhyAttack", "Defence": "PhyDefence", "MagicAttack": "MagicAttack"}
CARD_STATS |= {"MagicDefence": "MagicDefence", "Crit": "ForceHit", "Block": "Parry", "Live": "Live"}


def camp_type(row: Row) -> int:
    """Tipo de lugar das cartas para a campanha (linha de ``Campaigns``). (dedução) Types 4 (Catacombs, Necropolis)
    é o labirinto; a Tower of Kings (82xx) é a torre de provação; as masmorras (Types 0), a masmorra de vários."""
    if row.get("Types") == "4":
        return CAMP_TOWER
    if 8200 <= int(row.get("CampaignId") or 0) < 8300:
        return CAMP_TRIAL
    return CAMP_MULTI if row.get("Types") == "0" else 0


def camp_buffs_msg(
    snap: PlayerSnapshot, templates: GameTemplates, camp: int, slots: list[list[int]] | None = None
) -> pb.PowCardBufListMsg:
    """4903 (só turco: exp_kitabi #31 numa masmorra, 3041/3020/3000; yeralti #36 no labirinto, 4061/4020/4000; vazio
    ao sair, no login e no 4595): os buffs das cartas e coleções do 4905 cujo ``CampaignBufferTemps.Types`` é o do lugar
    (cada coleção é de um tipo: a 1000 dá 3041/3020/3000 no 800, a 1001 dá 4061/4020/4000 no 802)."""
    msg = pb.PowCardBufListMsg()
    for suite in powcard_msg(snap, templates, slots).suites if camp else ():
        for buf in [*(c.buf for c in suite.cardInfos), *suite.bufInfos]:
            if int((templates.get("CampaignBufferTemps", buf.bufId) or {}).get("Types") or 0) == camp:
                msg.bufInfos.add().CopyFrom(buf)
    return msg


def camp_stats(
    snap: PlayerSnapshot, templates: GameTemplates, camp: int, slots: list[list[int]] | None = None
) -> dict[str, int]:
    """O que os buffs do 4903 somam nos atributos do herói na luta (dedução: as colunas de ``CampaignBufferTemps``
    com os nomes do ``HeroStats``; Crit e Block como ForceHit e Parry, Leadpawn fica fora)."""
    total: dict[str, int] = {}
    for buf in camp_buffs_msg(snap, templates, camp, slots).bufInfos:
        row = templates.get("CampaignBufferTemps", buf.bufId) or {}
        for col, key in CARD_STATS.items():
            total[key] = total.get(key, 0) + int(row.get(col) or 0)
    return total


def send_camp_buffs(s: GameSession, camp: int) -> None:
    """Com cartas: o 150 (com o 4902 na frente, ``GameSession.send``) e o 4903 do lugar (só turco: exp_kitabi
    #29-#31, av_askeri #63-#65, online_odul #3-#5)."""
    from .player import _army  # player importa este módulo

    snap = s.snapshot
    assert snap is not None
    if not cards(rules.systems(snap)):
        return
    _army(s)
    s.send(S_CAMP_BUFFS, camp_buffs_msg(snap, s.ctx.templates, camp, s.ctx.world.settings.get("powcard_suite_slots")))


def send_fight_add(s: GameSession, times: int = 1) -> None:
    """``times`` 4902 soltos (fora do que o ``GameSession.send`` põe antes do 150). Nada sem cartas abaixo do 32."""
    assert s.snapshot is not None
    if (add := fight_add_msg(s.snapshot, s.ctx.templates, s.ctx.world.settings.get("powcard_suite_slots"))) is None:
        return
    for _ in range(times):
        s.send(S_FIGHT_ADD, add)


def send_cards(s: GameSession) -> None:
    """4905 e o 4902 logo depois (só turco: login #76-#77)."""
    assert s.snapshot is not None
    slots = s.ctx.world.settings.get("powcard_suite_slots")
    s.send(S_POWCARD, powcard_msg(s.snapshot, s.ctx.templates, slots))
    if (add := fight_add_msg(s.snapshot, s.ctx.templates, slots)) is not None:
        s.send(S_FIGHT_ADD, add)


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
        # idioma card.cardHelper.content02 "Activate all cards in your inventory?" (MagicCardSlotView): usa as
        # cartas da mochila. Sem nenhuma, só o 111 (captura 20261029-121453-1 #574-#575, #4119-#4120, esta com
        # cartas já na coleção). *(dedução)* com cartas: os pacotes do 5006 de cada uma
        from .items import _use_power_card  # items importa este módulo

        held = [i for i in bag.in_bag(snap) if (templates.get("ItemTempInfos", i.template_id) or {}).get("SonType")
                == CARD_ITEM]  # fmt: skip
        if not held:
            alert(s, NO_CARDS)
            return
        for item in held:
            await _use_power_card(s, item, templates.get("ItemTempInfos", item.template_id) or {}, item.count)
        return
    elif msg.op != CARD_TIDY:
        s.log.info("9505 op desconhecida", pedido=str(msg))
        return
    if msg.op != CARD_TIDY:
        store_cards(sy, found)
        await s.ctx.characters.save(sy)
    send_cards(s)
