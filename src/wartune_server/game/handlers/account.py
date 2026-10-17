"""Conta e segurança: anti-vício (AAS), senha secundária, captcha, celular, acelerador, guia QTE.

Detalhes e fontes em ``docs/diversos.md``.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timedelta

from ...domain.models import Character
from ...protocol.messages import wartune_pb2 as pb
from ..router import router
from ..session import GameSession

S_AAS_CHANGE, S_VICE_PASSWORD, S_CHECK_SEND, S_NODE_STAND = 4172, 4696, 4420, 4208
VP_CHECK, VP_SET, VP_CHANGE, VP_RESET = 1, 2, 3, 4  # VicePasswordMsg.opType (VicePasswordUtil.as)
VP_RESET_DAYS = 3  # ponytail: prazo do reset não está no cliente nem nas capturas; ajustar se aparecer
ACCELERATOR_PERIOD = 60  # s: o cliente manda 20010 a cada 60 ticks do relógio local
ACCELERATOR_SLACK = 0.8  # abaixo de 80% do período conta como relógio acelerado
PIN = re.compile(r"\d{6}")


def _hash(c: Character, password: str) -> str:
    return hashlib.sha256(f"{c.id}:{password}".encode()).hexdigest()


def _valid_password(p: str) -> bool:
    """6 dígitos, sem repetir tudo e sem sequência (``VicePasswordUtil.strCheck/numCheck``)."""
    if not PIN.fullmatch(p) or len(set(p)) == 1:
        return False
    steps = {int(b) - int(a) for a, b in zip(p, p[1:], strict=False)}
    return steps not in ({1}, {-1})


def expire_vice_reset(c: Character, now: datetime) -> bool:
    """Reset pedido há ``VP_RESET_DAYS``: apaga a senha. True se mudou (gravar)."""
    if c.vice_reset_at is None or now - c.vice_reset_at < timedelta(days=VP_RESET_DAYS):
        return False
    c.vice_password, c.vice_reset_at = "", None
    return True


# -- anti-vício -------------------------------------------------------------------------------


def _adult_age(card_id: str, now: datetime) -> int:
    """Idade pelo documento chinês de 18 posições (nascimento nas posições 7-14); 0 se inválido."""
    if not re.fullmatch(r"\d{17}[\dXx]", card_id):
        return 0
    try:
        born = datetime.strptime(card_id[6:14], "%Y%m%d")
    except ValueError:
        return 0
    return now.year - born.year - ((now.month, now.day) < (born.month, born.day))


@router.on(8260)
async def aas_change(s: GameSession, msg: pb.PlayerAASReqMsg) -> None:
    # só abre com ConfigManager.info.AAS (mandamos sysSwitch=false no 4173); não gravamos documento
    age = _adult_age(msg.cardId, s.ctx.clock.now())
    ok = bool(msg.cardName.strip()) and age > 0
    s.send(S_AAS_CHANGE, pb.PlayerAASRspMsg(result=ok, age=age, cardId=msg.cardId if ok else ""))


@router.on(8261)
async def aas_refresh(s: GameSession, msg: pb.PlayerAASRefreshMsg) -> None:
    # tempo online do anti-vício; desligado aqui (4173 isCloseAAS=true), o oficial não responde
    s.log.debug("8261 tempo AAS", segundos=msg.aasOnlineTime)


@router.on(8620)
async def aas_switch(s: GameSession, _: pb.PlayerAASRefreshMsg) -> None:
    # o cliente só manda depois de a plataforma (Kaixin) confirmar identidade e maioridade
    s.send(S_AAS_CHANGE, pb.PlayerAASRspMsg(result=True, age=18, cardId=""))


# -- senha secundária -------------------------------------------------------------------------


@router.on(8806)
async def vice_password(s: GameSession, msg: pb.VicePasswordMsg) -> None:
    snap = s.snapshot
    assert snap is not None
    c, now = snap.character, s.ctx.clock.now()
    changed = expire_vice_reset(c, now)
    ok = False
    if msg.opType == VP_CHECK:
        ok = bool(c.vice_password) and _hash(c, msg.inputPass) == c.vice_password
        s.vice_confirmed = s.vice_confirmed or ok
    elif msg.opType == VP_SET:
        ok = not c.vice_password and msg.inputPass == msg.newPass and _valid_password(msg.inputPass)
        if ok:
            c.vice_password = _hash(c, msg.inputPass)
    elif msg.opType == VP_CHANGE:
        right = bool(c.vice_password) and _hash(c, msg.prePass) == c.vice_password
        ok = right and msg.inputPass == msg.newPass and _valid_password(msg.inputPass)
        if ok:
            c.vice_password, c.vice_reset_at = _hash(c, msg.inputPass), None
    elif msg.opType == VP_RESET:
        ok = bool(c.vice_password) and c.vice_reset_at is None
        if ok:
            c.vice_reset_at = now
    else:
        s.log.info("8806 opType desconhecido", op=msg.opType)
        return
    if ok and msg.opType != VP_CHECK:
        s.vice_confirmed = msg.opType != VP_RESET
    if ok or changed:
        await s.ctx.characters.save(c)
    s.send(S_VICE_PASSWORD, pb.VicePasswordMsg(opType=msg.opType, result=int(ok)))


# -- verificações -----------------------------------------------------------------------------


@router.on(8516)
async def check_show_code(s: GameSession, _: object) -> None:
    pass  # "tem captcha para mim?": o servidor não aplica captcha (4402), e o oficial só responde quando tem


@router.on(8514)
async def check_code(s: GameSession, msg: pb.CheckImageMsg) -> None:
    s.log.info("8514 resposta de captcha sem captcha pendente", resposta=msg.result[:32])


@router.on(8524)
async def check_send(s: GameSession, _: pb.CheckSend) -> None:
    # tarefa de vincular celular: -1 = telefone ainda não informado (o SMS é por HTTP, não existe aqui)
    s.send(S_CHECK_SEND, pb.CheckSend(canSend=-1))


@router.on(8352)
async def user_pin(s: GameSession, _: pb.UserPin) -> None:
    s.log.info("8352 código de SMS recusado: vínculo de celular não existe neste servidor")


@router.on(20009)
async def accelerator(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    s.log.warning("20009 cliente acusou acelerador/ferramenta", tipo=msg.param1)


@router.on(20010)
async def check_accelerator(s: GameSession, _: object) -> None:
    """Batida de 60 s do relógio do cliente; chegando mais rápido, o relógio dele está acelerado.

    O oficial não responde (``replay_packets.json``: 12 pacotes 20010, nenhuma resposta); só registra.
    """
    now = time.monotonic()
    last, s.accelerator_at = s.accelerator_at, now
    if last is not None and now - last < ACCELERATOR_PERIOD * ACCELERATOR_SLACK:
        s.log.warning("20010 adiantado: possível speed-hack", intervalo=round(now - last, 1))


@router.on(5041)
async def micro_client_info(s: GameSession, _: pb.SimplePropertyMsg) -> None:
    pass  # credenciais da plataforma do launcher (param4/5/6/12): não usadas e não registradas em log


@router.on(5020)
async def login_state(s: GameSession, _: object) -> None:
    pass  # SocketSendManager.loginState() não tem chamador; o estado vai no 6 do login


@router.on(8598)
async def class_check(s: GameSession, msg: pb.SimplePropertyMsg) -> None:
    # resposta ao desafio 4490 (classe existe no cliente?); não mandamos 4490, então só registra
    s.log.info("8598 resposta de integridade", classe=msg.param5[:64], ausente=msg.param7)


@router.on(8302)
async def qte_guide_finished(s: GameSession, _: object) -> None:
    """Guia da skill QTE concluído: volta no PlayerMsg.qteGuide e o cliente não mostra de novo."""
    c = s.snapshot.character if s.snapshot else None
    if c is None or c.qte_guide:
        return
    c.qte_guide = 1
    await s.ctx.characters.save(c)


@router.on(8301)
async def node_state(s: GameSession, msg: pb.PlayerNodeStateMsg) -> None:
    """Saiu de perto do nó de teleporte (``TranseferWaitMediator``): cancela a espera com 4208."""
    c = s.campaign
    if c is None or msg.mapId != c.map_id or c.node(msg.nodeId) is None:
        return
    state = pb.PlayerNodeStateMsg(mapId=c.map_id, nodeId=msg.nodeId, isStand=msg.isStand, armyId=s.player_id)
    s.send(S_NODE_STAND, state)  # ponytail: sala de um jogador só; broadcast quando houver sala compartilhada


@router.on(8353)
async def captain_speak(s: GameSession, msg: pb.CaptainSpeakMsg) -> None:
    # convite rápido do capitão de sala PvE; salas compartilhadas não existem ainda (docs/diversos.md)
    s.log.info("8353 convite rápido sem sala", linhas=len(msg.inviteContent))
