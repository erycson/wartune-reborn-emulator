"""Gods Descent (GodArrive, "pedágio"): 30 chefes em fila, pontos, ranking e prêmios no fim do evento.

8753 e 8755 levam ``ChallengeMsg.type``: 1 é deste sistema (``GodArriveModel``), 0 é o Sky Trails
(``SinglePassSocketOutManager``), despachado para ``singlepass``.

Cliente (``GodArriveManager``, ``GodArriveModel``, ``GodArriveFrame``, ``GodPassCardItemView``) e o idioma
(``godarrive.GodarriveFrame.helpBtnTipContent``):

* 8753 type 1: 4645 (``isOpen``), 4643 (``TollgateMsg`` inteiro: janela, pontos, posição, tentativas, chefe atual
  e o ``challengeInfo`` de cada chefe: primeiro a matar, contagem e vida) e, com prêmio a receber, 4644.
* 8755 type 1, ``tarUserId`` = chefe atual (``curTollgateId``): luta (battleType 294, ``BattleResultHandler``).
  Grau 60 (``__godArriveAttack``). Tentativas: ``tollgate_count`` por dia, uma volta a cada ``restore_count_time``
  s; sem tentativa, compra por ``tollgate_attack_count`` Balens até ``tollgate_add_count`` (ConfigInfo).
  O chefe é o ``HeroIds`` do ``CampaignDataInfo`` da campanha 40002 com ``Param1`` = índice.
* Derrota: a vida do chefe fica até o fim da contagem (idioma 4-5); 5021 type 2 estica 5 min por
  ``addTimeCount`` * 10 Balens (``__addTimeHandler``), ``addTimeCount`` até ``tollgate_add_time_count``.
* Vitória: ``BossReward`` Type 1 do chefe; o primeiro do servidor também o Type 3 (``GodPassCardItemView``: drops1
  e drops2, ``firstName``); pontos e o próximo chefe ("cleared levels cannot be challenged again").
* 8754: ranking (4646, ``ChallengeScoreMsg``): pontos, poder de luta e nível (idioma 9).
* 8752: no fim do evento, o ``ScoreReward`` da posição (``Order`` "n" ou "de,até") e, nas posições da sorte
  (``luckyReward``), o ``LuckyReward``; responde 4647.

Regras sem fonte em ``game_settings.gods_descent`` (migração 0119). Estado do jogador: JSON no ``EventState``
``godarrive``; o primeiro a matar cada chefe: ``godarrive_first`` (``minijogo.shared``).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from ...domain import gameday
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import arena as A
from .. import rules
from ..battle import Battle
from ..router import router
from ..session import GameSession
from . import minijogo as mj
from . import singlepass as sp
from .campaign import S_BATTLE_REPORT, _report, player_hero
from .player import hero_after_fight, hp_pack
from .shop import Charge, send_charge

S_INFO, S_REWARD_READY, S_IS_OPEN, S_SCORES, S_REWARD = 4643, 4644, 4645, 4646, 4647
KEY, FIRST, CFG = "godarrive", "godarrive_first", "gods_descent"
CAMPAIGN = 40002  # GodArriveModel.getGodArriveDataByIndex
BATTLE_TYPE = 294  # BattleResultHandler / BattleUIView.isGodArrive
GODS, SKY = 1, 0  # ChallengeMsg.type
MIN_GRADE = 60  # GodArriveFrame.__godArriveAttack
ADD_MINUTES = 5  # godarrive.GodArriveFrame.addRemainTime.Alert: "extend countdown by 5 minutes"


def _cfg(s: GameSession) -> dict[str, Any]:
    return dict(mj.cfg(s, CFG))


def _window(s: GameSession, now: datetime) -> tuple[datetime, datetime] | None:
    """(começo, fim das lutas) da edição vigente; depois do fim e até a próxima, só o prêmio."""
    c = _cfg(s)
    ed = mj.edition(c, now)
    if ed is None:
        return None
    return ed[0], min(ed[1], ed[0] + timedelta(hours=float(c.get("openHours", 1e6))))


def _conf(s: GameSession, name: str, default: int) -> int:
    return int(A.config(s.ctx.templates, name, default))


def _gates(s: GameSession) -> int:
    return len(list(s.ctx.templates.find("CampaignData", CampaignId=CAMPAIGN)))


def _live(s: GameSession, index: int) -> int:
    row = sp.stage(s.ctx.templates, CAMPAIGN, index)
    return max(1, int(sp.boss_row(s.ctx.templates, row).get("Live") or 1)) if row is not None else 1


def lucky(s: GameSession, ed: str) -> list[int]:
    """Posições da sorte da edição ("Lucky prizes will be given to different ranks every event"). TODO(inventado):
    ``luckyCount`` sorteadas entre 1 e ``luckyTop``, fixas por edição."""
    c = _cfg(s)
    top, n = int(c.get("luckyTop", 50)), int(c.get("luckyCount", 3))
    return sorted(random.Random(f"{KEY}:{ed}").sample(range(1, top + 1), min(n, top)))


def _data(s: GameSession, now: datetime) -> dict[str, Any]:
    """Estado do jogador na edição vigente: troca de edição guarda a anterior (``prev``) para o prêmio; o dia zera
    as tentativas e as compradas; uma tentativa volta a cada ``restore_count_time`` s até a base. shortcut: conta
    o tempo de relógio, não só o online (o idioma 6 diz online); trocar se houver como medir a presença."""
    snap = s.snapshot
    assert snap is not None
    d = mj.load(snap, KEY)
    win = _window(s, now)
    ed = mj.fmt(win[0]) if win else ""
    base, period = _conf(s, "tollgate_count", 5), _conf(s, "restore_count_time", 600)
    if d.get("ed") != ed:
        prev = d.get("prev")
        if d.get("score", 0) > 0 and not d.get("claimed"):
            prev = {"ed": d["ed"], "score": d["score"], "fight": d.get("fight", 0), "grade": d.get("grade", 0)}
        d = {"ed": ed, "prev": prev, "cur": 1, "score": 0, "hp": 0, "until": "", "adds": 0}
    today = gameday.local(now).date().isoformat()
    if d.get("day") != today:
        d.update(day=today, left=base, bought=0, tick=now.timestamp())
    while d["left"] < base and now.timestamp() - d["tick"] >= period:
        d["left"] += 1
        d["tick"] += period
    if d["left"] >= base:
        d["tick"] = now.timestamp()
    ch = snap.character
    d.update(nick=ch.nickname or "", grade=ch.grades)
    d["fight"] = rules.leader_stats(snap, s.ctx.templates, now).fighting_capacity if snap.leader else 0
    return d


def _counting(d: dict[str, Any], now: datetime) -> int:
    """Segundos da contagem do chefe atual (0: a vida dele já voltou)."""
    if not d.get("until") or not d.get("hp"):
        return 0
    return max(0, int((datetime.fromisoformat(d["until"]) - now).total_seconds()))


def _score_of(d: dict[str, Any], ed: str) -> dict[str, Any] | None:
    if d.get("ed") == ed:
        return d
    prev = d.get("prev") or {}
    return prev if prev.get("ed") == ed else None


async def ranking(s: GameSession, ed: str, mine: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    """(id, estado) de quem tem pontos na edição, na ordem do idioma 9: pontos, poder de luta e nível."""
    snap = s.snapshot
    assert snap is not None
    rows = await s.ctx.characters.read(lambda uow: uow.events.by_prefix(snap.character.server_id, KEY))
    states = {st.character_id: mj.load_text(st.text) for st in rows if st.key == KEY}
    states[s.player_id] = mine
    out = []
    for uid, d in states.items():
        got = _score_of(d, ed)
        if got is not None and int(got.get("score", 0)) > 0:
            out.append((uid, {**got, "nick": d.get("nick", "")}))
    out.sort(key=lambda r: (-int(r[1]["score"]), -int(r[1].get("fight", 0)), -int(r[1].get("grade", 0)), r[0]))
    return out


async def _first(s: GameSession, ed: str) -> dict[str, Any]:
    data = await mj.shared(s, FIRST)
    return data if data.get("ed") == ed else {"ed": ed, "gates": {}, "rev": data.get("rev", 0)}


def _claimable(d: dict[str, Any], now: datetime, fights_end: datetime | None) -> dict[str, Any] | None:
    """O resultado ainda não recebido: o da edição vigente depois das lutas, ou o da anterior."""
    if fights_end is not None and now >= fights_end and d.get("score", 0) > 0 and not d.get("claimed"):
        return d
    prev = d.get("prev")
    return prev if prev and not prev.get("claimed") else None


async def gods_info(s: GameSession) -> None:
    now = s.ctx.clock.now()
    win = _window(s, now)
    s.send(S_IS_OPEN, pb.TollgateMsg(isOpen=win is not None and now < win[1]))
    d = _data(s, now)
    if win is None:
        if _claimable(d, now, None):
            s.send(S_REWARD_READY)
        return
    order = next((i for i, (uid, _) in enumerate(await ranking(s, d["ed"], d), 1) if uid == s.player_id), 0)
    base, period = _conf(s, "tollgate_count", 5), _conf(s, "restore_count_time", 600)
    msg = pb.TollgateMsg(
        userId=s.player_id, startTime=mj.fmt(win[0]), endTime=mj.fmt(win[1]), order=order, score=d["score"],
        remainCount=d["left"], curTollgateId=d["cur"], luckyReward=",".join(map(str, lucky(s, d["ed"]))),
        remainBuyCount=max(0, _conf(s, "tollgate_add_count", 1000) - d["bought"]),
        addTimeCount=min(d["adds"] + 1, _conf(s, "tollgate_add_time_count", 20)),
        remainTime=int(period - (now.timestamp() - d["tick"])) if d["left"] < base else 0,
    )  # fmt: skip
    first = (await _first(s, d["ed"]))["gates"]
    for index in range(1, _gates(s) + 1):
        gate = msg.challengeInfo.add(tollgateId=index)
        if (who := first.get(str(index))) is not None:
            gate.attackUserid, gate.attackName, gate.attackTime = who
        live = _live(s, index)
        if index == d["cur"] and (left := _counting(d, now)):
            gate.remainTime, gate.lastHp = left, d["hp"]
        else:
            gate.lastHp = 0 if index < d["cur"] else live
    s.send(S_INFO, msg)
    if _claimable(d, now, win[1]):
        s.send(S_REWARD_READY)
    snap = s.snapshot
    assert snap is not None
    await s.ctx.characters.save(mj.store(snap, KEY, d, now))


async def gods_attack(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None
    win = _window(s, now)
    d = _data(s, now)
    index = d["cur"]
    row = sp.stage(templates, CAMPAIGN, index)
    reason = (
        "fechado" if win is None or now >= win[1]
        else "em batalha" if s.battle is not None
        else "grau" if snap.character.grades < MIN_GRADE
        else "não é o chefe atual" if msg.tarUserId != index or row is None
        else ""
    )  # fmt: skip
    extra: list[object] = []
    if not reason and d["left"] <= 0:
        if d["bought"] >= _conf(s, "tollgate_add_count", 1000):
            reason = "sem tentativas"  # NoLeftCount
        else:
            cost = _conf(s, "tollgate_attack_count", 45)
            spent = cash.pay(snap.character, cost, msg.payType, "godarrive", f"attack:{index}", now)
            reason = "sem Balens" if spent is None else ""
            extra = [snap.character, spent] if spent is not None else []
            d["bought"] += 1
    elif not reason:
        d["left"] -= 1
    if reason or row is None:
        s.log.info("8755 Gods Descent recusado", motivo=reason, alvo=msg.tarUserId)
        await gods_info(s)
        return
    hero = sp.boss_row(templates, row)
    hp = d["hp"] if _counting(d, now) else max(1, int(hero.get("Live") or 1))
    spec = sp.boss_spec(s, hero, hp, BATTLE_TYPE)

    async def finished(battle: Battle, won: bool) -> None:
        await _over(s, battle, index)

    s.battle = Battle(spec, player_hero(s, spec), templates, s.ctx.clock, s.send, finished,
                      settings=s.ctx.world.settings)  # fmt: skip
    await s.ctx.characters.save(mj.store(snap, KEY, d, now), *extra)
    if extra:
        send_charge(s, Charge(ledger=extra[1]))  # type: ignore[arg-type]
    s.log.info("batalha do Gods Descent", chefe=index, vida=hp, battle=s.battle.id)
    s.battle.start()


def points(s: GameSession, index: int) -> int:
    """TODO(inventado): ``pointsPerStage`` * índice ("Higher levels provide ... more points", idioma 2)."""
    return int(_cfg(s).get("pointsPerStage", 10)) * index


async def _over(s: GameSession, battle: Battle, index: int) -> None:
    snap, templates, now = s.snapshot, s.ctx.templates, s.ctx.clock.now()
    assert snap is not None
    s.battle, s.hero_sp = None, battle.player_sp
    healed = hero_after_fight(s, battle.player.hp if battle.player is not None else None)
    d = _data(s, now)
    left = sp.boss_left(battle)
    got: list[tuple[int, int]] = []
    rows: list[object] = [snap.leader] if snap.leader is not None else []
    if left <= 0 and d["cur"] == index:
        d["score"] += points(s, index)
        got += sp.drops(templates, "BossRewards", Type=1, Floor=index)
        async with mj.lock(s, FIRST):
            first = await _first(s, d["ed"])
            if str(index) not in first["gates"]:
                first["gates"][str(index)] = [s.player_id, snap.character.nickname or "", mj.fmt(now)]
                got += sp.drops(templates, "BossRewards", Type=3, Floor=index)
                await s.ctx.characters.save(mj.store_shared(snap, FIRST, first, now))
        d.update(cur=index + 1, hp=0, until="", adds=0)
    elif d["cur"] == index:
        # TODO(inventado): ``resetMinutes`` de contagem a cada derrota (o idioma não diz quanto)
        d.update(hp=left, until=(now + timedelta(minutes=float(_cfg(s).get("resetMinutes", 30)))).isoformat())
    report = _report(battle, left <= 0, 0)
    for t, n in got:
        report.baseItem.add(templateId=t, count=n)
    s.send(S_BATTLE_REPORT, report)
    hp_pack(s, healed)
    st = mj.store(snap, KEY, d, now)
    if got:
        await mj.give(s, snap, got, st, *rows)
    else:
        await s.ctx.characters.save(st, *rows)
    await gods_info(s)


async def add_time(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    """5021 type 2 (``GodArriveModel.addRemainTime``): +5 min na contagem do chefe atual."""
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    d = _data(s, now)
    n = min(d["adds"] + 1, _conf(s, "tollgate_add_time_count", 20))
    spent = (
        cash.pay(snap.character, n * 10, msg.payType, "godarrive", f"time:{d['cur']}", now)
        if _counting(d, now)
        else None
    )
    if spent is None:
        s.log.info("5021 type 2 recusado", contagem=_counting(d, now), custo=n * 10)
    else:
        d["until"] = (datetime.fromisoformat(d["until"]) + timedelta(minutes=ADD_MINUTES)).isoformat()
        d["adds"] += 1
        await s.ctx.characters.save(snap.character, spent, mj.store(snap, KEY, d, now))
        send_charge(s, Charge(ledger=spent))
    await gods_info(s)


@router.on(8752)
async def get_reward(s: GameSession, _: object) -> None:
    snap, now = s.snapshot, s.ctx.clock.now()
    assert snap is not None
    win = _window(s, now)
    d = _data(s, now)
    got = _claimable(d, now, win[1] if win else None)
    if got is None:
        s.log.info("8752 sem prêmio do Gods Descent")
        return
    ed = str(got["ed"])
    order = next((i for i, (uid, _) in enumerate(await ranking(s, ed, d), 1) if uid == s.player_id), 0)
    templates = s.ctx.templates
    span = [(r, [int(x) for x in r["Order"].split(",")]) for r in templates.rows("ScoreRewards")]
    score_items = [(int(r["TemplateId"]), int(r["Count"])) for r, o in span if o[0] <= order <= o[-1]]
    lucky_items = [(int(r["TemplateId"]), int(r["Count"])) for r in templates.rows("LuckyRewards")]
    lucky_items = lucky_items if order in lucky(s, ed) else []
    got["claimed"] = True
    st = mj.store(snap, KEY, d, now)
    if score_items or lucky_items:
        await mj.give(s, snap, score_items + lucky_items, st)
    else:
        await s.ctx.characters.save(st)
    s.send(S_REWARD, pb.TollgateRewardMsg(
        userId=s.player_id, score=int(got["score"]), order=order,
        scoreItems=",".join(f"{t}|{n}" for t, n in score_items),
        luckyItems=",".join(f"{t}|{n}" for t, n in lucky_items),
    ))  # fmt: skip


@router.on(8753)
async def request(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    if msg.type == SKY:
        await sp.info(s)
    else:
        await gods_info(s)


@router.on(8754)
async def score(s: GameSession, _: object) -> None:
    now = s.ctx.clock.now()
    d = _data(s, now)
    top = int(_cfg(s).get("rankTop", 50))
    luck = lucky(s, d["ed"])
    msg = pb.TollgateMsg()
    for order, (uid, row) in enumerate((await ranking(s, d["ed"], d))[:top], 1):
        msg.scoreInfo.add(userId=uid, nickName=row.get("nick", ""), grade=int(row.get("grade", 0)),
                          fightCapacity=int(row.get("fight", 0)), score=int(row["score"]), order=order,
                          tollgateId=int(row.get("cur", 1)), isLucky=order in luck)  # fmt: skip
    s.send(S_SCORES, msg)


@router.on(8755)
async def request_attack(s: GameSession, msg: pb.PlayerChallengeMsg) -> None:
    if msg.type == SKY:
        await sp.attack(s, msg.tarUserId)
    else:
        await gods_attack(s, msg)
