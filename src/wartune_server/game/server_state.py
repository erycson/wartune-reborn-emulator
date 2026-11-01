"""Estado do servidor que não é de um personagem (``server_states``, migração 0109).

Vive nos objetos de sempre do ``GameContext``: a proteção dos castelos NPC (``wilds.shields``), a fúria da ilha dos
pets (``pet_rage``), os Invasores da terra secreta (``guilds.invasions``) e os times livres (``teams``). Cada mudança
grava a chave inteira em JSON (``save``); o arranque lê tudo (``ServerStates.load``) e devolve aos objetos
(``restore``). O que só existe enquanto a luta roda (``Invasion.fighting``, convites de time) não vai.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from ..domain.models import ServerState
from .fam import Invasion, Lords

if TYPE_CHECKING:
    from ..services.characters import CharacterService
    from .session import GameContext

SHIELDS, PET_RAGE, INVASIONS, TEAMS, MARRIAGE = "shields", "pet_rage", "invasions", "teams", "marriage"
LORDS = "lords"  # Master Treasure Thief chamado (`guilds.lords`): hora da chamada e os vencidos
RAGE_KEEP = timedelta(days=1)  # janelas da fúria mais velhas que isso já fecharam (a janela dura horas)


@dataclass
class ServerStates:
    server_id: int = 0
    rows: dict[str, ServerState] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # duas gravações da mesma chave nova: um INSERT só

    @classmethod
    async def load(cls, characters: CharacterService, server_id: int) -> ServerStates:
        rows = await characters.read(lambda uow: uow.events.of_server(server_id))
        return cls(server_id, {r.key: r for r in rows})

    def value(self, key: str) -> Any:
        row = self.rows.get(key)
        return json.loads(row.text) if row is not None and row.text else None


def _dump(ctx: GameContext, key: str, now: datetime) -> Any:
    if key == SHIELDS:
        return {f"{a}:{b}": until.isoformat() for (a, b), until in ctx.wilds.shields.items() if until > now}
    if key == PET_RAGE:
        return {start.isoformat(): points for start, points in ctx.pet_rage.items() if start > now - RAGE_KEEP}
    if key == INVASIONS:
        return {str(g): {"wave": i.wave.isoformat(), "dead": sorted(i.dead)} for g, i in ctx.guilds.invasions.items()}
    if key == LORDS:
        return {
            str(g): {"at": x.called_at.isoformat(), "dead": sorted(x.dead), "wave": x.wave, "told": x.told}
            for g, x in ctx.guilds.lords.items()
        }
    if key == TEAMS:
        return ctx.teams.dump()
    if key == MARRIAGE:
        from .handlers import marriage  # o handler importa a sessão, que importa este módulo

        return marriage.dump_pending()
    raise KeyError(key)


async def save(ctx: GameContext, key: str) -> None:
    """Grava ``key`` como está agora na memória."""
    now = ctx.clock.now()
    async with ctx.states.lock:
        row = ctx.states.rows.get(key) or ServerState(ctx.states.server_id, key, now)
        row.text, row.updated_at = json.dumps(_dump(ctx, key, now)), now
        ctx.states.rows[key] = row
        await ctx.characters.save(row)


def restore(ctx: GameContext, states: ServerStates) -> None:
    """Põe o que ``states`` leu do banco nos objetos do contexto (arranque)."""
    ctx.states.server_id, ctx.states.rows = states.server_id, states.rows
    for k, until in (states.value(SHIELDS) or {}).items():
        a, b = k.split(":")
        ctx.wilds.shields[int(a), int(b)] = datetime.fromisoformat(until)
    for start, points in (states.value(PET_RAGE) or {}).items():
        ctx.pet_rage[datetime.fromisoformat(start)] = points
    for g, inv in (states.value(INVASIONS) or {}).items():
        ctx.guilds.invasions[int(g)] = Invasion(datetime.fromisoformat(inv["wave"]), set(inv["dead"]))
    for g, x in (states.value(LORDS) or {}).items():  # a vencida sai no próximo ``fam.lords_of``
        at = datetime.fromisoformat(x["at"])
        ctx.guilds.lords[int(g)] = Lords(at, set(x["dead"]), wave=x.get("wave", 0), told=x.get("told", 0))
    ctx.teams.restore(states.value(TEAMS) or [])
    from .handlers import marriage

    marriage.load_pending(states.value(MARRIAGE) or {})
