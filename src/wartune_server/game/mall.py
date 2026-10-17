"""Mercado entre jogadores: encerrar os anúncios vencidos e as cartas que saem deles (correio).

Não há job agendado: ``settle`` roda no começo de cada pedido do mercado (``handlers/mall.py``), na mesma
transação da operação. O item e o diamante vão pelo correio porque o destinatário pode estar offline e o
snapshot dele não pode ser alterado daqui.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..domain.models import Item, Mail, MailType
from ..domain.repositories import UnitOfWork
from ..templates.repository import GameTemplates
from . import mail as mailbox
from .bag import name

DIAMOND = -400  # TemplateId da moeda no correio (CURRENCIES, handlers/player.py): elmas não vinculados


async def post(
    uow: UnitOfWork,
    receiver: int,
    now: datetime,
    title: str,
    text: str,
    goods: Sequence[tuple[int, int]] = (),
    items: Sequence[Item] = (),
) -> Mail:
    """Carta do sistema na transação de quem chama (sem ``commit``). Mande o 148 com ``notify`` depois."""
    mail = Mail(receiver, now, title, text, mail_type=MailType.SYSTEM, send_type=mailbox.SYSTEM_SENDER)
    await mailbox.stage(uow, mail, goods, items)
    return mail


async def settle(uow: UnitOfWork, templates: GameTemplates, server_id: int, now: datetime) -> list[Mail]:
    """Encerra os anúncios vencidos do servidor. Com lance: o item vai ao vencedor e o diamante ao vendedor.
    Sem lance: o item volta ao vendedor. Devolve as cartas (o 148 sai depois do commit)."""
    due = await uow.mall.expired(server_id, now)
    if not due:
        return []
    items = {i.id: i for i in await uow.items.by_ids([x.item_id for x in due])}
    mails: list[Mail] = []
    for listing in due:
        for bid in await uow.mall.bids_of(listing.id or 0):
            await uow.delete(bid)
        await uow.delete(listing)
        item = items.get(listing.item_id)
        if item is None:  # o item é apagado junto com o anúncio (cascata): não há o que entregar
            continue
        label = f"{name(templates, item.template_id)} x{item.count}"
        if listing.bidder_id:
            mails.append(
                await post(
                    uow, listing.bidder_id, now, "Kazanılan eşya", f"{label}: en yüksek teklif sizde.", items=[item]
                )
            )
            mails.append(
                await post(
                    uow, listing.seller_id, now, "Satış geliri", f"{label} satıldı.", goods=[(DIAMOND, listing.point)]
                )
            )
        else:
            mails.append(
                await post(uow, listing.seller_id, now, "Geri dönen eşya", f"{label}: alıcı çıkmadı.", items=[item])
            )
    return mails
