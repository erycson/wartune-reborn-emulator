"""Defend Sylph Atoll: 4686 no login e na abertura/fechamento da janela (regras em ``game/pet_defend.py``).

*(visto)* O login manda os sete campos (tutorial_en #44 zerado; oficial_encantar #43 aberto); a abertura (#2337) e o
fechamento (#866) não mandam ``peace*``, e o cliente só troca os contadores quando os três vêm
(``BaseManager.__petBossSwitchHandler``). Junto vão os avisos do canal 12 (#867-#868, #2338). Vai para todos os
níveis; o cliente só avisa do nível 50 em diante.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from .. import pet_defend as pd
from ..session import GameSession

S_STATE, S_CHAT = 4686, 83
OPENED = "Defend Sylph Atoll has opened. Warriors, head forth and use your wrath for good!" + " " * 27  # #2338
SUBSIDED = "Sylphs' anger has subsided. They are at peace again."  # #867
OVER = "Defend Sylph Atoll is over. Sylphs show themselves again."  # #868


def _state(s: GameSession, *, peace: bool) -> pb.PetIslandDefendStateMsg:
    now = s.ctx.clock.now()
    win = pd.window(s.ctx.templates, s.ctx.world.settings, now)
    msg = pb.PetIslandDefendStateMsg(leftTime=0, mapId=0, bossId=0, ragePoint=0)
    if win is not None:
        start, end, floor = win
        msg.leftTime = int((end - now).total_seconds() * 1000)
        msg.mapId, msg.bossId = floor, pd.boss_id(floor)
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
    """No relógio (20008): 4686 e o aviso quando a janela abre, fecha ou troca de andar."""
    if s.pet_defend_map is None or s.snapshot is None:
        return
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
