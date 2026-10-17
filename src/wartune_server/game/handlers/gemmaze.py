"""Labirinto de gemas (9508..9517): abrir (4922), trocar (4923/4924), comprar movimentos (4927), receber tudo.

Regra da troca e da cascata em ``game/gemmaze.py``. O estado fica numa linha ``EventState`` (chave
``gemmaze``, ``text`` em JSON). Cada pedido valida tudo antes, muda o snapshot, grava uma vez e só então
manda os pacotes.

Fontes: *(visto)* captura ``av_askeri_ve_odul_toplama.json`` (4922, 4923 por passo, 4924 depois de cada
movimento, 115 da bolsa 24 e o "Başarıyla alındı!" do 9517) e o login da replay (4922 de personagem novo);
*(cliente)* ``GemMazeManager``, ``GemMazeView``, ``GemMazeFrame`` (compra de movimentos), ``GemMazeBagView``.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Any

from ...domain.models import BagType, EventState, Item, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from ...services import ledger
from ...templates.repository import GameTemplates
from .. import bag, rewards
from .. import events as ev
from .. import gemmaze as gm
from ..builders import login as b
from ..builders.player import item_moved
from ..router import router
from ..session import GameSession
from .player import alert

KEY = "gemmaze"  # EventState do tabuleiro (text = Game.dump)
MAZE_SIZE = 48  # (cliente) GemMazeView: com 48 itens na bolsa a troca nem sai
BOX_IDS = (2131035, 2131036, 2131037, 2131038, 2131039)  # (visto) 4922: as 5 caixas de tesouro do labirinto
OP_OK = 1  # (visto) playerId da 4924 em todas as capturas; o cliente só usa a mensagem para liberar a troca
S_INFO, S_UPDATE, S_OP, S_CHAT, S_ITEMS, S_BUY, S_BOX = 4922, 4923, 4924, 83, 115, 4927, 4928
_rng = random.Random()


def _snap(s: GameSession) -> PlayerSnapshot:
    snap = s.snapshot
    assert snap is not None
    return snap


def _send(s: GameSession, code: int, msg: Any) -> None:
    s.send(code, b.complete(msg))


def _game(snap: PlayerSnapshot) -> gm.Game:
    """O tabuleiro gravado, ou um novo (não gravado: quem muda o estado é que grava)."""
    row = ev.peek(snap, KEY)
    if row is not None and row.text:
        return gm.Game.load(row.text)
    return gm.new_game(_rng)


def _save(snap: PlayerSnapshot, game: gm.Game, now: Any) -> EventState:
    st = ev.state(snap, KEY, now)
    st.text, st.updated_at = game.dump(), now
    return st


def _info_msg(game: gm.Game) -> pb.GemMazeInfoMsg:
    return pb.GemMazeInfoMsg(
        allGems=[pb.GemInfoMsg(mark=m, color=c) for m, c in enumerate(game.board)],
        score=game.score,
        weekScore=game.week,
        timesLeft=game.times,
        buyTimesLeft=0,  # ponytail: o oficial manda 0 para personagem novo; o contador não foi capturado
        helpTimesLeft=game.help,
        gemLevel=game.level,
        curExp=game.exp,
        maxExp=game.max_exp,
        boxMark=0,
        scoreOrder=0,  # ponytail: ranking semanal não existe aqui (o oficial manda 1771 para um jogador de topo)
        boxesId=BOX_IDS,
    )


def _buy_info(templates: GameTemplates) -> tuple[int, int, int]:
    """``Gem_Maze_BuyInfo`` = movimentos por compra, diamantes por compra, teto de movimentos (99 = 89 + 10,
    o mesmo limite do cliente, que não deixa comprar com 90 ou mais)."""
    per, cost, cap = (int(x) for x in ev.config(templates, "Gem_Maze_BuyInfo", "10,5,99").split(","))
    return per, cost, cap


def _maze_fits(snap: PlayerSnapshot, templates: GameTemplates, rewards: Iterable[int]) -> bool:
    """Cabem todos os prêmios na bolsa do labirinto? Pilha empilha até o ``MaxCount``; senão abre espaço."""
    held = [i for i in snap.items if i.bag_type == BagType.MAZE]
    free = MAZE_SIZE - len(held)
    room: dict[int, int] = {}
    for tid in rewards:
        top = bag.max_count(templates, tid)
        if tid not in room:
            room[tid] = sum(top - i.count for i in held if i.template_id == tid and i.count < top)
        if room[tid] > 0:
            room[tid] -= 1
            continue
        free -= 1
        room[tid] += top - 1
    return free >= 0


def _add_maze(snap: PlayerSnapshot, templates: GameTemplates, tid: int, now: Any) -> Item:
    """Um prêmio na bolsa do labirinto: empilha na primeira pilha com espaço, senão no menor espaço livre."""
    held = [i for i in snap.items if i.bag_type == BagType.MAZE]
    top = bag.max_count(templates, tid)
    stack = next((i for i in sorted(held, key=lambda i: i.pos) if i.template_id == tid and i.count < top), None)
    if stack is not None:
        stack.count += 1
        return stack
    used = {i.pos for i in held}
    item = bag.new_item(snap, templates, tid, 1)
    item.bag_type = BagType.MAZE
    item.pos = next(p for p in range(MAZE_SIZE) if p not in used)
    snap.items.append(item)
    return item


@router.on(9508)
async def open_maze(s: GameSession, _: object) -> None:
    """Abre o labirinto (4922). Sem tabuleiro gravado, sorteia um e grava: abrir de novo mostra o mesmo."""
    snap = _snap(s)
    now = s.ctx.clock.now()
    if ev.peek(snap, KEY) is None:
        st = _save(snap, _game(snap), now)
        await s.ctx.characters.save(st)
    _send(s, S_INFO, _info_msg(_game(snap)))


@router.on(9509)
async def move_gem(s: GameSession, msg: pb.GemMoveMsg) -> None:
    """Troca ``beginMark``/``endMark``: resolve a cascata inteira em memória, põe cada prêmio na bolsa 24,
    grava uma vez e manda, por passo, o 115 (bolsa), os "Puan"/"EXP" e o 4923; por fim o 4924 libera a troca.
    Pedido inválido ou bolsa sem espaço para os prêmios: nada muda e só o 4924 (o cliente não trava)."""
    snap = _snap(s)
    now = s.ctx.clock.now()
    templates = s.ctx.templates
    game = _game(snap)
    result = gm.play(game, msg.beginMark, msg.endMark, _rng)
    if result is None or not _maze_fits(snap, templates, [p.reward for p in result.steps]):
        s.log.info("9509 recusado", inicio=msg.beginMark, fim=msg.endMark)
        _send(s, S_OP, pb.GemInviteOpMsg(playerId=OP_OK))
        return
    out: list[tuple[int, Any]] = []
    changed: list[Item] = []
    for step in result.steps:
        # ponytail: sem subida de nível (a tabela de EXP por nível não foi capturada): curExp passa de maxExp
        game.exp += step.exp
        item = _add_maze(snap, templates, step.reward, now)
        if item not in changed:
            changed.append(item)
        out.append((S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Puan {step.points}")))
        out.append((S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"EXP {step.exp}")))
        out.append((S_ITEMS, item_moved(BagType.MAZE, 0, item.pos, item, s.player_id)))
        out.append((S_UPDATE, _update_msg(step, game)))
        name = (templates.get("ItemTempInfos", step.reward) or {}).get("TemplateName", str(step.reward))
        out.append((S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=f"Kazanılan:{name} x 1")))
    game.board, game.times = result.board, result.times
    game.score += sum(p.points for p in result.steps)
    # ponytail: o semanal soma o mesmo que o total (dedução; a regra de reset semanal não existe aqui)
    game.week += sum(p.points for p in result.steps)
    st = _save(snap, game, now)
    await s.ctx.characters.save(st, *changed)
    for code, m in out:
        _send(s, code, m)
    _send(s, S_OP, pb.GemInviteOpMsg(playerId=OP_OK))


def _update_msg(step: gm.Step, game: gm.Game) -> pb.GemInfoUpdateMsg:
    """4923 de um passo: ``gemDel`` (cor 0), ``gemAdd`` (só as gemas novas: o cliente faz a gravidade)."""
    return pb.GemInfoUpdateMsg(
        gemDel=[pb.GemInfoMsg(mark=m, color=0) for m in step.dels],
        gemAdd=[pb.GemInfoMsg(mark=m, color=c) for m, c in step.adds],
        score=[step.points],
        curExp=game.exp,
        maxExp=game.max_exp,
        gemLevel=game.level,
        scoreOrder=0,
        rewardInfo=[pb.RewardInfoMsg(rewardId=step.reward)],
    )


@router.on(9510)
async def invite_friend(s: GameSession, _: object) -> None:
    """Pedir ajuda a um amigo: sem amigos aqui (o 4925 nunca sai). O 4924 só libera a troca do cliente."""
    s.log.info("9510 recusado: ajuda de amigo não existe no servidor")
    _send(s, S_OP, pb.GemInviteOpMsg(playerId=OP_OK))


@router.on(9515)
async def help_friend(s: GameSession, _: object) -> None:
    """Resposta de quem ajuda (sem convite pendente, porque o 4925 não sai): só registra."""
    s.log.info("9515 recusado: ajuda de amigo não existe no servidor")


@router.on(9513)
async def reward_box(s: GameSession, _: object) -> None:
    """Caixa de tesouro do labirinto (2131035..39). O limiar de pontos de cada caixa não está nos templates:
    responde 4928 vazio, com a marca atual (sempre 0 aqui)."""
    s.log.info("9513 recusado: limiar das caixas não capturado")
    _send(s, S_BOX, pb.GetRewardBoxRspMsg(boxGetMark=0))


@router.on(9516)
async def buy_times(s: GameSession, msg: pb.GemMazeBuyTimesMsg) -> None:
    """Compra movimentos (``Gem_Maze_BuyInfo``): ``buyTypes`` 2 gasta diamante vinculado, 1 diamante.
    O 4927 faz o cliente somar os movimentos, por isso só sai quando a compra vale."""
    snap = _snap(s)
    now = s.ctx.clock.now()
    per, cost, cap = _buy_info(s.ctx.templates)
    game = _game(snap)
    if game.times + per > cap:
        s.log.info("9516 recusado: teto de movimentos", atual=game.times)
        return
    # ponytail: o template não diz a moeda nem o limite diário: diamante (ou vinculado com buyTypes 2) é dedução
    spent = ledger.spend(snap.character, cost, "gemmaze_buy", now, bound=msg.buyTypes == 2, ref=str(per))
    if spent is None:
        s.log.info("9516 sem diamante")
        return
    game.times += per
    st = _save(snap, game, now)
    await s.ctx.characters.save(snap.character, st, spent)
    _send(s, S_BUY, pb.GemMazeBuyTimesRspMsg(moveTimesLeft=game.times))


@router.on(9517)
async def get_all(s: GameSession, _: object) -> None:
    """Receber tudo: a bolsa do labirinto vai para a mochila, e só se couber tudo. O cliente não tem aviso
    de mochila cheia para isso, então a recusa fica só no log."""
    snap = _snap(s)
    now = s.ctx.clock.now()
    templates = s.ctx.templates
    maze = [i for i in snap.items if i.bag_type == BagType.MAZE]
    if not maze:
        return
    if not bag.fits(snap, templates, [(i.template_id, i.count) for i in maze], now):
        s.log.info("9517 recusado: mochila sem espaço", itens=len(maze))
        return
    for item in maze:
        snap.items.remove(item)
    changed: list[Item] = []
    for item in maze:
        for new in bag.add(snap, templates, item.template_id, item.count, now):
            if new not in changed:
                changed.append(new)
    await s.ctx.characters.save(*changed, delete=tuple(maze))
    removed = pb.ItemMovedListMsg()
    for item in maze:
        removed.moved.add(changeType=BagType.MAZE, changeObjId=0, changePos=item.pos)
    _send(s, S_ITEMS, removed)
    _send(s, S_ITEMS, rewards.items_msg(changed, s.player_id))
    alert(s, "Başarıyla alındı!")


def login_push(s: GameSession) -> None:
    """Login: o 4922 só quando a conta já tem tabuleiro gravado. O login.json (4638 e 4640, #93-94) não tem
    nenhum 4922; o replay (pacotes 10 e 12, depois do 4900) tem, com o tabuleiro já aberto (*dedução*). Não grava."""
    snap = _snap(s)
    if ev.peek(snap, KEY) is not None:
        _send(s, S_INFO, _info_msg(_game(snap)))
