"""Títulos (``AppellInfos``) e o 4484 ``AppellsMsg``.

(visto) em todas as capturas inglesas o 4484 traz 221 dos 225 títulos: os de ``Job`` 0 e os da classe do
jogador (a maga não recebe Top Archer/Top Knight/Warlord/Eagle Eye), na ordem de um HashMap Java de 1024 posições
(``id % 1024``, depois o id), todos com ``isGet`` falso e ``validDate`` 2000-01-01. O ``value`` é o progresso da
condição: só o 30 ("Love Thy Guild", CondtionType 10) saiu diferente de 0 no inglês (10, 11, 200, 240 na 171155,
a contribuição da guilda); o turco mostra 384 nos de Honor (CondtionType 7, o geste).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime

from ..domain.models import Character, EventState, PlayerSnapshot
from ..protocol.messages import wartune_pb2 as pb
from ..templates.repository import GameTemplates, Row
from . import events as ev
from . import maze as mz
from . import rules

HASH_BUCKETS = 1024
NO_DATE = "2000-01-01 00:00:00"
HONOR, GUILD_OFFER, OWN_ITEM = "7", "10", "22"  # AppellInfos.CondtionType
# contadores (Descript do template: "Accumulated 1000 Arena wins", "Cleared Lvl. 100 of the Forgotten Catacombs"...):
# o progresso é o número e o título sai com ``progress >= Para``
ARENA_WINS, FIELD_KILLS, GUILD_WAR_FIRST, ASTRAL_10, CATACOMBS, NECROPOLIS = "2", "3", "4", "6", "8", "9"
COUNTED = (HONOR, GUILD_OFFER, ARENA_WINS, FIELD_KILLS, GUILD_WAR_FIRST, ASTRAL_10, CATACOMBS, NECROPOLIS)
# posições de ranking ("#1 in Battle Rating Rankings", "Top 10 in Arena Rankings", "#2 in Fishing Points Ranking"): o
# progresso é a posição (0 = fora) e o título sai com ``0 < posição <= Para``; 26/40/41 pedem a posição exata (1, 2, 3)
POWER, POWER_ARCHER, POWER_KNIGHT, POWER_MAGE, ARENA_RANK, CROSS = "15", "16", "17", "18", "14", "21"
FISH, GEMS = "40", "41"
RANKED = (POWER, POWER_ARCHER, POWER_KNIGHT, POWER_MAGE, ARENA_RANK, CROSS)
EXACT = (FISH, GEMS)
OWN_ONE = ("39", "202")  # ter o item/montaria ``Para`` ("Collect the mount Kitty UFO to activate the title")
OWN_SET = (OWN_ITEM, "203")  # ter todos os itens de ``Para``
# eventos dos contadores sem coluna própria (EventState.value, para sempre)
GUILD_WAR_WINS, GUILD_WAR_LOSSES = "guildwar:win", "guildwar:lose"  # matchWin/matchFailed da lista de membros
KEYS = {ARENA_WINS: "title:arena_wins", FIELD_KILLS: "title:field_kills", GUILD_WAR_FIRST: GUILD_WAR_WINS}


def count(snap: PlayerSnapshot, kind: str, now: datetime, n: int = 1) -> EventState:
    """+``n`` no contador de título ``kind`` (``KEYS``); devolve a linha para gravar."""
    st = ev.state(snap, KEYS[kind], now)
    st.value, st.updated_at = st.value + n, now
    return st


def counters(snap: PlayerSnapshot) -> dict[str, int]:
    """O progresso das condições contadas que vêm do próprio jogador (sem ranking)."""
    out = {k: st.value for k, key in KEYS.items() if (st := ev.peek(snap, key)) is not None}
    out[CATACOMBS], out[NECROPOLIS] = mz.record(snap, mz.CATACOMBS), mz.record(snap, mz.NECROPOLIS)
    out[ASTRAL_10] = sum(st.grade >= 10 for st in snap.stars)  # "Own a Lvl. 10 Astral"
    return out


def _progress(c: Character, row: Row, extra: Mapping[str, int]) -> int:
    """TODO(inventado): as condições sem contador aqui (Honor/Charm/montaria em ranking, chefe do mundo, guerra de
    classes, Sylph...) vão 0; o inglês só mostrou o valor da contribuição."""
    if row["CondtionType"] == HONOR:
        return c.geste
    if row["CondtionType"] == GUILD_OFFER:
        return c.consortia_total_offer
    return extra.get(row["CondtionType"], 0)


def _got(row: Row, progress: int, owned: Collection[int]) -> bool:
    """(dedução do template) ``Para`` é o limiar das condições contadas ("Have at least 2000 Honor", "Guild Contribution
    of more than 100,000"), a posição máxima nos rankings ("Top 10") e, no 22, os itens que é preciso ter ("Has both
    Lover's Hat and Lover's Gown")."""
    para, kind = row.get("Para") or "", row["CondtionType"]
    if kind in COUNTED:
        return progress >= int(para)
    if kind in RANKED:
        return 0 < progress <= int(para)
    if kind in EXACT:
        return progress == int(para)
    if kind in OWN_SET:
        return all(int(t) in owned for t in para.split(",") if t)
    if kind in OWN_ONE:
        return int(para) in owned
    return False


def appells_msg(
    c: Character, templates: GameTemplates, owned: Collection[int] = (), extra: Mapping[str, int] | None = None
) -> pb.AppellsMsg:
    """``owned``: os templates dos itens do jogador (condição 22); ``extra``: o progresso por ``CondtionType``
    (``counters`` e as posições de ``handlers/events.title_ranks``)."""
    job = rules.job_type(c.job)
    rows = [r for r in templates.rows("AppellInfos") if int(r.get("Job") or 0) in (0, job)]
    rows.sort(key=lambda r: (int(r["TemplateId"]) % HASH_BUCKETS, int(r["TemplateId"])))
    msg = pb.AppellsMsg()
    for r in rows:
        progress = _progress(c, r, extra or {})
        # TODO(inventado): validDate de título ganho com ``Time`` (o inglês só mostrou títulos não ganhos)
        msg.appells.add(
            appellId=int(r["TemplateId"]), isGet=_got(r, progress, owned), value=str(progress), validDate=NO_DATE
        )
    return msg


def item_checks(templates: GameTemplates) -> int:
    """Quantos 4484 vão depois de um item ganho: (visto) 9 seguidos em toda a sessão inglesa (153200 #207-#215,
    231733 #266-#274), os 9 títulos de ``CondtionType`` 22 (ter o item ``Para``); o turco, com mais desses, manda 11."""
    return sum(r["CondtionType"] == OWN_ITEM for r in templates.rows("AppellInfos"))
