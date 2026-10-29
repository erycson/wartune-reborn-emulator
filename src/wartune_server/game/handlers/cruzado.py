"""PvP entre servidores rodando como fila LOCAL: só jogadores deste servidor se enfrentam.

Entrada: a inscrição da guerra entre servidores (8779, ``ConsortiaSocketOutManager``; o resto da tela,
``GvgCrossReadyController``, segue em ``guild_events.py``). Dois na fila: luta no motor do coliseu
(``campaign.pvp_fight`` com a cópia do outro, ``battleType`` 10 / ``battleScene`` 8 como a arena em grupo); o
outro assiste a própria cópia como espectador (``Battle.watch``) e recebe o 4803 no fim. Os dois somam os pontos
da arena em grupo (``crossScore``, ``game/arena_grupo.py``) e recebem o 4481 se já podem resgatar (8590 em
``arena.py``). TODO(inventado): o oficial cruza servidores e não há captura desta fila; tudo aqui é dedução.
"""

from __future__ import annotations

from typing import Any

from ...protocol.messages import wartune_pb2 as pb
from .. import arena_grupo as ag
from ..builders import login as b
from ..session import GameSession

MATCHING, SCENE = 10, 8  # os da arena em grupo (handlers/arena_grupo.py)
WON, LOST = 1, 2
S_PLAYER, S_ALERT, S_REPORT, S_IS_TAKE = 3, 111, 4103, 4481


def _free(s: GameSession, pid: int) -> GameSession | None:
    o = s.ctx.online.get(pid)
    ok = o is not None and o is not s and o.snapshot is not None and o.snapshot.leader is not None and o.battle is None
    return o if ok else None


def enter(s: GameSession) -> None:
    """Entra na fila; se alguém daqui já espera, lutam já."""
    queue = s.ctx.cross_queue
    queue[:] = [p for p in queue if s.ctx.online.get(p) is not None]  # quem saiu do jogo sai da fila
    if s.battle is not None or s.player_id in queue:
        return
    other = next((o for pid in list(queue) if (o := _free(s, pid)) is not None), None)
    if other is None:
        queue.append(s.player_id)
        # (visto, arena em grupo #19911) o mesmo aviso da procura de partida
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg="Matching in progress..."))
        return
    queue.remove(other.player_id)
    _fight(s, other)


def _fight(s: GameSession, other: GameSession) -> None:
    from .campaign import pvp_fight  # noqa: PLC0415  (campaign importa muita coisa)

    assert other.snapshot is not None
    other_id = other.player_id

    async def on_end(won: bool) -> None:
        await after(s, won)
        if (o := s.ctx.online.get(other_id)) is not None and o.snapshot is not None:
            await after(o, not won)

    pvp_fight(s, other.snapshot, MATCHING, SCENE, on_end)
    battle = s.battle
    assert battle is not None
    battle.watch(other)  # TODO(inventado): o outro vê do lado 1 (a cópia dele é o lado 2)

    async def forfeit() -> None:  # quem conduz caiu: derrota dele, o outro sai da tela
        await on_end(False)
        battle.release_viewers(False)

    battle.forfeit = forfeit
    s.log.info("pvp entre servidores (fila local)", battle=battle.id, jogadores=(s.player_id, other_id))


async def after(o: GameSession, won: bool) -> None:
    """4103, pontos (``crossScore`` no 3) e o 4481 se o prêmio já pode ser resgatado."""
    from .login import player_info  # noqa: PLC0415

    snap, now = o.snapshot, o.ctx.clock.now()
    assert snap is not None
    o.send(S_REPORT, pb.BattleReportMsg(battleResult=WON if won else LOST, battleScene=SCENE))
    cfg: dict[str, Any] = dict(o.ctx.world.settings.get("arena_party") or {})
    scored, _ = ag.add(snap, won, now, cfg)
    await o.ctx.characters.save(scored)
    o.send(S_PLAYER, b.complete(player_info(o, snap)))
    cross = o.ctx.world.settings.get("cross_score") or {}
    if ag.can_claim(snap, now, cfg, cross):
        o.send(S_IS_TAKE, pb.ChallengeRankRewardMsg(isTake=True))
