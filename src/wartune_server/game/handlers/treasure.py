"""Mapa do tesouro (8744, 8745): estado do jogador e o que o servidor consegue responder.

Só a info (op 6) é respondida com o estado (4633). As outras operações dependem de pontos de tesouro no
mapa do mundo (dig, refresh, use) e de batalha de equipe (dig, reward), que o servidor não tem: recusam com
o estado atual, que é o que o cliente usa para se atualizar. 8745 (reforço de mapa de guilda) só registra.
"""

from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession

S_TREASURE = 4633
OP_INFO = 6


def _state(s: GameSession, op: int) -> pb.PlayerTreasureMsg:
    return b.complete(pb.PlayerTreasureMsg(userId=s.player_id, opType=op))


@router.on(8744)
async def treasure_map(s: GameSession, msg: pb.PlayerTreasureMsg) -> None:
    if msg.opType != OP_INFO:
        s.log.info("8744 recusado", op=msg.opType, motivo="sem pontos de tesouro ou batalha de equipe")
    s.send(S_TREASURE, _state(s, msg.opType))


@router.on(8745)
async def reinforce_treasure(s: GameSession, msg: pb.GuildMsg) -> None:
    s.log.info("8745 reforço de mapa de tesouro sem mapa de guilda", param1=msg.param1)
