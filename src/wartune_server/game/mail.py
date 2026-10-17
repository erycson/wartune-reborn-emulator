"""Correio: gravar e avisar (148), montar ``MailInfoMsg`` e o XML do ``maillist``.

O cliente lê a lista por HTTP (``EmailManager.getMailList``) e mapeia cada atributo de ``<Info>``
para o campo de mesmo nome de ``EmailInfo``. Anexos aqui são sempre por template: ``AnnexN``
negativo (o cliente só busca ``itemlist`` para ``AnnexN > 0``), ``AnnexNName`` = TemplateId.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from xml.sax.saxutils import quoteattr

from ..domain.models import BagType, Item, Mail, MailAnnex, MailType
from ..domain.repositories import UnitOfWork
from ..protocol.messages import wartune_pb2 as pb
from ..services.characters import CharacterService
from .builders.login import fmt_time
from .session import GameContext, OnlinePlayers

S_NEW_MAIL = 148
UNREAD = "2999-01-01 00:00:00"  # EmailInfo.isRead: ano 2999 = não lido
SYSTEM_SENDER = 2  # EmailInfo.SendType 2: ícone de GM, sem "responder"
MAX_ANNEXES = 5


async def deliver(
    characters: CharacterService,
    online: OnlinePlayers,
    mail: Mail,
    goods: Sequence[tuple[int, int]] = (),
    *also: object,
) -> list[MailAnnex]:
    """Grava o correio, os anexos e ``also`` (ex. o ouro do remetente) numa transação; avisa o 148."""
    if len(goods) > MAX_ANNEXES:
        raise ValueError("no máximo 5 anexos por correio")
    annexes: list[MailAnnex] = []

    async def insert(uow: UnitOfWork) -> None:
        for entity in (mail, *also):
            await uow.save(entity)
        await uow.flush()  # o anexo precisa do id do correio
        for slot, (template_id, count) in enumerate(goods, 1):
            annexes.append(MailAnnex(mail.id or 0, slot, template_id, count))
            await uow.save(annexes[-1])

    await characters.write(insert)
    if (receiver := online.get(mail.receiver_id)) is not None:
        receiver.send(S_NEW_MAIL, pb.MailMsg(playerId=mail.receiver_id, mailId=mail.id))
    return annexes


async def stage(uow: UnitOfWork, mail: Mail, goods: Sequence[tuple[int, int]] = (), items: Sequence[Item] = ()) -> None:
    """Põe o correio na transação de quem chama (sem ``commit``): anexos por template e itens que já têm
    linha, que passam para a bolsa MAIL do destinatário. Quem chama manda o 148 com ``notify`` depois."""
    if len(goods) + len(items) > MAX_ANNEXES:
        raise ValueError("no máximo 5 anexos por correio")
    await uow.save(mail)
    await uow.flush()  # o anexo precisa do id do correio
    slot = 0
    for item in items:
        item.character_id, item.bag_type, item.object_id, item.pos = mail.receiver_id, BagType.MAIL, 0, 0
        await uow.save(item)
        slot += 1
        await uow.save(MailAnnex(mail.id or 0, slot, item.template_id, item.count, item_id=item.id or 0))
    for template_id, count in goods:
        slot += 1
        await uow.save(MailAnnex(mail.id or 0, slot, template_id, count))


def notify(online: OnlinePlayers, mail: Mail) -> None:
    """148 para o destinatário, se estiver online. Depois do commit."""
    if (receiver := online.get(mail.receiver_id)) is not None:
        receiver.send(S_NEW_MAIL, pb.MailMsg(playerId=mail.receiver_id, mailId=mail.id))


async def send_system_mail(
    ctx: GameContext, receiver_id: int, title: str, contents: str, goods: Sequence[tuple[int, int]] = ()
) -> Mail:
    """Correio do servidor com anexos ``(templateId, quantidade)`` (moedas: -100 ouro, -400 diamante...).

    Para quando o item não cabe na mochila, recompensas, casamento etc.; até 5 anexos por correio.
    """
    mail = Mail(receiver_id, ctx.clock.now(), title, contents, mail_type=MailType.SYSTEM, send_type=SYSTEM_SENDER)
    await deliver(ctx.characters, ctx.online, mail, goods)
    return mail


def fields(mail: Mail, annexes: Sequence[MailAnnex], receiver_nick: str) -> dict[str, object]:
    """Campos de ``EmailInfo`` (mesmos nomes no XML; o 4131 usa a versão camelCase)."""
    out: dict[str, object] = {
        "Id": mail.id,
        "MailType": mail.mail_type,
        "SendId": mail.sender_id,
        "SendType": mail.send_type,
        "SendNickName": mail.sender_nick,
        "SendPlayerGrade": mail.sender_grades,
        "ReceiveId": mail.receiver_id,
        "ReceiveNickName": receiver_nick,
        "SendDate": fmt_time(mail.sent_at),
        "ReadDate": fmt_time(mail.read_at) if mail.read_at else UNREAD,
        "Title": mail.title,
        "Contents": mail.contents,
        "RemoveDate": fmt_time(mail.sent_at + timedelta(days=mail.validity_days)),
        "ValidityDate": mail.validity_days,
        "IsExist": True,
    }
    by_slot = {a.slot: a for a in annexes if a.mail_id == mail.id}
    for slot in range(1, MAX_ANNEXES + 1):
        a = by_slot.get(slot)
        out[f"Annex{slot}"] = -(a.id or slot) if a else 0
        out[f"Annex{slot}Name"] = a.template_id if a else 0
        out[f"Annex{slot}Count"] = a.count if a else 0
        out[f"IsAnnex{slot}"] = a.taken if a else False
    return out


def info_msg(mail: Mail, annexes: Sequence[MailAnnex], receiver_nick: str) -> pb.MailInfoMsg:
    """``MailInfoMsg`` do 4131 (``EmailHelp.transferToMailInfo``)."""
    f = fields(mail, annexes, receiver_nick)
    msg = pb.MailInfoMsg(sendPlayerGrades=mail.sender_grades)
    for key, value in f.items():
        name = {"Id": "id", "SendPlayerGrade": None}.get(key, key[0].lower() + key[1:])
        if name is not None:
            setattr(msg, name, value)
    return msg


def list_xml(mails: Sequence[Mail], annexes: Sequence[MailAnnex], receiver_nick: str) -> str:
    def attr(value: object) -> str:
        return quoteattr(str(value).lower() if isinstance(value, bool) else str(value))

    infos = "".join(
        "<Info " + " ".join(f"{k}={attr(v)}" for k, v in fields(m, annexes, receiver_nick).items()) + "/>"
        for m in mails
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><Result value="true" message="Success">{infos}</Result>'
