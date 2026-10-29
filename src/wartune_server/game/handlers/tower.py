"""Forgotten Catacombs e Tormented Necropolis (8296/8297/8299/8300, 4205/4373) e guarda de batalha (8742).

Andares e estado em ``game/maze.py``; a luta, o portal e a varredura passam pela masmorra (``handlers/campaign.py``,
``handlers/dungeon.py``). Fontes em docs/salas-campanha.md. As gemas da guarda não são modeladas.
"""

from __future__ import annotations

from typing import Any

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import maze as mz
from .. import rewards, rules, titles
from ..builders import login as b
from ..campaign import DONE, CampaignMap
from ..router import router
from ..session import GameSession

S_TOWER_INFO, S_TOWER_LIST, S_BATTLEGUARD, S_ITEMS = 4205, 4373, 4631, 115
CONTINUE, START = 0, 1  # EnterTowerInfoMsg.chooseIndex (MazeFrame: Continue / Start)
DOUBLE = 2  # isDouble: lucro dobrado, gasta uma Crypt Key
S_TOWER_DIED = 4207  # TowerDiedMsg "Respawn Note": o msg é o custo do reviver (``MazeRiverView.cost``, 0 = grátis)
S_ALERT, S_DIE_STATE = 111, 4175
S_TOWER_REPORT = 4419  # TowerInfoMsg só com itemTempIds: a saída morta, os itens da corrida (visto 10/28 #1840)
RESPAWN_TITLE = "Respawn Note"
MAZE_LEED = 23  # LeedTemp 23 "Enter Forgotten Catacombs"


def _cfg(s: GameSession, kind: mz.Kind = mz.CATACOMBS) -> dict[str, Any]:
    return mz.settings(s.ctx.world.settings, kind)


def _kind(s: GameSession) -> mz.Kind:
    """A torre do andar onde o jogador está."""
    return (mz.kind_of(s.campaign.map_id) if s.campaign is not None else None) or mz.CATACOMBS


def _info(s: GameSession, tower: mz.Tower, kind: mz.Kind) -> pb.TowerInfoMsg:
    return mz.info(tower, _cfg(s, kind), kind, s.maze_order.get(kind.key, 0))


def tower_msg(s: GameSession, index: int = 0) -> pb.TowerInfoMsg:
    snap = s.snapshot
    assert snap is not None
    kind = mz.KINDS[index] if 0 <= index < len(mz.KINDS) else mz.CATACOMBS
    return _info(s, mz.load(snap, s.ctx.clock.now(), kind), kind)


def record(s: GameSession) -> int:
    """maxIndex do personagem (missão 38, título PASS_TOWER, loja do labirinto)."""
    return mz.record(s.snapshot) if s.snapshot is not None else 0


def login_list(s: GameSession) -> pb.TowerListMsg:
    """4373 do login: (visto) tutorial_en e 215937 vazio sem registro; (só turco: login #55) com a torre."""
    snap = s.snapshot
    assert snap is not None
    out = pb.TowerListMsg()
    for kind in mz.KINDS:
        tower = mz.load(snap, s.ctx.clock.now(), kind)
        if tower.record or tower.index:
            out.towerInfo.append(_info(s, tower, kind))
    return out


@router.on(8297)
async def tower_info(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Info de uma aba (4205). O ``order`` é recalculado aqui (o cliente pede ao abrir o MazeFrame, 10/28 #984).
    shortcut: o 4373 do login vai com order 0 até a primeira abertura."""
    snap = s.snapshot
    assert snap is not None
    kind = mz.KINDS[msg.index] if 0 <= msg.index < len(mz.KINDS) else mz.CATACOMBS
    states = await s.ctx.characters.read(lambda uow: uow.events.by_prefix(snap.character.server_id, kind.key))
    s.maze_order[kind.key] = mz.position(states, s.player_id, kind)
    s.send(S_TOWER_INFO, tower_msg(s, msg.index))


@router.on(8299)
async def tower_reset(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Reset (``MazeFrame``: "Are you sure you want to forfeit all progress and start over?"; sem custo no cliente):
    a corrida volta ao andar 0, o recorde fica. A tela se refaz com o 4205."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    kind = mz.KINDS[msg.index] if 0 <= msg.index < len(mz.KINDS) else mz.CATACOMBS
    tower = mz.load(snap, now, kind)
    if s.campaign is None:
        tower.index, tower.gp, tower.items, tower.double = 0, 0, [], False
        await s.ctx.characters.save(mz.store(snap, tower, now, kind))
    s.send(S_TOWER_INFO, _info(s, tower, kind))


@router.on(8296)
async def tower_enter(s: GameSession, msg: pb.EnterTowerInfoMsg) -> None:
    """Entrar (``MazeFrame``): ``chooseIndex`` 1 Start (gasta uma entrada do dia, do andar 1; "No attempts left!"
    sem entrada), 0 Continue (o andar da corrida). ``isDouble`` 2 gasta uma Crypt Key (sem ela o cliente abre a
    compra). (só turco: yeralti #26-#39) 4205, 4165, 150, 150, 125, 140, 21, 3, 4902/150, 4903, 127, 4205 e o 83 da
    poção de vida. A Necropolis (8101) só abre com o recorde 100 das Catacombs."""
    snap = s.snapshot
    assert snap is not None
    kind = mz.kind_of(msg.campaignId)
    if kind is None or msg.campaignId != kind.campaign or s.campaign is not None or s.battle is not None:
        s.log.info("8296 recusado", campanha=msg.campaignId)
        return
    now, cfg = s.ctx.clock.now(), _cfg(s, kind)
    if not mz.is_open(snap, cfg):
        s.log.info("8296 torre fechada", campanha=msg.campaignId)
        return
    tower = mz.load(snap, now, kind)
    key: tuple[Item, bool] | None = None
    if msg.chooseIndex == START:
        if tower.enters >= int(cfg["max_enter"]):
            s.log.info("8296 sem entrada do dia", feitas=tower.enters)
            return
        if msg.isDouble == DOUBLE and (key := rewards.take_one(snap, int(cfg["key"]))) is None:
            s.log.info("8296 dobrado sem Crypt Key")
            return
        tower.enters += 1
        tower.index, tower.gp, tower.items, tower.double, tower.dead = 1, 0, [], msg.isDouble == DOUBLE, False
    elif tower.index <= 0:
        s.log.info("8296 continuar sem corrida")
        return
    if key is not None:
        item, gone = key
        await s.ctx.characters.save(*([] if gone else [item]), delete=(item,) if gone else ())
        s.send(S_ITEMS, rewards.taken_msg(item, gone, s.player_id))
    await s.ctx.characters.save(mz.store(snap, tower, now, kind))
    await _enter(s, tower, kind)
    if msg.chooseIndex == START and kind == mz.CATACOMBS:
        from . import events as hev  # events importa este módulo

        await hev.leed_done(s, MAZE_LEED)


async def _enter(s: GameSession, tower: mz.Tower, kind: mz.Kind) -> None:
    from . import campaign as ch  # campaign importa login, que importa este módulo
    from . import systems
    from .login import army
    from .player import hp_pack

    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    floor_map = mz.map_of(tower.index, kind)
    full = mz.content(templates, _cfg(s, kind), kind)
    s.send(S_TOWER_INFO, _info(s, tower, kind))
    ch._send(s, ch.S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    s.send(ch.S_FULL_ARMY, b.complete(army(s, snap)[0]), cards=False)
    s.send(ch.S_FULL_ARMY, b.complete(army(s, snap)[0]), cards=False)
    s.campaign = c = CampaignMap.enter_dungeon(full, floor_map)
    c.content = full
    created = pb.RoomCreatedMsg(createdType=ch.ENTER)
    created.room.campaignId = floor_map
    ch._send(s, ch.S_ROOM_CREATED, created)
    ch._send(s, ch.S_MAP_SYNC, ch.map_sync(s, ch.ARMY_IDLE))
    ch._send(s, ch.S_ROOM_ENTER, ch._room_enter(s))
    await ch._push_player(s)
    s.send(ch.S_FULL_ARMY, b.complete(army(s, snap)[0]))
    systems.send_camp_buffs(s, systems.camp_type(ch._campaign_row(s, kind.campaign)))
    ch._send(s, ch.S_NODES, c.node_list())
    s.send(S_TOWER_INFO, _info(s, tower, kind))
    healed = rules.heal_hero(snap, templates, s.ctx.clock.now()) if snap.leader is not None else 0
    hp_pack(s, healed)  # (só turco: yeralti #39) "HP Paketi kullanılarak HP arttırıldı."
    if snap.leader is not None:
        await s.ctx.characters.save(snap.leader)


def died(s: GameSession) -> Any:
    """Herói caído no labirinto, depois do 140 da derrota: 4207 "Respawn Note" com o custo do reviver (0 = grátis).
    (visto) 10/25 #10593 msg 0 e #11400 msg 25; 10/24 #13946 e 10/26 #13436 msg 0. A 1ª morte do dia é grátis e as
    seguintes custam 25 (jogador 28/10: 0, 25, 25; sair não zera). Devolve a linha a gravar."""
    snap = s.snapshot
    assert snap is not None
    kind = _kind(s)
    now, cfg = s.ctx.clock.now(), _cfg(s, kind)
    tower = mz.load(snap, now, kind)
    tower.deaths += 1
    tower.dead = True
    cost = 0 if tower.deaths == 1 else int(cfg["revive"])
    s.send(S_TOWER_DIED, pb.TowerDiedMsg(title=RESPAWN_TITLE, msg=str(cost)))
    return mz.store(snap, tower, now, kind)


def floor_entered(s: GameSession, map_id: int) -> list[Any]:
    """Portal para o andar seguinte: (só turco: yeralti #86-#87) o 4205 com o ``towerIndex`` novo sai logo depois do
    21. A missão 38 (passar a Catacombs, Para1 8001) avança em cada andar subido (TODO(inventado): o Para2 de vezes).
    Devolve as linhas a gravar."""
    from .army import send_quests  # army importa este pacote, que importa o campaign

    snap = s.snapshot
    assert snap is not None
    now, kind = s.ctx.clock.now(), mz.kind_of(map_id) or mz.CATACOMBS
    tower = mz.load(snap, now, kind)
    tower.index = mz.floor_of(map_id)
    tower.raise_record(tower.index, now)  # (visto 10/28 #1672 maxIndex 28 antes de vencer o 28)
    s.send(S_TOWER_INFO, _info(s, tower, kind))
    quests = rules.quest_event(snap, s.ctx.templates, rules.CATACOMBS_CONDITION, mz.CAMPAIGN, 1) if (
        kind == mz.CATACOMBS) else []  # fmt: skip
    send_quests(s, quests)
    return [mz.store(snap, tower, now, kind), *quests]


def floor_won(s: GameSession, map_id: int, gp: int) -> Any:
    """Vitória no andar: o totalGp soma a EXP (com os bônus) e o recorde sobe; (só turco: yeralti #75) o 4373 sai
    antes do 131. Devolve a linha a gravar."""
    snap = s.snapshot
    assert snap is not None
    now, kind = s.ctx.clock.now(), mz.kind_of(map_id) or mz.CATACOMBS
    tower = mz.load(snap, now, kind)
    tower.gp += gp
    tower.raise_record(mz.floor_of(map_id), now)
    s.send(S_TOWER_LIST, pb.TowerListMsg(towerInfo=[_info(s, tower, kind)]))
    return mz.store(snap, tower, now, kind)


async def leave_maze(s: GameSession) -> bool:
    """5025 num andar do labirinto: sai para a cidade do céu como a pedreira (4165, 150, 150, 140, 22, 4595). Morto sem
    reviver manda antes o 4419 com os itens da corrida (já na mochila desde o baú, ``open_chest``: não entrega de
    novo) e zera a corrida (index, gp, itens); o recorde e as entradas ficam. (visto 10/28 #1827-#1854; 10/25
    #11400-#11418 e 10/26 #13436-#13476 com o 4419). Vivo ou revivido sai igual, sem 4419, e a corrida continua
    (10/24 #13956-#13965, e o 4205 #17782 com towerIndex 20)."""
    from . import campaign as ch  # campaign importa login, que importa este módulo

    snap = s.snapshot
    assert snap is not None
    if s.campaign is None or not mz.is_floor(s.campaign.map_id):
        return False
    now, kind = s.ctx.clock.now(), _kind(s)
    tower = mz.load(snap, now, kind)
    if tower.dead:
        s.send(S_TOWER_REPORT, pb.TowerInfoMsg(itemTempIds=tower.item_ids()))
        tower.index, tower.gp, tower.items, tower.double, tower.dead = 0, 0, [], False, False
        await s.ctx.characters.save(mz.store(snap, tower, now, kind))
    ch.exit_to_city(s)
    return True


def doubled(s: GameSession, gp: int) -> int:
    """Corrida com a Crypt Key: TODO(inventado) a EXP do andar em dobro (o cliente só diz "lucro dobrado")."""
    snap = s.snapshot
    assert snap is not None
    return gp * 2 if mz.load(snap, s.ctx.clock.now(), _kind(s)).double else gp


async def open_chest(s: GameSession, camp: int, goods: list[list[int]]) -> None:
    """Baú do andar (5125 no nó). (só turco: labirent_sandik #1-#18) 128 DESTROYED, 115, 4476/4426, os 4484, 111
    "Received: ...", 4205 com o ``itemTempIds`` novo e o 83."""
    from . import campaign as ch  # campaign importa login, que importa este módulo
    from . import events as hev

    snap = s.snapshot
    assert snap is not None
    templates, now = s.ctx.templates, s.ctx.clock.now()
    got = [(int(t), int(n)) for t, n in goods]
    if not rewards.can_grant(snap, templates, got, now):
        s.log.info("baú do labirinto: mochila cheia", nó=camp)
        return
    new, _ = rewards.grant(snap, templates, got)
    kind = _kind(s)
    tower = mz.load(snap, now, kind)
    tower.add_items(got)
    await s.ctx.characters.save(*rewards.owners(snap), *new, mz.store(snap, tower, now, kind))
    ch._node_update(s, camp, DONE)
    s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    hev.progress(s)
    for _ in range(titles.item_checks(templates)):
        hev.send_titles(s)
    text = rewards.received(templates, got)
    ch._send(s, ch.S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_TOWER_INFO, _info(s, tower, kind))
    ch._send(s, ch.S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(8300)
async def tower_live(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Reviver no labirinto (``MazeRiverView``: "You are dead. Revive now?", 25 Balens; ``payType`` 0 aceita os
    vinculados). (visto 10/28) grátis #1134-#1137: 111 "Respawn Successful!" e 4175 estado 0; pago #1566-#1573 e
    #1755-#1760: 3, 4152/83 da devoção (só o 1º gasto do dia), 150, 4434 e depois os mesmos 111 e 4175. A vida enche
    sem o 83 da poção."""
    from . import events
    from .campaign import _push_player
    from .player import balens_changed

    snap = s.snapshot
    assert snap is not None
    if s.campaign is None or not mz.is_floor(s.campaign.map_id) or snap.leader is None:
        return
    now, kind = s.ctx.clock.now(), _kind(s)
    tower = mz.load(snap, now, kind)
    cost = 0 if tower.deaths <= 1 else int(_cfg(s, kind)["revive"])  # a 1ª morte da entrada é grátis
    paid = cash.pay(snap.character, cost, msg.payType, "maze_revive", str(s.campaign.map_id), now) if cost else None
    if cost and paid is None:
        s.log.info("8300 sem Balens")
        return
    rules.heal_hero(snap, s.ctx.templates, now)
    tower.dead = False  # (visto 10/24 #13956-#13959) revivido, a saída depois não manda o 4419
    await s.ctx.characters.save(
        snap.character, snap.leader, mz.store(snap, tower, now, kind), *([paid] if paid is not None else [])
    )
    if paid is not None:
        await _push_player(s)
        await events.leed_done(s, events.BALEN_LEED)
        balens_changed(s)
    s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Respawn Successful!"))
    alive = pb.WorldBossPlayerStateMsg(armyId=s.player_id, state=0, leftTime=0)
    s.send(S_DIE_STATE, b.complete(pb.PlayerStateListMsg(playerState=[alive])))


def guard_open(s: GameSession) -> bool:
    """A guarda abre no menor ``Grades`` do UpGradeTempInfos tipo 28 (55; ``BattleGuardView.activeItem``)."""
    snap = s.snapshot
    assert snap is not None
    rows = [r for r in s.ctx.templates.rows("UpGradeTempInfos") if str(r.get("Types")) == "28"]
    return bool(rows) and snap.character.grades >= min(int(r["Grades"]) for r in rows)


def login_guard(s: GameSession) -> None:
    """4631 do login (só turco: login.json #35, nível 56, com uma gema; o inglês até o 16 não manda).
    shortcut: sem gemas modeladas vai vazio; preencher quando o 8742 existir."""
    if guard_open(s):
        s.send(S_BATTLEGUARD, pb.HeroWatchMsg(userId=s.player_id))


@router.on(8742)
async def battleguard_op(s: GameSession, msg: pb.HeroWatchOpMsg) -> None:
    """Gemas da guarda de batalha (4631). Sem inventário de gemas, a operação é recusada e volta o estado vazio."""
    s.log.info("8742 recusado (gemas não modeladas)", op=msg.opType)
    s.send(S_BATTLEGUARD, pb.HeroWatchMsg(userId=s.player_id))
