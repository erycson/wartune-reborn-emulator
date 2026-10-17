"""Chefe do mundo (Dünya Boss): agenda de hoje (4182) e a leitura dos templates.

Os chefes são as campanhas com ``Types=1`` (5001 e 5003). O cliente guarda todo campanha com
``Types>=1`` (menos 5 e 9) e derruba com um id fora desse dicionário, então o 4182 manda só estes.
Os horários (``OpenTime``/``StopTime``) são do jogo no fuso de Istambul: a captura de 4182 em
``replay_packets.json`` (pacotes 78 -> 102, 12:20 em UTC+3) mostra 5001 já fechado (passou das 12:00)
e 5003 ainda não aberto (antes das 21:35). Em UTC o mesmo instante daria 5001 aberto.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row

GAME_TZ = timezone(timedelta(hours=3))  # ponytail: fuso fixo (UTC+3, sem horário de verão); outro fuso vira config
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
    local = now.astimezone(GAME_TZ).time()
    if local < _hour(row["OpenTime"]):
        return BEFORE
    if local < _hour(row["StopTime"]):
        return OPEN
    return CLOSED


def states_msg(templates: GameTemplates, now: datetime) -> pb.WorldBossStateMsg:
    msg = pb.WorldBossStateMsg()
    for row in bosses(templates):
        msg.worldBossInfo.add(campaignId=int(row["CampaignId"]), state=state(row, now))
    return msg
