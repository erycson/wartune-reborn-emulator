"""Arquivos de ranking que o cliente baixa do site do jogo (``TEMPLATE_PATH``, o espelho do s134 no Apache).

O ``challengeorder.xml`` do "Hero Rankings" do coliseu (``HeroRankFrame``) e o ``fight.xml`` do ranking de poder
(``SortController``: aba 2 do ranking e os títulos do ``ColosseumSelfView``) e o ``gemmaze.xml`` do ranking semanal do
labirinto de gemas (``GemMazeControler.loadGemMazeOrderData``), todos no loader tipo 5 (zlib). Sem
``ranking_xml_dir`` o servidor não grava nada e o site fica com o que tiver (o espelho oficial não tem ``fight.xml``).
"""

from __future__ import annotations

import asyncio
import zlib
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import quoteattr

import structlog

from ..domain.models import ArenaRank, Character, EventState
from ..domain.repositories import UnitOfWork
from ..services.characters import CharacterService
from ..services.clock import Clock
from . import arena_grupo as ag
from . import events as ev
from . import fishing as fs
from . import gemmaze as gm
from .guild import Guilds

log = structlog.get_logger(__name__)

HERO_TOP = 20  # o challengeorder.xml do espelho oficial tem 20 linhas
FIGHT_TOP = 100  # ponytail: tamanho do fight.xml sem arquivo oficial para conferir; o SortModel pagina o que vier
VIP_KEY, VIP_TYPE_KEY = "vip", "vip:type"  # event_states do VIP (handlers/vip.py)
GEM_KEY = "gemmaze"  # event_state do tabuleiro (handlers/gemmaze.py)
# shortcut: tamanho do gemmaze.xml sem arquivo oficial com linhas (o do espelho vem vazio); subir se o oficial mostrar
GEM_TOP = 100


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


def gem_weeks(states: list[EventState], now: datetime) -> list[tuple[int, gm.Game]]:
    """Os tabuleiros por pontos da semana, do maior ao menor (renovados para agora: semana nova zera)."""
    out = []
    for e in states:
        if e.key == GEM_KEY and e.text:
            game = gm.Game.load(e.text)
            gm.refresh(game, now)
            out.append((e.character_id, game))
    out.sort(key=lambda x: (-x[1].week, x[0]))
    return out


def gem_position(states: list[EventState], character_id: int, now: datetime) -> int:
    """``scoreOrder``: 1 + quantos têm mais pontos na semana (dedução: o personagem novo inglês, com 0, saiu 133 no
    oficial_encantar; o turco ficou em 1771 a sessão toda, então a posição não muda a cada troca)."""
    games = gem_weeks(states, now)
    mine = next((g.week for c, g in games if c == character_id), 0)
    return 1 + sum(g.week > mine for _, g in games)


async def gem_order(characters: CharacterService, guilds: Guilds, server_id: int, clock: Clock) -> bytes:
    """``<GemMazeScores><GemMazeScore UserId Job NickName Score ConsortiaName Grades GemMazeGrades Order Index
    FightingCapacity IsVip VipType/></GemMazeScores>`` (raiz do espelho; os atributos são os que
    ``GemMazeControler`` lê). ``Score`` são os pontos da semana (o ``GemMazeSortFrame`` mostra o ``weekScore`` do
    jogador ao lado); só entra quem pontuou. ``Index`` vai igual a ``Order`` (dedução: o cliente não lê)."""

    async def query(uow: UnitOfWork) -> tuple[list[tuple[int, gm.Game]], list[Character], list[EventState]]:
        states = await uow.events.by_prefix(server_id, GEM_KEY)
        games = [x for x in gem_weeks(states, clock.now()) if x[1].week > 0][:GEM_TOP]
        chars = await uow.characters.by_ids([c for c, _ in games])
        return games, chars, await uow.events.by_prefix(server_id, VIP_KEY)

    games, chars, vips = await characters.read(query)
    by_id = {c.id: c for c in chars}
    vip_of = vips_of(vips, clock)
    rows = []
    for pos, (cid, game) in enumerate(games, 1):
        if (c := by_id.get(cid)) is None:
            continue
        vip, kind = vip_of(cid)
        attrs = {
            "UserId": cid,
            "Job": c.job,
            "NickName": c.nickname or "",
            "Score": game.week,
            "ConsortiaName": _guild_name(guilds, cid),
            "Grades": c.grades,
            "GemMazeGrades": game.level,
            "Order": pos,
            "Index": pos,
            "FightingCapacity": c.fighting_capacity,
            "IsVip": str(vip).lower(),
            "VipType": kind,
        }
        rows.append(_row("GemMazeScore", attrs))
    return _xml("".join(rows), "GemMazeScores")


async def fish_order(characters: CharacterService, guilds: Guilds, server_id: int, clock: Clock) -> bytes:
    """``<FishScores><FishScore UserId NickName Job Grades FightingCapacity ConsortiaName IsVip VipType Order Score
    FishGrades/></FishScores>`` como o ``fish.xml`` do espelho oficial (``FishControler.loadFishOrderData``);
    ``Score`` são os pontos da semana; quem pescou e está com 0 na semana vai no fim, como no oficial."""

    async def query(uow: UnitOfWork) -> tuple[list[tuple[int, fs.Fisher]], list[Character], list[EventState]]:
        ranked = fs.weeks(await uow.events.by_prefix(server_id, fs.KEY), clock.now(), zeros=True)[:GEM_TOP]
        chars = await uow.characters.by_ids([c for c, _ in ranked])
        return ranked, chars, await uow.events.by_prefix(server_id, VIP_KEY)

    ranked, chars, vips = await characters.read(query)
    by_id = {c.id: c for c in chars}
    vip_of = vips_of(vips, clock)
    rows = []
    for pos, (cid, f) in enumerate(ranked, 1):
        if (c := by_id.get(cid)) is None:
            continue
        vip, kind = vip_of(cid)
        attrs = {
            "UserId": cid,
            "NickName": c.nickname or "",
            "Job": c.job,
            "Grades": c.grades,
            "FightingCapacity": c.fighting_capacity,
            "ConsortiaName": _guild_name(guilds, cid),
            "IsVip": str(vip).lower(),
            "VipType": kind,
            "Order": pos,
            "Score": f.score,
            "FishGrades": f.level,
        }
        rows.append(_row("FishScore", attrs))
    return _xml("".join(rows), "FishScores")


async def cross_order(characters: CharacterService, guilds: Guilds, server_id: int, clock: Clock) -> bytes:
    """``cross/crossscore.xml`` do ``PvpHeroFrame``: ``<list><info createDate/><CrossScoreTotalAdd .../></list>``
    com os atributos do ``SortController.read`` (``orderId``, ``userid``, ``nikcName``, ``weekScore``...); o
    cliente mostra os 20 primeiros. ``weekScore`` = pontos da arena em grupo (``game/arena_grupo.py``).
    shortcut: o período vem do padrão "week" (o loop não tem o game_settings); passar a config se ``reset`` mudar."""

    async def query(uow: UnitOfWork) -> tuple[list[tuple[int, int]], list[Character], list[EventState]]:
        ranked = ag.ranked(await uow.events.by_prefix(server_id, ag.KEY), clock.now(), {})[:HERO_TOP]
        chars = await uow.characters.by_ids([c for c, _ in ranked])
        return ranked, chars, await uow.events.by_prefix(server_id, VIP_KEY)

    ranked, chars, vips = await characters.read(query)
    by_id = {c.id: c for c in chars}
    vip_of = vips_of(vips, clock)
    rows = [_row("info", {"createDate": clock.now().strftime("%Y-%m-%d %H:%M:%S")})]
    for pos, (cid, score) in enumerate(ranked, 1):
        if (c := by_id.get(cid)) is None:
            continue
        vip, kind = vip_of(cid)
        attrs = {
            "orderId": pos,
            "userid": cid,
            "nikcName": c.nickname or "",
            "job": c.job,
            "grades": c.grades,
            "fightCapaity": c.fighting_capacity,
            "ConsortiaName": _guild_name(guilds, cid),
            "IsVip": str(vip).lower(),
            "VipType": kind,
            "weekScore": score,
            "serverId": server_id,
        }
        rows.append(_row("CrossScoreTotalAdd", attrs))
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


def _xml(rows: str, root: str = "list") -> bytes:
    text = f'<?xml version="1.0" encoding="UTF-8"?>\n\n<{root}>\n' + rows + f"</{root}>\n"
    return zlib.compress(text.encode("utf-8"))


def write(folder: Path, name: str, body: bytes) -> None:
    """Grava por cima de uma cópia temporária: o Apache nunca serve o arquivo pela metade."""
    target = folder / name
    target.parent.mkdir(parents=True, exist_ok=True)  # cross/crossscore.xml fica numa subpasta
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_bytes(body)
    tmp.replace(target)


async def run(
    folder: Path, characters: CharacterService, guilds: Guilds, server_id: int, clock: Clock, every: float
) -> None:
    """Loop dos rankings (``app.py`` cancela ao desligar). A primeira rodada sai já; um arquivo que falha é
    registrado sem impedir o outro, e a próxima rodada tenta de novo."""
    files = (
        ("challengeorder.xml", challenge_order),
        ("fight.xml", fight_order),
        ("gemmaze.xml", gem_order),
        ("fish.xml", fish_order),
        ("cross/crossscore.xml", cross_order),
    )
    while True:
        for name, build in files:
            try:
                write(folder, name, await build(characters, guilds, server_id, clock))
            except Exception:
                log.exception("ranking falhou", arquivo=name, pasta=str(folder), proxima_em_s=every)
        await asyncio.sleep(every)
