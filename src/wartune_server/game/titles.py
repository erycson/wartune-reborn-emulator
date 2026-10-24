"""Títulos (``AppellInfos``) e o 4484 ``AppellsMsg``.

(visto) em todas as capturas inglesas o 4484 traz 221 dos 225 títulos: os de ``Job`` 0 e os da classe do
jogador (a maga não recebe Top Archer/Top Knight/Warlord/Eagle Eye), na ordem de um HashMap Java de 1024 posições
(``id % 1024``, depois o id), todos com ``isGet`` falso e ``validDate`` 2000-01-01. O ``value`` é o progresso da
condição: só o 30 ("Love Thy Guild", CondtionType 10) saiu diferente de 0 no inglês (10, 11, 200, 240 na 171155,
a contribuição da guilda); o turco mostra 384 nos de Honor (CondtionType 7, o geste).
"""

from __future__ import annotations

from ..domain.models import Character
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import rules

HASH_BUCKETS = 1024
NO_DATE = "2000-01-01 00:00:00"
HONOR, GUILD_OFFER, OWN_ITEM = "7", "10", "22"  # AppellInfos.CondtionType


def _progress(c: Character, row: Row) -> int:
    # TODO(inventado): as outras condições (vitórias na arena, andares do labirinto, rankings...) vão 0 até o
    # servidor contar cada uma; o inglês só mostrou o valor da contribuição
    if row["CondtionType"] == HONOR:
        return c.geste
    if row["CondtionType"] == GUILD_OFFER:
        return c.consortia_total_offer
    return 0


def appells_msg(c: Character, templates: GameTemplates) -> pb.AppellsMsg:
    job = rules.job_type(c.job)
    rows = [r for r in templates.rows("AppellInfos") if int(r.get("Job") or 0) in (0, job)]
    rows.sort(key=lambda r: (int(r["TemplateId"]) % HASH_BUCKETS, int(r["TemplateId"])))
    msg = pb.AppellsMsg()
    for r in rows:
        msg.appells.add(appellId=int(r["TemplateId"]), isGet=False, value=str(_progress(c, r)), validDate=NO_DATE)
    return msg


def item_checks(templates: GameTemplates) -> int:
    """Quantos 4484 vão depois de um item ganho: (visto) 9 seguidos em toda a sessão inglesa (153200 #207-#215,
    231733 #266-#274), os 9 títulos de ``CondtionType`` 22 (ter o item ``Para``); o turco, com mais desses, manda 11."""
    return sum(r["CondtionType"] == OWN_ITEM for r in templates.rows("AppellInfos"))
