"""Senhores (Warlords, "众神之战") e Senhores de casal (Mate Lords): evento fechado.

O torneio é entre servidores, com fases (preliminar, final, aposta) agendadas pelo oficial; não há
agenda nem adversários aqui. O servidor responde o que o cliente usa para mostrar "não aberto" sem
travar (``docs/pvp.md``): processo 0, listas vazias, agenda no passado no login.
"""

from __future__ import annotations

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_MAIN, S_START, S_BET_LIST, S_AWARD_LIST, S_OPEN, S_CLOSE, S_LOCAL_FINAL = 4529, 4530, 4531, 4532, 4535, 4536, 4537
S_TIMER, S_MATE_MAIN = 4776, 4799
CLOSED = 0  # WarlordsModel.process READY
LORDS_TIMER = 4  # TimerInfoMsg.type do 4776 do login (tutorial_en #106)
PAST = "2000-01-01 00:00:00"  # datas no passado: o botão da barra superior fica escondido


def login(s: GameSession) -> None:
    """4776 e 4535 do login: o oficial manda a agenda; aqui ela já passou."""
    timer = pb.TimerInfoListMsg()
    timer.timerInfo.add(
        type=LORDS_TIMER, index=0, name="", readyOpen=PAST, readyStop=PAST, finalOpen=PAST, finalStop=PAST, param1="0"
    )
    s.send(S_TIMER, timer)
    s.send(S_OPEN, pb.SimplePropertyMsg(param1=CLOSED))


def _orders(**fields: object) -> pb.LordsOrderListMsg:
    return pb.LordsOrderListMsg(param1=0, param2=0, **fields)  # type: ignore[arg-type]


@router.on(8711)
async def main_board(s: GameSession, _: object) -> None:
    """Estátuas do mapa do céu: nenhum campeão; processo 0 faz o cliente recusar a sala."""
    s.send(S_MAIN, _orders(param3="0", currTurn=0, maxTurn=0, score=0, myOrder=0))


@router.on(8714, 8710)
async def start(s: GameSession, _: object) -> None:
    """Sala (8714 repete a cada 5 s até o 4530) e "lutar" (8710): fechado, então expulsa (4536)."""
    s.send(S_START, _orders())
    s.send(S_CLOSE)


@router.on(8715, 8716)
async def bet_list(s: GameSession, msg: object) -> None:
    """Lista de apostas (8715) e apostar (8716): sem final, ninguém para apostar; nada é cobrado."""
    s.send(S_BET_LIST, _orders(param3="0", param4="0"))


@router.on(8718)
async def award_list(s: GameSession, _: object) -> None:
    s.send(S_AWARD_LIST, _orders())


@router.on(8721)
async def local_final(s: GameSession, _: object) -> None:
    s.send(S_LOCAL_FINAL, _orders(myOrder=0))


@router.on(8717, 8720)
async def leave_or_reward(s: GameSession, _: object) -> None:
    """Sair da sala (o cliente não espera resposta) e recompensa da final (só aparece depois do 4533,
    que nunca é mandado): nada a fazer."""
    s.log.info("senhores: pedido sem efeito (evento fechado)")


@router.on(8979, 8975, 8976, 8981)
async def mate_lords(s: GameSession, _: object) -> None:
    """Info, inscrição, sala e inspirar dos Senhores de casal: evento fechado (4799 sem inscrição)."""
    s.send(S_MATE_MAIN, pb.MateLordsListMsg(isSign=False, isOpen=False, isOver=True, inspirLevel=0))
