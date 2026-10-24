"""Guilda: contribuição, melhorias, habilidades e mercado."""

from __future__ import annotations

import math
from datetime import datetime

from ....domain.models import (
    Consortia,
    ConsortiaMember,
    PlayerSnapshot,
    Quest,
)
from ....protocol.messages import wartune_pb2 as pb
from ....services import ledger
from ... import bag, rules
from ... import guild as gd
from ...builders import login as b
from ...builders.player import quest_update
from ...castle import castle_yield
from ...router import router
from ...session import GameSession
from ..login import army
from .common import (
    GOLD_PER_OFFER,
    GUILD_SHOP,
    POINTS_PER_OFFER,
    QUICK_SECONDS,
    R_FAIL,
    R_GUILD,
    R_LEVEL,
    R_LIMIT,
    R_NO_ITEM,
    R_NO_MONEY,
    R_NO_PLAYER,
    R_OK,
    S_ARMY,
    S_CHAT,
    S_ITEMS,
    S_OFFER,
    S_OFFERS,
    S_QUESTS,
    S_SHOP_BUY,
    _alert,
    _can,
    _char,
    _day,
    _event,
    _mine,
    _now,
    _player,
    _profile,
    _push_info,
    _refuse,
)

S_EFFECT, GUILD_SKILL_EFFECT = 110, 3  # (visto) #5047; o cliente não usa o tipo 3

# ---- contribuição e melhorias ----------------------------------------------------------------


def _today(m: ConsortiaMember, now: datetime) -> int:
    return m.today_offer if m.offer_day == _day(now) else 0


@router.on(5144)
async def contribute(s: GameSession, msg: pb.ConsortiaUserOfferReqMsg) -> None:
    """Doação: 1000 ouro ou 5 Balens = 1 de contribuição (arredondados para baixo; só se gasta o que
    vira contribuição), para a riqueza da guilda e para o jogador. Os Balens vinculados vão primeiro
    (cliente inglês ``useBindPoint``: "Use Bound Balens first"). (visto) oficial_20261023-171155-1 #4951-#4961,
    #4964-#4974, #5028-#5036: 109, 3, 111 "Contribution Submitted!", 4152 (a 1ª do dia), 150, 42, 164 e o 83 da
    devoção por último; 10000 de ouro = 10, 5 Balens = 1. Os 4484 (títulos) não vão: não há títulos."""
    mine = _mine(s)
    c = _char(s)
    gold = max(msg.offerGold, 0) // GOLD_PER_OFFER * GOLD_PER_OFFER
    points = max(msg.offerPoint, 0) // POINTS_PER_OFFER * POINTS_PER_OFFER
    if mine is None or gold + points == 0 or c.gold < gold or c.point + c.gift_token < points:
        _refuse(s, 5144, "sem guilda ou sem recursos", ouro=msg.offerGold, diamantes=msg.offerPoint)
        return
    guild, member = mine
    now = _now(s)
    entry = ledger.pay(c, points, bind=True, reason="guild_contribute", ref=f"guild:{guild.id}", now=now)
    assert entry is not None  # saldo conferido acima
    c.gold -= gold
    offer = gold // GOLD_PER_OFFER + points // POINTS_PER_OFFER
    c.consortia_offer += offer
    c.consortia_total_offer += offer
    guild.offer += offer
    guild.total_offer += offer
    member.today_offer, member.offer_day = _today(member, now) + offer, _day(now)
    snap = s.snapshot
    assert snap is not None
    # missão 29: o total acumulado (cliente checkConsortiaOffer), não o valor desta doação
    quests = rules.quest_event(snap, s.ctx.templates, rules.OFFER_CONDITION, 0, c.consortia_total_offer)
    await s.ctx.characters.save(c, guild, member, *quests, *([entry] if points else []))
    if gold:
        castle_yield(s)
    _player(s)
    _alert(s, "Contribution Submitted!")
    from .. import events  # handlers.events importa login, que importa a guilda

    devotion = events.devotion(s)
    await events.leed_done(s, events.GUILD_OFFER_LEED, say=False)
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    s.send(S_ARMY, b.complete(army(s, snap)[0]))
    s.send(S_OFFER, b.complete(pb.ConsortiaMsg(result=True)))
    _push_info(s, guild)
    if events.devotion(s) > devotion:
        events.say_devotion(s)


@router.on(8208)
async def offer_list(s: GameSession, msg: pb.ConsortiaOfferReqMsg) -> None:
    """Ranking de contribuição (de hoje, ou total com ``isHistory``), 8 por página."""
    mine = _mine(s)
    out = pb.ConsortiaContributeRspMsg(totalRows=0)
    now = _now(s)
    rows = []
    for m in s.ctx.guilds.members_of(mine[0].id or 0) if mine else []:
        c = _profile(s, m.character_id)
        if c is not None:
            rows.append((c.nickname or "", c.consortia_total_offer, _today(m, now), m.character_id))
    rows.sort(key=lambda r: (-(r[1] if msg.isHistory else r[2]), -r[1], r[3]))
    page = max(msg.pageIndex, 1)
    out.totalRows = len(rows)
    for nick, total, today, _ in rows[(page - 1) * gd.PAGE : page * gd.PAGE]:
        out.contributeInfo.add(nickName=nick, totalOffer=total, todayOffer=today)
    me = next((i for i, r in enumerate(rows) if r[3] == s.player_id), None)
    if me is not None:
        out.selfInfo.CopyFrom(
            pb.ConsortiaContributeMsg(nickName=rows[me][0], totalOffer=rows[me][1], todayOffer=rows[me][2])
        )
        # (visto) oficial_20261023-171155-1 #4949: sem contribuição (hoje) a posição vem 0
        out.selfOrder = me + 1 if (rows[me][1] if msg.isHistory else rows[me][2]) else 0
    s.send(S_OFFERS, b.complete(out))


def _cooldown_left(guild: Consortia, now: datetime) -> int:
    if guild.code_begin_at is None:
        return 0
    return max(0, guild.code_need - int((now - guild.code_begin_at).total_seconds()))


@router.on(5133)
async def upgrade(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Melhoria da guilda (tipos 1-5, direito 3) ou pesquisa de habilidade (6-12, direito 2),
    paga com a riqueza. O nível sobe já; ``CodeTime`` só trava a próxima melhoria de prédio."""
    kind = msg.upgradeType
    attr = gd.LEVEL_TYPES.get(kind)
    mine = _can(s, gd.R_UPGRADE if kind <= 5 else gd.R_RESEARCH)
    if attr is None or mine is None:
        _refuse(s, 5133, "tipo inválido ou sem direito", tipo=kind)
        return
    guild, now, templates = mine[0], _now(s), s.ctx.templates
    level = getattr(guild, attr) + 1
    row = gd.level_row(templates, kind, level)
    pre = templates.get("ConsortiaLevelInfos", int(row.get("PreTemplateId") or 0)) if row else None
    pre_ok = pre is None or getattr(guild, gd.LEVEL_TYPES[int(pre["Types"])]) >= int(pre["Levels"])
    need = int(row["NeedOffer"]) if row else 0
    busy = kind <= 5 and _cooldown_left(guild, now) > 0
    if row is None or level > gd.MAX_LEVEL or not pre_ok or guild.offer < need or busy:
        _refuse(s, 5133, "nível máximo, requisito, riqueza ou espera", tipo=kind, nivel=level)
        return
    setattr(guild, attr, level)
    guild.offer -= need
    if kind <= 5 and int(row.get("CodeTime") or 0) > 0:
        guild.code_type, guild.code_begin_at, guild.code_need = kind, now, int(row["CodeTime"])
    event = _event(s, guild, gd.EV_UPGRADE, f"{row.get('LevelName', kind)} Lv.{level}")
    # missão de nível da guilda (51) vale para todos os membros online, não só para quem melhorou
    changed: list[tuple[GameSession, PlayerSnapshot, list[Quest]]] = []
    # pesquisa (6-12) não é Para1 da 51: (cliente) checkConsortuaGrade só conhece 1-5
    for o in gd.online_members(s.ctx, guild.id or 0) if kind in rules.GUILD_LEVEL_ATTRS else []:
        member_snap = o.snapshot
        assert member_snap is not None
        if quests := rules.quest_event(member_snap, templates, rules.GUILD_LEVEL_CONDITION, kind, level):
            changed.append((o, member_snap, quests))
    await s.ctx.characters.save(guild, event, *(q for _, _, qs in changed for q in qs))
    _push_info(s, guild)
    for o, member_snap, qs in changed:
        o.send(S_QUESTS, quest_update(qs, rules.quest_bitmap(member_snap)))


@router.on(8545)
async def quick(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Acaba a espera da melhoria: 1 diamante a cada 10 min que faltam (ConsortiaUpgradeFrame);
    ``payType`` 0 gasta os vinculados primeiro."""
    mine = _can(s, gd.R_UPGRADE)
    if mine is None:
        _refuse(s, 8545, "sem direito")
        return
    guild, c, now = mine[0], _char(s), _now(s)
    left = _cooldown_left(guild, now)
    cost = math.ceil(left / QUICK_SECONDS)
    bind = msg.payType == 0
    entry = ledger.pay(c, cost, bind=bind, reason="guild_upgrade_quick", ref=f"guild:{guild.id}", now=now)
    if left <= 0 or entry is None:
        _refuse(s, 8545, "sem espera ou sem diamantes", falta=left)
        return
    guild.code_begin_at, guild.code_need = None, 0
    await s.ctx.characters.save(c, guild, entry)
    _player(s)
    _push_info(s, guild)


@router.on(5147)
async def learn(s: GameSession, msg: pb.ConsortiaMsg) -> None:
    """Aprende um nível de habilidade: gasta a contribuição pessoal (``NeedOffer`` do nível) e
    não passa da pesquisa da guilda daquele tipo. (visto) oficial_20261023-171155-1 #5045-#5051: 3 já sem a
    contribuição e com o nível antigo, 110 ``{propertyType 3, value}`` (o bônus do nível, 40), 150 com os
    atributos novos (``rules.guild_skills``), 3 com o nível novo e 111 "Successfully learned skill!"."""
    attr = gd.SKILLS.get(msg.studySkill)
    mine = _mine(s)
    c = _char(s)
    if attr is None or mine is None:
        _refuse(s, 5147, "tipo inválido ou sem guilda", tipo=msg.studySkill)
        return
    level = getattr(c, attr) + 1
    row = gd.level_row(s.ctx.templates, msg.studySkill, level)
    researched = getattr(mine[0], gd.LEVEL_TYPES[msg.studySkill])
    if row is None or level > gd.MAX_LEVEL or researched < level or c.consortia_offer < int(row["NeedOffer"]):
        _refuse(s, 5147, "nível, pesquisa ou contribuição", tipo=msg.studySkill, nivel=level)
        return
    c.consortia_offer -= int(row["NeedOffer"])
    _player(s)
    setattr(c, attr, level)
    await s.ctx.characters.save(c)
    assert s.snapshot is not None
    value = rules.guild_skills(c, s.ctx.templates).get(msg.studySkill, 0)
    s.send(S_EFFECT, pb.PropertyUpdatedMsg(propertyType=GUILD_SKILL_EFFECT, value=value))
    s.send(S_ARMY, b.complete(army(s, s.snapshot)[0]))
    _player(s)
    _alert(s, "Successfully learned skill!")


def _buy_result(s: GameSession, buy: pb.BuyInfo, result: int) -> None:
    out = pb.BuyInfo(
        isDiscount=False, goodId=buy.goodId, count=buy.count, receiveId=s.player_id, result=result, type=buy.type
    )
    s.send(S_SHOP_BUY, b.complete(pb.ShopMsg(buyInfo=out)))


async def shop_buy(s: GameSession, buy: pb.BuyInfo) -> bool:
    """Compra no mercado da guilda (``ShopTempInfos.ShopType`` 2), paga com a contribuição pessoal.

    Não tem opcode próprio: o cliente usa a compra genérica 5154 (``ShopManager.sendShoping``), e o
    handler dele (``handlers/shop.py``) chama esta função primeiro. Devolve False se o ``goodId`` não
    é do mercado da guilda. Ordem do oficial: 3, 115, 111, 90, 83 (só turco:
    birlik_katkisi_ve_birlik_market_alisverisi #45-#62).
    """
    row = s.ctx.templates.get("ShopTempInfos", buy.goodId, key="Id")
    if row is None or row.get("ShopType") != GUILD_SHOP:
        return False
    from ..shop import count_buy, today_count  # shop importa este módulo

    snap, mine = s.snapshot, _mine(s)
    assert snap is not None
    c, count, now = snap.character, buy.count, s.ctx.clock.now()
    limit = int(row.get("VIP0Count") or -1)  # ShopGoodsInfo.OneDayCount: pedras e peças épicas, 1-5 por dia
    item_row = s.ctx.templates.get("ItemTempInfos", int(row["ItemId"]))
    price = int(row.get("ConsortiaOffer") or 0) * count
    # o primeiro motivo que o cliente mostra (código 0 deixa a mensagem vazia)
    if mine is None or mine[0].shop_level < int(row.get("NeedConsortiaLevels") or 0):
        code = R_GUILD
    elif c.grades < int(row.get("NeedGrades") or 0):
        code = R_LEVEL
    elif buy.receiveId not in (0, s.player_id):  # presente exige gravar outro personagem
        code = R_NO_PLAYER
    elif item_row is None or not 0 < count <= 999:
        code = R_NO_ITEM
    elif limit != -1 and today_count(snap, buy.goodId, now) + count > limit:
        code = R_LIMIT
    elif c.consortia_offer < price:
        code = R_NO_MONEY
    elif not bag.fits(snap, s.ctx.templates, [(int(row["ItemId"]), count)], now):  # espaços comprados contam
        code = R_FAIL
    else:
        code = R_OK
    if code != R_OK:
        _refuse(s, 5154, "mercado, nível, presente, quantidade, contribuição ou mochila", item=buy.goodId, codigo=code)
        _buy_result(s, buy, code)
        return True
    assert item_row is not None
    c.consortia_offer -= price
    got = bag.add(snap, s.ctx.templates, int(row["ItemId"]), count, now)  # empilha onde dá, como a loja comum
    await s.ctx.characters.save(c, *got, count_buy(snap, buy.goodId, count, now))
    _player(s)
    s.send(S_ITEMS, bag.moved(got, s.player_id))
    from .. import events, shop  # os dois importam guild

    events.items_gained(s)
    # o mesmo texto da loja comum (só turco: birlik_katkisi #60-#62 tem a mesma forma, 111, 90 e 83)
    text = shop.bought_text(item_row.get("TemplateName", row["ItemId"]), count)
    _alert(s, text)
    _buy_result(s, buy, 1)
    s.send(S_CHAT, b.complete(pb.ChatChannelMsg(channel=3, encodeMsg=text)))
    return True
