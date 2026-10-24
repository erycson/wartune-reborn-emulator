"""Arquivos de ranking que o cliente baixa do site do jogo (``TEMPLATE_PATH``, o espelho do s134 no Apache).

O ``challengeorder.xml`` do "Hero Rankings" do coliseu (``HeroRankFrame``) e o ``fight.xml`` do ranking de poder
(``SortController``: aba 2 do ranking e os títulos do ``ColosseumSelfView``), os dois no loader tipo 5 (zlib). Sem
``ranking_xml_dir`` o servidor não grava nada e o site fica com o que tiver (o espelho oficial não tem ``fight.xml``).
"""

from __future__ import annotations

import asyncio
import zlib
from collections.abc import Callable, Mapping
from pathlib import Path
from xml.sax.saxutils import quoteattr

import structlog

from ..domain.models import ArenaRank, Character, EventState
from ..domain.repositories import UnitOfWork
from ..services.characters import CharacterService
from ..services.clock import Clock
from . import events as ev
from .guild import Guilds

log = structlog.get_logger(__name__)

HERO_TOP = 20  # o challengeorder.xml do espelho oficial tem 20 linhas
FIGHT_TOP = 100  # ponytail: tamanho do fight.xml sem arquivo oficial para conferir; o SortModel pagina o que vier
VIP_KEY, VIP_TYPE_KEY = "vip", "vip:type"  # event_states do VIP (handlers/vip.py)


async def challenge_order(characters: CharacterService, guilds: Guilds, server_id: int, clock: Clock) -> bytes:
    """``<list><item userId nickName job grades fightingCapacity consortiaName IsVip VipType order curRank
    direction/></list>`` como o arquivo do oficial: ``curRank`` é a posição no coliseu e ``order`` a do jogador por EXP
    no servidor (o ``HeroRankFrame`` lê ``order`` como ``gpOrder``). Robôs do coliseu não têm personagem e ficam fora.
    ``direction`` vai 0 como no arquivo do oficial (o cliente não lê)."""

    async def query(uow: UnitOfWork) -> tuple[list[ArenaRank], list[Character], list[EventState], list[int]]:
        ranks = await uow.arena.ranks(server_id, 1, HERO_TOP)
        chars = await uow.characters.by_ids([r.character_id for r in ranks])
        vips = await uow.events.by_prefix(server_id, VIP_KEY)
        orders = [await uow.characters.gp_order(server_id, c.total_gp) for c in chars]
        return ranks, chars, vips, orders

    ranks, chars, vips, orders = await characters.read(query)
    by_id = {c.id: (c, o) for c, o in zip(chars, orders, strict=True)}
    vip_of = vips_of(vips, clock)
    rows = []
    for r in ranks:
        if (found := by_id.get(r.character_id)) is None:
            continue
        c, order = found
        vip, kind = vip_of(r.character_id)
        attrs = {
            "userId": c.id,
            "nickName": c.nickname or "",
            "job": c.job,
            "grades": c.grades,
            "fightingCapacity": c.fighting_capacity,
            "consortiaName": _guild_name(guilds, r.character_id),
            "IsVip": str(vip).lower(),
            "VipType": kind,
            "order": order,
            "curRank": r.rank,
            "direction": 0,
        }
        rows.append(_row("item", attrs))
    return _xml("".join(rows))


async def fight_order(characters: CharacterService, guilds: Guilds, server_id: int, clock: Clock) -> bytes:
    """``<list><info createDate/><PlayerFight .../></list>`` lido por ``SortController.read``: ``orderId`` e ``gpOrde``
    (fightCapacityOrder) são a posição por poder, ``CurrentOrder`` a por EXP; ``job`` é o template do líder (com ``Job``
    vazio o cliente cai nele) e dá a classe dos títulos do coliseu. O poder é o ``fighting_capacity`` gravado na saída
    do jogo."""

    async def query(uow: UnitOfWork) -> tuple[list[Character], list[EventState], list[int]]:
        chars = await uow.characters.strongest(server_id, FIGHT_TOP)
        vips = await uow.events.by_prefix(server_id, VIP_KEY)
        return chars, vips, [await uow.characters.gp_order(server_id, c.total_gp) for c in chars]

    chars, vips, orders = await characters.read(query)
    vip_of = vips_of(vips, clock)
    rows = [_row("info", {"createDate": clock.now().strftime("%Y-%m-%d %H:%M:%S")})]
    for pos, (c, order) in enumerate(zip(chars, orders, strict=True), 1):
        vip, kind = vip_of(c.id or 0)
        attrs = {
            "orderId": pos,
            "userid": c.id,
            "nikcName": c.nickname or "",  # sic: os nomes com erro são os que o cliente lê
            "job": c.job,
            "grades": c.grades,
            "CurrentGp": c.total_gp,
            "fightCapaity": c.fighting_capacity,
            "ConsortiaName": _guild_name(guilds, c.id or 0),
            "IsVip": str(vip).lower(),
            "VipType": kind,
            "gpOrde": pos,
            "CurrentOrder": order,
        }
        rows.append(_row("PlayerFight", attrs))
    return _xml("".join(rows))


def vips_of(vips: list[EventState], clock: Clock) -> Callable[[int], tuple[bool, int]]:
    """``(IsVip, VipType)`` por personagem: VIP vencido vai ``false`` e tipo 0."""
    now = clock.now()
    ends = {e.character_id: e.text for e in vips if e.key == VIP_KEY}
    kinds = {e.character_id: e.value for e in vips if e.key == VIP_TYPE_KEY}

    def of(character_id: int) -> tuple[bool, int]:
        end = ends.get(character_id)
        vip = bool(end) and ev.parse_time(end or "") > now
        return vip, kinds.get(character_id, 0) if vip else 0

    return of


def _guild_name(guilds: Guilds, character_id: int) -> str:
    mine = guilds.of(character_id)
    return mine[0].name if mine else ""


def _row(tag: str, attrs: Mapping[str, object]) -> str:
    return f"  <{tag} " + " ".join(f"{k}={quoteattr(str(v))}" for k, v in attrs.items()) + "/>\n"


def _xml(rows: str) -> bytes:
    text = '<?xml version="1.0" encoding="UTF-8"?>\n\n<list>\n' + rows + "</list>\n"
    return zlib.compress(text.encode("utf-8"))


def write(folder: Path, name: str, body: bytes) -> None:
    """Grava por cima de uma cópia temporária: o Apache nunca serve o arquivo pela metade."""
    tmp = folder / f".{name}.tmp"
    tmp.write_bytes(body)
    tmp.replace(folder / name)


async def run(
    folder: Path, characters: CharacterService, guilds: Guilds, server_id: int, clock: Clock, every: float
) -> None:
    """Loop dos rankings (``app.py`` cancela ao desligar). A primeira rodada sai já; um arquivo que falha é
    registrado sem impedir o outro, e a próxima rodada tenta de novo."""
    files = (("challengeorder.xml", challenge_order), ("fight.xml", fight_order))
    while True:
        for name, build in files:
            try:
                write(folder, name, await build(characters, guilds, server_id, clock))
            except Exception:
                log.exception("ranking falhou", arquivo=name, pasta=str(folder), proxima_em_s=every)
        await asyncio.sleep(every)
