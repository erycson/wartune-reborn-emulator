"""Defend Sylph Atoll: 4686, os monstros da invasão no andar e as lutas (regras em ``game/pet_defend.py``).

*(visto)* O login manda os sete campos (tutorial_en #44 zerado; oficial_encantar #43 aberto); a abertura (#2337) e o
fechamento (#866) não mandam ``peace*``, e o cliente só troca os contadores quando os três vêm
(``BaseManager.__petBossSwitchHandler``). Junto vão os avisos do canal 12 (#867-#868, #2338). Vai para todos os
níveis; o cliente só avisa do nível 50 em diante.

Sem captura da luta (nível 50), o resto é **dedução** a partir do cliente e dos nós do 20001 (``petisland.json``):
os nós ``masterType`` 1003 (``PosType.PET_BOSS_MONSTER``) chegam escondidos (state 8) e aparecem na janela; o
clique (5125) é uma luta de campanha contra o herói do nó (7511x avançado, 7512x sofisticado, 510x o chefe). Cada
vitória soma ``pet_island_defend_rage_add`` (2, 5) à fúria do andar; com ``pet_island_defend_boss_rage`` (100) o
chefe aparece a todos no andar ("the Lord appears after enough kills", ajuda do cliente). Prêmio só até
``pet_island_defend_reward_count`` (20, 10, 1) por dia; os itens são inventados (``game_settings``, 0057).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...domain.models import Item
from ...protocol.messages import wartune_pb2 as pb
from .. import outer_city, rewards, server_state
from .. import pet_defend as pd
from ..arena import npc_hero
from ..battle import Battle
from ..builders import login as b
from ..builders.army import castle_pawns
from ..campaign import DONE, FIGHTING, NORMAL, PET_ISLANDS
from ..session import GameSession

S_STATE, S_CHAT, S_ALERT, S_ITEMS, S_REPORT, S_FULL_ARMY, S_ARMY_PAWN = 4686, 83, 111, 115, 4103, 150, 100
OPENED = "Defend Sylph Atoll has opened. Warriors, head forth and use your wrath for good!" + " " * 27  # #2338
SUBSIDED = "Sylphs' anger has subsided. They are at peace again."  # #867
OVER = "Defend Sylph Atoll is over. Sylphs show themselves again."  # #868
RIOT = 1003  # PosType.PET_BOSS_MONSTER
BATTLE_TYPE, SCENE = 6, 3  # luta de nó de campanha (tutorial), BattleReportMsg.battleScene da campanha
ENEMY = {"livingId": 4, "side": 2, "pos": 5}


def _state(s: GameSession, *, peace: bool) -> pb.PetIslandDefendStateMsg:
    now = s.ctx.clock.now()
    win = pd.window(s.ctx.templates, s.ctx.world.settings, now)
    msg = pb.PetIslandDefendStateMsg(leftTime=0, mapId=0, bossId=0, ragePoint=0)
    if win is not None:
        start, end, floor = win
        msg.leftTime = int((end - now).total_seconds() * 1000)
        msg.mapId, msg.bossId, msg.ragePoint = floor, pd.boss_id(floor), s.ctx.pet_rage.get(start, 0)
    if peace:
        assert s.snapshot is not None
        msg.peaceMiddle, msg.peaceHigh, msg.peaceBoss = pd.counts(s.snapshot, now)
    return msg


def _notice(s: GameSession, text: str, *, center: bool) -> None:
    s.send(S_CHAT, pb.ChatChannelMsg(channel=12, encodeMsg=text, otherId=-1, userType=1, isCenterTip=center))


def login(s: GameSession) -> None:
    msg = _state(s, peace=True)
    s.pet_defend_map = msg.mapId
    s.send(S_STATE, msg)


def push_state(s: GameSession) -> None:
    """No relógio (20008): 4686 e o aviso quando a janela abre, fecha ou troca de andar; os nós de quem está na ilha."""
    if s.pet_defend_map is None or s.snapshot is None:
        return
    sync_nodes(s)
    msg = _state(s, peace=False)
    if msg.mapId == s.pet_defend_map:
        return
    s.pet_defend_map = msg.mapId
    s.send(S_STATE, msg)
    if msg.mapId:
        _notice(s, OPENED, center=True)
    else:
        _notice(s, SUBSIDED, center=True)
        _notice(s, OVER, center=False)


def _window(s: GameSession) -> tuple[datetime, datetime, int] | None:
    return pd.window(s.ctx.templates, s.ctx.world.settings, s.ctx.clock.now())


def _boss_up(s: GameSession, start: datetime) -> bool:
    return s.ctx.pet_rage.get(start, 0) >= pd.max_rage(s.ctx.templates)


def sync_nodes(s: GameSession, *, send: bool = True) -> None:
    """Estado dos nós 1003 do mapa da ilha desta sessão: na janela do andar, os monstros aparecem (uma vez por
    janela: o vencido fica DONE) e o chefe quando a fúria enche; fora dela, tudo escondido (8, como no 127)."""
    from .campaign import _node_update  # campaign importa este módulo

    c = s.campaign
    if c is None or c.map_id not in PET_ISLANDS:
        return
    win = _window(s)
    key = (win[0], _boss_up(s, win[0])) if win is not None and win[2] == c.map_id else None
    prev, s.pet_defend_nodes = s.pet_defend_nodes, key
    if key == prev:
        return
    new_window = key is not None and (prev is None or prev[0] != key[0])
    for camp, node in c.nodes.items():
        kind = pd.kind(int(node["heroTempId"])) if node["masterType"] == RIOT else None
        if kind is None or node["state"] == FIGHTING:
            continue
        if key is None:
            want = DONE
        elif kind == pd.BOSS:
            if key[1] and (new_window or prev is None or not prev[1]):
                want = NORMAL  # a fúria encheu (ou entrou com ela cheia)
            else:
                want = DONE if new_window else node["state"]
        else:
            want = NORMAL if new_window else node["state"]
        if want != node["state"]:
            if send:
                _node_update(s, camp, want, fresh=True)
            else:
                node["state"] = want


async def attack(s: GameSession, camp: int, node: dict[str, Any]) -> None:
    """5125 num nó 1003: luta contra o herói do nó (battleType 6, como o nó de campanha)."""
    from .campaign import ARMY_FIGHTING, S_ARMY_POS, S_MAP_SYNC, _army_brief, _node_update, map_sync, player_hero

    c, snap = s.campaign, s.snapshot
    assert c is not None and snap is not None
    win, hero_id = _window(s), int(node["heroTempId"])
    kind = pd.kind(hero_id)
    if win is None or win[2] != c.map_id or kind is None or s.battle is not None or c.fighting:
        s.log.info("invasão: luta recusada", nó=camp, janela=win is not None)
        return
    row = s.ctx.templates.get("GameHeroTemp", hero_id) or {}
    hp = max(1, int(row.get("Live") or 1))
    soldiers, pawn_tpl = outer_city.army_soldiers(snap, s.ctx.templates)
    enemy = npc_hero(
        **ENEMY,
        tempId=hero_id,
        nickName=row.get("TemplateName", ""),
        grade=int(row.get("Grades") or 0),
        maxHp=hp,
        initHp=hp,
        hp=hp,
        captain=int(row.get("Captain") or 0),
        res=row.get("ResPath", ""),
    )
    spec = {
        "battleType": BATTLE_TYPE,
        "mapTempId": c.map_id,
        "attackModel": 2,
        "battleScene": SCENE,
        "soldiers": soldiers,
        "heroes": [enemy],
        "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
    }
    c.fighting = camp
    s.send(S_MAP_SYNC, map_sync(s, ARMY_FIGHTING))
    s.send(S_ARMY_POS, _army_brief(s, ARMY_FIGHTING))
    _node_update(s, camp, FIGHTING, user=True)

    async def finished(battle: Battle, won: bool) -> None:
        await _over(s, battle, camp, kind, win[0], won)

    s.battle = Battle(
        spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, s.send, finished, settings=s.ctx.world.settings
    )
    s.log.info("invasão: luta", nó=camp, heroi=hero_id, battle=s.battle.id)
    s.battle.start()


async def _over(s: GameSession, battle: Battle, camp: int, kind: int, start: datetime, won: bool) -> None:
    """Fim: tropas, 4103, prêmio (até o teto do dia) e fúria; o 4686 novo vai a todos (a fúria é do andar) e os
    nós do chefe aparecem quando ela enche."""
    from . import events  # events importa login, que importa a campanha
    from .campaign import ARMY_IDLE, S_ARMY_POS, S_MAP_SYNC, _army_brief, _node_update, _report, map_sync

    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None and snap.leader is not None
    s.battle, s.hero_sp = None, battle.player_sp
    rows: list[object] = []
    if (hit := outer_city.lose_troops(snap, templates, battle.troops())) is not None:
        outer_city.refill(*hit)
        rows += [snap.leader, *snap.pawns]
    drops: list[tuple[int, int]] = []
    new: list[Item] = []
    text = ""
    if won:
        st = pd.count_state(snap, kind, now)
        drops = pd.drops(s.ctx.world.settings, kind)
        if st.value >= pd.max_counts(templates)[kind]:
            drops = []  # passou do teto: ainda soma fúria (dedução), sem prêmio
        elif not rewards.can_grant(snap, templates, drops, now):
            s.log.info("invasão: mochila cheia", tipo=kind)
            drops = []
        else:
            st.value, st.updated_at = st.value + 1, now
            items, text = rewards.grant(snap, templates, drops)
            new = list(items)
            rows += [st, *rewards.owners(snap), *items]
        if kind != pd.BOSS:
            s.ctx.pet_rage[start] = min(
                pd.max_rage(templates), s.ctx.pet_rage.get(start, 0) + pd.rage_add(templates, kind)
            )
            await server_state.save(s.ctx, server_state.PET_RAGE)
    if rows:
        await s.ctx.characters.save(*rows)
    s.send(S_REPORT, _report(battle, won, 0))
    s.send(S_FULL_ARMY, b.complete(_army(s)))
    s.send(S_ARMY_PAWN, castle_pawns(snap, templates))
    c = s.campaign
    if c is not None and c.fighting == camp:
        c.fighting = 0
        s.send(S_MAP_SYNC, map_sync(s, ARMY_IDLE))
        s.send(S_ARMY_POS, _army_brief(s, ARMY_IDLE))
        _node_update(s, camp, DONE if won else NORMAL, fresh=won)
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
        events.items_gained(s)
    if text:
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    if won:
        s.send(S_STATE, _state(s, peace=True))  # contadores novos só para quem lutou
        for o in s.ctx.online.sessions():
            if o is not s and o.snapshot is not None and o.pet_defend_map:
                o.send(S_STATE, _state(o, peace=False))
            if o.snapshot is not None:
                sync_nodes(o)


def _army(s: GameSession) -> pb.ArmyArmyMsg:
    from .login import army

    assert s.snapshot is not None
    return army(s, s.snapshot)[0]
