"""Sky Trails (SinglePass): 100 fases em 10 áreas, chefe de cada fase, avaliação D..S e prêmios.

Cliente: ``SinglePassManager``, ``SinglePassSocketOutManager``, ``SinglePassModel`` e o idioma
(``singlepass.view.SinglePassHelpFrame.helpContent``, ``managers.SinglePassManager.TipsTxt01-04``).

* 8753/8755 com ``ChallengeMsg.type`` 0 (o 1 é o Gods Descent: ``tollgate`` despacha): estado (4552) e luta com a
  fase ``tarUserId``. A fase é o ``CampaignDataInfo`` da campanha 40001 com ``Param1`` = índice; o chefe é o
  ``HeroIds`` (``GameHeroTemp``). Só abre a próxima (``maxIndex`` + 1, TipsTxt02) e a fase com S (avaliação 5,
  ``JUDGE_MAX``) não luta mais (TipsTxt03).
* ``SinglePass_Count`` (ConfigInfo, ``SinglePassModel.maxCount``) lutas por dia; passado isso, cada luta gasta um
  3140001 (``PROP_TEMPLATE_ID``, TipsTxt01).
* Vencer pela primeira vez: ``BossReward`` Type 0 da fase (``Floor`` = índice, ``SinglePassCardItemView``); a
  primeira S: Type 2 ("S Assessment Bonus Rewards").
* 8637: área toda feita (``maxIndex`` == área * 10, TipsTxt04) dá o ``AreaReward`` da área e abre a próxima;
  ``areaReward`` é a lista das áreas já pagas (``SinglePassModel.initFloors``).
* 8638: Heaven Horn (3150001): ``maxIndex / 5 * 2 - itemCount`` (``SinglePassManager``, ``bugleCount`` 2).
  O Wishing Wall (8639/8640) não está aqui.
* Cada luta conta na atividade 113 (``FunnyType.SINGLEPASS_TIMES_TYPE``).

Estado do jogador: JSON no ``EventState`` ``singlepass``.
"""

from __future__ import annotations

from typing import Any

from ...domain import gameday
from ...protocol.messages import wartune_pb2 as pb
from ...templates.repository import GameTemplates, Row
from .. import arena as A
from .. import events as ev
from .. import outer_city as oc
from .. import rewards
from ..battle import Battle
from ..builders import login as b
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from .campaign import CAMPAIGN_SCENE, S_BATTLE_REPORT, _report, player_hero
from .player import S_ITEMS, hero_after_fight, hp_pack

S_SINGLE_PASS = 4552
KEY = "singlepass"
CAMPAIGN = 40001  # SinglePassModel.CAMPAIGN_TEMPLATE_ID
BATTLE_TYPE = 293  # BattleResultHandler: volta ao Sky Trails / abre o SinglePassVicotyResultView
PROP, BUGLE = 3140001, 3150001  # SinglePassModel.PROP_TEMPLATE_ID / BUGLE_TEMPLATE_ID
PER_AREA, AREAS, JUDGE_MAX, BUGLES = 10, 10, 5, 2  # SinglePassModel: TOLLGATE_PER_FLOOR, MAX_FLOOR, JUDGE_MAX, 2
BOSS_LIVING = 1


def stage(templates: GameTemplates, campaign: int, index: int) -> Row | None:
    """``CampaignDataInfo`` da fase (``GodArriveTemplateCate.getGodArriveData``: CampaignId e Param1)."""
    return next(templates.find("CampaignData", CampaignId=campaign, Param1=index), None)


def boss_row(templates: GameTemplates, row: Row) -> Row:
    hero_id = int(str(row.get("HeroIds", "")).split(",")[0] or 0)
    return templates.get("GameHeroTemp", hero_id) or {}


def boss_spec(s: GameSession, hero: Row, hp: int, battle_type: int) -> dict[str, Any]:
    """Luta com o chefe (herói NPC type 3, como o chefe do mundo em ``worldboss.battle_spec``) contra as tropas e o
    herói do jogador; ``hp`` é a vida com que ele começa (``maxHp`` = ``Live``)."""
    snap = s.snapshot
    assert snap is not None
    live = max(1, int(hero.get("Live") or 1))
    soldiers, pawn_tpl = oc.army_soldiers(snap, s.ctx.templates)
    enemy = A.npc_hero(livingId=BOSS_LIVING, side=2, pos=5, type=3, tempId=int(hero.get("TemplateId") or 0),
                       nickName=hero.get("TemplateName", ""), grade=int(hero.get("Grades") or 0), maxHp=live,
                       initHp=hp, hp=hp, captain=int(hero.get("Captain") or 0), res=hero.get("ResPath", ""),
                       castTime=4000)  # fmt: skip
    return {
        "battleType": battle_type, "mapTempId": 1, "attackModel": 2, "battleScene": CAMPAIGN_SCENE,
        "soldiers": soldiers, "heroes": [enemy], "player": {"livingId": 3, "pos": 4, "pawnTempId": pawn_tpl},
    }  # fmt: skip


def boss_left(battle: Battle) -> int:
    return next((u.hp for u in battle.units if u.living_id == BOSS_LIVING and u.side == 2), 0)


def drops(templates: GameTemplates, category: str, **attrs: object) -> list[tuple[int, int]]:
    """``BossReward``/``AreaReward``: ``ItemId`` x ``Count``."""
    return [(int(r["ItemId"]), int(r["Count"])) for r in templates.find(category, **attrs)]


def _data(s: GameSession) -> dict[str, Any]:
    """Estado com a contagem do dia zerada na virada (``count`` é por dia: TipsTxt01 "for today")."""
    snap = s.snapshot
    assert snap is not None
    d = mj.load(snap, KEY)
    today = gameday.local(s.ctx.clock.now()).date().isoformat()
    if d.get("day") != today:
        d["day"], d["count"] = today, 0
    d.setdefault("area", 1)
    d.setdefault("max", 0)
    d.setdefault("paid", [])
    d.setdefault("ranks", {})
    d.setdefault("items", 0)
    return d


def _msg(s: GameSession, d: dict[str, Any]) -> pb.SinglePassMsg:
    msg = b.complete(pb.SinglePassMsg(userId=s.player_id, area=d["area"], maxIndex=d["max"]))
    msg.areaReward = ",".join(str(a) for a in d["paid"])
    msg.count, msg.itemCount = d["count"], d["items"]
    for index, rank in sorted(d["ranks"].items(), key=lambda kv: int(kv[0])):
        msg.rankInfo.add(index=int(index), rank=rank)
    return msg


def judge(s: GameSession, battle: Battle) -> int:
    """Avaliação 1..5 (D..S: ``SinglePassVicotyResultView`` pelo ``battleScene``). TODO(inventado): pela vida que
    sobrou ao herói, limiares em ``game_settings.sky_trails.judge`` (% para S, A, B, C)."""
    steps = list(mj.cfg(s, "sky_trails").get("judge") or [80, 60, 40, 20])
    p = battle.player
    pct = 100 * p.hp // max(1, p.max_hp or p.hp) if p is not None else 0
    return JUDGE_MAX - next((i for i, need in enumerate(steps) if pct >= need), len(steps))


async def info(s: GameSession) -> None:
    s.send(S_SINGLE_PASS, _msg(s, _data(s)))


async def attack(s: GameSession, index: int) -> None:
    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None
    d = _data(s)
    row = stage(templates, CAMPAIGN, index)
    limit = int(A.config(templates, "SinglePass_Count", 10))
    reason = (
        "em batalha" if s.battle is not None
        else "fase não existe" if row is None
        else "fase anterior" if index > d["max"] + 1 or (index - 1) // PER_AREA + 1 > d["area"]  # TipsTxt02
        else "já tem S" if d["ranks"].get(str(index), 0) >= JUDGE_MAX  # TipsTxt03
        else ""
    )  # fmt: skip
    taken = None
    if not reason and d["count"] >= limit and (taken := rewards.take_one(snap, PROP)) is None:
        reason = "sem tentativas"  # TipsTxt01
    if reason or row is None:
        s.log.info("8755 Sky Trails recusado", motivo=reason, fase=index)
        s.send(S_SINGLE_PASS, _msg(s, d))
        return
    d["count"] += 1
    hero = boss_row(templates, row)
    live = max(1, int(hero.get("Live") or 1))
    spec = boss_spec(s, hero, live, BATTLE_TYPE)

    async def finished(battle: Battle, won: bool) -> None:
        await _over(s, battle, won, index)

    s.battle = Battle(spec, player_hero(s, spec), templates, s.ctx.clock, s.send, finished,
                      settings=s.ctx.world.settings)  # fmt: skip
    counted = ev.count(snap, s.ctx.events, ev.SKY_TRAILS, now)
    item = [] if taken is None or taken[1] else [taken[0]]
    await s.ctx.characters.save(mj.store(snap, KEY, d, now), *counted, *item,
                                delete=(taken[0],) if taken and taken[1] else ())  # fmt: skip
    if taken is not None:
        s.send(S_ITEMS, rewards.taken_msg(taken[0], taken[1], s.player_id))
    s.log.info("batalha do Sky Trails", fase=index, battle=s.battle.id)
    s.battle.start()


async def _over(s: GameSession, battle: Battle, won: bool, index: int) -> None:
    snap, templates = s.snapshot, s.ctx.templates
    assert snap is not None
    s.battle, s.hero_sp = None, battle.player_sp
    healed = hero_after_fight(s, battle.player.hp if battle.player is not None else None)
    d = _data(s)
    got: list[tuple[int, int]] = []
    rank = 0
    if won:
        rank = judge(s, battle)
        old = int(d["ranks"].get(str(index), 0))
        if index > d["max"]:
            d["max"] = index
            got += drops(templates, "BossRewards", Type=0, Floor=index)
        if rank >= JUDGE_MAX > old:
            got += drops(templates, "BossRewards", Type=2, Floor=index)
        d["ranks"][str(index)] = max(old, rank)
    report = _report(battle, won, 0)
    report.battleScene = rank or 1
    for t, n in got:
        report.baseItem.add(templateId=t, count=n)
    s.send(S_BATTLE_REPORT, report)
    hp_pack(s, healed)
    st = mj.store(snap, KEY, d, s.ctx.clock.now())
    leader = [snap.leader] if snap.leader is not None else []
    if got:
        await mj.give(s, snap, got, st, *leader)
    else:
        await s.ctx.characters.save(st, *leader)
    s.send(S_SINGLE_PASS, _msg(s, d))


@router.on(8636)
async def update_area(s: GameSession, _: object) -> None:
    await info(s)


@router.on(8637)
async def get_area_reward(s: GameSession, _: object) -> None:
    snap = s.snapshot
    assert snap is not None
    d = _data(s)
    area = d["area"]
    if d["max"] < area * PER_AREA or area in d["paid"]:
        s.log.info("8637 recompensa de área recusada", area=area, max=d["max"])  # TipsTxt04
        s.send(S_SINGLE_PASS, _msg(s, d))
        return
    d["paid"].append(area)
    d["area"] = min(area + 1, AREAS)
    got = drops(s.ctx.templates, "AreaRewards", Area=area)
    st = mj.store(snap, KEY, d, s.ctx.clock.now())
    if got:
        await mj.give(s, snap, got, st)
    else:
        await s.ctx.characters.save(st)
    s.send(S_SINGLE_PASS, _msg(s, d))


@router.on(8638)
async def get_bugle(s: GameSession, _: object) -> None:
    """Heaven Horn das fases feitas: 2 a cada 5 (``SinglePassManager`` e ``GetHornBtnTips01``)."""
    snap = s.snapshot
    assert snap is not None
    d = _data(s)
    left = d["max"] // 5 * BUGLES - d["items"]
    if left <= 0:
        s.log.info("8638 sem Heaven Horn", max=d["max"], pegos=d["items"])  # GetHornBtnTips02/03
    else:
        d["items"] += left
        await mj.give(s, snap, [(BUGLE, left)], mj.store(snap, KEY, d, s.ctx.clock.now()))
    s.send(S_SINGLE_PASS, _msg(s, d))
