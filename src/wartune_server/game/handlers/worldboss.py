"""Chefe do mundo: agenda (8271 -> 4182), entrada (8258), reviver pago (8264), buff (8470) e info (8259).

Regras e fontes em ``docs/boss-eventos.md``. O mapa do chefe (5001/5003) tem um nó só, montado da config no
banco (``world_bosses``); a vida compartilhada está em ``game/boss_fight.py``.
"""

from __future__ import annotations

from typing import Any

from ...domain.world import WorldBoss
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates
from .. import boss_fight, space, worldboss
from ..campaign import NORMAL, CampaignMap
from ..router import router
from ..session import GameSession
from .player import alert

S_BOSS_STATE, S_BOSS_INFO, S_MILESTONES = 4182, 4174, 4369
S_ROOM_ENTER, S_EXIT, S_ROOM_CREATED, S_NODES, S_FOG = 21, 22, 125, 127, 130
ROOM_ENTER = 1  # RoomCreatedMsg.createdType
BOSS_NODE, BOSS_MASTER = 1, 41  # nodeId do único nó; masterType do chefe (como o 102109 da masmorra)
TILE = 20
NO_MAP = "This World Boss has no battle map yet."
NOT_OPEN = "World Boss is not open now."
UNAVAILABLE = "This action is not available now."  # reviver e buff: o cliente só pede dentro do mapa do chefe


@router.on(8535)
async def cancel_transport(s: GameSession, _: object) -> None:
    """Cancela o transporte do jogador morto no mapa de PvP do chefe (ExtraBufferItem, tipo 5). Esse estado de
    morte vem do mapa da batalha compartilhada, que não existe aqui: nada para cancelar, e o cliente não espera
    resposta. Só registramos."""
    s.log.info("8535 sem transporte de morte: não há mapa de PvP do chefe")


@router.on(8271)
async def boss_state(s: GameSession, _: object) -> None:
    """Agenda de hoje dos dois chefes. O cliente pede isso uma vez, no login (``WorldBossManager.setup``)."""
    s.boss_states = worldboss.states(s.ctx.templates, s.ctx.clock.now())
    s.send(S_BOSS_STATE, worldboss.states_msg(s.ctx.templates, s.ctx.clock.now()))


def push_states(s: GameSession) -> None:
    """No relógio (20008): manda o 4182 de novo quando um chefe abre ou fecha. O 8258 só passa no cliente com
    ``worldbossState`` ligado, e só o 4182 com ``state`` 0 liga (``WorldBossManager``)."""
    if s.boss_states is None:
        return  # o cliente ainda não pediu (8271)
    now = s.ctx.clock.now()
    if (states := worldboss.states(s.ctx.templates, now)) != s.boss_states:
        s.boss_states = states
        s.send(S_BOSS_STATE, worldboss.states_msg(s.ctx.templates, now))


@router.on(8259)
async def boss_info(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Info por mapa: ``reqWorldBossCmd`` não tem chamador no cliente, então não há o que responder."""
    s.log.info("pedido de info do chefe ignorado", pedido=str(msg))


@router.on(8258)
async def enter_boss(s: GameSession, msg: pb.WorldBossMsg) -> None:
    """Entrar no chefe (``param1`` = campanha): 125, 4369, 21, 127, 130 e 4174.

    (cliente) o 4369 tem de chegar antes da view do mapa, senão o quadro dos degraus não aparece; o mapa é a
    própria campanha (``MapInfos`` 5001/5003, 1600x1700) e ``checkFogMap`` ignora a névoa nele, mas o 130 abre a
    view. Os outros jogadores do mapa recebem o 21 de quem entrou (``CampaignManager.readMember`` soma um a um).
    """
    if (why := _refusal(s, msg.param1)) is not None:
        alert(s, why)
        return
    ctx = s.ctx
    pool = await ctx.bosses.pool(ctx.world, ctx.templates, ctx.characters, msg.param1, ctx.clock.now())
    if pool is None:
        alert(s, NO_MAP if msg.param1 not in ctx.world.world_bosses else NOT_OPEN)
        return
    if s.battle is not None or s.campaign is not None:
        return  # entrou em outro lugar durante o await
    snap = s.snapshot
    assert snap is not None
    boss = pool.boss
    node = boss_node(ctx.templates, boss)
    s.campaign = CampaignMap(boss.campaign_id, {node["campDataId"]: node}, (boss.start_x, boss.start_y),
                             world_boss=True)  # fmt: skip
    space.leave(s)
    room = pb.RoomCreatedMsg(createdType=ROOM_ENTER)
    room.room.campaignId = boss.campaign_id
    s.send(S_ROOM_CREATED, room)
    s.send(S_MILESTONES, boss_fight.milestones(ctx.world, pool, s.player_id))
    me = space.room_player(snap, ctx.templates, s.campaign.pos, boss.campaign_id)
    others = on_map(s, boss.campaign_id)
    players = [space.room_player(o.snapshot, ctx.templates, o.campaign.pos, boss.campaign_id)  # type: ignore[arg-type,union-attr]
               for o in others]  # fmt: skip
    s.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me, *players]))
    for other in others:
        other.send(S_ROOM_ENTER, pb.RoomEnterMsg(result=1, player=[me]))
    s.send(S_NODES, s.campaign.node_list())
    s.send(S_FOG, s.campaign.fog())
    s.send(S_BOSS_INFO, pool.info(ctx.templates, s.player_id, ctx.clock.now()))


def boss_node(templates: GameTemplates, boss: WorldBoss) -> dict[str, Any]:
    """O nó do chefe no 127, no molde do chefe da masmorra (102109, ``dungeon_1001.json``): masterType 41,
    ``heroTempId`` do ``GameHeroTemp`` (o cliente monta o herói por ele) e o avatar em ``swf/npc/<sonType>``."""
    hero = templates.get("GameHeroTemp", boss.hero_id) or {}
    x, y = boss.node_x, boss.node_y
    return {
        "nodeId": BOSS_NODE, "campDataId": boss.campaign_id * 100 + 1, "nodeName": hero.get("TemplateName", ""),
        "masterType": BOSS_MASTER, "sonType": boss.son_type, "preNodeIds": "0", "nextNodeIds": "", "state": NORMAL,
        "refreshSpeed": 1, "posX": x, "posY": y, "curX": x, "curY": y, "level": int(hero.get("Grades") or 0),
        "styleType": 1, "attackTypes": 0, "nameColor": 5, "sizeType": 1, "toward": 180, "resource": 1,
        "resetX": 0, "resetY": 0, "fixX": x * TILE, "fixY": y * TILE, "heroTempId": boss.hero_id,
        "handlerRange": 0, "fightCapaity": 0, "param1": 0, "param2": 0, "param3": "", "param4": "", "param5": "",
    }  # fmt: skip


def on_map(s: GameSession, campaign_id: int) -> list[GameSession]:
    """Os outros jogadores no mapa do chefe ``campaign_id``."""
    return [o for o in s.ctx.online.sessions()
            if o is not s and o.campaign is not None and o.campaign.world_boss and o.campaign.map_id == campaign_id
            and o.snapshot is not None]  # fmt: skip


def leave_boss(s: GameSession) -> bool:
    """Sai do mapa do chefe (5025 ou desconexão): 22 para todos no mapa, o próprio também (o cliente volta com
    ``exitBack``; os outros tiram o exército, ``CampaignSocketManger.__campaignExitHandler``)."""
    c, snap = s.campaign, s.snapshot
    if c is None or not c.world_boss or snap is None:
        return False
    if s.battle is not None:
        s.battle.cancel()
        s.battle = None
    msg = pb.CampaignExitMsg(result=1, playerId=s.player_id, armyId=s.player_id, serverName=snap.server.name)
    for other in on_map(s, c.map_id):
        other.send(S_EXIT, msg)
    s.campaign = None
    s.send(S_EXIT, msg)
    return True


def _refusal(s: GameSession, campaign_id: int) -> str | None:
    row = worldboss.boss(s.ctx.templates, campaign_id)
    if row is None:
        if next(s.ctx.templates.find("Campaigns", CampaignId=campaign_id), None) is not None:
            return UNAVAILABLE  # (cliente) TaskFrameII.as:707-708: o botão ir manda 8258 com a campanha 6001 (Types 2)
        return "Invalid World Boss."
    snap = s.snapshot
    assert snap is not None
    if worldboss.state(row, s.ctx.clock.now()) != worldboss.OPEN:
        return NOT_OPEN
    if snap.character.grades < int(row["MinLevel"]):
        return f"World Boss requires level {row['MinLevel']}."
    if s.battle is not None or s.campaign is not None:
        return "Finish your current battle or map first."
    return None


@router.on(8264)
async def revive_or_fight(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Entrar na luta agora, pagando (``Live_Fight_Pay`` 3; payType 0 = vinculado primeiro, 1 = só
    diamante). O botão existe na ``RiverView`` tipo 1, depois de morrer no chefe, e o servidor ainda
    não sabe disso: nada é cobrado. ``Live_Pay`` (2) não tem botão no chefe.

    ponytail: o mesmo 8264 é o reviver do altar de guilda (``RiverView`` tipo 2, paga em contribuição);
    quem fizer o mapa do altar tem de separar pelo mapa do jogador.
    """
    s.log.info("reviver pago recusado (sem morte no chefe)", pedido=str(msg))
    alert(s, UNAVAILABLE)


@router.on(8470)
async def buy_buff(s: GameSession, msg: pb.WorldBossBufferMsg) -> None:
    """Buff do chefe (``CampaignBufferTemps`` ``Types=4``, ``WorldBossBuyBuffModel.BUFFER_TYPE``): só se compra
    dentro do mapa do chefe. Nada é cobrado."""
    s.log.info("buff do chefe recusado (sem mapa do chefe)", pedido=str(msg))
    alert(s, UNAVAILABLE)
