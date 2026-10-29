"""Pedidos de batalha que não mudam a simulação (ou que o cliente quase nunca manda).

Os básicos (10007, 10008, 10010, 10020, 10022) ficam em ``campaign.py``. Comportamento do cliente
em ``docs/batalha.md``.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..battle import Battle
from ..router import router
from ..session import GameSession

S_FIGHT_MODE, S_ITEM_RESULT, S_VIEW_INFO = 77, 158, 4804
REFUSED = 1  # ItemUseResultMsg.result != 0: o cliente tira a marca da skill e libera a barra
BATTLE_ITEM, TRIAL_ITEM = 1, 2  # ItemUseResultMsg.type (2 prova, 3 casal: só importam no sucesso)
VIEW_QUIT, VIEW_CHECK, VIEW_USER, VIEW_TEAM = -1, 0, 1, 2  # BattleViewManager: QUIT, CHECK, VIEW_ZS, VIEW_TT


def _battle(s: GameSession, battle_id: str) -> Battle | None:
    return s.battle if s.battle is not None and s.battle.id == battle_id else None


@router.on(10018)
async def reinforce_load_over(s: GameSession, msg: pb.LoadOverMsg) -> None:
    """Igual ao 10007 para quem entra como reforço (``useWay != 0``)."""
    if (battle := _battle(s, msg.battleId)) is not None:
        battle.load_over()


@router.on(10016)
async def fight_mode(s: GameSession, msg: pb.AttackModeMsg) -> None:
    """Postura ataque (2) / defesa (1): o cliente espera o 77 de volta para liberar os botões."""
    if _battle(s, msg.battleId) is None:
        return
    # ponytail: a postura não muda o dano (o efeito dela não tem captura)
    s.send(S_FIGHT_MODE, pb.AttackModeMsg(userId=s.player_id, battleId=msg.battleId, mode=msg.mode, fmTurn=0, heroSp=0))


@router.on(10507)
async def trial_prop(s: GameSession, msg: pb.BattleItemMsg) -> None:
    """Spire Rune na luta da Spire (``sendUseBattleTrialProp``): 158 ``type`` 2 com ``uItemId`` = o índice dela no
    ``HeroMsg.trials`` e ``count`` = as cargas que sobram (cliente ``__useBattleItemServerBack``); sem carga, recusa."""
    if (battle := _battle(s, msg.battleId)) is None:
        return
    left = battle.use_trial(msg.skillTempId)
    if left is None or battle.player is None:
        await battle_item(s, msg)
        return
    reply = pb.ItemUseResultMsg(uItemId=list(battle.trials).index(msg.skillTempId), count=left, result=0)
    reply.livingId, reply.tempId, reply.type = battle.player.living_id, msg.skillTempId, TRIAL_ITEM
    s.send(S_ITEM_RESULT, reply)


@router.on(10499, 10509)
async def battle_item(s: GameSession, msg: pb.BattleItemMsg) -> None:
    """Item e skill de casal: nenhum existe aqui ainda, então recusa (158). A Spire Rune sem carga cai aqui."""
    if _battle(s, msg.battleId) is None:
        return
    s.log.info("item de batalha recusado (sem itens de batalha)", pedido=str(msg))
    reply = pb.ItemUseResultMsg(uItemId=msg.uItemId, bagPos=msg.bagPos, count=0, result=REFUSED)
    reply.livingId, reply.tempId, reply.type = msg.userId, msg.skillTempId, BATTLE_ITEM
    s.send(S_ITEM_RESULT, reply)


def _watched(s: GameSession, kind: int, msg: pb.BattleViewMsg) -> Battle | None:
    """A luta em andamento: ``kind`` 1 pela sessão do ``userId``, 2 pelo id da luta (``teamUuid``)."""
    if kind == VIEW_USER:
        other = s.ctx.online.get(msg.userId)
        battle = other.battle if other is not None else None
    elif kind == VIEW_TEAM:
        battle = next((o.battle for o in s.ctx.online.sessions() if o.battle and o.battle.id == msg.teamUuid), None)
    else:
        battle = None
    return battle if battle is not None and battle.running else None


@router.on(8985)
async def battle_view(s: GameSession, msg: pb.BattleViewMsg) -> None:
    """Assistir a luta de outro (cliente ``BattleViewManager.sendOperationToServer``): ``type`` 0 consulta (o alvo
    vem do ``sonType``), 1/2 entra, -1 sai. Consulta: 4804 ``param1`` = espera em ms (0: o cliente manda o pedido de
    entrar na hora) e ``param7`` = "acabou". Entrar: a luta manda o 157/156 e daí tudo (``Battle.watch``); sair ou o
    fim da luta: 4803. Nenhuma tela do cliente inglês chama ``sendOperationToServer`` fora do próprio manager e do
    ``BattleCDViewFrame`` (grep em decomp): fica pronto para quando houver."""
    if msg.type == VIEW_QUIT:
        for o in s.ctx.online.sessions():
            if o.battle is not None and s in o.battle.viewers:
                o.battle.unwatch(s)
        return
    battle = _watched(s, msg.sonType if msg.type == VIEW_CHECK else msg.type, msg)
    if battle is not None and s.battle is None and (msg.type == VIEW_CHECK or battle.watch(s)):
        if msg.type == VIEW_CHECK:
            s.send(S_VIEW_INFO, pb.SimplePropertyMsg(param1=0, param7=False))
        return
    # param7 True em toda recusa: com False e espera 0 o cliente repete o pedido sem parar
    s.send(S_VIEW_INFO, pb.SimplePropertyMsg(param1=0, param7=True))


@router.on(10015, 10497, 10516, 10003)
async def ignored(s: GameSession, msg: object) -> None:
    """Sem resposta no cliente: QTE (10015, bônus não modelado), remover batalha (10497, código
    morto), skill do filho (10516, não há filhos) e a batalha de depuração (10003). O combo (8282) vai para o
    137 da masmorra (``handlers/campaign.py``); o 8283 (tirar efeito de pergaminho) para ``handlers/items.py``."""
    s.log.info("pacote de batalha ignorado", pedido=str(msg))
