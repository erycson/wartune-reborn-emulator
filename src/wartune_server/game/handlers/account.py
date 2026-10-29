"""Conta e segurança: anti-vício (AAS), senha secundária, captcha, celular, acelerador, guia QTE.

Detalhes e fontes em ``docs/diversos.md``.
"""

from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from ...domain.models import Character, PlayerSnapshot
from ...protocol.messages import wartune_pb2 as pb
from .. import events as gev
from .. import rewards, rules, space, taxas
from ..router import router
from ..session import GameSession
from .chat import scene_key

S_AAS_CHANGE, S_VICE_PASSWORD, S_CHECK_SEND, S_NODE_STAND = 4172, 4696, 4420, 4208
S_CHAT, S_ALERT, S_ITEMS = 83, 111, 115
VP_CHECK, VP_SET, VP_CHANGE, VP_RESET = 1, 2, 3, 4  # VicePasswordMsg.opType (VicePasswordUtil.as)
VP_FIRST = 6  # opType 6: result 1 = a recompensa da primeira senha ainda está lá (PlayerInfo.needShowReward)
FIRST_KEY = "vice_reward"  # event_states: a recompensa da primeira senha já saiu

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


def expire_vice_reset(c: Character, now: datetime, settings: Mapping[str, Any]) -> bool:
    """Reset pedido há ``taxas.vp_reset_days`` (0134, TODO(inventado)): apaga a senha. True se mudou (gravar)."""
    if c.vice_reset_at is None or now - c.vice_reset_at < timedelta(days=int(taxas.get(settings, "vp_reset_days"))):
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
    changed = expire_vice_reset(c, now, s.ctx.world.settings)
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
    first = _first_reward(s) if ok and msg.opType == VP_SET else []
    text = ""
    if first:
        await _grant_first(s, first)
        # (visto) oficial_encantar #270-#273: itens antes das moedas, "Congrats! You earned: Lvl. 1-3 Gem Pack x1,
        # Mount Training Whip x20, 5,000 Gold, 2,000 Daru" no 111, o 4696 6/0, o 2/1 e o mesmo texto no 83
        order = [d for d in first if d[0] > 0] + [d for d in first if d[0] < 0]
        text = "Congrats! You earned: " + rewards.text(s.ctx.templates, order).removeprefix("Received: ")
        s.send(S_ALERT, pb.ChatChannelMsg(channel=7, encodeMsg=text))
        s.send(S_VICE_PASSWORD, pb.VicePasswordMsg(opType=VP_FIRST, result=0))
    elif ok or changed:
        await s.ctx.characters.save(c)
    s.send(S_VICE_PASSWORD, pb.VicePasswordMsg(opType=msg.opType, result=int(ok)))
    if text:
        s.send(S_CHAT, pb.ChatChannelMsg(channel=3, encodeMsg=text))


async def _grant_first(s: GameSession, drops: list[rewards.Drop]) -> None:
    """(visto) oficial_encantar #257-#269: 109, 3, 115, 4476 e os 4484 de item ganho."""
    from ..castle import castle_yield
    from . import events
    from .player import _player  # player importa login, que importa este módulo

    snap = s.snapshot
    assert snap is not None
    now = s.ctx.clock.now()
    new, _ = rewards.grant(snap, s.ctx.templates, drops)
    st = gev.state(snap, FIRST_KEY, now)
    st.text, st.updated_at = "1", now
    await s.ctx.characters.save(*rewards.owners(snap), *new, st)
    castle_yield(s)
    _player(s)
    if new:
        s.send(S_ITEMS, rewards.items_msg(new, s.player_id))
        events.items_gained(s)


def first_reward_pending(snap: PlayerSnapshot) -> bool:
    return gev.peek(snap, FIRST_KEY) is None


def login_first(s: GameSession) -> None:
    """(visto) oficial_encantar #95: 4696 opType 6 result 1 logo antes do 4598 enquanto a recompensa da primeira
    senha não saiu; o mesmo personagem, depois de criar a senha (#256), não recebe mais (153200, 171155, 215937,
    231733); só turco: login.json #99. O tutorial_en (personagem novo) não tem: (dedução) só depois do tutorial."""
    snap = s.snapshot
    assert snap is not None
    c = snap.character  # com senha já feita (sem a recompensa: mochila cheia) não há como resgatar
    if c.novice_process >= space.POST_TUTORIAL and not c.vice_password and first_reward_pending(snap):
        s.send(S_VICE_PASSWORD, pb.VicePasswordMsg(opType=VP_FIRST, result=1))


def _first_reward(s: GameSession) -> list[rewards.Drop]:
    """``vice_password_reward`` (ConfigInfos: "首次添加二级密码时获得的奖励"); o cliente mostra o mesmo em
    ``SetVPView``. Vazio se já saiu ou a mochila não cabe."""
    snap = s.snapshot
    assert snap is not None
    if not first_reward_pending(snap):
        return []
    raw = rules.config(s.ctx.templates, "vice_password_reward", "")
    drops = [(int(t), int(n)) for t, n in (p.split(",") for p in raw.split("|") if p)]
    if not rewards.can_grant(snap, s.ctx.templates, drops, s.ctx.clock.now()):
        s.log.info("recompensa da senha secundária: mochila cheia")  # (dedução) fica para a próxima senha
        return []
    return drops


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

    O oficial não responde (tutorial_en: 33 pacotes 20010, #130 o primeiro, nenhuma resposta); só registra.
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
    key = scene_key(s)  # todos no mesmo mapa (sala ou mapa compartilhado) veem quem saiu do nó
    for o in s.ctx.online.sessions():
        if o.campaign is not None and scene_key(o) == key:
            o.send(S_NODE_STAND, state)
