"""Forgotten Catacombs (8296/8297/8299/8300, 4205/4373) e guarda de batalha (8742).

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
MAZE_LEED = 23  # LeedTemp 23 "Enter Forgotten Catacombs"


def _cfg(s: GameSession) -> dict[str, Any]:
    return mz.settings(s.ctx.world.settings)


def tower_msg(s: GameSession, index: int = 0) -> pb.TowerInfoMsg:
    snap = s.snapshot
    assert snap is not None
    return mz.info(mz.load(snap, s.ctx.clock.now()), _cfg(s), index)


def record(s: GameSession) -> int:
    """maxIndex do personagem (missão 38, título PASS_TOWER, loja do labirinto)."""
    return mz.record(s.snapshot) if s.snapshot is not None else 0


def login_list(s: GameSession) -> pb.TowerListMsg:
    """4373 do login: (visto) tutorial_en e 215937 vazio sem registro; (só turco: login #55) com a torre."""
    snap = s.snapshot
    assert snap is not None
    tower = mz.load(snap, s.ctx.clock.now())
    if not tower.record and not tower.index:
        return pb.TowerListMsg()
    return pb.TowerListMsg(towerInfo=[mz.info(tower, _cfg(s))])


@router.on(8297)
async def tower_info(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Info de uma aba (4205)."""
    s.send(S_TOWER_INFO, tower_msg(s, msg.index))


@router.on(8299)
async def tower_reset(s: GameSession, msg: pb.TowerInfoReqMsg) -> None:
    """Reset (``MazeFrame``: "Are you sure you want to forfeit all progress and start over?"; sem custo no cliente):
    a corrida volta ao andar 0, o recorde fica. A tela se refaz com o 4205."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    tower = mz.load(snap, now)
    if msg.index == 0 and s.campaign is None:
        tower.index, tower.gp, tower.items, tower.double = 0, 0, [], False
        await s.ctx.characters.save(mz.store(snap, tower, now))
    s.send(S_TOWER_INFO, mz.info(tower, _cfg(s), msg.index))


@router.on(8296)
async def tower_enter(s: GameSession, msg: pb.EnterTowerInfoMsg) -> None:
    """Entrar (``MazeFrame``): ``chooseIndex`` 1 Start (gasta uma entrada do dia, do andar 1; "No attempts left!"
    sem entrada), 0 Continue (o andar da corrida). ``isDouble`` 2 gasta uma Crypt Key (sem ela o cliente abre a
    compra). (só turco: yeralti #26-#39) 4205, 4165, 150, 150, 125, 140, 21, 3, 4902/150, 4903, 127, 4205 e o 83 da
    poção de vida."""
    snap = s.snapshot
    assert snap is not None
    now, cfg = s.ctx.clock.now(), _cfg(s)
    tower = mz.load(snap, now)
    if msg.campaignId != mz.CAMPAIGN or s.campaign is not None or s.battle is not None:
        s.log.info("8296 recusado", campanha=msg.campaignId)  # shortcut: a Necropolis (8101) não tem andares aqui
        return
    key: tuple[Item, bool] | None = None
    if msg.chooseIndex == START:
        if tower.enters >= int(cfg["max_enter"]):
            s.log.info("8296 sem entrada do dia", feitas=tower.enters)
            return
        if msg.isDouble == DOUBLE and (key := rewards.take_one(snap, int(cfg["key"]))) is None:
            s.log.info("8296 dobrado sem Crypt Key")
            return
        tower.enters += 1
        tower.index, tower.gp, tower.items, tower.double = 1, 0, [], msg.isDouble == DOUBLE
    elif tower.index <= 0:
        s.log.info("8296 continuar sem corrida")
        return
    if key is not None:
        item, gone = key
        await s.ctx.characters.save(*([] if gone else [item]), delete=(item,) if gone else ())
        s.send(S_ITEMS, rewards.taken_msg(item, gone, s.player_id))
    await s.ctx.characters.save(mz.store(snap, tower, now))
    await _enter(s, tower)
    if msg.chooseIndex == START:
        from . import events as hev  # events importa este módulo

        await hev.leed_done(s, MAZE_LEED)


async def _enter(s: GameSession, tower: mz.Tower) -> None:
    from . import campaign as ch  # campaign importa login, que importa este módulo
    from . import systems
    from .login import army
    from .player import hp_pack

    snap = s.snapshot
    assert snap is not None
    templates = s.ctx.templates
    floor_map = mz.map_of(tower.index)
    full = mz.content(templates, _cfg(s))
    content = {**full, "maps": {**full["maps"], str(floor_map): mz.from_town(full["maps"][str(floor_map)])}}
    s.send(S_TOWER_INFO, mz.info(tower, _cfg(s)))
    ch._send(s, ch.S_BUFFERS, pb.CampaignBufferMsg(armyId=s.player_id))
    s.send(ch.S_FULL_ARMY, b.complete(army(s, snap)[0]), cards=False)
    s.send(ch.S_FULL_ARMY, b.complete(army(s, snap)[0]), cards=False)
    s.campaign = c = CampaignMap.enter_dungeon(content, floor_map)
    c.content = full  # pelo portal, o início dos outros andares é o 40
    created = pb.RoomCreatedMsg(createdType=ch.ENTER)
    created.room.campaignId = floor_map
    ch._send(s, ch.S_ROOM_CREATED, created)
    ch._send(s, ch.S_MAP_SYNC, ch.map_sync(s, ch.ARMY_IDLE))
    ch._send(s, ch.S_ROOM_ENTER, ch._room_enter(s))
    await ch._push_player(s)
    s.send(ch.S_FULL_ARMY, b.complete(army(s, snap)[0]))
    systems.send_camp_buffs(s, systems.camp_type(ch._campaign_row(s, mz.CAMPAIGN)))
    ch._send(s, ch.S_NODES, c.node_list())
    s.send(S_TOWER_INFO, mz.info(tower, _cfg(s)))
    healed = rules.heal_hero(snap, templates, s.ctx.clock.now()) if snap.leader is not None else 0
    hp_pack(s, healed)  # (só turco: yeralti #39) "HP Paketi kullanılarak HP arttırıldı."
    if snap.leader is not None:
        await s.ctx.characters.save(snap.leader)


def floor_entered(s: GameSession, map_id: int) -> Any:
    """Portal para o andar seguinte: (só turco: yeralti #86-#87) o 4205 com o ``towerIndex`` novo sai logo depois do
    21. Devolve a linha a gravar."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    tower = mz.load(snap, now)
    tower.index = mz.floor_of(map_id)
    s.send(S_TOWER_INFO, mz.info(tower, _cfg(s)))
    return mz.store(snap, tower, now)


def floor_won(s: GameSession, map_id: int, gp: int) -> Any:
    """Vitória no andar: o totalGp soma a EXP (com os bônus) e o recorde sobe; (só turco: yeralti #75) o 4373 sai
    antes do 131. Devolve a linha a gravar."""
    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    tower = mz.load(snap, now)
    tower.gp += gp
    tower.record = max(tower.record, mz.floor_of(map_id))
    s.send(S_TOWER_LIST, pb.TowerListMsg(towerInfo=[mz.info(tower, _cfg(s))]))
    return mz.store(snap, tower, now)


def doubled(s: GameSession, gp: int) -> int:
    """Corrida com a Crypt Key: TODO(inventado) a EXP do andar em dobro (o cliente só diz "lucro dobrado")."""
    snap = s.snapshot
    assert snap is not None
    return gp * 2 if mz.load(snap, s.ctx.clock.now()).double else gp


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
    tower = mz.load(snap, now)
    tower.add_items(got)
    await s.ctx.characters.save(*rewards.owners(snap), *new, mz.store(snap, tower, now))
    ch._node_update(s, camp, DONE)
    s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
    hev.progress(s)
    for _ in range(titles.item_checks(templates)):
        hev.send_titles(s)
    text = rewards.received(templates, got)
    ch._send(s, ch.S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    s.send(S_TOWER_INFO, mz.info(tower, _cfg(s)))
    ch._send(s, ch.S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


@router.on(8300)
async def tower_live(s: GameSession, msg: pb.PayTypeMsg) -> None:
    """Reviver no labirinto (``MazeRiverView``: "You are dead. Revive now?", 25 Balens; ``payType`` 0 aceita os
    vinculados). TODO(inventado): a resposta (nenhuma captura): a vida do herói enche (3 e o 83 da poção)."""
    from .campaign import _push_player
    from .player import hp_pack

    snap = s.snapshot
    assert snap is not None
    if s.campaign is None or not mz.is_floor(s.campaign.map_id) or snap.leader is None:
        return
    now = s.ctx.clock.now()
    paid = cash.pay(snap.character, int(_cfg(s)["revive"]), msg.payType, "maze_revive", str(s.campaign.map_id), now)
    if paid is None:
        s.log.info("8300 sem Balens")
        return
    healed = rules.heal_hero(snap, s.ctx.templates, now)
    await s.ctx.characters.save(snap.character, snap.leader, paid)
    await _push_player(s)
    hp_pack(s, healed)


@router.on(8742)
async def battleguard_op(s: GameSession, msg: pb.HeroWatchOpMsg) -> None:
    """Gemas da guarda de batalha (4631). Sem inventário de gemas, a operação é recusada e volta o estado vazio."""
    s.log.info("8742 recusado (gemas não modeladas)", op=msg.opType)
    s.send(S_BATTLEGUARD, pb.HeroWatchMsg(userId=s.player_id))
