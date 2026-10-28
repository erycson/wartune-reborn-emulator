"""Chefe do mundo (World Boss): agenda de hoje (4182) e a leitura dos templates.

Os chefes são as campanhas com ``Types=1`` (5001 e 5003). O cliente guarda todo campanha com
``Types>=1`` (menos 5 e 9) e derruba com um id fora desse dicionário, então o 4182 manda só estes.
Os horários (``OpenTime``/``StopTime``) são do jogo no fuso do servidor (``gameday.GAME_TZ``). O inglês segue o
Pacífico: o 4182 da captura inglesa (#103, 18:24 no Pacífico) mostra 5001 já fechado (passou das 12:00) e 5003
ainda não aberto (antes das 21:35).
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import UTC, datetime, time, timedelta

from ..domain import gameday
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row

OPEN, BEFORE, CLOSED = 0, 1, 2  # WorldBossInfoStateMsg.state: aberto, ainda não abriu hoje, encerrado hoje
# (visto) oficial 27/10 (5001, OpenTime 11:35) e 26/10 (5003, 21:00), hora do servidor = captura + ~6 s (o sendDate
# do correio): o 4381 leftTime 15/10/5 sai 14/9/4 min antes de nascer, o de 5 junto do 4182 aberto; "will appear in
# N minutes" N min antes; nasce 1 min depois do OpenTime (11:36, 21:01)
SPAWN_AFTER = timedelta(minutes=1)
NOTICES, COUNTDOWN = (15, 10, 5), (3, 2, 1)
OPEN_NOTICE = 5  # o aviso que abre o mapa
SPAWN_GAP = timedelta(minutes=OPEN_NOTICE - 1)  # do mapa aberto ao nascimento


def spawn_at(row: Row, now: datetime) -> datetime:
    """Quando o chefe nasce hoje (UTC)."""
    day = gameday.local(now)
    h = _hour(row["OpenTime"])
    return day.replace(hour=h.hour, minute=h.minute, second=0, microsecond=0).astimezone(UTC) + SPAWN_AFTER


def _notice_at(row: Row, now: datetime, left: int) -> datetime:
    return spawn_at(row, now) - timedelta(minutes=left - 1)  # o de 5 sai SPAWN_GAP antes


def spawned(row: Row, now: datetime) -> bool:
    return now >= spawn_at(row, now)


def events(row: Row, since: datetime, now: datetime) -> list[tuple[str, int]]:
    """Os marcos de hoje em ``(since, now]``, na ordem: ``notice`` (4381), ``countdown`` (N min) e ``spawn``."""
    out = [(t, kind, n) for kind, n, t in (
        *(("notice", n, _notice_at(row, now, n)) for n in NOTICES),
        *(("countdown", n, spawn_at(row, now) - timedelta(minutes=n)) for n in COUNTDOWN),
        ("spawn", 0, spawn_at(row, now)),
    ) if since < t <= now]  # fmt: skip
    return [(kind, n) for _, kind, n in sorted(out)]


def boss(templates: GameTemplates, campaign_id: int) -> Row | None:
    return next(templates.find("Campaigns", CampaignId=campaign_id, Types=1), None)


def bosses(templates: GameTemplates) -> list[Row]:
    return sorted(templates.find("Campaigns", Types=1), key=lambda r: int(r["CampaignId"]))


def _hour(text: str) -> time:
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


def state(row: Row, now: datetime) -> int:
    """Estado de hoje: aberto do aviso de 5 min (o mapa abre antes do chefe nascer) até ``StopTime``.

    ponytail: janela que cruza a meia-noite não existe nos templates; não é tratada.
    """
    opened, stop = window(row, now)
    if now < opened:
        return BEFORE
    if now < stop:
        return OPEN
    return CLOSED


def window(row: Row, now: datetime) -> tuple[datetime, datetime]:
    """Abertura do mapa e fechamento de hoje (no fuso do jogo), em UTC."""
    h = _hour(row["StopTime"])
    stop = gameday.local(now).replace(hour=h.hour, minute=h.minute, second=0, microsecond=0)
    return _notice_at(row, now, OPEN_NOTICE), stop.astimezone(UTC)


def states(templates: GameTemplates, now: datetime, defeated: Collection[int] = ()) -> dict[int, int]:
    """Estado de cada chefe; ``defeated`` (morto na janela de hoje) aparece encerrado."""
    return {int(row["CampaignId"]): CLOSED if int(row["CampaignId"]) in defeated else state(row, now)
            for row in bosses(templates)}  # fmt: skip


def states_msg(templates: GameTemplates, now: datetime, defeated: Collection[int] = ()) -> pb.WorldBossStateMsg:
    msg = pb.WorldBossStateMsg()
    for campaign_id, value in states(templates, now, defeated).items():
        msg.worldBossInfo.add(campaignId=campaign_id, state=value)
    return msg
