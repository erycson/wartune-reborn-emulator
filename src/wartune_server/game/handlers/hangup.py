"""Ganho da campanha (gancho) e PK por convite no mapa da campanha (8292, 8293, 8295, 8525).

O gancho (ganho offline da campanha) não tem sistema no servidor: o cliente só manda 8293 com
``hookleftWeay`` diferente de zero, e o servidor nunca o põe acima de zero. Então o 8293 é uma
ressincronização: 4200 zerado, sem cobrar nada. O 8292 (cancelar o gancho) não tem gancho para cancelar:
é a mesma resposta. O 8295 pede o estado das salas do gancho (Altar of Ennoblement, ``HookFrame``), e o cliente só
termina o pré-carregamento quando ele chega (``HookContorler.__updateRoomState``).

O convite de PK (8525 op 1) precisa da batalha no mapa da campanha, que não existe. O cliente não espera
resposta, então só registramos. Não mandamos 4421 de volta: com a recusa automática ligada
(``SharedManager.refuseInvitation``) o cliente responde 8525 op 3 a qualquer 4421, e isso viraria laço.
"""

from ...protocol.messages import wartune_pb2 as pb
from ..builders import login as b
from ..router import router
from ..session import GameSession

S_HANGUP_STATE, S_HANGUP_ROOM = 4200, 4204
HOOK_TYPE = 3  # Campaigns.Types das salas do gancho (7001-7009): o HookFrame desenha uma por campanha


def _no_hangup(s: GameSession) -> None:
    s.send(S_HANGUP_STATE, pb.HangupInfoMsg(leftWeay=0, isStartHangup=False, addWeay=0))


@router.on(8293)
async def quick_hangup(s: GameSession, _: pb.PayTypeMsg) -> None:
    _no_hangup(s)


@router.on(8292)
async def cancel_hangup(s: GameSession, _: object) -> None:
    """Cancela o gancho (``HookTimeView``, depois da confirmação). Sem gancho no servidor: 4200 zerado."""
    _no_hangup(s)


@router.on(8295)
async def hangup_room_state(s: GameSession, _: object) -> None:
    """Estado das salas do gancho: uma entrada por campanha, senão o ``HookItem`` lê ``roomState[id]`` indefinido e
    a janela quebra. ``curCount`` 0 (ninguém em gancho aqui); ``maxCount`` = ``Capacity`` da campanha (*dedução*): o
    ``HookContorler.getStateByCount`` mostra "cheia" com ``curCount >= maxCount / 2``."""
    rows = sorted(s.ctx.templates.find("Campaigns", Types=HOOK_TYPE), key=lambda r: int(r["CampaignId"]))
    out = pb.HangupStateListMsg(maxCount=max((int(r["Capacity"]) for r in rows), default=0))
    for r in rows:
        out.hangupState.add(campaignId=int(r["CampaignId"]), curCount=0)
    s.send(S_HANGUP_ROOM, b.complete(out))


@router.on(8525)
async def map_pk(s: GameSession, msg: pb.HangupAttackMsg) -> None:
    """op 1 convite, 2 aceita, 3 recusa; sem op é o ataque no campo de animais (sem batalha aqui)."""
    s.log.info("8525 sem batalha de PK no mapa da campanha", op=msg.op, alvo=msg.defenceId)
