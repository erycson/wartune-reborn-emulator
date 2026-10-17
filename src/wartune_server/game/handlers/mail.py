"""Correio pelo socket: enviar (8205), apagar (8206), pegar anexos (5022) e verificação de e-mail
(9591). A lista em si vai por HTTP (``maillist``, ver http/app.py e game/mail.py)."""

from __future__ import annotations

import re

from ...domain.models import Mail, MailAnnex, MailType
from ...protocol.messages import wartune_pb2 as pb
from .. import items, social
from .. import mail as mailbox
from ..builders import login as b
from ..builders.player import item_moved
from ..router import router
from ..session import GameSession
from .login import player_info
from .player import castle_yield

S_PICKUP, S_MAIL_UPDATE, S_DELETED, S_MAIL_CHECK, S_ITEMS, S_PLAYER = 114, 4131, 4132, 337, 115, 3
SEND_COST = 100  # EmailControler.sendEmail: precisa de 100 de ouro
TITLE_MAX, CONTENTS_MAX = 15, 300  # WriteEmailFrame: assunto maxChars 15; texto limitado a 7 linhas
MIN_GRADE = 6  # ReadEmailView: responder exige nível 6
PLAYER_MAIL = 1  # MailSendReqMsg.sendType: 1 jogador, 2 guilda
MAX_PICKUP = 50
_TAG = re.compile(r"<[^>]*>")


def _clean(raw: str, limit: int) -> str | None:
    text = _TAG.sub("", raw).strip()
    return text if 0 < len(text) <= limit else None


@router.on(8205)
async def send_mail(s: GameSession, msg: pb.MailSendReqMsg) -> None:
    """Correio de jogador para jogador: só texto (o proto não tem anexo), custa 100 de ouro.

    ponytail: correio de guilda (sendType 2) recusado até existir guilda.
    """
    snap = s.snapshot
    assert snap is not None
    c = snap.character
    title, contents = _clean(msg.title, TITLE_MAX), _clean(msg.contents, CONTENTS_MAX)
    targets = list(msg.receiverUserId)
    found = await social.characters(s.ctx, targets[:1]) if len(targets) == 1 else {}
    receiver = next((r.id for r in found.values() if r.server_id == c.server_id and r.id != c.id), None)
    if (
        msg.sendType != PLAYER_MAIL
        or receiver is None
        or title is None
        or contents is None
        or c.gold < SEND_COST
        or c.grades < MIN_GRADE
    ):
        s.log.info("8205 recusado", para=targets, tipo=msg.sendType, ouro=c.gold)
        return
    c.gold -= SEND_COST  # antes do await: dois envios seguidos não gastam o mesmo ouro
    mail = Mail(
        receiver,
        s.ctx.clock.now(),
        title,
        contents,
        sender_id=s.player_id,
        sender_nick=c.nickname or "",
        sender_grades=c.grades,
        mail_type=MailType.PLAYER,
    )
    await mailbox.deliver(s.ctx.characters, s.ctx.online, mail, (), c)
    castle_yield(s)


@router.on(8206)
async def delete_mail(s: GameSession, msg: pb.MailDelReqMsg) -> None:
    """4132 com os ids apagados; lista vazia o cliente mostra como erro."""
    ids = list(dict.fromkeys(msg.delList))[:MAX_PICKUP]
    mine = await s.ctx.characters.read(lambda uow: uow.mails.by_receiver(s.player_id, ids))
    if mine:
        await s.ctx.characters.save(delete=tuple(mine))  # anexos vão junto (ON DELETE CASCADE)
    s.send(S_DELETED, pb.MailDelReqMsg(delList=[m.id or 0 for m in mine]))


@router.on(5022)
async def take_annexes(s: GameSession, msg: pb.MailMsg) -> None:
    """Pega os anexos (``position`` 0 = todos, senão 1..5) de cada correio, tudo numa transação.

    Mochila sem espaço para todos os itens de um correio: aquele correio fica com result false.
    """
    snap = s.snapshot
    assert snap is not None
    ids = list(dict.fromkeys(msg.mailsIdArray))[:MAX_PICKUP]
    positions = dict(zip(msg.mailsIdArray, msg.position, strict=False))
    mails = await s.ctx.characters.read(lambda uow: uow.mails.by_receiver(s.player_id, ids))
    annexes = await s.ctx.characters.read(lambda uow: uow.mails.annexes([m.id or 0 for m in mails]))
    now = s.ctx.clock.now()
    c = snap.character
    before = c.gold, c.point, c.gift_token, c.strategy
    result = pb.MailPickupRspMsg()
    taken: list[MailAnnex] = []
    new_items = []
    for mail in mails:
        pos = positions.get(mail.id or 0, 0)
        wanted = [a for a in annexes if a.mail_id == mail.id and not a.taken and pos in (0, a.slot)]
        goods = [(a.template_id, a.count) for a in wanted]
        ok = bool(wanted) and items.fits(snap, goods) and all(items.known(s.ctx.templates, t) for t, _ in goods)
        if ok:
            new_items += items.grant(snap, goods)  # snapshot muda antes do save: nada de await no meio
            for a in wanted:
                a.taken = True
            taken += wanted
            mail.read_at = mail.read_at or now
        result.pickupResult.add(mailId=mail.id, attachIndex=pos, result=ok)
    if taken:
        await s.ctx.characters.save(c, *new_items, *taken, *(m for m in mails if m.read_at == now))
    s.send(S_PICKUP, result)
    if not taken:
        return
    update = pb.ReceiveMailMsg()
    for mail in mails:
        update.mailInfos.append(mailbox.info_msg(mail, annexes, c.nickname or ""))
    s.send(S_MAIL_UPDATE, update)
    if new_items:
        moved = pb.ItemMovedListMsg()
        for item in new_items:
            moved.moved.extend(item_moved(item.bag_type, 0, item.pos, item, s.player_id).moved)
        s.send(S_ITEMS, moved)
    if c.gold != before[0]:
        castle_yield(s)
    if (c.point, c.gift_token, c.strategy) != before[1:]:
        s.send(S_PLAYER, b.complete(player_info(s, snap)))


@router.on(9591)
async def mail_check(s: GameSession, msg: pb.MailCheckMsg) -> None:
    """Verificação do endereço de e-mail do jogador (op 1 pede o código, op 2 envia o PIN), que
    dá o prêmio ``mail_rewards``. Sem SMTP o código nunca chega: responde estado 0 (botão de
    enviar desligado) e não dá prêmio. Depende de um serviço de e-mail."""
    s.log.info("9591 sem SMTP; verificação de e-mail indisponível", op=msg.op)
    s.send(S_MAIL_CHECK, b.complete(pb.MailCheckMsg(op=msg.op, state=0, mail=msg.mail[:64])))
