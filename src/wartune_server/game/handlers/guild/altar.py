"""Guilda: bênção do altar."""

from __future__ import annotations

import random
from datetime import datetime

from ....domain.models import ConsortiaMember, Item
from ....protocol.messages import wartune_pb2 as pb
from ... import bag, rewards, rules, social
from ... import guild as gd
from ...builders import login as b
from ...builders.player import quest_update
from ...router import router
from ...session import GameSession
from .. import shop
from .common import (
    GUILD_SHOP,
    S_ADDFRESH,
    S_ALTAR_INFO,
    S_ALTAR_ITEM,
    S_BLESS,
    S_ITEMS,
    S_QUESTS,
    S_SITE,
    _char,
    _day,
    _mine,
    _now,
    _player,
    _refuse,
)

S_CHAT, WORLD = 83, 2  # ChatChannelMsg.channel dos anúncios para o servidor
S_ALERT, S_MINE, ALERT, MINE = 111, 83, 7, 3

_rng = random.Random()  # os testes trocam o sorteio da casa e do prêmio
SHOP_SITE = 1  # "Shop Item": um item do mercado da guilda liberado pelo nível do altar
QUICK_COUNT, QUICK_VIP = 10, 6  # ConsortiaAltarFrame.QUICK_BLESS_COUNT / QUICK_BLESS_VIP_GRADE
FIXED = (2, 1)  # (visto) todo 4144 de 171155, 121659 e 191924 começa com Strength e Shop Item; o resto embaralha
# Prêmio de cada casa (DropViewInfos.Site) = [(TemplateId, quantidade, peso, anuncia?)]. (visto) os 17 prêmios de
# oficial_20261024-121659-1 #549-#589 e 191924 #1413-#1994, a casa pelo 4144 anterior (-500 sempre na 9, -100 na
# 6, -300 na 10), nenhum anunciado; os anunciados (83 canal 2) de 113904 #1723/#1749/#2377/#2383 e 231733 #3250.
# TODO(inventado): os pesos, a casa dos anunciados (gema na 5, o resto na 8) e as sementes (casa 4, nunca saiu)
BLESS_PRIZES: dict[int, list[tuple[int, int, int, bool]]] = {
    2: [(2014003, 1, 1, False)],  # Lvl. 3 Endurance Potion
    3: [(2014701, 1, 1, False), (2014401, 1, 1, False)],  # Crit Scroll, Magic Defense Scroll
    4: [(2160001, 1, 1, False), (2160004, 1, 1, False), (2160010, 1, 1, False)],  # [L1] Gold/Daru/Leveler's Seed
    5: [(2050801, 1, 10, False), (2050403, 1, 1, True)],  # Lvl. 1 Block Gem; Lvl. 3 Magic Defense Gem
    6: [(-100, 5000, 10, False), (-100, 50000, 1, False)],  # Gold
    7: [(2030702, 1, 1, False), (2030703, 1, 1, False)],  # Lvl. 2 e 3 EXP Book
    8: [(208014, 5, 10, False), (208008, 1, 1, True), (208017, 1, 1, True), (2040108, 1, 1, True)],
    9: [(-500, 2, 3, False), (-500, 4, 1, False)],  # Bound Balens
    10: [(-300, 2000, 1, False), (-300, 10000, 1, False)],  # Daru
}

# ---- bênção do altar -------------------------------------------------------------------------


def _bless_used(m: ConsortiaMember, now: datetime) -> int:
    return m.bless_count if m.bless_day == _day(now) else 0


def _sites(s: GameSession) -> list[int]:
    """DropViewInfos: as 10 casas da roleta (o cliente indexa os templates pelo Site), na ordem do último 4144: o
    ``blessSite`` do 5145 é a posição nessa lista."""
    if not s.altar_sites:
        s.altar_sites = [int(r["Site"]) for r in s.ctx.templates.rows("DropViewInfos")][:10]
    return s.altar_sites


@router.on(8215)
async def altar_info(s: GameSession, _: object) -> None:
    """4141 ``blessLeftTime`` = bênçãos já usadas hoje; 4142 o prêmio que falta pegar."""
    mine = _mine(s)
    s.send(S_ALTAR_INFO, b.complete(pb.ConsortiaMsg(blessLeftTime=_bless_used(mine[1], _now(s)) if mine else 0)))
    if mine is not None and mine[1].bless_item:
        item = pb.ItemInfoMsg(templateId=mine[1].bless_item, count=mine[1].bless_item_count, userId=s.player_id)
        s.send(S_ALTAR_ITEM, b.complete(item))


@router.on(8217)
async def altar_site(s: GameSession, _: object) -> None:
    """(visto) oficial_20261023-171155-1 #5151: as casas embaralhadas (2, 1, 4, 5, 8, 7, 9, 6, 3, 10). (dedução) a cada
    abertura do altar uma ordem nova; uma captura só não diz se o oficial guarda a ordem por dia."""
    s.altar_sites = []
    base = _sites(s)
    rest = [x for x in base if x not in FIXED]
    random.shuffle(rest)
    s.altar_sites = [x for x in FIXED if x in base] + rest
    s.send(S_SITE, b.complete(pb.ConsortiaInfoMsg(site=s.altar_sites)))


@router.on(5145)
async def bless(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Bênção: gasta ``Property1`` de contribuição, até ``Property2`` vezes por dia (nível do altar).
    ``blessSite`` é a posição na lista do 4144 (-1 = nada). O prêmio fica na linha do membro até o 8216. Com um prêmio
    por pegar, o cliente pergunta antes (``ConsortiaAltarHelper.canBless``: "abandon the item(s) and continue?") e só
    manda o 5145 se o jogador abandonar: o prêmio novo toma o lugar do antigo.

    A casa sai por sorteio entre as 10 e o prêmio de ``BLESS_PRIZES`` (a "Shop Item", do mercado da guilda liberado
    pelo nível do altar: 121659 #552 Enhanced Bounty Scroll). (visto) 3, 4152 do leed, 45 e o 83 da devoção; os
    prêmios comuns sem anúncio.

    Bênção rápida (``param1`` 10): (cliente) m6 ``ConsortiaAltarFrame.QUICK_BLESS_COUNT`` 10 e
    ``QUICK_BLESS_VIP_GRADE`` 6, com o mesmo ``canBless`` (uma bênção e o custo de uma). TODO(inventado): faz até 10
    (o que sobra no dia e a contribuição deixam), entrega na hora as n-1 primeiras (mochila, cheia -> correio; moeda
    no personagem) e a última fica no altar como a bênção simples, porque o 4144 só leva um prêmio.
    """
    from ..vip import is_vip, vip_grade  # noqa: PLC0415

    mine = _mine(s)
    c, now = _char(s), _now(s)
    used = _bless_used(mine[1], now) if mine else 0
    row = gd.level_row(s.ctx.templates, 3, mine[0].altar_level) if mine else None
    sites = _sites(s)
    pool = [
        r
        for r in s.ctx.templates.find("ShopTempInfos", ShopType=GUILD_SHOP)
        if mine is not None and int(r.get("NeedConsortiaLevels") or 0) <= mine[0].altar_level
    ]
    snap = s.snapshot
    assert snap is not None
    quick = msg.param1 == QUICK_COUNT and is_vip(snap, now) and vip_grade(s, snap) >= QUICK_VIP
    ok = mine is not None and row is not None and (msg.param1 <= 1 or quick)
    if (
        not ok
        or row is None
        or mine is None
        or used >= int(row["Property2"])
        or c.consortia_offer < int(row["Property1"])
    ):
        _refuse(s, 5145, "sem altar, limite do dia, contribuição ou rápida", usadas=used)
        s.send(S_BLESS, b.complete(pb.ConsortiaMsg(blessSite=-1, blessLeftTime=used)))
        return
    prizes = {SHOP_SITE: [(int(r["ItemId"]), 1, 1, False) for r in pool], **BLESS_PRIZES}
    open_sites = [x for x in sites if prizes.get(x)]
    if not open_sites:
        _refuse(s, 5145, "templates sem prêmio")
        s.send(S_BLESS, b.complete(pb.ConsortiaMsg(blessSite=-1, blessLeftTime=used)))
        return
    cost = int(row["Property1"])
    n = min(QUICK_COUNT, int(row["Property2"]) - used, c.consortia_offer // cost) if quick else 1
    extra: list[object] = []
    letters: list[shop.Letter] = []
    texts: list[str] = []
    for i in range(n):
        site = _rng.choice(open_sites)
        options = prizes[site]
        prize, count, _, shout = _rng.choices(options, weights=[o[2] for o in options])[0]
        c.consortia_offer -= cost
        if i == n - 1:
            break
        if prize < 0:  # moeda das n-1 primeiras: no personagem; ouro no teto encerra o lote e o prêmio fica no altar
            from .. import farm  # noqa: PLC0415

            paid = farm._payout(s, snap, prize, count, "altar", reason="altar")
            if paid is None:
                n = i + 1
                break
            extra += paid[0]
        else:
            got, mail = shop.place(s, snap, s.player_id, [(prize, count)], now)
            extra += got
            letters += mail
        texts.append(rewards.text(s.ctx.templates, [(prize, count)]))
    member = mine[1]
    member.bless_count, member.bless_day = used + n, _day(now)
    member.bless_item, member.bless_item_count = prize, count
    quests = rules.quest_event(snap, s.ctx.templates, rules.BLESS_CONDITION, 0, n)  # missão 30
    await shop.save_with_mail(s, letters, c, member, *quests, *extra)
    if extra:
        if items := [x for x in extra if isinstance(x, Item)]:
            s.send(S_ITEMS, bag.moved(items, s.player_id))
        _player(s)  # ouro, Daru e Bound Balens das n-1
    for text in texts:
        s.send(S_MINE, pb.ChatChannelMsg(channel=MINE, encodeMsg=text))
    from .. import events  # handlers.events importa login, que importa a guilda

    # (visto) oficial_20261024-121659-1 #549-#553 e #576-#580: 3, 4152 do leed, 45 e o 83 da devoção depois do 45
    _player(s)
    devotion = events.devotion(s)
    await events.leed_done(s, events.BLESS_LEED, say=False)  # LeedTemp 12 "Perform a guild blessing" (PassCount 2)
    s.send(
        S_BLESS,
        b.complete(
            pb.ConsortiaMsg(blessLeftTime=used + n, blessSite=sites.index(site), blessTempId=prize, blessCount=count)
        ),
    )
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    if events.devotion(s) > devotion:
        events.say_devotion(s)
    if not shout:
        return
    # (visto) 113904 #1723/#1749/#2377/#2383, 231733 #3250/#3332: o prêmio raro de outros jogadores no 83 canal 2
    text = f"Congratulations to {social.player_link(s.ctx, c)} for obtaining {social.item_link(s.ctx.templates, prize)}"
    news = pb.ChatChannelMsg(channel=WORLD, encodeMsg=f"{text} x{count} from Guild Blessing!")
    for other in s.ctx.online.sessions():
        other.send(S_CHAT, news)


@router.on(8216)
async def altar_take(s: GameSession, _: object) -> None:
    """Pega o prêmio da bênção: item para a mochila, moeda no personagem (4143 ``result``). Sem espaço livre ou com o
    ouro no teto, o prêmio fica no membro; (visto) 191924 #1488 e #1594: sem prêmio, só 4143 falso.

    ``bag.fits``/``bag.add`` contam os espaços comprados e empilham onde dá, como a loja comum.
    ponytail: o prêmio fica na linha do membro, então sair da guilda antes de pegar perde o prêmio
    (o oficial não mostrou esse caso).
    """
    from .. import events, farm  # handlers.events importa login, que importa a guilda
    from ..player import balens_changed

    snap, mine, now = s.snapshot, _mine(s), _now(s)
    assert snap is not None
    member = mine[1] if mine is not None else None
    prize, count = (member.bless_item, member.bless_item_count) if member is not None else (0, 0)
    if member is None or not prize or (prize > 0 and not bag.fits(snap, s.ctx.templates, [(prize, count)], now)):
        s.send(S_ADDFRESH, b.complete(pb.ConsortiaMsg(result=False)))
        return
    if prize < 0:  # moeda: (visto) 191924 #1540 ouro 109; #1630 Daru 3; #1498 Bound Balens 3, 150, 4434
        paid = farm._payout(s, snap, prize, count, "altar", reason="altar")
        if paid is None:  # ouro no teto
            s.send(S_ADDFRESH, b.complete(pb.ConsortiaMsg(result=False)))
            return
        member.bless_item, member.bless_item_count = 0, 0
        await s.ctx.characters.save(member, *paid[0])
        await farm._payout_sent(s, snap, prize, None, 0)
        if prize == -500:
            balens_changed(s)
        text = f"Received:  {count} Bound Balens" if prize == -500 else rewards.text(s.ctx.templates, [(prize, count)])
    else:  # (visto) 191924 #1418-#1435: 115, 4476/4426/4484, 111, 4143 e 83 "Received: Lvl. 1 Block Gem x1"
        member.bless_item, member.bless_item_count = 0, 0
        got = bag.add(snap, s.ctx.templates, prize, count, now)
        await s.ctx.characters.save(member, *got)
        s.send(S_ITEMS, bag.moved(got, s.player_id))
        events.items_gained(s)
        text = rewards.text(s.ctx.templates, [(prize, count)])
    s.send(S_ALERT, pb.ChatChannelMsg(channel=ALERT, encodeMsg=text))
    s.send(S_ADDFRESH, b.complete(pb.ConsortiaMsg(result=True)))
    s.send(S_MINE, pb.ChatChannelMsg(channel=MINE, encodeMsg=text))
