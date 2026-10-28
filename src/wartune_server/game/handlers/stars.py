"""Estrelas (Astro/Astral): sortear nos cristais, recolher/vender, mover, equipar, devorar, compor, travar,
comprar espaço e loja. Cliente ``StarManager.as``. As ações só têm a captura turca (só turco:
``kader_sistemi``); o tutorial_en só tem o login (#49).

Sacolas: 0 temporária (sorteadas, até 16), 1 mochila (8 + compradas), 2 equipadas.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence

from ...domain.models import PlayerSnapshot, Star, StarBag
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates, Row
from .. import rules, social
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .player import _army, _player

S_MOVE, S_PICK, S_RAND, S_COMPOSE = 4178, 4179, 4180, 4479
SITE_COST = (4000, 5000, 6000, 8000, 10000)  # ouro por cristal (MakeStarView inglês ``_makeStarCosts``)
# MakeStarView: "Astro Expense:{0}\n Star Point:{1}" com {1} = 1..5 do cristal 0..4
QUICK_MIN_GOLD = 20000  # StarRandView: sorteio rápido (site -1)
TEMP_MAX, BAG_BASE, MAX_GRADE = 16, 8, 10
# StarManager.sendBagCellBuy: (comprados/4 + 1) x 395, "unlock 1 star inventory row" (4 espaços);
# PlayerStarListView.PLAYER_STAR_BAG_COUNT 16 = 8 de base + 8 comprados
BAG_ROW, BAG_ROW_COST, BAG_BOUGHT_MAX = 4, 395, 8
PICK, SELL, PICK_ALL, QUICK_SELL = 1, 2, -2, -1  # StarIconView way 1/2; StarModel -2; DisplayStarView -1
JUNK, ENERGY = "1", "6"  # starTempInfo.Profile: lixo (vende sozinho) e Energine (só comida de EXP)
EXP_TYPES = {"2": "9", "3": "10", "4": "11", "5": "12", "6": "13", "7": "22"}  # Profile -> UpGrade Types
LOCK_QUEST = 53  # QuestCondictionInfos: travar estrela
# 36 "Astro": QuestTemps 3 (nível 25, como a 623 de travar) manda clicar [Astro] e "Upgrade 1 [Astro]" = sortear.
# Para1 1 (a 622 tem 0): sem fonte do que é; todo sorteio passa 1 e conta cada estrela (dedução)
RAND_QUEST, RAND_PARA1 = 36, 1
# ponytail: o oficial não publica as chances do sorteio; pesos por qualidade (Profile) e cristal
# tirados a olho da captura (só turco: kader_sistemi, lixo ~40%), e 30% de abrir o próximo cristal. Valem os do banco
# (``game_settings`` ``star_weights`` e ``star_open_next``, migração 0035); estes são o padrão sem a linha
WEIGHTS = {"1": (40,) * 5, "2": (35, 33, 30, 27, 24), "3": (18, 21, 24, 27, 30), "4": (5, 8, 11, 14, 17)}
WEIGHTS |= {"5": (0, 2, 4, 6, 8), "7": (0, 0, 0, 0, 1), "6": (2,) * 5}
OPEN_NEXT = 0.3
# (visto) oficial_encantar #2753/#2824: o sorteio de uma Profile 5 sai para o servidor inteiro no 83 canal 2. (dedução)
# a Profile 7, mais rara, também; ``game_settings.star_rare_profiles`` troca a lista
RARE_PROFILES, S_CHAT, WORLD = ("5", "7"), 83, 2
RARE_TEXT = '{} just received the extremely rare [<a t="3" id="{}" name="{}" grades="{}"/>] Astral!'
# (só turco: kader_sistemi #64, #112-#122) 111 canal 7 "Kader Tiran lv 2'a geliştirildi." e "Kader Tiran, 200 puan kader
# EXP kazandı"; o de nível volta no 83 canal 3 depois da resposta. TODO(inventado): o inglês, no molde do
# "Town Hall has been upgraded to Lvl. 2" (oficial_20261023-153200 #594) e com Kader = Astral
LEVEL_TEXT, EXP_TEXT, S_ALERT = "Astral {} has been upgraded to Lvl. {}", "Astral {} gained {} Astral EXP", 111
_rng = random.Random()  # abrir o próximo cristal (os testes trocam)


def star_tpl(templates: GameTemplates, star: Star) -> Row:
    return templates.get("starTempInfos", star.template_id) or {}


def star_info(star: Star, player_id: int) -> pb.StarInfoMsg:
    return pb.StarInfoMsg(
        id=star.id or 0,
        templateId=star.template_id,
        userId=player_id,
        pos=star.pos,
        exist=True,
        bagType=star.bag_type,
        grade=star.grade,
        gp=star.gp,
        isLock=star.locked,
    )


def at(snap: PlayerSnapshot, bag: int, pos: int) -> Star | None:
    return next((s for s in snap.stars if (s.bag_type, s.pos) == (bag, pos)), None)


def bag(snap: PlayerSnapshot, kind: int) -> list[Star]:
    return sorted((s for s in snap.stars if s.bag_type == kind), key=lambda s: s.pos)


def free_pos(snap: PlayerSnapshot, kind: int, size: int) -> int | None:
    used = {s.pos for s in bag(snap, kind)}
    return next((p for p in range(size) if p not in used), None)


def bag_size(snap: PlayerSnapshot) -> int:
    return BAG_BASE + rules.systems(snap).star_bag


def equip_slots(snap: PlayerSnapshot) -> int:
    return min(8, snap.character.grades // 10)


def value(templates: GameTemplates, star: Star) -> int:
    """EXP que a estrela dá ao ser devorada: SellGp + EXP dos graus já subidos + gp atual.
    Conferido: 1503 grau 1 devorou 8 estrelas verdes (10), duas 303/1003 (30) e uma 303 com 30 de
    gp (60) = 200 -> grau 2 (70) com 130 sobrando (só turco: kader_sistemi #115)."""
    tpl = star_tpl(templates, star)
    steps = exp_steps(templates, tpl)
    return int(tpl.get("SellGp", 0)) + sum(steps.get(g, 0) for g in range(2, star.grade + 1)) + star.gp


def exp_steps(templates: GameTemplates, tpl: Row) -> dict[int, int]:
    types = EXP_TYPES.get(tpl.get("Profile", ""), "")
    return {int(r["Grades"]): int(r["Data"]) for r in templates.find("UpGradeTempInfos", Types=types)}


def feed(templates: GameTemplates, star: Star, gp: int) -> None:
    steps = exp_steps(templates, star_tpl(templates, star))
    star.gp += gp
    while star.grade < MAX_GRADE and (need := steps.get(star.grade + 1)) is not None and star.gp >= need:
        star.gp -= need
        star.grade += 1


def eat_all(templates: GameTemplates, star: Star, gp: int) -> list[str]:
    """``feed`` com os textos de nível (um por grau, dedução) que saem antes e depois da resposta."""
    before = star.grade
    feed(templates, star, gp)
    name = star_tpl(templates, star).get("TemplateName", "")
    return [LEVEL_TEXT.format(name, g) for g in range(before + 1, star.grade + 1)]


def say_gain(s: GameSession, star: Star, gp: int, levels: list[str]) -> None:
    """(só turco: kader_sistemi #112-#113) os 111 de nível e depois o 111 com a EXP ganha."""
    name = star_tpl(s.ctx.templates, star).get("TemplateName", "")
    for text in [*levels, EXP_TEXT.format(name, gp)]:
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))


def say_levels(s: GameSession, levels: list[str]) -> None:
    """(só turco: kader_sistemi #116, #121) o 83 canal 3 de cada nível."""
    for text in levels:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


def temp_full(snap: PlayerSnapshot) -> bool:
    """(dedução) o 4484 sai quando a temporária enche (kader_sistemi #110-#111) ou deixa de estar cheia (#115-#117);
    a composição na mochila (#120-#121) e a devoração (#126) não o mandam."""
    return free_pos(snap, StarBag.TEMP, TEMP_MAX) is None


def sites(snap: PlayerSnapshot) -> list[int]:
    return [int(x) for x in rules.systems(snap).star_sites.split(",")]


def rand_msg(snap: PlayerSnapshot, stars: list[Star], player_id: int) -> pb.StarRandRspMsg:
    msg = pb.StarRandRspMsg(site=sites(snap))
    for star in stars:
        msg.starRand.add(dropSite=star.pos, starInfo=star_info(star, player_id))
    return msg


def move_msg(changes: list[tuple[int, int, Star | None]], player_id: int) -> pb.StarMoveRspMsg:
    msg = pb.StarMoveRspMsg()
    for kind, pos, star in changes:
        entry = msg.move.add(changeType=kind, changePos=pos)
        if star is not None:
            entry.star_Info.CopyFrom(star_info(star, player_id))
    return msg


def login_stars(s: GameSession) -> None:
    """Resposta ao flag ``star`` do 8224: mochila + equipadas (4178, só se houver; só turco: login.json #51) e os
    cristais (4180). Sem estrela, só o 4180 (tutorial_en #49)."""
    snap = s.snapshot
    assert snap is not None
    placed = [(st.bag_type, st.pos, st) for st in snap.stars if st.bag_type != StarBag.TEMP]
    if placed:
        s.send(S_MOVE, move_msg(placed, s.player_id))  # type: ignore[arg-type]
    s.send(S_RAND, rand_msg(snap, bag(snap, StarBag.TEMP), s.player_id))


def roll(templates: GameTemplates, grade: int, site: int, table: Mapping[str, Sequence[float]] = WEIGHTS) -> Row:
    """Estrela sorteada no cristal ``site``: peso ``table[Profile][site]`` (``star_weights`` do banco)."""
    pool = [r for r in templates.rows("starTempInfos") if int(r["NeedGrades"]) <= grade and r["Profile"] in table]
    weights = [table[r["Profile"]][site] for r in pool]
    return random.choices(pool, weights=weights)[0]


@router.on(8269)
async def star_rand(s: GameSession, msg: pb.StarRandReqMsg) -> None:
    """Sorteia no cristal ``site`` (ouro SITE_COST, ou um sorteio grátis do dia); -1 = rápido (repete
    no melhor cristal aberto até encher ou acabar o ouro). Resposta (só turco: kader_sistemi #9-#11): 109, 3, 4180;
    no 1º do dia (#1-#8) 109, 3, 4152 do leed, 3, 4180 e o 83 da devoção; o que enche a temporária (#110-#111) leva o
    4484 depois (``temp_full``)."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy, c = rules.systems(snap), snap.character
    rules.refresh_star_day(sy, s.ctx.clock.now())
    opened = sites(snap)
    quick = msg.site == -1
    if (quick and c.gold < QUICK_MIN_GOLD) or (not quick and not (0 <= msg.site < len(opened) and opened[msg.site])):
        s.log.info("8269 recusado", pedido=str(msg))
        return
    new: list[Star] = []
    settings = s.ctx.world.settings
    table, open_next = settings.get("star_weights") or WEIGHTS, float(settings.get("star_open_next", OPEN_NEXT))
    while (pos := free_pos(snap, StarBag.TEMP, TEMP_MAX)) is not None:
        site = max(i for i, o in enumerate(opened) if o) if quick else msg.site
        free = sy.star_free > 0
        if not free and c.gold < SITE_COST[site]:
            break
        if free:
            sy.star_free -= 1
        else:
            c.gold -= SITE_COST[site]
        sy.star_point += site + 1  # ponytail: o grátis do dia também dá ponto, o cliente não diz; mudar com captura
        tpl = roll(templates, c.grades, site, table)
        star = Star(c.id or 0, int(tpl["TemplateId"]), bag_type=StarBag.TEMP, pos=pos)
        snap.stars.append(star)
        new.append(star)
        if site:  # o cristal usado apaga; o 0 fica sempre aceso (só turco: kader_sistemi)
            opened[site] = 0
        if site + 1 < len(opened) and _rng.random() < open_next:
            opened[site + 1] = 1
        sy.star_sites = ",".join(map(str, opened))
        if not quick:
            break
    if not new:
        s.log.info("8269 recusado: sem ouro ou sem espaço", pedido=str(msg))
        return
    quests = rules.quest_event(snap, templates, RAND_QUEST, RAND_PARA1, len(new))
    await s.ctx.characters.save(c, sy, *new, *quests)
    castle_yield(s)
    _player(s)
    from . import events  # handlers.events importa login, que importa player

    devotion = events.devotion(s)
    await events.leed_done(s, events.ASTRAL_LEED, say=False)
    if up := events.devotion(s) != devotion:
        _player(s)
    s.send(S_RAND, rand_msg(snap, new, s.player_id))
    if up:
        events.say_devotion(s)
    if temp_full(snap):
        events.send_titles(s)
    rare = tuple(settings.get("star_rare_profiles") or RARE_PROFILES)
    for star in new:
        if (tpl := star_tpl(templates, star)).get("Profile") in rare:
            link = social.player_link(s.ctx, c)
            shout = pb.ChatChannelMsg(
                channel=WORLD, encodeMsg=RARE_TEXT.format(link, star.template_id, tpl["TemplateName"], star.grade)
            )
            for other in s.ctx.online.sessions():
                other.send(S_CHAT, shout)
    if quests:
        from .army import send_quests

        send_quests(s, quests)


@router.on(8268)
async def star_pick(s: GameSession, msg: pb.StarPickReqMsg) -> None:
    """Tira da temporária (cliente inglês): ``dropsite`` = posição com ``way`` 1 recolhe e 2 vende (StarIconView);
    -2 recolhe todas ("Collect all", StarModel.quickPickupClick); -1 vende as de ``Profile <= way``, grau 1 e
    sem gp (venda rápida, DisplayStarView/StarModel.checkAction). O lixo (Profile 1) sempre é vendido (SellGold,
    bagType -1 no 4179). Resposta (só turco: kader_sistemi #56-#60): 109 e 4179 dos vendidos, 4178 e 4179 dos
    recolhidos, sem o 3."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy, c = rules.systems(snap), snap.character
    temp = bag(snap, StarBag.TEMP)
    if msg.dropsite == PICK_ALL:
        chosen, sell = temp, False
    elif msg.dropsite == QUICK_SELL:
        cheap = [st for st in temp if int(star_tpl(templates, st).get("Profile") or 0) <= msg.way]
        chosen, sell = [st for st in cheap if st.grade == 1 and st.gp == 0], True
    else:
        chosen, sell = [st for st in temp if st.pos == msg.dropsite and msg.way in (PICK, SELL)], msg.way == SELL
    sold, picked, deleted, changed = [], [], [], []
    for star in chosen:
        tpl = star_tpl(templates, star)
        if tpl.get("Profile") == JUNK or sell:
            c.gold += int(tpl.get("SellGold", 0))
        elif (pos := free_pos(snap, StarBag.BAG, bag_size(snap))) is not None:
            star.bag_type, star.pos, drop = StarBag.BAG, pos, star.pos
            picked.append((drop, star))
            changed.append(star)
            continue
        else:
            continue  # mochila cheia: fica na temporária
        sold.append(Star(star.character_id, star.template_id, bag_type=-1, pos=star.pos, grade=star.grade))
        snap.stars.remove(star)
        deleted.append(star)
    if not sold and not picked:
        s.log.info("8268 recusado", pedido=str(msg))
        return
    await s.ctx.characters.save(c, sy, *changed, delete=tuple(deleted))
    if sold:
        castle_yield(s)
        s.send(S_PICK, rand_msg(snap, sold, s.player_id))
    if picked:
        s.send(S_MOVE, move_msg([(StarBag.BAG, st.pos, st) for _, st in picked], s.player_id))
        reply = pb.StarRandRspMsg(site=sites(snap))
        for drop, star in picked:
            reply.starRand.add(dropSite=drop, starInfo=star_info(star, s.player_id))
        s.send(S_PICK, reply)


@router.on(8267)
async def star_move(s: GameSession, msg: pb.StarMoveReqMsg) -> None:
    """Move entre mochila (1) e equipadas (2). Destino ocupado: com ``eat`` a estrela do destino
    devora a movida, senão trocam. Equipadas: até min(8, nível/10), sem repetir MasterType, sem lixo nem fonte de
    energia. Resposta: 4178 (+4902 e 150 se mexeu nas equipadas). Devorando (só turco: kader_sistemi #122-#126): 111 da
    EXP, 4902 e 150, um 4178 com a origem vazia e outro com a que comeu, 83 de cada nível."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    src = at(snap, msg.beginStarType, msg.beginPos)
    dst = at(snap, msg.endStarType, msg.endPos)
    kinds = {StarBag.BAG, StarBag.EQUIP}
    size = bag_size(snap) if msg.endStarType == StarBag.BAG else equip_slots(snap)
    ok = src is not None and msg.endStarType in kinds and msg.beginStarType in kinds and 0 <= msg.endPos < size
    ok = ok and src is not dst
    if not ok or src is None:
        s.log.info("8267 recusado", pedido=str(msg))
        return
    changes: list[tuple[int, int, Star | None]] = []
    deleted: list[Star] = []
    if dst is not None and msg.eat:
        if dst.locked or src.locked or star_tpl(templates, dst).get("Profile") == ENERGY:
            s.log.info("8267 recusado: travada", pedido=str(msg))
            return
        gp = value(templates, src)
        levels = eat_all(templates, dst, gp)
        snap.stars.remove(src)
        deleted.append(src)
        changes += [(msg.beginStarType, msg.beginPos, None), (dst.bag_type, dst.pos, dst)]
    else:
        if not equip_ok(snap, templates, src, msg.endStarType, dst) or (
            dst is not None and not equip_ok(snap, templates, dst, msg.beginStarType, src)
        ):
            s.log.info("8267 recusado: não equipa", pedido=str(msg))
            return
        src.bag_type, src.pos = msg.endStarType, msg.endPos
        if dst is not None:
            dst.bag_type, dst.pos = msg.beginStarType, msg.beginPos
        changes += [(msg.beginStarType, msg.beginPos, dst), (msg.endStarType, msg.endPos, src)]
    await s.ctx.characters.save(*(x for x in (src, dst) if x is not None and x not in deleted), delete=tuple(deleted))
    equip = StarBag.EQUIP in (msg.beginStarType, msg.endStarType)
    if deleted:
        assert dst is not None
        say_gain(s, dst, gp, levels)
        if equip:
            _army(s)
        for change in changes:
            s.send(S_MOVE, move_msg([change], s.player_id))
        say_levels(s, levels)
        return
    s.send(S_MOVE, move_msg(changes, s.player_id))
    if equip:
        _army(s)


def equip_ok(snap: PlayerSnapshot, templates: GameTemplates, star: Star, kind: int, leaving: Star | None) -> bool:
    if kind != StarBag.EQUIP:
        return True
    tpl = star_tpl(templates, star)
    others = [x for x in bag(snap, StarBag.EQUIP) if x is not star and x is not leaving]
    same = any(star_tpl(templates, x).get("MasterType") == tpl.get("MasterType") for x in others)
    return (
        tpl.get("Profile") not in (JUNK, ENERGY) and not same and snap.character.grades >= int(tpl.get("NeedGrades", 1))
    )


@router.on(8331)
async def star_compose(s: GameSession, msg: pb.StarComposeReqMsg) -> None:
    """Composição rápida: a estrela em ``pos`` devora todas as outras não travadas da mesma sacola
    (0 temporária, 1 mochila); o lixo da temporária é vendido. Resposta (só turco: kader_sistemi #64-#65, #112-#121):
    111 de cada nível, 111 da EXP, 109 (dedução: só se vendeu lixo; #64 sem lixo não tem), 4479 com as que sobraram
    (temporária) ou 4178 (mochila), 83 de cada nível e, se a temporária estava cheia, o 4484 (``temp_full``)."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    c = snap.character
    target = at(snap, msg.bagType, msg.pos)
    if (
        target is None
        or msg.bagType not in (StarBag.TEMP, StarBag.BAG)
        or star_tpl(templates, target).get("Profile") in (JUNK, ENERGY)
    ):
        s.log.info("8331 recusado", pedido=str(msg))
        return
    eaten, gp, junk, full = [], 0, False, temp_full(snap)
    for star in bag(snap, msg.bagType):
        profile = star_tpl(templates, star).get("Profile")
        if star is target or star.locked or star.grade >= MAX_GRADE:  # o Energine também é devorado (HoroscopeFrame)
            continue
        if profile == JUNK:
            c.gold += int(star_tpl(templates, star).get("SellGold", 0))
            junk = True
        else:
            gp += value(templates, star)
        snap.stars.remove(star)
        eaten.append(star)
    levels = eat_all(templates, target, gp)
    await s.ctx.characters.save(c, target, delete=tuple(eaten))
    if gp:
        say_gain(s, target, gp, levels)
    if msg.bagType == StarBag.TEMP:
        if junk:
            castle_yield(s)
        s.send(S_COMPOSE, rand_msg(snap, bag(snap, StarBag.TEMP), s.player_id))
    else:
        changes = [(StarBag.BAG, st.pos, None) for st in eaten] + [(StarBag.BAG, target.pos, target)]
        s.send(S_MOVE, move_msg(changes, s.player_id))  # type: ignore[arg-type]
    say_levels(s, levels)
    if msg.bagType == StarBag.TEMP and full and not temp_full(snap):
        from .events import send_titles  # handlers.events importa login, que importa player

        send_titles(s)


@router.on(8330)
async def star_lock(s: GameSession, msg: pb.StarLockReqMsg) -> None:
    """Trava/destrava a estrela contra a composição. Resposta: 4180 (temporária) ou 4178."""
    snap = s.snapshot
    assert snap is not None
    star = at(snap, msg.starType, msg.pos)
    if star is None:
        s.log.info("8330 recusado", pedido=str(msg))
        return
    star.locked = not star.locked
    quests = rules.quest_event(snap, s.ctx.templates, LOCK_QUEST, 0, 1) if star.locked else []
    await s.ctx.characters.save(star, *quests)
    if star.bag_type == StarBag.TEMP:
        s.send(S_RAND, rand_msg(snap, [star], s.player_id))
    else:
        s.send(S_MOVE, move_msg([(star.bag_type, star.pos, star)], s.player_id))
    if quests:
        from .army import send_quests

        send_quests(s, quests)
    if star.locked:  # (visto) 20261024-191924-1 #20257: 4178, 112 e 111 "Astral Locked!"; sem captura de destravar
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Astral Locked!"))


@router.on(8270)
async def star_bag_buy(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Compra uma linha (4 espaços) da mochila de estrelas: (comprados/4 + 1) x 395 diamantes, até 16 espaços
    (StarManager.sendBagCellBuy, PlayerStarListView); payType 0 aceita vinculado. Resposta: 3 (starCount)."""
    snap = s.snapshot
    assert snap is not None
    sy = rules.systems(snap)
    cost = (sy.star_bag // BAG_ROW + 1) * BAG_ROW_COST
    spent = None
    if sy.star_bag < BAG_BOUGHT_MAX:
        spent = ledger.pay(
            snap.character, cost, bind=msg.payType == 0, reason="star_bag", ref="", now=s.ctx.clock.now()
        )
    if spent is None:
        s.log.info("8270 recusado", pedido=str(msg))
        return
    sy.star_bag = min(sy.star_bag + BAG_ROW, BAG_BOUGHT_MAX)
    await s.ctx.characters.save(snap.character, sy, spent)
    _player(s)


@router.on(8325)
async def star_daily_reset(s: GameSession, _: object) -> None:
    """O cliente pede às 5h: renova o sorteio grátis do dia. Resposta: 3 (startFree)."""
    snap = s.snapshot
    assert snap is not None
    sy = rules.systems(snap)
    before = sy.star_day
    rules.refresh_star_day(sy, s.ctx.clock.now())
    if sy.star_day != before:
        await s.ctx.characters.save(sy)
    _player(s)


@router.on(8341)
async def star_shop_buy(s: GameSession, msg: pb.StarShopMsg) -> None:
    """Loja de estrelas: ``goodId`` = starTempInfo; custa o StarPoint dele. Resposta: 4178 e 3."""
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    sy, c = rules.systems(snap), snap.character
    tpl = templates.get("starTempInfos", msg.goodId)
    price = int(tpl.get("StarPoint", 0)) if tpl else 0
    pos = free_pos(snap, StarBag.BAG, bag_size(snap))
    if tpl is None or price <= 0 or sy.star_point < price or pos is None:
        s.log.info("8341 recusado", pedido=str(msg))
        return
    sy.star_point -= price
    star = Star(c.id or 0, msg.goodId, bag_type=StarBag.BAG, pos=pos)
    snap.stars.append(star)
    await s.ctx.characters.save(sy, star)
    s.send(S_MOVE, move_msg([(StarBag.BAG, pos, star)], s.player_id))
    _player(s)
