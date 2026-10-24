"""Terra secreta da guilda (Guild Chamber, mapa 7501): entrada (8537), a sala, a árvore, os Invasores e a saída.

(visto) oficial_20261023-171155-1 #5056-#5172, membro comum de uma guilda nível 8, sem a árvore invocada:

- 8537 -> 125 {createdType 1, campaignId 7501}, 140 (parado) e 21;
- 5035 state 4 (mapa carregado) -> 127 (os nós), 21, 21, 4432 (a árvore), 4632 (Invasores) e 4453 (quem está lá);
- 5038 {7501} -> 20 {soldierTemplated 3001} (``campaign_map.system_army``, do conteúdo);
- 5125 num Invasor (masterType 151) -> 140, 131, 128 em combate e 157 battleType 23 (``campaign._start_battle``);
- a derrota (#5099-#5114) e o 4382 no 5035 state 4 seguinte (#5117); a vitória não tem captura;
- 5025 sai como a pedreira (``campaign.leave_quarry``) e o 8747 seguinte manda 83 "Left Guild Chamber".

Conteúdo no banco (``campaign_contents`` 7501, migração 0073, ``tools/extract_dungeon.py``): os 62 nós, só 3
Invasores à vista (state 1); os outros 6, a árvore, as 21 coletas e os 30 Master Treasure Thief chegam escondidos.

A árvore (regras em ``game/fam.py``, sem captura: tudo **dedução** do cliente e da ajuda): o líder invoca (8565, o
botão só aparece com ``treeState`` 2 ao líder) e todos os membros online recebem o 4432 com ``opreate`` 2 (o cliente
avisa "Tree of Ancients spawned" a quem está fora); por 15 min a árvore fica à vista, quem está na sala ganha EXP a
cada 15 s (pago no relógio, 20008), energiza uma vez (5125 na árvore), compra o buff (8566) e colhe as coletas que
aparecem a cada 3 min (5125 nelas, contribuição). O tesouro do senhor (8743, Master Treasure Thief) depende do
ranking da Class Wars entre servidores (``isCanCall``): sem ela o botão nunca aparece.
"""

from __future__ import annotations

from typing import Any

from ...domain.models import Consortia, ConsortiaMember, Quest
from ...protocol.messages import wartune_pb2 as pb
from .. import fam, outer_city, rules, social, space
from .. import guild as gd
from ..battle import Battle
from ..builders import login as b
from ..builders.army import castle_pawns
from ..builders.player import quest_update
from ..campaign import COLLECT, DONE, FAM_MAP, NORMAL, PANDORA, CampaignMap
from ..router import router
from ..session import GameSession
from .campaign import (
    ARMY_IDLE,
    ENTER,
    S_ALERT,
    S_ARMY_PAWN,
    S_ARMY_POS,
    S_BATTLE_REPORT,
    S_CHAT,
    S_FULL_ARMY,
    S_MAP_SYNC,
    S_NODES,
    S_NPC_MOVE,
    S_QUESTS,
    S_ROOM_CREATED,
    S_ROOM_ENTER,
    _army_brief,
    _exp_text,
    _node_update,
    _push_player,
    _report,
    _room_enter,
    _start_battle,
    map_sync,
)
from .guild.common import _mine, _push_info, _refuse, guild_chat
from .login import army
from .player import hero_after_fight, hp_pack, push_level
from .shop import send_blood

S_TREE, S_LORDS, S_INFO, S_ARMY_MOVED = 4432, 4632, 4453, 4104
INVADER = 151  # masterType do Invasor (o 127 da captura: 9 nós, sonType 2105)
TREE = PANDORA  # masterType 61 do nó "Guild Tree of Ancients" (sonType 2392)
SUMMONED = 2  # FamInfoMsg.opreate: o cliente avisa quem está fora da sala (``__consortiaTreeUpdateHandler``)
NO_DATE = "2000-01-01 00:00:00"  # data vazia do oficial (kickDate, quitDate do 4138)
LORDS_LEFT = 180000  # (visto) 4632 #5065 leftTime: o cliente mostra em segundos (remainMonsterTime)
# (visto) "<link> has defeated an invader and earned 10 guild contribution!" (171155 #5497, 215937 #148, 231733
# #4104) e o 164 seguinte com a riqueza +10 (405703 -> 405713); ``game_settings.fam_invader_offer``, 0073
INVADER_OFFER = 10
UNDER_ATTACK = "The Guild Chamber is under attack! Grab your weapons and drive the invaders away!"
BUSY = "Target is in battle, please wait…"  # (cliente) playermenu.command01; (dedução) o aviso de quem chega depois


def _invasion(s: GameSession, guild: Consortia) -> fam.Invasion:
    inv, new = fam.invasion(s.ctx.guilds.invasions, guild.id or 0, s.ctx.clock.now())
    if new:
        guild_chat(s, guild, UNDER_ATTACK)
        s.log.info("terra secreta: Invasores chegaram", guilda=guild.id)
    return inv


def _start_state(c: CampaignMap, camp: int) -> int:
    """Estado do nó no conteúdo (o que o 127 da entrada traz)."""
    nodes = (c.content or {}).get("maps", {}).get(str(FAM_MAP), {}).get("nodes", [])
    return next((int(n["state"]) for n in nodes if n["campDataId"] == camp), DONE)


def _here(s: GameSession, guild_id: int) -> list[GameSession]:
    """Membros online da guilda que estão na terra secreta."""
    return [o for o in gd.online_members(s.ctx, guild_id) if o.campaign is not None and o.campaign.fam]


def _info(s: GameSession, guild: Consortia, member: ConsortiaMember | None) -> pb.FamInfoMsg:
    # (visto) #5066 personNum 10, rate 1.0 sem a árvore; com ela, o rate é o de ``fam.rate``
    rate = fam.rate(guild, member, s.ctx.world.settings, s.ctx.clock.now())
    return pb.FamInfoMsg(personNum=len(_here(s, guild.id or 0)), rate=rate)


def _tree(s: GameSession, guild: Consortia, member: ConsortiaMember | None, opreate: int = 0) -> pb.FamInfoMsg:
    """4432: (visto) #5064 consortiaId, treeGrades, treeGp, treeWaterCount (energia), treeState, personNum, rate,
    opreate 0 e pickTime (a última invocação)."""
    now = s.ctx.clock.now()
    msg = _info(s, guild, member)
    msg.consortiaId, msg.treeGrades, msg.treeGp = guild.id or 0, guild.tree_grade, guild.tree_gp
    msg.treeWaterCount, msg.treeState, msg.opreate = guild.tree_power, fam.state(guild, now), opreate
    msg.pickTime = b.fmt_time(guild.tree_called_at) if guild.tree_called_at else NO_DATE
    return msg


def _tell_room(s: GameSession, guild: Consortia, *, tree: bool = False) -> None:
    """Quem está na sala vê o novo número e o rate (4453) e, com ``tree``, a árvore (4432). (dedução) o 4453 é o
    que o cliente usa no ``__consortiaSecretUpdateHandler``."""
    for o in _here(s, guild.id or 0):
        mine = _mine(o)
        member = mine[1] if mine else None
        if tree:
            o.send(S_TREE, _tree(o, guild, member))
        o.send(S_INFO, _info(o, guild, member))


def _sync_nodes(s: GameSession, guild: Consortia, *, send: bool = True) -> None:
    """A árvore à vista só invocada; a cada 3 min da invocação uma leva nova de coletas (``fam.collect_batch``)."""
    c = s.campaign
    if c is None or not c.fam:
        return
    now = s.ctx.clock.now()
    batch = fam.collect_batch(guild, now)
    new_batch = batch is not None and batch != s.fam_batch
    s.fam_batch = batch
    inv = _invasion(s, guild)
    for camp, node in c.nodes.items():
        if node["masterType"] == TREE:
            want = NORMAL if batch is not None else DONE
        elif node["masterType"] == COLLECT:
            want = NORMAL if new_batch else DONE if batch is None else node["state"]
        elif node["masterType"] == INVADER and c.fighting != camp:
            want = DONE if camp in inv.dead else _start_state(c, camp)
        else:
            continue
        if want != node["state"]:
            if send:
                _node_update(s, camp, want, fresh=True)
            else:
                node["state"] = want


def _add_offer(s: GameSession, offer: int) -> list[Quest]:
    """Contribuição ganha na sala; a missão 29 lê o total (como a doação, ``guild/upgrades.py``)."""
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    c.consortia_offer += offer
    c.consortia_total_offer += offer
    return rules.quest_event(snap, s.ctx.templates, rules.OFFER_CONDITION, 0, c.consortia_total_offer)


def _contribution(s: GameSession, offer: int, quests: list[Quest]) -> None:
    # TODO(inventado): o texto (o oficial não mostrou ganho de contribuição na terra secreta)
    text = f"Received: {offer} Contribution"
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if quests and s.snapshot is not None:
        s.send(S_QUESTS, quest_update(quests, rules.quest_bitmap(s.snapshot)))


@router.on(8537)
async def enter(s: GameSession, _: object) -> None:
    """Entrar: só membro de guilda, fora de luta e de outro mapa. (visto) #5057-#5059: 125, 140, 21."""
    content = s.ctx.world.campaigns.get(FAM_MAP)
    if _mine(s) is None or content is None or s.battle is not None or s.campaign is not None:
        _refuse(s, 8537, "sem guilda, sem conteúdo ou já num mapa", conteudo=content is not None)
        return
    space.leave(s)
    s.campaign = CampaignMap.enter_dungeon(content, FAM_MAP)
    s.fam_paid_at, s.fam_batch = s.ctx.clock.now(), None  # EXP só a partir da entrada
    room = pb.RoomCreatedMsg(createdType=ENTER)
    room.room.campaignId = FAM_MAP
    s.send(S_ROOM_CREATED, room)
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    s.send(S_ROOM_ENTER, _room_enter(s))
    s.log.info("entrou na terra secreta")


def show_room(s: GameSession) -> None:
    """1º 5035 state 4: (visto) #5061-#5066 127, 21, 21, 4432, 4632, 4453. Os nós já vêm com a árvore e as coletas."""
    c, mine = s.campaign, _mine(s)
    assert c is not None
    c.ready = True
    if mine is None:
        return
    guild, member = mine
    _sync_nodes(s, guild, send=False)
    s.send(S_NODES, c.node_list())
    s.send(S_ROOM_ENTER, _room_enter(s))
    s.send(S_ROOM_ENTER, _room_enter(s))
    s.send(S_TREE, _tree(s, guild, member))
    # (visto) #5065: sem chamar o tesouro do senhor (isCanCall, só com o ranking da Class Wars) e 1ª leva
    s.send(S_LORDS, pb.FamLordsInfoMsg(isCanCall=False, isOpenLordsNode=False, currentTurns=1, leftTime=LORDS_LEFT))
    s.send(S_INFO, _info(s, guild, member))
    for o in _here(s, guild.id or 0):
        if o is not s:
            o.send(S_INFO, _info(o, guild, _mine(o)[1] if _mine(o) else None))  # type: ignore[index]


async def push_state(s: GameSession) -> None:
    """No relógio (20008): a onda de Invasores da guilda (o aviso sai a todos, dentro ou fora da sala) e, dentro da
    sala, os tiques de EXP vencidos, a árvore, as coletas e os Invasores."""
    c, mine, snap = s.campaign, _mine(s), s.snapshot
    if mine is not None:
        _invasion(s, mine[0])
    if c is None or not c.fam or not c.ready or mine is None or snap is None:
        return
    guild, member = mine
    now = s.ctx.clock.now()
    before_batch = s.fam_batch
    _sync_nodes(s, guild)
    if s.fam_batch is None and before_batch is not None:
        s.send(S_TREE, _tree(s, guild, member))  # (dedução) a árvore acabou: treeState 3, o botão do buff some
        s.send(S_INFO, _info(s, guild, member))
    n, s.fam_paid_at = fam.ticks(guild, s.fam_paid_at, now)
    if n <= 0:
        return
    rate = fam.rate(guild, member, s.ctx.world.settings, guild.tree_called_at or now)
    gp = n * fam.tick_exp(snap.character.grades, guild, rate, s.ctx.world.settings)
    if gp <= 0:
        return
    grade = snap.character.grades
    rules.add_gp(snap, s.ctx.templates, gp)
    await s.ctx.characters.save(snap.character, *([snap.leader] if snap.leader else []))
    await _push_player(s)
    s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=_exp_text(gp)))  # (dedução) o texto da EXP das lutas
    if snap.character.grades > grade:
        await push_level(s, grade)
    s.log.info("terra secreta: EXP da árvore", tiques=n, exp=gp, rate=rate)


@router.on(8565)
async def summon(s: GameSession, _: object) -> None:
    """Invocar a árvore: só o líder (o botão do ``ConsortiaSecretInfoView`` é do ``isChairman``), uma vez por dia."""
    mine, now = _mine(s), s.ctx.clock.now()
    if mine is None or mine[0].chairman_id != s.player_id or fam.state(mine[0], now) != fam.CALLABLE:
        _refuse(s, 8565, "não é o líder ou a árvore já foi invocada hoje", estado=mine and fam.state(mine[0], now))
        return
    guild = mine[0]
    fam.summon(guild, s.ctx.templates, now)
    await s.ctx.characters.save(guild)
    for o in gd.online_members(s.ctx, guild.id or 0):
        om = _mine(o)
        o.send(S_TREE, _tree(o, guild, om[1] if om else None, SUMMONED))
        if o.campaign is not None and o.campaign.fam:
            o.fam_paid_at = now
            _sync_nodes(o, guild)
            o.send(S_INFO, _info(o, guild, om[1] if om else None))
    s.log.info("terra secreta: árvore invocada", nivel=guild.tree_grade, exp=guild.tree_gp)


@router.on(8566)
async def buff(s: GameSession, _: object) -> None:
    """Buff de +20% de EXP (``Fam_Buffer_Price`` de contribuição) enquanto a árvore está invocada, uma vez por
    invocação; (dedução) a resposta é o 3 (contribuição nova) e o 4453 com o rate novo."""
    mine, snap, now = _mine(s), s.snapshot, s.ctx.clock.now()
    price = gd.config(s.ctx.templates, "Fam_Buffer_Price", 200)
    in_room = s.campaign is not None and s.campaign.fam
    if mine is None or snap is None or not in_room or fam.state(mine[0], now) != fam.CALLED:
        _refuse(s, 8566, "fora da sala ou sem a árvore")
        return
    guild, member = mine
    if fam.bought(guild, member) or snap.character.consortia_offer < price:
        _refuse(s, 8566, "já comprado ou sem contribuição", contribuicao=snap.character.consortia_offer)
        return
    snap.character.consortia_offer -= price
    member.fam_buff_at = guild.tree_called_at
    await s.ctx.characters.save(snap.character, member)
    await _push_player(s)
    s.send(S_INFO, _info(s, guild, member))


@router.on(8743)
async def lords(s: GameSession, _: object) -> None:
    """Chamar o Master Treasure Thief: só quem ficou entre os primeiros da Class Wars (entre servidores) pode
    (``isCanCall``, ajuda da Class Wars, item 7). O 4632 manda sempre ``isCanCall`` falso, então o cliente não mostra o
    botão; um 8743 mesmo assim é recusado."""
    _refuse(s, 8743, "sem Class Wars: ninguém pode chamar o tesouro do senhor")


async def arrive(s: GameSession, camp: int, node: dict[str, Any]) -> None:
    """5125: o Invasor luta (o 750109 da captura; os outros pelo ``sonType``, ``battle_like``); a árvore energiza;
    a coleta dá contribuição."""
    c, mine = s.campaign, _mine(s)
    assert c is not None
    if node["masterType"] == TREE and mine is not None:
        await _energize(s, camp, *mine)
        return
    if node["masterType"] == COLLECT and node["state"] == NORMAL and mine is not None:
        await _collect(s, camp, mine[0])
        return
    if node["masterType"] != INVADER or c.battle_like(camp) is None or s.battle is not None or mine is None:
        s.log.info("terra secreta: 5125 sem luta", nó=camp, tipo=node["masterType"])
        return
    inv = _invasion(s, mine[0])
    holder = inv.fighting.get(camp, s.player_id)
    other = s.ctx.online.get(holder)
    if camp in inv.dead or (holder != s.player_id and other is not None and other.battle is not None):
        s.send(S_ALERT, b.complete(pb.ChatChannelMsg(channel=7, encodeMsg=BUSY)))
        _node_update(s, camp, DONE if camp in inv.dead else node["state"])
        s.log.info("terra secreta: Invasor ocupado ou vencido", nó=camp, lutando=holder)
        return
    inv.fighting[camp] = s.player_id

    async def over(battle: Battle, won: bool) -> None:
        await _over(s, battle, camp, won)

    _start_battle(s, camp, over)


async def _energize(s: GameSession, camp: int, guild: Consortia, member: ConsortiaMember) -> None:
    """Uma energia por membro e invocação, até ``fam.max_power``; (dedução) a sala vê o 4432 e o 4453 novos."""
    now = s.ctx.clock.now()
    if fam.state(guild, now) != fam.CALLED or fam.energized(guild, member):
        s.log.info("terra secreta: energia recusada", estado=fam.state(guild, now))
        return
    if guild.tree_power >= fam.max_power(guild, s.ctx.templates):
        s.log.info("terra secreta: energia cheia", energia=guild.tree_power)
        return
    guild.tree_power += 1
    member.fam_power_at = guild.tree_called_at
    await s.ctx.characters.save(guild, member)
    _tell_room(s, guild, tree=True)
    s.log.info("terra secreta: energizou", nó=camp, energia=guild.tree_power)


async def _collect(s: GameSession, camp: int, guild: Consortia) -> None:
    """Coleta da leva em curso: some (128 state 8) e dá ``fam_tree.collect_offer`` de contribuição."""
    snap = s.snapshot
    assert snap is not None
    if fam.collect_batch(guild, s.ctx.clock.now()) is None:
        return
    offer = fam.collect_offer(s.ctx.world.settings)
    quests = _add_offer(s, offer)
    await s.ctx.characters.save(snap.character, *quests)
    _node_update(s, camp, DONE, fresh=True)
    await _push_player(s)
    _contribution(s, offer, quests)


async def _over(s: GameSession, battle: Battle, camp: int, won: bool) -> None:
    """(visto) derrota #5099-#5114: 113, 3 e 83 da poção, 150, 4103 (battleScene 3, sem EXP nem Daru), 3, 150, 100,
    4122 (o Invasor volta ao lugar), 140, 4104 e 131 (o exército volta à entrada), 128 state 1 com uuId e o 83 da
    poção de novo; o 4382 (tudo 0) no 5035 state 4 seguinte. A tropa morre e se repõe como nas outras lutas.

    A vitória: (visto, de quem estava fora da sala) o 83 do canal 5 "<link> has defeated an invader and earned 10
    guild contribution!" a toda a guilda e o 164 com a riqueza +10; o Invasor some para todos na sala (o usuário).
    TODO(inventado) o que o vencedor vê: a mesma ordem, o Invasor some (128 state 8, como na ilha dos pets), o
    exército fica onde está e a contribuição vem com 111 e 83 "Received: N Contribution".
    """
    snap, c = s.snapshot, s.campaign
    assert snap is not None and snap.leader is not None
    mine = _mine(s)
    inv = _invasion(s, mine[0]) if mine is not None else None
    if inv is not None and inv.fighting.get(camp) == s.player_id:
        del inv.fighting[camp]
    s.battle, s.hero_sp = None, battle.player_sp
    rows: list[object] = [snap.leader]
    if (hit := outer_city.lose_troops(snap, s.ctx.templates, battle.troops())) is not None:
        outer_city.refill(*hit)
        rows += snap.pawns
    healed = hero_after_fight(s, battle.player.hp if battle.player is not None else None)
    offer = int(s.ctx.world.settings.get("fam_invader_offer", INVADER_OFFER)) if won else 0
    quests = _add_offer(s, offer) if offer else []
    if offer:
        rows += [snap.character, *quests]
    if won and mine is not None and inv is not None:
        inv.dead.add(camp)
        mine[0].offer += offer
        mine[0].total_offer += offer
        rows.append(mine[0])
    await s.ctx.characters.save(*rows)
    if won and mine is not None and inv is not None:
        link = social.player_link(s.ctx, snap.character)
        guild_chat(s, mine[0], f"{link} has defeated an invader and earned {offer} guild contribution!")
        _push_info(s, mine[0])
        for o in _here(s, mine[0].id or 0):
            if o is not s and o.campaign is not None and o.campaign.node(camp) is not None:
                _node_update(o, camp, DONE, fresh=True)
    if healed:
        send_blood(s)
        await _push_player(s)
        hp_pack(s, healed)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]), cards=False)  # como na cidade externa: o do 154 sem o 4902
    s.send(S_BATTLE_REPORT, _report(battle, won, 0))
    await _push_player(s)
    s.send(S_FULL_ARMY, b.complete(army(s, snap)[0]))
    s.send(S_ARMY_PAWN, castle_pawns(snap, s.ctx.templates))
    if c is None or not c.fam:
        return  # saiu no meio da luta
    node = c.node(camp)
    assert node is not None
    c.fighting, c.over = 0, (0, 0)
    if not won:
        s.send(S_NPC_MOVE, pb.NPCMoveMsg(id=node["nodeId"], curPosX=node["posX"], curPosY=node["posY"]))
    s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
    if not won and c.content is not None:
        x, y = c.content["maps"][str(FAM_MAP)]["start"]
        c.pos = (int(x), int(y))
        s.send(S_ARMY_MOVED, pb.ArmyPosUpdatedMsg(armyId=s.player_id, curPosX=c.pos[0], curPosY=c.pos[1]))
    s.send(S_ARMY_POS, _army_brief(s, ARMY_IDLE))
    _node_update(s, camp, DONE if won else NORMAL, fresh=True)
    if offer:
        _contribution(s, offer, quests)
    hp_pack(s, healed)
    s.log.info("terra secreta: luta", nó=camp, venceu=won, contribuição=offer)


def leaving(s: GameSession) -> None:
    """5025 (antes de ``leave_quarry`` limpar o mapa): o 83 sai no 8747 e os outros veem um a menos."""
    s.fam_left = True
    if (mine := _mine(s)) is not None:
        s.campaign = None
        _tell_room(s, mine[0])
