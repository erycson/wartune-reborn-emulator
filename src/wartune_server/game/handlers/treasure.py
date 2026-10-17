"""Mapa do tesouro (8744, 8745): receber um mapa, a contagem do dia e o estado que o cliente mostra.

Receber um mapa (op 1) dá um item de mapa (SonType 219) e conta no dia (``join_tremap_count``). A conta vai
no mesmo ``save`` do item: sem isso dava para receber, relogar e vender o mapa (1000 de ouro) de novo.

Os outros passos dependem do que o servidor não tem: pontos de tesouro no mapa do mundo (escavar, atualizar
a lista, usar um mapa) e batalha de equipe (escavar, receber a recompensa). Esses recebem o estado atual
(4633), que é o que o cliente usa para se atualizar. 8745 (reforço de mapa de guilda) só registra.
"""

from datetime import datetime

from ...domain.models import TreasureMap
from ...protocol.messages import wartune_pb2 as pb
from .. import arena as A
from .. import rewards
from ..builders import login as b
from ..router import router
from ..session import GameSession
from .player import granted

S_TREASURE = 4633
OP_GET, OP_INFO = 1, 6
# ponytail: o oficial sorteia a qualidade do mapa; sem essa tabela, dá sempre o de bronze (2190001)
GET_ITEM = 2190001


def _config(s: GameSession, name: str) -> int:
    row = next(s.ctx.templates.find("ConfigInfos", ConfigName=name), None)
    return int(row["ConfigValue"]) if row else 0


def _book(s: GameSession, now: datetime) -> TreasureMap:
    """O mapa do tesouro do personagem; a contagem do dia zera na primeira leitura do dia."""
    snap = s.snapshot
    assert snap is not None and snap.character.id is not None
    if not snap.treasure:
        snap.treasure.append(TreasureMap(snap.character.id))
    book = snap.treasure[0]
    if book.day != A.today(now):
        book.day, book.join_count = A.today(now), 0
    return book


def _state(s: GameSession, book: TreasureMap, op: int) -> pb.PlayerTreasureMsg:
    return b.complete(
        pb.PlayerTreasureMsg(userId=s.player_id, joinCount=book.join_count, rewardCount=book.reward_count, opType=op)
    )


async def _receive(s: GameSession, book: TreasureMap) -> None:
    snap = s.snapshot
    assert snap is not None
    if book.join_count >= _config(s, "join_tremap_count"):
        s.log.info("8744 mapa recusado", motivo="limite do dia")
        return
    drops = [(GET_ITEM, 1)]
    if not rewards.can_grant(snap, s.ctx.templates, drops):
        s.log.info("8744 mapa recusado", motivo="mochila cheia")
        return
    book.join_count += 1
    new, text = rewards.grant(snap, s.ctx.templates, drops)
    await s.ctx.characters.save(book, *new)
    granted(s, drops, new, text)


@router.on(8744)
async def treasure_map(s: GameSession, msg: pb.PlayerTreasureMsg) -> None:
    book = _book(s, s.ctx.clock.now())
    if msg.opType == OP_GET:
        await _receive(s, book)
    elif msg.opType != OP_INFO:
        s.log.info("8744 recusado", op=msg.opType, motivo="depende de pontos de tesouro ou batalha de equipe")
    s.send(S_TREASURE, _state(s, book, msg.opType))


@router.on(8745)
async def reinforce_treasure(s: GameSession, msg: pb.GuildMsg) -> None:
    s.log.info("8745 reforço de mapa de tesouro sem mapa de guilda", param1=msg.param1)
