"""Atividades da guilda: altar do demônio (chefe de guilda), terra secreta, guerra de guildas e
guerra entre servidores.

Todas acontecem em mapas próprios (7601 altar, 7501 terra secreta, 4501 guerra, 4601 entre
servidores) que o cliente abre com o 125 ``RoomCreatedMsg``. O servidor só tem o mapa do
tutorial (``game/campaign.py``), então as entradas ficam recusadas e os pacotes de dentro do mapa
só registram no log. O que tem estado fora do mapa (abrir o altar, listas vazias) está aqui.
Dependências em docs/guilda.md.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from .. import guild as gd
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .guild import _can, _char, _mine, _now, _push_info, _refuse

S_ALTAR_OPEN, S_GVG_TEAM, S_GVG_CHALLENGE, S_GVG_LIST, S_CROSS_GROUP = 4436, 4441, 4377, 4379, 4682
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
    event = s.ctx.guilds.add_event(guild.id or 0, now, f"{c.nickname} şeytan sunağını açtı.")
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
        o.send(S_ALTAR_OPEN, out)
    _push_info(s, guild)


@router.on(8542)
async def altar_enter(s: GameSession, _: object) -> None:
    """Entrar no altar: o cliente espera o 125 do mapa 7601.

    ponytail: falta o sistema de mapas de campanha (só existe o do tutorial) e as ondas de
    monstros; a luta usaria o fluxo PvE de ``game/battle.py``.
    """
    mine = _mine(s)
    state = gd.altar_state(mine[0], _now(s)) if mine else gd.ALTAR_CLOSED
    _refuse(s, 8542, "mapa do altar (7601) não implementado", estado=state)


@router.on(8549)
async def altar_arrive(s: GameSession, msg: pb.ArriveAltarReqMsg) -> None:
    _refuse(s, 8549, "fora do mapa do altar", no=msg.nodeId)


@router.on(8550)
async def altar_buff(s: GameSession, _: object) -> None:
    _refuse(s, 8550, "fora do mapa do altar")


@router.on(8593)
async def altar_skill(s: GameSession, msg: pb.ConsortiaAltarOpenReqMsg) -> None:
    _refuse(s, 8593, "fora do mapa do altar", tipo=msg.altarType)


# ---- terra secreta (fam) ---------------------------------------------------------------------


@router.on(8537)
async def fam_enter(s: GameSession, _: object) -> None:
    """Entrar na terra secreta: o cliente espera o 125 do mapa 7501 (sem mapa: nada acontece)."""
    _refuse(s, 8537, "mapa da terra secreta (7501) não implementado")


@router.on(8565, 8566, 8743)
async def fam_action(s: GameSession, _: object) -> None:
    """Chamar a árvore, buff e nó do senhor: só existem dentro do mapa 7501."""
    _refuse(s, 8565, "8565/8566/8743 fora do mapa da terra secreta")


# ---- guerra de guildas -----------------------------------------------------------------------


@router.on(8546)
async def gvg_groups(s: GameSession, _: object) -> None:
    """Grupos da guerra: vazio abre a janela com a entrada desligada (a guerra nunca abre:
    login manda ``GuildMsg.param5`` falso)."""
    s.send(S_GVG_TEAM, b.complete(pb.GuildGroupListMsg()))


@router.on(8472)
async def gvg_challenge(s: GameSession, _: object) -> None:
    s.send(S_GVG_CHALLENGE, pb.GuildChallengeOrderListMsg())


@router.on(8477)
async def gvg_list(s: GameSession, _: object) -> None:
    s.send(S_GVG_LIST, pb.GuildChallengeOrderListMsg())


@router.on(8471)
async def gvg_enter(s: GameSession, _: object) -> None:
    """Entrar na guerra: o cliente espera o 125 do mapa 4501."""
    _refuse(s, 8471, "guerra de guildas não implementada")


@router.on(8473)
async def gvg_team_edit(s: GameSession, msg: pb.TeamEditMsg) -> None:
    _refuse(s, 8473, "guerra de guildas não implementada", alvo=msg.userId, op=msg.op)


@router.on(8547)
async def gvg_buff(s: GameSession, msg: pb.GuildMsg) -> None:
    _refuse(s, 8547, "fora do mapa da guerra", buff=msg.param1)


# ---- guerra entre servidores -----------------------------------------------------------------


@router.on(8782)
async def cross_group(s: GameSession, msg: pb.CrossGuildMsg) -> None:
    """Grupos da guerra entre servidores: 4682 sem ``info`` = guilda não inscrita."""
    s.send(S_CROSS_GROUP, pb.CrossGuildMsg())


@router.on(8779)
async def cross_signup(s: GameSession, _: object) -> None:
    """Inscrição: precisa de outros servidores; responde "não inscrita" para a janela não travar."""
    _refuse(s, 8779, "guerra entre servidores não implementada")
    s.send(S_CROSS_GROUP, pb.CrossGuildMsg())


@router.on(8778)
async def cross_team_edit(s: GameSession, msg: pb.CrossGuildMsg) -> None:
    _refuse(s, 8778, "guerra entre servidores não implementada", time=msg.param1)


@router.on(8783)
async def cross_enter(s: GameSession, _: object) -> None:
    _refuse(s, 8783, "guerra entre servidores não implementada (mapa 4601)")
