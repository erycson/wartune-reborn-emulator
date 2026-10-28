"""Pesca: 9507 ``FreshPoolMsg {op, paras}`` (``FishActionEnums``). Regras e cardume em ``game/fishing.py``.

Ops e respostas *(visto 26/10, 27/10 e 28/10, salvo onde diz cliente)*:

- 4 FISHPOOL (botão do topo, ``TopToolsBar``): sem resposta; aqui recalcula o ``order``. Vem sempre com 1 [10].
- 1 FRESH_FISH ``[10]`` abrir: 4916 e 4918. ``[1]`` peixe saiu / depois de pescar, ``[4]`` depois do torpedo: 4918.
- 11 ``[2, id]`` o arpão tocou o peixe: sem resposta. ``[1, id, ângulo, quadro]`` *(cliente)* fisgou o enfurecido.
- 10 CATCHFISH ``[ids]``: 115 (cesto, bagType 23, uma posição por peixe), 111 "Received X xN while fishing!", 4917,
  4916, 4918 (o pescado com state 5) e 83 canal 3 com o mesmo texto. Sem ids (errou): 4917 vazio, 4916 e 4918.
- 2 GETALL_FISH (cesto): 111 "Looted successfully!", 115 com as posições do cesto vazias e 115 da mochila.
- 8 CLOSE: sem resposta.
- *(cliente, sem captura)* 3 COOLCD ``[usar vinculado]``, 5 USETOOL ``[1-4]``, 6 HELP ``[dono]``, 7 SENDHELP
  ``[1 pago | 2 mundo | 3 guilda]``, 9 TIMEOVER (fim da fúria): respostas por dedução, ver cada função.
"""

from __future__ import annotations

import random
from xml.sax.saxutils import quoteattr

from ...domain.models import BagType, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import cash
from .. import bag
from .. import events as ev
from .. import fishing as fs
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .player import _player, alert

S_POOL, S_RESULT, S_INFOS, S_HELP_OVER, S_CRAZY = 4916, 4917, 4918, 4919, 4920
S_ITEMS, S_CHAT = 115, 83
FRESH, GETALL, COOLCD, FISHPOOL, USETOOL, HELP, SENDHELP, CLOSE, TIMEOVER, CATCH, CRAZY = range(1, 12)
OPEN = 10  # paras do 1 na abertura (TopToolsBar)
TOUCH, RAGE_HOOK = 2, 1  # paras[0] do op 11 (FishView.addFishSigInfo / rageFish)
PAID, WORLD, GUILD = 1, 2, 3  # FishHelpEnums
LORD_OF_TIME = 4  # KingContracts 4: FishFrame manda o 3 sem perguntar o preço (o mesmo contrato da sala de treino)
WORLD_CHANNEL = 10
FISH_LINK = 102  # ChatFormat: <a t="102" userId name/> vira a célula de pesca; o clique manda o 6 [userId]
# TODO(inventado): texto do pedido de ajuda (a captura não tem; o link é o do cliente)
HELP_TEXT = "{} found an Enraged Fish! Click to help."
EXIT_TEXT = "The person who asked for help has quit, this help is invalid."  # fish.FishFrame.exit
RNG = random.Random()  # os testes trocam


def _snap(s: GameSession) -> PlayerSnapshot:
    assert s.snapshot is not None
    return s.snapshot


def _pool(s: GameSession, f: fs.Fisher) -> fs.Pool:
    now = s.ctx.clock.now()
    if s.fish_pool is None:
        s.fish_pool = fs.new_pool(s.ctx.templates, f.level, now, RNG)
    else:
        fs.refresh(s.fish_pool, s.ctx.templates, f.level, now, RNG)
    pool: fs.Pool = s.fish_pool
    return pool


def _send_pool(to: GameSession, owner: GameSession, f: fs.Fisher) -> None:
    pool: fs.Pool | None = owner.fish_pool
    msg = fs.pool_msg(f, owner.ctx.clock.now(), owner.player_id, owner.fish_order, pool.helpers if pool else [])
    to.send(S_POOL, b.complete(msg))


def _send_infos(to: GameSession, pool: fs.Pool) -> None:
    to.send(S_INFOS, b.complete(fs.infos_msg(pool, to.ctx.clock.now())))


@router.on(9507)
async def fishing(s: GameSession, msg: pb.FreshPoolMsg) -> None:
    snap = _snap(s)
    if snap.character.grades < fs.OPEN_GRADE:
        s.log.info("9507 abaixo do nível", nivel=snap.character.grades, op=msg.op)
        return
    paras = list(msg.paras)
    now = s.ctx.clock.now()
    f = fs.load(snap, now)
    if msg.op == FISHPOOL:
        states = await s.ctx.characters.read(lambda uow: uow.events.by_prefix(snap.character.server_id, fs.KEY))
        s.fish_order = fs.position(states, s.player_id, now)
        s.fish_watch = 0
    elif msg.op == FRESH:
        await _fresh(s, f, paras)
    elif msg.op == CRAZY:
        _hook(s, f, paras)
    elif msg.op == CATCH:
        await _cast(s, f, paras)
    elif msg.op == TIMEOVER:
        await _rage_end(s, f, paid=False)
    elif msg.op == SENDHELP:
        await _send_help(s, f, paras)
    elif msg.op == GETALL:
        await _loot(s, snap)
    elif msg.op == COOLCD:
        await _cool(s, f, paras)
    elif msg.op == USETOOL:
        await _tool(s, f, paras)
    elif msg.op == HELP:
        _watch(s, paras)
    elif msg.op == CLOSE:
        _close(s)
    else:
        s.log.info("9507 op desconhecido", op=msg.op)


async def _fresh(s: GameSession, f: fs.Fisher, paras: list[int]) -> None:
    """1: o cardume do dono que o jogador está vendo (o próprio ou, ajudando, o de quem pediu)."""
    owner = s.ctx.online.get(s.fish_watch) if s.fish_watch else s
    if owner is None or owner.snapshot is None:
        s.fish_watch = 0
        return
    of = fs.load(owner.snapshot, owner.ctx.clock.now()) if owner is not s else f
    pool = _pool(owner, of)
    if paras[:1] == [OPEN]:
        _send_pool(s, owner, of)
    _send_infos(s, pool)


def _hook(s: GameSession, f: fs.Fisher, paras: list[int]) -> None:
    """11 [2, id]: guarda o fisgado (valida o 10). 11 [1, id, ângulo, quadro] (FishView.rageFish): começa a fúria; os
    ajudantes que entrarem recebem o 4920 com ângulo e quadro (FishManager.__fishCrazyHandler)."""
    pool = _pool(s, f)
    if len(paras) >= 2 and paras[0] == TOUCH:
        pool.hooked.add(paras[1])
    elif len(paras) >= 4 and paras[0] == RAGE_HOOK:
        fish = pool.fish.get(paras[1])
        if fish is not None and fish.state == fs.RAGE and pool.rage is None:
            pool.rage, pool.helpers = (paras[1], paras[2], paras[3]), []
    else:
        s.log.info("9507 op 11 inválido", paras=paras)


def _basket_add(snap: PlayerSnapshot, s: GameSession, tid: int, count: int) -> Item:
    """(visto) 27/10 #176/#199: cada pesca abre uma posição nova no cesto, sem empilhar (Gold Chest x2 na 0 e na 1)."""
    used = {i.pos for i in bag.in_bag(snap, BagType.FISH)}
    item = bag.new_item(snap, s.ctx.templates, tid, count)
    item.bag_type, item.pos = BagType.FISH, next(p for p in range(len(used) + 1) if p not in used)
    snap.items.append(item)
    return item


async def _land(s: GameSession, f: fs.Fisher, pool: fs.Pool, ids: list[int], bonus: list[tuple[int, int]]) -> None:
    """Lançamento: os peixes ``ids`` (já validados) e ``bonus`` (prêmio da fúria) vão para o cesto; soma GP, pontos,
    a tentativa (só com peixe) e os 300 s do cd (sempre). Respostas na ordem da captura."""
    snap, now, templates = _snap(s), s.ctx.clock.now(), s.ctx.templates
    result = pb.FishResultMsg(userId=s.player_id)
    goods: list[tuple[int, int]] = []
    tools: list[str] = []
    for fid in ids:
        fish = pool.fish[fid]
        row = templates.get("FishTemplateInfos", fish.template) or {}
        fs.add_gp(f, templates, int(row.get("GP", 0)))
        f.score += int(row.get("Score", 0))
        if int(row.get("RewardId", 0)) > 0:
            goods.append((int(row["RewardId"]), int(row["RewardCount"])))
        roll = RNG.randint(1, fs.TOOL_ROLL)  # (dedução) o ``tool`` do 4917 é o sorteio; 1-4 dá a ferramenta
        if roll <= len(f.tools):
            f.tools[roll - 1] += 1
            tools.append(fs.TOOL_NAMES[roll - 1])
        result.results.add(fishId=fid, tool=roll)
        fish.state = fs.CAUGHT
        pool.hooked.discard(fid)
    goods += [g for g in bonus if g[0] > 0 and g[1] > 0]
    if ids:
        f.count += 1
        f.hook = 0  # TODO(inventado): a lança trocada (ferramenta 2/3) vale um lançamento
    fs.add_cd(f, now)
    items = [_basket_add(snap, s, tid, n) for tid, n in goods]
    await s.ctx.characters.save(fs.store(snap, f, now), *items)
    text = ""
    if goods or tools:
        text = fs.ALERT.format(
            ", ".join([f"{bag.name(templates, t)} x{n}" for t, n in goods] + [f"{t} x1" for t in tools])
        )
        if items:
            s.send(S_ITEMS, bag.moved(items, s.player_id))
        alert(s, text)
    s.send(S_RESULT, b.complete(result))
    _send_pool(s, s, f)
    _send_infos(s, pool)
    if text:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


async def _cast(s: GameSession, f: fs.Fisher, paras: list[int]) -> None:
    """10: o cliente já bloqueou cd, tentativas e cesto (FishFrame.__clickHandler); aqui confere de novo."""
    snap, now = _snap(s), s.ctx.clock.now()
    pool = _pool(s, f)
    full = len(bag.in_bag(snap, BagType.FISH)) >= fs.BASKET
    if not fs.can_cast(f, now) or full or pool.rage is not None:
        s.log.info("9507 lançamento recusado", cd=fs.cd_left(f, now), vezes=f.count, cesto_cheio=full)
        _send_pool(s, s, f)
        return
    ids = fs.catchable(pool, s.ctx.templates, paras)[: fs.HOOK_FISH.get(f.hook, 1)]
    await _land(s, f, pool, ids, [])


async def _rage_end(s: GameSession, f: fs.Fisher, paid: bool) -> None:
    """Fim da fúria: 9 (tempo acabou) ou 7 [1] (pagou o que faltava). Com 3 ajudantes ou pago, o prêmio da fúria é
    o ``RageId1`` (FishView.playIcon mostra o RageId1 quando ``isRageReward``). Sem isso: TODO(inventado) o
    ``RageId2``. Os ajudantes recebem o 4919 (HelpOverMsg) com o resultado."""
    pool = _pool(s, f)
    if pool.rage is None:
        s.log.info("9507 fim de fúria sem fúria", op=TIMEOVER)
        return
    fid = pool.rage[0]
    row = s.ctx.templates.get("FishTemplateInfos", pool.fish[fid].template) or {}
    win = paid or len(pool.helpers) >= fs.HELPERS
    slot = "1" if win else "2"
    bonus = [(int(row.get(f"RageId{slot}", 0)), int(row.get(f"RageCount{slot}", 0)))]
    helpers = pool.helpers
    pool.rage, pool.helpers = None, []
    await _land(s, f, pool, [fid], bonus)
    for hid, _ in helpers:
        h = s.ctx.online.get(hid)
        if h is not None and h.fish_watch == s.player_id:
            h.send(S_HELP_OVER, pb.HelpOverMsg(result=win))
            h.fish_watch = 0


async def _send_help(s: GameSession, f: fs.Fisher, paras: list[int]) -> None:
    """7 (FishHelpFrame): [1] paga (3 - ajudantes) * 5 Balens e termina a fúria com prêmio; [2]/[3] pede ajuda no
    mundo / na guilda com o link de pesca."""
    snap, pool = _snap(s), _pool(s, f)
    kind = paras[0] if paras else 0
    if pool.rage is None:
        s.log.info("9507 ajuda sem fúria", tipo=kind)
        return
    if kind == PAID:
        cost = (fs.HELPERS - len(pool.helpers)) * fs.HELP_PRICE
        # (dedução) o alerta do cliente tem a caixa de vinculado: usa os vinculados primeiro
        spent = (
            cash.pay(snap.character, cost, cash.BIND_FIRST, "fish_help", str(cost), s.ctx.clock.now())
            if cost > 0
            else None
        )
        if cost > 0 and spent is None:
            alert(s, "Insufficient Balens")  # TODO(inventado) texto da recusa
            return
        await s.ctx.characters.save(snap.character, *([spent] if spent else []))
        _player(s)
        await _rage_end(s, f, paid=True)
        return
    c = snap.character
    link = f'<a t="{FISH_LINK}" userId="{c.id}" name={quoteattr(c.nickname or "")}/>'
    out = b.complete(pb.ChatChannelMsg(channel=WORLD_CHANNEL, encodeMsg=HELP_TEXT.format(link), otherId=-1, userType=1))
    if kind == WORLD:
        for o in s.ctx.online.sessions():
            o.send(S_CHAT, out)
    elif kind == GUILD and (mine := s.ctx.guilds.of(s.player_id)):
        from .guild.common import guild_chat  # guild importa handlers

        guild_chat(s, mine[0], HELP_TEXT.format(link))


def _watch(s: GameSession, paras: list[int]) -> None:
    """6 [dono] (clique no link): o ajudante vê a piscina do dono (4916 com ``userId`` dele e os ajudantes, 4918) e, se
    a fúria está em curso, entra como ajudante (até 3) e recebe o 4920. O dono recebe o 4916 com a lista nova."""
    owner = s.ctx.online.get(paras[0]) if paras else None
    pool: fs.Pool | None = owner.fish_pool if owner is not None else None
    if owner is None or owner is s or owner.snapshot is None or pool is None:
        alert(s, EXIT_TEXT)
        return
    s.fish_watch = owner.player_id
    of = fs.load(owner.snapshot, owner.ctx.clock.now())
    nick = _snap(s).character.nickname or ""
    if pool.rage is not None and len(pool.helpers) < fs.HELPERS and all(h != s.player_id for h, _ in pool.helpers):
        pool.helpers.append((s.player_id, nick))
        _send_pool(owner, owner, of)
    _send_pool(s, owner, of)
    _send_infos(s, pool)
    if pool.rage is not None:
        fid, angle, frame = pool.rage
        s.send(S_CRAZY, b.complete(pb.CrazyFishInfoMsg(fishId=fid, angle=angle, frame=frame)))


def _close(s: GameSession) -> None:
    """8: fecha a tela. O ajudante sai da lista do dono (o dono recebe o 4916)."""
    owner = s.ctx.online.get(s.fish_watch) if s.fish_watch else None
    s.fish_watch = 0
    pool: fs.Pool | None = owner.fish_pool if owner is not None else None
    if owner is None or owner.snapshot is None or pool is None:
        return
    pool.helpers = [h for h in pool.helpers if h[0] != s.player_id]
    _send_pool(owner, owner, fs.load(owner.snapshot, owner.ctx.clock.now()))


async def _loot(s: GameSession, snap: PlayerSnapshot) -> None:
    """2 (FishBagFrame "pick up"): o cesto vai todo para a mochila, só se couber tudo."""
    now, templates = s.ctx.clock.now(), s.ctx.templates
    stock = sorted(bag.in_bag(snap, BagType.FISH), key=lambda i: -i.pos)
    if not stock:
        return
    if not bag.fits(snap, templates, [(i.template_id, i.count) for i in stock], now):
        alert(s, "Inventory Full")  # TODO(inventado) texto (o mesmo da árvore dourada)
        return
    for item in stock:
        snap.items.remove(item)
    changed: list[Item] = []
    for item in sorted(stock, key=lambda i: i.pos):
        changed += [i for i in bag.add(snap, templates, item.template_id, item.count, now) if i not in changed]
    await s.ctx.characters.save(*changed, delete=tuple(stock))
    alert(s, "Looted successfully!")
    removed = pb.ItemMovedListMsg()
    for item in stock:  # (visto) 28/10 #369: posições do cesto em ordem decrescente
        removed.moved.add(changeType=BagType.FISH, changeObjId=0, changePos=item.pos)
    s.send(S_ITEMS, b.complete(removed))
    s.send(S_ITEMS, bag.moved(changed, s.player_id))


async def _cool(s: GameSession, f: fs.Fisher, paras: list[int]) -> None:
    """3 [1 usar vinculado | 0]: zera o cd por ``ceil(cd/60)*3`` Balens; grátis com o contrato do rei 4. (dedução)
    resposta 3 (se pagou) e 4916 com cd 0."""
    snap, now = _snap(s), s.ctx.clock.now()
    cost = 0 if ev.has_contract(snap, LORD_OF_TIME, now) else fs.cool_price(f, now)
    pay_type = cash.BIND_FIRST if paras[:1] == [1] else 1
    spent = cash.pay(snap.character, cost, pay_type, "fish_cd", str(cost), now) if cost else None
    if cost and spent is None:
        s.log.info("9507 sem saldo para o cd", custo=cost)
        _send_pool(s, s, f)
        return
    f.cd_end = ""
    await s.ctx.characters.save(fs.store(snap, f, now), *([snap.character, spent] if spent else []))
    if spent:
        _player(s)
    _send_pool(s, s, f)


async def _tool(s: GameSession, f: fs.Fisher, paras: list[int]) -> None:
    """5 [1-4] (FishToolItemClickMediator): 1 e 4 torpedos (somem peixes rasos, ver ``fs.TORPEDO``; o cliente pede o
    1 [4] depois), 2 e 3 trocam a lança (hookState 1 tripla, 2 força). (dedução) resposta 4916 e, no torpedo, 4918."""
    snap, now = _snap(s), s.ctx.clock.now()
    tool = paras[0] if paras else 0
    if not 1 <= tool <= len(f.tools) or f.tools[tool - 1] <= 0 or f.count >= fs.MAX_COUNT:
        s.log.info("9507 ferramenta recusada", ferramenta=tool)
        _send_pool(s, s, f)
        return
    f.tools[tool - 1] -= 1
    pool = _pool(s, f)
    if tool in fs.TORPEDO:
        fs.torpedo(pool, tool, now)
    else:
        f.hook = fs.THREE if tool == 2 else fs.POWER
    await s.ctx.characters.save(fs.store(snap, f, now))
    _send_pool(s, s, f)
    if tool in fs.TORPEDO:
        _send_infos(s, pool)
