"""Guilda: bênção do altar."""

from __future__ import annotations

import random
from datetime import datetime

from ....domain.models import (
    ConsortiaMember,
)
from ....protocol.messages import wartune_pb2 as pb
from ... import bag, rules, social
from ... import guild as gd
from ...builders import login as b
from ...builders.player import quest_update
from ...router import router
from ...session import GameSession
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
    random.shuffle(sites := _sites(s))
    s.send(S_SITE, b.complete(pb.ConsortiaInfoMsg(site=sites)))


@router.on(5145)
async def bless(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    """Bênção: gasta ``Property1`` de contribuição, até ``Property2`` vezes por dia (nível do altar).
    ``blessSite`` é a posição na lista do 4144 (-1 = nada). O prêmio fica na linha do membro até o 8216. Com um prêmio
    por pegar, o cliente pergunta antes (``ConsortiaAltarHelper.canBless``: "abandon the item(s) and continue?") e só
    manda o 5145 se o jogador abandonar: o prêmio novo toma o lugar do antigo.

    ponytail: a tabela de prêmios do oficial não está nos templates; o prêmio é sempre um item
    do mercado da guilda liberado pelo nível do altar, na casa "Shop Item" (Site 1). A bênção
    rápida (``param1`` > 1, VIP 6) fica recusada: o m6 (ConsortiaAltarFrame) mostra o VIP 6 e as 10
    bênçãos, mas não o custo nem a forma da resposta.
    """
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
    ok = mine is not None and row is not None and msg.param1 <= 1
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
    if not pool or 1 not in sites:
        _refuse(s, 5145, "templates sem prêmio")
        s.send(S_BLESS, b.complete(pb.ConsortiaMsg(blessSite=-1, blessLeftTime=used)))
        return
    prize = int(random.choice(pool)["ItemId"])
    c.consortia_offer -= int(row["Property1"])
    member = mine[1]
    member.bless_count, member.bless_day = used + 1, _day(now)
    member.bless_item, member.bless_item_count = prize, 1
    snap = s.snapshot
    assert snap is not None
    quests = rules.quest_event(snap, s.ctx.templates, rules.BLESS_CONDITION, 0, 1)  # missão 30
    await s.ctx.characters.save(c, member, *quests)
    _player(s)
    s.send(
        S_BLESS,
        b.complete(pb.ConsortiaMsg(blessLeftTime=used + 1, blessSite=sites.index(1), blessTempId=prize, blessCount=1)),
    )
    if quests:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(snap)))
    # (visto) oficial_encantar #1723/#1749/#2377/#2383, 231733 #3250/#3332: o prêmio de outros jogadores no 83 canal 2
    # (gema, chave, chicote, pedra da sorte); (dedução) todo prêmio, já que o prêmio daqui é um item do mercado
    text = f"Congratulations to {social.player_link(s.ctx, c)} for obtaining {social.item_link(s.ctx.templates, prize)}"
    shout = pb.ChatChannelMsg(channel=WORLD, encodeMsg=f"{text} x1 from Guild Blessing!")
    for other in s.ctx.online.sessions():
        other.send(S_CHAT, shout)
    from .. import events  # handlers.events importa login, que importa a guilda

    await events.leed_done(s, events.BLESS_LEED)  # LeedTemp 12 "Perform a guild blessing" (PassCount 2)


@router.on(8216)
async def altar_take(s: GameSession, _: object) -> None:
    """Pega o prêmio da bênção para a mochila (4143 ``result``). Sem espaço livre, o prêmio fica no membro.

    ``bag.fits``/``bag.add`` contam os espaços comprados e empilham onde dá, como a loja comum.
    ponytail: o prêmio fica na linha do membro, então sair da guilda antes de pegar perde o prêmio
    (o oficial não mostrou esse caso).
    """
    snap, mine, now = s.snapshot, _mine(s), _now(s)
    assert snap is not None
    member = mine[1] if mine is not None else None
    goods = [(member.bless_item, member.bless_item_count)] if member is not None and member.bless_item else []
    if member is None or not goods or not bag.fits(snap, s.ctx.templates, goods, now):
        s.send(S_ADDFRESH, b.complete(pb.ConsortiaMsg(result=False)))
        return
    member.bless_item, member.bless_item_count = 0, 0
    got = bag.add(snap, s.ctx.templates, goods[0][0], goods[0][1], now)
    await s.ctx.characters.save(member, *got)
    s.send(S_ITEMS, bag.moved(got, s.player_id))
    s.send(S_ADDFRESH, b.complete(pb.ConsortiaMsg(result=True)))
