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
BATTLE_ITEM = 1  # ItemUseResultMsg.type (2 prova, 3 casal: só importam no sucesso)


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


@router.on(10499, 10507, 10509)
async def battle_item(s: GameSession, msg: pb.BattleItemMsg) -> None:
    """Item, prova (battleType 25) e skill de casal: nenhum existe aqui ainda, então recusa (158)."""
    if _battle(s, msg.battleId) is None:
        return
    s.log.info("item de batalha recusado (sem itens de batalha)", pedido=str(msg))
    reply = pb.ItemUseResultMsg(uItemId=msg.uItemId, bagPos=msg.bagPos, count=0, result=REFUSED)
    reply.livingId, reply.tempId, reply.type = msg.userId, msg.skillTempId, BATTLE_ITEM
    s.send(S_ITEM_RESULT, reply)


@router.on(8985)
async def battle_view(s: GameSession, msg: pb.BattleViewMsg) -> None:
    """Assistir batalha de outro: não há batalhas assistíveis; 4804 com param7 = "acabou" (só um aviso)."""
    s.send(S_VIEW_INFO, pb.SimplePropertyMsg(param1=0, param7=True))


@router.on(10015, 10497, 10516, 10003)
async def ignored(s: GameSession, msg: object) -> None:
    """Sem resposta no cliente: QTE (10015, bônus não modelado), remover batalha (10497, código
    morto), skill do filho (10516, não há filhos) e a batalha de depuração (10003). O combo (8282) vai para o
    137 da masmorra (``handlers/campaign.py``); o 8283 (tirar efeito de pergaminho) para ``handlers/items.py``."""
    s.log.info("pacote de batalha ignorado", pedido=str(msg))
