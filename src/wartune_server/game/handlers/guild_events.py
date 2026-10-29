"""Atividades da guilda: altar do demônio (chefe de guilda), terra secreta, guerra de guildas e
guerra entre servidores.

Todas acontecem em mapas próprios (7601 altar, 7501 terra secreta, 4501 guerra, 4601 entre
servidores) que o cliente abre com o 125 ``RoomCreatedMsg``. A terra secreta está em ``handlers/fam.py``, o altar em
``handlers/altar.py`` e a guerra de guildas (entrar, lista de participantes, buffs e o mapa) em
``handlers/guildwar.py``; a entre servidores fica recusada e os pacotes de dentro do mapa só registram no
log. O que tem estado fora do mapa (abrir o altar, listas vazias, os grupos da guerra) está aqui.
Dependências em docs/guilda.md.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from .. import guild as gd
from .. import guildwar as gw
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .guild.common import _can, _char, _now, _push_info, _refuse

S_ALTAR_OPEN, S_GVG_TEAM, S_GVG_CHALLENGE, S_GVG_LIST, S_CROSS_GROUP = 4436, 4441, 4377, 4379, 4682
S_GVG_ORDER = 4458
ALTAR_MIN_LEVEL = 5  # ConsortiaDemonFrame: guilda nível 5
ALTAR_COST = {0: ("Consortia_OpenAltar1_Offer", 50000), 1: ("Consortia_OpenAltar2_Offer", 200000)}


# ---- altar do demônio ------------------------------------------------------------------------


@router.on(8541)
async def altar_open(s: GameSession, msg: pb.ConsortiaAltarOpenReqMsg) -> None:
    """Abre o altar (direito 3, guilda nível 5) pagando com a riqueza; uma vez por dia.

    Avisa os membros online com o 4436 (``result`` = estado novo) e o 164.
    """
    mine = _can(s, gd.R_UPGRADE)
    cost_cfg = ALTAR_COST.get(msg.altarType)
    if mine is None or cost_cfg is None:
        _refuse(s, 8541, "sem direito ou tipo inválido", tipo=msg.altarType)
        return
    guild, now = mine[0], _now(s)
    cost = gd.config(s.ctx.templates, *cost_cfg)
    if guild.levels < ALTAR_MIN_LEVEL or guild.offer < cost or gd.altar_state(guild, now) != gd.ALTAR_CLOSED:
        _refuse(s, 8541, "nível, riqueza ou já aberto hoje", nivel=guild.levels, riqueza=guild.offer)
        return
    guild.offer -= cost
    guild.altar_state, guild.altar_at = gd.ALTAR_OPEN, now
    c = _char(s)
    # texto deduzido (sem fonte no cliente/captura); nome do language.txt consortiaDemonBtnTipData
    event = s.ctx.guilds.add_event(guild.id or 0, now, gd.EV_EVENT, "Divine Altar opened by", c.nickname or "", "")
    await s.ctx.characters.save(guild, event)
    out = pb.ConsortiaAltarOpenRspMsg(
        consortiaId=guild.id,
        chairmanId=s.player_id,
        chairmanName=c.nickname or "",
        result=gd.ALTAR_OPEN,
        altarDate=b.fmt_time(now),
        pop=True,
    )
    for o in gd.online_members(s.ctx, guild.id or 0):
        o.send(S_ALTAR_OPEN, b.complete(out))
    _push_info(s, guild)


# entrada (8542), o mapa 7601 e o que se faz lá dentro (8549, 8550, 8593): ``handlers/altar.py``


# ---- guerra de guildas -----------------------------------------------------------------------


GVG_GUILDS = 8  # (visto) oficial_20261023-171155-1 #5135-#5136: 8 guildas no 4441 e no 4458


@router.on(8546)
async def gvg_groups(s: GameSession, _: object) -> None:
    """Grupos da guerra. (visto) oficial_20261023-171155-1 #5135-#5136 e 20261026-225632-1 #2464/#6451: 4441 com as 8
    guildas de maior ``fightPower``, ``group1`` = posição % 4 + 1 (as duas do mesmo grupo se enfrentam, ``guildwar``)
    e ``result1`` 1 na vencedora da guerra de hoje; depois o 4458 com a ordem da semana passada. TODO(inventado): só a
    1ª rodada (``group2``-``group4`` vão 0), ``isGuildSize`` com 8 guildas no servidor, e a "semana passada" é a
    mesma ordem de agora com ``orderTime`` = agora.
    """
    from .guildwar import result  # guildwar importa guild, que importa este módulo

    g = s.ctx.guilds
    top = sorted(g.guilds.values(), key=lambda x: -g.fight_power(x.id or 0))[:GVG_GUILDS]
    teams = pb.GuildGroupListMsg(isGuildSize=len(g.guilds) >= GVG_GUILDS)
    order = pb.GuildGroupListMsg(orderTime=b.fmt_time(_now(s)))
    ids = [x.id or 0 for x in top]
    for i, x in enumerate(top, 1):
        power = g.fight_power(x.id or 0)
        teams.group.add(consortiaId=x.id or 0, consortiaName=x.name, fightPower=power,
                        group1=gw.group_of(ids, x.id or 0), result1=result(s.ctx, x.id or 0))  # fmt: skip
        order.group.add(consortiaId=x.id or 0, consortiaName=x.name, order=i, fightPower=power)
    s.send(S_GVG_TEAM, b.complete(teams))
    s.send(S_GVG_ORDER, b.complete(order))


@router.on(8472)
async def gvg_challenge(s: GameSession, _: object) -> None:
    s.send(S_GVG_CHALLENGE, b.complete(pb.GuildChallengeOrderListMsg()))


@router.on(8477)
async def gvg_list(s: GameSession, _: object) -> None:
    s.send(S_GVG_LIST, b.complete(pb.GuildChallengeOrderListMsg()))


# ---- guerra entre servidores -----------------------------------------------------------------


@router.on(8782)
async def cross_group(s: GameSession, msg: pb.CrossGuildMsg) -> None:
    """Grupos da guerra entre servidores: 4682 sem ``info`` = guilda não inscrita."""
    s.send(S_CROSS_GROUP, b.complete(pb.CrossGuildMsg()))


@router.on(8779)
async def cross_signup(s: GameSession, _: object) -> None:
    """Inscrição: vira a fila LOCAL do PvP entre servidores (``handlers/cruzado.py``); o 4682 sem ``info`` segue
    para a janela não travar (os grupos de guildas do mapa 4601 não existem num servidor só)."""
    from . import cruzado  # noqa: PLC0415  (cruzado importa campaign, pesado)

    s.send(S_CROSS_GROUP, b.complete(pb.CrossGuildMsg()))
    cruzado.enter(s)


@router.on(8778)
async def cross_team_edit(s: GameSession, msg: pb.CrossGuildMsg) -> None:
    _refuse(s, 8778, "guerra entre servidores não implementada", time=msg.param1)


@router.on(8783)
async def cross_enter(s: GameSession, _: object) -> None:
    _refuse(s, 8783, "guerra entre servidores não implementada (mapa 4601)")
