"""Árvore dourada ("Sacred Gold Tree", 8604 ``BottleOpMsg``; no código do cliente é a "garrafa"/``Bottle``).

opType *(cliente)*: 0 ativa (``alterType`` 1/2/3 = 1/10/50 vezes; ``stickFirst`` 0 = varinhas primeiro), 1 vende o
armazém, 2 tira tudo do armazém, 3 atualiza (depois de cada animação), 4 abre a tela (botão do topo), 5 baú de
vezes (``param`` = vezes pedidas), 6 baú de andar (``param`` = andar). Respostas: 295 (lista e baús), 4526
(``BottleScoreMsg``: vezes, baús pegos, ``openView``, ``alterBottle``), 4825 (andares) e 4497 (linhas da sorte).

Fontes: *(visto)* tutorial_en #71 (4497 ``passType`` 2) e #72 (295 aberto: 70 itens, 5 baús de vezes, 5 de andar,
``endTime``); *(cliente)* ``BottleManager``, ``BottleModel``, ``BottleFrame``, ``BottleStorageFrame``,
``BottleIntergalBoxView``, ``BottleBottomIntergalBoxView``, ``TopToolsBar.showBottleBtn``; o help do
``language.txt`` inglês (``bottle.BottleFrame.helpFrame.helpContent``). Nenhum 8604, 4526 nem 4825 foi capturado:
a ordem das respostas e o que cada uma leva além do que o cliente lê são *dedução* (docs/eventos.md).

Estado: ``goldtree:<edição>`` no personagem (``value`` = vezes, ``text`` = ``treeStatus``) e
``goldtree:<edição>:floor:<andar>`` no personagem que bateu o andar (``value`` 1 = pegou, ``text`` = apelido). O
total do servidor é a soma das vezes (``by_prefix``), carregado uma vez por edição e mantido em ``ctx.gold_tree``.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

from ...domain import gameday
from ...domain.models import BagType, EventState, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from .. import bag, rewards
from .. import events as ev
from ..builders import login as b
from ..castle import castle_yield
from ..router import router
from ..session import GameSession
from .items import sell_gold
from .player import _player, alert, granted

S_DROP, S_PASS, S_RESULT, S_FLOORS, S_ITEMS = 295, 4497, 4526, 4825, 115
OPEN, SELL_ALL, LOOT_ALL, REFRESH, SHOW, COUNT_BOX, FLOOR_BOX = range(7)
PULLS = {1: 1, 2: 10, 3: 50}  # (cliente) BottleFrame: alterType -> _openNum
WAND = 208022  # Golden Wand: (cliente) BottleFrame._hammerNum; cada uma vale uma ativação (point + wands*preço1)
WAREHOUSE = 40  # (cliente) BottleFrame: com mais de 8*5 itens no armazém a árvore não ativa
# (dedução) o cliente não confere se o sorteio cabe (BottleBagView passa de 8x5 para 8x7): 40 + 50 de uma ativação
WAREHOUSE_MAX = WAREHOUSE + max(PULLS.values())
OWN, LUCK = 1, 2  # BottlePassMsg.passType: 1 = o que eu ganhei (soma), 2 = sorte do servidor (troca a lista)
LUCK_KEEP = 20  # ponytail: linhas da sorte guardadas em memória (o #71 mostra 3); perdem-se no restart
_rng = random.Random()


@dataclass
class Floor:
    character_id: int
    nick: str
    claimed: bool


@dataclass
class Shared:
    """Estado do servidor numa edição: total de ativações, dono de cada andar e as linhas da sorte."""

    total: int
    floors: dict[int, Floor]
    luck: list[str] = field(default_factory=list)


def _cfg(s: GameSession) -> Mapping[str, Any]:
    """``game_settings.gold_tree`` (0041, valores do #72). Sem a linha a árvore não existe."""
    return s.ctx.world.settings.get("gold_tree") or {}


def _at(cfg: Mapping[str, Any], name: str) -> datetime:
    return datetime.strptime(str(cfg[name]), ev.TIME_FMT).replace(tzinfo=gameday.GAME_TZ)


def is_open(cfg: Mapping[str, Any], now: datetime) -> bool:
    return bool(cfg) and _at(cfg, "startDate") <= now <= _at(cfg, "endDate")


def prices(s: GameSession) -> list[int]:
    """``Bottle_Price`` (1|10|50 ativações; o inglês tem 65|650|3250), lido como o ``BottleFrame``."""
    return [int(x) for x in ev.config(s.ctx.templates, "Bottle_Price", "65|650|3250").split("|")]


def split_cost(pulls: int, price: int, single: int, wands: int, use_wands: bool) -> tuple[int, int]:
    """(varinhas gastas, diamantes). Cada varinha paga uma ativação (o cliente confere ``point + wands*preço1 >=
    preço``); o resto sai do preço do pacote."""
    used = min(wands, pulls) if use_wands else 0
    return used, max(0, price - used * single)


def draw(drops: Sequence[Sequence[Any]], n: int, rng: random.Random = _rng) -> list[Sequence[Any]]:
    """``n`` sorteios com reposição pelos pesos (``drops[i][4]``, padrão 1 = uniforme: o oficial não mostra)."""
    return rng.choices(list(drops), weights=[float(d[4]) if len(d) > 4 else 1.0 for d in drops], k=n)


def _key(cfg: Mapping[str, Any]) -> str:
    return f"goldtree:{cfg['id']}"


def _floor_key(cfg: Mapping[str, Any], storey: int) -> str:
    return f"{_key(cfg)}:floor:{storey}"


def _boxes(cfg: Mapping[str, Any], name: str) -> list[list[int]]:
    """Baús ``[param, item, quantidade]`` em ordem de ``param``, a ordem em que o cliente os mostra (``sortOn``)."""
    return sorted(([int(x) for x in box] for box in cfg[name]), key=lambda box: box[0])


async def _shared(s: GameSession, cfg: Mapping[str, Any]) -> Shared:
    """Total e andares da edição: lidos do banco na primeira vez (soma das vezes de cada personagem do servidor)."""
    cache = s.ctx.gold_tree
    if cfg["id"] in cache:
        return cast(Shared, cache[cfg["id"]])
    assert s.snapshot is not None
    server, key = s.snapshot.character.server_id, _key(cfg)
    rows = await s.ctx.characters.read(lambda uow: uow.events.by_prefix(server, key))
    total = sum(r.value for r in rows if r.key == key)
    floors = {
        int(r.key.rsplit(":", 1)[1]): Floor(r.character_id, r.text, r.value == 1)
        for r in rows
        if r.key.startswith(f"{key}:floor:")
    }
    return cast(Shared, cache.setdefault(cfg["id"], Shared(total, floors)))  # outra corrotina pode ter carregado


def _mine(snap: PlayerSnapshot, cfg: Mapping[str, Any], now: datetime) -> EventState:
    st = ev.state(snap, _key(cfg), now)
    if not st.text:
        st.text = ",".join("0" * len(cfg["score"]))
    return st


def _drop_msg(cfg: Mapping[str, Any], now: datetime) -> pb.BottleDropListMsg:
    msg = pb.BottleDropListMsg(open=is_open(cfg, now), endTime=int(_at(cfg, "endDate").timestamp() * 1000))
    for tid, n, show, new, *_w in cfg["drops"]:
        msg.dropItem.add(tempId=int(tid), count=int(n), isShow=bool(show), isNewItems=bool(new))
    for name, field_ in (("score", msg.score), ("storey", msg.storey)):
        for param, tid, n in cfg[name]:
            field_.add(param=int(param)).item.add(tempId=int(tid), count=int(n), isShow=True)
    return msg


def _score_msg(st: EventState, open_view: bool = False, alter: bool = False) -> pb.BottleScoreMsg:
    return pb.BottleScoreMsg(treeStatus=st.text, count=st.value, openView=open_view, alterBottle=alter)


def _floors_msg(cfg: Mapping[str, Any], sh: Shared) -> pb.BottleMsg:
    """4825: um ``PlayerBottleMsg`` por andar, na ordem do ``param`` (``userId`` 0 = ninguém chegou); ``state`` 1 =
    já pegou (``BottleIntergalBoxView``). ponytail: ``isVip`` falso (o dono pode estar offline)."""
    msg = pb.BottleMsg(total=sh.total)
    for storey, _tid, _n in _boxes(cfg, "storey"):
        f = sh.floors.get(storey)
        if f is None:
            msg.playerBottle.add()
        else:
            msg.playerBottle.add(userId=f.character_id, nickName=f.nick, isVip=False, state=int(f.claimed))
    return msg


def _send(s: GameSession, code: int, msg: Any) -> None:
    s.send(code, b.complete(msg))


def _line(snap: PlayerSnapshot, s: GameSession, tid: int, n: int) -> str:
    """Linha da sorte no formato do #71 (links de jogador e de item do chat). ``consortiaId`` 1 e ``grades`` 0 como
    vieram nas 3 linhas do #71 (dedução: não é a guilda); ``skill`` = ``DefaultSkill`` (8001 no 1128274)."""
    c = snap.character
    row = s.ctx.templates.get("ItemTempInfos", tid) or {}
    skill = (row.get("DefaultSkill") or "0").split(",")[0] or "0"
    return (
        f'Congratulations to <a t="1" id="{c.id}" name="{c.nickname}" consortiaId="1" serverName="" grades="0" /> '
        f'for receiving: <a t="2" id="0" name="{row.get("TemplateName", tid)}" bind="true" join="-1,-1,-1,-1" '
        f'skill="{skill},0,0,0,0" tempid="{tid}" grade="0" appSkill="0"/> x {n}'
    )


@router.on(8604)
async def gold_tree(s: GameSession, msg: pb.BottleOpMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    cfg, now = _cfg(s), s.ctx.clock.now()
    if not cfg:  # sem árvore no banco: fechada (295 open falso esconde o botão; 4526 sem tela)
        _send(s, S_DROP, pb.BottleDropListMsg(open=False))
        _send(s, S_RESULT, pb.BottleScoreMsg(openView=False))
        return
    if msg.opType == LOOT_ALL:
        await _loot_all(s, snap)
        return
    if msg.opType == SELL_ALL:
        await _sell_all(s, snap)
        return
    sh = await _shared(s, cfg)
    st = _mine(snap, cfg, now)
    if msg.opType == OPEN:
        await _activate(s, snap, cfg, sh, st, msg)
    elif msg.opType == COUNT_BOX:
        await _count_box(s, snap, cfg, st, msg.alterType)
    elif msg.opType == FLOOR_BOX:
        await _floor_box(s, snap, cfg, sh, msg.alterType, now)
    elif msg.opType == SHOW:
        if not is_open(cfg, now) or snap.character.grades < int(cfg.get("minGrades", 0)):
            _send(s, S_DROP, _drop_msg(cfg, now))  # (dedução) fechada: o 295 com open falso tira o botão
            return
        _send(s, S_FLOORS, _floors_msg(cfg, sh))
        _send(s, S_PASS, pb.BottlePassMsg(passType=LUCK, infos=sh.luck))
        _send(s, S_RESULT, _score_msg(st, open_view=True))
    else:  # REFRESH
        _send(s, S_FLOORS, _floors_msg(cfg, sh))
        _send(s, S_RESULT, _score_msg(st))


async def _activate(
    s: GameSession, snap: PlayerSnapshot, cfg: Mapping[str, Any], sh: Shared, st: EventState, msg: pb.BottleOpMsg
) -> None:
    """Ativa 1/10/50 vezes: varinhas primeiro (``stickFirst`` 0), o resto em diamante (só ``point``, como o
    ``BottleFrame`` confere); cada sorteio vai para o armazém (bolsa 22). Recusa: 4526 com ``alterBottle``, que
    destrava a tela do cliente sem somar nada."""
    now, templates = s.ctx.clock.now(), s.ctx.templates
    pulls = PULLS.get(msg.alterType, 0)
    price = prices(s)
    goods = draw(cfg["drops"], pulls) if pulls else []
    used, diamonds = (0, 0)
    if pulls:
        wands = bag.count_of(snap, WAND)
        used, diamonds = split_cost(pulls, price[msg.alterType - 1], price[0], wands, msg.stickFirst == 0)
    if (
        not pulls
        or not is_open(cfg, now)
        or snap.character.grades < int(cfg.get("minGrades", 0))
        or len(bag.in_bag(snap, BagType.BOTTLE)) > WAREHOUSE
        or not bag.side_fits(snap, templates, [(int(g[0]), int(g[1])) for g in goods], BagType.BOTTLE, WAREHOUSE_MAX)
    ):
        s.log.info("8604 ativação recusada", vezes=pulls)
        _send(s, S_RESULT, _score_msg(st, alter=True))
        return
    spent = ledger.spend(snap.character, diamonds, "gold_tree", now, bound=False, ref=str(pulls)) if diamonds else None
    if diamonds and spent is None:
        s.log.info("8604 sem diamante", vezes=pulls, diamantes=diamonds)
        _send(s, S_RESULT, _score_msg(st, alter=True))
        return
    wand_changed, wand_gone = bag.take(snap, WAND, used) if used else ([], [])
    stored: list[Item] = []
    for g in goods:
        stored += [i for i in bag.side_add(snap, templates, int(g[0]), int(g[1]), BagType.BOTTLE, WAREHOUSE_MAX)
                   if i not in stored]  # fmt: skip
    before = sh.total
    st.value += pulls
    st.updated_at = now
    sh.total += pulls
    # (dedução) o andar fica com quem fez a ativação que chegou nele ("Lucky Level", help do cliente)
    won: list[EventState] = []
    for storey, _tid, _n in _boxes(cfg, "storey"):
        if before < storey <= sh.total and storey not in sh.floors:
            sh.floors[storey] = Floor(snap.character.id or 0, snap.character.nickname or "", False)
            mark = ev.state(snap, _floor_key(cfg, storey), now)
            mark.value, mark.text = 0, snap.character.nickname or ""
            won.append(mark)
    lines = [_line(snap, s, int(g[0]), int(g[1])) for g in goods]
    # (dedução) as 3 linhas do #71 são de itens com isNewItems (1118274 tem isShow falso): é esse o "raro"
    rare = [line for g, line in zip(goods, lines, strict=True) if g[3]]
    sh.luck = (sh.luck + rare)[-LUCK_KEEP:]
    extra = [x for x in (spent,) if x is not None]
    await s.ctx.characters.save(snap.character, st, *won, *extra, *wand_changed, *stored, delete=tuple(wand_gone))
    if diamonds:
        _player(s)
    if used:
        s.send(S_ITEMS, bag.moved(wand_changed, s.player_id, empty=wand_gone))
    s.send(S_ITEMS, bag.moved(stored, s.player_id))
    _send(s, S_PASS, pb.BottlePassMsg(passType=OWN, infos=lines))
    _send(s, S_RESULT, _score_msg(st, alter=True))
    if won:
        for o in s.ctx.online.sessions():  # o andar novo aparece para quem está com a árvore aberta
            if o.snapshot is not None:
                _send(o, S_FLOORS, _floors_msg(cfg, sh))
    if rare:
        for o in s.ctx.online.sessions():
            if o.snapshot is not None:
                _send(o, S_PASS, pb.BottlePassMsg(passType=LUCK, infos=sh.luck))


async def _count_box(s: GameSession, snap: PlayerSnapshot, cfg: Mapping[str, Any], st: EventState, want: int) -> None:
    """Baú de vezes (``BottleBottomIntergalBoxView``): ``param`` = vezes do baú; libera com ``count >= param``;
    ``treeStatus`` marca "1" no índice do baú (ordem do ``param``). O prêmio vai para a mochila (dedução)."""
    boxes = _boxes(cfg, "score")
    i = next((k for k, box in enumerate(boxes) if box[0] == want), -1)
    marks = st.text.split(",")
    drops = [(boxes[i][1], boxes[i][2])] if i >= 0 else []
    if i < 0 or st.value < want or marks[i] != "0" or not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        s.log.info("8604 baú de vezes recusado", vezes=want, minhas=st.value)
        _send(s, S_RESULT, _score_msg(st))
        return
    marks[i] = "1"
    st.text, st.updated_at = ",".join(marks), s.ctx.clock.now()
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), st, *new)
    granted(s, drops, new, text)
    _send(s, S_RESULT, _score_msg(st))


async def _floor_box(
    s: GameSession, snap: PlayerSnapshot, cfg: Mapping[str, Any], sh: Shared, storey: int, now: datetime
) -> None:
    """Baú de andar (``BottleIntergalBoxView``): só o dono do andar, uma vez."""
    box = next((x for x in _boxes(cfg, "storey") if x[0] == storey), None)
    f = sh.floors.get(storey)
    drops = [(box[1], box[2])] if box else []
    if box is None or f is None or f.character_id != snap.character.id or f.claimed:
        s.log.info("8604 baú de andar recusado", andar=storey)
        _send(s, S_FLOORS, _floors_msg(cfg, sh))
        return
    if not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        _send(s, S_FLOORS, _floors_msg(cfg, sh))
        return
    mark = ev.state(snap, _floor_key(cfg, storey), now)
    mark.value, mark.updated_at = 1, now
    f.claimed = True
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(*rewards.owners(snap), mark, *new)
    granted(s, drops, new, text)
    _send(s, S_FLOORS, _floors_msg(cfg, sh))


async def _loot_all(s: GameSession, snap: PlayerSnapshot) -> None:
    """Tira tudo do armazém para a mochila, só se couber tudo (como o 9517 do labirinto)."""
    now, templates = s.ctx.clock.now(), s.ctx.templates
    stock = bag.in_bag(snap, BagType.BOTTLE)
    if not stock or not bag.fits(snap, templates, [(i.template_id, i.count) for i in stock], now):
        s.log.info("8604 tirar tudo recusado", itens=len(stock))
        if stock:
            alert(s, "Inventory Full")
        return
    for item in stock:
        snap.items.remove(item)
    changed: list[Item] = []
    for item in stock:
        changed += [i for i in bag.add(snap, templates, item.template_id, item.count, now) if i not in changed]
    await s.ctx.characters.save(*changed, delete=tuple(stock))
    s.send(S_ITEMS, bag.moved(changed, s.player_id, empty=stock))


async def _sell_all(s: GameSession, snap: PlayerSnapshot) -> None:
    """ "Sell All" do armazém: ouro de venda de cada pilha (``GoodsHelp.getSellGold``, o mesmo do 5007)."""
    stock = bag.in_bag(snap, BagType.BOTTLE)
    gold = 0
    for item in stock:
        row = s.ctx.templates.get("ItemTempInfos", item.template_id)
        gold += sell_gold(row, item, item.count) if row else 0
    if not stock:
        return
    for item in stock:
        snap.items.remove(item)
    snap.character.gold += gold
    await s.ctx.characters.save(snap.character, delete=tuple(stock))
    s.send(S_ITEMS, bag.moved([], s.player_id, empty=stock))
    castle_yield(s)


def login_push(s: GameSession) -> None:
    """Login com a árvore no banco: 4497 da sorte (#71) e 295 (#72), nessa ordem. Não lê o banco: a sorte é a da
    memória (vazia depois de um restart)."""
    cfg = _cfg(s)
    if not cfg:
        return
    sh = s.ctx.gold_tree.get(cfg["id"])
    _send(s, S_PASS, pb.BottlePassMsg(passType=LUCK, infos=sh.luck if sh else []))
    _send(s, S_DROP, _drop_msg(cfg, s.ctx.clock.now()))
