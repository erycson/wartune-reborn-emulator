"""Chefe do mundo (Dünya Boss): agenda de hoje (4182) e a leitura dos templates.

Os chefes são as campanhas com ``Types=1`` (5001 e 5003). O cliente guarda todo campanha com
``Types>=1`` (menos 5 e 9) e derruba com um id fora desse dicionário, então o 4182 manda só estes.
Os horários (``OpenTime``/``StopTime``) são do jogo no fuso do servidor (``GAME_TZ``). No turco era UTC+3: a
captura de 4182 em ``replay_packets.json`` (pacotes 78 -> 102, 12:20 em UTC+3) mostra 5001 já fechado (passou das 12:00)
e 5003 ainda não aberto (antes das 21:35). Em UTC o mesmo instante daria 5001 aberto.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row


def parse_timezone(text: str) -> tzinfo:
    """``"+03:00"``, ``"UTC-7"`` (deslocamento fixo) ou um nome IANA (``"America/Los_Angeles"``, com horário
    de verão; no Windows vem do pacote ``tzdata``)."""
    fixed = re.fullmatch(r"(?:UTC)?([+-])(\d{1,2})(?::?(\d{2}))?", text.strip())
    if fixed is None:
        return ZoneInfo(text.strip())
    sign = -1 if fixed.group(1) == "-" else 1
    return timezone(sign * timedelta(hours=int(fixed.group(2)), minutes=int(fixed.group(3) or 0)))


# Fuso do jogo (horários dos chefes, createDate das minas, relógio dos chefes do mapa). Vem de
# ``Settings.game_timezone`` (WARTUNE_GAME_TIMEZONE) na subida (``set_timezone`` em ``build_services``).
# O oficial inglês segue o horário do Pacífico (troca PDT/PST); as capturas são do turco (UTC+3).
GAME_TZ: tzinfo = parse_timezone("America/Los_Angeles")


def set_timezone(text: str) -> None:
    global GAME_TZ
    GAME_TZ = parse_timezone(text)


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
