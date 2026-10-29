"""Arena em grupo (Party): a luta das salas PvP (``roomType`` 1) que procuram partida (5039 com ``paraInt2`` 0).

(visto) oficial_20261027-152321-1 #19909-#19958 e #19959-#19995, sala de 1 contra jogador de outro servidor:
5039 -> 25 estado 2 e 111 "Matching in progress..."; achado o adversário, 157 com ``battleType`` 10
(``BattleType.BATTLE_MATCHING`` do cliente), ``mapTempId`` 992, ``attackModel`` 2, sem soldados, os dois heróis
``type`` 1 com o ``userId`` de cada um, ``pos`` 1 nos dois lados, e ``side`` = o lado de quem recebe (o cliente
põe ``selfSide = side``, ``CreateGameTransaction``; #19912 o jogador no lado 2). Depois da luta: 4103
``{battleResult, battleScene 8}``, 3, 112 (missão 421, tipo 16), 4152 (leed 13), 3, 4413 (``match``), 111, 115 e
83 "Received: Insignia x10" (derrota), 4476, 4426, 4484..., 24 e 25 estado 1 (a sala volta a esperar).

A fila são as próprias salas: PvP em estado 2 (``COMPETING``); o 5037 (cancelar) e a saída do dono tiram a sala.
Sem adversário a sala espera (o oficial não manda nada até achar; o cliente tem o Cancel). Só salas deste
servidor (o oficial cruza servidores).
"""

from __future__ import annotations

from typing import Any

from google.protobuf.message import Message

from ...protocol.messages import wartune_pb2 as pb
from .. import arena_grupo as ag
from .. import events as ev
from .. import rewards, rules
from ..battle import TEAM_POS, Battle
from ..builders import login as b
from ..rooms import COMPETING, IN_USE, PLAYING, PVP, Room
from ..session import GameSession

MATCHING, SCENE = 10, 8  # battleType e battleScene vistos (#19968, #19987)
LEADER_POS = 1  # (visto #19912, #19968) o herói de cada sala no lugar 1 do seu lado
WON, LOST = 1, 2
S_REPORT, S_CLICK_ADD, S_ALERT, S_CHAT, S_ITEMS, S_PLAYER = 4103, 4413, 111, 83, 115, 3
ARENA_PARTY_LEED = 13  # LeedTemp 13: (visto #19930) 4152 com currentCount +1 a cada luta
CLICK_KEY = "match"  # DayGuideManager: "match" -> atividade 2/10; (visto #19932) 4413 keyData +1
# game_settings.arena_party (migração 0107): prêmio por resultado, {"win": [[templateId, n]], "lose": [...]}


def _fit(room: Room, s: GameSession) -> list[GameSession] | None:
    """Sessões da sala, todas no jogo e fora de luta; ``None`` se alguma não pode lutar."""
    out = [s.ctx.online.get(p) for p in room.members]
    ok = all(o is not None and o.snapshot is not None and o.snapshot.leader is not None and o.battle is None
             for o in out)  # fmt: skip
    return [o for o in out if o is not None] if ok else None


def match(s: GameSession, room: Room, rewarded: bool) -> None:
    """A sala ``room`` (de ``s``, o dono) entrou na fila: luta contra a primeira outra sala PvP esperando.
    ``rewarded``: o dono quer prêmio (``paraBool1`` = ``isNoGet`` false), como o ``room.rewarded`` dos outros."""
    if rewarded:
        room.rewarded.add(room.master)
    else:
        room.rewarded.discard(room.master)
    mine = _fit(room, s)
    if mine is None:
        return
    for other in s.ctx.rooms.visible():
        if other is room or other.type != PVP or other.state != COMPETING:
            continue
        theirs = _fit(other, s)
        if theirs is not None:
            _fight(s, room, mine, other, theirs)
            return


def _fight(s: GameSession, room: Room, mine: list[GameSession], other: Room, theirs: list[GameSession]) -> None:
    from .. import arena as A  # noqa: PLC0415  (game.arena é pesado)
    from .campaign import _with_team, player_hero, team_hero  # noqa: PLC0415  (campaign importa room)

    room.state = other.state = PLAYING  # (visto #19911 -> #19912) sem 25 entre o 111 e o 157
    team = [o for o in mine if o is not s]
    spec = A.colosseum_spec([], [])
    spec.update(battleType=MATCHING, battleScene=SCENE, player={"livingId": A.PLAYER_LIVING, "pos": LEADER_POS})
    spec = _with_team(s, spec, team)
    used = max([u["livingId"] for u in spec["heroes"]] + [A.PLAYER_LIVING])
    # TODO(inventado): os lugares dos outros do lado 2 (só visto 1 contra 1, os dois no lugar 1)
    enemies = [
        team_hero(s, o) | {"side": 2, "livingId": used + 1 + i, "pos": ([LEADER_POS, *TEAM_POS])[i]}
        for i, o in enumerate(theirs)
    ]
    spec["heroes"] = [*spec["heroes"], *enemies]
    a_ids, b_ids = [o.player_id for o in mine], [o.player_id for o in theirs]

    def send(code: int, msg: Message) -> None:
        for pid in a_ids:
            if (o := s.ctx.online.get(pid)) is not None:
                o.send(code, msg)
        if isinstance(msg, pb.BattlePrepareMsg):  # o lado 2 vê a luta do seu lado (selfSide)
            copy = pb.BattlePrepareMsg()
            copy.CopyFrom(msg)
            copy.side, msg = 2, copy
        for pid in b_ids:
            if (o := s.ctx.online.get(pid)) is not None:
                o.send(code, msg)

    async def finished(battle: Battle, won: bool) -> None:
        s.battle, s.hero_sp = None, battle.player_sp
        for ids, r, win in ((a_ids, room, won), (b_ids, other, not won)):
            for pid in ids:
                if (o := s.ctx.online.get(pid)) is not None and o.snapshot is not None:
                    await _after(o, win, pid in r.rewarded)
            _back(s, r)

    s.battle = Battle(spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, send, finished,
                      settings=s.ctx.world.settings)  # fmt: skip
    battle = s.battle
    battle.forfeit = lambda: finished(battle, False)  # dono caiu no meio: derrota dele, as salas voltam a 1
    s.log.info("arena em grupo", battle=s.battle.id, salas=(room.id, other.id), times=(a_ids, b_ids))
    s.battle.start()


async def _after(o: GameSession, won: bool, rewarded: bool) -> None:
    """4103, missão 16, leed 13, contador ``match`` e o prêmio (só a quem pediu prêmio)."""
    from .army import count_quest  # noqa: PLC0415  (army importa player, que importa room)
    from .events import click_info, items_gained, leed_done  # noqa: PLC0415

    snap, now = o.snapshot, o.ctx.clock.now()
    assert snap is not None
    from .login import player_info  # noqa: PLC0415

    o.send(S_REPORT, pb.BattleReportMsg(battleResult=WON if won else LOST, battleScene=SCENE))
    cfg: dict[str, Any] = dict(o.ctx.world.settings.get("arena_party") or {})
    scored, delta = ag.add(snap, won, now, cfg)
    await o.ctx.characters.save(scored)
    o.send(S_PLAYER, b.complete(player_info(o, snap)))  # (visto #19928) 3 logo depois do 4103; leva o crossScore
    await count_quest(o, rules.ARENA_PARTY_CONDITION, 1)
    await leed_done(o, ARENA_PARTY_LEED)
    clicked = ev.click(snap, CLICK_KEY, now)
    await o.ctx.characters.save(clicked)
    o.send(S_CLICK_ADD, pb.ClickDatasRspMsg(info=[click_info(clicked)]))
    # TODO(inventado): o texto dos pontos (a captura não mostra); "Points  +5" do torneio de fadas como modelo
    o.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Points {delta:+d}"))
    drops = [(int(t), int(n)) for t, n in cfg.get("win" if won else "lose", [])]
    if not rewarded or not drops or not rewards.can_grant(snap, o.ctx.templates, drops, now):
        return
    new, text = rewards.grant(snap, o.ctx.templates, drops)
    await o.ctx.characters.save(*new)
    o.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
    o.send(S_ITEMS, rewards.items_msg(new, o.player_id))
    o.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))
    items_gained(o)


def _back(s: GameSession, room: Room) -> None:
    """(visto #19957-#19958) 24 com os prontos e 25 estado 1: a sala volta a esperar."""
    from .room import S_STATE, _send_ready, _to_room  # noqa: PLC0415

    if s.ctx.rooms.get(room.id) is not room:  # o dono saiu no meio: a sala já acabou
        return
    room.state = IN_USE
    _send_ready(s, room)
    _to_room(s, room, S_STATE, pb.RoomStateRspMsg(roomState=IN_USE))
