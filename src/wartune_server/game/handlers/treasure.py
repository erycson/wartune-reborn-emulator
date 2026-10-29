"""Mapa do tesouro, "Lost Treasure" (8744, 8745, 4633, 4634): pelo cliente (``TreasureMapManager``,
``TreasureMapSocketOutManager``, ``TreasureMapModel``, ``TreasureMapGetFrame``/``UseFrame``) e o idioma inglês
(``map.internals.view.treasuremap.*.helpContent``). Regras do operador em ``game_settings.treasure_map`` (migração
0105); estado do personagem no ``TreasureMap`` (contagens do dia) e num ``EventState`` (qualidade da vez e as marcas
de primeira vez).

8744 por ``opType`` (``TreasureMapModel``):

* 1 receber: o mapa ``templateIds[index]`` com o lugar do tesouro no item (``randomSkill1`` = mapa, ``2``/``3`` =
  x/y em pixels: ``analyzeTreasureMap``); conta no dia (``join_tremap_count``) e a qualidade volta à primeira.
* 2 melhorar a qualidade (``refreshType`` = direto à lendária): Berdim's Wine (208050) primeiro, o que faltar a 5
  Balens cada (``sendRefreshTreasureMap``: ``Property3`` do mapa da vez, ou ``treasure_refresh_item``).
* 5 usar o mapa no lugar (o cliente já conferiu a distância; o servidor confere de novo) e 3 escavar já (paga
  ``treasure_imm_battle`` Balens, em qualquer lugar da Cloud City ou da terra dos pets): luta contra o ladrão.
* vencendo, 4634 ("You found the treasure!"); 4 com ``isReward`` confirma: o mapa some e cada um do grupo que
  lutou leva ``Property6`` x Crystal Shard (208028), até ``reward_tremap_count`` por dia.
* 6 só o estado (4633).

8745: reforço de quem é do mesmo grupo (``TreasureMapManager.checkReinforce``) na escavação em curso.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from ...domain.models import BagType, Item, TreasureMap
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import arena as A
from .. import bag, rewards, rules
from ..battle import Battle
from ..builders import login as b
from ..campaign import PET_ISLANDS
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .army import count_quest
from .campaign import S_BATTLE_REPORT, _report, _with_team, player_hero, team_hero
from .player import S_ITEMS, granted, hero_after_fight, hp_pack
from .shop import Charge, place, save_with_mail, send_charge

KEY = "treasure_map"  # game_settings e EventState
S_TREASURE, S_FOUND = 4633, 4634
OP_GET, OP_REFRESH, OP_DIG_NOW, OP_REWARD, OP_USE, OP_INFO = 1, 2, 3, 4, 5, 6
MAP_SON_TYPE = "219"  # os quatro mapas (Uncommon, Rare, Epic, Legendary), NeedGrades 55
WINE, SHARD = 208050, 208028  # TreasureMapModel.COST_TEMPLATE_ID / REWARD_TEMPLATE_ID
WINE_POINTS = 5  # TreasureMapModel.COST_ITEM_TO_POINTS: um vinho vale 5 Balens
TOP = 3  # TreasureMapModel.QUALITY_MAX: índice da lendária
TILE = 20  # px por tile da Cloud City (MapNodeInfos: PosX 142 -> FixX 2850)
RNG = random.Random()


@dataclass
class Dig:
    """Escavação de um dono de mapa: da luta até o 4 com ``isReward``."""

    pos: int  # posição do mapa na mochila
    template_id: int
    mates: list[int] = field(default_factory=list)  # quem lutou junto (grupo e reforços)
    won: bool = False


def dig_of(s: GameSession) -> Dig | None:
    """A escavação gravada no ``EventState`` (chave ``dig``): sobrevive a reinício e desconexão."""
    raw = _data(s).get("dig")
    return Dig(**raw) if raw else None


async def save_dig(s: GameSession, dig: Dig | None) -> None:
    assert s.snapshot is not None
    d = _data(s)
    d["dig"] = asdict(dig) if dig is not None else None
    await s.ctx.characters.save(mj.store(s.snapshot, KEY, d, s.ctx.clock.now()))


def _config(s: GameSession, name: str) -> int:
    row = next(s.ctx.templates.find("ConfigInfos", ConfigName=name), None)
    return int(row["ConfigValue"]) if row else 0


def _book(s: GameSession, now: datetime) -> TreasureMap:
    """O mapa do tesouro do personagem; as contagens do dia zeram na primeira leitura do dia (o idioma: "claimed 5
    times per day", os dois limites)."""
    snap = s.snapshot
    assert snap is not None and snap.character.id is not None
    if not snap.treasure:
        snap.treasure.append(TreasureMap(snap.character.id))
    book = snap.treasure[0]
    if book.day != A.today(now):
        book.day, book.join_count, book.reward_count = A.today(now), 0, 0
    return book


def _maps(s: GameSession) -> list[int]:
    return sorted(int(r["TemplateId"]) for r in s.ctx.templates.find("ItemTempInfos", SonType=MAP_SON_TYPE))


def _data(s: GameSession) -> dict[str, Any]:
    """``index`` (qualidade da vez) e as marcas ``quest``/``get``/``use`` (já melhorou/recebeu/usou: sem elas o
    cliente pisca o botão e abre o guia, ``TreasureMapGetFrame.setBtnEnabled``/``TreasureMapUseFrame.show``)."""
    assert s.snapshot is not None
    return {"index": 0, "quest": False, "get": False, "use": False, **mj.load(s.snapshot, KEY)}


def _state(s: GameSession, book: TreasureMap, op: int = 0) -> pb.PlayerTreasureMsg:
    """(só turco: login.json #36) ``templateIds`` com os quatro mapas e ``index`` o da vez: o
    ``TreasureMapGetFrame`` lê ``templateIds[index]``."""
    d = _data(s)
    return b.complete(
        pb.PlayerTreasureMsg(
            userId=s.player_id, joinCount=book.join_count, rewardCount=book.reward_count, opType=op,
            index=d["index"], templateIds=_maps(s), isFirstQuest=d["quest"], isFirstGet=d["get"],
            isFirstUse=d["use"],
        )
    )  # fmt: skip


def login(s: GameSession) -> None:
    """4633 do login (só turco: login.json #36, nível 56); (dedução) só a partir do nível dos mapas (55), como o
    inglês (as capturas inglesas vão do nível 11 ao 31 e não mandam). Sem captura inglesa acima do 55."""
    snap = s.snapshot
    assert snap is not None
    need = int((s.ctx.templates.get("ItemTempInfos", _maps(s)[0]) or {}).get("NeedGrades", 0))
    if snap.character.grades >= need:
        s.send(S_TREASURE, _state(s, _book(s, s.ctx.clock.now())))
        dig = dig_of(s)
        if dig is not None and dig.won:  # (dedução) tesouro achado antes de cair: o aviso volta
            s.send(S_FOUND)


def _spot(s: GameSession) -> tuple[int, int, int]:
    """Lugar do tesouro: (mapa, x, y) em pixels. TODO(inventado): um NPC da Cloud City sorteado (``FixX``/``FixY``
    do ``MapNodeInfos``: um ponto onde se anda com certeza)."""
    map_id = int(mj.cfg(s, KEY)["mapId"])
    node = RNG.choice(list(s.ctx.templates.find("MapNodeInfos", MapId=str(map_id))))
    return map_id, int(node["FixX"]), int(node["FixY"])


async def _receive(s: GameSession, book: TreasureMap) -> None:
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    d = _data(s)
    tid = _maps(s)[d["index"]]
    # o cliente não tem trava de nível para receber; o item pede NeedGrades (55), e sem isso dava para
    # subir um personagem novo só para pegar mapas e vender (*(dedução)*)
    need = int((s.ctx.templates.get("ItemTempInfos", tid) or {}).get("NeedGrades", 0))
    if snap.character.grades < need:
        s.log.info("8744 mapa recusado", motivo="nível", precisa=need)
        return
    if book.join_count >= _config(s, "join_tremap_count"):
        s.log.info("8744 mapa recusado", motivo="limite do dia")
        return
    book.join_count += 1
    d.update(index=0, get=True)  # (dedução) o próximo mapa recomeça da primeira qualidade
    # mochila cheia: pelo correio. A conta vai no mesmo save do item: sem isso dava para receber, relogar e vender o
    # mapa (1000 de ouro) de novo
    got, letters = place(s, snap, s.player_id, [(tid, 1)], now, binds=True)
    spot = _spot(s)
    for item in got + [i for _, _, chunk in letters for i in chunk]:
        item.random_skill, item.random_skill_2, item.random_skill_3 = spot
    await save_with_mail(s, letters, *got, book, mj.store(snap, KEY, d, now))
    await granted(s, [(tid, 1)], got, rewards.text(s.ctx.templates, [(tid, 1)]))


async def _refresh(s: GameSession, book: TreasureMap, msg: pb.PlayerTreasureMsg) -> None:
    """Op 2. ``refreshType``: direto à lendária. (dedução) as chances vêm de ``Property1``/``Property2`` do mapa da
    vez: ``Property1`` % fica, ``Property2`` % sobe duas, o resto sobe uma (Uncommon 90/5, Rare 50/10, Epic 40/20,
    a lendária 0/0: a única leitura em que as três somam no máximo 100)."""
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    d = _data(s)
    if d["index"] >= TOP or book.join_count >= _config(s, "join_tremap_count"):
        s.log.info("8744 melhora recusada", index=d["index"])
        return
    row = s.ctx.templates.get("ItemTempInfos", _maps(s)[d["index"]]) or {}
    need = _config(s, "treasure_refresh_item") if msg.refreshType else int(row.get("Property3") or 0)
    wine = min(bag.count_of(snap, WINE), need)
    points = (need - wine) * WINE_POINTS
    ledger = (
        cash.pay(snap.character, points, msg.payType, "treasure_map", f"refresh:{d['index']}", now) if points else None
    )
    if points and ledger is None:
        s.log.info("8744 melhora recusada", motivo="sem Balens", precisa=points)
        return
    changed, gone = bag.take(snap, WINE, wine) if wine else ([], [])
    if msg.refreshType:
        d["index"] = TOP
    else:
        r = RNG.randrange(100)
        stay, jump = int(row.get("Property1") or 0), int(row.get("Property2") or 0)
        d["index"] = d["index"] if r < stay else min(TOP, d["index"] + (2 if r < stay + jump else 1))
    d["quest"] = True
    extra = [ledger] if ledger is not None else []
    await s.ctx.characters.save(snap.character, *changed, *extra, mj.store(snap, KEY, d, now), delete=tuple(gone))
    send_charge(s, Charge(ledger=ledger, changed=changed, gone=gone))


def _map_at(s: GameSession, pos: int) -> Item | None:
    assert s.snapshot is not None
    item = bag.at(s.snapshot, BagType.BAG, 0, pos)
    row = s.ctx.templates.get("ItemTempInfos", item.template_id) if item is not None else None
    return item if row is not None and row.get("SonType") == MAP_SON_TYPE else None


def _thief(s: GameSession) -> Mapping[str, Any]:
    """O ladrão de tesouro do nível do jogador: o de maior ``Grades`` até o nível dele (o primeiro abaixo de todos)."""
    assert s.snapshot is not None
    rows = [s.ctx.templates.get("GameHeroTemp", h) or {} for h in mj.cfg(s, KEY)["thieves"]]
    rows = sorted((r for r in rows if r), key=lambda r: int(r["Grades"]))
    fit = [r for r in rows if int(r["Grades"]) <= s.snapshot.character.grades]
    return (fit or rows)[-1]


def _team(s: GameSession) -> list[GameSession]:
    """Os do grupo livre (``FreedomTeam``) na Cloud City, perto (``teamRange`` tiles) e fora de luta: o idioma
    ("make sure your party members are close by")."""
    team, here = s.ctx.teams.of(s.player_id), s.space_pos
    if team is None or here is None:
        return []
    near = int(mj.cfg(s, KEY)["teamRange"])
    out = []
    for pid in team.members:
        o = s.ctx.online.get(pid)
        if o is None or o is s or pid in team.away or o.battle is not None or o.space_pos is None:
            continue
        if max(abs(o.space_pos[0] - here[0]), abs(o.space_pos[1] - here[1])) <= near:
            out.append(o)
    return out


async def _dig(s: GameSession, book: TreasureMap, item: Item) -> None:
    """A luta da escavação: o ladrão (herói NPC, como o chefe dos Wilds em ``monsters.battle``) contra o jogador e o
    grupo perto (heróis copiados, ``campaign._with_team``). Conta a missão 89 para todos ao entrar."""
    c = mj.cfg(s, KEY)
    snap = s.snapshot
    assert snap is not None and snap.leader is not None
    if s.battle is not None or book.reward_count >= _config(s, "reward_tremap_count"):
        s.log.info("8744 escavação recusada", luta=s.battle is not None, premios=book.reward_count)  # TipTxt6
        return
    row = _thief(s)
    hp = max(1, int(row.get("Live") or 1))
    thief = A.npc_hero(livingId=1, side=2, pos=5, tempId=int(row["TemplateId"]), nickName=row.get("TemplateName", ""),
                       grade=int(row.get("Grades") or 0), maxHp=hp, initHp=hp, hp=hp, fightCapacity=0,
                       type=int(row.get("HeroType") or 3), captain=int(row.get("Captain") or 0),
                       res=row.get("ResPath", ""), castTime=6000)  # fmt: skip
    spec: dict[str, Any] = {
        "battleType": int(c["battleType"]), "mapTempId": int(c["mapId"]), "attackModel": 2,
        "battleScene": int(c["battleScene"]), "soldiers": [], "heroes": [thief],
        "player": {"livingId": 2, "pos": 2, "pawnTempId": 0},
    }  # fmt: skip
    team = _team(s)
    if team:
        spec = _with_team(s, spec, team)
    dig = Dig(item.pos, item.template_id, [m.player_id for m in team])
    await save_dig(s, dig)

    def send(code: int, msg: Any) -> None:
        s.send(code, msg)
        for m in team:
            m.send(code, msg)

    async def finished(battle: Battle, won: bool) -> None:
        s.battle, s.hero_sp = None, battle.player_sp
        healed = hero_after_fight(s, battle.player.hp if battle.player is not None else None)
        battle.send(S_BATTLE_REPORT, _report(battle, won, 0))  # o time e os reforços (``join``)
        hp_pack(s, healed)
        now_dig = dig_of(s)  # relido: o 8745 pode ter somado reforços durante a luta
        if won and now_dig is not None:  # TipTxt1: "You found the treasure!"; o 4 com isReward responde
            now_dig.won = True
            await save_dig(s, now_dig)
            s.send(S_FOUND)
        else:  # idioma: "if you are defeated, the map will not be lost"
            await save_dig(s, None)

    s.battle = Battle(spec, player_hero(s, spec), s.ctx.templates, s.ctx.clock, send, finished,
                      settings=s.ctx.world.settings)  # fmt: skip
    s.log.info("batalha do mapa do tesouro", mapa=item.template_id, battle=s.battle.id, time=dig.mates)
    s.battle.start()
    for who in (s, *team):
        await count_quest(who, rules.LOST_TREASURE_CONDITION)


async def _use(s: GameSession, book: TreasureMap, msg: pb.PlayerTreasureMsg, now_pay: bool) -> None:
    """Op 5 (no lugar) e op 3 (escavar já, pago)."""
    snap, now, c = s.snapshot, s.ctx.clock.now(), mj.cfg(s, KEY)
    assert snap is not None
    item = _map_at(s, msg.index)
    if item is None:
        s.log.info("8744 sem mapa na posição", pos=msg.index)
        return
    in_space = s.space_pos is not None
    if now_pay:  # TreasureMapUseFrame.checkScene: Cloud City ou terra dos pets
        if not in_space and not (s.campaign is not None and s.campaign.map_id in PET_ISLANDS):
            s.log.info("8744 escavar já recusado", motivo="cena")  # digBtnAlertTxt2
            return
    else:
        here = s.space_pos
        reach = int(c["digRange"]) * TILE
        if (
            here is None
            or item.random_skill != int(c["mapId"])
            or max(abs(here[0] * TILE - item.random_skill_2), abs(here[1] * TILE - item.random_skill_3)) > reach
        ):
            s.log.info("8744 longe do tesouro", pos=here, alvo=(item.random_skill_2, item.random_skill_3))
            return
    if s.battle is not None or book.reward_count >= _config(s, "reward_tremap_count"):
        s.log.info("8744 escavação recusada", premios=book.reward_count)
        return
    d = _data(s)
    d["use"] = True
    extra: list[object] = []
    if now_pay:
        cost = _config(s, "treasure_imm_battle")
        ledger = cash.pay(snap.character, cost, msg.payType, "treasure_map", f"dig:{item.template_id}", now)
        if ledger is None:
            s.log.info("8744 escavar já recusado", motivo="sem Balens", precisa=cost)
            return
        extra = [snap.character, ledger]
    await s.ctx.characters.save(*extra, mj.store(snap, KEY, d, now))
    if now_pay:
        send_charge(s, Charge(ledger=extra[1]))  # type: ignore[arg-type]
    await _dig(s, book, item)


async def _claim(s: GameSession, book: TreasureMap, msg: pb.PlayerTreasureMsg) -> None:
    """Op 4. ``isReward``: o mapa some e cada um leva o prêmio (o dono do lendário, ``legendaryBonus`` % a mais:
    idioma). Quem já usou os prêmios do dia luta mas não leva (idioma helpContent). (dedução) sem ``isReward`` o
    tesouro fica por ora: o mapa continua na mochila."""
    dig = dig_of(s)
    if dig is None or not dig.won or dig.pos != msg.index:
        s.log.info("8744 sem tesouro achado", pos=msg.index)
        return
    await save_dig(s, None)  # (o _pay_out grava o resto; o EventState já sem a escavação)
    item = _map_at(s, dig.pos)
    if not msg.isReward or item is None or item.template_id != dig.template_id:
        return
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    row = s.ctx.templates.get("ItemTempInfos", dig.template_id) or {}
    base = int(row.get("Property6") or 0)
    legendary = dig.template_id == _maps(s)[TOP]
    bonus = int(mj.cfg(s, KEY)["legendaryBonus"])
    snap.items.remove(item)
    s.send(S_ITEMS, bag.moved([], s.player_id, empty=[item]))
    await _pay_out(s, book, base + (base * bonus // 100 if legendary else 0), delete=(item,))
    for pid in dig.mates:
        o = s.ctx.online.get(pid)
        if o is not None and o.snapshot is not None:
            mate = _book(o, now)
            await _pay_out(o, mate, base)
            o.send(S_TREASURE, _state(o, mate, OP_REWARD))


async def _pay_out(s: GameSession, book: TreasureMap, count: int, delete: tuple[object, ...] = ()) -> None:
    snap = s.snapshot
    assert snap is not None
    if book.reward_count < _config(s, "reward_tremap_count") and count > 0:
        book.reward_count += 1
        drops = [(SHARD, count)]  # idioma helpContent: "Rewards are bound"
        got, letters = place(s, snap, s.player_id, drops, s.ctx.clock.now(), binds=True)
        await save_with_mail(s, letters, *got, book, delete=delete)
        await granted(s, drops, got, rewards.text(s.ctx.templates, drops))
    elif delete:
        await s.ctx.characters.save(delete=delete)


@router.on(8744)
async def treasure_map(s: GameSession, msg: pb.PlayerTreasureMsg) -> None:
    if not mj.cfg(s, KEY):
        s.log.info("8744 sem game_settings.treasure_map")
        return
    book = _book(s, s.ctx.clock.now())
    if msg.opType == OP_GET:
        await _receive(s, book)
    elif msg.opType == OP_REFRESH:
        await _refresh(s, book, msg)
    elif msg.opType in (OP_USE, OP_DIG_NOW):
        await _use(s, book, msg, msg.opType == OP_DIG_NOW)
    elif msg.opType == OP_REWARD:
        await _claim(s, book, msg)
    s.send(S_TREASURE, _state(s, book, msg.opType))


@router.on(8745)
async def reinforce_treasure(s: GameSession, msg: pb.GuildMsg) -> None:
    """Reforço (``checkReinforce``): quem é do mesmo grupo de ``param1`` entra na escavação em curso dele e leva o
    prêmio junto: o herói dele entra na luta em curso (``Battle.join``), e ele na partilha e na missão 89."""
    team, owner = s.ctx.teams.of(s.player_id), s.ctx.online.get(msg.param1)
    dig = dig_of(owner) if owner is not None and owner.snapshot is not None else None
    mine = dig_of(s)
    if (
        team is None
        or owner is None
        or owner is s
        or msg.param1 not in team.members
        or dig is None
        or dig.won
        or owner.battle is None  # escavação gravada sem luta (reinício no meio): nada a reforçar
        or s.player_id in dig.mates
        or s.battle is not None
        or (mine is not None and not mine.won)
    ):
        s.log.info("8745 reforço recusado", alvo=msg.param1)
        return
    assert owner.battle is not None
    if not owner.battle.join(team_hero(owner, s), s):
        s.log.info("8745 reforço recusado", alvo=msg.param1, motivo="luta acabando ou sem lugar")
        return
    dig.mates.append(s.player_id)
    await save_dig(owner, dig)
    await count_quest(s, rules.LOST_TREASURE_CONDITION)
