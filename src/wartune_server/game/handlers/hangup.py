"""Ganho da campanha (gancho) e PK por convite no mapa da campanha (8293, 8525).

O gancho (ganho offline da campanha) não tem sistema no servidor: o cliente só manda 8293 com
``hookleftWeay`` diferente de zero, e o servidor nunca o põe acima de zero. Então o 8293 é uma
ressincronização: 4200 zerado, sem cobrar nada.

O convite de PK (8525 op 1) precisa da batalha no mapa da campanha, que não existe. O cliente não espera
resposta, então só registramos. Não mandamos 4421 de volta: com a recusa automática ligada
(``SharedManager.refuseInvitation``) o cliente responde 8525 op 3 a qualquer 4421, e isso viraria laço.
"""

from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_HANGUP_STATE = 4200


@router.on(8293)
async def quick_hangup(s: GameSession, _: pb.PayTypeMsg) -> None:
    s.send(S_HANGUP_STATE, pb.HangupInfoMsg(leftWeay=0, isStartHangup=False, addWeay=0))


@router.on(8525)
async def map_pk(s: GameSession, msg: pb.HangupAttackMsg) -> None:
    """op 1 convite, 2 aceita, 3 recusa; sem op é o ataque no campo de animais (sem batalha aqui)."""
    s.log.info("8525 sem batalha de PK no mapa da campanha", op=msg.op, alvo=msg.defenceId)
