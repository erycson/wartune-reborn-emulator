"""Chefe do mundo (World Boss): agenda de hoje (4182) e a leitura dos templates.

Os chefes são as campanhas com ``Types=1`` (5001 e 5003). O cliente guarda todo campanha com
``Types>=1`` (menos 5 e 9) e derruba com um id fora desse dicionário, então o 4182 manda só estes.
Os horários (``OpenTime``/``StopTime``) são do jogo no fuso do servidor (``gameday.GAME_TZ``). O inglês segue o
Pacífico: o 4182 da captura inglesa (#103, 18:24 no Pacífico) mostra 5001 já fechado (passou das 12:00) e 5003
ainda não aberto (antes das 21:35).
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import UTC, datetime, time

from ..domain import gameday
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row

OPEN, BEFORE, CLOSED = 0, 1, 2  # WorldBossInfoStateMsg.state: aberto, ainda não abriu hoje, encerrado hoje


def boss(templates: GameTemplates, campaign_id: int) -> Row | None:
    return next(templates.find("Campaigns", CampaignId=campaign_id, Types=1), None)


def bosses(templates: GameTemplates) -> list[Row]:
    return sorted(templates.find("Campaigns", Types=1), key=lambda r: int(r["CampaignId"]))


def _hour(text: str) -> time:
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def state(row: Row, now: datetime) -> int:
    """Estado de hoje: aberto de ``OpenTime`` até ``StopTime`` (sem o minuto final).

    ponytail: janela que cruza a meia-noite não existe nos templates; não é tratada.
    """
    local = gameday.local(now).time()
    if local < _hour(row["OpenTime"]):
        return BEFORE
    if local < _hour(row["StopTime"]):
        return OPEN
    return CLOSED


def window(row: Row, now: datetime) -> tuple[datetime, datetime]:
    """Abertura e fechamento de hoje (no fuso do jogo), em UTC."""
    day = gameday.local(now)
    opened, stop = (day.replace(hour=h.hour, minute=h.minute, second=0, microsecond=0)
                    for h in (_hour(row["OpenTime"]), _hour(row["StopTime"])))  # fmt: skip
    return opened.astimezone(UTC), stop.astimezone(UTC)


def states(templates: GameTemplates, now: datetime, defeated: Collection[int] = ()) -> dict[int, int]:
    """Estado de cada chefe; ``defeated`` (morto na janela de hoje) aparece encerrado."""
    return {int(row["CampaignId"]): CLOSED if int(row["CampaignId"]) in defeated else state(row, now)
            for row in bosses(templates)}  # fmt: skip


def states_msg(templates: GameTemplates, now: datetime, defeated: Collection[int] = ()) -> pb.WorldBossStateMsg:
    msg = pb.WorldBossStateMsg()
    for campaign_id, value in states(templates, now, defeated).items():
        msg.worldBossInfo.add(campaignId=campaign_id, state=value)
    return msg
